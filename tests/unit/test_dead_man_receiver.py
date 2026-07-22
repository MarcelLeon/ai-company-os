from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from aico.app.dead_man_receiver import (
    DeadManEvent,
    DeadManEventType,
    DeadManMonitorConflictError,
    DeadManMonitorNotArmedError,
    DeadManNotificationAttemptResult,
    DeadManNotificationCoordinator,
    DeadManNotificationPolicyConflictError,
    DeadManNotificationProbeContract,
    DeadManNotificationProbeEvent,
    DeadManNotificationQuorumError,
    DeadManNotificationRouteStatus,
    DeadManOutageReason,
    DeadManOutboundEvent,
    DeadManPulseReason,
    DeadManRouteHealthEvent,
    DeadManRouteHealthEventType,
    DeadManRouteObservationSource,
    QuorumDeadManNotificationSink,
    SQLiteDeadManReceiverStore,
    WebhookDeadManNotificationSink,
)
from aico.app.runtime_liveness import (
    RuntimeAlertDeliverySignal,
    RuntimeLivenessPulse,
    RuntimeLivenessReceiverStatus,
)


class RecordingSink:
    def __init__(self, *, fail: bool = False, accept_then_fail: bool = False) -> None:
        self.fail = fail
        self.accept_then_fail = accept_then_fail
        self.events: list[DeadManOutboundEvent] = []
        self.attempts = 0

    async def send(self, event: DeadManOutboundEvent) -> None:
        self.attempts += 1
        if self.fail and not self.accept_then_fail:
            raise RuntimeError("private notification failure")
        self.events.append(event)
        if self.accept_then_fail:
            raise RuntimeError("accepted before local ack")


def test_monitor_and_missing_first_pulse_outage_survive_store_restart(tmp_path: Path) -> None:
    path = tmp_path / "receiver.db"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(
        path,
        outage_id_factory=lambda: "outage-1",
        event_id_factory=lambda: "event-open",
    )
    armed = store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)

    rebuilt = SQLiteDeadManReceiverStore(
        path,
        outage_id_factory=lambda: "outage-1",
        event_id_factory=lambda: "event-open",
    )
    opened = rebuilt.evaluate(now=now + timedelta(seconds=180))
    repeated = SQLiteDeadManReceiverStore(path).evaluate(now=now + timedelta(seconds=240))
    snapshot = rebuilt.get_monitor("owner-runtime")

    assert armed.status is RuntimeLivenessReceiverStatus.HEALTHY
    assert snapshot.status is RuntimeLivenessReceiverStatus.STALE
    assert snapshot.outage_id == "outage-1"
    assert [event.event_type for event in opened] == [DeadManEventType.OUTAGE_OPENED]
    assert repeated == ()
    assert rebuilt.pending_count() == 1


def test_schema_v1_monitor_migrates_with_conservative_delivery_defaults(
    tmp_path: Path,
) -> None:
    path = tmp_path / "receiver-v1.db"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE dead_man_monitors (
                runtime_id TEXT PRIMARY KEY,
                expires_after_seconds INTEGER NOT NULL,
                armed_at TEXT NOT NULL,
                boot_id TEXT,
                sequence INTEGER,
                sent_at TEXT,
                last_received_at TEXT,
                outage_id TEXT UNIQUE,
                outage_opened_at TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO dead_man_monitors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "owner-runtime",
                180,
                now.isoformat(),
                "boot-1",
                1,
                now.isoformat(),
                now.isoformat(),
                "outage-1",
                (now + timedelta(seconds=180)).isoformat(),
                (now + timedelta(seconds=180)).isoformat(),
            ),
        )
        connection.execute("PRAGMA user_version = 1")

    snapshot = SQLiteDeadManReceiverStore(path).get_monitor("owner-runtime")
    with sqlite3.connect(path) as connection:
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert schema_version == 5
    assert snapshot.last_pulse_received_at == now
    assert snapshot.alert_delivery_status is RuntimeAlertDeliverySignal.DISABLED
    assert snapshot.outage_reason is DeadManOutageReason.PULSE_EXPIRED


