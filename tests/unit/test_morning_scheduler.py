import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from aico.app.morning_delivery import (
    MAX_MORNING_DELIVERY_ATTEMPTS,
    MorningDeliveryStatus,
    SQLiteMorningDeliveryStore,
)
from aico.app.morning_scheduler import (
    MorningPushConfig,
    MorningPushScheduler,
    parse_push_time,
    seconds_until_next_push,
)
from aico.app.scheduled_autonomy import (
    MAX_SCHEDULED_AUTONOMY_ATTEMPTS,
    ScheduledAutonomyStatus,
    SQLiteScheduledAutonomyStore,
)
from aico.app.scheduled_autonomy_delivery import (
    AutonomyOutcomeDeliveryRecord,
    AutonomyOutcomeDeliveryStatus,
    SQLiteAutonomyOutcomeDeliveryStore,
    autonomy_outcome_notification_id,
)
from aico.core.models import ChannelTarget, HealthStatus, SentMessage
from aico.core.morning import MorningHandoffEnvelope, morning_handoff_envelope
from aico.core.standing_autonomy import (
    StandingAutonomyOutcomeEnvelope,
    StandingAutonomyOutcomeStatus,
    StandingAutonomyReceipt,
    StandingAutonomyReceiptStatus,
    StandingAutonomyRunDisposition,
    StandingAutonomyRunReceipt,
    standing_autonomy_outcome_envelope,
)


class FakeMorningTransport:
    def __init__(
        self,
        *,
        failures: int = 0,
        autonomy_failure: bool = False,
        record_before_autonomy_failure: bool = False,
        wrong_ack_target: bool = False,
        wrong_outcome_ack_target: bool = False,
        outcome_failures: int = 0,
    ) -> None:
        self.failures = failures
        self.autonomy_failure = autonomy_failure
        self.record_before_autonomy_failure = record_before_autonomy_failure
        self.wrong_ack_target = wrong_ack_target
        self.wrong_outcome_ack_target = wrong_outcome_ack_target
        self.outcome_failures = outcome_failures
        self.prepare_calls = 0
        self.delivered: list[MorningHandoffEnvelope] = []
        self.autonomy_calls: list[str] = []
        self.autonomy_evidence: dict[str, StandingAutonomyRunReceipt] = {}
        self.outcomes: list[StandingAutonomyOutcomeEnvelope] = []

    def prepare_morning_handoff(
        self,
        *,
        project_id: str,
        scope_id: str,
        delivery_id: str,
    ) -> MorningHandoffEnvelope:
        del scope_id
        self.prepare_calls += 1
        return morning_handoff_envelope(
            delivery_id=delivery_id,
            project_id=project_id,
            task_snapshots=(),
        )

    async def deliver_morning_handoff(
        self,
        target: ChannelTarget,
        envelope: MorningHandoffEnvelope,
    ) -> SentMessage:
        self.delivered.append(envelope)
        if self.failures > 0:
            self.failures -= 1
            raise RuntimeError("sensitive transport detail")
        acknowledged_target = (
            ChannelTarget(channel_name=target.channel_name, target_id="wrong-chat")
            if self.wrong_ack_target
            else target
        )
        return SentMessage(message_id="raw-platform-message-id", target=acknowledged_target)

    async def run_scheduled_autonomy(
        self,
        target: ChannelTarget,
        *,
        project_id: str,
        intent_id: str,
    ) -> StandingAutonomyRunReceipt:
        del target
        self.autonomy_calls.append(intent_id)
        receipt = StandingAutonomyRunReceipt(
            intent_id=intent_id,
            project_id=project_id,
            disposition=StandingAutonomyRunDisposition.NOT_APPLICABLE,
        )
        if self.record_before_autonomy_failure:
            receipt = _recorded_receipt(intent_id, project_id)
            self.autonomy_evidence[intent_id] = receipt
        if self.autonomy_failure:
            raise RuntimeError("standing autonomy failed")
        return receipt

    def scheduled_autonomy_evidence(
        self,
        *,
        project_id: str,
        intent_id: str,
    ) -> StandingAutonomyRunReceipt | None:
        receipt = self.autonomy_evidence.get(intent_id)
        if receipt is not None and receipt.project_id != project_id:
            raise AssertionError("project mismatch")
        return receipt

    def prepare_scheduled_autonomy_outcome(
        self,
        receipt: StandingAutonomyRunReceipt,
    ) -> StandingAutonomyOutcomeEnvelope | None:
        if receipt.disposition is not StandingAutonomyRunDisposition.DISPATCH_RECORDED:
            return None
        return standing_autonomy_outcome_envelope(
            receipt,
            StandingAutonomyReceipt(
                proposal_id=receipt.proposal_id or "missing",
                task_id=receipt.task_id,
                charter_id="absence-loop",
                authorization_id="grant-private-id",
                status=StandingAutonomyReceiptStatus.DONE,
                decided_at=datetime(2026, 7, 22, 9, tzinfo=UTC),
                finished_at=datetime(2026, 7, 22, 9, 1, tzinfo=UTC),
                outcome_status=StandingAutonomyOutcomeStatus.COMPLETE,
                criteria_met=1,
                criteria_total=1,
                verified_sources=1,
            ),
        )

    async def deliver_scheduled_autonomy_outcome(
        self,
        target: ChannelTarget,
        envelope: StandingAutonomyOutcomeEnvelope,
    ) -> SentMessage:
        self.outcomes.append(envelope)
        if self.outcome_failures > 0:
            self.outcome_failures -= 1
            raise RuntimeError("sensitive outcome transport detail")
        acknowledged_target = (
            ChannelTarget(channel_name=target.channel_name, target_id="wrong-chat")
            if self.wrong_outcome_ack_target
            else target
        )
        return SentMessage(message_id="raw-outcome-message-id", target=acknowledged_target)


