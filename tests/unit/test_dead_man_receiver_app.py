from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from aico.app.dead_man_receiver import (
    DeadManNotificationAttemptResult,
    DeadManOutboundEvent,
    QuorumDeadManNotificationSink,
    SQLiteDeadManReceiverStore,
    WebhookDeadManNotificationSink,
)
from aico.app.dead_man_receiver_app import (
    DeadManReceiverSettings,
    ReceiverWorkerHealth,
    _notification_sink,
    _run_receiver_worker,
    build_dead_man_receiver_app,
)
from aico.app.runtime_liveness import (
    RuntimeLivenessPublisher,
    RuntimeLivenessPulse,
    WebhookRuntimeLivenessSink,
)

PULSE_SECRET = "p" * 32
ADMIN_SECRET = "a" * 32


class RecordingSink:
    def __init__(self) -> None:
        self.events: list[DeadManOutboundEvent] = []

    async def send(
        self,
        event: DeadManOutboundEvent,
    ) -> DeadManNotificationAttemptResult | None:
        self.events.append(event)
        return None


class DualRecordingSink(RecordingSink):
    async def send(self, event: DeadManOutboundEvent) -> DeadManNotificationAttemptResult:
        self.events.append(event)
        return DeadManNotificationAttemptResult(acknowledged_routes=(True, True))


class FailingSink:
    async def send(self, event: DeadManOutboundEvent) -> None:
        _ = event
        raise RuntimeError("private downstream failure")


def test_receiver_settings_require_https_distinct_tokens_and_redact_secrets(
    tmp_path: Path,
) -> None:
    base = {
        "state_db_path": tmp_path / "receiver.db",
        "pulse_bearer_token": PULSE_SECRET,
        "admin_bearer_token": ADMIN_SECRET,
        "notification_webhook_url": "https://notify.example.test/private",
    }
    with pytest.raises(ValueError, match="HTTPS"):
        DeadManReceiverSettings.model_validate(
            {**base, "notification_webhook_url": "http://notify.example.test"}
        )
    with pytest.raises(ValueError, match="must differ"):
        DeadManReceiverSettings.model_validate({**base, "admin_bearer_token": PULSE_SECRET})
    with pytest.raises(ValueError, match="placeholder"):
        DeadManReceiverSettings.model_validate(
            {
                **base,
                "pulse_bearer_token": "replace-with-at-least-32-random-characters",
            }
        )
    with pytest.raises(ValueError, match="at least 32"):
        DeadManReceiverSettings.model_validate({**base, "admin_bearer_token": "too-short"})

    settings = DeadManReceiverSettings.model_validate(base)
    rendered = str(settings)

    assert PULSE_SECRET not in rendered
    assert ADMIN_SECRET not in rendered
    assert "notify.example.test" not in rendered