def test_schema_v2_migrates_default_notification_policy(tmp_path: Path) -> None:
    path = tmp_path / "receiver-v2.db"
    SQLiteDeadManReceiverStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE dead_man_notification_outbox")
        connection.execute(
            """
            CREATE TABLE dead_man_notification_outbox (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                outage_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                runtime_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                delivered INTEGER NOT NULL DEFAULT 0 CHECK (delivered IN (0, 1)),
                delivery_attempts INTEGER NOT NULL DEFAULT 0 CHECK (delivery_attempts >= 0),
                next_attempt_at TEXT,
                UNIQUE (outage_id, event_type)
            )
            """
        )
        connection.execute("DROP TABLE dead_man_notification_policy")
        connection.execute("PRAGMA user_version = 2")

    policy = SQLiteDeadManReceiverStore(path).get_notification_policy()
    with sqlite3.connect(path) as connection:
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(dead_man_notification_outbox)")
        }

    assert schema_version == 5
    assert policy.configured_routes == 1
    assert policy.minimum_acknowledgements == 1
    assert {"configured_routes", "minimum_acknowledgements"} <= columns


def test_schema_v3_migrates_unknown_route_health_and_attempt_checkpoint(tmp_path: Path) -> None:
    path = tmp_path / "receiver-v3.db"
    SQLiteDeadManReceiverStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE dead_man_notification_routes")
        connection.execute("DROP TABLE dead_man_route_health_outbox")
        connection.execute("DROP TABLE dead_man_notification_outbox")
        connection.execute(
            """
            CREATE TABLE dead_man_notification_outbox (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                outage_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                runtime_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                delivered INTEGER NOT NULL DEFAULT 0 CHECK (delivered IN (0, 1)),
                delivery_attempts INTEGER NOT NULL DEFAULT 0 CHECK (delivery_attempts >= 0),
                next_attempt_at TEXT,
                configured_routes INTEGER NOT NULL DEFAULT 1
                    CHECK (configured_routes BETWEEN 1 AND 2),
                minimum_acknowledgements INTEGER NOT NULL DEFAULT 1
                    CHECK (minimum_acknowledgements BETWEEN 1 AND configured_routes),
                UNIQUE (outage_id, event_type)
            )
            """
        )
        connection.execute("PRAGMA user_version = 3")

    store = SQLiteDeadManReceiverStore(path)
    with sqlite3.connect(path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(dead_man_notification_outbox)")
        }

    assert version == 5
    assert {"acknowledged_route_mask", "last_attempt_at"} <= columns
    assert [route.status for route in store.list_notification_routes()] == [
        DeadManNotificationRouteStatus.UNKNOWN
    ]


def test_schema_v4_migrates_disabled_probe_and_route_probe_checkpoints(tmp_path: Path) -> None:
    path = tmp_path / "receiver-v4.db"
    SQLiteDeadManReceiverStore(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE dead_man_notification_probe")
        connection.execute("DROP TABLE dead_man_route_health_outbox")
        connection.execute("DROP TABLE dead_man_notification_routes")
        connection.execute(
            """
            CREATE TABLE dead_man_notification_routes (
                route_slot INTEGER PRIMARY KEY CHECK (route_slot BETWEEN 1 AND 2),
                status TEXT NOT NULL CHECK (status IN ('unknown', 'healthy', 'degraded')),
                consecutive_failures INTEGER NOT NULL DEFAULT 0
                    CHECK (consecutive_failures >= 0),
                last_attempt_at TEXT,
                last_acknowledged_at TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE dead_man_route_health_outbox (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                route_slot INTEGER NOT NULL CHECK (route_slot BETWEEN 1 AND 2),
                event_type TEXT NOT NULL CHECK (
                    event_type IN ('notification_route_degraded', 'notification_route_recovered')
                ),
                triggering_event_id TEXT NOT NULL,
                runtime_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                delivered INTEGER NOT NULL DEFAULT 0 CHECK (delivered IN (0, 1)),
                delivery_attempts INTEGER NOT NULL DEFAULT 0 CHECK (delivery_attempts >= 0),
                next_attempt_at TEXT,
                UNIQUE (route_slot, event_type, triggering_event_id)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO dead_man_notification_routes (route_slot, status, updated_at)
            VALUES (1, 'unknown', '1970-01-01T00:00:00+00:00')
            """
        )
        connection.execute("PRAGMA user_version = 4")

    rebuilt = SQLiteDeadManReceiverStore(path)
    fresh_path = tmp_path / "receiver-v5.db"
    SQLiteDeadManReceiverStore(fresh_path)
    with sqlite3.connect(path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(dead_man_notification_routes)")
        }
        alert_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(dead_man_route_health_outbox)")
        }
        migrated_sql = {
            row[0]: " ".join(str(row[1]).split()).lower()
            for row in connection.execute(
                """
                SELECT name, sql FROM sqlite_master
                WHERE name IN ('dead_man_notification_routes', 'dead_man_route_health_outbox')
                """
            )
        }
    with sqlite3.connect(fresh_path) as connection:
        fresh_sql = {
            row[0]: " ".join(str(row[1]).split()).lower()
            for row in connection.execute(
                """
                SELECT name, sql FROM sqlite_master
                WHERE name IN ('dead_man_notification_routes', 'dead_man_route_health_outbox')
                """
            )
        }

    assert version == 5
    assert rebuilt.get_notification_probe().contract is DeadManNotificationProbeContract.DISABLED
    assert {
        "consecutive_probe_failures",
        "last_probe_at",
        "last_probe_acknowledged_at",
    } <= columns
    assert "observation_source" in alert_columns
    assert migrated_sql == fresh_sql


