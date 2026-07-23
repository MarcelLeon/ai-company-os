from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aico.app.boss_absent_aico_im import (
    AicoImAmbiguousDeliveryError,
    AicoImDecision,
    AicoImDeliveryAckKind,
    AicoImDeliveryReceipt,
    AicoImExchangeKind,
    AicoImExchangeRequest,
    AicoImExchangeStore,
    AicoImOwnerBinding,
    collect_aico_im_decision,
    dispatch_aico_im_request,
    observe_aico_im_incoming,
)
from aico.channel.base import IncomingMessageHandler
from aico.core.models import (
    ChannelTarget,
    HealthStatus,
    IncomingMessage,
    MessageContent,
    SentMessage,
    utc_now,
)


def _request(
    kind: AicoImExchangeKind = AicoImExchangeKind.APPROVAL,
    *,
    created_at: datetime = datetime(2026, 7, 23, tzinfo=UTC),
) -> AicoImExchangeRequest:
    return AicoImExchangeRequest(
        kind=kind,
        contract_sha256="a" * 64,
        task_id="owner-im-test",
        subject_sha256="b" * 64,
        created_at=created_at,
        expires_at=created_at + timedelta(minutes=10),
    )


def _owner() -> AicoImOwnerBinding:
    return AicoImOwnerBinding(
        channel_name="telegram",
        target_id="owner-chat",
        sender_id="owner-user",
    )


def _incoming(
    value: str,
    *,
    sender_id: str = "owner-user",
    raw_ref: str = "callback-1",
    timestamp: datetime = datetime(2026, 7, 23, 0, 0, 5, tzinfo=UTC),
) -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=_owner().target(),
        sender_id=sender_id,
        content=MessageContent(text=value),
        timestamp=timestamp,
        raw_ref=raw_ref,
    )


class _FakeChannel:
    def __init__(self) -> None:
        self.sent: list[tuple[ChannelTarget, MessageContent]] = []
        self.handler: IncomingMessageHandler | None = None
        self.started = False
        self.stopped = False
        self.auto_reply = False

    @property
    def name(self) -> str:
        return "telegram"

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def send_message(
        self,
        target: ChannelTarget,
        content: MessageContent,
    ) -> SentMessage:
        self.sent.append((target, content))
        if self.auto_reply:
            assert self.handler is not None
            await self.handler(
                _incoming(
                    content.actions[0].value,
                    timestamp=utc_now(),
                )
            )
        return SentMessage(message_id=f"platform-{len(self.sent)}", target=target)

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> None:
        raise AssertionError("not used")

    async def delete_message(self, target: ChannelTarget, message_id: str) -> None:
        raise AssertionError("not used")

    def on_incoming(self, handler: IncomingMessageHandler) -> None:
        self.handler = handler

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


class _CrashBeforeDeliveryStore(AicoImExchangeStore):
    def save_delivery(self, value: AicoImDeliveryReceipt) -> None:
        raise RuntimeError("simulated crash after platform send")


@pytest.mark.asyncio
async def test_owner_bound_approval_counts_relevant_actions_and_closes_once(
    tmp_path: Path,
) -> None:
    channel = _FakeChannel()
    owner = _owner()
    request = _request()
    store = AicoImExchangeStore((tmp_path / "exchange").absolute())

    delivery = await dispatch_aico_im_request(channel, owner, request, store)
    approve = channel.sent[0][1].actions[0].value
    invalid = approve.removesuffix("approve") + "maybe"

    assert (
        observe_aico_im_incoming(
            owner,
            store,
            _incoming(approve, sender_id="intruder", raw_ref="intruder"),
        )
        is None
    )
    assert (
        observe_aico_im_incoming(
            owner,
            store,
            _incoming(invalid, raw_ref="attempt-1"),
        )
        is None
    )
    receipt = observe_aico_im_incoming(
        owner,
        store,
        _incoming(
            approve,
            raw_ref="attempt-2",
            timestamp=request.created_at + timedelta(seconds=8),
        ),
    )
    repeated = observe_aico_im_incoming(
        owner,
        store,
        _incoming(
            approve,
            raw_ref="attempt-3",
            timestamp=request.created_at + timedelta(seconds=9),
        ),
    )

    assert receipt is not None
    assert repeated == receipt
    assert receipt.decision is AicoImDecision.APPROVED
    assert receipt.actions == 2
    assert receipt.elapsed_seconds == 8
    assert delivery.ack_kind is AicoImDeliveryAckKind.PLATFORM_SEND_RESPONSE
    assert len(channel.sent) == 1
    for name in ("intent.json", "delivery.json", "actions.json", "decision.json"):
        assert (tmp_path / "exchange" / name).stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_restart_does_not_resend_ambiguous_delivery_and_inbound_reconciles(
    tmp_path: Path,
) -> None:
    root = (tmp_path / "exchange").absolute()
    channel = _FakeChannel()
    owner = _owner()
    request = _request()

    with pytest.raises(RuntimeError, match="simulated crash"):
        await dispatch_aico_im_request(
            channel,
            owner,
            request,
            _CrashBeforeDeliveryStore(root),
        )
    restarted = AicoImExchangeStore(root)
    with pytest.raises(AicoImAmbiguousDeliveryError, match="wait for owner"):
        await dispatch_aico_im_request(channel, owner, request, restarted)

    approve = channel.sent[0][1].actions[0].value
    receipt = observe_aico_im_incoming(
        owner,
        restarted,
        _incoming(approve, timestamp=request.created_at + timedelta(seconds=4)),
    )
    delivery = restarted.load_delivery()

    assert receipt is not None
    assert len(channel.sent) == 1
    assert delivery is not None
    assert delivery.ack_kind is AicoImDeliveryAckKind.OWNER_INBOUND_RECONCILIATION
    assert receipt.delivery_ack_sha256


@pytest.mark.asyncio
async def test_exclusive_collector_handles_immediate_owner_takeover_reply(
    tmp_path: Path,
) -> None:
    now = utc_now()
    request = _request(AicoImExchangeKind.TAKEOVER, created_at=now)
    channel = _FakeChannel()
    channel.auto_reply = True

    receipt = await collect_aico_im_decision(
        channel,
        _owner(),
        request,
        AicoImExchangeStore((tmp_path / "takeover").absolute()),
        max_wait_seconds=5,
    )

    assert receipt.decision is AicoImDecision.ACKNOWLEDGED
    assert receipt.kind is AicoImExchangeKind.TAKEOVER
    assert receipt.actions == 1
    assert channel.started is True
    assert channel.stopped is True


@pytest.mark.asyncio
async def test_owner_action_outside_frozen_window_is_ignored(tmp_path: Path) -> None:
    channel = _FakeChannel()
    owner = _owner()
    request = _request()
    store = AicoImExchangeStore((tmp_path / "exchange").absolute())
    await dispatch_aico_im_request(channel, owner, request, store)

    result = observe_aico_im_incoming(
        owner,
        store,
        _incoming(
            channel.sent[0][1].actions[0].value,
            timestamp=request.expires_at,
        ),
    )

    assert result is None
    assert store.load_decision() is None
