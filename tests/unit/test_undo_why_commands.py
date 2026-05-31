"""Boss-only /undo and /why command handlers + recent activity in inbox/morning."""

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
from aico.core.undo_why_commands import UndoCommandHandler, WhyCommandHandler

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


def _incoming(text: str = "/undo") -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="boss-1",
        mentions=(),
        content=MessageContent(kind=MessageKind.TEXT, text=text),
        timestamp=datetime(2026, 5, 31, 9, 0, tzinfo=UTC),
        raw_ref="raw-1",
    )


def _index_factory(
    store: JsonlMemoryStore,
    *,
    audit: tuple[AuditEvent, ...] = (),
) -> Callable[[], UnifiedEventIndex]:
    def factory() -> UnifiedEventIndex:
        atoms = store.list_atoms(MemoryScope.project("aico"), include_archived=True)
        return InMemoryUnifiedEventIndex(audit_events=audit, memory_atoms=atoms)

    return factory


def _active_experience(memory_id: str) -> MemoryAtom:
    return MemoryAtom(
        memory_id=memory_id,
        claim="Retry adapter with verbose logging after idle timeout.",
        evidence=(MemoryEvidence(ref=f"task:{memory_id}", source="dream_review"),),
        scope=MemoryScope.project("aico"),
        source="dream_review",
        confidence=0.6,
        created_by="lead-agent",
        status=MemoryStatus.ACTIVE,
        kind=MemoryKind.EXPERIENCE,
        experience=ExperienceMeta(applies_to=("implementer",)),
    )


async def test_undo_with_no_undoable_events_replies_nothing_to_undo(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    channel = _RecordingChannel()
    handler = UndoCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        memory_store=store,
        event_index_factory=_index_factory(store),
    )

    await handler.handle_undo(_incoming(), "")

    assert "Nothing to undo" in channel.sent[-1].text
    assert "does not revert files, shell commands, or sent IM messages" in channel.sent[-1].text


async def test_undo_reverses_recent_experience_promotion(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    channel = _RecordingChannel()
    handler = UndoCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        memory_store=store,
        event_index_factory=_index_factory(store),
    )
    store.append_atom(_active_experience("mem-exp-active"))

    await handler.handle_undo(_incoming(), "")

    reverted = store.get_atom("mem-exp-active")
    assert reverted is not None
    assert reverted.status is MemoryStatus.CANDIDATE
    assert "reverted" in channel.sent[-1].text.lower()


async def test_undo_archives_recent_fact_memory(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    channel = _RecordingChannel()
    handler = UndoCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        memory_store=store,
        event_index_factory=_index_factory(store),
    )
    store.append_atom(
        MemoryAtom(
            memory_id="mem-fact-undo",
            claim="Boss prefers concise reports.",
            evidence=(MemoryEvidence(ref="raw:1", source="boss"),),
            scope=MemoryScope.project("aico"),
            source="boss_remember_command",
            confidence=1.0,
            created_by="boss-1",
        )
    )

    await handler.handle_undo(_incoming(), "")

    atom = store.get_atom("mem-fact-undo")
    assert atom is not None
    assert atom.status is MemoryStatus.ARCHIVED


async def test_why_with_no_index_reports_no_events(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    channel = _RecordingChannel()
    handler = WhyCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        event_index_factory=_index_factory(store),
    )

    await handler.handle_why(_incoming("/why"), "")

    assert "no events found" in channel.sent[-1].text.lower()


async def test_why_walks_trace_for_short_id(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    audit = (
        AuditEvent(
            event_id="evt-1",
            event_type=AuditEventType.TASK_SUBMITTED,
            task_id="task-1234567890",
            actor_id="boss-1",
            target_persona="implementer",
            risk_level=RiskLevel.READ_ONLY,
            timestamp=datetime(2026, 5, 31, 9, 0, tzinfo=UTC),
            trace_id="task-1234567890",
        ),
        AuditEvent(
            event_id="evt-2",
            event_type=AuditEventType.TASK_COMPLETED,
            task_id="task-1234567890",
            actor_id="boss-1",
            target_persona="implementer",
            risk_level=RiskLevel.READ_ONLY,
            timestamp=datetime(2026, 5, 31, 9, 1, tzinfo=UTC),
            trace_id="task-1234567890",
        ),
    )
    channel = _RecordingChannel()
    handler = WhyCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        event_index_factory=_index_factory(store, audit=audit),
    )

    await handler.handle_why(_incoming("/why task-123"), "task-123")

    body = channel.sent[-1].text
    assert "task-123" in body
    assert "task_submitted" in body
    assert "task_completed" in body