def test_pending_delivery_fences_quorum_policy_across_restart(tmp_path: Path) -> None:
    path = tmp_path / "receiver.db"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(path)
    configured = store.configure_notification_policy(
        configured_routes=2,
        minimum_acknowledgements=2,
        configured_at=now,
    )
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    store.evaluate(now=now + timedelta(seconds=180))

    rebuilt = SQLiteDeadManReceiverStore(path)
    with pytest.raises(DeadManNotificationPolicyConflictError, match="pending"):
        rebuilt.configure_notification_policy(
            configured_routes=2,
            minimum_acknowledgements=1,
            configured_at=now + timedelta(seconds=181),
        )

    assert rebuilt.get_notification_policy() == configured
    pending_event = rebuilt.list_events()[0]
    assert rebuilt.record_notification_attempt(
        pending_event.event_id,
        acknowledged_routes=(True, True),
        transport_succeeded=True,
        attempted_at=now + timedelta(seconds=181),
    )
    changed = rebuilt.configure_notification_policy(
        configured_routes=2,
        minimum_acknowledgements=1,
        configured_at=now + timedelta(seconds=181),
    )
    evidence = rebuilt.export_evidence(
        "owner-runtime",
        generated_at=now + timedelta(seconds=182),
        max_outages=1,
    )
    assert changed.minimum_acknowledgements == 1
    assert evidence.notification_policy.minimum_acknowledgements == 1
    assert evidence.outages[0].opened.minimum_acknowledgements == 2


def test_pending_route_health_alert_fences_policy_change(tmp_path: Path) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(tmp_path / "receiver.db")
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
    assert store.pending_count() == 0
    assert store.pending_route_health_alert_count() == 1
    with pytest.raises(DeadManNotificationPolicyConflictError, match="pending"):
        store.configure_notification_policy(
            configured_routes=2,
            minimum_acknowledgements=2,
            configured_at=now + timedelta(seconds=181),
        )


def test_outage_and_open_event_roll_back_together_when_outbox_insert_fails(
    tmp_path: Path,
) -> None:
    path = tmp_path / "receiver.db"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(path)
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_dead_man_event
            BEFORE INSERT ON dead_man_notification_outbox
            BEGIN
                SELECT RAISE(ABORT, 'reject event');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="reject event"):
        store.evaluate(now=now + timedelta(seconds=180))

    snapshot = store.get_monitor("owner-runtime")
    assert snapshot.status is RuntimeLivenessReceiverStatus.HEALTHY
    assert snapshot.outage_id is None
    assert store.pending_count() == 0


def test_receiver_expiry_uses_acceptance_time_not_sender_time(tmp_path: Path) -> None:
    path = tmp_path / "receiver.db"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(path)
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    pulse = _pulse(sent_at=now - timedelta(days=30))

    receipt = store.accept(pulse, received_at=now + timedelta(seconds=10))
    rebuilt = SQLiteDeadManReceiverStore(path)
    fresh = rebuilt.evaluate(now=now + timedelta(seconds=189))
    stale = rebuilt.evaluate(now=now + timedelta(seconds=190))

    assert receipt.accepted is True
    assert receipt.reason is DeadManPulseReason.ACCEPTED
    assert fresh == ()
    assert len(stale) == 1
    assert rebuilt.get_monitor("owner-runtime").expires_at == now + timedelta(seconds=190)


