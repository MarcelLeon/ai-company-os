"""Restart-safe scheduled morning handoff delivery for absence-first operation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Protocol

from aico.app.morning_delivery import (
    MorningDeliveryRecord,
    MorningDeliveryStatus,
    MorningDeliveryStore,
)
from aico.app.scheduled_autonomy import (
    ScheduledAutonomyIntent,
    ScheduledAutonomyStatus,
    ScheduledAutonomyStore,
)
from aico.app.scheduled_autonomy_delivery import (
    AutonomyOutcomeDeliveryRecord,
    AutonomyOutcomeDeliveryStatus,
    AutonomyOutcomeDeliveryStore,
    autonomy_outcome_notification_id,
)
from aico.core.models import ChannelTarget, HealthStatus, SentMessage
from aico.core.morning import MorningHandoffEnvelope
from aico.core.standing_autonomy import (
    StandingAutonomyOutcomeEnvelope,
    StandingAutonomyRunDisposition,
    StandingAutonomyRunReceipt,
)

log = logging.getLogger(__name__)
_Clock = Callable[[], datetime]
_Sleep = Callable[[float], Awaitable[None]]


class MorningHandoffTransport(Protocol):
    def prepare_morning_handoff(
        self,
        *,
        project_id: str,
        scope_id: str,
        delivery_id: str,
    ) -> MorningHandoffEnvelope: ...

    async def deliver_morning_handoff(
        self,
        target: ChannelTarget,
        envelope: MorningHandoffEnvelope,
    ) -> SentMessage: ...

    async def run_scheduled_autonomy(
        self,
        target: ChannelTarget,
        *,
        project_id: str,
        intent_id: str,
    ) -> StandingAutonomyRunReceipt: ...

    def scheduled_autonomy_evidence(
        self,
        *,
        project_id: str,
        intent_id: str,
    ) -> StandingAutonomyRunReceipt | None: ...

    def prepare_scheduled_autonomy_outcome(
        self,
        receipt: StandingAutonomyRunReceipt,
    ) -> StandingAutonomyOutcomeEnvelope | None: ...

    async def deliver_scheduled_autonomy_outcome(
        self,
        target: ChannelTarget,
        envelope: StandingAutonomyOutcomeEnvelope,
    ) -> SentMessage: ...


@dataclass(frozen=True)
class MorningPushConfig:
    channel_name: str
    target_id: str
    project_id: str
    push_time: time
    thread_id: str | None = None
    scope_id: str | None = None
    push_on_start: bool = False
    delivery_timeout_seconds: float = 60

    def __post_init__(self) -> None:
        if self.delivery_timeout_seconds <= 0:
            raise ValueError("morning delivery timeout must be positive")


class MorningPushScheduler:
    """Deliver one durable logical morning handoff per local calendar day."""

    def __init__(
        self,
        *,
        orchestrator: MorningHandoffTransport,
        config: MorningPushConfig,
        store: MorningDeliveryStore,
        autonomy_store: ScheduledAutonomyStore,
        outcome_store: AutonomyOutcomeDeliveryStore,
        clock: _Clock | None = None,
        sleep: _Sleep = asyncio.sleep,
    ) -> None:
        self._orchestrator = orchestrator
        self._config = config
        self._store = store
        self._autonomy_store = autonomy_store
        self._outcome_store = outcome_store
        self._clock = clock or (lambda: datetime.now().astimezone())
        self._sleep = sleep
        self._binding_sha256 = _binding_sha256(config)
        self._task: asyncio.Task[None] | None = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._start_task()

    async def stop(self) -> None:
        self._running = False
        if self._task is None:
            return
        if not self._task.done():
            self._task.cancel()
        await self._consume_task()
        self._task = None

    async def _consume_task(self) -> None:
        if self._task is None:
            return
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log.error("Morning push task stopped unexpectedly: type=%s", type(exc).__name__)

    async def health_check(self) -> HealthStatus:
        if self._task is None or self._task.done():
            return HealthStatus.FAILED
        latest = self._store.latest(self._binding_sha256)
        autonomy = self._autonomy_store.latest(self._binding_sha256)
        outcome = self._outcome_store.latest(self._binding_sha256)
        if outcome is not None and outcome.status is AutonomyOutcomeDeliveryStatus.EXHAUSTED:
            return HealthStatus.FAILED
        if autonomy is not None and autonomy.status is ScheduledAutonomyStatus.EXHAUSTED:
            return HealthStatus.FAILED
        if latest is not None and latest.status is MorningDeliveryStatus.EXHAUSTED:
            return HealthStatus.FAILED
        if latest is not None and latest.status is not MorningDeliveryStatus.DELIVERED:
            return HealthStatus.DEGRADED
        if autonomy is not None and autonomy.status is not ScheduledAutonomyStatus.SETTLED:
            return HealthStatus.DEGRADED
        if outcome is not None and outcome.status is not AutonomyOutcomeDeliveryStatus.DELIVERED:
            return HealthStatus.DEGRADED
        if self._outcome_missing_for(autonomy):
            return HealthStatus.DEGRADED
        return HealthStatus.OK

    def owned_task_alive(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    async def restart_owned_task(self) -> None:
        if not self._running or self.owned_task_alive():
            return
        if self._task is not None:
            await self._consume_task()
        if self._running:
            self._start_task()

    async def dispatch_once(self) -> MorningDeliveryRecord:
        now = self._aware_now()
        self._ensure_latest_outcome(now=now)
        await self._deliver_next_outcome(now=now)
        open_record = self._store.next_open(self._binding_sha256)
        if open_record is not None:
            recovered = await self._deliver_if_due(open_record, now=now)
            if recovered.status is not MorningDeliveryStatus.DELIVERED:
                return recovered
        record = self._ensure_occurrence(now)
        delivered = await self._deliver_if_due(record, now=now)
        await self._run_next_autonomy(now=self._aware_now())
        self._ensure_latest_outcome(now=self._aware_now())
        await self._deliver_next_outcome(now=self._aware_now())
        return delivered

    async def _run(self) -> None:
        now = self._aware_now()
        self._store.reconcile_interrupted(now=now)
        self._outcome_store.reconcile_interrupted(now=now)
        await self._reconcile_interrupted_autonomy(now)
        self._ensure_latest_outcome(now=self._aware_now())
        await self._safe_drain_open(now)
        if self._config.push_on_start:
            await self._safe_dispatch()
        while True:
            await self._sleep(self._seconds_until_work())
            await self._safe_dispatch()

    def _start_task(self) -> None:
        self._task = asyncio.create_task(self._run(), name="aico-morning-push")

    async def _safe_dispatch(self) -> None:
        try:
            await self.dispatch_once()
        except Exception as exc:
            log.error("Morning push attempt failed: type=%s", type(exc).__name__)

    async def _safe_drain_open(self, now: datetime) -> None:
        record = self._store.next_open(self._binding_sha256)
        try:
            await self._deliver_next_outcome(now=now)
            if record is not None:
                await self._deliver_if_due(record, now=now)
            await self._run_next_autonomy(now=self._aware_now())
            self._ensure_latest_outcome(now=self._aware_now())
            await self._deliver_next_outcome(now=self._aware_now())
        except Exception as exc:
            log.error("Morning push recovery failed: type=%s", type(exc).__name__)

    def _ensure_occurrence(self, now: datetime) -> MorningDeliveryRecord:
        scheduled_for = now.replace(
            hour=self._config.push_time.hour,
            minute=self._config.push_time.minute,
            second=0,
            microsecond=0,
        )
        delivery_id = _delivery_id(self._binding_sha256, scheduled_for)
        existing = self._store.load(delivery_id)
        if existing is not None:
            return existing
        envelope = self._orchestrator.prepare_morning_handoff(
            project_id=self._config.project_id,
            scope_id=self._config.scope_id or self._config.target_id,
            delivery_id=delivery_id,
        )
        return self._store.enqueue(
            MorningDeliveryRecord(
                delivery_id=delivery_id,
                binding_sha256=self._binding_sha256,
                scheduled_for=scheduled_for,
                envelope=envelope,
                created_at=now,
                updated_at=now,
            )
        )

    async def _deliver_if_due(
        self,
        record: MorningDeliveryRecord,
        *,
        now: datetime,
    ) -> MorningDeliveryRecord:
        self._ensure_autonomy_intent(record, now=now)
        sending = self._store.begin_attempt(record.delivery_id, now=now)
        if sending.status is not MorningDeliveryStatus.SENDING:
            return sending
        target = ChannelTarget(
            channel_name=self._config.channel_name,
            target_id=self._config.target_id,
            thread_id=self._config.thread_id,
        )
        try:
            sent = await asyncio.wait_for(
                self._orchestrator.deliver_morning_handoff(target, sending.envelope),
                timeout=self._config.delivery_timeout_seconds,
            )
            if sent.target != target:
                raise ValueError("morning platform acknowledgement target mismatch")
        except BaseException:
            self._store.defer(record.delivery_id, now=self._aware_now())
            raise
        return self._store.mark_delivered(
            record.delivery_id,
            sent=sent,
            now=self._aware_now(),
        )

    async def _run_next_autonomy(self, *, now: datetime) -> None:
        intent = self._autonomy_store.next_open(self._binding_sha256)
        if intent is None:
            return
        delivery = self._store.load(intent.delivery_id)
        if delivery is None or delivery.status is not MorningDeliveryStatus.DELIVERED:
            return
        running = self._autonomy_store.begin_attempt(intent.intent_id, now=now)
        if running.status is not ScheduledAutonomyStatus.RUNNING:
            return
        target = self._target()
        try:
            receipt = await self._orchestrator.run_scheduled_autonomy(
                target,
                project_id=running.project_id,
                intent_id=running.intent_id,
            )
        except BaseException:
            self._settle_or_defer(running, now=self._aware_now())
            raise
        self._autonomy_store.mark_settled(
            running.intent_id,
            receipt=receipt,
            now=self._aware_now(),
        )

    def _ensure_latest_outcome(self, *, now: datetime) -> None:
        intent = self._autonomy_store.latest(self._binding_sha256)
        if not self._outcome_missing_for(intent):
            return
        assert intent is not None and intent.receipt is not None
        envelope = self._orchestrator.prepare_scheduled_autonomy_outcome(intent.receipt)
        if envelope is None:
            return
        self._outcome_store.ensure(
            AutonomyOutcomeDeliveryRecord(
                notification_id=autonomy_outcome_notification_id(intent.intent_id),
                intent_id=intent.intent_id,
                binding_sha256=intent.binding_sha256,
                envelope=envelope,
                created_at=now,
                updated_at=now,
            )
        )

    async def _deliver_next_outcome(self, *, now: datetime) -> None:
        record = self._outcome_store.next_open(self._binding_sha256)
        if record is None:
            return
        sending = self._outcome_store.begin_attempt(record.notification_id, now=now)
        if sending.status is not AutonomyOutcomeDeliveryStatus.SENDING:
            return
        target = self._target()
        try:
            sent = await asyncio.wait_for(
                self._orchestrator.deliver_scheduled_autonomy_outcome(
                    target,
                    sending.envelope,
                ),
                timeout=self._config.delivery_timeout_seconds,
            )
            if sent.target != target:
                raise ValueError("autonomy outcome acknowledgement target mismatch")
        except BaseException:
            self._outcome_store.defer(record.notification_id, now=self._aware_now())
            raise
        self._outcome_store.mark_delivered(
            record.notification_id,
            sent=sent,
            now=self._aware_now(),
        )

    def _outcome_missing_for(self, intent: ScheduledAutonomyIntent | None) -> bool:
        return bool(
            intent is not None
            and intent.status is ScheduledAutonomyStatus.SETTLED
            and intent.receipt is not None
            and intent.receipt.disposition is StandingAutonomyRunDisposition.DISPATCH_RECORDED
            and self._outcome_store.for_intent(intent.intent_id) is None
        )

    async def _reconcile_interrupted_autonomy(self, now: datetime) -> None:
        for intent in self._autonomy_store.interrupted(self._binding_sha256):
            self._settle_or_defer(intent, now=now, immediate=True)

    def _settle_or_defer(
        self,
        intent: ScheduledAutonomyIntent,
        *,
        now: datetime,
        immediate: bool = False,
    ) -> None:
        evidence = self._orchestrator.scheduled_autonomy_evidence(
            project_id=intent.project_id,
            intent_id=intent.intent_id,
        )
        if evidence is not None:
            self._autonomy_store.mark_settled(
                intent.intent_id,
                receipt=evidence,
                now=now,
            )
            return
        self._autonomy_store.defer(intent.intent_id, now=now, immediate=immediate)

    def _ensure_autonomy_intent(
        self,
        record: MorningDeliveryRecord,
        *,
        now: datetime,
    ) -> ScheduledAutonomyIntent:
        return self._autonomy_store.ensure(
            ScheduledAutonomyIntent(
                intent_id=_autonomy_intent_id(record.delivery_id),
                delivery_id=record.delivery_id,
                binding_sha256=record.binding_sha256,
                project_id=record.envelope.project_id,
                created_at=now,
                updated_at=now,
            )
        )

    def _target(self) -> ChannelTarget:
        return ChannelTarget(
            channel_name=self._config.channel_name,
            target_id=self._config.target_id,
            thread_id=self._config.thread_id,
        )

    def _seconds_until_work(self) -> float:
        now = self._aware_now()
        delay = seconds_until_next_push(self._config.push_time, now=now)
        open_record = self._store.next_open(self._binding_sha256)
        if open_record is not None:
            retry_at = open_record.next_attempt_at or now
            delay = min(delay, max(0.01, (retry_at - now).total_seconds()))
        autonomy = self._autonomy_store.next_open(self._binding_sha256)
        if autonomy is not None:
            delivery = self._store.load(autonomy.delivery_id)
            if delivery is not None and delivery.status is MorningDeliveryStatus.DELIVERED:
                retry_at = autonomy.next_attempt_at or now
                delay = min(delay, max(0.01, (retry_at - now).total_seconds()))
        outcome = self._outcome_store.next_open(self._binding_sha256)
        if outcome is not None:
            retry_at = outcome.next_attempt_at or now
            delay = min(delay, max(0.01, (retry_at - now).total_seconds()))
        if self._outcome_missing_for(self._autonomy_store.latest(self._binding_sha256)):
            delay = min(delay, 60.0)
        return delay

    def _aware_now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("morning scheduler clock must be timezone-aware")
        return now


def parse_push_time(value: str) -> time:
    try:
        hour_text, minute_text = value.strip().split(":", maxsplit=1)
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError as exc:
        raise ValueError("morning push time must be HH:MM") from exc
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("morning push time must be HH:MM")
    return time(hour=hour, minute=minute)


def seconds_until_next_push(push_time: time, *, now: datetime | None = None) -> float:
    current = now or datetime.now()
    next_push = current.replace(
        hour=push_time.hour,
        minute=push_time.minute,
        second=0,
        microsecond=0,
    )
    if next_push <= current:
        next_push += timedelta(days=1)
    return (next_push - current).total_seconds()


def _binding_sha256(config: MorningPushConfig) -> str:
    payload = json.dumps(
        {
            "channel": config.channel_name,
            "target": config.target_id,
            "thread": config.thread_id,
            "scope": config.scope_id or config.target_id,
            "project": config.project_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _delivery_id(binding_sha256: str, scheduled_for: datetime) -> str:
    occurrence = scheduled_for.date().isoformat()
    digest = hashlib.sha256(f"{binding_sha256}:{occurrence}".encode()).hexdigest()
    return f"morning-{digest[:32]}"


def _autonomy_intent_id(delivery_id: str) -> str:
    digest = hashlib.sha256(f"scheduled-autonomy:{delivery_id}".encode()).hexdigest()
    return f"autonomy-{digest[:32]}"
