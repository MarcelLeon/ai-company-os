"""Durable owner-bound IM exchanges for formal AICO benchmark decisions."""

from __future__ import annotations

import asyncio
import hashlib
import os
import stat
import tempfile
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import Field, model_validator

from aico.channel.base import IMChannel
from aico.core.boss_absent_benchmark import canonical_sha256
from aico.core.models import (
    ChannelTarget,
    FrozenModel,
    IncomingMessage,
    MessageAction,
    MessageContent,
    SentMessage,
    utc_now,
)

_MAX_EXCHANGE_FILE_BYTES = 65_536
_MAX_ACTIONS = 64
ModelT = TypeVar("ModelT", bound=FrozenModel)


class AicoImExchangeKind(StrEnum):
    APPROVAL = "approval"
    TAKEOVER = "takeover"


class AicoImDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    ACKNOWLEDGED = "acknowledged"


class AicoImDeliveryAckKind(StrEnum):
    PLATFORM_SEND_RESPONSE = "platform_send_response"
    OWNER_INBOUND_RECONCILIATION = "owner_inbound_reconciliation"


class AicoImOwnerBinding(FrozenModel):
    channel_name: str = Field(min_length=1, max_length=64)
    target_id: str = Field(min_length=1, max_length=256)
    sender_id: str = Field(min_length=1, max_length=256)
    thread_id: str | None = Field(default=None, min_length=1, max_length=256)

    def target(self) -> ChannelTarget:
        return ChannelTarget(
            channel_name=self.channel_name,
            target_id=self.target_id,
            thread_id=self.thread_id,
        )


class AicoImExchangeRequest(FrozenModel):
    version: Literal[1] = 1
    kind: AicoImExchangeKind
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    subject_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_window(self) -> AicoImExchangeRequest:
        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
            or self.expires_at.tzinfo is None
            or self.expires_at.utcoffset() is None
            or self.expires_at <= self.created_at
        ):
            raise ValueError("AICO IM exchange window is invalid")
        return self


class AicoImSendIntent(FrozenModel):
    version: Literal[1] = 1
    request: AicoImExchangeRequest
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    message_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_values_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_request_identity(self) -> AicoImSendIntent:
        if self.request_sha256 != canonical_sha256(self.request):
            raise ValueError("AICO IM intent request identity drifted")
        return self


class AicoImDeliveryReceipt(FrozenModel):
    version: Literal[1] = 1
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ack_kind: AicoImDeliveryAckKind
    platform_ack_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    acknowledged_at: datetime

    @model_validator(mode="after")
    def validate_timestamp(self) -> AicoImDeliveryReceipt:
        if self.acknowledged_at.tzinfo is None or self.acknowledged_at.utcoffset() is None:
            raise ValueError("AICO IM delivery timestamp must be timezone-aware")
        return self


class AicoImInboundAction(FrozenModel):
    version: Literal[1] = 1
    sequence: int = Field(ge=1, le=_MAX_ACTIONS)
    previous_action_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_ref_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_value_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: datetime
    accepted_decision: AicoImDecision | None = None


class AicoImActionLedger(FrozenModel):
    version: Literal[1] = 1
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    events: tuple[AicoImInboundAction, ...] = Field(default=(), max_length=_MAX_ACTIONS)

    @model_validator(mode="after")
    def validate_chain(self) -> AicoImActionLedger:
        previous: str | None = None
        raw_refs: set[str] = set()
        terminal_seen = False
        for index, event in enumerate(self.events, start=1):
            if (
                event.sequence != index
                or event.request_sha256 != self.request_sha256
                or event.previous_action_sha256 != previous
                or event.raw_ref_sha256 in raw_refs
                or terminal_seen
            ):
                raise ValueError("AICO IM action ledger chain is invalid")
            raw_refs.add(event.raw_ref_sha256)
            terminal_seen = event.accepted_decision is not None
            previous = canonical_sha256(event)
        return self


class AicoImDecisionReceipt(FrozenModel):
    version: Literal[1] = 1
    kind: AicoImExchangeKind
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    subject_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    delivery_ack_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    inbound_ack_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: AicoImDecision
    actions: int = Field(ge=1, le=_MAX_ACTIONS)
    elapsed_seconds: float = Field(ge=0)
    decided_at: datetime

    @model_validator(mode="after")
    def validate_decision_kind(self) -> AicoImDecisionReceipt:
        allowed = (
            {AicoImDecision.APPROVED, AicoImDecision.REJECTED}
            if self.kind is AicoImExchangeKind.APPROVAL
            else {AicoImDecision.ACKNOWLEDGED}
        )
        if self.decision not in allowed:
            raise ValueError("AICO IM decision does not match the exchange kind")
        return self


