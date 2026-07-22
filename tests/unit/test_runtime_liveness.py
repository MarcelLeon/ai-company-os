from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import ValidationError

from aico.app.runtime_liveness import (
    RuntimeAlertDeliverySignal,
    RuntimeLivenessPublisher,
    RuntimeLivenessPulse,
    RuntimeLivenessReceiverStatus,
    RuntimeLivenessStatus,
    RuntimeLivenessTracker,
    RuntimeLivenessTransition,
    WebhookRuntimeLivenessSink,
)


class RecordingSink:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.pulses: list[RuntimeLivenessPulse] = []

    async def send(self, pulse: RuntimeLivenessPulse) -> None:
        self.pulses.append(pulse)
        if self.fail:
            raise RuntimeError("private receiver failure")


async def test_publisher_sends_immediate_secret_free_pulse_then_waits_for_interval() -> None:
    now = [datetime(2026, 7, 21, 12, tzinfo=UTC)]
    sink = RecordingSink()
    publisher = RuntimeLivenessPublisher(
        runtime_id="owner-runtime",
        sink=sink,
        interval_seconds=60,
        expires_after_seconds=180,
        boot_id_factory=lambda: "boot-1",
        clock=lambda: now[0],
    )

    first = await publisher.check()
    now[0] += timedelta(seconds=59)
    waiting = await publisher.check()
    now[0] += timedelta(seconds=1)
    second = await publisher.check()

    assert [pulse.sequence for pulse in sink.pulses] == [1, 2]
    assert sink.pulses[0].to_payload() == {
        "schema_version": 2,
        "event_type": "runtime_liveness_pulse",
        "runtime_id": "owner-runtime",
        "boot_id": "boot-1",
        "sequence": 1,
        "sent_at": "2026-07-21T12:00:00Z",
        "interval_seconds": 60,
        "expires_after_seconds": 180,
        "alert_delivery_status": "disabled",
    }
    assert first.status is RuntimeLivenessStatus.HEALTHY
    assert waiting.status is RuntimeLivenessStatus.HEALTHY
    assert second.status is RuntimeLivenessStatus.HEALTHY
    assert "token" not in json.dumps(sink.pulses[0].to_payload()).casefold()


async def test_publisher_retries_exact_pending_pulse_and_tracks_ttl_health() -> None:
    now = [datetime(2026, 7, 21, 12, tzinfo=UTC)]
    sink = RecordingSink()
    publisher = RuntimeLivenessPublisher(
        runtime_id="owner-runtime",
        sink=sink,
        interval_seconds=60,
        expires_after_seconds=180,
        boot_id_factory=lambda: "boot-1",
        clock=lambda: now[0],
    )
    assert (await publisher.check()).status is RuntimeLivenessStatus.HEALTHY

    now[0] += timedelta(seconds=60)
    sink.fail = True
    degraded = await publisher.check()
    failed_pulse = sink.pulses[-1]

    now[0] += timedelta(seconds=59)
    assert (await publisher.check()).status is RuntimeLivenessStatus.DEGRADED
    assert len(sink.pulses) == 2

    now[0] += timedelta(seconds=1)
    assert (await publisher.check()).status is RuntimeLivenessStatus.DEGRADED
    assert sink.pulses[-1] == failed_pulse

    now[0] += timedelta(seconds=60)
    assert (await publisher.check()).status is RuntimeLivenessStatus.FAILED
    assert sink.pulses[-1] == failed_pulse

    sink.fail = False
    now[0] += timedelta(seconds=60)
    recovered = await publisher.check()

    assert degraded.status is RuntimeLivenessStatus.DEGRADED
    assert recovered.status is RuntimeLivenessStatus.HEALTHY
    assert sink.pulses[-1] == failed_pulse


async def test_publisher_freezes_alert_delivery_signal_until_pulse_ack() -> None:
    now = [datetime(2026, 7, 21, 12, tzinfo=UTC)]
    sink = RecordingSink(fail=True)
    publisher = RuntimeLivenessPublisher(
        runtime_id="owner-runtime",
        sink=sink,
        interval_seconds=60,
        expires_after_seconds=180,
        boot_id_factory=lambda: "boot-1",
        clock=lambda: now[0],
    )

    await publisher.check(alert_delivery_status=RuntimeAlertDeliverySignal.PENDING)
    pending = sink.pulses[0]
    sink.fail = False
    now[0] += timedelta(seconds=60)
    await publisher.check(alert_delivery_status=RuntimeAlertDeliverySignal.HEALTHY)
    now[0] += timedelta(seconds=60)
    await publisher.check(alert_delivery_status=RuntimeAlertDeliverySignal.HEALTHY)

    assert sink.pulses[1] == pending
    assert pending.alert_delivery_status is RuntimeAlertDeliverySignal.PENDING
    assert sink.pulses[2].alert_delivery_status is RuntimeAlertDeliverySignal.HEALTHY


