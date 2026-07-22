from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aico.app.dead_man_receiver import DeadManNotificationProbeContract
from aico.app.dead_man_receiver_app import (
    DeadManReceiverSettings,
    build_dead_man_receiver_app,
)
from aico.app.dead_man_receiver_recovery import (
    DeadManReceiverRecoveryError,
    create_dead_man_receiver_backup,
    drill_dead_man_receiver_backup,
    restore_dead_man_receiver_backup,
    verify_dead_man_receiver_backup,
)
from aico.app.dead_man_receiver_recovery_cli import run
from aico.app.dead_man_receiver_store import (
    DeadManReceiverSchemaError,
    SQLiteDeadManReceiverStore,
)
from aico.app.runtime_owner import RuntimeOwnerLock, runtime_owner_lock_path


class _RecordingSink:
    async def send(self, _event: object) -> None:
        return None


def test_online_backup_is_consistent_and_private_while_receiver_owner_is_active(
    tmp_path: Path,
) -> None:
    state = tmp_path / "private" / "dead-man.db"
    backup = tmp_path / "receiver-backup.db"
    store, now = _seed_receiver(state)
    owner = RuntimeOwnerLock(
        runtime_owner_lock_path(state, base_dir=state.parent), resource_path=state
    )
    owner.acquire()
    try:
        summary = create_dead_man_receiver_backup(state, backup)
        assert store.record_notification_attempt(
            "private-event-open",
            acknowledged_routes=(True,),
            transport_succeeded=True,
            attempted_at=now + timedelta(seconds=182),
        )
    finally:
        owner.release()

    artifact_before = backup.read_bytes()
    verified = verify_dead_man_receiver_backup(backup)
    rendered = summary.model_dump_json()
    assert summary.operation == "backup"
    assert verified.operation == "verify"
    assert summary.monitor_count == 1
    assert summary.open_monitor_count == 1
    assert summary.outage_count == 1
    assert summary.event_count == 1
    assert summary.pending_event_count == 1
    assert verified.sha256 == hashlib.sha256(backup.read_bytes()).hexdigest()
    assert backup.read_bytes() == artifact_before
    assert stat.S_IMODE(state.stat().st_mode) == 0o600
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    assert "private-runtime" not in rendered
    assert "private-event-open" not in rendered
    assert str(state) not in rendered
    assert now.isoformat() not in rendered


def test_recovery_verifies_route_health_outbox_and_frozen_acknowledgements(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 12, tzinfo=UTC)
    state = tmp_path / "dead-man.db"
    store = SQLiteDeadManReceiverStore(state)
    store.configure_notification_policy(
        configured_routes=2,
        minimum_acknowledgements=1,
        configured_at=now,
    )
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    event = store.evaluate(now=now + timedelta(seconds=180))[0]
    assert store.record_notification_attempt(
        event.event_id,
        acknowledged_routes=(True, False),
        transport_succeeded=True,
        attempted_at=now + timedelta(seconds=180),
    )
    original = tmp_path / "backup.db"
    summary = create_dead_man_receiver_backup(state, original)

    assert summary.degraded_route_count == 1
    assert summary.route_health_alert_count == 1
    assert summary.pending_route_health_alert_count == 1

    invalid_route = tmp_path / "invalid-route.db"
    invalid_route.write_bytes(original.read_bytes())
    invalid_route.chmod(0o600)
    with sqlite3.connect(invalid_route) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute(
            """
            UPDATE dead_man_notification_routes
            SET status = 'healthy', consecutive_failures = 0, last_acknowledged_at = NULL
            WHERE route_slot = 2
            """
        )
    with pytest.raises(DeadManReceiverRecoveryError, match="route checkpoint"):
        verify_dead_man_receiver_backup(invalid_route)

    invalid_alert = tmp_path / "invalid-alert.db"
    invalid_alert.write_bytes(original.read_bytes())
    invalid_alert.chmod(0o600)
    with sqlite3.connect(invalid_alert) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute(
            "UPDATE dead_man_route_health_outbox SET triggering_event_id = 'other-event'"
        )
    with pytest.raises(DeadManReceiverRecoveryError, match="payload metadata"):
        verify_dead_man_receiver_backup(invalid_alert)

    missed_quorum = tmp_path / "missed-quorum.db"
    missed_quorum.write_bytes(original.read_bytes())
    missed_quorum.chmod(0o600)
    with sqlite3.connect(missed_quorum) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("UPDATE dead_man_notification_outbox SET acknowledged_route_mask = 0")
    with pytest.raises(DeadManReceiverRecoveryError, match="missed frozen quorum"):
        verify_dead_man_receiver_backup(missed_quorum)


