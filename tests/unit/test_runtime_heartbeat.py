from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aico.app.runtime_alerts import (
    RuntimeAlertCoordinator,
    RuntimeAlertDeliverySnapshot,
    RuntimeAlertDeliveryStatus,
    RuntimeAlertEvent,
    SQLiteRuntimeAlertStore,
)
from aico.app.runtime_health import RuntimeComponentHealth, RuntimeHealthSnapshot
from aico.app.runtime_heartbeat import RuntimeHeartbeat, heartbeat_health
from aico.app.runtime_liveness import (
    RuntimeLivenessSnapshot,
    RuntimeLivenessStatus,
)
from aico.app.runtime_self_healing import (
    BoundedOwnedTaskSupervisor,
    OwnedTaskRecovery,
    OwnedTaskRecoveryHealth,
    RecoveryStatus,
    RuntimeSelfHealingSnapshot,
)
from aico.core import HealthStatus


async def test_runtime_heartbeat_records_running_and_stopped_without_secrets(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-heartbeat.json"
    now = [datetime(2026, 7, 21, 12, tzinfo=UTC)]
    heartbeat = RuntimeHeartbeat(
        path,
        interval_seconds=60,
        clock=lambda: now[0],
        pid_factory=lambda: 4242,
        health_probe=lambda: _health_snapshot(now[0]),
    )

    await heartbeat.start()

    running = json.loads(path.read_text(encoding="utf-8"))
    assert running == {
        "schema_version": 2,
        "state": "running",
        "pid": 4242,
        "started_at": "2026-07-21T12:00:00+00:00",
        "heartbeat_at": "2026-07-21T12:00:00+00:00",
        "health": {
            "status": "degraded",
            "checked_at": "2026-07-21T12:00:00+00:00",
            "components": [
                {
                    "kind": "channel",
                    "name": "telegram",
                    "required": True,
                    "status": "ok",
                },
                {
                    "kind": "adapter",
                    "name": "codex",
                    "required": False,
                    "status": "failed",
                },
            ],
        },
    }
    assert "token" not in path.read_text(encoding="utf-8").casefold()

    now[0] += timedelta(seconds=5)
    await heartbeat.stop()

    stopped = json.loads(path.read_text(encoding="utf-8"))
    assert stopped["state"] == "stopped"
    assert stopped["heartbeat_at"] == "2026-07-21T12:00:05+00:00"


def test_heartbeat_health_distinguishes_fresh_stale_and_stopped(tmp_path: Path) -> None:
    path = tmp_path / "runtime-heartbeat.json"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "state": "running",
                "pid": 1,
                "started_at": (now - timedelta(minutes=2)).isoformat(),
                "heartbeat_at": (now - timedelta(seconds=20)).isoformat(),
                "health": {
                    "status": "ok",
                    "checked_at": (now - timedelta(seconds=20)).isoformat(),
                    "components": [],
                },
            }
        ),
        encoding="utf-8",
    )

    assert heartbeat_health(path, now=now, stale_after_seconds=90).status == "ok"
    assert heartbeat_health(path, now=now, stale_after_seconds=10).status == "fail"

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"] = "stopped"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert heartbeat_health(path, now=now, stale_after_seconds=90).status == "warn"


def test_heartbeat_health_reports_component_failure_and_legacy_unknown(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-heartbeat.json"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    base = {
        "schema_version": 2,
        "state": "running",
        "pid": 1,
        "started_at": now.isoformat(),
        "heartbeat_at": now.isoformat(),
    }
    failed = {
        **base,
        "health": {
            "status": "failed",
            "checked_at": now.isoformat(),
            "components": [
                {
                    "kind": "channel",
                    "name": "telegram",
                    "required": True,
                    "status": "failed",
                }
            ],
        },
    }
    path.write_text(json.dumps(failed), encoding="utf-8")

    health = heartbeat_health(path, now=now)

    assert health.status == "fail"
    assert health.detail == "components failed: channel:telegram"

    path.write_text(json.dumps(base), encoding="utf-8")
    legacy = heartbeat_health(path, now=now)

    assert legacy.status == "warn"
    assert legacy.detail == "fresh (0s old); component health unavailable"


