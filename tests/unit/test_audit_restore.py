from __future__ import annotations

import hashlib
import json
import os
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.app.audit_backup import (
    AUDIT_LEDGER_MEMBER,
    create_audit_backup,
    verify_audit_backup,
)
from aico.app.audit_restore import (
    AUDIT_QUARANTINE_MANIFEST_MEMBER,
    AuditRestoreError,
    drill_audit_backup,
    restore_audit_backup,
)
from aico.app.runtime_owner import RuntimeOwnerLock, runtime_owner_lock_path
from aico.core import AuditEvent, AuditEventType, InMemoryAuditLog, JsonlAuditSink, Task
from aico.core.audit_ledger import AuditIntegrityError, verify_audit_ledger
from aico.core.audit_recovery import replace_audit_ledger_snapshot
from aico.core.task_store import SQLiteTaskStateStore


def test_disposable_audit_drill_uses_materialization_and_publishes_safe_report(
    tmp_path: Path,
) -> None:
    live = tmp_path / "private" / "audit.jsonl"
    backup = tmp_path / "off-device.zip"
    workspace = tmp_path / "workspace"
    report = tmp_path / "evidence" / "audit-drill.json"
    workspace.mkdir()
    secret = "merchant private operation"
    _write_event(live, "event-1", "task-1", payload=secret)
    artifact = create_audit_backup(live, backup)
    before = live.read_bytes()

    summary = drill_audit_backup(
        backup,
        expected_sha256=artifact.sha256,
        workspace=workspace,
        report_path=report,
        clock=lambda: datetime(2026, 7, 22, 10, tzinfo=UTC),
    )

    assert summary.operation == "drill"
    assert summary.event_count == 1
    assert summary.backup_sha256 == artifact.sha256
    assert summary.report_name == "audit-drill.json"
    assert tuple(workspace.iterdir()) == ()
    assert live.read_bytes() == before
    assert stat.S_IMODE(report.stat().st_mode) == 0o600
    assert json.loads(report.read_text()) == summary.model_dump(mode="json")
    assert secret not in report.read_text()
    assert str(live) not in report.read_text()


def test_audit_drill_rejects_bad_hash_and_report_race_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = tmp_path / "audit.jsonl"
    backup = tmp_path / "recovery.zip"
    workspace = tmp_path / "workspace"
    report = tmp_path / "report.json"
    workspace.mkdir()
    _write_event(live, "event-1", "task-1")
    artifact = create_audit_backup(live, backup)

    with pytest.raises(AuditRestoreError, match="SHA"):
        drill_audit_backup(
            backup,
            expected_sha256="0" * 64,
            workspace=workspace,
            report_path=report,
        )
    assert tuple(workspace.iterdir()) == ()
    assert not report.exists()

    def publish_race(_source: Path, destination: Path) -> None:
        destination.write_bytes(b"concurrent evidence")
        raise FileExistsError

    monkeypatch.setattr("aico.app.audit_restore.os.link", publish_race)
    with pytest.raises(AuditRestoreError, match="already exists"):
        drill_audit_backup(
            backup,
            expected_sha256=artifact.sha256,
            workspace=workspace,
            report_path=report,
        )
    assert report.read_bytes() == b"concurrent evidence"
    assert tuple(workspace.iterdir()) == ()


def test_live_restore_is_owner_fenced_and_creates_verified_safety_backup(
    tmp_path: Path,
) -> None:
    live = tmp_path / "audit.jsonl"
    backup = tmp_path / "recovery.zip"
    safety = tmp_path / "pre-restore.zip"
    state_db = tmp_path / "state.db"
    SQLiteTaskStateStore(state_db)
    _write_event(live, "event-1", "task-before")
    artifact = create_audit_backup(live, backup)
    _write_event(live, "event-2", "task-after")

    summary = restore_audit_backup(
        live,
        backup,
        expected_sha256=artifact.sha256,
        state_db_path=state_db,
        preservation_path=safety,
        base_dir=tmp_path,
        confirmed=True,
        clock=lambda: datetime(2026, 7, 22, 11, tzinfo=UTC),
    )

    assert summary.operation == "restore"
    assert summary.event_count == 1
    assert summary.backup_sha256 == artifact.sha256
    assert summary.preservation is not None
    assert summary.preservation.kind == "verified_safety"
    assert summary.preservation.artifact_name == safety.name
    assert verify_audit_ledger(live).event_count == 1
    assert verify_audit_backup(safety).event_count == 2
    assert stat.S_IMODE(safety.stat().st_mode) == 0o600