class AicoImExchangeStore:
    """Owner-only durable exchange state shared across collector restarts."""

    def __init__(self, root: Path) -> None:
        if not root.is_absolute():
            raise ValueError("AICO IM exchange root must be absolute")
        self._root = root

    def load_intent(self) -> AicoImSendIntent | None:
        return self._load("intent.json", AicoImSendIntent)

    def save_intent(self, value: AicoImSendIntent) -> None:
        self._write_immutable("intent.json", _model_bytes(value))

    def load_delivery(self) -> AicoImDeliveryReceipt | None:
        return self._load("delivery.json", AicoImDeliveryReceipt)

    def save_delivery(self, value: AicoImDeliveryReceipt) -> None:
        self._write_immutable("delivery.json", _model_bytes(value))

    def load_actions(self, request_sha256: str) -> AicoImActionLedger:
        existing = self._load("actions.json", AicoImActionLedger)
        if existing is None:
            return AicoImActionLedger(request_sha256=request_sha256)
        if existing.request_sha256 != request_sha256:
            raise ValueError("AICO IM action ledger request drifted")
        return existing

    def save_actions(self, value: AicoImActionLedger) -> None:
        self._write_atomic("actions.json", _model_bytes(value))

    def load_decision(self) -> AicoImDecisionReceipt | None:
        return self._load("decision.json", AicoImDecisionReceipt)

    def save_decision(self, value: AicoImDecisionReceipt) -> None:
        self._write_immutable("decision.json", _model_bytes(value))

    def _load(self, name: str, model_type: type[ModelT]) -> ModelT | None:
        path = self._path(name)
        if not path.exists() and not path.is_symlink():
            return None
        payload = _read_owner_file(path)
        try:
            return model_type.model_validate_json(payload)
        except ValueError:
            raise ValueError(f"AICO IM {name} is invalid") from None

    def _write_immutable(self, name: str, payload: bytes) -> None:
        path = self._path(name)
        self._prepare_root()
        if path.exists() or path.is_symlink():
            if _read_owner_file(path) != payload:
                raise ValueError(f"AICO IM {name} identity drifted")
            return
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            _fsync_directory(self._root)
        except BaseException:
            if path.exists() and path.stat().st_size == 0:
                path.unlink()
            raise

    def _write_atomic(self, name: str, payload: bytes) -> None:
        self._prepare_root()
        target = self._path(name)
        if target.exists() or target.is_symlink():
            _read_owner_file(target)
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f".{name}.",
            suffix=".tmp",
            dir=self._root,
        )
        temporary = Path(raw_path)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, target)
            _fsync_directory(self._root)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _prepare_root(self) -> None:
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self._root.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            raise ValueError("AICO IM exchange root must be owner-only")

    def _path(self, name: str) -> Path:
        return self._root / name


class AicoImAmbiguousDeliveryError(RuntimeError):
    """Raised when a durable send intent exists without a platform ACK."""


async def dispatch_aico_im_request(
    channel: IMChannel,
    owner: AicoImOwnerBinding,
    request: AicoImExchangeRequest,
    store: AicoImExchangeStore,
) -> AicoImDeliveryReceipt:
    """Persist intent before sending, and never blindly resend an ambiguous request."""
    _validate_channel(channel, owner)
    intent = _intent(request, owner)
    existing_intent = store.load_intent()
    delivery = store.load_delivery()
    if existing_intent is not None and existing_intent != intent:
        raise ValueError("AICO IM exchange intent drifted")
    if delivery is not None:
        _validate_delivery(intent, delivery)
        return delivery
    if existing_intent is not None:
        raise AicoImAmbiguousDeliveryError(
            "AICO IM send intent has no delivery ACK; wait for owner inbound reconciliation"
        )
    store.save_intent(intent)
    sent = await channel.send_message(owner.target(), _request_message(request))
    platform_delivery = _platform_delivery(intent, sent, owner)
    reconciled = store.load_delivery()
    if reconciled is not None:
        _validate_delivery(intent, reconciled)
        return reconciled
    store.save_delivery(platform_delivery)
    return platform_delivery