def test_recovery_verifies_pending_silent_probe_and_probe_health_transition(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 12, tzinfo=UTC)
    state = tmp_path / "dead-man.db"
    store = SQLiteDeadManReceiverStore(state)
    store.configure_notification_policy(
        configured_routes=2,
        minimum_acknowledgements=1,
        configured_at=now,
    )
    store.configure_notification_probe(
        contract=DeadManNotificationProbeContract.SILENT_ROUTE_PROBE_V1,
        interval_seconds=60,
        failure_threshold=2,
        max_age_seconds=120,
        configured_at=now,
    )
    first = store.ensure_notification_probe_due(now=now)
    assert first is not None
    store.record_notification_probe_attempt(
        first.event_id,
        acknowledged_routes=(True, False),
        transport_succeeded=True,
        attempted_at=now,
    )
    second = store.ensure_notification_probe_due(now=now + timedelta(seconds=60))
    assert second is not None
    store.record_notification_probe_attempt(
        second.event_id,
        acknowledged_routes=(True, False),
        transport_succeeded=True,
        attempted_at=now + timedelta(seconds=60),
    )
    pending = store.ensure_notification_probe_due(now=now + timedelta(seconds=120))
    assert pending is not None
    original = tmp_path / "backup.db"
    summary = create_dead_man_receiver_backup(state, original)

    assert summary.notification_probe_enabled
    assert summary.notification_probe_pending
    assert summary.degraded_route_count == 1
    assert summary.route_health_alert_count == 1

    invalid = tmp_path / "invalid-probe.db"
    invalid.write_bytes(original.read_bytes())
    invalid.chmod(0o600)
    with sqlite3.connect(invalid) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute(
            "UPDATE dead_man_notification_probe "
            "SET probe_id = 'rp-00000000000000000000000000000000'"
        )
    with pytest.raises(DeadManReceiverRecoveryError, match="probe checkpoint"):
        verify_dead_man_receiver_backup(invalid)


def test_recovery_accepts_delivered_event_after_persisted_retry(tmp_path: Path) -> None:
    now = datetime(2026, 7, 22, 12, tzinfo=UTC)
    state = tmp_path / "dead-man.db"
    store = SQLiteDeadManReceiverStore(state)
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    event = store.evaluate(now=now + timedelta(seconds=180))[0]

    assert not store.record_notification_attempt(
        event.event_id,
        acknowledged_routes=(False,),
        transport_succeeded=False,
        attempted_at=now + timedelta(seconds=180),
    )
    assert store.record_notification_attempt(
        event.event_id,
        acknowledged_routes=(True,),
        transport_succeeded=True,
        attempted_at=now + timedelta(seconds=240),
    )
    summary = create_dead_man_receiver_backup(state, tmp_path / "backup.db")

    assert summary.pending_event_count == 0
    assert summary.degraded_route_count == 0


