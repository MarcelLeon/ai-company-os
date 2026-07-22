import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest

from aico.app.morning_delivery import MorningDeliveryRecord, SQLiteMorningDeliveryStore
from aico.app.recovery_backup import (
    RecoveryBackupReceipt,
    RecoveryBackupRecord,
    SQLiteRecoveryBackupStore,
)
from aico.app.recovery_drill import (
    RecoveryDrillReceipt,
    RecoveryDrillRecord,
    SQLiteRecoveryDrillStore,
)
from aico.app.runtime_alerts import SQLiteRuntimeAlertStore
from aico.app.runtime_health import RuntimeComponentHealth, RuntimeHealthSnapshot
from aico.app.runtime_owner import RuntimeOwnerLock, runtime_owner_lock_path
from aico.app.runtime_self_healing import (
    OwnedTaskRecoveryHealth,
    RecoveryStatus,
    RuntimeSelfHealingSnapshot,
)
from aico.app.scheduled_autonomy import (
    ScheduledAutonomyIntent,
    SQLiteScheduledAutonomyStore,
)
from aico.app.scheduled_autonomy_delivery import (
    AutonomyOutcomeDeliveryRecord,
    SQLiteAutonomyOutcomeDeliveryStore,
    autonomy_outcome_notification_id,
)
from aico.app.state_cli import run_state_cli
from aico.core import ChannelTarget, HealthStatus, SentMessage, Task, TaskSnapshot, TaskStatus
from aico.core.morning import morning_handoff_envelope
from aico.core.standing_autonomy import (
    StandingAutonomyOutcomeStatus,
    StandingAutonomyReceipt,
    StandingAutonomyReceiptStatus,
    StandingAutonomyRunDisposition,
    StandingAutonomyRunReceipt,
    standing_autonomy_outcome_envelope,
)
from aico.core.task_store import SQLiteTaskStateStore


def test_state_cli_summarizes_sqlite_state_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteTaskStateStore(db_path)
    store.upsert_task_record(
        Task(task_id="task-1", payload="hello", requester_id="user-1", target_persona="claude")
    )
    stdout = StringIO()

    assert run_state_cli(["--db", str(db_path)], stdout=stdout) == 0

    output = stdout.getvalue()
    assert f"AICO state DB: {db_path}" in output
    assert "schema_version: 13" in output
    assert "pending_recovery_audits: 0" in output
    assert "pending_runtime_alerts: 0" in output
    assert "runtime_health_alert_candidates: 0" in output
    assert "- task_records: 1" in output
    assert "- task_recovery_audit_outbox: 0" in output