def observe_aico_im_incoming(
    owner: AicoImOwnerBinding,
    store: AicoImExchangeStore,
    incoming: IncomingMessage,
) -> AicoImDecisionReceipt | None:
    """Record one owner-bound action and close the exchange on an exact decision."""
    intent = store.load_intent()
    if intent is None:
        raise ValueError("AICO IM incoming action has no durable request intent")
    existing = store.load_decision()
    if existing is not None:
        return existing
    if not _matches_owner(owner, incoming):
        return None
    if not (intent.request.created_at <= incoming.timestamp < intent.request.expires_at):
        return None
    value = incoming.content.text.strip()
    token = _request_token(intent.request)
    if not value.startswith(f"aico:{intent.request.kind.value}:") or token not in value:
        return None
    ledger = store.load_actions(intent.request_sha256)
    raw_ref_sha = _sha(incoming.raw_ref.encode("utf-8"))
    if any(event.raw_ref_sha256 == raw_ref_sha for event in ledger.events):
        return store.load_decision()
    decision = _decision_for_value(intent.request, value)
    event = AicoImInboundAction(
        sequence=len(ledger.events) + 1,
        previous_action_sha256=(canonical_sha256(ledger.events[-1]) if ledger.events else None),
        request_sha256=intent.request_sha256,
        owner_binding_sha256=intent.owner_binding_sha256,
        raw_ref_sha256=raw_ref_sha,
        action_value_sha256=_sha(value.encode("utf-8")),
        observed_at=incoming.timestamp,
        accepted_decision=decision,
    )
    ledger = ledger.model_copy(update={"events": (*ledger.events, event)})
    store.save_actions(ledger)
    if decision is None:
        return None
    delivery = store.load_delivery()
    if delivery is None:
        delivery = _inbound_delivery(intent, incoming)
        store.save_delivery(delivery)
    _validate_delivery(intent, delivery)
    elapsed = max(0.0, (incoming.timestamp - intent.request.created_at).total_seconds())
    receipt = AicoImDecisionReceipt(
        kind=intent.request.kind,
        contract_sha256=intent.request.contract_sha256,
        task_id=intent.request.task_id,
        subject_sha256=intent.request.subject_sha256,
        request_sha256=intent.request_sha256,
        owner_binding_sha256=intent.owner_binding_sha256,
        delivery_ack_sha256=canonical_sha256(delivery),
        inbound_ack_sha256=canonical_sha256(event),
        decision=decision,
        actions=len(ledger.events),
        elapsed_seconds=elapsed,
        decided_at=incoming.timestamp,
    )
    store.save_decision(receipt)
    return receipt


async def collect_aico_im_decision(
    channel: IMChannel,
    owner: AicoImOwnerBinding,
    request: AicoImExchangeRequest,
    store: AicoImExchangeStore,
    *,
    max_wait_seconds: float,
) -> AicoImDecisionReceipt:
    """Exclusively own one IM channel until the bound owner decides or time expires."""
    if max_wait_seconds <= 0:
        raise ValueError("AICO IM collector wait must be positive")
    existing = store.load_decision()
    if existing is not None:
        _validate_decision(request, owner, existing)
        return existing
    decided = asyncio.Event()

    async def handler(message: IncomingMessage) -> None:
        if observe_aico_im_incoming(owner, store, message) is not None:
            decided.set()

    channel.on_incoming(handler)
    await channel.start()
    try:
        try:
            await dispatch_aico_im_request(channel, owner, request, store)
        except AicoImAmbiguousDeliveryError:
            pass
        existing = store.load_decision()
        if existing is None:
            remaining = (request.expires_at - utc_now()).total_seconds()
            if remaining <= 0:
                raise TimeoutError("AICO IM exchange expired")
            await asyncio.wait_for(decided.wait(), timeout=min(max_wait_seconds, remaining))
        result = store.load_decision()
        if result is None:
            raise RuntimeError("AICO IM collector woke without a durable decision")
        _validate_decision(request, owner, result)
        return result
    finally:
        await channel.stop()


def _intent(
    request: AicoImExchangeRequest,
    owner: AicoImOwnerBinding,
) -> AicoImSendIntent:
    message = _request_message(request)
    action_values = tuple(action.value for action in message.actions)
    return AicoImSendIntent(
        request=request,
        request_sha256=canonical_sha256(request),
        owner_binding_sha256=canonical_sha256(owner),
        message_sha256=_sha(message.text.encode("utf-8")),
        action_values_sha256=_sha("\0".join(action_values).encode("utf-8")),
    )


