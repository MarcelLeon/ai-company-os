"""Derived, read-only unified view across audit / memory / task event sources.

This index does NOT own truth. Audit JSONL, Memory JSONL, and the SQLite
task state store remain the canonical sources. The unified index is rebuilt
from those sources and can be discarded at any time without data loss.

It exists so that L5 boss commands (`/why`, `/undo`) and the L6 aico-view
read API can answer "what happened in this trace" with a single lookup,
instead of stitching together three sources by hand.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from aico.core.command_messages import short_id_text
from aico.core.memory import MemoryAtom
from aico.core.models import AuditEvent, TaskSnapshot, utc_now


class UnifiedEventSource(StrEnum):
    AUDIT = "audit"
    MEMORY = "memory"
    TASK = "task"


@dataclass(frozen=True)
class UnifiedEvent:
    """A single point in the cross-source timeline, keyed by trace_id."""

    event_id: str
    trace_id: str
    source: UnifiedEventSource
    short_id: str
    kind: str
    timestamp: datetime
    summary: str


class UnifiedEventIndex(Protocol):
    """Read-only index across audit / memory / task event sources."""

    def all_events(self) -> tuple[UnifiedEvent, ...]: ...

    def events_for_trace(self, trace_id: str) -> tuple[UnifiedEvent, ...]: ...

    def recent(self, *, limit: int) -> tuple[UnifiedEvent, ...]: ...


class InMemoryUnifiedEventIndex:
    """Aggregate `UnifiedEvent`s by trace_id, sorted by timestamp.

    Constructed from in-memory snapshots of the three sources. Callers
    rebuild after material changes; we deliberately avoid a long-running
    subscription mechanism to keep the index a pure derivation.
    """

    def __init__(
        self,
        *,
        audit_events: tuple[AuditEvent, ...] = (),
        memory_atoms: tuple[MemoryAtom, ...] = (),
        task_snapshots: tuple[TaskSnapshot, ...] = (),
    ) -> None:
        events: list[UnifiedEvent] = []
        for audit in audit_events:
            events.append(_from_audit(audit))
        for atom in memory_atoms:
            events.append(_from_memory(atom))
        for snapshot in task_snapshots:
            events.append(_from_task(snapshot))
        self._events: tuple[UnifiedEvent, ...] = tuple(
            sorted(events, key=lambda event: event.timestamp)
        )
        index: dict[str, list[UnifiedEvent]] = {}
        for event in self._events:
            index.setdefault(event.trace_id, []).append(event)
        self._by_trace: dict[str, tuple[UnifiedEvent, ...]] = {
            trace_id: tuple(items) for trace_id, items in index.items()
        }

    def all_events(self) -> tuple[UnifiedEvent, ...]:
        return self._events

    def events_for_trace(self, trace_id: str) -> tuple[UnifiedEvent, ...]:
        return self._by_trace.get(trace_id, ())

    def recent(self, *, limit: int) -> tuple[UnifiedEvent, ...]:
        if limit <= 0:
            return ()
        return self._events[-limit:]


def _from_audit(audit: AuditEvent) -> UnifiedEvent:
    return UnifiedEvent(
        event_id=audit.event_id,
        trace_id=audit.trace_id or audit.task_id,
        source=UnifiedEventSource.AUDIT,
        short_id=short_id_text(audit.task_id),
        kind=audit.event_type.value,
        timestamp=audit.timestamp,
        summary=audit.detail or audit.event_type.value,
    )


def _from_memory(atom: MemoryAtom) -> UnifiedEvent:
    return UnifiedEvent(
        event_id=atom.memory_id,
        trace_id=atom.trace_id or atom.memory_id,
        source=UnifiedEventSource.MEMORY,
        short_id=short_id_text(atom.memory_id),
        kind=f"memory:{atom.kind.value}:{atom.status.value}",
        timestamp=atom.archived_at or atom.created_at,
        summary=atom.claim,
    )


def _from_task(snapshot: TaskSnapshot) -> UnifiedEvent:
    return UnifiedEvent(
        event_id=snapshot.task_id,
        trace_id=snapshot.task_id,
        source=UnifiedEventSource.TASK,
        short_id=short_id_text(snapshot.task_id),
        kind=f"task:{snapshot.status.value}",
        timestamp=snapshot.updated_at,
        summary=snapshot.reason or snapshot.status.value,
    )


def short_event_id(value: str) -> str:
    """Render a unified event id for IM display."""
    return short_id_text(value)


def short_memory_id(value: str) -> str:
    """Render a memory id for IM display."""
    return short_id_text(value)


def short_trace_id(value: str) -> str:
    """Render a trace id for IM display."""
    return short_id_text(value)


def now() -> datetime:
    """Re-export utc_now for callers that want consistent timestamps."""
    return utc_now()
