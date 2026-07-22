"""Ephemeral runtime pulses for an independently deployed dead-man receiver."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Literal, Protocol, Self
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

log = logging.getLogger(__name__)


class RuntimeLivenessStatus(StrEnum):
    DISABLED = "disabled"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class RuntimeLivenessReceiverStatus(StrEnum):
    UNARMED = "unarmed"
    HEALTHY = "healthy"
    STALE = "stale"


class RuntimeLivenessTransition(StrEnum):
    NONE = "none"
    OUTAGE_OPENED = "outage_opened"
    OUTAGE_RESOLVED = "outage_resolved"


class RuntimeAlertDeliverySignal(StrEnum):
    DISABLED = "disabled"
    HEALTHY = "healthy"
    PENDING = "pending"
    FAILED = "failed"

    @property
    def renews_monitor(self) -> bool:
        return self in {self.DISABLED, self.HEALTHY}


class RuntimeLivenessPulse(BaseModel):
    """Strict, secret-free pulse accepted by a remote receiver."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: Literal["runtime_liveness_pulse"] = "runtime_liveness_pulse"
    runtime_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    boot_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    sequence: int = Field(ge=1)
    sent_at: datetime
    interval_seconds: int = Field(ge=1)
    expires_after_seconds: int = Field(ge=1)
    alert_delivery_status: RuntimeAlertDeliverySignal = RuntimeAlertDeliverySignal.DISABLED

    @field_validator("sent_at")
    @classmethod
    def require_aware_sent_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("runtime liveness sent_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_bounded_ttl(self) -> Self:
        if self.expires_after_seconds < self.interval_seconds * 3:
            raise ValueError("runtime liveness TTL must be at least three intervals")
        return self

    @property
    def idempotency_key(self) -> str:
        return f"runtime-liveness:{self.runtime_id}:{self.boot_id}:{self.sequence}"

    def to_payload(self) -> dict[str, object]:
        return {"schema_version": 2, **self.model_dump(mode="json")}

    @property
    def renews_monitor(self) -> bool:
        return self.alert_delivery_status.renews_monitor


class RuntimeLivenessSink(Protocol):
    async def send(self, pulse: RuntimeLivenessPulse) -> None: ...


class WebhookRuntimeLivenessSink:
    """Send liveness pulses to an owner-configured HTTPS receiver."""

    def __init__(
        self,
        *,
        url: str,
        bearer_token: str | None = None,
        timeout_seconds: float = 5,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        parsed_url = httpx.URL(url)
        if parsed_url.scheme != "https" or parsed_url.host is None:
            raise ValueError("runtime liveness webhook URL must use HTTPS")
        if timeout_seconds <= 0:
            raise ValueError("runtime liveness webhook timeout must be positive")
        self._url = url
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def send(self, pulse: RuntimeLivenessPulse) -> None:
        headers = {"Idempotency-Key": pulse.idempotency_key}
        if self._bearer_token is not None:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        if self._client is not None:
            await self._post(self._client, pulse, headers)
            return
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            await self._post(client, pulse, headers)

    async def _post(
        self,
        client: httpx.AsyncClient,
        pulse: RuntimeLivenessPulse,
        headers: dict[str, str],
    ) -> None:
        response = await client.post(
            self._url,
            json=pulse.to_payload(),
            headers=headers,
        )
        response.raise_for_status()


class RuntimeLivenessSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: RuntimeLivenessStatus
    checked_at: datetime
    last_success_at: datetime | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def require_consistent_delivery_window(self) -> Self:
        for field_name, value in (
            ("checked_at", self.checked_at),
            ("last_success_at", self.last_success_at),
            ("expires_at", self.expires_at),
        ):
            if value is not None and value.tzinfo is None:
                raise ValueError(f"runtime liveness {field_name} must be timezone-aware")
        last_success = self.last_success_at
        expires_at = self.expires_at
        has_window = last_success is not None and expires_at is not None
        if (last_success is None) != (expires_at is None):
            raise ValueError("runtime liveness delivery window must be complete")
        if last_success is not None and expires_at is not None and expires_at <= last_success:
            raise ValueError("runtime liveness expiry must follow last success")
        if self.status in {RuntimeLivenessStatus.HEALTHY, RuntimeLivenessStatus.DEGRADED}:
            if not has_window:
                raise ValueError("runtime liveness success status requires a delivery window")
        if self.status is RuntimeLivenessStatus.DISABLED and has_window:
            raise ValueError("disabled runtime liveness cannot have a delivery window")
        if (
            self.status is RuntimeLivenessStatus.FAILED
            and expires_at is not None
            and self.checked_at < expires_at
        ):
            raise ValueError("failed runtime liveness window must be expired")
        return self

    def to_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class RuntimeLivenessPublisher:
    """Publish bounded ephemeral pulses without creating durable history."""

    def __init__(
        self,
        *,
        runtime_id: str,
        sink: RuntimeLivenessSink,
        interval_seconds: int,
        expires_after_seconds: int,
        clock: Callable[[], datetime] | None = None,
        boot_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("runtime liveness interval must be positive")
        if expires_after_seconds < interval_seconds * 3:
            raise ValueError("runtime liveness TTL must be at least three intervals")
        self._runtime_id = _validate_identity(runtime_id, field="runtime_id")
        self._sink = sink
        self._interval_seconds = interval_seconds
        self._expires_after_seconds = expires_after_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        factory = boot_id_factory or (lambda: str(uuid4()))
        self._boot_id = _validate_identity(factory(), field="boot_id")
        self._next_sequence = 1
        self._pending: RuntimeLivenessPulse | None = None
        self._retry_at: datetime | None = None
        self._next_pulse_at: datetime | None = None
        self._last_success_at: datetime | None = None

    async def check(
        self,
        *,
        alert_delivery_status: RuntimeAlertDeliverySignal = RuntimeAlertDeliverySignal.DISABLED,
    ) -> RuntimeLivenessSnapshot:
        now = self._clock()
        if self._pending is None and self._pulse_due(now):
            self._pending = self._new_pulse(now, alert_delivery_status=alert_delivery_status)
        if self._pending is not None and self._retry_due(now):
            await self._attempt_pending(now)
        return self._snapshot(now)

    def _pulse_due(self, now: datetime) -> bool:
        return self._next_pulse_at is None or now >= self._next_pulse_at

    def _retry_due(self, now: datetime) -> bool:
        return self._retry_at is None or now >= self._retry_at

    def _new_pulse(
        self,
        now: datetime,
        *,
        alert_delivery_status: RuntimeAlertDeliverySignal,
    ) -> RuntimeLivenessPulse:
        return RuntimeLivenessPulse(
            runtime_id=self._runtime_id,
            boot_id=self._boot_id,
            sequence=self._next_sequence,
            sent_at=now,
            interval_seconds=self._interval_seconds,
            expires_after_seconds=self._expires_after_seconds,
            alert_delivery_status=alert_delivery_status,
        )

    async def _attempt_pending(self, now: datetime) -> None:
        pulse = self._pending
        if pulse is None:
            return
        try:
            await self._sink.send(pulse)
        except Exception as exc:
            log.error(
                "Runtime liveness delivery failed: sequence=%s type=%s",
                pulse.sequence,
                type(exc).__name__,
            )
            delay = min(self._interval_seconds, 60)
            self._retry_at = now + timedelta(seconds=delay)
            return
        self._last_success_at = now
        self._next_sequence += 1
        self._pending = None
        self._retry_at = None
        self._next_pulse_at = now + timedelta(seconds=self._interval_seconds)

    def _snapshot(self, now: datetime) -> RuntimeLivenessSnapshot:
        last_success = self._last_success_at
        expires_at = (
            last_success + timedelta(seconds=self._expires_after_seconds)
            if last_success is not None
            else None
        )
        if last_success is None or (expires_at is not None and now >= expires_at):
            status = RuntimeLivenessStatus.FAILED
        elif self._pending is not None:
            status = RuntimeLivenessStatus.DEGRADED
        else:
            status = RuntimeLivenessStatus.HEALTHY
        return RuntimeLivenessSnapshot(
            status=status,
            checked_at=now,
            last_success_at=last_success,
            expires_at=expires_at,
        )


@dataclass(frozen=True)
class RuntimeLivenessObservation:
    status: RuntimeLivenessReceiverStatus
    transition: RuntimeLivenessTransition = RuntimeLivenessTransition.NONE
    accepted: bool = False


@dataclass(frozen=True)
class _ReceivedPulse:
    pulse: RuntimeLivenessPulse
    received_at: datetime

    @property
    def expires_at(self) -> datetime:
        return self.received_at + timedelta(seconds=self.pulse.expires_after_seconds)


@dataclass(frozen=True)
class _ArmedMonitor:
    armed_at: datetime
    expires_after_seconds: int

    @property
    def expires_at(self) -> datetime:
        return self.armed_at + timedelta(seconds=self.expires_after_seconds)


class RuntimeLivenessTracker:
    """Reference receiver state machine; deployment and persistence stay external."""

    def __init__(self) -> None:
        self._armed: dict[str, _ArmedMonitor] = {}
        self._received: dict[str, _ReceivedPulse] = {}
        self._ordered: dict[str, RuntimeLivenessPulse] = {}
        self._statuses: dict[str, RuntimeLivenessReceiverStatus] = {}

    def arm(
        self,
        runtime_id: str,
        *,
        armed_at: datetime,
        expires_after_seconds: int,
    ) -> None:
        identity = _validate_identity(runtime_id, field="runtime_id")
        _require_aware_datetime(armed_at, field="armed_at")
        if expires_after_seconds <= 0:
            raise ValueError("runtime liveness receiver TTL must be positive")
        self._armed[identity] = _ArmedMonitor(
            armed_at=armed_at,
            expires_after_seconds=expires_after_seconds,
        )
        self._received.pop(identity, None)
        self._ordered.pop(identity, None)
        self._statuses[identity] = RuntimeLivenessReceiverStatus.HEALTHY

    def disarm(self, runtime_id: str) -> None:
        self._armed.pop(runtime_id, None)
        self._received.pop(runtime_id, None)
        self._ordered.pop(runtime_id, None)
        self._statuses.pop(runtime_id, None)

    def accept(
        self,
        pulse: RuntimeLivenessPulse,
        *,
        received_at: datetime,
    ) -> RuntimeLivenessObservation:
        _require_aware_datetime(received_at, field="received_at")
        runtime_id = pulse.runtime_id
        monitor = self._armed.get(runtime_id)
        if monitor is None:
            return _unarmed_observation()
        if pulse.expires_after_seconds != monitor.expires_after_seconds:
            return RuntimeLivenessObservation(status=self._status(runtime_id))
        current = self._ordered.get(runtime_id)
        if current is not None and not _is_newer_pulse(pulse, current):
            return RuntimeLivenessObservation(status=self._status(runtime_id))
        expiry = self.check(runtime_id, now=received_at)
        was_stale = expiry.status is RuntimeLivenessReceiverStatus.STALE
        self._ordered[runtime_id] = pulse
        if not pulse.renews_monitor:
            return RuntimeLivenessObservation(
                status=self._status(runtime_id),
                transition=expiry.transition,
                accepted=True,
            )
        self._received[runtime_id] = _ReceivedPulse(pulse=pulse, received_at=received_at)
        self._statuses[runtime_id] = RuntimeLivenessReceiverStatus.HEALTHY
        transition = (
            RuntimeLivenessTransition.OUTAGE_RESOLVED
            if was_stale
            else RuntimeLivenessTransition.NONE
        )
        return RuntimeLivenessObservation(
            status=RuntimeLivenessReceiverStatus.HEALTHY,
            transition=transition,
            accepted=True,
        )

    def check(self, runtime_id: str, *, now: datetime) -> RuntimeLivenessObservation:
        _require_aware_datetime(now, field="now")
        monitor = self._armed.get(runtime_id)
        if monitor is None:
            return _unarmed_observation()
        received = self._received.get(runtime_id)
        expires_at = received.expires_at if received is not None else monitor.expires_at
        if now < expires_at:
            return RuntimeLivenessObservation(status=self._status(runtime_id))
        if self._status(runtime_id) is RuntimeLivenessReceiverStatus.STALE:
            return RuntimeLivenessObservation(status=RuntimeLivenessReceiverStatus.STALE)
        self._statuses[runtime_id] = RuntimeLivenessReceiverStatus.STALE
        return RuntimeLivenessObservation(
            status=RuntimeLivenessReceiverStatus.STALE,
            transition=RuntimeLivenessTransition.OUTAGE_OPENED,
        )

    def _status(self, runtime_id: str) -> RuntimeLivenessReceiverStatus:
        return self._statuses.get(runtime_id, RuntimeLivenessReceiverStatus.HEALTHY)


def disabled_runtime_liveness_snapshot(checked_at: datetime) -> RuntimeLivenessSnapshot:
    return RuntimeLivenessSnapshot(
        status=RuntimeLivenessStatus.DISABLED,
        checked_at=checked_at,
    )


def failed_runtime_liveness_snapshot(checked_at: datetime) -> RuntimeLivenessSnapshot:
    return RuntimeLivenessSnapshot(
        status=RuntimeLivenessStatus.FAILED,
        checked_at=checked_at,
    )


def _unarmed_observation() -> RuntimeLivenessObservation:
    return RuntimeLivenessObservation(status=RuntimeLivenessReceiverStatus.UNARMED)


def _is_newer_pulse(
    candidate: RuntimeLivenessPulse,
    current: RuntimeLivenessPulse,
) -> bool:
    if candidate.boot_id == current.boot_id:
        return candidate.sequence > current.sequence
    return candidate.sent_at >= current.sent_at


def _validate_identity(value: str, *, field: str) -> str:
    if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", value) is None:
        raise ValueError(f"unsafe runtime liveness {field}")
    return value


def _require_aware_datetime(value: datetime, *, field: str) -> None:
    if value.tzinfo is None:
        raise ValueError(f"runtime liveness {field} must be timezone-aware")