def test_receiver_fallback_notification_requires_independent_valid_quorum(
    tmp_path: Path,
) -> None:
    base = {
        "state_db_path": tmp_path / "receiver.db",
        "pulse_bearer_token": PULSE_SECRET,
        "admin_bearer_token": ADMIN_SECRET,
        "notification_webhook_url": "https://primary.example.test/private",
        "notification_bearer_token": "primary-secret",
        "notification_fallback_webhook_url": "https://fallback.example.test/private",
        "notification_fallback_bearer_token": "fallback-secret",
        "notification_minimum_acknowledgements": 1,
    }
    settings = DeadManReceiverSettings.model_validate(base)

    assert isinstance(_notification_sink(settings), QuorumDeadManNotificationSink)
    assert "primary.example.test" not in str(settings)
    assert "fallback.example.test" not in str(settings)
    assert "primary-secret" not in str(settings)
    assert "fallback-secret" not in str(settings)

    sink = RecordingSink()
    app = build_dead_man_receiver_app(settings, notification_sink=sink)
    with TestClient(app) as client:
        assert client.get("/v1/notification-routes").status_code == 401
        route_status = client.get(
            "/v1/notification-routes",
            headers={"Authorization": f"Bearer {ADMIN_SECRET}"},
        )
        policy = SQLiteDeadManReceiverStore(settings.state_db_path).get_notification_policy()
    assert policy.configured_routes == 2
    assert policy.minimum_acknowledgements == 1
    assert route_status.status_code == 200
    assert [route["status"] for route in route_status.json()["routes"]] == [
        "unknown",
        "unknown",
    ]
    assert "example.test" not in route_status.text

    with pytest.raises(ValueError, match="fallback URL"):
        DeadManReceiverSettings.model_validate(
            {
                **base,
                "notification_fallback_webhook_url": None,
            }
        )
    with pytest.raises(ValueError, match="different HTTPS origin"):
        DeadManReceiverSettings.model_validate(
            {
                **base,
                "notification_fallback_webhook_url": ("https://primary.example.test/other-path"),
            }
        )
    with pytest.raises(ValueError, match="bearer tokens must differ"):
        DeadManReceiverSettings.model_validate(
            {
                **base,
                "notification_fallback_bearer_token": "primary-secret",
            }
        )
    with pytest.raises(ValueError, match="differ from receiver authority"):
        DeadManReceiverSettings.model_validate(
            {
                **base,
                "notification_fallback_bearer_token": PULSE_SECRET,
            }
        )
    with pytest.raises(ValueError, match="cannot exceed configured routes"):
        DeadManReceiverSettings.model_validate(
            {
                **base,
                "notification_minimum_acknowledgements": 3,
            }
        )


def test_receiver_single_notification_route_keeps_narrow_sink(tmp_path: Path) -> None:
    sink = _notification_sink(_settings(tmp_path))

    assert isinstance(sink, WebhookDeadManNotificationSink)


def test_receiver_silent_probe_requires_explicit_dual_route_contract(tmp_path: Path) -> None:
    base = {
        "state_db_path": tmp_path / "receiver.db",
        "pulse_bearer_token": PULSE_SECRET,
        "admin_bearer_token": ADMIN_SECRET,
        "notification_webhook_url": "https://primary.example.test/private",
        "notification_probe_contract": "silent-route-probe-v1",
        "notification_probe_interval_seconds": 60,
        "notification_probe_failure_threshold": 2,
        "notification_probe_max_age_seconds": 120,
    }
    with pytest.raises(ValueError, match="requires two notification routes"):
        DeadManReceiverSettings.model_validate(base)
    with pytest.raises(ValueError, match="cover two intervals"):
        DeadManReceiverSettings.model_validate(
            {
                **base,
                "notification_fallback_webhook_url": "https://fallback.example.test/private",
                "notification_probe_interval_seconds": 120,
                "notification_probe_max_age_seconds": 200,
            }
        )

    settings = DeadManReceiverSettings.model_validate(
        {
            **base,
            "notification_fallback_webhook_url": "https://fallback.example.test/private",
        }
    )
    sink = DualRecordingSink()
    app = build_dead_man_receiver_app(settings, notification_sink=sink)
    with TestClient(app) as client:
        response = client.get(
            "/v1/notification-routes",
            headers={"Authorization": f"Bearer {ADMIN_SECRET}"},
        )

    assert response.status_code == 200
    assert response.json()["probe"]["contract"] == "silent-route-probe-v1"
    assert response.json()["probe"]["fresh"] is True
    assert response.json()["probe"]["last_acknowledged_routes"] == [True, True]
    assert [event.event_type for event in sink.events] == ["notification_route_probe"]


