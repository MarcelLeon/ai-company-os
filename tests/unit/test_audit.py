import json
import stat
from pathlib import Path
from typing import Any

import pytest

from aico.core import (
    AuditEvent,
    AuditEventType,
    InMemoryAuditLog,
    JsonlAuditSink,
    RiskLevel,
    Task,
    read_jsonl_audit_events,
)
from aico.core.audit_ledger import (
    AuditIntegrityError,
    seal_legacy_audit_ledger,
    verify_audit_ledger,
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
    assert payload["_audit"]["schema_version"] == 1
    assert len(payload["_audit"]["previous_sha256"]) == 64
    assert len(payload["_audit"]["entry_sha256"]) == 64
    checkpoint = audit_path.with_name("audit.jsonl.checkpoint.json")
    assert checkpoint.is_file()
    assert stat.S_IMODE(audit_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(checkpoint.stat().st_mode) == 0o600


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


def test_record_existing_is_idempotent_in_memory_and_jsonl(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    first_log = InMemoryAuditLog(
        event_id_factory=lambda: "event-stable",
        sinks=(JsonlAuditSink(audit_path),),
    )
    task = Task(
        task_id="task-recovery",
        payload="recover",
        requester_id="runtime",
        target_persona="operator",
    )
    event = first_log.record(AuditEventType.TASK_INTERRUPTED, task)
    retry_log = InMemoryAuditLog(sinks=(JsonlAuditSink(audit_path),))

    assert retry_log.record_existing(event) == event
    assert retry_log.record_existing(event) == event
    assert retry_log.events() == (event,)
    assert read_jsonl_audit_events(audit_path) == (event,)


def test_record_existing_rejects_event_id_collision() -> None:
    audit_log = InMemoryAuditLog()
    task = Task(
        task_id="task-recovery",
        payload="recover",
        requester_id="runtime",
        target_persona="operator",
    )
    event = audit_log.record(AuditEventType.TASK_INTERRUPTED, task)

    with pytest.raises(ValueError, match="audit event id collision"):
        audit_log.record_existing(event.model_copy(update={"detail": "different"}))


def test_jsonl_sink_rejects_existing_event_id_with_different_content(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    first_log = InMemoryAuditLog(
        event_id_factory=lambda: "event-stable",
        sinks=(JsonlAuditSink(audit_path),),
    )
    task = Task(
        task_id="task-recovery",
        payload="recover",
        requester_id="runtime",
        target_persona="operator",
    )
    event = first_log.record(AuditEventType.TASK_INTERRUPTED, task)
    retry_log = InMemoryAuditLog(sinks=(JsonlAuditSink(audit_path),))

    with pytest.raises(ValueError, match="audit event id collision"):
        retry_log.record_existing(event.model_copy(update={"detail": "different"}))


def test_audit_ledger_detects_event_mutation_and_tail_truncation(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    first = _event("event-1", "task-1")
    second = _event("event-2", "task-2")
    sink = JsonlAuditSink(audit_path)
    sink.write(first)
    sink.write(second)
    original = audit_path.read_bytes()

    audit_path.write_bytes(original.replace(b'"task_id": "task-1"', b'"task_id": "task-x"'))
    with pytest.raises(AuditIntegrityError, match="hash chain"):
        read_jsonl_audit_events(audit_path)

    audit_path.write_bytes(original.splitlines(keepends=True)[0])
    with pytest.raises(AuditIntegrityError, match="truncated"):
        read_jsonl_audit_events(audit_path)


def test_audit_ledger_detects_checkpoint_rewrite_or_removal(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    JsonlAuditSink(audit_path).write(_event("event-1", "task-1"))
    checkpoint = audit_path.with_name("audit.jsonl.checkpoint.json")
    original = checkpoint.read_bytes()
    payload = json.loads(original)
    payload["head_sha256"] = "f" * 64
    checkpoint.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(AuditIntegrityError, match="checkpoint does not match"):
        read_jsonl_audit_events(audit_path)

    checkpoint.write_bytes(original)
    checkpoint.unlink()
    with pytest.raises(AuditIntegrityError, match="unsealed"):
        read_jsonl_audit_events(audit_path)


def test_active_audit_sink_detects_same_size_rewrite_before_next_append(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    sink = JsonlAuditSink(audit_path)
    sink.write(_event("event-1", "task-1"))
    rewritten = audit_path.read_bytes().replace(b'"task_id": "task-1"', b'"task_id": "task-x"')
    audit_path.write_bytes(rewritten)

    with pytest.raises(AuditIntegrityError, match="hash chain"):
        sink.write(_event("event-2", "task-2"))


def test_audit_ledger_detects_reorder_insertion_and_torn_tail(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    sink = JsonlAuditSink(audit_path)
    sink.write(_event("event-1", "task-1"))
    sink.write(_event("event-2", "task-2"))
    lines = audit_path.read_bytes().splitlines(keepends=True)

    audit_path.write_bytes(lines[1] + lines[0])
    with pytest.raises(AuditIntegrityError, match="hash chain"):
        read_jsonl_audit_events(audit_path)

    audit_path.write_bytes(lines[0] + lines[0] + lines[1])
    with pytest.raises(AuditIntegrityError):
        read_jsonl_audit_events(audit_path)

    audit_path.write_bytes(lines[0] + lines[1][:-1])
    with pytest.raises(AuditIntegrityError, match="incomplete"):
        read_jsonl_audit_events(audit_path)


def test_audit_ledger_requires_explicit_legacy_seal_and_anchors_old_bytes(
    tmp_path: Path,
) -> None:
    audit_path = tmp_path / "audit.jsonl"
    legacy = _event("event-legacy", "task-legacy")
    audit_path.write_text(legacy.model_dump_json() + "\n", encoding="utf-8")
    audit_path.chmod(0o600)

    with pytest.raises(AuditIntegrityError, match="unsealed"):
        JsonlAuditSink(audit_path)

    audit_path.chmod(0o644)
    summary = seal_legacy_audit_ledger(audit_path)
    assert summary.sealed
    assert summary.event_count == 1
    assert stat.S_IMODE(audit_path.stat().st_mode) == 0o600
    assert read_jsonl_audit_events(audit_path) == (legacy,)

    JsonlAuditSink(audit_path).write(_event("event-new", "task-new"))
    assert len(read_jsonl_audit_events(audit_path)) == 2
    legacy_line, chained_line = audit_path.read_bytes().splitlines(keepends=True)
    audit_path.write_bytes(legacy_line.replace(b"task-legacy", b"task-changed") + chained_line)
    with pytest.raises(AuditIntegrityError):
        read_jsonl_audit_events(audit_path)


def test_audit_ledger_recovers_fsynced_event_when_checkpoint_write_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_path = tmp_path / "audit.jsonl"
    sink = JsonlAuditSink(audit_path)
    event = _event("event-crash", "task-crash")
    from aico.core import audit_ledger

    real_write = audit_ledger._write_checkpoint  # noqa: SLF001
    attempts = 0

    def fail_once(path: Path, checkpoint: Any) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("simulated checkpoint crash")
        real_write(path, checkpoint)

    monkeypatch.setattr(audit_ledger, "_write_checkpoint", fail_once)
    with pytest.raises(OSError, match="simulated checkpoint crash"):
        sink.write(event)

    restarted = JsonlAuditSink(audit_path)
    restarted.write(event)

    assert read_jsonl_audit_events(audit_path) == (event,)
    assert verify_audit_ledger(audit_path).checkpoint_lag is False


def test_two_audit_sinks_refresh_under_file_lock_without_losing_chain(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    first = JsonlAuditSink(audit_path)
    second = JsonlAuditSink(audit_path)

    first.write(_event("event-1", "task-1"))
    second.write(_event("event-2", "task-2"))

    assert [event.event_id for event in read_jsonl_audit_events(audit_path)] == [
        "event-1",
        "event-2",
    ]


def test_audit_ledger_refuses_symlink_target(tmp_path: Path) -> None:
    target = tmp_path / "target.jsonl"
    target.write_text("", encoding="utf-8")
    link = tmp_path / "audit.jsonl"
    link.symlink_to(target)

    with pytest.raises(AuditIntegrityError, match="symlink"):
        JsonlAuditSink(link)


def _event(event_id: str, task_id: str) -> AuditEvent:
    log = InMemoryAuditLog(event_id_factory=lambda: event_id)
    return log.record(
        AuditEventType.TASK_SUBMITTED,
        Task(
            task_id=task_id,
            payload="inspect",
            requester_id="owner",
            target_persona="reviewer",
        ),
    )
