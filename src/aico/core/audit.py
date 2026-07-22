"""Audit event recording for Phase 4 dogfooding."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from aico.core.audit_ledger import AuditLedger, read_audit_ledger
from aico.core.models import AuditEvent, AuditEventType, RiskLevel, Task

EventIdFactory = Callable[[], str]


class AuditSink(Protocol):
    """Persist or forward audit events after they are recorded."""

    def write(self, event: AuditEvent) -> None: ...


class JsonlAuditSink:
    """Append audit events as one JSON object per line."""

    def __init__(self, path: Path) -> None:
        self._ledger = AuditLedger(path)

    def write(self, event: AuditEvent) -> None:
        self._ledger.append(event)


def read_jsonl_audit_events(path: Path) -> tuple[AuditEvent, ...]:
    return read_audit_ledger(path)


class InMemoryAuditLog:
    """Append-only audit log with optional durable sinks."""

    def __init__(
        self,
        event_id_factory: EventIdFactory | None = None,
        sinks: tuple[AuditSink, ...] = (),
        initial_events: tuple[AuditEvent, ...] = (),
    ) -> None:
        self._event_id_factory = event_id_factory or _new_event_id
        self._sinks = sinks
        self._events: list[AuditEvent] = []
        self._events_by_id: dict[str, AuditEvent] = {}
        for event in initial_events:
            existing = self._events_by_id.get(event.event_id)
            if existing is not None:
                if existing != event:
                    raise ValueError(f"audit event id collision: {event.event_id}")
                continue
            self._events.append(event)
            self._events_by_id[event.event_id] = event

    def record(
        self,
        event_type: AuditEventType,
        task: Task,
        *,
        actor_id: str | None = None,
        adapter_name: str | None = None,
        risk_level: RiskLevel = RiskLevel.READ_ONLY,
        detail: str | None = None,
        trace_id: str | None = None,
    ) -> AuditEvent:
        return self.record_event(
            event_type,
            task_id=task.task_id,
            actor_id=actor_id or task.requester_id,
            target_persona=task.target_persona,
            adapter_name=adapter_name,
            risk_level=risk_level,
            detail=detail,
            trace_id=trace_id or task.trace_id or task.task_id,
        )

    def record_event(
        self,
        event_type: AuditEventType,
        *,
        task_id: str,
        actor_id: str,
        target_persona: str,
        adapter_name: str | None = None,
        risk_level: RiskLevel = RiskLevel.READ_ONLY,
        detail: str | None = None,
        trace_id: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=self._event_id_factory(),
            event_type=event_type,
            task_id=task_id,
            actor_id=actor_id,
            target_persona=target_persona,
            adapter_name=adapter_name,
            risk_level=risk_level,
            detail=detail,
            trace_id=trace_id or task_id,
        )
        return self.record_existing(event)

    def record_existing(self, event: AuditEvent) -> AuditEvent:
        """Record an event with an already allocated id, idempotently."""
        existing = self._events_by_id.get(event.event_id)
        if existing is not None:
            if existing != event:
                raise ValueError(f"audit event id collision: {event.event_id}")
            return existing
        for sink in self._sinks:
            sink.write(event)
        self._events.append(event)
        self._events_by_id[event.event_id] = event
        return event

    def events(self, *, limit: int | None = None) -> tuple[AuditEvent, ...]:
        if limit is None:
            return tuple(self._events)
        return tuple(self._events[-limit:])


def _new_event_id() -> str:
    return str(uuid4())