def test_receiver_startup_refuses_quorum_downgrade_with_pending_event(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    settings = DeadManReceiverSettings.model_validate(
        {
            "state_db_path": tmp_path / "receiver.db",
            "pulse_bearer_token": PULSE_SECRET,
            "admin_bearer_token": ADMIN_SECRET,
            "notification_webhook_url": "https://primary.example.test/private",
            "notification_fallback_webhook_url": ("https://fallback.example.test/private"),
            "notification_minimum_acknowledgements": 1,
        }
    )
    store = SQLiteDeadManReceiverStore(settings.state_db_path)
    store.configure_notification_policy(
        configured_routes=2,
        minimum_acknowledgements=2,
        configured_at=now,
    )
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    store.evaluate(now=now + timedelta(seconds=180))
    app = build_dead_man_receiver_app(
        settings,
        notification_sink=RecordingSink(),
        clock=lambda: now + timedelta(seconds=181),
    )

    with pytest.raises(RuntimeError, match="policy conflicts with pending"):
        with TestClient(app):
            pass


def test_receiver_http_separates_admin_and_pulse_authority_and_is_idempotent(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    settings = _settings(tmp_path)
    sink = RecordingSink()
    app = build_dead_man_receiver_app(
        settings,
        notification_sink=sink,
        clock=lambda: now,
    )
    admin_headers = {"Authorization": f"Bearer {ADMIN_SECRET}"}
    pulse = _pulse(now)
    pulse_headers = {
        "Authorization": f"Bearer {PULSE_SECRET}",
        "Idempotency-Key": pulse.idempotency_key,
    }

    with TestClient(app) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/readyz").json() == {"status": "ready"}
        assert (
            client.post(
                "/v1/monitors/owner-runtime/arm",
                json={"expires_after_seconds": 180},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/v1/monitors/owner-runtime/arm",
                json={"expires_after_seconds": 180},
                headers={"Authorization": f"Bearer {PULSE_SECRET}"},
            ).status_code
            == 401
        )
        armed = client.post(
            "/v1/monitors/owner-runtime/arm",
            json={"expires_after_seconds": 180},
            headers=admin_headers,
        )
        wrong_key = client.post(
            "/v1/runtime-liveness/pulses",
            json=pulse.to_payload(),
            headers={**pulse_headers, "Idempotency-Key": "wrong-key"},
        )
        accepted = client.post(
            "/v1/runtime-liveness/pulses",
            json=pulse.to_payload(),
            headers=pulse_headers,
        )
        duplicate = client.post(
            "/v1/runtime-liveness/pulses",
            json=pulse.to_payload(),
            headers=pulse_headers,
        )
        monitor = client.get(
            "/v1/monitors/owner-runtime",
            headers=admin_headers,
        )

    assert armed.status_code == 200
    assert wrong_key.status_code == 409
    assert accepted.status_code == 200
    assert accepted.json()["accepted"] is True
    assert duplicate.status_code == 200
    assert duplicate.json()["accepted"] is False
    assert monitor.status_code == 200
    rendered = str((armed.json(), accepted.json(), duplicate.json(), monitor.json()))
    assert PULSE_SECRET not in rendered
    assert ADMIN_SECRET not in rendered
    assert "notify.example.test" not in rendered


def test_receiver_http_rejects_extra_fields_and_disarm_cannot_be_undone_by_pulse(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    settings = _settings(tmp_path)
    app = build_dead_man_receiver_app(
        settings,
        notification_sink=RecordingSink(),
        clock=lambda: now,
    )
    admin_headers = {"Authorization": f"Bearer {ADMIN_SECRET}"}
    pulse = _pulse(now)
    pulse_headers = {
        "Authorization": f"Bearer {PULSE_SECRET}",
        "Idempotency-Key": pulse.idempotency_key,
    }

    with TestClient(app) as client:
        client.post(
            "/v1/monitors/owner-runtime/arm",
            json={"expires_after_seconds": 180},
            headers=admin_headers,
        )
        extra = client.post(
            "/v1/runtime-liveness/pulses",
            json={**pulse.to_payload(), "token": "leak-me"},
            headers=pulse_headers,
        )
        disarmed = client.post(
            "/v1/monitors/owner-runtime/disarm",
            headers=admin_headers,
        )
        delayed = client.post(
            "/v1/runtime-liveness/pulses",
            json=pulse.to_payload(),
            headers=pulse_headers,
        )

    assert extra.status_code == 422
    assert "leak-me" not in extra.text
    assert disarmed.status_code == 200
    assert delayed.status_code == 409


def test_receiver_evidence_export_requires_admin_and_stays_secret_free(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    settings = _settings(tmp_path)
    SQLiteDeadManReceiverStore(settings.state_db_path).arm(
        "owner-runtime",
        expires_after_seconds=180,
        armed_at=now,
    )
    app = build_dead_man_receiver_app(
        settings,
        notification_sink=RecordingSink(),
        clock=lambda: now + timedelta(seconds=181),
    )
    admin_headers = {"Authorization": f"Bearer {ADMIN_SECRET}"}

    with TestClient(app) as client:
        missing = client.get("/v1/monitors/owner-runtime/evidence")
        pulse_authority = client.get(
            "/v1/monitors/owner-runtime/evidence",
            headers={"Authorization": f"Bearer {PULSE_SECRET}"},
        )
        exported = client.get(
            "/v1/monitors/owner-runtime/evidence?max_outages=20",
            headers=admin_headers,
        )
        unknown = client.get(
            "/v1/monitors/unknown-runtime/evidence",
            headers=admin_headers,
        )

    assert missing.status_code == 401
    assert pulse_authority.status_code == 401
    assert exported.status_code == 200
    assert exported.json()["outages"][0]["opened"]["event_type"] == "outage_opened"
    assert unknown.status_code == 404
    rendered = exported.text
    assert PULSE_SECRET not in rendered
    assert ADMIN_SECRET not in rendered
    assert "notify.example.test" not in rendered
    assert str(settings.state_db_path) not in rendered


def test_receiver_lifespan_immediately_reconciles_persisted_expiry(
    tmp_path: Path,
) -> None:
    armed_at = datetime(2026, 7, 21, 12, tzinfo=UTC)
    settings = _settings(tmp_path)
    store = SQLiteDeadManReceiverStore(settings.state_db_path)
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=armed_at)
    sink = RecordingSink()
    app = build_dead_man_receiver_app(
        settings,
        notification_sink=sink,
        clock=lambda: armed_at + timedelta(seconds=181),
    )

    with TestClient(app):
        pass

    assert len(sink.events) == 1
    assert sink.events[0].event_type == "outage_opened"
    assert SQLiteDeadManReceiverStore(settings.state_db_path).pending_count() == 0


def test_receiver_readyz_fails_closed_on_stale_worker_and_recovers(
    tmp_path: Path,
) -> None:
    monotonic_now = [0.0]
    settings = _settings(tmp_path, sweep_interval_seconds=10)
    app = build_dead_man_receiver_app(
        settings,
        notification_sink=RecordingSink(),
        monotonic_clock=lambda: monotonic_now[0],
    )

    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 200

        monotonic_now[0] = 31
        stale = client.get("/readyz")
        app.state.receiver_worker_health.record_success(monotonic_now[0])
        recovered = client.get("/readyz")

    assert stale.status_code == 503
    assert stale.json() == {"detail": "not ready"}
    assert recovered.status_code == 200


def test_receiver_readyz_hides_database_failure_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = build_dead_man_receiver_app(
        _settings(tmp_path),
        notification_sink=RecordingSink(),
    )

    def fail_ping() -> None:
        raise RuntimeError("private database path and detail")

    monkeypatch.setattr(app.state.receiver_store, "ping", fail_ping)
    with TestClient(app) as client:
        response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"detail": "not ready"}
    assert "private database" not in response.text


def test_receiver_readyz_stays_ready_when_downstream_delivery_is_backing_off(
    tmp_path: Path,
) -> None:
    armed_at = datetime(2026, 7, 21, 12, tzinfo=UTC)
    settings = _settings(tmp_path)
    store = SQLiteDeadManReceiverStore(settings.state_db_path)
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=armed_at)
    app = build_dead_man_receiver_app(
        settings,
        notification_sink=FailingSink(),
        clock=lambda: armed_at + timedelta(seconds=181),
    )

    with TestClient(app) as client:
        response = client.get("/readyz")

    assert response.status_code == 200
    assert SQLiteDeadManReceiverStore(settings.state_db_path).pending_count() == 1


def test_receiver_worker_health_fails_after_three_errors_and_success_recovers() -> None:
    health = ReceiverWorkerHealth(stale_after_seconds=30)
    health.record_success(0)

    health.record_failure()
    health.record_failure()
    assert health.is_ready(29) is True

    health.record_failure()
    assert health.is_ready(29) is False

    health.record_success(30)
    assert health.is_ready(31) is True


async def test_aico_publisher_reaches_strict_receiver_over_dedicated_liveness_route(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    settings = _settings(tmp_path)
    app = build_dead_man_receiver_app(
        settings,
        notification_sink=RecordingSink(),
        clock=lambda: now,
    )
    with TestClient(app) as admin_client:
        armed = admin_client.post(
            "/v1/monitors/owner-runtime/arm",
            json={"expires_after_seconds": 180},
            headers={"Authorization": f"Bearer {ADMIN_SECRET}"},
        )
        assert armed.status_code == 200

    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app))
    sink = WebhookRuntimeLivenessSink(
        url="https://receiver.example/v1/runtime-liveness/pulses",
        bearer_token=PULSE_SECRET,
        client=client,
    )
    publisher = RuntimeLivenessPublisher(
        runtime_id="owner-runtime",
        sink=sink,
        interval_seconds=60,
        expires_after_seconds=180,
        boot_id_factory=lambda: "boot-1",
        clock=lambda: now,
    )
    try:
        snapshot = await publisher.check()
        wrong_protocol = await client.post(
            "https://receiver.example/v1/runtime-liveness/pulses",
            json={
                "schema_version": 1,
                "event_type": "incident_opened",
                "event_id": "event-1",
            },
            headers={
                "Authorization": f"Bearer {PULSE_SECRET}",
                "Idempotency-Key": "event-1",
            },
        )
    finally:
        await client.aclose()

    monitor = SQLiteDeadManReceiverStore(settings.state_db_path).get_monitor("owner-runtime")
    assert snapshot.status.value == "healthy"
    assert monitor.last_sequence == 1
    assert monitor.last_received_at == now
    assert wrong_protocol.status_code == 422


