from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

import aico.app.state_backup as state_backup_module
from aico.app.recovery_backup import RecoveryBackupRecord, SQLiteRecoveryBackupStore
from aico.app.recovery_drill import RecoveryDrillRecord, SQLiteRecoveryDrillStore
from aico.app.runtime_alerts import SQLiteRuntimeAlertStore
from aico.app.runtime_owner import RuntimeOwnerLock, runtime_owner_lock_path
from aico.app.scheduled_autonomy import (
    ScheduledAutonomyIntent,
    SQLiteScheduledAutonomyStore,
)
from aico.app.scheduled_autonomy_delivery import SQLiteAutonomyOutcomeDeliveryStore
from aico.app.state_backup import (
    StateBackupError,
    create_state_backup,
    drill_state_backup,
    restore_state_backup,
    verify_state_backup,
)
from aico.core import Task
from aico.core.task_store import SQLiteTaskStateStore


def test_online_backup_is_consistent_while_runtime_owner_is_active(tmp_path: Path) -> None:
    state_path = tmp_path / "state.db"
    backup_path = tmp_path / "backup.db"
    store = SQLiteTaskStateStore(state_path)
    store.upsert_task_record(_task("task-1"))
    autonomy_store = SQLiteScheduledAutonomyStore(state_path)
    autonomy_store.ensure(
        ScheduledAutonomyIntent(
            intent_id="autonomy-" + "a" * 32,
            delivery_id="morning-" + "b" * 32,
            binding_sha256="c" * 64,
            project_id="aico",
            created_at=datetime(2026, 7, 22, 9, tzinfo=UTC),
            updated_at=datetime(2026, 7, 22, 9, tzinfo=UTC),
        )
    )
    SQLiteAutonomyOutcomeDeliveryStore(state_path)
    SQLiteRuntimeAlertStore(state_path)
    recovery_store = SQLiteRecoveryBackupStore(state_path)
    recovery_store.ensure(
        RecoveryBackupRecord(
            backup_id="recovery-" + "d" * 32,
            binding_sha256="e" * 64,
            scheduled_for=datetime(2026, 7, 22, 9, tzinfo=UTC),
            created_at=datetime(2026, 7, 22, 9, tzinfo=UTC),
            updated_at=datetime(2026, 7, 22, 9, tzinfo=UTC),
        )
    )
    drill_store = SQLiteRecoveryDrillStore(state_path)
    drill_store.ensure(
        RecoveryDrillRecord(
            drill_id="drill-" + "f" * 32,
            binding_sha256="e" * 64,
            backup_id="recovery-" + "d" * 32,
            policy_sha256="1" * 64,
            scheduled_for=datetime(2026, 7, 22, 9, tzinfo=UTC),
            created_at=datetime(2026, 7, 22, 9, tzinfo=UTC),
            updated_at=datetime(2026, 7, 22, 9, tzinfo=UTC),
        )
    )
    owner = RuntimeOwnerLock(
        runtime_owner_lock_path(state_path, base_dir=tmp_path),
        resource_path=state_path,
    )
    owner.acquire()
    try:
        summary = create_state_backup(state_path, backup_path)
        store.upsert_task_record(_task("task-2"))
    finally:
        owner.release()

    backed_up = SQLiteTaskStateStore(backup_path).load_task_records()
    assert [task.task_id for task in backed_up] == ["task-1"]
    assert summary.operation == "backup"
    assert summary.schema_version == 13
    assert summary.integrity == "ok"
    assert summary.table_counts["task_records"] == 1
    assert summary.table_counts["scheduled_autonomy_intents"] == 1
    assert summary.table_counts["scheduled_autonomy_outcome_outbox"] == 0
    assert summary.table_counts["runtime_health_alert_observations"] == 0
    assert summary.table_counts["scheduled_recovery_backups"] == 1
    assert summary.table_counts["scheduled_recovery_drills"] == 1
    with sqlite3.connect(backup_path) as connection:
        assert connection.execute("SELECT status FROM scheduled_autonomy_intents").fetchone() == (
            "pending",
        )
        assert connection.execute("SELECT status FROM scheduled_recovery_backups").fetchone() == (
            "pending",
        )
        assert connection.execute("SELECT status FROM scheduled_recovery_drills").fetchone() == (
            "pending",
        )
    assert summary.sha256 == hashlib.sha256(backup_path.read_bytes()).hexdigest()
    assert stat.S_IMODE(backup_path.stat().st_mode) == 0o600
    assert not Path(f"{backup_path}-wal").exists()