def test_state_cli_reports_morning_receipt_without_raw_delivery_identity(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteMorningDeliveryStore(db_path)
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    delivery_id = "morning-" + "a" * 32
    envelope = morning_handoff_envelope(
        delivery_id=delivery_id,
        project_id="aico",
        task_snapshots=(),
    )
    store.enqueue(
        MorningDeliveryRecord(
            delivery_id=delivery_id,
            binding_sha256="b" * 64,
            scheduled_for=now,
            envelope=envelope,
            created_at=now,
            updated_at=now,
        )
    )
    store.begin_attempt(delivery_id, now=now)
    store.mark_delivered(
        delivery_id,
        sent=SentMessage(
            message_id="secret-platform-message",
            target=ChannelTarget(channel_name="telegram", target_id="secret-chat"),
        ),
        now=now,
    )
    stdout = StringIO()

    assert run_state_cli(["--db", str(db_path)], stdout=stdout) == 0

    output = stdout.getvalue()
    assert f"{delivery_id} status=delivered attempts=1" in output
    assert envelope.content_sha256 in output
    assert "secret-platform-message" not in output
    assert "secret-chat" not in output
    assert envelope.content.text not in output


def test_state_cli_reports_secret_free_scheduled_autonomy_evidence(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteScheduledAutonomyStore(db_path)
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    intent_id = "autonomy-" + "a" * 32
    proposal_id = "private-proposal-identity"
    task_id = "private-task-identity"
    store.ensure(
        ScheduledAutonomyIntent(
            intent_id=intent_id,
            delivery_id="morning-" + "b" * 32,
            binding_sha256="c" * 64,
            project_id="private-project",
            created_at=now,
            updated_at=now,
        )
    )
    store.begin_attempt(intent_id, now=now)
    store.mark_settled(
        intent_id,
        receipt=StandingAutonomyRunReceipt(
            intent_id=intent_id,
            project_id="private-project",
            disposition=StandingAutonomyRunDisposition.DISPATCH_RECORDED,
            proposal_id=proposal_id,
            task_id=task_id,
        ),
        now=now,
    )
    stdout = StringIO()

    assert run_state_cli(["--db", str(db_path)], stdout=stdout) == 0

    output = stdout.getvalue()
    assert f"{intent_id} status=settled attempts=1" in output
    assert hashlib.sha256(proposal_id.encode()).hexdigest() in output
    assert hashlib.sha256(task_id.encode()).hexdigest() in output
    assert proposal_id not in output
    assert task_id not in output
    assert "private-project" not in output

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE scheduled_autonomy_intents SET status = 'retrying' WHERE intent_id = ?",
            (intent_id,),
        )
    with pytest.raises(ValueError, match="state mismatch"):
        run_state_cli(["--db", str(db_path)], stdout=StringIO())


def test_state_cli_reports_outcome_ack_without_content_or_raw_message(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteAutonomyOutcomeDeliveryStore(db_path)
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    receipt = StandingAutonomyRunReceipt(
        intent_id="autonomy-" + "d" * 32,
        project_id="private-project",
        disposition=StandingAutonomyRunDisposition.DISPATCH_RECORDED,
        proposal_id="private-proposal",
        task_id="private-task",
    )
    envelope = standing_autonomy_outcome_envelope(
        receipt,
        StandingAutonomyReceipt(
            proposal_id="private-proposal",
            task_id="private-task",
            charter_id="private-charter",
            authorization_id="private-grant",
            status=StandingAutonomyReceiptStatus.EVIDENCE_MISSING,
            decided_at=now,
            outcome_status=StandingAutonomyOutcomeStatus.MISSING,
        ),
    )
    notification_id = autonomy_outcome_notification_id(receipt.intent_id)
    store.ensure(
        AutonomyOutcomeDeliveryRecord(
            notification_id=notification_id,
            intent_id=receipt.intent_id,
            binding_sha256="e" * 64,
            envelope=envelope,
            created_at=now,
            updated_at=now,
        )
    )
    store.begin_attempt(notification_id, now=now)
    store.mark_delivered(
        notification_id,
        sent=SentMessage(
            message_id="private-outcome-message",
            target=ChannelTarget(channel_name="telegram", target_id="private-chat"),
        ),
        now=now,
    )

    stdout = StringIO()
    assert run_state_cli(["--db", str(db_path)], stdout=stdout) == 0

    output = stdout.getvalue()
    assert f"{notification_id} intent={receipt.intent_id} status=delivered" in output
    assert "source_status=evidence_missing outcome=missing" in output
    assert envelope.content_sha256 in output
    assert envelope.content.text not in output
    assert "private-outcome-message" not in output
    assert "private-chat" not in output
    assert "private-project" not in output
    assert "private-proposal" not in output


def test_state_cli_reports_secret_free_recovery_backup_evidence(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteRecoveryBackupStore(db_path)
    now = datetime(2026, 7, 22, 10, tzinfo=UTC)
    backup_id = "recovery-" + "a" * 32
    artifact_sha256 = "b" * 64
    receipt_sha256 = "c" * 64
    store.ensure(
        RecoveryBackupRecord(
            backup_id=backup_id,
            binding_sha256="d" * 64,
            scheduled_for=now,
            created_at=now,
            updated_at=now,
        )
    )
    store.begin_attempt(backup_id, now=now)
    store.mark_verified(
        backup_id,
        receipt=RecoveryBackupReceipt(
            backup_id=backup_id,
            artifact_name="aico-core-recovery-" + "a" * 32 + ".zip",
            artifact_sha256=artifact_sha256,
            created_at=now,
            capture_window_seconds=2,
            state_schema_version=13,
            state_table_count=15,
            audit_event_count=3,
            audit_head_sha256="e" * 64,
            memory_record_count=4,
            memory_head_sha256="f" * 64,
            config_revision="1" * 40,
            destination_fingerprint_sha256="2" * 64,
        ),
        receipt_sha256=receipt_sha256,
        now=now,
    )
    stdout = StringIO()

    assert run_state_cli(["--db", str(db_path)], stdout=stdout) == 0

    output = stdout.getvalue()
    assert f"{backup_id} status=verified attempts=1" in output
    assert artifact_sha256 in output
    assert receipt_sha256 in output
    assert "custody=verified" in output
    assert "custody_failures=0" in output
    assert "1" * 40 not in output
    assert "2" * 64 not in output
    assert "aico-core-recovery" not in output

    drill_id = "drill-" + "4" * 32
    drill_store = SQLiteRecoveryDrillStore(db_path)
    drill_store.ensure(
        RecoveryDrillRecord(
            drill_id=drill_id,
            binding_sha256="d" * 64,
            backup_id=backup_id,
            policy_sha256="5" * 64,
            scheduled_for=now,
            created_at=now,
            updated_at=now,
        )
    )
    drill_store.begin_attempt(drill_id, now=now)
    drill_store.mark_verified(
        drill_id,
        receipt=RecoveryDrillReceipt(
            drill_id=drill_id,
            backup_id=backup_id,
            policy_sha256="5" * 64,
            artifact_sha256=artifact_sha256,
            backup_receipt_sha256=receipt_sha256,
            state_schema_version=13,
            state_table_count=13,
            audit_event_count=3,
            audit_head_sha256="e" * 64,
            memory_record_count=4,
            memory_head_sha256="f" * 64,
            config_revision="1" * 40,
            unresolved_asset_count=0,
            post_restore_evidence_asset_count=5,
            completed_at=now,
        ),
        receipt_sha256="6" * 64,
        now=now,
    )
    drill_stdout = StringIO()
    assert run_state_cli(["--db", str(db_path)], stdout=drill_stdout) == 0
    drill_output = drill_stdout.getvalue()
    assert f"{drill_id} status=verified attempts=1" in drill_output
    assert f"backup_id={backup_id}" in drill_output
    assert "policy_sha256=" + "5" * 64 in drill_output
    assert "receipt_sha256=" + "6" * 64 in drill_output
    assert "state_tables=13 unresolved_assets=0 post_restore_evidence_assets=5" in drill_output
    assert "1" * 40 not in drill_output
    assert "2" * 64 not in drill_output
    assert "aico-core-recovery" not in drill_output

    store.begin_prune(backup_id, policy_sha256="3" * 64, now=now)
    store.mark_pruned(backup_id, now=now)
    pruned_stdout = StringIO()
    assert run_state_cli(["--db", str(db_path)], stdout=pruned_stdout) == 0
    pruned_output = pruned_stdout.getvalue()
    assert f"{backup_id} status=pruned attempts=1" in pruned_output
    assert "retention_policy_sha256=" + "3" * 64 in pruned_output
    assert "retention_started_at=" in pruned_output
    assert "pruned_at=" in pruned_output
    assert "aico-core-recovery" not in pruned_output
    assert "2" * 64 not in pruned_output

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE scheduled_recovery_backups SET status = 'retrying' WHERE backup_id = ?",
            (backup_id,),
        )
    with pytest.raises(ValueError, match="state mismatch"):
        run_state_cli(["--db", str(db_path)], stdout=StringIO())


def test_state_cli_reset_requires_confirmation_and_clears_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteTaskStateStore(db_path)
    store.upsert_task_record(
        Task(task_id="task-1", payload="hello", requester_id="user-1", target_persona="claude")
    )
    store.upsert_task_snapshot(
        TaskSnapshot(
            task_id="task-1",
            target_persona="claude",
            status=TaskStatus.RUNNING,
        )
    )
    store.reconcile_running_tasks(reason="runtime recovery")
    alert_store = SQLiteRuntimeAlertStore(db_path)
    alert_store.observe(
        RuntimeSelfHealingSnapshot(
            status=RecoveryStatus.OPEN,
            checked_at=datetime(2026, 7, 21, 15, tzinfo=UTC),
            components=(
                OwnedTaskRecoveryHealth(
                    name="channel:telegram-polling",
                    status=RecoveryStatus.OPEN,
                    attempts=3,
                ),
            ),
        ),
        RuntimeHealthSnapshot(
            status=HealthStatus.FAILED,
            checked_at=datetime(2026, 7, 21, 15, tzinfo=UTC),
            components=(
                RuntimeComponentHealth(
                    kind="scheduler",
                    name="morning-push",
                    required=True,
                    status=HealthStatus.FAILED,
                ),
            ),
        ),
    )
    autonomy_store = SQLiteScheduledAutonomyStore(db_path)
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    autonomy_store.ensure(
        ScheduledAutonomyIntent(
            intent_id="autonomy-" + "d" * 32,
            delivery_id="morning-" + "e" * 32,
            binding_sha256="f" * 64,
            project_id="aico",
            created_at=now,
            updated_at=now,
        )
    )
    recovery_store = SQLiteRecoveryBackupStore(db_path)
    recovery_store.ensure(
        RecoveryBackupRecord(
            backup_id="recovery-" + "1" * 32,
            binding_sha256="2" * 64,
            scheduled_for=now,
            created_at=now,
            updated_at=now,
        )
    )
    drill_store = SQLiteRecoveryDrillStore(db_path)
    drill_store.ensure(
        RecoveryDrillRecord(
            drill_id="drill-" + "3" * 32,
            binding_sha256="2" * 64,
            backup_id="recovery-" + "1" * 32,
            policy_sha256="4" * 64,
            scheduled_for=now,
            created_at=now,
            updated_at=now,
        )
    )
    summary = StringIO()

    assert run_state_cli(["--db", str(db_path)], stdout=summary) == 0
    assert "pending_recovery_audits: 1" in summary.getvalue()
    assert "pending_runtime_alerts: 1" in summary.getvalue()
    assert "runtime_health_alert_candidates: 1" in summary.getvalue()
    assert alert_store.health_observation_count() == 1

    stdout = StringIO()

    assert run_state_cli(["--db", str(db_path), "reset"], stdout=stdout) == 2
    assert store.load_task_records()
    assert store.load_pending_recovery_audit_events()

    stdout = StringIO()
    assert run_state_cli(["--db", str(db_path), "reset", "--yes"], stdout=stdout) == 0
    assert store.load_task_records() == ()
    assert store.load_pending_recovery_audit_events() == ()
    assert alert_store.pending_count() == 0
    assert alert_store.active_incident_count() == 0
    assert alert_store.health_observation_count() == 0
    assert autonomy_store.load("autonomy-" + "d" * 32) is None
    assert recovery_store.load("recovery-" + "1" * 32) is None
    assert drill_store.load("drill-" + "3" * 32) is None


def test_state_cli_backup_verify_restore_and_owner_fenced_reset(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    backup_path = tmp_path / "backup.db"
    store = SQLiteTaskStateStore(db_path)
    store.upsert_task_record(
        Task(task_id="task-1", payload="hello", requester_id="user-1", target_persona="claude")
    )
    stdout = StringIO()

    assert (
        run_state_cli(
            ["--db", str(db_path), "backup", "--output", str(backup_path)],
            stdout=stdout,
        )
        == 0
    )
    backup_summary = json.loads(stdout.getvalue())
    assert backup_summary["operation"] == "backup"

    stdout = StringIO()
    assert (
        run_state_cli(
            ["--db", str(db_path), "verify", "--backup", str(backup_path)],
            stdout=stdout,
        )
        == 0
    )
    assert json.loads(stdout.getvalue())["sha256"] == backup_summary["sha256"]

    store.upsert_task_record(
        Task(task_id="task-2", payload="later", requester_id="user-1", target_persona="claude")
    )
    stdout = StringIO()
    assert (
        run_state_cli(
            [
                "--db",
                str(db_path),
                "restore",
                "--from",
                str(backup_path),
                "--expected-sha256",
                backup_summary["sha256"],
            ],
            stdout=stdout,
        )
        == 2
    )
    assert len(store.load_task_records()) == 2

    owner = RuntimeOwnerLock(
        runtime_owner_lock_path(db_path, base_dir=tmp_path),
        resource_path=db_path,
    )
    owner.acquire()
    try:
        stdout = StringIO()
        assert run_state_cli(["--db", str(db_path), "reset", "--yes"], stdout=stdout) == 3
        assert "active" in stdout.getvalue()
    finally:
        owner.release()
    assert len(store.load_task_records()) == 2

    stdout = StringIO()
    assert (
        run_state_cli(
            [
                "--db",
                str(db_path),
                "restore",
                "--from",
                str(backup_path),
                "--expected-sha256",
                backup_summary["sha256"],
                "--yes",
            ],
            stdout=stdout,
        )
        == 0
    )
    assert json.loads(stdout.getvalue())["operation"] == "restore"
    assert [task.task_id for task in store.load_task_records()] == ["task-1"]

    drill_live_path = tmp_path / "must-not-exist.db"
    drill_workspace = tmp_path / "drill-workspace"
    drill_report = tmp_path / "drill-report.json"
    drill_workspace.mkdir()
    stdout = StringIO()
    assert (
        run_state_cli(
            [
                "--db",
                str(drill_live_path),
                "drill",
                "--backup",
                str(backup_path),
                "--expected-sha256",
                backup_summary["sha256"],
                "--workspace",
                str(drill_workspace),
                "--report",
                str(drill_report),
            ],
            stdout=stdout,
        )
        == 0
    )
    assert json.loads(stdout.getvalue())["operation"] == "drill"
    assert drill_report.is_file()
    assert not drill_live_path.exists()
    assert tuple(drill_workspace.iterdir()) == ()