async def test_receiver_worker_wakes_without_waiting_for_full_interval() -> None:
    calls = 0
    wake = asyncio.Event()
    health = ReceiverWorkerHealth(stale_after_seconds=30)

    class Coordinator:
        async def check(self, *, now: datetime) -> None:
            nonlocal calls
            _ = now
            calls += 1
            if calls == 1:
                wake.set()
            elif calls == 2:
                raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await _run_receiver_worker(
            Coordinator(),
            wake=wake,
            interval_seconds=3600,
            clock=lambda: datetime(2026, 7, 21, 12, tzinfo=UTC),
            health=health,
            monotonic_clock=lambda: 0,
        )

    assert calls == 2
    assert health.is_ready(0) is True


def test_dead_man_receiver_docker_contract_is_non_root_and_persistent() -> None:
    deploy_dir = Path(__file__).parents[2] / "deploy/dead-man-receiver"
    dockerfile = (deploy_dir / "Dockerfile").read_text(encoding="utf-8")
    compose = (deploy_dir / "compose.yaml").read_text(encoding="utf-8")

    assert "USER aico" in dockerfile
    assert 'VOLUME ["/data"]' in dockerfile
    assert "aico-dead-man-receiver" in dockerfile
    assert "TOKEN=" not in dockerfile
    assert "SECRET=" not in dockerfile
    assert '"127.0.0.1:8080:8080"' in compose
    assert "read_only: true" in compose
    assert "no-new-privileges:true" in compose
    assert "dead-man-data:/data" in compose
    assert "restart: unless-stopped" in compose
    assert "/readyz" in compose


def _settings(
    tmp_path: Path,
    *,
    sweep_interval_seconds: float = 3600,
) -> DeadManReceiverSettings:
    return DeadManReceiverSettings.model_validate(
        {
            "state_db_path": tmp_path / "receiver.db",
            "pulse_bearer_token": PULSE_SECRET,
            "admin_bearer_token": ADMIN_SECRET,
            "notification_webhook_url": "https://notify.example.test/private",
            "sweep_interval_seconds": sweep_interval_seconds,
        }
    )


def _pulse(now: datetime) -> RuntimeLivenessPulse:
    return RuntimeLivenessPulse(
        runtime_id="owner-runtime",
        boot_id="boot-1",
        sequence=1,
        sent_at=now,
        interval_seconds=60,
        expires_after_seconds=180,
    )