async def test_runtime_heartbeat_records_secret_free_self_healing_state(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-heartbeat.json"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)

    async def health_probe() -> RuntimeHealthSnapshot:
        return _ok_health_snapshot(now)

    async def recovery_probe() -> RuntimeSelfHealingSnapshot:
        return _recovery_snapshot(now, RecoveryStatus.RECOVERING, attempts=1)

    heartbeat = RuntimeHeartbeat(
        path,
        interval_seconds=60,
        clock=lambda: now,
        health_probe=health_probe,
        self_healing_probe=recovery_probe,
    )

    await heartbeat.start()

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 3
    assert payload["self_healing"] == {
        "status": "recovering",
        "checked_at": "2026-07-21T12:00:00+00:00",
        "components": [
            {
                "name": "channel:telegram-polling",
                "status": "recovering",
                "attempts": 1,
            }
        ],
    }
    assert heartbeat_health(path, now=now).status == "warn"
    assert "token" not in path.read_text(encoding="utf-8").casefold()
    await heartbeat.stop()


async def test_runtime_heartbeat_drives_owned_task_recovery_before_health_check(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-heartbeat.json"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    alive = False
    restart_count = 0

    async def restart() -> None:
        nonlocal alive, restart_count
        restart_count += 1
        alive = True

    async def health_probe() -> RuntimeHealthSnapshot:
        assert alive is True
        return _ok_health_snapshot(now)

    supervisor = BoundedOwnedTaskSupervisor(
        [OwnedTaskRecovery("channel:telegram-polling", lambda: alive, restart)],
        clock=lambda: now,
    )
    heartbeat = RuntimeHeartbeat(
        path,
        interval_seconds=60,
        clock=lambda: now,
        health_probe=health_probe,
        self_healing_probe=supervisor.check,
    )

    await heartbeat.start()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert restart_count == 1
    assert payload["self_healing"]["status"] == "recovering"
    assert payload["health"]["status"] == "ok"
    await heartbeat.stop()


def test_heartbeat_health_reports_open_recovery_circuit_as_failed(tmp_path: Path) -> None:
    path = tmp_path / "runtime-heartbeat.json"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "state": "running",
                "pid": 1,
                "started_at": now.isoformat(),
                "heartbeat_at": now.isoformat(),
                "health": _ok_health_snapshot(now).to_payload(),
                "self_healing": _recovery_snapshot(
                    now,
                    RecoveryStatus.OPEN,
                    attempts=3,
                ).to_payload(),
            }
        ),
        encoding="utf-8",
    )

    health = heartbeat_health(path, now=now)

    assert health.status == "fail"
    assert health.detail == "owned task recovery open: channel:telegram-polling"