def test_parse_push_time_accepts_hh_mm() -> None:
    parsed = parse_push_time("08:30")
    assert parsed.hour == 8
    assert parsed.minute == 30


def test_parse_push_time_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="HH:MM"):
        parse_push_time("25:00")


def test_seconds_until_next_push_uses_today_when_time_is_future() -> None:
    seconds = seconds_until_next_push(
        parse_push_time("08:30"),
        now=datetime(2026, 6, 15, 8, 0, 0),
    )
    assert seconds == 30 * 60


def test_seconds_until_next_push_rolls_to_tomorrow() -> None:
    seconds = seconds_until_next_push(
        parse_push_time("08:30"),
        now=datetime(2026, 6, 15, 9, 0, 0),
    )
    assert seconds == 23.5 * 60 * 60


def test_morning_envelope_binds_content_and_standing_receipt_fingerprints() -> None:
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    envelope = morning_handoff_envelope(
        delivery_id="morning-" + "a" * 32,
        project_id="aico",
        task_snapshots=(),
        standing_autonomy_receipts=(
            StandingAutonomyReceipt(
                proposal_id="proposal-1",
                task_id="task-1",
                charter_id="absence-loop",
                authorization_id="grant-1",
                status=StandingAutonomyReceiptStatus.DONE,
                decided_at=now,
                finished_at=now,
                outcome_status=StandingAutonomyOutcomeStatus.COMPLETE,
            ),
        ),
    )

    assert len(envelope.autonomy_receipt_sha256) == 1
    assert len(envelope.autonomy_receipt_sha256[0]) == 64
    with pytest.raises(ValidationError, match="content fingerprint mismatch"):
        MorningHandoffEnvelope.model_validate(
            {
                **envelope.model_dump(),
                "content": envelope.content.model_copy(update={"text": "tampered"}),
            }
        )