def _request_message(request: AicoImExchangeRequest) -> MessageContent:
    token = _request_token(request)
    actions: tuple[MessageAction, ...]
    if request.kind is AicoImExchangeKind.APPROVAL:
        text = (
            "AICO benchmark approval required.\n"
            f"Task: {request.task_id}\n"
            f"Request: {token}\n"
            "Approve only the frozen isolated action."
        )
        actions = (
            MessageAction(label="Approve", value=f"aico:approval:{token}:approve"),
            MessageAction(label="Reject", value=f"aico:approval:{token}:reject"),
        )
    else:
        text = (
            "AICO benchmark takeover check.\n"
            f"Task: {request.task_id}\n"
            f"Request: {token}\n"
            "Acknowledge the terminal checkpoint."
        )
        actions = (MessageAction(label="Take over", value=f"aico:takeover:{token}:ack"),)
    return MessageContent(text=text, actions=actions)


def _decision_for_value(
    request: AicoImExchangeRequest,
    value: str,
) -> AicoImDecision | None:
    token = _request_token(request)
    values = (
        {
            f"aico:approval:{token}:approve": AicoImDecision.APPROVED,
            f"aico:approval:{token}:reject": AicoImDecision.REJECTED,
        }
        if request.kind is AicoImExchangeKind.APPROVAL
        else {f"aico:takeover:{token}:ack": AicoImDecision.ACKNOWLEDGED}
    )
    return values.get(value)


def _platform_delivery(
    intent: AicoImSendIntent,
    sent: SentMessage,
    owner: AicoImOwnerBinding,
) -> AicoImDeliveryReceipt:
    if sent.target != owner.target():
        raise ValueError("AICO IM platform acknowledged a different target")
    return AicoImDeliveryReceipt(
        request_sha256=intent.request_sha256,
        owner_binding_sha256=intent.owner_binding_sha256,
        ack_kind=AicoImDeliveryAckKind.PLATFORM_SEND_RESPONSE,
        platform_ack_sha256=_sha(
            "\0".join(
                (
                    sent.message_id,
                    canonical_sha256(sent.target),
                    sent.timestamp.isoformat(),
                )
            ).encode("utf-8")
        ),
        acknowledged_at=sent.timestamp,
    )


def _inbound_delivery(
    intent: AicoImSendIntent,
    incoming: IncomingMessage,
) -> AicoImDeliveryReceipt:
    return AicoImDeliveryReceipt(
        request_sha256=intent.request_sha256,
        owner_binding_sha256=intent.owner_binding_sha256,
        ack_kind=AicoImDeliveryAckKind.OWNER_INBOUND_RECONCILIATION,
        platform_ack_sha256=_sha(
            "\0".join(
                (
                    incoming.raw_ref,
                    canonical_sha256(incoming.source),
                    incoming.timestamp.isoformat(),
                )
            ).encode("utf-8")
        ),
        acknowledged_at=incoming.timestamp,
    )


def _validate_delivery(
    intent: AicoImSendIntent,
    delivery: AicoImDeliveryReceipt,
) -> None:
    if (
        delivery.request_sha256 != intent.request_sha256
        or delivery.owner_binding_sha256 != intent.owner_binding_sha256
    ):
        raise ValueError("AICO IM delivery receipt drifted")


def _validate_decision(
    request: AicoImExchangeRequest,
    owner: AicoImOwnerBinding,
    decision: AicoImDecisionReceipt,
) -> None:
    if (
        decision.kind is not request.kind
        or decision.contract_sha256 != request.contract_sha256
        or decision.task_id != request.task_id
        or decision.subject_sha256 != request.subject_sha256
        or decision.request_sha256 != canonical_sha256(request)
        or decision.owner_binding_sha256 != canonical_sha256(owner)
    ):
        raise ValueError("AICO IM decision receipt drifted")


def _validate_channel(channel: IMChannel, owner: AicoImOwnerBinding) -> None:
    if channel.name != owner.channel_name:
        raise ValueError("AICO IM channel does not match the owner binding")


def _matches_owner(owner: AicoImOwnerBinding, incoming: IncomingMessage) -> bool:
    return (
        incoming.channel_name == owner.channel_name
        and incoming.source == owner.target()
        and incoming.sender_id == owner.sender_id
        and incoming.timestamp.tzinfo is not None
        and incoming.timestamp.utcoffset() is not None
    )


def _request_token(request: AicoImExchangeRequest) -> str:
    return canonical_sha256(request)[:16]


def _read_owner_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("AICO IM artifact must be a regular non-symlink file")
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077
        or info.st_size > _MAX_EXCHANGE_FILE_BYTES
    ):
        raise ValueError("AICO IM artifact must be owner-only and bounded")
    return path.read_bytes()


def _model_bytes(value: FrozenModel) -> bytes:
    payload = value.model_dump_json(indent=2).encode("utf-8") + b"\n"
    if len(payload) > _MAX_EXCHANGE_FILE_BYTES:
        raise ValueError("AICO IM artifact exceeds bounded size")
    return payload


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