async def test_runtime_heartbeat_records_health_before_alerting(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-heartbeat.json"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    order: list[str] = []

    async def recovery_probe() -> RuntimeSelfHealingSnapshot:
        order.append("recovery")
        return _recovery_snapshot(now, RecoveryStatus.HEALTHY, attempts=0)

    async def alert_probe(
        snapshot: RuntimeSelfHealingSnapshot,
        health_snapshot: RuntimeHealthSnapshot | None,
    ) -> RuntimeAlertDeliverySnapshot:
        assert health_snapshot is not None
        order.append(f"alert:{snapshot.status.value}")
        return _alert_snapshot(now, RuntimeAlertDeliveryStatus.DISABLED, pending=0)

    async def health_probe() -> RuntimeHealthSnapshot:
        order.append("health")
        return _ok_health_snapshot(now)

    heartbeat = RuntimeHeartbeat(
        path,
        interval_seconds=60,
        clock=lambda: now,
        self_healing_probe=recovery_probe,
        alert_probe=alert_probe,
        health_probe=health_probe,
    )

    await heartbeat.start()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert order == ["recovery", "health", "alert:healthy"]
    assert payload["schema_version"] == 4
    assert payload["alerting"] == {
        "status": "disabled",
        "checked_at": "2026-07-21T12:00:00Z",
        "pending_events": 0,
    }
    assert heartbeat_health(path, now=now).detail == "out-of-band alerting disabled"
    await heartbeat.stop()


def test_heartbeat_health_reports_pending_and_failed_alert_delivery(tmp_path: Path) -> None:
    path = tmp_path / "runtime-heartbeat.json"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    payload = {
        "schema_version": 4,
        "state": "running",
        "pid": 1,
        "started_at": now.isoformat(),
        "heartbeat_at": now.isoformat(),
        "health": _ok_health_snapshot(now).to_payload(),
        "self_healing": _recovery_snapshot(
            now,
            RecoveryStatus.HEALTHY,
            attempts=0,
        ).to_payload(),
        "alerting": _alert_snapshot(
            now,
            RuntimeAlertDeliveryStatus.PENDING,
            pending=2,
        ).to_payload(),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    pending = heartbeat_health(path, now=now)
    payload["alerting"] = _alert_snapshot(
        now,
        RuntimeAlertDeliveryStatus.FAILED,
        pending=None,
    ).to_payload()
    path.write_text(json.dumps(payload), encoding="utf-8")
    failed = heartbeat_health(path, now=now)

    assert pending.status == "warn"
    assert pending.detail == "out-of-band alerts pending: 2"
    assert failed.status == "fail"
    assert failed.detail == "out-of-band alerting failed"


async def test_required_component_failure_creates_alert_after_three_health_checks(
    tmp_path: Path,
) -> None:
    delivered: list[RuntimeAlertEvent] = []

    class Sink:
        async def send(self, event: RuntimeAlertEvent) -> None:
            delivered.append(event)

    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteRuntimeAlertStore(tmp_path / "state.db")
    coordinator = RuntimeAlertCoordinator(
        store=store,
        sink=Sink(),
    )

    async def recovery_probe() -> RuntimeSelfHealingSnapshot:
        return _recovery_snapshot(now, RecoveryStatus.HEALTHY, attempts=0)

    health_status = [HealthStatus.FAILED]
    health_checks = [0]

    async def health_probe() -> RuntimeHealthSnapshot:
        checked_at = now + timedelta(seconds=health_checks[0] * 30)
        health_checks[0] += 1
        return RuntimeHealthSnapshot(
            status=health_status[0],
            checked_at=checked_at,
            components=(
                RuntimeComponentHealth(
                    kind="channel",
                    name="telegram",
                    required=True,
                    status=health_status[0],
                ),
            ),
        )

    heartbeat = RuntimeHeartbeat(
        tmp_path / "heartbeat.json",
        self_healing_probe=recovery_probe,
        alert_probe=coordinator.check,
        health_probe=health_probe,
    )

    await heartbeat.start()
    await heartbeat._refresh()  # noqa: SLF001
    await heartbeat._refresh()  # noqa: SLF001

    assert len(delivered) == 1
    assert delivered[0].event_type.value == "incident_opened"
    assert delivered[0].component == "health:channel:telegram"
    assert store.pending_count() == 0

    health_status[0] = HealthStatus.OK
    await heartbeat._refresh()  # noqa: SLF001

    assert [event.event_type.value for event in delivered] == [
        "incident_opened",
        "incident_resolved",
    ]
    assert delivered[0].incident_id == delivered[1].incident_id
    assert store.pending_count() == 0
    assert heartbeat_health(tmp_path / "heartbeat.json", now=now).status == "ok"
    await heartbeat.stop()


async def test_runtime_heartbeat_records_liveness_after_health_and_alert(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-heartbeat.json"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    order: list[str] = []

    async def recovery_probe() -> RuntimeSelfHealingSnapshot:
        order.append("recovery")
        return _recovery_snapshot(now, RecoveryStatus.HEALTHY, attempts=0)

    async def alert_probe(
        snapshot: RuntimeSelfHealingSnapshot,
        health_snapshot: RuntimeHealthSnapshot | None,
    ) -> RuntimeAlertDeliverySnapshot:
        assert health_snapshot is not None
        order.append(f"alert:{snapshot.status.value}")
        return _alert_snapshot(now, RuntimeAlertDeliveryStatus.HEALTHY, pending=0)

    async def liveness_probe(
        alerting: RuntimeAlertDeliverySnapshot | None,
    ) -> RuntimeLivenessSnapshot:
        assert alerting is not None
        assert alerting.status is RuntimeAlertDeliveryStatus.HEALTHY
        order.append("liveness")
        return _liveness_snapshot(now, RuntimeLivenessStatus.HEALTHY)

    async def health_probe() -> RuntimeHealthSnapshot:
        order.append("health")
        return _ok_health_snapshot(now)

    heartbeat = RuntimeHeartbeat(
        path,
        interval_seconds=60,
        clock=lambda: now,
        self_healing_probe=recovery_probe,
        alert_probe=alert_probe,
        liveness_probe=liveness_probe,
        health_probe=health_probe,
    )

    await heartbeat.start()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert order == ["recovery", "health", "alert:healthy", "liveness"]
    assert payload["schema_version"] == 5
    assert payload["liveness"] == {
        "status": "healthy",
        "checked_at": "2026-07-21T12:00:00Z",
        "last_success_at": "2026-07-21T12:00:00Z",
        "expires_at": "2026-07-21T12:03:00Z",
    }
    assert heartbeat_health(path, now=now).status == "ok"
    assert "owner-runtime" not in path.read_text(encoding="utf-8")
    await heartbeat.stop()


def test_heartbeat_health_reports_liveness_disabled_degraded_and_failed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-heartbeat.json"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    payload = {
        "schema_version": 5,
        "state": "running",
        "pid": 1,
        "started_at": now.isoformat(),
        "heartbeat_at": now.isoformat(),
        "health": _ok_health_snapshot(now).to_payload(),
        "self_healing": _recovery_snapshot(
            now,
            RecoveryStatus.HEALTHY,
            attempts=0,
        ).to_payload(),
        "alerting": _alert_snapshot(
            now,
            RuntimeAlertDeliveryStatus.HEALTHY,
            pending=0,
        ).to_payload(),
        "liveness": _liveness_snapshot(
            now,
            RuntimeLivenessStatus.DISABLED,
        ).to_payload(),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    disabled = heartbeat_health(path, now=now)

    payload["liveness"] = _liveness_snapshot(
        now,
        RuntimeLivenessStatus.DEGRADED,
    ).to_payload()
    path.write_text(json.dumps(payload), encoding="utf-8")
    degraded = heartbeat_health(path, now=now)

    payload["liveness"] = _liveness_snapshot(
        now,
        RuntimeLivenessStatus.FAILED,
    ).to_payload()
    path.write_text(json.dumps(payload), encoding="utf-8")
    failed = heartbeat_health(path, now=now)

    assert disabled == type(disabled)(status="warn", detail="external liveness pulse disabled")
    assert degraded == type(degraded)(status="warn", detail="external liveness pulse degraded")
    assert failed == type(failed)(status="fail", detail="external liveness pulse failed")


def test_heartbeat_v5_requires_valid_secret_free_liveness_state(tmp_path: Path) -> None:
    path = tmp_path / "runtime-heartbeat.json"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    payload = {
        "schema_version": 5,
        "state": "running",
        "pid": 1,
        "started_at": now.isoformat(),
        "heartbeat_at": now.isoformat(),
        "health": _ok_health_snapshot(now).to_payload(),
        "self_healing": _recovery_snapshot(
            now,
            RecoveryStatus.HEALTHY,
            attempts=0,
        ).to_payload(),
        "alerting": _alert_snapshot(
            now,
            RuntimeAlertDeliveryStatus.HEALTHY,
            pending=0,
        ).to_payload(),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    missing = heartbeat_health(path, now=now)
    payload["liveness"] = _liveness_snapshot(
        now,
        RuntimeLivenessStatus.HEALTHY,
    ).to_payload()
    payload.pop("alerting")
    path.write_text(json.dumps(payload), encoding="utf-8")
    missing_alerting = heartbeat_health(path, now=now)
    payload["alerting"] = _alert_snapshot(
        now,
        RuntimeAlertDeliveryStatus.HEALTHY,
        pending=0,
    ).to_payload()
    payload["liveness"] = {
        "status": "healthy",
        "checked_at": now.isoformat(),
        "last_success_at": None,
        "expires_at": None,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    inconsistent = heartbeat_health(path, now=now)

    assert missing.detail == "invalid liveness state"
    assert missing_alerting.detail == "invalid alerting state"
    assert inconsistent.detail == "invalid liveness state"


async def _health_snapshot(now: datetime) -> RuntimeHealthSnapshot:
    return RuntimeHealthSnapshot(
        status=HealthStatus.DEGRADED,
        checked_at=now,
        components=(
            RuntimeComponentHealth(
                kind="channel",
                name="telegram",
                required=True,
                status=HealthStatus.OK,
            ),
            RuntimeComponentHealth(
                kind="adapter",
                name="codex",
                required=False,
                status=HealthStatus.FAILED,
            ),
        ),
    )


def _ok_health_snapshot(now: datetime) -> RuntimeHealthSnapshot:
    return RuntimeHealthSnapshot(
        status=HealthStatus.OK,
        checked_at=now,
        components=(
            RuntimeComponentHealth(
                kind="channel",
                name="telegram",
                required=True,
                status=HealthStatus.OK,
            ),
        ),
    )


def _recovery_snapshot(
    now: datetime,
    status: RecoveryStatus,
    *,
    attempts: int,
) -> RuntimeSelfHealingSnapshot:
    return RuntimeSelfHealingSnapshot(
        status=status,
        checked_at=now,
        components=(
            OwnedTaskRecoveryHealth(
                name="channel:telegram-polling",
                status=status,
                attempts=attempts,
            ),
        ),
    )


def _liveness_snapshot(
    now: datetime,
    status: RuntimeLivenessStatus,
) -> RuntimeLivenessSnapshot:
    has_success = status in {
        RuntimeLivenessStatus.HEALTHY,
        RuntimeLivenessStatus.DEGRADED,
    }
    return RuntimeLivenessSnapshot(
        status=status,
        checked_at=now,
        last_success_at=now if has_success else None,
        expires_at=now + timedelta(seconds=180) if has_success else None,
    )


def _alert_snapshot(
    now: datetime,
    status: RuntimeAlertDeliveryStatus,
    *,
    pending: int | None,
) -> RuntimeAlertDeliverySnapshot:
    return RuntimeAlertDeliverySnapshot(
        status=status,
        checked_at=now,
        pending_events=pending,
    )