def test_autonomy_outcome_envelope_rejects_content_and_source_drift() -> None:
    receipt = _recorded_receipt("autonomy-" + "a" * 32, "aico")
    outcome = StandingAutonomyReceipt(
        proposal_id=receipt.proposal_id or "missing",
        task_id=receipt.task_id,
        charter_id="absence-loop",
        authorization_id="grant-1",
        status=StandingAutonomyReceiptStatus.EVIDENCE_MISSING,
        decided_at=datetime(2026, 7, 22, 9, tzinfo=UTC),
        outcome_status=StandingAutonomyOutcomeStatus.MISSING,
    )
    envelope = standing_autonomy_outcome_envelope(receipt, outcome)

    with pytest.raises(ValidationError, match="content fingerprint mismatch"):
        StandingAutonomyOutcomeEnvelope.model_validate(
            {
                **envelope.model_dump(),
                "content": envelope.content.model_copy(update={"text": "tampered"}),
            }
        )
    with pytest.raises(ValueError, match="source mismatch"):
        standing_autonomy_outcome_envelope(
            receipt,
            outcome.model_copy(update={"task_id": "another-task"}),
        )


async def test_dispatch_persists_ack_and_deduplicates_same_day(tmp_path: Path) -> None:
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport()
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: now)

    first = await scheduler.dispatch_once()
    second = await scheduler.dispatch_once()

    assert first.status is MorningDeliveryStatus.DELIVERED
    assert second.delivery_id == first.delivery_id
    assert transport.prepare_calls == 1
    assert len(transport.delivered) == 1
    assert first.message_id_sha256 is not None
    assert "raw-platform-message-id" not in first.model_dump_json()
    assert first.delivery_id in first.envelope.content.text


async def test_failed_delivery_retries_exact_persisted_content_after_restart(
    tmp_path: Path,
) -> None:
    current = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport(failures=1)
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: current)

    with pytest.raises(RuntimeError, match="sensitive"):
        await scheduler.dispatch_once()
    failed = store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert failed is not None
    assert failed.status is MorningDeliveryStatus.RETRYING
    assert failed.duplicate_possible is True
    assert failed.attempts == 1
    intent = scheduler._autonomy_store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert intent is not None
    assert intent.status is ScheduledAutonomyStatus.PENDING

    current += timedelta(seconds=61)
    restarted = _scheduler(transport, store, clock=lambda: current)
    delivered = await restarted.dispatch_once()

    assert delivered.status is MorningDeliveryStatus.DELIVERED
    assert transport.prepare_calls == 1
    assert transport.delivered[0] == transport.delivered[1]
    assert delivered.attempts == 2


async def test_acknowledgement_for_wrong_target_is_not_marked_delivered(tmp_path: Path) -> None:
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport(wrong_ack_target=True)
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: now)

    with pytest.raises(ValueError, match="target mismatch"):
        await scheduler.dispatch_once()

    latest = store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert latest is not None
    assert latest.status is MorningDeliveryStatus.RETRYING
    assert latest.message_id_sha256 is None


async def test_autonomy_failure_does_not_retry_acknowledged_morning(tmp_path: Path) -> None:
    current = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport(autonomy_failure=True)
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: current)

    with pytest.raises(RuntimeError, match="autonomy"):
        await scheduler.dispatch_once()
    delivered = store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert delivered is not None
    assert delivered.status is MorningDeliveryStatus.DELIVERED
    intent = scheduler._autonomy_store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert intent is not None
    assert intent.status is ScheduledAutonomyStatus.RETRYING

    transport.autonomy_failure = False
    current += timedelta(seconds=61)
    repeated = await scheduler.dispatch_once()
    assert repeated.status is MorningDeliveryStatus.DELIVERED
    assert len(transport.delivered) == 1
    assert len(transport.autonomy_calls) == 2
    settled = scheduler._autonomy_store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert settled is not None
    assert settled.status is ScheduledAutonomyStatus.SETTLED


async def test_recorded_dispatch_is_settled_after_autonomy_exception(tmp_path: Path) -> None:
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport(
        autonomy_failure=True,
        record_before_autonomy_failure=True,
    )
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: now)

    with pytest.raises(RuntimeError, match="autonomy"):
        await scheduler.dispatch_once()

    intent = scheduler._autonomy_store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert intent is not None
    assert intent.status is ScheduledAutonomyStatus.SETTLED
    assert intent.receipt is not None
    assert intent.receipt.disposition is StandingAutonomyRunDisposition.DISPATCH_RECORDED

    transport.autonomy_failure = False
    await scheduler.dispatch_once()
    assert len(transport.delivered) == 1
    assert len(transport.autonomy_calls) == 1


