"""Lead-internal /timeline and /rollback commands.

/timeline: filtered view of the UnifiedEventIndex (source, role, hours).
/rollback memory|experience|task <id>: precise reversal of AICO-internal
state changes; same scope boundary as /undo (no git/shell/file) but
explicit instead of "most recent".

Both commands write a ROLLBACK_PERFORMED audit event so the reversal
is itself auditable. The boss does not normally use these; they exist
so a lead can clean up after their team without paging the boss.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from aico.channel import IMChannel
from aico.core.audit import InMemoryAuditLog
from aico.core.command_messages import short_id_text
from aico.core.memory import MemoryKind, MemoryStatus, MemoryStore
from aico.core.message_rendering import rich_text_message
from aico.core.models import (
    AuditEventType,
    IncomingMessage,
    MessageContent,
    RiskLevel,
    utc_now,
)
from aico.core.unified_event import (
    UnifiedEvent,
    UnifiedEventIndex,
    UnifiedEventSource,
)


class EventIndexFactory(Protocol):
    def __call__(self) -> UnifiedEventIndex: ...


_DEFAULT_TIMELINE_WINDOW = timedelta(hours=24)
_TIMELINE_USAGE = (
    "Usage: /timeline [--since 24h] [--source audit|memory|task] [--limit 30] [--trace <id>]"
)
_ROLLBACK_USAGE = (
    "Usage:\n- /rollback memory <id>\n- /rollback experience <id>\n- /rollback task <id>"
)


class TimelineCommandHandler:
    """Filtered /timeline output for lead inspection."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        event_index_factory: EventIndexFactory,
    ) -> None:
        self._channel = channel
        self._event_index_factory = event_index_factory

    async def handle_timeline(self, message: IncomingMessage, payload: str) -> None:
        options = _parse_timeline_options(payload)
        if options is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=_TIMELINE_USAGE),
            )
            return
        since_hours, source_filter, limit, trace_filter = options
        index = self._event_index_factory()
        cutoff = utc_now() - timedelta(hours=since_hours)
        events = _filter_events(
            index.all_events(),
            cutoff=cutoff,
            source_filter=source_filter,
            trace_filter=trace_filter,
            limit=limit,
        )
        await self._channel.send_message(
            message.source,
            _render_timeline_message(
                events,
                since_hours=since_hours,
                source_filter=source_filter,
                trace_filter=trace_filter,
            ),
        )


