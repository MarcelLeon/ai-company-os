"""UnifiedEventIndex aggregation and trace_id traversal."""

from __future__ import annotations

from datetime import UTC, datetime

from aico.core import (
    AuditEvent,
    AuditEventType,
    InMemoryUnifiedEventIndex,
    MemoryAtom,
    MemoryEvidence,
    MemoryKind,
    MemoryScope,
    MemoryStatus,
    RiskLevel,
    TaskSnapshot,
    TaskStatus,
    UnifiedEventSource,
)


def _audit(
    *,
    event_id: str,
    task_id: str,
    trace_id: str | None,
    when: datetime,
    event_type: AuditEventType = AuditEventType.TASK_SUBMITTED,
    detail: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        event_type=event_type,
        task_id=task_id,
        actor_id="boss",
        target_persona="implementer",
        risk_level=RiskLevel.READ_ONLY,
        detail=detail,
        timestamp=when,
        trace_id=trace_id,
    )


def _memory(*, memory_id: str, trace_id: str | None, when: datetime) -> MemoryAtom:
    return MemoryAtom(
        memory_id=memory_id,
        claim="Boss confirmed the release plan.",
        evidence=(MemoryEvidence(ref=f"audit:{memory_id}", source="audit"),),
        scope=MemoryScope.project("aico"),
        source="boss_feedback",
        confidence=0.9,
        created_by="lead-agent",
        created_at=when,
        status=MemoryStatus.ACTIVE,
        kind=MemoryKind.FACT,
        trace_id=trace_id,
    )


def _task_snapshot(*, task_id: str, when: datetime) -> TaskSnapshot:
    return TaskSnapshot(
        task_id=task_id,
        target_persona="implementer",
        adapter_name="claude-code",
        status=TaskStatus.RUNNING,
        risk_level=RiskLevel.READ_ONLY,
        created_at=when,
        updated_at=when,
    )


def test_unified_event_index_groups_events_by_trace_id() -> None:
    t0 = datetime(2026, 5, 31, 9, 0, tzinfo=UTC)
    t1 = datetime(2026, 5, 31, 9, 1, tzinfo=UTC)
    t2 = datetime(2026, 5, 31, 9, 2, tzinfo=UTC)
    audit_a = _audit(event_id="a1", task_id="task-1", trace_id="task-1", when=t0)
    audit_b = _audit(
        event_id="a2",
        task_id="task-1",
        trace_id="task-1",
        when=t1,
        event_type=AuditEventType.TASK_COMPLETED,
    )
    memory = _memory(memory_id="mem-1", trace_id="task-1", when=t2)

    index = InMemoryUnifiedEventIndex(
        audit_events=(audit_a, audit_b),
        memory_atoms=(memory,),
    )

    trace_events = index.events_for_trace("task-1")
    assert len(trace_events) == 3
    assert [event.source for event in trace_events] == [
        UnifiedEventSource.AUDIT,
        UnifiedEventSource.AUDIT,
        UnifiedEventSource.MEMORY,
    ]


def test_unified_event_index_falls_back_to_id_when_trace_missing() -> None:
    t0 = datetime(2026, 5, 31, 9, 0, tzinfo=UTC)
    audit = _audit(event_id="a1", task_id="task-7", trace_id=None, when=t0)
    memory = _memory(memory_id="mem-7", trace_id=None, when=t0)
    snapshot = _task_snapshot(task_id="task-9", when=t0)

    index = InMemoryUnifiedEventIndex(
        audit_events=(audit,),
        memory_atoms=(memory,),
        task_snapshots=(snapshot,),
    )

    assert index.events_for_trace("task-7")[0].source is UnifiedEventSource.AUDIT
    assert index.events_for_trace("mem-7")[0].source is UnifiedEventSource.MEMORY
    assert index.events_for_trace("task-9")[0].source is UnifiedEventSource.TASK


def test_unified_event_index_recent_returns_tail_in_order() -> None:
    t0 = datetime(2026, 5, 31, 9, 0, tzinfo=UTC)
    t1 = datetime(2026, 5, 31, 9, 1, tzinfo=UTC)
    t2 = datetime(2026, 5, 31, 9, 2, tzinfo=UTC)
    events = (
        _audit(event_id="a0", task_id="task-1", trace_id="task-1", when=t0),
        _audit(event_id="a1", task_id="task-2", trace_id="task-2", when=t1),
        _audit(event_id="a2", task_id="task-3", trace_id="task-3", when=t2),
    )

    index = InMemoryUnifiedEventIndex(audit_events=events)

    recent = index.recent(limit=2)
    assert [event.event_id for event in recent] == ["a1", "a2"]
    assert index.recent(limit=0) == ()