async def test_recorded_autonomy_outcome_is_persisted_before_delivery(tmp_path: Path) -> None:
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport(record_before_autonomy_failure=True)
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: now)

    await scheduler.dispatch_once()

    outcome = scheduler._outcome_store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert outcome is not None
    assert outcome.status is AutonomyOutcomeDeliveryStatus.DELIVERED
    assert outcome.attempts == 1
    assert outcome.message_id_sha256 is not None
    assert "raw-outcome-message-id" not in outcome.model_dump_json()
    assert len(transport.outcomes) == 1
    assert transport.outcomes[0] == outcome.envelope
    assert transport.autonomy_calls == [outcome.intent_id]


async def test_outcome_failure_retries_exact_content_without_rerunning_provider(
    tmp_path: Path,
) -> None:
    current = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport(
        record_before_autonomy_failure=True,
        outcome_failures=1,
    )
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: current)

    with pytest.raises(RuntimeError, match="outcome transport"):
        await scheduler.dispatch_once()
    failed = scheduler._outcome_store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert failed is not None
    assert failed.status is AutonomyOutcomeDeliveryStatus.RETRYING
    assert failed.duplicate_possible is True
    assert len(transport.autonomy_calls) == 1

    current += timedelta(seconds=61)
    restarted = _scheduler(transport, store, clock=lambda: current)
    await restarted.dispatch_once()

    delivered = restarted._outcome_store.load(failed.notification_id)  # noqa: SLF001
    assert delivered is not None
    assert delivered.status is AutonomyOutcomeDeliveryStatus.DELIVERED
    assert delivered.attempts == 2
    assert transport.outcomes[0] == transport.outcomes[1]
    assert len(transport.autonomy_calls) == 1
    assert len(transport.delivered) == 1


async def test_outcome_acknowledgement_for_wrong_target_is_not_delivered(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport(
        record_before_autonomy_failure=True,
        wrong_outcome_ack_target=True,
    )
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: now)

    with pytest.raises(ValueError, match="outcome acknowledgement target mismatch"):
        await scheduler.dispatch_once()

    outcome = scheduler._outcome_store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert outcome is not None
    assert outcome.status is AutonomyOutcomeDeliveryStatus.RETRYING
    assert outcome.message_id_sha256 is None
    assert len(transport.autonomy_calls) == 1


async def test_settled_dispatch_without_outbox_is_repaired_after_restart(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport()
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: now)
    intent_id = await _leave_autonomy_running(scheduler, store, now=now)
    running = scheduler._autonomy_store.load(intent_id)  # noqa: SLF001
    assert running is not None
    scheduler._autonomy_store.mark_settled(  # noqa: SLF001
        intent_id,
        receipt=_recorded_receipt(intent_id, "aico"),
        now=now,
    )

    restarted = _scheduler(transport, store, clock=lambda: now + timedelta(seconds=1))
    assert restarted._seconds_until_work() == 60  # noqa: SLF001
    await restarted.dispatch_once()

    outcome = restarted._outcome_store.for_intent(intent_id)  # noqa: SLF001
    assert outcome is not None
    assert outcome.status is AutonomyOutcomeDeliveryStatus.DELIVERED
    assert transport.autonomy_calls == []


def test_interrupted_outcome_send_retries_same_record_immediately(tmp_path: Path) -> None:
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    receipt = _recorded_receipt("autonomy-" + "b" * 32, "aico")
    transport = FakeMorningTransport()
    envelope = transport.prepare_scheduled_autonomy_outcome(receipt)
    assert envelope is not None
    store = SQLiteAutonomyOutcomeDeliveryStore(tmp_path / "state.db")
    notification_id = autonomy_outcome_notification_id(receipt.intent_id)
    store.ensure(
        AutonomyOutcomeDeliveryRecord(
            notification_id=notification_id,
            intent_id=receipt.intent_id,
            binding_sha256="c" * 64,
            envelope=envelope,
            created_at=now,
            updated_at=now,
        )
    )
    sending = store.begin_attempt(notification_id, now=now)

    assert sending.status is AutonomyOutcomeDeliveryStatus.SENDING
    assert store.reconcile_interrupted(now=now + timedelta(seconds=1)) == 1
    recovered = store.load(notification_id)
    assert recovered is not None
    assert recovered.status is AutonomyOutcomeDeliveryStatus.RETRYING
    assert recovered.duplicate_possible is True
    assert recovered.next_attempt_at == now + timedelta(seconds=1)