async def test_publisher_first_failure_is_failed_and_new_process_uses_new_boot() -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    failed_sink = RecordingSink(fail=True)
    failed = RuntimeLivenessPublisher(
        runtime_id="owner-runtime",
        sink=failed_sink,
        interval_seconds=60,
        expires_after_seconds=180,
        boot_id_factory=lambda: "boot-1",
        clock=lambda: now,
    )
    replacement_sink = RecordingSink()
    replacement = RuntimeLivenessPublisher(
        runtime_id="owner-runtime",
        sink=replacement_sink,
        interval_seconds=60,
        expires_after_seconds=180,
        boot_id_factory=lambda: "boot-2",
        clock=lambda: now,
    )

    assert (await failed.check()).status is RuntimeLivenessStatus.FAILED
    assert (await replacement.check()).status is RuntimeLivenessStatus.HEALTHY
    assert replacement_sink.pulses[0].boot_id == "boot-2"
    assert replacement_sink.pulses[0].sequence == 1


async def test_webhook_uses_stable_idempotency_key_and_redacts_transport_secrets() -> None:
    requests: list[httpx.Request] = []

    async def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202)

    pulse = _pulse(sequence=3)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    sink = WebhookRuntimeLivenessSink(
        url="https://receiver.example.test/private-path",
        bearer_token="super-secret-token",
        client=client,
    )
    try:
        await sink.send(pulse)
        await sink.send(pulse)
    finally:
        await client.aclose()

    expected_key = "runtime-liveness:owner-runtime:boot-1:3"
    assert [request.headers["Idempotency-Key"] for request in requests] == [
        expected_key,
        expected_key,
    ]
    assert requests[0].headers["Authorization"] == "Bearer super-secret-token"
    assert json.loads(requests[0].content) == pulse.to_payload()
    rendered = json.dumps(pulse.to_payload())
    assert "receiver.example.test" not in rendered
    assert "super-secret-token" not in rendered


def test_pulse_rejects_extra_secret_fields_and_unsafe_runtime_identity() -> None:
    with pytest.raises(ValidationError):
        RuntimeLivenessPulse.model_validate({**_pulse().model_dump(), "token": "secret"})
    with pytest.raises(ValidationError):
        RuntimeLivenessPulse.model_validate(
            {**_pulse().model_dump(), "runtime_id": "/Users/private/runtime"}
        )


def test_receiver_opens_once_after_ttl_and_resolves_once_on_valid_recovery() -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    tracker = RuntimeLivenessTracker()
    tracker.arm("owner-runtime", armed_at=now, expires_after_seconds=180)

    accepted = tracker.accept(_pulse(), received_at=now)
    fresh = tracker.check("owner-runtime", now=now + timedelta(seconds=179))
    opened = tracker.check("owner-runtime", now=now + timedelta(seconds=180))
    repeated = tracker.check("owner-runtime", now=now + timedelta(seconds=240))
    resolved = tracker.accept(
        _pulse(sequence=2, sent_at=now + timedelta(seconds=240)),
        received_at=now + timedelta(seconds=240),
    )
    healthy = tracker.check("owner-runtime", now=now + timedelta(seconds=241))

    assert accepted.status is RuntimeLivenessReceiverStatus.HEALTHY
    assert accepted.transition is RuntimeLivenessTransition.NONE
    assert fresh.status is RuntimeLivenessReceiverStatus.HEALTHY
    assert opened.status is RuntimeLivenessReceiverStatus.STALE
    assert opened.transition is RuntimeLivenessTransition.OUTAGE_OPENED
    assert repeated.transition is RuntimeLivenessTransition.NONE
    assert resolved.status is RuntimeLivenessReceiverStatus.HEALTHY
    assert resolved.transition is RuntimeLivenessTransition.OUTAGE_RESOLVED
    assert healthy.transition is RuntimeLivenessTransition.NONE