def test_verify_is_read_only_and_rejects_corrupt_or_wrong_schema(tmp_path: Path) -> None:
    state_path = tmp_path / "state.db"
    backup_path = tmp_path / "backup.db"
    SQLiteTaskStateStore(state_path).upsert_task_record(_task("task-1"))
    create_state_backup(state_path, backup_path)
    before = backup_path.read_bytes()

    verified = verify_state_backup(backup_path)

    assert backup_path.read_bytes() == before
    assert verified.operation == "verify"
    assert verified.sha256 == hashlib.sha256(before).hexdigest()

    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not a sqlite database")
    with pytest.raises(StateBackupError, match="integrity"):
        verify_state_backup(corrupt)

    wrong_schema = tmp_path / "wrong-schema.db"
    wrong_schema.write_bytes(before)
    with sqlite3.connect(wrong_schema) as connection:
        connection.execute("UPDATE aico_schema SET value = '3' WHERE key = 'schema_version'")
    with pytest.raises(StateBackupError, match="schema"):
        verify_state_backup(wrong_schema)


def test_restore_round_trip_creates_safety_backup_and_removes_stale_sidecars(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.db"
    backup_path = tmp_path / "backup.db"
    store = SQLiteTaskStateStore(state_path)
    store.upsert_task_record(_task("task-before-backup"))
    backup = create_state_backup(state_path, backup_path)
    store.upsert_task_record(_task("task-after-backup"))
    Path(f"{state_path}-wal").write_bytes(b"")
    Path(f"{state_path}-shm").write_bytes(b"")

    restored = restore_state_backup(
        state_path,
        backup_path,
        expected_sha256=backup.sha256,
        base_dir=tmp_path,
        clock=lambda: datetime(2026, 7, 21, 18, tzinfo=UTC),
    )

    records = SQLiteTaskStateStore(state_path).load_task_records()
    assert [task.task_id for task in records] == ["task-before-backup"]
    assert restored.operation == "restore"
    assert restored.restored_sha256 == backup.sha256
    assert restored.safety_backup_name == "state.db.pre-restore-20260721T180000Z.db"
    assert restored.safety_backup_name is not None
    safety = tmp_path / restored.safety_backup_name
    assert [task.task_id for task in SQLiteTaskStateStore(safety).load_task_records()] == [
        "task-before-backup",
        "task-after-backup",
    ]
    assert stat.S_IMODE(safety.stat().st_mode) == 0o600
    assert not Path(f"{state_path}-wal").exists()
    assert not Path(f"{state_path}-shm").exists()


def test_restore_rejects_hash_mismatch_and_active_owner_without_mutation(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.db"
    backup_path = tmp_path / "backup.db"
    store = SQLiteTaskStateStore(state_path)
    store.upsert_task_record(_task("task-1"))
    backup = create_state_backup(state_path, backup_path)
    store.upsert_task_record(_task("task-2"))
    before = state_path.read_bytes()

    with pytest.raises(StateBackupError, match="SHA"):
        restore_state_backup(
            state_path,
            backup_path,
            expected_sha256="0" * 64,
            base_dir=tmp_path,
        )
    assert state_path.read_bytes() == before

    owner = RuntimeOwnerLock(
        runtime_owner_lock_path(state_path, base_dir=tmp_path),
        resource_path=state_path,
    )
    owner.acquire()
    try:
        with pytest.raises(StateBackupError, match="active"):
            restore_state_backup(
                state_path,
                backup_path,
                expected_sha256=backup.sha256,
                base_dir=tmp_path,
            )
    finally:
        owner.release()
    assert [task.task_id for task in store.load_task_records()] == ["task-1", "task-2"]


def test_backup_rejects_missing_source_existing_output_and_same_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "state.db"
    output_path = tmp_path / "backup.db"
    with pytest.raises(StateBackupError, match="source"):
        create_state_backup(state_path, output_path)

    SQLiteTaskStateStore(state_path)
    output_path.write_bytes(b"keep me")
    with pytest.raises(StateBackupError, match="exists"):
        create_state_backup(state_path, output_path)
    assert output_path.read_bytes() == b"keep me"

    with pytest.raises(StateBackupError, match="differ"):
        create_state_backup(state_path, state_path)

    concurrent_source = tmp_path / "concurrent-source.db"
    concurrent_source.write_bytes(b"new artifact")
    output_path.write_bytes(b"concurrent artifact")
    with pytest.raises(StateBackupError, match="exists"):
        state_backup_module._publish_new_file(concurrent_source, output_path)
    assert output_path.read_bytes() == b"concurrent artifact"

    output_path.unlink()

    def fail_directory_sync(_path: Path) -> None:
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(state_backup_module, "_sync_directory", fail_directory_sync)
    with pytest.raises(StateBackupError, match="failed"):
        create_state_backup(state_path, output_path)
    assert not output_path.exists()


def test_backup_summary_json_contains_no_payload_or_absolute_source_path(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "private" / "state.db"
    backup_path = tmp_path / "backup.db"
    private_payload = "private task content"
    SQLiteTaskStateStore(state_path).upsert_task_record(
        Task(
            task_id="task-1",
            payload=private_payload,
            requester_id="user-1",
            target_persona="claude",
        )
    )

    summary = create_state_backup(state_path, backup_path)
    rendered = summary.model_dump_json()

    assert private_payload not in rendered
    assert str(state_path) not in rendered
    assert json.loads(rendered)["artifact_name"] == "backup.db"


def test_disposable_drill_materializes_report_without_touching_live_state(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "private" / "state.db"
    backup_path = tmp_path / "off-device-copy.db"
    report_path = tmp_path / "evidence" / "restore-drill.json"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    private_payload = "merchant private payload"
    store = SQLiteTaskStateStore(state_path)
    store.upsert_task_record(
        Task(
            task_id="task-before-backup",
            payload=private_payload,
            requester_id="user-1",
            target_persona="claude",
        )
    )
    backup = create_state_backup(state_path, backup_path)
    store.upsert_task_record(_task("task-after-backup"))
    live_records_before = store.load_task_records()
    owner = RuntimeOwnerLock(
        runtime_owner_lock_path(state_path, base_dir=tmp_path),
        resource_path=state_path,
    )
    owner.acquire()
    try:
        summary = drill_state_backup(
            backup_path,
            expected_sha256=backup.sha256,
            workspace=workspace,
            report_path=report_path,
            clock=lambda: datetime(2026, 7, 21, 19, tzinfo=UTC),
        )
    finally:
        owner.release()

    assert summary.operation == "drill"
    assert summary.backup_sha256 == backup.sha256
    assert summary.table_counts["task_records"] == 1
    assert summary.report_name == "restore-drill.json"
    assert summary.materialized_bytes > 0
    assert len(summary.materialized_sha256) == 64
    assert tuple(workspace.iterdir()) == ()
    assert store.load_task_records() == live_records_before
    assert stat.S_IMODE(report_path.stat().st_mode) == 0o600
    rendered = report_path.read_text(encoding="utf-8")
    assert json.loads(rendered) == summary.model_dump(mode="json")
    assert private_payload not in rendered
    assert str(state_path) not in rendered
    assert str(backup_path) not in rendered
    assert str(workspace) not in rendered


def test_disposable_drill_rejects_invalid_inputs_without_publishing_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "state.db"
    backup_path = tmp_path / "backup.db"
    report_path = tmp_path / "report.json"
    SQLiteTaskStateStore(state_path).upsert_task_record(_task("task-1"))
    backup = create_state_backup(state_path, backup_path)

    with pytest.raises(StateBackupError, match="SHA"):
        drill_state_backup(
            backup_path,
            expected_sha256="0" * 64,
            report_path=report_path,
        )
    assert not report_path.exists()

    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not sqlite")
    with pytest.raises(StateBackupError, match="integrity"):
        drill_state_backup(
            corrupt,
            expected_sha256=hashlib.sha256(corrupt.read_bytes()).hexdigest(),
            report_path=report_path,
        )
    assert not report_path.exists()

    missing_workspace = tmp_path / "missing-workspace"
    with pytest.raises(StateBackupError, match="workspace"):
        drill_state_backup(
            backup_path,
            expected_sha256=backup.sha256,
            workspace=missing_workspace,
            report_path=report_path,
        )

    with pytest.raises(StateBackupError, match="differ"):
        drill_state_backup(
            backup_path,
            expected_sha256=backup.sha256,
            report_path=backup_path,
        )

    report_path.write_bytes(b"existing evidence")
    with pytest.raises(StateBackupError, match="exists"):
        drill_state_backup(
            backup_path,
            expected_sha256=backup.sha256,
            report_path=report_path,
        )
    assert report_path.read_bytes() == b"existing evidence"

    report_path.unlink()

    def publish_race(_source: Path, destination: Path) -> None:
        destination.write_bytes(b"concurrent evidence")
        raise FileExistsError

    monkeypatch.setattr("aico.app.state_backup.os.link", publish_race)
    with pytest.raises(StateBackupError, match="exists"):
        drill_state_backup(
            backup_path,
            expected_sha256=backup.sha256,
            report_path=report_path,
        )
    assert report_path.read_bytes() == b"concurrent evidence"


def test_disposable_drill_cleans_workspace_after_materialization_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_path = tmp_path / "state.db"
    backup_path = tmp_path / "backup.db"
    workspace = tmp_path / "workspace"
    report_path = tmp_path / "report.json"
    workspace.mkdir()
    SQLiteTaskStateStore(state_path).upsert_task_record(_task("task-1"))
    backup = create_state_backup(state_path, backup_path)

    def fail_restore(target_path: Path, *_args: object, **_kwargs: object) -> object:
        (target_path.parent / "partial-artifact").write_bytes(b"partial")
        raise StateBackupError("synthetic restore failure")

    monkeypatch.setattr(state_backup_module, "restore_state_backup", fail_restore)
    with pytest.raises(StateBackupError, match="synthetic"):
        drill_state_backup(
            backup_path,
            expected_sha256=backup.sha256,
            workspace=workspace,
            report_path=report_path,
        )

    assert tuple(workspace.iterdir()) == ()
    assert not report_path.exists()


def _task(task_id: str) -> Task:
    return Task(
        task_id=task_id,
        payload=f"payload for {task_id}",
        requester_id="user-1",
        target_persona="claude",
    )
