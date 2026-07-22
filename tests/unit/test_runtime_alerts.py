from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from aico.app.runtime_alerts import (
    CONFIRMED_HEALTH_FAILURE_CHECKS,
    RuntimeAlertCoordinator,
    RuntimeAlertDeliveryStatus,
    RuntimeAlertEvent,
    RuntimeAlertEventType,
    SQLiteRuntimeAlertStore,
    WebhookRuntimeAlertSink,
)
from aico.app.runtime_health import RuntimeComponentHealth, RuntimeHealthSnapshot
from aico.app.runtime_self_healing import (
    OwnedTaskRecoveryHealth,
    RecoveryStatus,
    RuntimeSelfHealingSnapshot,
)
from aico.core import HealthStatus

COMPONENT = "channel:telegram-polling"
NOW = datetime(2026, 7, 21, 15, tzinfo=UTC)


class RecordingSink:
    def __init__(self, *, failures: int = 0) -> None:
        self.failures = failures
        self.events: list[RuntimeAlertEvent] = []

    async def send(self, event: RuntimeAlertEvent) -> None:
        self.events.append(event)
        if self.failures > 0:
            self.failures -= 1
            raise RuntimeError("secret sink failure")


def test_alert_store_deduplicates_open_and_resolves_same_incident(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    ids = iter(("incident-1", "event-open-1", "event-resolved-1", "incident-2", "event-open-2"))
    store = _store(db_path, ids)

    opened = store.observe(_snapshot(RecoveryStatus.OPEN, attempts=3))
    duplicate = store.observe(_snapshot(RecoveryStatus.OPEN, attempts=3))
    rebuilt = _store(db_path, ids)
    duplicate_after_restart = rebuilt.observe(_snapshot(RecoveryStatus.OPEN, attempts=3))
    recovering = rebuilt.observe(_snapshot(RecoveryStatus.RECOVERING, attempts=1))
    resolved = rebuilt.observe(_snapshot(RecoveryStatus.HEALTHY, attempts=0))
    duplicate_resolved = rebuilt.observe(_snapshot(RecoveryStatus.HEALTHY, attempts=0))
    reopened = rebuilt.observe(_snapshot(RecoveryStatus.OPEN, attempts=3))

    assert [event.event_type for event in opened] == [RuntimeAlertEventType.INCIDENT_OPENED]
    assert duplicate == ()
    assert duplicate_after_restart == ()
    assert recovering == ()
    assert resolved[0].event_type is RuntimeAlertEventType.INCIDENT_RESOLVED
    assert resolved[0].incident_id == opened[0].incident_id == "incident-1"
    assert resolved[0].attempts == 3
    assert duplicate_resolved == ()
    assert reopened[0].incident_id == "incident-2"
    assert len(rebuilt.load_pending(limit=10, now=NOW)) == 3


def test_alert_store_rolls_back_incident_when_outbox_insert_fails(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = _store(db_path, iter(("incident-1", "event-open-1")))
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_runtime_alert_outbox_insert
            BEFORE INSERT ON runtime_alert_outbox
            BEGIN
                SELECT RAISE(ABORT, 'forced runtime alert outbox failure');
            END;
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="forced runtime alert outbox failure"):
        store.observe(_snapshot(RecoveryStatus.OPEN, attempts=3))

    assert store.active_incident_count() == 0
    assert store.pending_count() == 0


def test_health_confirmation_and_outbox_open_commit_atomically(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = _store(
        db_path,
        iter(("incident-failed", "event-failed", "incident-1", "event-open-1")),
    )
    for offset in range(CONFIRMED_HEALTH_FAILURE_CHECKS - 1):
        store.observe(
            _snapshot(RecoveryStatus.HEALTHY, attempts=0),
            _health_snapshot(
                HealthStatus.FAILED,
                checked_at=NOW + timedelta(seconds=offset * 30),
            ),
        )
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_health_runtime_alert_outbox_insert
            BEFORE INSERT ON runtime_alert_outbox
            BEGIN
                SELECT RAISE(ABORT, 'forced health alert outbox failure');
            END;
            """
        )
    third_check = _health_snapshot(
        HealthStatus.FAILED,
        checked_at=NOW + timedelta(seconds=60),
    )

    with pytest.raises(sqlite3.IntegrityError, match="forced health alert outbox failure"):
        store.observe(_snapshot(RecoveryStatus.HEALTHY, attempts=0), third_check)

    assert store.active_incident_count() == 0
    assert store.pending_count() == 0
    with sqlite3.connect(db_path) as connection:
        connection.execute("DROP TRIGGER fail_health_runtime_alert_outbox_insert")
    opened = store.observe(_snapshot(RecoveryStatus.HEALTHY, attempts=0), third_check)
    assert opened[0].incident_id == "incident-1"
    assert store.pending_count() == 1


def test_alert_store_persists_bounded_retry_backoff(tmp_path: Path) -> None:
    store = _store(
        tmp_path / "state.db",
        iter(("incident-1", "event-open-1")),
    )
    event = store.observe(_snapshot(RecoveryStatus.OPEN, attempts=3))[0]

    store.defer(event.event_id, failed_at=NOW)
    assert store.load_pending(limit=1, now=NOW + timedelta(seconds=59)) == ()
    assert store.load_pending(limit=1, now=NOW + timedelta(seconds=60)) == (event,)

    store.defer(event.event_id, failed_at=NOW + timedelta(seconds=60))
    assert store.load_pending(limit=1, now=NOW + timedelta(seconds=359)) == ()
    assert store.load_pending(limit=1, now=NOW + timedelta(seconds=360)) == (event,)

    store.defer(event.event_id, failed_at=NOW + timedelta(seconds=360))
    assert store.load_pending(limit=1, now=NOW + timedelta(seconds=1259)) == ()
    assert store.load_pending(limit=1, now=NOW + timedelta(seconds=1260)) == (event,)


def test_required_health_failure_opens_after_durable_confirmation_and_resolves(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "state.db"
    ids = iter(("incident-1", "event-open-1", "event-resolved-1"))
    store = _store(db_path, ids)

    for offset in range(CONFIRMED_HEALTH_FAILURE_CHECKS - 1):
        created = store.observe(
            _snapshot(RecoveryStatus.HEALTHY, attempts=0),
            _health_snapshot(HealthStatus.FAILED, checked_at=NOW + timedelta(seconds=offset * 30)),
        )
        assert created == ()
    replacement = _store(db_path, ids)
    replayed = replacement.observe(
        _snapshot(RecoveryStatus.HEALTHY, attempts=0),
        _health_snapshot(HealthStatus.FAILED, checked_at=NOW + timedelta(seconds=30)),
    )
    opened = replacement.observe(
        _snapshot(RecoveryStatus.HEALTHY, attempts=0),
        _health_snapshot(HealthStatus.FAILED, checked_at=NOW + timedelta(seconds=60)),
    )
    duplicate = replacement.observe(
        _snapshot(RecoveryStatus.HEALTHY, attempts=0),
        _health_snapshot(HealthStatus.FAILED, checked_at=NOW + timedelta(seconds=90)),
    )
    degraded = replacement.observe(
        _snapshot(RecoveryStatus.HEALTHY, attempts=0),
        _health_snapshot(HealthStatus.DEGRADED, checked_at=NOW + timedelta(seconds=105)),
    )
    resolved = replacement.observe(
        _snapshot(RecoveryStatus.HEALTHY, attempts=0),
        _health_snapshot(HealthStatus.OK, checked_at=NOW + timedelta(seconds=120)),
    )

    assert replayed == ()
    assert opened[0].event_type is RuntimeAlertEventType.INCIDENT_OPENED
    assert opened[0].component == "health:scheduler:morning-push"
    assert opened[0].attempts == CONFIRMED_HEALTH_FAILURE_CHECKS
    assert duplicate == ()
    assert degraded == ()
    assert resolved[0].event_type is RuntimeAlertEventType.INCIDENT_RESOLVED
    assert resolved[0].incident_id == opened[0].incident_id
    assert replacement.health_observation_count() == 0


def test_transient_optional_and_degraded_health_do_not_open_incident(tmp_path: Path) -> None:
    store = _store(tmp_path / "state.db", iter(()))
    healthy_recovery = _snapshot(RecoveryStatus.HEALTHY, attempts=0)

    assert store.observe(healthy_recovery, _health_snapshot(HealthStatus.FAILED)) == ()
    assert store.observe(healthy_recovery, _health_snapshot(HealthStatus.OK)) == ()
    assert store.observe(healthy_recovery, _health_snapshot(HealthStatus.FAILED)) == ()
    assert store.observe(healthy_recovery, _health_snapshot(HealthStatus.DEGRADED)) == ()
    for offset in range(CONFIRMED_HEALTH_FAILURE_CHECKS + 1):
        assert (
            store.observe(
                healthy_recovery,
                _health_snapshot(
                    HealthStatus.FAILED,
                    required=False,
                    checked_at=NOW + timedelta(minutes=offset),
                ),
            )
            == ()
        )

    assert store.active_incident_count() == 0
    assert store.pending_count() == 0
    assert store.health_observation_count() == 0


def test_unsafe_health_component_name_is_hashed_before_outbound_event(tmp_path: Path) -> None:
    store = _store(tmp_path / "state.db", iter(("incident-1", "event-open-1")))
    health = _health_snapshot(HealthStatus.FAILED, name="provider/super-secret-token")

    for offset in range(CONFIRMED_HEALTH_FAILURE_CHECKS):
        created = store.observe(
            _snapshot(RecoveryStatus.HEALTHY, attempts=0),
            RuntimeHealthSnapshot(
                status=health.status,
                checked_at=NOW + timedelta(seconds=offset * 30),
                components=health.components,
            ),
        )

    event = created[0]
    assert event.component.startswith("health:scheduler:id-")
    assert "super-secret-token" not in event.model_dump_json()


def test_owned_task_circuit_and_matching_health_failure_emit_one_incident(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path / "state.db", iter(("incident-1", "event-open-1")))
    recovery = RuntimeSelfHealingSnapshot(
        status=RecoveryStatus.OPEN,
        checked_at=NOW,
        components=(
            OwnedTaskRecoveryHealth(
                name="scheduler:morning-push",
                status=RecoveryStatus.OPEN,
                attempts=3,
            ),
        ),
    )

    created = store.observe(recovery, _health_snapshot(HealthStatus.FAILED))
    for offset in range(1, CONFIRMED_HEALTH_FAILURE_CHECKS + 2):
        duplicate = store.observe(
            RuntimeSelfHealingSnapshot(
                status=RecoveryStatus.OPEN,
                checked_at=NOW + timedelta(seconds=offset * 30),
                components=recovery.components,
            ),
            _health_snapshot(
                HealthStatus.FAILED,
                checked_at=NOW + timedelta(seconds=offset * 30),
            ),
        )
        assert duplicate == ()

    assert len(created) == 1
    assert created[0].component == "scheduler:morning-push"
    assert store.active_incident_count() == 1
    assert store.health_observation_count() == 0


def test_active_health_incident_resolves_when_component_becomes_optional(
    tmp_path: Path,
) -> None:
    store = _store(
        tmp_path / "state.db",
        iter(("incident-1", "event-open-1", "event-resolved-1")),
    )
    for offset in range(CONFIRMED_HEALTH_FAILURE_CHECKS):
        created = store.observe(
            _snapshot(RecoveryStatus.HEALTHY, attempts=0),
            _health_snapshot(
                HealthStatus.FAILED,
                checked_at=NOW + timedelta(seconds=offset * 30),
            ),
        )

    resolved = store.observe(
        _snapshot(RecoveryStatus.HEALTHY, attempts=0),
        _health_snapshot(
            HealthStatus.FAILED,
            required=False,
            checked_at=NOW + timedelta(seconds=90),
        ),
    )

    assert created[0].event_type is RuntimeAlertEventType.INCIDENT_OPENED
    assert resolved[0].event_type is RuntimeAlertEventType.INCIDENT_RESOLVED
    assert resolved[0].incident_id == created[0].incident_id


async def test_coordinator_retries_same_event_after_sink_failure_and_restart(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    db_path = tmp_path / "state.db"
    store = _store(db_path, iter(("incident-1", "event-open-1")))
    failing = RecordingSink(failures=1)
    first = RuntimeAlertCoordinator(store=store, sink=failing)

    pending = await first.check(_snapshot(RecoveryStatus.OPEN, attempts=3))
    retry_sink = RecordingSink()
    replacement = RuntimeAlertCoordinator(
        store=_store(db_path, iter(())),
        sink=retry_sink,
    )
    not_due = await replacement.check(_snapshot(RecoveryStatus.OPEN, attempts=3))
    events_before_due = tuple(retry_sink.events)
    delivered = await replacement.check(
        _snapshot(
            RecoveryStatus.OPEN,
            attempts=3,
            checked_at=NOW + timedelta(seconds=60),
        )
    )

    assert pending.status is RuntimeAlertDeliveryStatus.PENDING
    assert pending.pending_events == 1
    assert not_due.status is RuntimeAlertDeliveryStatus.PENDING
    assert events_before_due == ()
    assert retry_sink.events == [failing.events[0]]
    assert delivered.status is RuntimeAlertDeliveryStatus.HEALTHY
    assert failing.events[0] == retry_sink.events[0]
    assert retry_sink.events[0].event_id == "event-open-1"
    assert store.pending_count() == 0
    assert "secret sink failure" not in caplog.text


async def test_coordinator_preserves_open_then_resolved_order_after_failure(
    tmp_path: Path,
) -> None:
    ids = iter(("incident-1", "event-open-1", "event-resolved-1"))
    store = _store(tmp_path / "state.db", ids)
    failing = RecordingSink(failures=1)
    coordinator = RuntimeAlertCoordinator(store=store, sink=failing)

    await coordinator.check(_snapshot(RecoveryStatus.OPEN, attempts=3))
    await coordinator.check(_snapshot(RecoveryStatus.HEALTHY, attempts=0))
    successful = RecordingSink()
    replacement = RuntimeAlertCoordinator(store=store, sink=successful)

    result = await replacement.check(
        _snapshot(
            RecoveryStatus.HEALTHY,
            attempts=0,
            checked_at=NOW + timedelta(seconds=60),
        )
    )

    assert result.status is RuntimeAlertDeliveryStatus.HEALTHY
    assert [event.event_type for event in successful.events] == [
        RuntimeAlertEventType.INCIDENT_OPENED,
        RuntimeAlertEventType.INCIDENT_RESOLVED,
    ]
    assert successful.events[0].incident_id == successful.events[1].incident_id


async def test_webhook_sink_uses_stable_idempotency_key_without_leaking_secret() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        sink = WebhookRuntimeAlertSink(
            url="https://alerts.example.test/runtime",
            bearer_token="super-secret-token",
            client=client,
        )
        event = RuntimeAlertEvent(
            event_id="event-1",
            incident_id="incident-1",
            event_type=RuntimeAlertEventType.INCIDENT_OPENED,
            component=COMPONENT,
            attempts=3,
            occurred_at=NOW,
        )

        await sink.send(event)

    request = requests[0]
    payload = json.loads(request.content)
    assert request.headers["Idempotency-Key"] == "event-1"
    assert request.headers["Authorization"] == "Bearer super-secret-token"
    assert payload == {
        "schema_version": 1,
        "event_id": "event-1",
        "incident_id": "incident-1",
        "event_type": "incident_opened",
        "component": COMPONENT,
        "attempts": 3,
        "occurred_at": "2026-07-21T15:00:00Z",
    }
    assert "super-secret-token" not in json.dumps(payload)
    assert "alerts.example.test" not in json.dumps(payload)


async def test_accept_before_ack_retries_same_webhook_idempotency_key(tmp_path: Path) -> None:
    keys: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        keys.append(request.headers["Idempotency-Key"])
        return httpx.Response(202, request=request)

    store = _store(tmp_path / "state.db", iter(("incident-1", "event-open-1")))
    store.observe(_snapshot(RecoveryStatus.OPEN, attempts=3))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        sink = WebhookRuntimeAlertSink(
            url="https://alerts.example.test/runtime",
            client=client,
        )
        await sink.send(store.load_pending(limit=1, now=NOW)[0])
        replacement = RuntimeAlertCoordinator(store=store, sink=sink)

        await replacement.check(_snapshot(RecoveryStatus.OPEN, attempts=3))

    assert keys == ["event-open-1", "event-open-1"]
    assert store.pending_count() == 0


def test_runtime_alert_event_rejects_unknown_or_secret_fields() -> None:
    with pytest.raises(ValueError):
        RuntimeAlertEvent.model_validate(
            {
                "event_id": "event-1",
                "incident_id": "incident-1",
                "event_type": "incident_opened",
                "component": COMPONENT,
                "attempts": 3,
                "occurred_at": NOW.isoformat(),
                "exception": "secret detail",
            }
        )


def _store(db_path: Path, ids: Iterator[str]) -> SQLiteRuntimeAlertStore:
    return SQLiteRuntimeAlertStore(
        db_path,
        incident_id_factory=lambda: next(ids),
        event_id_factory=lambda: next(ids),
    )


def _snapshot(
    status: RecoveryStatus,
    *,
    attempts: int,
    checked_at: datetime = NOW,
) -> RuntimeSelfHealingSnapshot:
    return RuntimeSelfHealingSnapshot(
        status=status,
        checked_at=checked_at,
        components=(
            OwnedTaskRecoveryHealth(
                name=COMPONENT,
                status=status,
                attempts=attempts,
            ),
        ),
    )


def _health_snapshot(
    status: HealthStatus,
    *,
    required: bool = True,
    name: str = "morning-push",
    checked_at: datetime = NOW,
) -> RuntimeHealthSnapshot:
    return RuntimeHealthSnapshot(
        status=status,
        checked_at=checked_at,
        components=(
            RuntimeComponentHealth(
                kind="scheduler",
                name=name,
                required=required,
                status=status,
            ),
        ),
    )
