"""Audit event recording for Phase 4 dogfooding."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from aico.core.models import AuditEvent, AuditEventType, RiskLevel, Task

EventIdFactory = Callable[[], str]


class AuditSink(Protocol):
    """Persist or forward audit events after they are recorded."""

    def write(self, event: AuditEvent) -> None: ...


class JsonlAuditSink:
    """Append audit events as one JSON object per line."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def write(self, event: AuditEvent) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        with self._path.open("a", encoding="utf-8") as file:
            file.write(f"{line}\n")


class InMemoryAuditLog:
    """Append-only audit log with optional durable sinks."""

    def __init__(
        self,
        event_id_factory: EventIdFactory | None = None,
        sinks: tuple[AuditSink, ...] = (),
    ) -> None:
        self._event_id_factory = event_id_factory or _new_event_id
        self._sinks = sinks
        self._events: list[AuditEvent] = []

    def record(
        self,
        event_type: AuditEventType,
        task: Task,
        *,
        actor_id: str | None = None,
        adapter_name: str | None = None,
        risk_level: RiskLevel = RiskLevel.READ_ONLY,
        detail: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=self._event_id_factory(),
            event_type=event_type,
            task_id=task.task_id,
            actor_id=actor_id or task.requester_id,
            target_persona=task.target_persona,
            adapter_name=adapter_name,
            risk_level=risk_level,
            detail=detail,
        )
        self._events.append(event)
        for sink in self._sinks:
            sink.write(event)
        return event

    def events(self, *, limit: int | None = None) -> tuple[AuditEvent, ...]:
        if limit is None:
            return tuple(self._events)
        return tuple(self._events[-limit:])


def _new_event_id() -> str:
    return str(uuid4())