def test_duplicate_and_out_of_order_pulses_do_not_extend_receiver_ttl(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(tmp_path / "receiver.db")
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    first = _pulse(sequence=2, sent_at=now)
    store.accept(first, received_at=now + timedelta(seconds=10))

    duplicate = store.accept(first, received_at=now + timedelta(seconds=100))
    older = store.accept(
        _pulse(sequence=1, sent_at=now + timedelta(seconds=1)),
        received_at=now + timedelta(seconds=110),
    )
    opened = store.evaluate(now=now + timedelta(seconds=190))

    assert duplicate.accepted is False
    assert duplicate.reason is DeadManPulseReason.DUPLICATE_OR_OLDER
    assert older.accepted is False
    assert len(opened) == 1


def test_alert_delivery_failure_opens_and_recovers_durable_receiver_outage(
    tmp_path: Path,
) -> None:
    path = tmp_path / "receiver.db"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    event_ids = iter(("event-open", "event-resolved"))
    store = SQLiteDeadManReceiverStore(
        path,
        outage_id_factory=lambda: "outage-1",
        event_id_factory=lambda: next(event_ids),
    )
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    store.accept(_pulse(), received_at=now)

    pending = store.accept(
        _pulse(
            sequence=2,
            sent_at=now + timedelta(seconds=60),
            alert_delivery_status=RuntimeAlertDeliverySignal.PENDING,
        ),
        received_at=now + timedelta(seconds=60),
    )
    rebuilt = SQLiteDeadManReceiverStore(
        path,
        outage_id_factory=lambda: "outage-1",
        event_id_factory=lambda: next(event_ids),
    )
    failed = rebuilt.accept(
        _pulse(
            sequence=3,
            sent_at=now + timedelta(seconds=180),
            alert_delivery_status=RuntimeAlertDeliverySignal.FAILED,
        ),
        received_at=now + timedelta(seconds=180),
    )
    opened = rebuilt.get_monitor("owner-runtime")
    recovered = rebuilt.accept(
        _pulse(
            sequence=4,
            sent_at=now + timedelta(seconds=181),
            alert_delivery_status=RuntimeAlertDeliverySignal.HEALTHY,
        ),
        received_at=now + timedelta(seconds=181),
    )
    events = rebuilt.list_events("owner-runtime")

    assert pending.reason is DeadManPulseReason.ACCEPTED_WITHOUT_RENEWAL
    assert pending.renewed is False
    assert failed.status is RuntimeLivenessReceiverStatus.STALE
    assert opened.last_received_at == now
    assert opened.last_pulse_received_at == now + timedelta(seconds=180)
    assert opened.alert_delivery_status is RuntimeAlertDeliverySignal.FAILED
    assert opened.outage_reason is DeadManOutageReason.ALERT_DELIVERY_UNHEALTHY
    assert recovered.renewed is True
    assert recovered.outage_resolved is True
    assert [event.reason for event in events] == [
        DeadManOutageReason.ALERT_DELIVERY_UNHEALTHY,
        DeadManOutageReason.ALERT_DELIVERY_UNHEALTHY,
    ]


def test_late_recovery_atomically_records_open_then_resolved_before_sweep(
    tmp_path: Path,
) -> None:
    path = tmp_path / "receiver.db"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    ids = iter(("event-open", "event-resolved"))
    store = SQLiteDeadManReceiverStore(
        path,
        outage_id_factory=lambda: "outage-1",
        event_id_factory=lambda: next(ids),
    )
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)

    receipt = store.accept(
        _pulse(sent_at=now + timedelta(seconds=181)),
        received_at=now + timedelta(seconds=181),
    )
    events = store.list_events("owner-runtime")

    assert receipt.accepted is True
    assert receipt.outage_resolved is True
    assert [(event.event_id, event.event_type) for event in events] == [
        ("event-open", DeadManEventType.OUTAGE_OPENED),
        ("event-resolved", DeadManEventType.OUTAGE_RESOLVED),
    ]
    assert events[0].outage_id == events[1].outage_id == "outage-1"
    assert events[0].occurred_at == now + timedelta(seconds=180)
    assert store.get_monitor("owner-runtime").status is RuntimeLivenessReceiverStatus.HEALTHY