def test_receiver_orders_but_does_not_renew_unhealthy_alert_delivery_pulses() -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    tracker = RuntimeLivenessTracker()
    tracker.arm("owner-runtime", armed_at=now, expires_after_seconds=180)
    tracker.accept(_pulse(), received_at=now)

    blocked = tracker.accept(
        _pulse(
            sequence=2,
            sent_at=now + timedelta(seconds=60),
            alert_delivery_status=RuntimeAlertDeliverySignal.PENDING,
        ),
        received_at=now + timedelta(seconds=60),
    )
    opened = tracker.accept(
        _pulse(
            sequence=3,
            sent_at=now + timedelta(seconds=180),
            alert_delivery_status=RuntimeAlertDeliverySignal.FAILED,
        ),
        received_at=now + timedelta(seconds=180),
    )
    resolved = tracker.accept(
        _pulse(
            sequence=4,
            sent_at=now + timedelta(seconds=181),
            alert_delivery_status=RuntimeAlertDeliverySignal.HEALTHY,
        ),
        received_at=now + timedelta(seconds=181),
    )

    assert blocked.accepted is True
    assert blocked.status is RuntimeLivenessReceiverStatus.HEALTHY
    assert opened.transition is RuntimeLivenessTransition.OUTAGE_OPENED
    assert opened.status is RuntimeLivenessReceiverStatus.STALE
    assert resolved.transition is RuntimeLivenessTransition.OUTAGE_RESOLVED


def test_receiver_rejects_duplicates_and_old_boot_but_accepts_replacement_boot() -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    tracker = RuntimeLivenessTracker()
    tracker.arm("owner-runtime", armed_at=now, expires_after_seconds=180)
    tracker.accept(_pulse(sequence=2), received_at=now)

    duplicate = tracker.accept(_pulse(sequence=2), received_at=now + timedelta(seconds=1))
    older_sequence = tracker.accept(
        _pulse(sequence=1, sent_at=now + timedelta(seconds=2)),
        received_at=now + timedelta(seconds=2),
    )
    replacement = tracker.accept(
        _pulse(boot_id="boot-2", sent_at=now + timedelta(seconds=3)),
        received_at=now + timedelta(seconds=3),
    )
    delayed_old_boot = tracker.accept(
        _pulse(boot_id="boot-1", sequence=99, sent_at=now + timedelta(seconds=2)),
        received_at=now + timedelta(seconds=4),
    )

    assert duplicate.accepted is False
    assert older_sequence.accepted is False
    assert replacement.accepted is True
    assert delayed_old_boot.accepted is False


def test_receiver_requires_explicit_arm_and_disarm_suppresses_stale_transition() -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    tracker = RuntimeLivenessTracker()

    ignored = tracker.accept(_pulse(), received_at=now)
    tracker.arm("owner-runtime", armed_at=now, expires_after_seconds=180)
    tracker.accept(_pulse(), received_at=now)
    tracker.disarm("owner-runtime")
    disarmed = tracker.check("owner-runtime", now=now + timedelta(hours=1))
    delayed = tracker.accept(_pulse(sequence=2), received_at=now + timedelta(hours=1))

    assert ignored.status is RuntimeLivenessReceiverStatus.UNARMED
    assert ignored.accepted is False
    assert disarmed.status is RuntimeLivenessReceiverStatus.UNARMED
    assert disarmed.transition is RuntimeLivenessTransition.NONE
    assert delayed.accepted is False


def test_receiver_opens_when_armed_runtime_never_sends_first_pulse() -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    tracker = RuntimeLivenessTracker()
    tracker.arm("owner-runtime", armed_at=now, expires_after_seconds=180)

    fresh = tracker.check("owner-runtime", now=now + timedelta(seconds=179))
    opened = tracker.check("owner-runtime", now=now + timedelta(seconds=180))
    resolved = tracker.accept(
        _pulse(sent_at=now + timedelta(seconds=181)),
        received_at=now + timedelta(seconds=181),
    )

    assert fresh.status is RuntimeLivenessReceiverStatus.HEALTHY
    assert opened.transition is RuntimeLivenessTransition.OUTAGE_OPENED
    assert resolved.transition is RuntimeLivenessTransition.OUTAGE_RESOLVED


def _pulse(
    *,
    boot_id: str = "boot-1",
    sequence: int = 1,
    sent_at: datetime | None = None,
    alert_delivery_status: RuntimeAlertDeliverySignal = RuntimeAlertDeliverySignal.DISABLED,
) -> RuntimeLivenessPulse:
    return RuntimeLivenessPulse(
        runtime_id="owner-runtime",
        boot_id=boot_id,
        sequence=sequence,
        sent_at=sent_at or datetime(2026, 7, 21, 12, tzinfo=UTC),
        interval_seconds=60,
        expires_after_seconds=180,
        alert_delivery_status=alert_delivery_status,
    )