def test_verify_rejects_corruption_schema_drift_executable_objects_and_semantic_drift(
    tmp_path: Path,
) -> None:
    state = tmp_path / "dead-man.db"
    _seed_receiver(state)
    original = tmp_path / "backup.db"
    create_dead_man_receiver_backup(state, original)

    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not sqlite")
    corrupt.chmod(0o600)
    with pytest.raises(DeadManReceiverRecoveryError, match="integrity"):
        verify_dead_man_receiver_backup(corrupt)

    wrong_version = tmp_path / "wrong-version.db"
    wrong_version.write_bytes(original.read_bytes())
    wrong_version.chmod(0o600)
    with sqlite3.connect(wrong_version) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA user_version = 0")
    with pytest.raises(DeadManReceiverRecoveryError, match="schema"):
        verify_dead_man_receiver_backup(wrong_version)

    executable = tmp_path / "executable.db"
    executable.write_bytes(original.read_bytes())
    executable.chmod(0o600)
    with sqlite3.connect(executable) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute(
            "CREATE TRIGGER forbidden AFTER UPDATE ON dead_man_monitors BEGIN SELECT 1; END"
        )
    with pytest.raises(DeadManReceiverRecoveryError, match="executable"):
        verify_dead_man_receiver_backup(executable)

    mismatched = tmp_path / "mismatched.db"
    mismatched.write_bytes(original.read_bytes())
    mismatched.chmod(0o600)
    with sqlite3.connect(mismatched) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("UPDATE dead_man_notification_outbox SET runtime_id = 'other-runtime'")
    with pytest.raises(DeadManReceiverRecoveryError, match="metadata mismatch"):
        verify_dead_man_receiver_backup(mismatched)

    invalid_delivery = tmp_path / "invalid-delivery.db"
    invalid_delivery.write_bytes(original.read_bytes())
    invalid_delivery.chmod(0o600)
    with sqlite3.connect(invalid_delivery) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA ignore_check_constraints = ON")
        connection.execute("UPDATE dead_man_notification_outbox SET delivered = 2")
    with pytest.raises(DeadManReceiverRecoveryError, match="delivery checkpoint"):
        verify_dead_man_receiver_backup(invalid_delivery)

    invalid_alert_status = tmp_path / "invalid-alert-status.db"
    invalid_alert_status.write_bytes(original.read_bytes())
    invalid_alert_status.chmod(0o600)
    with sqlite3.connect(invalid_alert_status) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("UPDATE dead_man_monitors SET alert_delivery_status = 'unknown'")
    with pytest.raises(DeadManReceiverRecoveryError, match="alert delivery status"):
        verify_dead_man_receiver_backup(invalid_alert_status)

    missing_policy = tmp_path / "missing-policy.db"
    missing_policy.write_bytes(original.read_bytes())
    missing_policy.chmod(0o600)
    with sqlite3.connect(missing_policy) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("DELETE FROM dead_man_notification_policy")
    with pytest.raises(DeadManReceiverRecoveryError, match="notification policy"):
        verify_dead_man_receiver_backup(missing_policy)

    pending_policy_drift = tmp_path / "pending-policy-drift.db"
    pending_policy_drift.write_bytes(original.read_bytes())
    pending_policy_drift.chmod(0o600)
    with sqlite3.connect(pending_policy_drift) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("UPDATE dead_man_notification_policy SET configured_routes = 2")
    with pytest.raises(DeadManReceiverRecoveryError, match="policy drifted"):
        verify_dead_man_receiver_backup(pending_policy_drift)

    partial_pulse = tmp_path / "partial-pulse.db"
    partial_pulse.write_bytes(original.read_bytes())
    partial_pulse.chmod(0o600)
    with sqlite3.connect(partial_pulse) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("UPDATE dead_man_monitors SET last_pulse_received_at = updated_at")
    with pytest.raises(DeadManReceiverRecoveryError, match="ordered pulse receipt"):
        verify_dead_man_receiver_backup(partial_pulse)

    reason_drift = tmp_path / "reason-drift.db"
    reason_drift.write_bytes(original.read_bytes())
    reason_drift.chmod(0o600)
    with sqlite3.connect(reason_drift) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute(
            "UPDATE dead_man_monitors SET outage_reason = 'alert_delivery_unhealthy'"
        )
    with pytest.raises(DeadManReceiverRecoveryError, match="disagree"):
        verify_dead_man_receiver_backup(reason_drift)

    broad = tmp_path / "broad.db"
    broad.write_bytes(original.read_bytes())
    broad.chmod(0o644)
    with pytest.raises(DeadManReceiverRecoveryError, match="owner-only"):
        verify_dead_man_receiver_backup(broad)

    linked = tmp_path / "linked.db"
    linked.symlink_to(original)
    with pytest.raises(DeadManReceiverRecoveryError, match="symlink"):
        verify_dead_man_receiver_backup(linked)

    future = tmp_path / "future.db"
    future.write_bytes(original.read_bytes())
    future.chmod(0o600)
    with sqlite3.connect(future) as connection:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA user_version = 6")
    with pytest.raises(DeadManReceiverSchemaError, match="not supported"):
        SQLiteDeadManReceiverStore(future)


def test_restore_round_trip_preserves_current_valid_state_and_removes_sidecars(
    tmp_path: Path,
) -> None:
    state = tmp_path / "dead-man.db"
    store, now = _seed_receiver(state)
    backup_path = tmp_path / "backup.db"
    backup = create_dead_man_receiver_backup(state, backup_path)
    assert store.record_notification_attempt(
        "private-event-open",
        acknowledged_routes=(True,),
        transport_succeeded=True,
        attempted_at=now + timedelta(seconds=182),
    )

    restored = restore_dead_man_receiver_backup(
        state,
        backup_path,
        expected_sha256=backup.sha256,
        clock=lambda: datetime(2026, 7, 22, 15, tzinfo=UTC),
    )

    assert restored.preservation == "verified_safety_backup"
    assert restored.restored_artifact_sha256 == backup.sha256
    assert restored.preservation_name == "dead-man.db.pre-restore-20260722T150000Z.db"
    safety = tmp_path / restored.preservation_name
    assert verify_dead_man_receiver_backup(state).pending_event_count == 1
    assert verify_dead_man_receiver_backup(safety).pending_event_count == 0
    assert not Path(f"{state}-wal").exists()
    assert not Path(f"{state}-shm").exists()
    assert SQLiteDeadManReceiverStore(state).pending_count() == 1


