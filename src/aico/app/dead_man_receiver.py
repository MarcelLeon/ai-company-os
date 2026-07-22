"""Durable notification delivery for an independent dead-man receiver."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Protocol

import httpx

from aico.app.dead_man_receiver_models import (
    DeadManDeliverySnapshot,
    DeadManDeliveryStatus,
    DeadManEvent,
    DeadManEventType,
    DeadManEvidenceBundle,
    DeadManEvidenceEvent,
    DeadManMonitorSnapshot,
    DeadManNotificationAttemptResult,
    DeadManNotificationPolicySnapshot,
    DeadManNotificationProbeContract,
    DeadManNotificationProbeEvent,
    DeadManNotificationProbeSnapshot,
    DeadManNotificationRouteSnapshot,
    DeadManNotificationRouteStatus,
    DeadManOutageEvidence,
    DeadManOutageReason,
    DeadManOutboundEvent,
    DeadManPulseReason,
    DeadManPulseReceipt,
    DeadManRouteHealthEvent,
    DeadManRouteHealthEventType,
    DeadManRouteHealthEvidence,
    DeadManRouteObservationSource,
)
from aico.app.dead_man_receiver_store import (
    DeadManMonitorConflictError,
    DeadManMonitorNotArmedError,
    DeadManNotificationPolicyConflictError,
    DeadManReceiverSchemaError,
    SQLiteDeadManReceiverStore,
)

log = logging.getLogger(__name__)

__all__ = [
    "DeadManDeliverySnapshot",
    "DeadManDeliveryStatus",
    "DeadManEvidenceBundle",
    "DeadManEvidenceEvent",
    "DeadManEvent",
    "DeadManEventType",
    "DeadManMonitorConflictError",
    "DeadManMonitorNotArmedError",
    "DeadManMonitorSnapshot",
    "DeadManNotificationAttemptResult",
    "DeadManNotificationProbeContract",
    "DeadManNotificationProbeEvent",
    "DeadManNotificationProbeSnapshot",
    "DeadManNotificationPolicyConflictError",
    "DeadManNotificationPolicySnapshot",
    "DeadManNotificationRouteSnapshot",
    "DeadManNotificationRouteStatus",
    "DeadManOutboundEvent",
    "DeadManNotificationQuorumError",
    "DeadManNotificationCoordinator",
    "DeadManNotificationSink",
    "DeadManOutageReason",
    "DeadManPulseReason",
    "DeadManPulseReceipt",
    "DeadManRouteHealthEvent",
    "DeadManRouteHealthEventType",
    "DeadManRouteHealthEvidence",
    "DeadManRouteObservationSource",
    "QuorumDeadManNotificationSink",
    "DeadManReceiverSchemaError",
    "DeadManOutageEvidence",
    "SQLiteDeadManReceiverStore",
    "WebhookDeadManNotificationSink",
]


class DeadManNotificationSink(Protocol):
    async def send(
        self,
        event: DeadManOutboundEvent,
    ) -> DeadManNotificationAttemptResult | None: ...


class DeadManNotificationQuorumError(RuntimeError):
    def __init__(self, result: DeadManNotificationAttemptResult) -> None:
        super().__init__("dead-man notification acknowledgement quorum missed")
        self.result = result


class WebhookDeadManNotificationSink:
    """Deliver vendor-neutral outage events through owner-configured HTTPS."""

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
            raise ValueError("dead-man notification webhook URL must use HTTPS")
        if timeout_seconds <= 0:
            raise ValueError("dead-man notification timeout must be positive")
        self._url = url
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def send(self, event: DeadManOutboundEvent) -> DeadManNotificationAttemptResult:
        headers = {"Idempotency-Key": event.event_id}
        if self._bearer_token is not None:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        if self._client is not None:
            await self._post(self._client, event, headers)
            return DeadManNotificationAttemptResult(acknowledged_routes=(True,))
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            await self._post(client, event, headers)
        return DeadManNotificationAttemptResult(acknowledged_routes=(True,))

    async def _post(
        self,
        client: httpx.AsyncClient,
        event: DeadManOutboundEvent,
        headers: dict[str, str],
    ) -> None:
        response = await client.post(
            self._url,
            json=event.to_payload(),
            headers=headers,
        )
        response.raise_for_status()


class QuorumDeadManNotificationSink:
    """Attempt independent routes concurrently and require a bounded ACK quorum."""

    def __init__(
        self,
        *,
        sinks: tuple[DeadManNotificationSink, ...],
        minimum_acknowledgements: int,
    ) -> None:
        if len(sinks) < 2:
            raise ValueError("notification quorum requires at least two routes")
        if minimum_acknowledgements <= 0:
            raise ValueError("notification quorum must be positive")
        if minimum_acknowledgements > len(sinks):
            raise ValueError("notification quorum cannot exceed route count")
        self._sinks = sinks
        self._minimum_acknowledgements = minimum_acknowledgements

    async def send(self, event: DeadManOutboundEvent) -> DeadManNotificationAttemptResult:
        results = await asyncio.gather(
            *(sink.send(event) for sink in self._sinks),
            return_exceptions=True,
        )
        result = DeadManNotificationAttemptResult(
            acknowledged_routes=tuple(
                not isinstance(route_result, BaseException) for route_result in results
            )
        )
        if result.acknowledgement_count < self._minimum_acknowledgements:
            raise DeadManNotificationQuorumError(result)
        return result


class DeadManNotificationCoordinator:
    """Evaluate monitor expiry and deliver immutable events in row order."""

    def __init__(
        self,
        *,
        store: SQLiteDeadManReceiverStore,
        sink: DeadManNotificationSink,
        batch_limit: int = 10,
    ) -> None:
        if batch_limit <= 0:
            raise ValueError("dead-man notification batch limit must be positive")
        self._store = store
        self._sink = sink
        self._batch_limit = batch_limit

    async def check(self, *, now: datetime) -> DeadManDeliverySnapshot:
        self._store.evaluate(now=now)
        failed = False
        for event in self._store.load_pending(limit=self._batch_limit, now=now):
            result: DeadManNotificationAttemptResult | None = None
            transport_succeeded = False
            try:
                result = await self._sink.send(event)
                transport_succeeded = True
            except DeadManNotificationQuorumError as exc:
                result = exc.result
            except Exception as exc:
                log.error(
                    "Dead-man notification failed: event_id=%s type=%s",
                    event.event_id,
                    type(exc).__name__,
                )
            settled = self._store.record_notification_attempt(
                event.event_id,
                acknowledged_routes=(result.acknowledged_routes if result is not None else None),
                transport_succeeded=transport_succeeded,
                attempted_at=now,
            )
            if not settled:
                failed = True
                break
        route_alert_failed = False if failed else await self._deliver_route_health_alerts(now=now)
        probe_failed = False
        if not failed and not route_alert_failed:
            probe_failed = await self._run_notification_probe(now=now)
            if not probe_failed:
                route_alert_failed = await self._deliver_route_health_alerts(now=now)
        pending = self._store.pending_count()
        pending_route_alerts = self._store.pending_route_health_alert_count()
        degraded_routes = self._store.degraded_notification_route_count()
        suspect_routes = self._store.suspect_notification_route_count()
        probe = self._store.get_notification_probe()
        probe_enabled = probe.contract is DeadManNotificationProbeContract.SILENT_ROUTE_PROBE_V1
        probe_fresh = probe.is_fresh(at=now)
        active_suspect_routes = suspect_routes if probe_enabled else 0
        if failed or route_alert_failed or probe_failed or (probe_enabled and not probe_fresh):
            status = DeadManDeliveryStatus.FAILED
        elif pending > 0 or pending_route_alerts > 0 or active_suspect_routes > 0:
            status = DeadManDeliveryStatus.PENDING
        elif degraded_routes > 0:
            status = DeadManDeliveryStatus.DEGRADED
        else:
            status = DeadManDeliveryStatus.HEALTHY
        return DeadManDeliverySnapshot(
            status=status,
            checked_at=now,
            pending_events=pending,
            pending_route_health_alerts=pending_route_alerts,
            degraded_routes=degraded_routes,
            suspect_routes=active_suspect_routes,
            notification_probe_enabled=probe_enabled,
            notification_probe_pending=probe.pending_probe is not None,
            notification_probe_fresh=probe_fresh,
        )

    async def _run_notification_probe(self, *, now: datetime) -> bool:
        event = self._store.ensure_notification_probe_due(now=now)
        if event is None:
            return False
        result: DeadManNotificationAttemptResult | None = None
        transport_succeeded = False
        try:
            result = await self._sink.send(event)
            transport_succeeded = True
        except DeadManNotificationQuorumError as exc:
            result = exc.result
        except Exception as exc:
            log.error(
                "Dead-man notification probe failed: event_id=%s type=%s",
                event.event_id,
                type(exc).__name__,
            )
        self._store.record_notification_probe_attempt(
            event.event_id,
            acknowledged_routes=(result.acknowledged_routes if result is not None else None),
            transport_succeeded=transport_succeeded,
            attempted_at=now,
        )
        return (result is None and not transport_succeeded) or (
            result is not None and result.acknowledgement_count == 0
        )

    async def _deliver_route_health_alerts(self, *, now: datetime) -> bool:
        for event in self._store.load_pending_route_health_alerts(
            limit=self._batch_limit,
            now=now,
        ):
            result: DeadManNotificationAttemptResult | None = None
            transport_succeeded = False
            try:
                result = await self._sink.send(event)
                transport_succeeded = True
            except DeadManNotificationQuorumError as exc:
                result = exc.result
            except Exception as exc:
                log.error(
                    "Dead-man route health notification failed: event_id=%s type=%s",
                    event.event_id,
                    type(exc).__name__,
                )
            acknowledged = (
                result.acknowledgement_count > 0 if result is not None else transport_succeeded
            )
            if not self._store.record_route_health_alert_attempt(
                event.event_id,
                acknowledged=acknowledged,
                attempted_at=now,
            ):
                return True
        return False
