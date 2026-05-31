import json
from pathlib import Path

from aico.core import (
    AuditEventType,
    InMemoryAuditLog,
    JsonlAuditSink,
    RiskLevel,
    Task,
    read_jsonl_audit_events,
)


def test_in_memory_audit_log_writes_jsonl_sink(tmp_path: Path) -> None:
    audit_path = tmp_path / "logs" / "audit.jsonl"
    audit_log = InMemoryAuditLog(
        event_id_factory=lambda: "event-1",
        sinks=(JsonlAuditSink(audit_path),),
    )
    task = Task(
        task_id="task-1",
        payload="run pytest",
        requester_id="user-1",
        target_persona="implementer",
    )

    event = audit_log.record(
        AuditEventType.TASK_SUBMITTED,
        task,
        adapter_name="claude-code",
        risk_level=RiskLevel.SHELL_EXEC,
        detail="approval required",
    )

    assert audit_log.events() == (event,)
    lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event_id"] == "event-1"
    assert payload["event_type"] == "task_submitted"
    assert payload["task_id"] == "task-1"
    assert payload["actor_id"] == "user-1"
    assert payload["adapter_name"] == "claude-code"
    assert payload["risk_level"] == "shell_exec"
    assert payload["detail"] == "approval required"


def test_read_jsonl_audit_events_loads_persisted_events(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    audit_log = InMemoryAuditLog(
        event_id_factory=lambda: "event-1",
        sinks=(JsonlAuditSink(audit_path),),
    )
    task = Task(
        task_id="task-1",
        payload="run pytest",
        requester_id="user-1",
        target_persona="implementer",
    )

    event = audit_log.record(AuditEventType.TASK_SUBMITTED, task)

    loaded = read_jsonl_audit_events(audit_path)
    assert loaded == (event,)

    restored = InMemoryAuditLog(initial_events=loaded)
    assert restored.events() == (event,)


def test_audit_record_propagates_task_trace_id() -> None:
    audit_log = InMemoryAuditLog(event_id_factory=lambda: "event-x")
    task = Task(
        task_id="task-7",
        payload="run pytest",
        requester_id="user-1",
        target_persona="implementer",
        trace_id="trace-42",
    )

    event = audit_log.record(AuditEventType.TASK_SUBMITTED, task)

    assert event.trace_id == "trace-42"


def test_audit_record_falls_back_trace_id_to_task_id() -> None:
    audit_log = InMemoryAuditLog(event_id_factory=lambda: "event-y")
    task = Task(
        task_id="task-9",
        payload="run pytest",
        requester_id="user-1",
        target_persona="implementer",
    )

    event = audit_log.record(AuditEventType.TASK_SUBMITTED, task)

    assert event.trace_id == "task-9"


def test_audit_record_event_falls_back_trace_id_to_task_id() -> None:
    audit_log = InMemoryAuditLog(event_id_factory=lambda: "event-z")
    event = audit_log.record_event(
        AuditEventType.MEMORY_BROADCASTED,
        task_id="memory:mem-42",
        actor_id="lead-agent",
        target_persona="team:aico/core",
    )

    assert event.trace_id == "memory:mem-42"
