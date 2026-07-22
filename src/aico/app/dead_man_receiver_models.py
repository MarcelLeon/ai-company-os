"""Domain models for the independently deployed dead-man receiver."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aico.app.runtime_liveness import (
    RuntimeAlertDeliverySignal,
    RuntimeLivenessReceiverStatus,
)


class DeadManEventType(StrEnum):
    OUTAGE_OPENED = "outage_opened"
    OUTAGE_RESOLVED = "outage_resolved"


class DeadManOutageReason(StrEnum):
    PULSE_EXPIRED = "pulse_expired"
    ALERT_DELIVERY_UNHEALTHY = "alert_delivery_unhealthy"


class DeadManPulseReason(StrEnum):
    ACCEPTED = "accepted"
    ACCEPTED_WITHOUT_RENEWAL = "accepted_without_renewal"
    DUPLICATE_OR_OLDER = "duplicate_or_older"


class DeadManDeliveryStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    PENDING = "pending"
    FAILED = "failed"


class DeadManNotificationRouteStatus(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"


class DeadManNotificationProbeContract(StrEnum):
    DISABLED = "disabled"
    SILENT_ROUTE_PROBE_V1 = "silent-route-probe-v1"


class DeadManRouteObservationSource(StrEnum):
    OUTAGE_DELIVERY = "outage_delivery"
    SILENT_PROBE = "silent_probe"


class DeadManRouteHealthEventType(StrEnum):
    ROUTE_DEGRADED = "notification_route_degraded"
    ROUTE_RECOVERED = "notification_route_recovered"


class DeadManNotificationAttemptResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    acknowledged_routes: tuple[bool, ...] = Field(min_length=1, max_length=2)

    @property
    def acknowledgement_count(self) -> int:
        return sum(self.acknowledged_routes)


class DeadManNotificationPolicySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    configured_routes: int = Field(ge=1, le=2)
    minimum_acknowledgements: int = Field(ge=1, le=2)
    updated_at: datetime

    @model_validator(mode="after")
    def require_possible_aware_policy(self) -> Self:
        if self.minimum_acknowledgements > self.configured_routes:
            raise ValueError("notification quorum cannot exceed configured routes")
        if self.updated_at.tzinfo is None:
            raise ValueError("notification policy timestamp must be timezone-aware")
        return self


class DeadManEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    outage_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    event_type: DeadManEventType
    runtime_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    reason: DeadManOutageReason = DeadManOutageReason.PULSE_EXPIRED
    occurred_at: datetime
    detected_at: datetime

    @model_validator(mode="after")
    def require_aware_ordered_times(self) -> Self:
        if self.occurred_at.tzinfo is None or self.detected_at.tzinfo is None:
            raise ValueError("dead-man event timestamps must be timezone-aware")
        if self.detected_at < self.occurred_at:
            raise ValueError("dead-man event detection cannot precede occurrence")
        return self

    def to_payload(self) -> dict[str, object]:
        return {"schema_version": 2, **self.model_dump(mode="json")}


class DeadManRouteHealthEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    event_type: DeadManRouteHealthEventType
    route_slot: int = Field(ge=1, le=2)
    triggering_event_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    runtime_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    observation_source: DeadManRouteObservationSource = (
        DeadManRouteObservationSource.OUTAGE_DELIVERY
    )
    acknowledged_routes: tuple[bool, ...] | None = Field(
        default=None,
        min_length=1,
        max_length=2,
    )
    occurred_at: datetime

    @model_validator(mode="after")
    def require_aware_time(self) -> Self:
        if self.occurred_at.tzinfo is None:
            raise ValueError("route health event timestamp must be timezone-aware")
        if self.observation_source is DeadManRouteObservationSource.SILENT_PROBE:
            if self.runtime_id != "receiver-notification-routes":
                raise ValueError("silent probe route health event runtime is invalid")
            if self.acknowledged_routes is None:
                raise ValueError("silent probe route health event requires route acknowledgements")
            if len(self.acknowledged_routes) != 2:
                raise ValueError("silent probe route health event requires two route results")
            acknowledged = self.acknowledged_routes[self.route_slot - 1]
            if self.event_type is DeadManRouteHealthEventType.ROUTE_DEGRADED and acknowledged:
                raise ValueError("degraded probe route cannot be acknowledged")
            if self.event_type is DeadManRouteHealthEventType.ROUTE_RECOVERED and not acknowledged:
                raise ValueError("recovered probe route requires acknowledgement")
        elif self.acknowledged_routes is not None:
            raise ValueError("outage route health event cannot carry probe acknowledgements")
        return self

    def to_payload(self) -> dict[str, object]:
        return {"schema_version": 1, **self.model_dump(mode="json")}


class DeadManNotificationProbeEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(pattern=r"^rp-[a-f0-9]{32}$")
    event_type: Literal["notification_route_probe"] = "notification_route_probe"
    contract: Literal["silent-route-probe-v1"] = "silent-route-probe-v1"
    scheduled_at: datetime

    @model_validator(mode="after")
    def require_aware_time(self) -> Self:
        if self.scheduled_at.tzinfo is None:
            raise ValueError("notification probe timestamp must be timezone-aware")
        return self

    def to_payload(self) -> dict[str, object]:
        return {"schema_version": 1, **self.model_dump(mode="json")}


DeadManOutboundEvent = DeadManEvent | DeadManRouteHealthEvent | DeadManNotificationProbeEvent


class DeadManMonitorSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    status: RuntimeLivenessReceiverStatus
    expires_after_seconds: int = Field(gt=0)
    armed_at: datetime
    last_received_at: datetime | None = None
    last_pulse_received_at: datetime | None = None
    alert_delivery_status: RuntimeAlertDeliverySignal = RuntimeAlertDeliverySignal.DISABLED
    expires_at: datetime
    last_sequence: int | None = Field(default=None, ge=1)
    outage_id: str | None = None
    outage_reason: DeadManOutageReason | None = None

    @model_validator(mode="after")
    def require_complete_outage_checkpoint(self) -> Self:
        if (self.outage_id is None) != (self.outage_reason is None):
            raise ValueError("dead-man monitor outage reason checkpoint is partial")
        return self


class DeadManPulseReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted: bool
    reason: DeadManPulseReason
    status: RuntimeLivenessReceiverStatus
    renewed: bool = False
    outage_resolved: bool = False


class DeadManDeliverySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: DeadManDeliveryStatus
    checked_at: datetime
    pending_events: int | None = Field(default=None, ge=0)
    pending_route_health_alerts: int = Field(default=0, ge=0)
    degraded_routes: int = Field(default=0, ge=0, le=2)
    suspect_routes: int = Field(default=0, ge=0, le=2)
    notification_probe_enabled: bool = False
    notification_probe_pending: bool = False
    notification_probe_fresh: bool = False


class DeadManNotificationProbeSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: DeadManNotificationProbeContract
    interval_seconds: int = Field(ge=60)
    failure_threshold: int = Field(ge=2, le=10)
    max_age_seconds: int = Field(ge=120)
    pending_probe: DeadManNotificationProbeEvent | None = None
    next_probe_at: datetime | None = None
    last_completed_at: datetime | None = None
    last_acknowledged_routes: tuple[bool, ...] | None = Field(
        default=None,
        min_length=2,
        max_length=2,
    )
    updated_at: datetime

    @model_validator(mode="after")
    def require_consistent_aware_checkpoint(self) -> Self:
        timestamps = (self.next_probe_at, self.last_completed_at, self.updated_at)
        if any(value is not None and value.tzinfo is None for value in timestamps):
            raise ValueError("notification probe timestamps must be timezone-aware")
        if self.max_age_seconds < self.interval_seconds * 2:
            raise ValueError("notification probe max age must cover two intervals")
        if self.contract is DeadManNotificationProbeContract.DISABLED:
            if self.pending_probe is not None or self.next_probe_at is not None:
                raise ValueError("disabled notification probe cannot retain work")
        elif self.next_probe_at is None:
            raise ValueError("enabled notification probe requires next schedule")
        if (self.last_completed_at is None) != (self.last_acknowledged_routes is None):
            raise ValueError("notification probe completion checkpoint is partial")
        return self

    def is_fresh(self, *, at: datetime) -> bool:
        if at.tzinfo is None:
            raise ValueError("notification probe freshness time must be timezone-aware")
        if self.contract is DeadManNotificationProbeContract.DISABLED:
            return False
        anchor = self.last_completed_at or self.updated_at
        return at <= anchor + timedelta(seconds=self.max_age_seconds)


class DeadManNotificationRouteSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    route_slot: int = Field(ge=1, le=2)
    status: DeadManNotificationRouteStatus
    consecutive_failures: int = Field(ge=0)
    consecutive_probe_failures: int = Field(ge=0)
    last_attempt_at: datetime | None = None
    last_acknowledged_at: datetime | None = None
    last_probe_at: datetime | None = None
    last_probe_acknowledged_at: datetime | None = None
    updated_at: datetime

    @model_validator(mode="after")
    def require_consistent_aware_checkpoint(self) -> Self:
        timestamps = (
            self.last_attempt_at,
            self.last_acknowledged_at,
            self.last_probe_at,
            self.last_probe_acknowledged_at,
            self.updated_at,
        )
        if any(value is not None and value.tzinfo is None for value in timestamps):
            raise ValueError("notification route timestamps must be timezone-aware")
        if self.status is DeadManNotificationRouteStatus.UNKNOWN:
            if self.consecutive_failures != 0:
                raise ValueError("unknown notification route cannot have confirmed failure")
            if self.consecutive_probe_failures == 0 and self.last_attempt_at is not None:
                raise ValueError("unknown notification route attempt is not explained by probe")
            if self.consecutive_probe_failures > 0 and self.last_probe_at is None:
                raise ValueError("unknown notification route probe failure lacks attempt")
        elif self.last_attempt_at is None:
            raise ValueError("observed notification route requires last attempt")
        if self.status is DeadManNotificationRouteStatus.HEALTHY:
            if self.consecutive_failures != 0 or self.last_acknowledged_at is None:
                raise ValueError("healthy notification route requires acknowledgement")
        if self.status is DeadManNotificationRouteStatus.DEGRADED:
            if self.consecutive_failures <= 0:
                raise ValueError("degraded notification route requires failure")
        if (
            self.last_attempt_at is not None
            and self.last_acknowledged_at is not None
            and self.last_acknowledged_at > self.last_attempt_at
        ):
            raise ValueError("route acknowledgement cannot follow its latest attempt")
        if (self.last_probe_at is None) != (self.last_probe_acknowledged_at is None):
            if self.last_probe_acknowledged_at is not None:
                raise ValueError("probe acknowledgement requires probe attempt")
        if (
            self.last_probe_at is not None
            and self.last_probe_acknowledged_at is not None
            and self.last_probe_acknowledged_at > self.last_probe_at
        ):
            raise ValueError("probe acknowledgement cannot follow its latest attempt")
        return self


class DeadManEvidenceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    event_type: DeadManEventType
    reason: DeadManOutageReason = DeadManOutageReason.PULSE_EXPIRED
    occurred_at: datetime
    detected_at: datetime
    delivered: bool
    delivery_attempts: int = Field(ge=0)
    next_attempt_at: datetime | None = None
    configured_routes: int = Field(ge=1, le=2)
    minimum_acknowledgements: int = Field(ge=1, le=2)
    acknowledged_routes: tuple[bool, ...] | None = Field(
        default=None,
        min_length=1,
        max_length=2,
    )
    last_attempt_at: datetime | None = None

    @model_validator(mode="after")
    def require_consistent_times_and_delivery(self) -> Self:
        if self.occurred_at.tzinfo is None or self.detected_at.tzinfo is None:
            raise ValueError("dead-man evidence timestamps must be timezone-aware")
        if self.detected_at < self.occurred_at:
            raise ValueError("dead-man evidence detection cannot precede occurrence")
        if self.next_attempt_at is not None and self.next_attempt_at.tzinfo is None:
            raise ValueError("dead-man retry timestamp must be timezone-aware")
        if self.delivered and self.next_attempt_at is not None:
            raise ValueError("delivered dead-man evidence cannot retain a next attempt")
        if self.minimum_acknowledgements > self.configured_routes:
            raise ValueError("event notification quorum cannot exceed configured routes")
        if self.acknowledged_routes is not None:
            if len(self.acknowledged_routes) != self.configured_routes:
                raise ValueError("event route acknowledgements must match configured routes")
            if self.last_attempt_at is None:
                raise ValueError("event route acknowledgements require attempt time")
            if self.delivered and sum(self.acknowledged_routes) < self.minimum_acknowledgements:
                raise ValueError("delivered event did not meet frozen notification quorum")
        if (self.acknowledged_routes is None) != (self.last_attempt_at is None):
            raise ValueError("event route attempt checkpoint is partial")
        if self.last_attempt_at is not None and self.last_attempt_at.tzinfo is None:
            raise ValueError("event attempt timestamp must be timezone-aware")
        return self


class DeadManRouteHealthEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    event_type: DeadManRouteHealthEventType
    route_slot: int = Field(ge=1, le=2)
    triggering_event_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    runtime_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    observation_source: DeadManRouteObservationSource = (
        DeadManRouteObservationSource.OUTAGE_DELIVERY
    )
    acknowledged_routes: tuple[bool, ...] | None = Field(
        default=None,
        min_length=1,
        max_length=2,
    )
    occurred_at: datetime
    delivered: bool
    delivery_attempts: int = Field(ge=0)
    next_attempt_at: datetime | None = None

    @model_validator(mode="after")
    def require_consistent_delivery(self) -> Self:
        if self.occurred_at.tzinfo is None:
            raise ValueError("route health evidence timestamp must be timezone-aware")
        if self.next_attempt_at is not None and self.next_attempt_at.tzinfo is None:
            raise ValueError("route health retry timestamp must be timezone-aware")
        if self.delivered and self.next_attempt_at is not None:
            raise ValueError("delivered route health evidence cannot retain retry time")
        DeadManRouteHealthEvent(
            event_id=self.event_id,
            event_type=self.event_type,
            route_slot=self.route_slot,
            triggering_event_id=self.triggering_event_id,
            runtime_id=self.runtime_id,
            observation_source=self.observation_source,
            acknowledged_routes=self.acknowledged_routes,
            occurred_at=self.occurred_at,
        )
        return self


class DeadManOutageEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outage_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    opened: DeadManEvidenceEvent
    resolved: DeadManEvidenceEvent | None = None

    @model_validator(mode="after")
    def require_opened_then_optional_resolved(self) -> Self:
        if self.opened.event_type is not DeadManEventType.OUTAGE_OPENED:
            raise ValueError("dead-man outage evidence must begin with opened")
        if self.resolved is None:
            return self
        if self.resolved.event_type is not DeadManEventType.OUTAGE_RESOLVED:
            raise ValueError("dead-man outage evidence must end with resolved")
        if self.resolved.event_id == self.opened.event_id:
            raise ValueError("dead-man outage evidence event identities must differ")
        if self.resolved.occurred_at < self.opened.occurred_at:
            raise ValueError("dead-man outage resolution cannot precede opening")
        if self.resolved.delivered and not self.opened.delivered:
            raise ValueError("dead-man resolved delivery cannot overtake opened")
        if self.resolved.reason is not self.opened.reason:
            raise ValueError("dead-man outage reason cannot change before resolution")
        return self


class DeadManEvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[5] = 5
    runtime_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    generated_at: datetime
    notification_policy: DeadManNotificationPolicySnapshot
    notification_probe: DeadManNotificationProbeSnapshot
    notification_probe_fresh: bool
    notification_routes: tuple[DeadManNotificationRouteSnapshot, ...]
    monitor: DeadManMonitorSnapshot | None = None
    outages: tuple[DeadManOutageEvidence, ...] = ()
    route_health_alerts: tuple[DeadManRouteHealthEvidence, ...] = ()

    @model_validator(mode="after")
    def require_single_runtime_unique_ordered_evidence(self) -> Self:
        if self.generated_at.tzinfo is None:
            raise ValueError("dead-man evidence generation time must be timezone-aware")
        if self.notification_policy.updated_at > self.generated_at:
            raise ValueError("dead-man evidence cannot predate notification policy")
        if self.notification_probe.updated_at > self.generated_at:
            raise ValueError("dead-man evidence cannot predate notification probe policy")
        if (
            self.notification_probe.last_completed_at is not None
            and self.notification_probe.last_completed_at > self.generated_at
        ):
            raise ValueError("dead-man evidence cannot predate notification probe completion")
        if self.notification_probe_fresh != self.notification_probe.is_fresh(at=self.generated_at):
            raise ValueError("dead-man evidence notification probe freshness is invalid")
        expected_slots = tuple(range(1, self.notification_policy.configured_routes + 1))
        if tuple(route.route_slot for route in self.notification_routes) != expected_slots:
            raise ValueError("notification route evidence does not match current policy")
        if any(route.updated_at > self.generated_at for route in self.notification_routes):
            raise ValueError("dead-man evidence cannot predate route health")
        if self.monitor is not None and self.monitor.runtime_id != self.runtime_id:
            raise ValueError("dead-man evidence monitor runtime mismatch")
        outage_ids: set[str] = set()
        event_by_id: dict[str, DeadManEvidenceEvent] = {}
        previous_detected_at: datetime | None = None
        for outage in self.outages:
            if outage.outage_id in outage_ids:
                raise ValueError("duplicate dead-man outage evidence")
            outage_ids.add(outage.outage_id)
            for event in (outage.opened, outage.resolved):
                if event is None:
                    continue
                if event.event_id in event_by_id:
                    raise ValueError("duplicate dead-man event evidence")
                event_by_id[event.event_id] = event
                if previous_detected_at is not None and event.detected_at < previous_detected_at:
                    raise ValueError("dead-man evidence events must be chronological")
                if event.detected_at > self.generated_at:
                    raise ValueError("dead-man evidence cannot be generated before detection")
                previous_detected_at = event.detected_at
        alert_ids: set[str] = set()
        for alert in self.route_health_alerts:
            if alert.observation_source is DeadManRouteObservationSource.OUTAGE_DELIVERY:
                if alert.runtime_id != self.runtime_id:
                    raise ValueError("route health evidence runtime mismatch")
                trigger = event_by_id.get(alert.triggering_event_id)
                if trigger is None:
                    raise ValueError("route health evidence trigger is outside outage evidence")
                if alert.route_slot > trigger.configured_routes:
                    raise ValueError("route health evidence route exceeds triggering policy")
            elif alert.runtime_id != "receiver-notification-routes":
                raise ValueError("silent probe route health evidence runtime mismatch")
            if alert.event_id in alert_ids:
                raise ValueError("duplicate route health evidence")
            alert_ids.add(alert.event_id)
            if alert.occurred_at > self.generated_at:
                raise ValueError("dead-man evidence cannot predate route health alert")
        return self

    @property
    def complete_outage_count(self) -> int:
        return sum(outage.resolved is not None for outage in self.outages)