def test_recovery_and_resolved_event_roll_back_together_when_event_insert_fails(
    tmp_path: Path,
) -> None:
    path = tmp_path / "receiver.db"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(path)
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    store.evaluate(now=now + timedelta(seconds=180))
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_dead_man_resolved
            BEFORE INSERT ON dead_man_notification_outbox
            WHEN NEW.event_type = 'outage_resolved'
            BEGIN
                SELECT RAISE(ABORT, 'reject resolved');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="reject resolved"):
        store.accept(
            _pulse(sent_at=now + timedelta(seconds=181)),
            received_at=now + timedelta(seconds=181),
        )

    snapshot = store.get_monitor("owner-runtime")
    assert snapshot.status is RuntimeLivenessReceiverStatus.STALE
    assert snapshot.last_received_at is None
    assert [event.event_type for event in store.list_events()] == [DeadManEventType.OUTAGE_OPENED]


def test_arm_is_idempotent_without_reset_and_ttl_change_requires_disarm(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(tmp_path / "receiver.db")
    first = store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    repeated = store.arm(
        "owner-runtime",
        expires_after_seconds=180,
        armed_at=now + timedelta(seconds=100),
    )

    with pytest.raises(DeadManMonitorConflictError):
        store.arm("owner-runtime", expires_after_seconds=300, armed_at=now)
    with pytest.raises(DeadManMonitorConflictError):
        store.accept(
            _pulse(expires_after_seconds=300),
            received_at=now + timedelta(seconds=1),
        )

    assert first.armed_at == repeated.armed_at == now
    assert len(store.evaluate(now=now + timedelta(seconds=180))) == 1


def test_disarm_persists_without_deleting_prior_notification_intent(
    tmp_path: Path,
) -> None:
    path = tmp_path / "receiver.db"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(path)
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    store.evaluate(now=now + timedelta(seconds=180))

    assert store.disarm("owner-runtime") is True
    rebuilt = SQLiteDeadManReceiverStore(path)

    with pytest.raises(DeadManMonitorNotArmedError):
        rebuilt.get_monitor("owner-runtime")
    with pytest.raises(DeadManMonitorNotArmedError):
        rebuilt.accept(_pulse(), received_at=now + timedelta(hours=1))
    assert rebuilt.evaluate(now=now + timedelta(hours=1)) == ()
    assert rebuilt.pending_count() == 1


async def test_notification_retry_persists_exact_events_and_open_precedes_resolved(
    tmp_path: Path,
) -> None:
    path = tmp_path / "receiver.db"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    ids = iter(("event-open", "event-resolved"))
    store = SQLiteDeadManReceiverStore(
        path,
        outage_id_factory=lambda: "outage-1",
        event_id_factory=lambda: next(ids),
    )
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    store.accept(
        _pulse(sent_at=now + timedelta(seconds=181)),
        received_at=now + timedelta(seconds=181),
    )
    failing = RecordingSink(accept_then_fail=True)
    first = DeadManNotificationCoordinator(store=store, sink=failing)

    await first.check(now=now + timedelta(seconds=181))
    await first.check(now=now + timedelta(seconds=240))
    rebuilt_sink = RecordingSink()
    rebuilt = DeadManNotificationCoordinator(
        store=SQLiteDeadManReceiverStore(path),
        sink=rebuilt_sink,
    )
    await rebuilt.check(now=now + timedelta(seconds=241))

    assert [event.event_id for event in failing.events] == ["event-open"]
    assert [event.event_id for event in rebuilt_sink.events] == [
        "event-open",
        "event-resolved",
    ]
    assert store.pending_count() == 0


async def test_notification_failure_uses_persisted_one_five_fifteen_minute_backoff(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(tmp_path / "receiver.db")
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    sink = RecordingSink(fail=True)
    coordinator = DeadManNotificationCoordinator(store=store, sink=sink)

    await coordinator.check(now=now + timedelta(seconds=180))
    await coordinator.check(now=now + timedelta(seconds=239))
    await coordinator.check(now=now + timedelta(seconds=240))
    await coordinator.check(now=now + timedelta(seconds=539))
    await coordinator.check(now=now + timedelta(seconds=540))
    await coordinator.check(now=now + timedelta(seconds=1439))
    await coordinator.check(now=now + timedelta(seconds=1440))

    assert sink.attempts == 4
    assert store.pending_count() == 1


async def test_notification_quorum_uses_fallback_and_retries_only_when_quorum_missed(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    available = RecordingSink()
    unavailable = RecordingSink(fail=True)
    failover_store = SQLiteDeadManReceiverStore(tmp_path / "failover.db")
    failover_store.configure_notification_policy(
        configured_routes=2,
        minimum_acknowledgements=1,
        configured_at=now,
    )
    failover_store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    failover = DeadManNotificationCoordinator(
        store=failover_store,
        sink=QuorumDeadManNotificationSink(
            sinks=(unavailable, available),
            minimum_acknowledgements=1,
        ),
    )

    delivered = await failover.check(now=now + timedelta(seconds=180))

    assert delivered.pending_events == 0
    assert unavailable.attempts == available.attempts == 2
    assert [event.event_id for event in available.events]

    strict_store = SQLiteDeadManReceiverStore(tmp_path / "strict.db")
    strict_store.configure_notification_policy(
        configured_routes=2,
        minimum_acknowledgements=2,
        configured_at=now,
    )
    strict_store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    strict_available = RecordingSink()
    strict_unavailable = RecordingSink(fail=True)
    strict = DeadManNotificationCoordinator(
        store=strict_store,
        sink=QuorumDeadManNotificationSink(
            sinks=(strict_unavailable, strict_available),
            minimum_acknowledgements=2,
        ),
    )

    pending = await strict.check(now=now + timedelta(seconds=180))

    strict_unavailable.fail = False
    recovered = await strict.check(now=now + timedelta(seconds=240))

    assert pending.pending_events == 1
    assert recovered.pending_events == 0
    assert strict_store.pending_count() == 0
    assert strict_unavailable.attempts == strict_available.attempts == 4
    available_outages = [
        event for event in strict_available.events if isinstance(event, DeadManEvent)
    ]
    recovered_outages = [
        event for event in strict_unavailable.events if isinstance(event, DeadManEvent)
    ]
    assert available_outages[0].event_id == available_outages[1].event_id
    assert recovered_outages[0].event_id == available_outages[0].event_id


def test_notification_quorum_rejects_impossible_or_single_route_contract() -> None:
    sink = RecordingSink()
    with pytest.raises(ValueError, match="at least two"):
        QuorumDeadManNotificationSink(sinks=(sink,), minimum_acknowledgements=1)
    with pytest.raises(ValueError, match="cannot exceed"):
        QuorumDeadManNotificationSink(
            sinks=(sink, RecordingSink()),
            minimum_acknowledgements=3,
        )


async def test_notification_webhook_has_stable_idempotency_and_no_transport_secrets() -> None:
    requests: list[httpx.Request] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202)

    event = DeadManEvent(
        event_id="event-1",
        outage_id="outage-1",
        event_type=DeadManEventType.OUTAGE_OPENED,
        runtime_id="owner-runtime",
        occurred_at=datetime(2026, 7, 21, 12, tzinfo=UTC),
        detected_at=datetime(2026, 7, 21, 12, 3, tzinfo=UTC),
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    sink = WebhookDeadManNotificationSink(
        url="https://notify.example.test/private",
        bearer_token="super-secret-token",
        client=client,
    )
    try:
        await sink.send(event)
        await sink.send(event)
    finally:
        await client.aclose()

    assert [request.headers["Idempotency-Key"] for request in requests] == [
        "event-1",
        "event-1",
    ]
    assert json.loads(requests[0].content) == event.to_payload()
    rendered = json.dumps(event.to_payload())
    assert "notify.example.test" not in rendered
    assert "super-secret-token" not in rendered


async def test_notification_quorum_sends_exact_event_to_distinct_webhooks() -> None:
    requests: list[httpx.Request] = []

    async def primary(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(503)

    async def fallback(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202)

    event = DeadManEvent(
        event_id="event-1",
        outage_id="outage-1",
        event_type=DeadManEventType.OUTAGE_OPENED,
        runtime_id="owner-runtime",
        occurred_at=datetime(2026, 7, 21, 12, tzinfo=UTC),
        detected_at=datetime(2026, 7, 21, 12, 3, tzinfo=UTC),
    )
    primary_client = httpx.AsyncClient(transport=httpx.MockTransport(primary))
    fallback_client = httpx.AsyncClient(transport=httpx.MockTransport(fallback))
    sinks = (
        WebhookDeadManNotificationSink(
            url="https://primary.example.test/hook",
            bearer_token="primary-secret",
            client=primary_client,
        ),
        WebhookDeadManNotificationSink(
            url="https://fallback.example.test/hook",
            bearer_token="fallback-secret",
            client=fallback_client,
        ),
    )
    try:
        result = await QuorumDeadManNotificationSink(
            sinks=sinks,
            minimum_acknowledgements=1,
        ).send(event)
        with pytest.raises(DeadManNotificationQuorumError, match="quorum missed") as error:
            await QuorumDeadManNotificationSink(
                sinks=sinks,
                minimum_acknowledgements=2,
            ).send(event)
    finally:
        await primary_client.aclose()
        await fallback_client.aclose()

    assert len(requests) == 4
    assert {request.url.host for request in requests} == {
        "primary.example.test",
        "fallback.example.test",
    }
    assert all(request.headers["Idempotency-Key"] == "event-1" for request in requests)
    assert all(json.loads(request.content) == event.to_payload() for request in requests)
    assert result == DeadManNotificationAttemptResult(acknowledged_routes=(False, True))
    assert error.value.result == result


async def test_partial_quorum_persists_and_notifies_route_degradation_and_recovery(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    event_ids = iter(("event-open", "event-resolved"))
    store = SQLiteDeadManReceiverStore(
        tmp_path / "receiver.db",
        outage_id_factory=lambda: "outage-1",
        event_id_factory=lambda: next(event_ids),
    )
    store.configure_notification_policy(
        configured_routes=2,
        minimum_acknowledgements=1,
        configured_at=now,
    )
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    primary = RecordingSink()
    fallback = RecordingSink(fail=True)
    coordinator = DeadManNotificationCoordinator(
        store=store,
        sink=QuorumDeadManNotificationSink(
            sinks=(primary, fallback),
            minimum_acknowledgements=1,
        ),
    )

    degraded = await coordinator.check(now=now + timedelta(seconds=180))

    routes = store.list_notification_routes()
    alerts = store.list_route_health_events()
    assert degraded.status.value == "degraded"
    assert degraded.degraded_routes == 1
    assert [route.status for route in routes] == [
        DeadManNotificationRouteStatus.HEALTHY,
        DeadManNotificationRouteStatus.DEGRADED,
    ]
    assert [alert.event_type for alert in alerts] == [DeadManRouteHealthEventType.ROUTE_DEGRADED]
    assert isinstance(primary.events[-1], DeadManRouteHealthEvent)
    assert primary.events[-1].route_slot == 2
    assert store.pending_route_health_alert_count() == 0

    store.accept(
        _pulse(sequence=2, sent_at=now + timedelta(seconds=181)),
        received_at=now + timedelta(seconds=181),
    )
    fallback.fail = False
    recovered = await coordinator.check(now=now + timedelta(seconds=181))
    evidence = store.export_evidence(
        "owner-runtime",
        generated_at=now + timedelta(seconds=182),
        max_outages=1,
    )

    assert recovered.status.value == "healthy"
    assert recovered.degraded_routes == 0
    assert all(
        route.status is DeadManNotificationRouteStatus.HEALTHY
        for route in store.list_notification_routes()
    )
    assert [alert.event_type for alert in store.list_route_health_events()] == [
        DeadManRouteHealthEventType.ROUTE_DEGRADED,
        DeadManRouteHealthEventType.ROUTE_RECOVERED,
    ]
    assert evidence.outages[0].opened.acknowledged_routes == (True, False)
    assert evidence.outages[0].resolved is not None
    assert evidence.outages[0].resolved.acknowledged_routes == (True, True)
    assert [route.status for route in evidence.notification_routes] == [
        DeadManNotificationRouteStatus.HEALTHY,
        DeadManNotificationRouteStatus.HEALTHY,
    ]
    assert [alert.delivered for alert in evidence.route_health_alerts] == [True, True]
    assert "private notification failure" not in evidence.model_dump_json()


async def test_silent_probe_is_durable_confirmed_and_recovers_without_owner_probe_noise(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 12, tzinfo=UTC)
    path = tmp_path / "receiver.db"
    store = SQLiteDeadManReceiverStore(path)
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
    configured_probe = store.get_notification_probe()
    assert configured_probe.is_fresh(at=now + timedelta(seconds=120))
    assert not configured_probe.is_fresh(at=now + timedelta(seconds=121))
    store.arm("owner-runtime", expires_after_seconds=600, armed_at=now)
    pending = store.ensure_notification_probe_due(now=now)
    assert isinstance(pending, DeadManNotificationProbeEvent)
    assert SQLiteDeadManReceiverStore(path).ensure_notification_probe_due(now=now) == pending
    with pytest.raises(DeadManNotificationPolicyConflictError, match="probe is pending"):
        store.configure_notification_probe(
            contract=DeadManNotificationProbeContract.DISABLED,
            interval_seconds=60,
            failure_threshold=2,
            max_age_seconds=120,
            configured_at=now,
        )

    primary = RecordingSink()
    fallback = RecordingSink(fail=True)
    coordinator = DeadManNotificationCoordinator(
        store=store,
        sink=QuorumDeadManNotificationSink(
            sinks=(primary, fallback),
            minimum_acknowledgements=1,
        ),
    )
    first = await coordinator.check(now=now)
    second = await coordinator.check(now=now + timedelta(seconds=60))

    assert first.status.value == "pending"
    assert first.suspect_routes == 1
    assert second.status.value == "degraded"
    assert [route.status for route in store.list_notification_routes()] == [
        DeadManNotificationRouteStatus.HEALTHY,
        DeadManNotificationRouteStatus.DEGRADED,
    ]
    assert [event.event_type for event in primary.events[:2]] == [
        "notification_route_probe",
        "notification_route_probe",
    ]
    assert isinstance(primary.events[-1], DeadManRouteHealthEvent)
    assert primary.events[-1].observation_source is DeadManRouteObservationSource.SILENT_PROBE
    assert primary.events[-1].acknowledged_routes == (True, False)

    fallback.fail = False
    recovered = await coordinator.check(now=now + timedelta(seconds=120))

    assert recovered.status.value == "healthy"
    assert [event.event_type for event in store.list_route_health_events()] == [
        DeadManRouteHealthEventType.ROUTE_DEGRADED,
        DeadManRouteHealthEventType.ROUTE_RECOVERED,
    ]
    assert store.get_notification_probe().last_acknowledged_routes == (True, True)
    assert store.list_notification_routes()[1].consecutive_probe_failures == 0
    evidence = store.export_evidence(
        "owner-runtime",
        generated_at=now + timedelta(seconds=121),
        max_outages=1,
    )
    assert evidence.notification_probe.contract is (
        DeadManNotificationProbeContract.SILENT_ROUTE_PROBE_V1
    )
    assert [alert.observation_source for alert in evidence.route_health_alerts] == [
        DeadManRouteObservationSource.SILENT_PROBE,
        DeadManRouteObservationSource.SILENT_PROBE,
    ]


async def test_all_routes_failed_health_edges_survive_until_one_route_recovers(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(tmp_path / "receiver.db")
    store.configure_notification_policy(
        configured_routes=2,
        minimum_acknowledgements=1,
        configured_at=now,
    )
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    primary = RecordingSink(fail=True)
    fallback = RecordingSink(fail=True)
    coordinator = DeadManNotificationCoordinator(
        store=store,
        sink=QuorumDeadManNotificationSink(
            sinks=(primary, fallback),
            minimum_acknowledgements=1,
        ),
    )

    failed = await coordinator.check(now=now + timedelta(seconds=180))

    assert failed.status.value == "failed"
    assert store.pending_count() == 1
    assert store.pending_route_health_alert_count() == 2
    assert primary.attempts == fallback.attempts == 1

    primary.fail = False
    fallback.fail = False
    recovered = await coordinator.check(now=now + timedelta(seconds=240))

    assert recovered.status.value == "healthy"
    assert recovered.pending_events == 0
    assert recovered.pending_route_health_alerts == 0
    assert [event.event_type for event in store.list_route_health_events()] == [
        DeadManRouteHealthEventType.ROUTE_DEGRADED,
        DeadManRouteHealthEventType.ROUTE_DEGRADED,
        DeadManRouteHealthEventType.ROUTE_RECOVERED,
        DeadManRouteHealthEventType.ROUTE_RECOVERED,
    ]
    assert all(route.status.value == "healthy" for route in store.list_notification_routes())


def _pulse(
    *,
    boot_id: str = "boot-1",
    sequence: int = 1,
    sent_at: datetime | None = None,
    expires_after_seconds: int = 180,
    alert_delivery_status: RuntimeAlertDeliverySignal = RuntimeAlertDeliverySignal.DISABLED,
) -> RuntimeLivenessPulse:
    return RuntimeLivenessPulse(
        runtime_id="owner-runtime",
        boot_id=boot_id,
        sequence=sequence,
        sent_at=sent_at or datetime(2026, 7, 21, 12, tzinfo=UTC),
        interval_seconds=60,
        expires_after_seconds=expires_after_seconds,
        alert_delivery_status=alert_delivery_status,
    )
