from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

import aico.app.audit_backup as audit_backup_module
import aico.core.audit_ledger as audit_ledger_module
from aico.app.audit_backup import (
    AUDIT_CHECKPOINT_MEMBER,
    AUDIT_LEDGER_MEMBER,
    AUDIT_MANIFEST_MEMBER,
    AuditBackupError,
    create_audit_backup,
    materialize_audit_backup,
    verify_audit_backup,
)
from aico.core import AuditEvent, AuditEventType, InMemoryAuditLog, JsonlAuditSink, Task
from aico.core.audit_ledger import verify_audit_ledger


def test_audit_backup_is_private_portable_and_offline_verifiable(tmp_path: Path) -> None:
    audit_path = tmp_path / "private" / "audit.jsonl"
    backup_path = tmp_path / "exports" / "audit-recovery.zip"
    private_payload = "merchant private operation"
    _write_event(audit_path, "event-1", "task-1", payload=private_payload)

    created = create_audit_backup(
        audit_path,
        backup_path,
        clock=lambda: datetime(2026, 7, 22, 9, tzinfo=UTC),
    )
    verified = verify_audit_backup(backup_path, expected_sha256=created.sha256)

    assert created.operation == "backup"
    assert verified.operation == "verify"
    assert created.event_count == verified.event_count == 1
    assert created.head_sha256 == verified.head_sha256
    assert created.sha256 == verified.sha256
    assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600
    with zipfile.ZipFile(backup_path) as archive:
        assert set(archive.namelist()) == {
            AUDIT_LEDGER_MEMBER,
            AUDIT_CHECKPOINT_MEMBER,
            AUDIT_MANIFEST_MEMBER,
        }
        manifest = archive.read(AUDIT_MANIFEST_MEMBER).decode("utf-8")
    assert private_payload not in manifest
    assert str(audit_path) not in manifest
    assert str(audit_path) not in created.model_dump_json()