class RollbackCommandHandler:
    """Precise /rollback for AICO-internal state, with ROLLBACK_PERFORMED audit."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        memory_store: MemoryStore | None,
        audit_log: InMemoryAuditLog | None,
    ) -> None:
        self._channel = channel
        self._memory_store = memory_store
        self._audit_log = audit_log

    async def handle_rollback(self, message: IncomingMessage, payload: str) -> None:
        kind, _, target_id = payload.partition(" ")
        kind = kind.strip().lower()
        target_id = target_id.strip()
        if kind in {"memory", "experience"} and not target_id:
            await self._channel.send_message(
                message.source,
                MessageContent(text=_ROLLBACK_USAGE),
            )
            return
        if kind == "memory":
            await self._rollback_memory(message, target_id, kind_label="memory")
            return
        if kind == "experience":
            await self._rollback_memory(message, target_id, kind_label="experience")
            return
        if kind == "task":
            await self._rollback_task(message, target_id)
            return
        await self._channel.send_message(
            message.source,
            MessageContent(text=_ROLLBACK_USAGE),
        )

    async def _rollback_memory(
        self,
        message: IncomingMessage,
        memory_id: str,
        *,
        kind_label: str,
    ) -> None:
        if self._memory_store is None:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text="Rollback needs shared memory. Set AICO_MEMORY_PATH and restart AICO."
                ),
            )
            return
        atom = self._memory_store.get_atom(memory_id)
        if atom is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Unknown memory id: {memory_id}"),
            )
            return
        expected_kind = MemoryKind.EXPERIENCE if kind_label == "experience" else MemoryKind.FACT
        if atom.kind is not expected_kind:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=(
                        f"Memory {memory_id} is kind={atom.kind.value}; "
                        f"use /rollback {atom.kind.value} {memory_id} instead."
                    )
                ),
            )
            return
        if kind_label == "experience" and atom.status is MemoryStatus.ACTIVE:
            reverted = atom.model_copy(update={"status": MemoryStatus.CANDIDATE})
            self._memory_store.append_atom(reverted)
            detail = f"experience {memory_id} active -> candidate"
        else:
            archived = self._memory_store.archive(memory_id, reason="lead /rollback")
            del archived
            detail = f"{kind_label} {memory_id} -> archived"
        self._record_rollback_audit(
            message=message,
            task_id=f"memory:{memory_id}",
            detail=detail,
        )
        await self._channel.send_message(
            message.source,
            _render_rollback_message(detail),
        )

    async def _rollback_task(self, message: IncomingMessage, task_id: str) -> None:
        if not task_id:
            await self._channel.send_message(
                message.source,
                MessageContent(text=_ROLLBACK_USAGE),
            )
            return
        # Task rollback in this sprint only writes the audit marker; M-future will
        # cascade-undo memory/experience writes that share the same trace_id.
        detail = f"task {task_id} marked as rolled back (AICO state only; files/shell unchanged)"
        self._record_rollback_audit(
            message=message,
            task_id=task_id,
            detail=detail,
        )
        await self._channel.send_message(
            message.source,
            _render_rollback_message(detail),
        )

    def _record_rollback_audit(
        self,
        *,
        message: IncomingMessage,
        task_id: str,
        detail: str,
    ) -> None:
        if self._audit_log is None:
            return
        self._audit_log.record_event(
            AuditEventType.ROLLBACK_PERFORMED,
            task_id=task_id,
            actor_id=message.sender_id,
            target_persona="lead",
            risk_level=RiskLevel.READ_ONLY,
            detail=detail,
        )


def _parse_timeline_options(
    payload: str,
) -> tuple[float, UnifiedEventSource | None, int, str | None] | None:
    since_hours = 24.0
    source_filter: UnifiedEventSource | None = None
    limit = 30
    trace_filter: str | None = None
    tokens = payload.split()
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "--since" and i + 1 < len(tokens):
            try:
                since_hours = _parse_duration_hours(tokens[i + 1])
            except ValueError:
                return None
            i += 2
            continue
        if token == "--source" and i + 1 < len(tokens):
            try:
                source_filter = UnifiedEventSource(tokens[i + 1].lower())
            except ValueError:
                return None
            i += 2
            continue
        if token == "--limit" and i + 1 < len(tokens):
            try:
                limit = max(1, min(200, int(tokens[i + 1])))
            except ValueError:
                return None
            i += 2
            continue
        if token == "--trace" and i + 1 < len(tokens):
            trace_filter = tokens[i + 1]
            i += 2
            continue
        return None
    return since_hours, source_filter, limit, trace_filter


def _parse_duration_hours(value: str) -> float:
    value = value.strip().lower()
    if value.endswith("h"):
        return float(value[:-1])
    if value.endswith("d"):
        return float(value[:-1]) * 24
    if value.endswith("m"):
        return float(value[:-1]) / 60
    return float(value)


def _filter_events(
    events: tuple[UnifiedEvent, ...],
    *,
    cutoff: datetime,
    source_filter: UnifiedEventSource | None,
    trace_filter: str | None,
    limit: int,
) -> tuple[UnifiedEvent, ...]:
    matches = [
        event
        for event in events
        if event.timestamp >= cutoff
        and (source_filter is None or event.source is source_filter)
        and (trace_filter is None or event.trace_id.startswith(trace_filter))
    ]
    return tuple(matches[-limit:])


def _render_timeline_message(
    events: tuple[UnifiedEvent, ...],
    *,
    since_hours: float,
    source_filter: UnifiedEventSource | None,
    trace_filter: str | None,
) -> MessageContent:
    header_parts = [f"Timeline (last {since_hours:g}h"]
    if source_filter is not None:
        header_parts.append(f"source={source_filter.value}")
    if trace_filter is not None:
        header_parts.append(f"trace~{trace_filter}")
    header = ", ".join(header_parts) + ")"
    lines = [f"# {header}"]
    if not events:
        lines.append("- no events in window")
    else:
        for event in events:
            ts = event.timestamp.strftime("%m-%d %H:%M")
            lines.append(
                f"- {ts} [{event.source.value}] {event.kind} {event.short_id} — {event.summary}"
            )
    lines.append("")
    lines.append("Tip:")
    lines.append("- /why <short_id> opens the full trace")
    return rich_text_message("\n".join(lines))


def _render_rollback_message(detail: str) -> MessageContent:
    return rich_text_message(
        "\n".join(
            (
                "# Rollback performed",
                detail,
                "",
                "Scope:",
                "- AICO-internal state only.",
                "- Files, shell side effects, and sent IM messages are NOT reverted.",
            )
        )
    )


def short_event_id_text(value: str) -> str:
    """Helper used by tests; alias for short_id_text to keep call sites obvious."""
    return short_id_text(value)