async def test_outcome_delivery_exhaustion_fails_health_without_provider_replay(
    tmp_path: Path,
) -> None:
    current = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport(
        record_before_autonomy_failure=True,
        outcome_failures=5,
    )
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: current)

    for _ in range(5):
        with pytest.raises(RuntimeError, match="outcome transport"):
            await scheduler.dispatch_once()
        current += timedelta(minutes=20)

    outcome = scheduler._outcome_store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert outcome is not None
    assert outcome.status is AutonomyOutcomeDeliveryStatus.EXHAUSTED
    assert outcome.attempts == 5
    assert len(transport.autonomy_calls) == 1
    assert len(transport.delivered) == 1
    scheduler.start()
    await asyncio.sleep(0)
    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()


async def test_interrupted_autonomy_without_evidence_retries_only_autonomy(
    tmp_path: Path,
) -> None:
    current = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport()
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: current)
    intent_id = await _leave_autonomy_running(scheduler, store, now=current)

    current += timedelta(seconds=1)
    restarted = _scheduler(transport, store, clock=lambda: current)
    await restarted._reconcile_interrupted_autonomy(current)  # noqa: SLF001
    await restarted.dispatch_once()

    intent = restarted._autonomy_store.load(intent_id)  # noqa: SLF001
    assert intent is not None
    assert intent.status is ScheduledAutonomyStatus.SETTLED
    assert intent.attempts == 2
    assert intent.duplicate_notification_possible is True
    assert len(transport.delivered) == 1
    assert transport.autonomy_calls == [intent_id]


async def test_interrupted_autonomy_with_accepted_evidence_is_not_rerun(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport()
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: now)
    intent_id = await _leave_autonomy_running(scheduler, store, now=now)
    transport.autonomy_evidence[intent_id] = _recorded_receipt(intent_id, "aico")

    restarted = _scheduler(transport, store, clock=lambda: now + timedelta(seconds=1))
    await restarted._reconcile_interrupted_autonomy(now + timedelta(seconds=1))  # noqa: SLF001
    await restarted.dispatch_once()

    intent = restarted._autonomy_store.load(intent_id)  # noqa: SLF001
    assert intent is not None
    assert intent.status is ScheduledAutonomyStatus.SETTLED
    assert intent.attempts == 1
    assert transport.autonomy_calls == []


async def test_autonomy_exhaustion_fails_scheduler_health(tmp_path: Path) -> None:
    current = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport(autonomy_failure=True)
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: current)

    for _ in range(MAX_SCHEDULED_AUTONOMY_ATTEMPTS):
        with pytest.raises(RuntimeError, match="autonomy"):
            await scheduler.dispatch_once()
        current += timedelta(minutes=20)

    intent = scheduler._autonomy_store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert intent is not None
    assert intent.status is ScheduledAutonomyStatus.EXHAUSTED
    assert len(transport.delivered) == 1
    scheduler.start()
    await asyncio.sleep(0)
    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()


async def test_interrupted_send_is_reconciled_as_duplicate_possible(tmp_path: Path) -> None:
    now = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport()
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: now)
    record = scheduler._ensure_occurrence(now)  # noqa: SLF001
    sending = store.begin_attempt(record.delivery_id, now=now)

    assert sending.status is MorningDeliveryStatus.SENDING
    assert store.reconcile_interrupted(now=now + timedelta(seconds=1)) == 1
    recovered = store.load(record.delivery_id)
    assert recovered is not None
    assert recovered.status is MorningDeliveryStatus.RETRYING
    assert recovered.duplicate_possible is True
    assert recovered.next_attempt_at == now + timedelta(seconds=1)