def test_audit_backup_is_a_point_in_time_not_a_live_alias(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    backup_path = tmp_path / "recovery.zip"
    sink = JsonlAuditSink(audit_path)
    sink.write(_event("event-1", "task-1"))

    created = create_audit_backup(audit_path, backup_path)
    sink.write(_event("event-2", "task-2"))

    assert created.event_count == 1
    assert verify_audit_backup(backup_path).event_count == 1
    assert verify_audit_ledger(audit_path).event_count == 2


def test_audit_backup_materializes_initialized_empty_ledger(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    backup_path = tmp_path / "empty-recovery.zip"
    JsonlAuditSink(audit_path)

    created = create_audit_backup(audit_path, backup_path)

    assert created.event_count == 0
    assert created.ledger_bytes == 0
    assert verify_audit_backup(backup_path).event_count == 0


def test_audit_backup_repairs_valid_checkpoint_lag_before_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_path = tmp_path / "audit.jsonl"
    backup_path = tmp_path / "recovery.zip"
    sink = JsonlAuditSink(audit_path)
    real_write = audit_ledger_module._write_checkpoint  # noqa: SLF001

    def fail_checkpoint(*_args: object, **_kwargs: object) -> None:
        raise OSError("synthetic checkpoint failure")

    monkeypatch.setattr(audit_ledger_module, "_write_checkpoint", fail_checkpoint)
    with pytest.raises(OSError, match="synthetic"):
        sink.write(_event("event-1", "task-1"))
    monkeypatch.setattr(audit_ledger_module, "_write_checkpoint", real_write)

    created = create_audit_backup(audit_path, backup_path)

    assert created.event_count == 1
    assert verify_audit_backup(backup_path).event_count == 1
    assert verify_audit_ledger(audit_path).checkpoint_lag is False


def test_audit_backup_rejects_tampered_member_and_extra_member(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    backup_path = tmp_path / "recovery.zip"
    _write_event(audit_path, "event-1", "task-1")
    create_audit_backup(audit_path, backup_path)
    members = _archive_members(backup_path)
    members[AUDIT_LEDGER_MEMBER] = members[AUDIT_LEDGER_MEMBER].replace(
        b'"task_id": "task-1"',
        b'"task_id": "task-x"',
    )
    _rewrite_archive(backup_path, members)

    with pytest.raises(AuditBackupError, match="hash"):
        verify_audit_backup(backup_path)

    members = _archive_members(backup_path)
    members["unexpected.txt"] = b"not allowed"
    _rewrite_archive(backup_path, members)
    with pytest.raises(AuditBackupError, match="members"):
        verify_audit_backup(backup_path)


def test_audit_backup_rechecks_hash_chain_after_manifest_is_rewritten(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    backup_path = tmp_path / "recovery.zip"
    _write_event(audit_path, "event-1", "task-1")
    create_audit_backup(audit_path, backup_path)
    members = _archive_members(backup_path)
    members[AUDIT_LEDGER_MEMBER] = members[AUDIT_LEDGER_MEMBER].replace(
        b'"task_id": "task-1"',
        b'"task_id": "task-x"',
    )
    manifest = json.loads(members[AUDIT_MANIFEST_MEMBER])
    manifest["ledger"]["sha256"] = hashlib.sha256(members[AUDIT_LEDGER_MEMBER]).hexdigest()
    members[AUDIT_MANIFEST_MEMBER] = (
        json.dumps(manifest, separators=(",", ":"), sort_keys=True).encode("utf-8") + b"\n"
    )
    _rewrite_archive(backup_path, members)

    with pytest.raises(AuditBackupError, match="integrity"):
        verify_audit_backup(backup_path)


def test_materialization_checks_manifest_parity_before_publishing_output(
    tmp_path: Path,
) -> None:
    audit_path = tmp_path / "audit.jsonl"
    backup_path = tmp_path / "recovery.zip"
    output_path = tmp_path / "materialized.jsonl"
    _write_event(audit_path, "event-1", "task-1")
    create_audit_backup(audit_path, backup_path)
    members = _archive_members(backup_path)
    manifest = json.loads(members[AUDIT_MANIFEST_MEMBER])
    manifest["event_count"] = 2
    members[AUDIT_MANIFEST_MEMBER] = (
        json.dumps(manifest, separators=(",", ":"), sort_keys=True).encode("utf-8") + b"\n"
    )
    _rewrite_archive(backup_path, members)
    artifact_sha = hashlib.sha256(backup_path.read_bytes()).hexdigest()

    with pytest.raises(AuditBackupError, match="manifest"):
        materialize_audit_backup(
            backup_path,
            output_path,
            expected_sha256=artifact_sha,
        )
    assert not output_path.exists()
    assert not output_path.with_name("materialized.jsonl.checkpoint.json").exists()


def test_audit_backup_rejects_compressed_members(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    backup_path = tmp_path / "recovery.zip"
    _write_event(audit_path, "event-1", "task-1")
    create_audit_backup(audit_path, backup_path)
    members = _archive_members(backup_path)

    with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    backup_path.chmod(0o600)

    with pytest.raises(AuditBackupError, match="encoding"):
        verify_audit_backup(backup_path)


def test_audit_backup_rejects_wrong_hash_wide_permissions_and_symlink(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    backup_path = tmp_path / "recovery.zip"
    _write_event(audit_path, "event-1", "task-1")
    created = create_audit_backup(audit_path, backup_path)

    with pytest.raises(AuditBackupError, match="does not match"):
        verify_audit_backup(backup_path, expected_sha256="0" * 64)

    backup_path.chmod(0o644)
    with pytest.raises(AuditBackupError, match="owner-only"):
        verify_audit_backup(backup_path)
    backup_path.chmod(0o600)

    link = tmp_path / "linked.zip"
    link.symlink_to(backup_path)
    with pytest.raises(AuditBackupError, match="non-symlink"):
        verify_audit_backup(link, expected_sha256=created.sha256)


def test_audit_backup_refuses_missing_unsealed_or_existing_targets(tmp_path: Path) -> None:
    missing = tmp_path / "missing.jsonl"
    output = tmp_path / "recovery.zip"
    with pytest.raises(AuditBackupError, match="does not exist"):
        create_audit_backup(missing, output)

    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text(_event("legacy", "task-legacy").model_dump_json() + "\n")
    legacy.chmod(0o600)
    with pytest.raises(AuditBackupError, match="unsealed"):
        create_audit_backup(legacy, output)

    audit_path = tmp_path / "audit.jsonl"
    _write_event(audit_path, "event-1", "task-1")
    output.write_bytes(b"keep existing artifact")
    before = output.read_bytes()
    with pytest.raises(AuditBackupError, match="already exists"):
        create_audit_backup(audit_path, output)
    assert output.read_bytes() == before

    with pytest.raises(AuditBackupError, match="must differ"):
        create_audit_backup(audit_path, audit_path)


def test_audit_backup_publication_failure_removes_only_its_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_path = tmp_path / "audit.jsonl"
    output = tmp_path / "recovery.zip"
    _write_event(audit_path, "event-1", "task-1")

    def fail_sync(_path: Path) -> None:
        raise OSError("synthetic directory fsync failure")

    monkeypatch.setattr(audit_backup_module, "_sync_directory", fail_sync)

    with pytest.raises(AuditBackupError, match="failed"):
        create_audit_backup(audit_path, output)
    assert not output.exists()
    assert verify_audit_ledger(audit_path).event_count == 1


def _write_event(
    path: Path,
    event_id: str,
    task_id: str,
    *,
    payload: str = "inspect",
) -> None:
    JsonlAuditSink(path).write(_event(event_id, task_id, payload=payload))


def _event(event_id: str, task_id: str, *, payload: str = "inspect") -> AuditEvent:
    return InMemoryAuditLog(event_id_factory=lambda: event_id).record(
        AuditEventType.TASK_SUBMITTED,
        Task(
            task_id=task_id,
            payload=payload,
            requester_id="owner",
            target_persona="reviewer",
        ),
    )


def _archive_members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _rewrite_archive(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    path.chmod(0o600)
