"""Lead-internal /timeline filtering and /rollback precision."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.core import (
    AuditEvent,
    AuditEventType,
    ChannelTarget,
    ExperienceMeta,
    InMemoryAuditLog,
    InMemoryUnifiedEventIndex,
    JsonlMemoryStore,
    MemoryAtom,
    MemoryEvidence,
    MemoryKind,
    MemoryScope,
    MemoryStatus,
    MessageContent,
    MessageKind,
    RiskLevel,
    UnifiedEventIndex,
)
from aico.core.models import IncomingMessage
from aico.core.timeline_rollback_commands import (
    RollbackCommandHandler,
    TimelineCommandHandler,
)

pytestmark = pytest.mark.asyncio


class _RecordingChannel:
    name = "telegram"

    def __init__(self) -> None:
        self.sent: list[MessageContent] = []

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> MessageContent:
        del target
        self.sent.append(content)
        return content

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> MessageContent:
        del target, message_id
        self.sent.append(content)
        return content


def _incoming(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="lead-1",
        mentions=(),
        content=MessageContent(kind=MessageKind.TEXT, text=text),
        timestamp=datetime(2026, 5, 31, 9, 0, tzinfo=UTC),
        raw_ref="raw-1",
    )


def _audit(*, event_id: str, when: datetime, task_id: str = "task-tl-1") -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        event_type=AuditEventType.TASK_SUBMITTED,
        task_id=task_id,
        actor_id="boss-1",
        target_persona="implementer",
        risk_level=RiskLevel.READ_ONLY,
        timestamp=when,
        trace_id=task_id,
    )


def _experience(memory_id: str) -> MemoryAtom:
    return MemoryAtom(
        memory_id=memory_id,
        claim="Always rerun adapter idle smoke before shipping.",
        evidence=(MemoryEvidence(ref="task:seed", source="dream_review"),),
        scope=MemoryScope.project("aico"),
        source="dream_review",
        confidence=0.7,
        created_by="lead-agent",
        status=MemoryStatus.ACTIVE,
        kind=MemoryKind.EXPERIENCE,
        experience=ExperienceMeta(applies_to=("implementer",)),
    )


def _index_factory(events: tuple[AuditEvent, ...]) -> Callable[[], UnifiedEventIndex]:
    def factory() -> UnifiedEventIndex:
        return InMemoryUnifiedEventIndex(audit_events=events)

    return factory


async def test_timeline_default_window_returns_recent_events() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)
    old = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)
    audit = (
        _audit(event_id="e-old", when=old, task_id="task-old"),
        _audit(event_id="e-now", when=now, task_id="task-recent"),
    )
    channel = _RecordingChannel()
    handler = TimelineCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        event_index_factory=_index_factory(audit),
    )

    await handler.handle_timeline(_incoming("/timeline --since 9999h"), "--since 9999h")

    body = channel.sent[-1].text
    assert "task-old" in body or "task-recent" in body
    assert "Timeline" in body


async def test_timeline_filters_by_source_and_trace() -> None:
    now = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)
    audit = (
        _audit(event_id="e-a", when=now, task_id="task-AAA"),
        _audit(event_id="e-b", when=now, task_id="task-BBB"),
    )
    channel = _RecordingChannel()
    handler = TimelineCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        event_index_factory=_index_factory(audit),
    )

    await handler.handle_timeline(
        _incoming("/timeline --source audit --trace task-AAA --since 9999h"),
        "--source audit --trace task-AAA --since 9999h",
    )

    body = channel.sent[-1].text
    assert "task-AAA" in body
    assert "task-BBB" not in body


async def test_timeline_rejects_unknown_option() -> None:
    channel = _RecordingChannel()
    handler = TimelineCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        event_index_factory=_index_factory(()),
    )

    await handler.handle_timeline(_incoming("/timeline --bogus 1"), "--bogus 1")

    assert "Usage" in channel.sent[-1].text


async def test_rollback_memory_archives_and_audits(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    audit_log = InMemoryAuditLog(event_id_factory=lambda: "evt-rb-1")
    store.append_atom(
        MemoryAtom(
            memory_id="mem-rb-1",
            claim="Boss prefers concise reports.",
            evidence=(MemoryEvidence(ref="raw:1", source="boss"),),
            scope=MemoryScope.project("aico"),
            source="boss",
            confidence=1.0,
            created_by="boss-1",
        )
    )
    channel = _RecordingChannel()
    handler = RollbackCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        memory_store=store,
        audit_log=audit_log,
    )

    await handler.handle_rollback(_incoming("/rollback memory mem-rb-1"), "memory mem-rb-1")

    archived = store.get_atom("mem-rb-1")
    assert archived is not None
    assert archived.status is MemoryStatus.ARCHIVED
    events = audit_log.events(limit=None)
    assert events[-1].event_type is AuditEventType.ROLLBACK_PERFORMED
    assert "mem-rb-1" in (events[-1].detail or "")


async def test_rollback_experience_reverts_to_candidate(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    audit_log = InMemoryAuditLog(event_id_factory=lambda: "evt-rb-2")
    store.append_atom(_experience("mem-exp-rb"))
    channel = _RecordingChannel()
    handler = RollbackCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        memory_store=store,
        audit_log=audit_log,
    )

    await handler.handle_rollback(
        _incoming("/rollback experience mem-exp-rb"), "experience mem-exp-rb"
    )

    reverted = store.get_atom("mem-exp-rb")
    assert reverted is not None
    assert reverted.status is MemoryStatus.CANDIDATE
    events = audit_log.events(limit=None)
    assert events[-1].event_type is AuditEventType.ROLLBACK_PERFORMED


async def test_rollback_task_only_writes_audit(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    audit_log = InMemoryAuditLog(event_id_factory=lambda: "evt-rb-3")
    channel = _RecordingChannel()
    handler = RollbackCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        memory_store=store,
        audit_log=audit_log,
    )

    await handler.handle_rollback(_incoming("/rollback task task-123"), "task task-123")

    events = audit_log.events(limit=None)
    assert events[-1].event_type is AuditEventType.ROLLBACK_PERFORMED
    body = channel.sent[-1].text
    assert "files/shell unchanged" in body or "files, shell" in body


async def test_rollback_rejects_wrong_kind(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    audit_log = InMemoryAuditLog(event_id_factory=lambda: "evt-rb-4")
    store.append_atom(_experience("mem-exp-mix"))
    channel = _RecordingChannel()
    handler = RollbackCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        memory_store=store,
        audit_log=audit_log,
    )

    await handler.handle_rollback(_incoming("/rollback memory mem-exp-mix"), "memory mem-exp-mix")

    atom = store.get_atom("mem-exp-mix")
    assert atom is not None
    assert atom.status is MemoryStatus.ACTIVE  # not rolled back
    assert "use /rollback experience" in channel.sent[-1].text


async def test_rollback_unknown_id(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    channel = _RecordingChannel()
    handler = RollbackCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        memory_store=store,
        audit_log=InMemoryAuditLog(),
    )

    await handler.handle_rollback(_incoming("/rollback memory mem-missing"), "memory mem-missing")

    assert "Unknown memory id" in channel.sent[-1].text


async def test_rollback_usage_when_no_args(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    channel = _RecordingChannel()
    handler = RollbackCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        memory_store=store,
        audit_log=InMemoryAuditLog(),
    )

    await handler.handle_rollback(_incoming("/rollback"), "")

    assert "Usage" in channel.sent[-1].text
