"""Boss-only /undo and /why commands for absence-first audit access.

Hard boundary (ADR-0032):
- /undo reverses AICO-internal state changes ONLY: memory atoms, experience
  lifecycle transitions, project appointments. It does NOT revert anything
  written to disk by an adapter, any shell command that already ran, or any
  IM message that was already delivered. Those belong to git, the file
  system, and the IM platform respectively.
- /why answers "what produced this event" by walking the UnifiedEventIndex
  for the trace_id derived from the short id the boss quoted.

Both commands are read-only with respect to truth sources (audit JSONL,
memory JSONL, SQLite task store) — undo writes a new reverse event rather
than rewriting history.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from aico.channel import IMChannel
from aico.core.command_messages import short_id_text
from aico.core.memory import MemoryStatus, MemoryStore
from aico.core.message_rendering import rich_text_message
from aico.core.models import IncomingMessage, MessageContent, utc_now
from aico.core.unified_event import (
    UnifiedEvent,
    UnifiedEventIndex,
    UnifiedEventSource,
)


class EventIndexFactory(Protocol):
    def __call__(self) -> UnifiedEventIndex: ...


_UNDOABLE_MEMORY_PREFIXES = ("memory:fact:", "memory:experience:")
_RECENT_WINDOW = timedelta(hours=24)


class UndoCommandHandler:
    """Reverse the most recent AICO-internal mutation when the boss asks."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        memory_store: MemoryStore | None,
        event_index_factory: EventIndexFactory,
    ) -> None:
        self._channel = channel
        self._memory_store = memory_store
        self._event_index_factory = event_index_factory

    async def handle_undo(self, message: IncomingMessage, payload: str) -> None:
        del payload
        if self._memory_store is None:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text="Undo needs shared memory. Set AICO_MEMORY_PATH and restart AICO."
                ),
            )
            return
        index = self._event_index_factory()
        cutoff = utc_now() - _RECENT_WINDOW
        candidate = _most_recent_undoable(index, cutoff=cutoff)
        if candidate is None:
            await self._channel.send_message(
                message.source,
                rich_text_message(
                    "\n".join(
                        (
                            "# Nothing to undo",
                            "scope: AICO-internal mutations in the last 24h",
                            "",
                            "Note:",
                            "- /undo reverses memory writes and experience promotions only.",
                            "- It does not revert files, shell commands, or sent IM messages.",
                        )
                    )
                ),
            )
            return
        await self._undo_memory_event(message, candidate)

    async def _undo_memory_event(
        self,
        message: IncomingMessage,
        event: UnifiedEvent,
    ) -> None:
        store = self._memory_store
        assert store is not None
        atom = store.get_atom(event.event_id)
        if atom is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Memory {event.event_id} no longer exists; cannot undo."),
            )
            return

        if event.kind.startswith("memory:experience:") and atom.status is MemoryStatus.ACTIVE:
            reverted = atom.model_copy(update={"status": MemoryStatus.CANDIDATE})
            store.append_atom(reverted)
            await self._channel.send_message(
                message.source,
                _undo_message(
                    f"Promotion of experience {short_id_text(atom.memory_id)} reverted",
                    detail=f"status: active -> candidate (memory_id: {atom.memory_id})",
                ),
            )
            return

        if atom.status is MemoryStatus.ARCHIVED:
            restored = atom.model_copy(
                update={
                    "status": MemoryStatus.ACTIVE,
                    "archived_at": None,
                    "reason": None,
                }
            )
            store.append_atom(restored)
            await self._channel.send_message(
                message.source,
                _undo_message(
                    f"Archive of {short_id_text(atom.memory_id)} reverted",
                    detail=f"status: archived -> active (memory_id: {atom.memory_id})",
                ),
            )
            return

        store.archive(atom.memory_id, reason="boss /undo")
        await self._channel.send_message(
            message.source,
            _undo_message(
                f"Recent memory write {short_id_text(atom.memory_id)} archived",
                detail=f"status: {atom.status.value} -> archived (memory_id: {atom.memory_id})",
                kind_label=f"kind: {atom.kind.value}",
            ),
        )


class WhyCommandHandler:
    """Explain what produced an event the boss saw, by walking trace_id."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        event_index_factory: EventIndexFactory,
    ) -> None:
        self._channel = channel
        self._event_index_factory = event_index_factory

    async def handle_why(self, message: IncomingMessage, payload: str) -> None:
        query = payload.strip()
        index = self._event_index_factory()
        events = _events_for_query(index, query)
        if not events:
            await self._channel.send_message(
                message.source,
                _why_empty_message(query),
            )
            return
        await self._channel.send_message(
            message.source,
            _why_message(query, events),
        )


def _most_recent_undoable(
    index: UnifiedEventIndex,
    *,
    cutoff: datetime,
) -> UnifiedEvent | None:
    all_events = index.all_events()
    for event in reversed(all_events):
        if event.timestamp < cutoff:
            return None
        if event.source is UnifiedEventSource.MEMORY and event.kind.startswith(
            _UNDOABLE_MEMORY_PREFIXES
        ):
            return event
    return None


def _events_for_query(
    index: UnifiedEventIndex,
    query: str,
) -> tuple[UnifiedEvent, ...]:
    if not query:
        recent = index.recent(limit=1)
        if not recent:
            return ()
        return index.events_for_trace(recent[-1].trace_id)
    normalized = query.lower()
    for event in index.all_events():
        candidates = (
            event.event_id.lower(),
            event.short_id.lower(),
            event.trace_id.lower(),
            short_id_text(event.trace_id).lower(),
        )
        if normalized in candidates or any(c.startswith(normalized) for c in candidates):
            return index.events_for_trace(event.trace_id)
    return ()


def _undo_message(
    headline: str,
    *,
    detail: str,
    kind_label: str | None = None,
) -> MessageContent:
    lines = [
        f"# {headline}",
        detail,
    ]
    if kind_label is not None:
        lines.append(kind_label)
    lines.extend(
        (
            "",
            "Scope:",
            "- AICO-internal state only.",
            "- Files, shell side effects, and sent IM messages are NOT reverted.",
        )
    )
    return rich_text_message("\n".join(lines))


def _why_message(query: str, events: tuple[UnifiedEvent, ...]) -> MessageContent:
    head = events[0]
    lines = [
        f"# Why: {query or 'most recent event'}",
        f"trace_id: {short_id_text(head.trace_id)}",
        "",
        "Events (oldest first):",
    ]
    for event in events:
        ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%SZ")
        lines.append(
            f"- {ts} [{event.source.value}] {event.kind} {event.short_id} — {event.summary}"
        )
    return rich_text_message("\n".join(lines))


def _why_empty_message(query: str) -> MessageContent:
    lines = ["# Why: no events found"]
    if query:
        lines.append(f"query: {query}")
    lines.extend(
        (
            "",
            "Tip:",
            "- /why <short_id> looks up the trace for a task or memory id.",
            "- /why (no argument) explains the most recent event.",
        )
    )
    return rich_text_message("\n".join(lines))


def recent_activity_lines(index: UnifiedEventIndex, *, limit: int = 5) -> list[str]:
    """Render a short 'Recent activity' block for /inbox and /morning."""
    events = index.recent(limit=limit)
    if not events:
        return ["", "Recent activity:", "- none"]
    lines = ["", "Recent activity:"]
    for event in events:
        ts = event.timestamp.strftime("%H:%M")
        lines.append(
            f"- {ts} [{event.source.value}] {event.kind} {event.short_id} — {event.summary}"
        )
    lines.append("- ask /why <short_id> for the full trace")
    return lines