def test_restore_quarantines_corrupt_live_bytes_without_claiming_integrity(
    tmp_path: Path,
) -> None:
    live = tmp_path / "audit.jsonl"
    backup = tmp_path / "recovery.zip"
    quarantine = tmp_path / "corrupt-live.zip"
    state_db = tmp_path / "state.db"
    SQLiteTaskStateStore(state_db)
    secret = "merchant-private-payload"
    _write_event(live, "event-1", "task-1", payload=secret)
    artifact = create_audit_backup(live, backup)
    corrupt = live.read_bytes().replace(b'"task_id": "task-1"', b'"task_id": "task-x"')
    live.write_bytes(corrupt)

    summary = restore_audit_backup(
        live,
        backup,
        expected_sha256=artifact.sha256,
        state_db_path=state_db,
        preservation_path=quarantine,
        base_dir=tmp_path,
        confirmed=True,
    )

    assert summary.preservation is not None
    assert summary.preservation.kind == "unverified_quarantine"
    assert summary.preservation.sha256 == hashlib.sha256(quarantine.read_bytes()).hexdigest()
    assert verify_audit_ledger(live).event_count == 1
    with zipfile.ZipFile(quarantine) as archive:
        assert archive.read(AUDIT_LEDGER_MEMBER) == corrupt
        manifest = archive.read(AUDIT_QUARANTINE_MANIFEST_MEMBER).decode()
    assert "unverified_quarantine" in manifest
    assert secret not in manifest
    assert str(live) not in manifest
    assert stat.S_IMODE(quarantine.stat().st_mode) == 0o600


def test_restore_refuses_active_owner_or_missing_confirmation_without_mutation(
    tmp_path: Path,
) -> None:
    live = tmp_path / "audit.jsonl"
    backup = tmp_path / "recovery.zip"
    preserve = tmp_path / "preserve.zip"
    state_db = tmp_path / "state.db"
    SQLiteTaskStateStore(state_db)
    _write_event(live, "event-1", "task-1")
    artifact = create_audit_backup(live, backup)
    _write_event(live, "event-2", "task-2")
    before = live.read_bytes()

    with pytest.raises(AuditRestoreError, match="confirmation"):
        _restore(live, backup, artifact.sha256, state_db, preserve, tmp_path, confirmed=False)
    assert live.read_bytes() == before
    assert not preserve.exists()

    owner = RuntimeOwnerLock(
        runtime_owner_lock_path(state_db, base_dir=tmp_path),
        resource_path=state_db,
    )
    owner.acquire()
    try:
        with pytest.raises(AuditRestoreError, match="active"):
            _restore(live, backup, artifact.sha256, state_db, preserve, tmp_path)
    finally:
        owner.release()
    assert live.read_bytes() == before
    assert not preserve.exists()


def test_restore_rejects_wrong_backup_hash_and_non_aico_fence_file(
    tmp_path: Path,
) -> None:
    live = tmp_path / "audit.jsonl"
    backup = tmp_path / "recovery.zip"
    preserve = tmp_path / "preserve.zip"
    state_db = tmp_path / "state.db"
    _write_event(live, "event-1", "task-1")
    artifact = create_audit_backup(live, backup)
    before = live.read_bytes()
    state_db.write_bytes(b"not an AICO state database")

    with pytest.raises(AuditRestoreError, match="identity"):
        _restore(live, backup, artifact.sha256, state_db, preserve, tmp_path)
    assert live.read_bytes() == before
    assert not preserve.exists()

    state_db.unlink()
    SQLiteTaskStateStore(state_db)
    with pytest.raises(AuditRestoreError, match="SHA"):
        _restore(live, backup, "0" * 64, state_db, preserve, tmp_path)
    assert live.read_bytes() == before
    assert not preserve.exists()


def test_pair_replacement_fails_closed_mid_publish_and_retry_converges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = tmp_path / "live.jsonl"
    source = tmp_path / "source.jsonl"
    _write_event(live, "event-live-1", "task-live-1")
    _write_event(live, "event-live-2", "task-live-2")
    _write_event(source, "event-source", "task-source")
    real_replace = os.replace

    def fail_checkpoint_publish(source_path: Path, destination_path: Path) -> None:
        if Path(destination_path).name == "live.jsonl.checkpoint.json":
            raise OSError("synthetic checkpoint publish failure")
        real_replace(source_path, destination_path)

    monkeypatch.setattr("aico.core.audit_recovery.os.replace", fail_checkpoint_publish)
    with pytest.raises(OSError, match="synthetic"):
        replace_audit_ledger_snapshot(live, source)
    with pytest.raises(AuditIntegrityError):
        verify_audit_ledger(live)

    monkeypatch.setattr("aico.core.audit_recovery.os.replace", real_replace)
    restored = replace_audit_ledger_snapshot(live, source)
    assert restored.event_count == 1
    assert verify_audit_ledger(live) == restored


def _restore(
    live: Path,
    backup: Path,
    sha256: str,
    state_db: Path,
    preserve: Path,
    base_dir: Path,
    *,
    confirmed: bool = True,
) -> object:
    return restore_audit_backup(
        live,
        backup,
        expected_sha256=sha256,
        state_db_path=state_db,
        preservation_path=preserve,
        base_dir=base_dir,
        confirmed=confirmed,
    )


def _write_event(path: Path, event_id: str, task_id: str, *, payload: str = "inspect") -> None:
    JsonlAuditSink(path).write(_event(event_id, task_id, payload=payload))


def _event(event_id: str, task_id: str, *, payload: str) -> AuditEvent:
    return InMemoryAuditLog(event_id_factory=lambda: event_id).record(
        AuditEventType.TASK_SUBMITTED,
        Task(
            task_id=task_id,
            payload=payload,
            requester_id="owner",
            target_persona="reviewer",
        ),
    )
