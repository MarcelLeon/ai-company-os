from __future__ import annotations

import hashlib
import io
import json
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.app.memory_cli import run
from aico.app.memory_recovery import (
    MEMORY_LEDGER_MEMBER,
    MEMORY_QUARANTINE_MANIFEST_MEMBER,
    MemoryRecoveryError,
    create_memory_backup,
    drill_memory_backup,
    restore_memory_backup,
    verify_memory_backup,
)
from aico.app.runtime_owner import RuntimeOwnerLock, runtime_owner_lock_path
from aico.core import JsonlMemoryStore, MemoryAtom, MemoryEvidence, MemoryScope
from aico.core.memory_ledger import verify_memory_ledger
from aico.core.task_store import SQLiteTaskStateStore


def test_memory_backup_is_private_portable_and_drillable(tmp_path: Path) -> None:
    live = tmp_path / "private" / "memory.jsonl"
    backup = tmp_path / "exports" / "memory.zip"
    workspace = tmp_path / "workspace"
    report = tmp_path / "evidence" / "memory-drill.json"
    workspace.mkdir()
    JsonlMemoryStore(live).append_atom(_atom("mem-1", "merchant private fact"))

    created = create_memory_backup(
        live, backup, clock=lambda: datetime(2026, 7, 22, 12, tzinfo=UTC)
    )
    verified = verify_memory_backup(backup, expected_sha256=created.sha256)
    drill = drill_memory_backup(
        backup,
        expected_sha256=created.sha256,
        workspace=workspace,
        report_path=report,
        clock=lambda: datetime(2026, 7, 22, 13, tzinfo=UTC),
    )

    assert created.record_count == verified.record_count == drill.record_count == 1
    assert created.head_sha256 == verified.head_sha256 == drill.head_sha256
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    assert stat.S_IMODE(report.stat().st_mode) == 0o600
    assert tuple(workspace.iterdir()) == ()
    assert "merchant private fact" not in report.read_text()
    assert str(live) not in report.read_text()


def test_backup_rejects_tampered_member_even_with_rewritten_manifest(tmp_path: Path) -> None:
    live = tmp_path / "memory.jsonl"
    backup = tmp_path / "memory.zip"
    JsonlMemoryStore(live).append_atom(_atom("mem-1", "trusted claim"))
    create_memory_backup(live, backup)
    members = _members(backup)
    members[MEMORY_LEDGER_MEMBER] = members[MEMORY_LEDGER_MEMBER].replace(
        b"trusted claim", b"altered claim"
    )
    manifest = json.loads(members["manifest.json"])
    manifest["ledger"]["sha256"] = hashlib.sha256(members[MEMORY_LEDGER_MEMBER]).hexdigest()
    members["manifest.json"] = (
        json.dumps(manifest, separators=(",", ":"), sort_keys=True).encode() + b"\n"
    )
    _rewrite(backup, members)

    with pytest.raises(MemoryRecoveryError, match="integrity"):
        verify_memory_backup(backup)


def test_owner_fenced_restore_preserves_newer_live_memory(tmp_path: Path) -> None:
    live = tmp_path / "memory.jsonl"
    backup = tmp_path / "memory.zip"
    safety = tmp_path / "pre-restore.zip"
    state_db = tmp_path / "state.db"
    SQLiteTaskStateStore(state_db)
    store = JsonlMemoryStore(live)
    store.append_atom(_atom("before", "captured version"))
    artifact = create_memory_backup(live, backup)
    store.append_atom(_atom("after", "newer live version"))

    restored = restore_memory_backup(
        live,
        backup,
        expected_sha256=artifact.sha256,
        state_db_path=state_db,
        preservation_path=safety,
        base_dir=tmp_path,
        confirmed=True,
    )

    assert restored.record_count == 1
    assert restored.preservation is not None
    assert restored.preservation.kind == "verified_safety"
    assert verify_memory_ledger(live).record_count == 1
    assert verify_memory_backup(safety).record_count == 2


def test_restore_quarantines_corrupt_live_and_refuses_active_owner(tmp_path: Path) -> None:
    live = tmp_path / "memory.jsonl"
    backup = tmp_path / "memory.zip"
    quarantine = tmp_path / "corrupt-live.zip"
    state_db = tmp_path / "state.db"
    SQLiteTaskStateStore(state_db)
    JsonlMemoryStore(live).append_atom(_atom("mem-1", "merchant secret"))
    artifact = create_memory_backup(live, backup)
    corrupt = live.read_bytes().replace(b"merchant secret", b"merchant stolen")
    live.write_bytes(corrupt)

    owner = RuntimeOwnerLock(
        runtime_owner_lock_path(state_db, base_dir=tmp_path), resource_path=state_db
    )
    owner.acquire()
    try:
        with pytest.raises(MemoryRecoveryError, match="active"):
            restore_memory_backup(
                live,
                backup,
                expected_sha256=artifact.sha256,
                state_db_path=state_db,
                preservation_path=quarantine,
                base_dir=tmp_path,
                confirmed=True,
            )
    finally:
        owner.release()
    assert not quarantine.exists()

    restored = restore_memory_backup(
        live,
        backup,
        expected_sha256=artifact.sha256,
        state_db_path=state_db,
        preservation_path=quarantine,
        base_dir=tmp_path,
        confirmed=True,
    )
    assert restored.preservation is not None
    assert restored.preservation.kind == "unverified_quarantine"
    with zipfile.ZipFile(quarantine) as archive:
        assert archive.read(MEMORY_LEDGER_MEMBER) == corrupt
        manifest = archive.read(MEMORY_QUARANTINE_MANIFEST_MEMBER).decode()
    assert "merchant secret" not in manifest
    assert str(live) not in manifest


def test_memory_cli_uses_environment_and_keeps_errors_payload_free(tmp_path: Path) -> None:
    live = tmp_path / "memory.jsonl"
    backup = tmp_path / "memory.zip"
    JsonlMemoryStore(live).append_atom(_atom("mem-1", "merchant private payload"))
    stdout = io.StringIO()

    assert (
        run(
            ["backup", "--output", str(backup)],
            stdout=stdout,
            environ={"AICO_MEMORY_PATH": str(live)},
        )
        == 0
    )
    created = json.loads(stdout.getvalue())
    error = io.StringIO()
    assert (
        run(
            [
                "verify-backup",
                "--backup",
                str(backup),
                "--expected-sha256",
                "0" * 64,
            ],
            stderr=error,
            environ={},
        )
        == 2
    )
    assert created["record_count"] == 1
    assert "does not match" in error.getvalue()
    assert "merchant private payload" not in error.getvalue()
    assert str(live) not in error.getvalue()


def _atom(memory_id: str, claim: str) -> MemoryAtom:
    return MemoryAtom(
        memory_id=memory_id,
        claim=claim,
        evidence=(MemoryEvidence(ref=f"task:{memory_id}", source="test"),),
        scope=MemoryScope.project("aico"),
        source="test",
        confidence=0.9,
        created_by="test-agent",
    )


def _members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _rewrite(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    path.chmod(0o600)