async def test_delivery_exhaustion_fails_scheduler_health(tmp_path: Path) -> None:
    current = datetime(2026, 7, 22, 9, tzinfo=UTC)
    transport = FakeMorningTransport(failures=MAX_MORNING_DELIVERY_ATTEMPTS)
    store = SQLiteMorningDeliveryStore(tmp_path / "state.db")
    scheduler = _scheduler(transport, store, clock=lambda: current)
    scheduler.start()
    await asyncio.sleep(0)

    for _ in range(MAX_MORNING_DELIVERY_ATTEMPTS):
        with pytest.raises(RuntimeError):
            await scheduler.dispatch_once()
        current += timedelta(minutes=20)

    latest = store.latest(scheduler._binding_sha256)  # noqa: SLF001
    assert latest is not None
    assert latest.status is MorningDeliveryStatus.EXHAUSTED
    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()


async def test_morning_scheduler_health_tracks_owned_background_task(tmp_path: Path) -> None:
    now = datetime(2026, 7, 22, 8, tzinfo=UTC)
    scheduler = _scheduler(
        FakeMorningTransport(),
        SQLiteMorningDeliveryStore(tmp_path / "state.db"),
        clock=lambda: now,
    )

    assert await scheduler.health_check() is HealthStatus.FAILED
    scheduler.start()
    await asyncio.sleep(0)
    assert await scheduler.health_check() is HealthStatus.OK
    await scheduler.stop()
    assert await scheduler.health_check() is HealthStatus.FAILED


async def test_morning_scheduler_restarts_only_a_dead_owned_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 22, 8, tzinfo=UTC)
    scheduler = _scheduler(
        FakeMorningTransport(),
        SQLiteMorningDeliveryStore(tmp_path / "state.db"),
        clock=lambda: now,
    )
    attempts = 0
    keep_alive = asyncio.Event()

    async def fail_once_then_wait() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("sensitive scheduler detail")
        await keep_alive.wait()

    monkeypatch.setattr(scheduler, "_run", fail_once_then_wait)
    scheduler.start()
    await asyncio.sleep(0)
    assert scheduler.owned_task_alive() is False
    await scheduler.restart_owned_task()
    await asyncio.sleep(0)
    await scheduler.restart_owned_task()
    assert scheduler.owned_task_alive() is True
    assert attempts == 2
    await scheduler.stop()


def _scheduler(
    transport: FakeMorningTransport,
    store: SQLiteMorningDeliveryStore,
    *,
    clock: object,
) -> MorningPushScheduler:
    autonomy_store = SQLiteScheduledAutonomyStore(store._database.path)  # noqa: SLF001
    outcome_store = SQLiteAutonomyOutcomeDeliveryStore(store._database.path)  # noqa: SLF001
    return MorningPushScheduler(
        orchestrator=transport,
        store=store,
        autonomy_store=autonomy_store,
        outcome_store=outcome_store,
        config=MorningPushConfig(
            channel_name="telegram",
            target_id="trusted-chat",
            project_id="aico",
            push_time=parse_push_time("08:30"),
        ),
        clock=clock,  # type: ignore[arg-type]
    )


def _recorded_receipt(intent_id: str, project_id: str) -> StandingAutonomyRunReceipt:
    return StandingAutonomyRunReceipt(
        intent_id=intent_id,
        project_id=project_id,
        disposition=StandingAutonomyRunDisposition.DISPATCH_RECORDED,
        proposal_id="proposal-private-id",
        task_id="task-private-id",
    )


async def _leave_autonomy_running(
    scheduler: MorningPushScheduler,
    store: SQLiteMorningDeliveryStore,
    *,
    now: datetime,
) -> str:
    record = scheduler._ensure_occurrence(now)  # noqa: SLF001
    delivered = await scheduler._deliver_if_due(record, now=now)  # noqa: SLF001
    assert delivered.status is MorningDeliveryStatus.DELIVERED
    intent = scheduler._autonomy_store.next_open(scheduler._binding_sha256)  # noqa: SLF001
    assert intent is not None
    running = scheduler._autonomy_store.begin_attempt(intent.intent_id, now=now)  # noqa: SLF001
    assert running.status is ScheduledAutonomyStatus.RUNNING
    assert store.load(record.delivery_id) is not None
    return intent.intent_id
