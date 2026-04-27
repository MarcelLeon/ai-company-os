"""In-memory audit event recording for Phase 4 dogfooding."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from aico.core.models import AuditEvent, AuditEventType, RiskLevel, Task

EventIdFactory = Callable[[], str]


class InMemoryAuditLog:
    """Append-only audit log used until Phase 4 chooses durable storage."""

    def __init__(self, event_id_factory: EventIdFactory | None = None) -> None:
        self._event_id_factory = event_id_factory or _new_event_id
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
        return event

    def events(self, *, limit: int | None = None) -> tuple[AuditEvent, ...]:
        if limit is None:
            return tuple(self._events)
        return tuple(self._events[-limit:])


def _new_event_id() -> str:
    return str(uuid4())