def test_restore_rejects_wrong_hash_and_active_worker_without_mutation(
    tmp_path: Path,
) -> None:
    state = tmp_path / "dead-man.db"
    _seed_receiver(state)
    backup_path = tmp_path / "backup.db"
    backup = create_dead_man_receiver_backup(state, backup_path)
    before = state.read_bytes()

    with pytest.raises(DeadManReceiverRecoveryError, match="SHA-256"):
        restore_dead_man_receiver_backup(state, backup_path, expected_sha256="0" * 64)
    assert state.read_bytes() == before

    owner = RuntimeOwnerLock(runtime_owner_lock_path(state, base_dir=tmp_path), resource_path=state)
    owner.acquire()
    try:
        with pytest.raises(DeadManReceiverRecoveryError, match="active"):
            restore_dead_man_receiver_backup(state, backup_path, expected_sha256=backup.sha256)
    finally:
        owner.release()
    assert state.read_bytes() == before


def test_restore_quarantines_corrupt_live_bytes_and_interruption_keeps_valid_live(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.db"
    _seed_receiver(source)
    backup_path = tmp_path / "backup.db"
    backup = create_dead_man_receiver_backup(source, backup_path)
    target = tmp_path / "target.db"
    target.write_bytes(b"private corrupt live bytes")
    Path(f"{target}-wal").write_bytes(b"private corrupt wal")

    restored = restore_dead_man_receiver_backup(
        target,
        backup_path,
        expected_sha256=backup.sha256,
        clock=lambda: datetime(2026, 7, 22, 16, tzinfo=UTC),
    )

    assert restored.preservation == "unverified_quarantine"
    assert restored.preservation_name is not None
    quarantine = tmp_path / restored.preservation_name
    assert (quarantine / "target.db").read_bytes() == b"private corrupt live bytes"
    assert (quarantine / "target.db-wal").read_bytes() == b"private corrupt wal"
    assert verify_dead_man_receiver_backup(target).sha256

    live_before = target.read_bytes()

    def fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("synthetic interrupted replace")

    monkeypatch.setattr(
        "aico.app.dead_man_receiver_recovery.os.replace",
        fail_replace,
    )
    with pytest.raises(DeadManReceiverRecoveryError, match="restore failed"):
        restore_dead_man_receiver_backup(
            target,
            backup_path,
            expected_sha256=backup.sha256,
            clock=lambda: datetime(2026, 7, 22, 17, tzinfo=UTC),
        )
    assert target.read_bytes() == live_before
    assert verify_dead_man_receiver_backup(target).sha256


def test_disposable_drill_is_private_cleans_workspace_and_cli_requires_confirmation(
    tmp_path: Path,
) -> None:
    state = tmp_path / "private" / "dead-man.db"
    _seed_receiver(state)
    backup_path = tmp_path / "backup.db"
    backup = create_dead_man_receiver_backup(state, backup_path)
    workspace = tmp_path / "workspace"
    report = tmp_path / "evidence" / "drill.json"
    workspace.mkdir()

    summary = drill_dead_man_receiver_backup(
        backup_path,
        expected_sha256=backup.sha256,
        workspace=workspace,
        report_path=report,
        clock=lambda: datetime(2026, 7, 22, 18, tzinfo=UTC),
    )

    assert summary.operation == "drill"
    assert summary.pending_event_count == 1
    assert tuple(workspace.iterdir()) == ()
    assert stat.S_IMODE(report.stat().st_mode) == 0o600
    rendered = report.read_text()
    assert json.loads(rendered) == summary.model_dump(mode="json")
    assert "private-runtime" not in rendered
    assert str(state) not in rendered

    output = io.StringIO()
    assert (
        run(
            [
                "restore",
                "--db",
                str(state),
                "--from",
                str(backup_path),
                "--expected-sha256",
                backup.sha256,
            ],
            stdout=output,
        )
        == 2
    )
    assert "without --yes" in output.getvalue()


def test_receiver_lifespan_holds_same_kernel_fence_used_by_restore(tmp_path: Path) -> None:
    settings = DeadManReceiverSettings.model_validate(
        {
            "state_db_path": tmp_path / "dead-man.db",
            "pulse_bearer_token": "p" * 32,
            "admin_bearer_token": "a" * 32,
            "notification_webhook_url": "https://notify.example.test/hook",
        }
    )
    first = build_dead_man_receiver_app(settings, notification_sink=_RecordingSink())
    second = build_dead_man_receiver_app(settings, notification_sink=_RecordingSink())

    with TestClient(first) as client:
        assert client.get("/readyz").status_code == 200
        with pytest.raises(RuntimeError, match="owner is already active"):
            with TestClient(second):
                pass


def _seed_receiver(path: Path) -> tuple[SQLiteDeadManReceiverStore, datetime]:
    now = datetime(2026, 7, 22, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(
        path,
        outage_id_factory=lambda: "private-outage",
        event_id_factory=lambda: "private-event-open",
    )
    store.arm("private-runtime", expires_after_seconds=180, armed_at=now)
    store.evaluate(now=now + timedelta(seconds=181))
    return store, now
