from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aico.core import (
    AckStatus,
    AdapterRegistry,
    AdapterStatus,
    ApprovalStatus,
    AuditEvent,
    AuditEventType,
    Capability,
    HealthStatus,
    InMemoryAuditLog,
    JsonlAuditSink,
    MetadataEntry,
    OutputType,
    PersonaProfile,
    PersonaRegistry,
    RequesterOrListedApproverPolicy,
    RiskLevel,
    SQLiteTaskStateStore,
    Task,
    TaskAck,
    TaskBus,
    TaskOutput,
    TaskStatus,
    read_jsonl_audit_events,
)
from aico.core.authorization_clock import AUTHORIZATION_CLOCK_ROLLBACK_REASON
from aico.core.inbox import inbox_message
from aico.core.morning import morning_message
from aico.core.task_state import RUNTIME_RESTART_INTERRUPTED_REASON


class RecordingAdapter:
    def __init__(
        self,
        name: str = "recording",
        output_type: OutputType = OutputType.TEXT,
        capabilities: frozenset[Capability] | None = None,
    ) -> None:
        self._name = name
        self._output_type = output_type
        self._capabilities = capabilities or frozenset(
            {
                Capability.CODE_EDIT,
                Capability.SHELL_EXEC,
                Capability.STREAM_OUTPUT,
            }
        )
        self.received_tasks: list[Task] = []
        self.interrupted_task_ids: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    def capabilities(self) -> frozenset[Capability]:
        return self._capabilities

    async def receive_task(self, task: Task) -> TaskAck:
        self.received_tasks.append(task)
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    async def _outputs(self, task_id: str) -> AsyncIterator[TaskOutput]:
        yield TaskOutput(task_id=task_id, sequence=0, type=self._output_type, content="ok")

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        return self._outputs(task_id)

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        self.interrupted_task_ids.append(task_id)

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


class FailingAuditSink:
    def write(self, event: AuditEvent) -> None:
        del event
        raise RuntimeError("audit sink unavailable")


async def test_task_bus_delegates_submit_stream_and_interrupt() -> None:
    adapter = RecordingAdapter()
    bus = TaskBus(adapter)
    task = Task(
        task_id="task-1",
        payload="do work",
        requester_id="user-1",
        target_persona="default",
    )

    ack = await bus.submit(task)
    outputs = [output async for output in bus.stream_output(task.task_id)]
    await bus.interrupt(task.task_id)

    assert ack == TaskAck(task_id="task-1", status=AckStatus.ACCEPTED)
    assert adapter.received_tasks == [task]
    assert len(outputs) == 1
    assert outputs[0].model_dump(exclude={"timestamp"}) == TaskOutput(
        task_id="task-1",
        sequence=0,
        type=OutputType.TEXT,
        content="ok",
    ).model_dump(exclude={"timestamp"})
    assert adapter.interrupted_task_ids == ["task-1"]
    assert bus.task_snapshots()[0].status is TaskStatus.INTERRUPTED


async def test_task_bus_routes_tasks_to_adapter_registry_by_persona() -> None:
    claude = RecordingAdapter("claude-code")
    codex = RecordingAdapter("codex")
    bus = TaskBus(AdapterRegistry([claude, codex]))
    task = Task(
        task_id="task-1",
        payload="do work",
        requester_id="user-1",
        target_persona="codex",
    )

    ack = await bus.submit(task)
    outputs = [output async for output in bus.stream_output(task.task_id)]

    assert ack.status is AckStatus.ACCEPTED
    assert claude.received_tasks == []
    assert codex.received_tasks == [task]
    assert outputs[0].content == "ok"
    assert bus.task_snapshots()[0].adapter_name == "codex"
    assert bus.task_snapshots()[0].status is TaskStatus.RUNNING


async def test_task_bus_routes_persona_to_adapter_and_prefixes_payload() -> None:
    claude = RecordingAdapter("claude-code")
    codex = RecordingAdapter("codex")
    persona_registry = PersonaRegistry(
        [
            PersonaProfile(
                name="reviewer",
                adapter_name="codex",
                role_instruction="Role: reviewer.",
                aliases=("codex",),
            )
        ]
    )
    bus = TaskBus(AdapterRegistry([claude, codex]), persona_registry=persona_registry)
    task = Task(
        task_id="task-1",
        payload="inspect this",
        requester_id="user-1",
        target_persona="reviewer",
    )

    ack = await bus.submit(task)

    assert ack.status is AckStatus.ACCEPTED
    assert claude.received_tasks == []
    assert codex.received_tasks[0].target_persona == "reviewer"
    assert codex.received_tasks[0].payload == "Role: reviewer.\n\ninspect this"
    assert bus.broadcast_targets() == ("reviewer",)


async def test_task_bus_rejects_unknown_persona() -> None:
    bus = TaskBus(AdapterRegistry([RecordingAdapter("claude-code")]))
    task = Task(
        task_id="task-1",
        payload="do work",
        requester_id="user-1",
        target_persona="missing",
    )

    ack = await bus.submit(task)
    outputs = [output async for output in bus.stream_output(task.task_id)]

    assert ack == TaskAck(
        task_id="task-1",
        status=AckStatus.REJECTED,
        reason="unknown adapter or persona: missing",
    )
    assert outputs[0].type is OutputType.ERROR
    assert outputs[0].content == "unknown task id"
    assert bus.task_snapshots()[0].status is TaskStatus.REJECTED


async def test_task_bus_waits_for_approval_before_dispatching_risky_task() -> None:
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(AdapterRegistry([adapter]))
    task = Task(
        task_id="task-approval",
        payload="modify src/aico/core/task_bus.py",
        requester_id="user-1",
        target_persona="claude-code",
    )

    ack = await bus.submit(task)

    assert ack.status is AckStatus.WAITING_APPROVAL
    assert adapter.received_tasks == []
    assert bus.task_snapshots()[0].status is TaskStatus.WAITING_APPROVAL
    assert bus.task_snapshots()[0].risk_level is RiskLevel.WRITE_FILES
    assert [event.event_type for event in bus.audit_events()] == [
        AuditEventType.TASK_SUBMITTED,
        AuditEventType.APPROVAL_REQUESTED,
    ]


async def test_task_bus_rejects_risky_task_for_read_only_adapter() -> None:
    adapter = RecordingAdapter(
        "codex",
        capabilities=frozenset({Capability.CODE_REVIEW, Capability.STREAM_OUTPUT}),
    )
    bus = TaskBus(AdapterRegistry([adapter]))
    task = Task(
        task_id="task-codex-write",
        payload="create /tmp/readme.md",
        requester_id="user-1",
        target_persona="codex",
    )

    ack = await bus.submit(task)

    assert ack.status is AckStatus.REJECTED
    assert ack.reason == "adapter codex cannot handle write_files tasks; use /claude"
    assert adapter.received_tasks == []
    assert bus.task_snapshots()[0].status is TaskStatus.REJECTED
    assert bus.audit_events()[-1].event_type is AuditEventType.TASK_REJECTED


async def test_task_bus_keeps_collaboration_context_from_escalating_read_only_request() -> None:
    codex = RecordingAdapter(
        "codex",
        capabilities=frozenset({Capability.CODE_REVIEW, Capability.STREAM_OUTPUT}),
    )
    bus = TaskBus(AdapterRegistry([codex]))
    task = Task(
        task_id="task-codex-review",
        payload=(
            "Collaboration request from implementer:\n\n"
            "Context from implementer output so far:\n"
            "Plan:\n"
            "- run pytest\n"
            "- git push origin main\n\n"
            "Current task:\n"
            "review the release plan for risks and missing tests"
        ),
        requester_id="user-1",
        target_persona="codex",
    )

    ack = await bus.submit(task)

    assert ack.status is AckStatus.ACCEPTED
    assert codex.received_tasks == [task]
    assert bus.task_snapshots()[0].status is TaskStatus.RUNNING
    assert bus.task_snapshots()[0].risk_level is RiskLevel.READ_ONLY


async def test_task_bus_approval_dispatches_waiting_task() -> None:
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(AdapterRegistry([adapter]))
    task = Task(
        task_id="task-approval",
        payload="run pytest",
        requester_id="user-1",
        target_persona="claude-code",
    )

    await bus.submit(task)
    ack = await bus.approve(task.task_id, reviewer_id="user-1")

    assert ack.status is AckStatus.ACCEPTED
    assert adapter.received_tasks == [task]
    assert bus.task_snapshots()[0].status is TaskStatus.RUNNING
    assert [event.event_type for event in bus.audit_events()] == [
        AuditEventType.TASK_SUBMITTED,
        AuditEventType.APPROVAL_REQUESTED,
        AuditEventType.APPROVAL_APPROVED,
        AuditEventType.ADAPTER_DISPATCHED,
    ]


async def test_task_bus_expires_stale_approval_before_boss_handoff() -> None:
    now = [datetime(2026, 7, 22, 8, tzinfo=UTC)]
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(
        AdapterRegistry([adapter]),
        approval_max_age_seconds=300,
        clock=lambda: now[0],
    )
    task = Task(
        task_id="task-stale-approval",
        payload="modify src/aico/core/task_bus.py",
        requester_id="user-1",
        target_persona="claude-code",
        metadata=(MetadataEntry(key="aico.project_id", value="aico"),),
    )

    await bus.submit(task)
    pending = bus.pending_approvals()[0]
    assert pending.expires_at == now[0] + timedelta(seconds=300)
    now[0] += timedelta(seconds=300)
    snapshots = bus.task_snapshots(limit=None)
    ack = await bus.approve("task-sta", reviewer_id="user-1")
    message = inbox_message(project_id="aico", task_snapshots=snapshots).text

    assert adapter.received_tasks == []
    assert bus.pending_approvals() == ()
    assert snapshots[0].status is TaskStatus.REJECTED
    assert snapshots[0].reason == "approval lease expired; submit a new task for fresh review"
    assert ack.status is AckStatus.REJECTED
    assert ack.reason == "approval lease expired; submit a new task for fresh review"
    assert [event.event_type for event in bus.audit_events()] == [
        AuditEventType.TASK_SUBMITTED,
        AuditEventType.APPROVAL_REQUESTED,
        AuditEventType.APPROVAL_EXPIRED,
    ]
    assert "approve task-sta" not in message
    assert "recover task-sta" in message


async def test_task_bus_invalidates_pending_approval_after_clock_rollback() -> None:
    wall = [datetime(2026, 7, 22, 8, tzinfo=UTC)]
    steady = [100.0]
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(
        adapter,
        approval_max_age_seconds=300,
        clock=lambda: wall[0],
        monotonic_clock=lambda: steady[0],
    )
    task = Task(
        task_id="task-clock-rollback",
        payload="modify src/aico/core/task_bus.py",
        requester_id="user-1",
        target_persona="claude-code",
    )
    await bus.submit(task)

    wall[0] += timedelta(seconds=1)
    steady[0] += 301
    ack = await bus.approve(task.task_id, reviewer_id="user-1")

    assert ack.status is AckStatus.REJECTED
    assert ack.reason == AUTHORIZATION_CLOCK_ROLLBACK_REASON
    assert bus.pending_approvals() == ()
    assert bus.task_snapshots()[0].status is TaskStatus.REJECTED
    assert bus.task_snapshots()[0].reason == AUTHORIZATION_CLOCK_ROLLBACK_REASON
    assert adapter.received_tasks == []


async def test_task_bus_persists_clock_rollback_fence_and_rejects_new_risk(
    tmp_path: Path,
) -> None:
    wall = [datetime(2026, 7, 22, 8, tzinfo=UTC)]
    path = tmp_path / "state.db"
    store = SQLiteTaskStateStore(path)
    first = TaskBus(RecordingAdapter("claude-code"), task_store=store, clock=lambda: wall[0])
    first.authorization_time_refusal()

    wall[0] -= timedelta(minutes=1)
    adapter = RecordingAdapter("claude-code")
    restarted = TaskBus(adapter, task_store=store, clock=lambda: wall[0])
    task = Task(
        task_id="task-new-risk-after-rollback",
        payload="modify src/aico/core/task_bus.py",
        requester_id="user-1",
        target_persona="claude-code",
    )
    ack = await restarted.submit(task)

    assert ack.status is AckStatus.REJECTED
    assert ack.reason == AUTHORIZATION_CLOCK_ROLLBACK_REASON
    assert restarted.pending_approvals() == ()
    assert adapter.received_tasks == []


async def test_task_bus_restart_invalidates_persisted_pending_approval_on_rollback(
    tmp_path: Path,
) -> None:
    wall = [datetime(2026, 7, 22, 8, tzinfo=UTC)]
    path = tmp_path / "state.db"
    store = SQLiteTaskStateStore(path)
    first = TaskBus(RecordingAdapter("claude-code"), task_store=store, clock=lambda: wall[0])
    task = Task(
        task_id="task-persisted-clock-rollback",
        payload="modify src/aico/core/task_bus.py",
        requester_id="user-1",
        target_persona="claude-code",
    )
    await first.submit(task)

    wall[0] -= timedelta(minutes=1)
    restarted = TaskBus(
        RecordingAdapter("claude-code"),
        task_store=store,
        clock=lambda: wall[0],
    )
    restarted.recover_startup_state()

    approval = store.load_approvals()[0]
    snapshot = store.load_task_snapshots()[0]
    assert approval.status is ApprovalStatus.EXPIRED
    assert approval.reason == AUTHORIZATION_CLOCK_ROLLBACK_REASON
    assert snapshot.status is TaskStatus.REJECTED
    assert snapshot.reason == AUTHORIZATION_CLOCK_ROLLBACK_REASON
    assert [event.event_type for event in restarted.audit_events()] == [
        AuditEventType.APPROVAL_EXPIRED
    ]
    assert store.load_pending_recovery_audit_events() == ()


async def test_task_bus_approval_lease_survives_restart_and_audit_retry(tmp_path: Path) -> None:
    created_at = datetime(2026, 7, 22, 8, tzinfo=UTC)
    db_path = tmp_path / "state.db"
    store = SQLiteTaskStateStore(db_path)
    first_bus = TaskBus(
        RecordingAdapter("claude-code"),
        task_store=store,
        approval_max_age_seconds=300,
        clock=lambda: created_at,
    )
    task = Task(
        task_id="task-expiry-restart",
        payload="run pytest",
        requester_id="user-1",
        target_persona="claude-code",
    )
    await first_bus.submit(task)

    failed = TaskBus(
        RecordingAdapter("claude-code"),
        audit_log=InMemoryAuditLog(sinks=(FailingAuditSink(),)),
        task_store=store,
        approval_max_age_seconds=604_800,
        clock=lambda: created_at + timedelta(seconds=301),
    )
    with pytest.raises(RuntimeError, match="audit sink unavailable"):
        failed.recover_startup_state()

    assert store.load_approvals()[0].status is ApprovalStatus.EXPIRED
    assert store.load_task_snapshots()[0].status is TaskStatus.REJECTED
    assert len(store.load_pending_recovery_audit_events()) == 1

    audit_path = tmp_path / "audit.jsonl"
    recovered = TaskBus(
        RecordingAdapter("claude-code"),
        audit_log=InMemoryAuditLog(sinks=(JsonlAuditSink(audit_path),)),
        task_store=store,
        approval_max_age_seconds=604_800,
        clock=lambda: created_at + timedelta(seconds=302),
    )
    recovered.recover_startup_state()

    assert store.load_approvals()[0].status is ApprovalStatus.EXPIRED
    assert store.load_task_snapshots()[0].status is TaskStatus.REJECTED
    assert store.load_pending_recovery_audit_events() == ()
    assert [event.event_type for event in read_jsonl_audit_events(audit_path)] == [
        AuditEventType.APPROVAL_EXPIRED
    ]

    restarted = TaskBus(
        RecordingAdapter("claude-code"),
        audit_log=InMemoryAuditLog(sinks=(JsonlAuditSink(audit_path),)),
        task_store=store,
        approval_max_age_seconds=604_800,
        clock=lambda: created_at + timedelta(seconds=303),
    )
    restarted.recover_startup_state()
    assert len(read_jsonl_audit_events(audit_path)) == 1


async def test_task_bus_interrupt_cancels_waiting_approval_task() -> None:
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(AdapterRegistry([adapter]))
    task = Task(
        task_id="task-approval",
        payload="modify src/aico/core/task_bus.py",
        requester_id="user-1",
        target_persona="claude-code",
    )

    await bus.submit(task)
    ack = await bus.interrupt("task-app")

    assert ack.status is AckStatus.ACCEPTED
    assert ack.reason == "pending approval canceled"
    assert adapter.received_tasks == []
    assert bus.pending_approvals() == ()
    assert bus.task_snapshots()[0].status is TaskStatus.INTERRUPTED
    assert bus.task_snapshots()[0].reason == "interrupted before approval"
    assert [event.event_type for event in bus.audit_events()] == [
        AuditEventType.TASK_SUBMITTED,
        AuditEventType.APPROVAL_REQUESTED,
        AuditEventType.APPROVAL_REJECTED,
        AuditEventType.TASK_INTERRUPTED,
    ]


async def test_task_bus_denies_approval_from_unlisted_reviewer() -> None:
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(AdapterRegistry([adapter]))
    task = Task(
        task_id="task-approval",
        payload="run pytest",
        requester_id="user-1",
        target_persona="claude-code",
    )

    await bus.submit(task)
    ack = await bus.approve(task.task_id, reviewer_id="user-2")

    assert ack.status is AckStatus.REJECTED
    assert ack.reason == "approver not authorized"
    assert adapter.received_tasks == []
    assert bus.task_snapshots()[0].status is TaskStatus.WAITING_APPROVAL
    assert bus.audit_events()[-1].event_type is AuditEventType.APPROVAL_DENIED
    assert bus.audit_events()[-1].actor_id == "user-2"


async def test_task_bus_allows_configured_reviewer_to_approve_task() -> None:
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(
        AdapterRegistry([adapter]),
        approval_policy=RequesterOrListedApproverPolicy(("admin-1",)),
    )
    task = Task(
        task_id="task-approval",
        payload="run pytest",
        requester_id="user-1",
        target_persona="claude-code",
    )

    await bus.submit(task)
    ack = await bus.approve(task.task_id, reviewer_id="admin-1")

    assert ack.status is AckStatus.ACCEPTED
    assert adapter.received_tasks == [task]


async def test_task_bus_approval_without_id_dispatches_only_pending_task() -> None:
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(AdapterRegistry([adapter]))
    task = Task(
        task_id="task-approval",
        payload="run pytest",
        requester_id="user-1",
        target_persona="claude-code",
    )

    await bus.submit(task)
    ack = await bus.approve(None, reviewer_id="user-1")

    assert ack.status is AckStatus.ACCEPTED
    assert ack.task_id == "task-approval"
    assert adapter.received_tasks == [task]


async def test_task_bus_approval_accepts_short_task_id_prefix() -> None:
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(AdapterRegistry([adapter]))
    task = Task(
        task_id="abcdef12-3456",
        payload="run pytest",
        requester_id="user-1",
        target_persona="claude-code",
    )

    await bus.submit(task)
    ack = await bus.approve("abcdef12", reviewer_id="user-1")

    assert ack.status is AckStatus.ACCEPTED
    assert ack.task_id == "abcdef12-3456"
    assert adapter.received_tasks == [task]


async def test_task_bus_approval_without_id_lists_multiple_pending_approvals() -> None:
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(AdapterRegistry([adapter]))
    first = Task(
        task_id="abcdef12-3456",
        payload="run pytest",
        requester_id="user-1",
        target_persona="claude-code",
    )
    second = Task(
        task_id="12345678-abcd",
        payload="modify src/aico/core/task_bus.py",
        requester_id="user-1",
        target_persona="claude-code",
    )

    await bus.submit(first)
    await bus.submit(second)
    ack = await bus.approve(None, reviewer_id="user-1")

    assert ack.status is AckStatus.REJECTED
    assert ack.reason == "multiple pending approvals: abcdef12, 12345678"
    assert adapter.received_tasks == []


async def test_task_bus_rejects_waiting_approval_without_dispatching() -> None:
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(AdapterRegistry([adapter]))
    task = Task(
        task_id="task-approval",
        payload="delete src/aico/core/models.py",
        requester_id="user-1",
        target_persona="claude-code",
    )

    await bus.submit(task)
    ack = await bus.reject_approval(task.task_id, reviewer_id="user-1", reason="too broad")

    assert ack.status is AckStatus.REJECTED
    assert ack.reason == "too broad"
    assert adapter.received_tasks == []
    assert bus.task_snapshots()[0].status is TaskStatus.REJECTED
    assert bus.task_snapshots()[0].reason == "too broad"
    assert bus.audit_events()[-1].event_type is AuditEventType.TASK_REJECTED


async def test_task_bus_restores_pending_approval_from_sqlite_store(tmp_path: Path) -> None:
    store = SQLiteTaskStateStore(tmp_path / "aico-state.db")
    first_adapter = RecordingAdapter("claude-code")
    first_bus = TaskBus(AdapterRegistry([first_adapter]), task_store=store)
    task = Task(
        task_id="task-approval",
        payload="run pytest",
        requester_id="user-1",
        target_persona="claude-code",
    )

    await first_bus.submit(task)

    second_adapter = RecordingAdapter("claude-code")
    second_bus = TaskBus(AdapterRegistry([second_adapter]), task_store=store)

    assert second_bus.task_snapshots()[0].status is TaskStatus.WAITING_APPROVAL
    assert len(second_bus.pending_approvals()) == 1

    ack = await second_bus.approve(None, reviewer_id="user-1")

    assert ack.status is AckStatus.ACCEPTED
    assert second_adapter.received_tasks == [task]
    assert second_bus.task_snapshots()[0].status is TaskStatus.RUNNING


async def test_task_bus_restores_task_snapshots_from_sqlite_store(tmp_path: Path) -> None:
    store = SQLiteTaskStateStore(tmp_path / "aico-state.db")
    first_bus = TaskBus(RecordingAdapter(), task_store=store)
    task = Task(
        task_id="task-1",
        payload="do work",
        requester_id="user-1",
        target_persona="default",
        trace_id="trace-crash",
        metadata=(MetadataEntry(key="aico.project_id", value="aico"),),
    )

    await first_bus.submit(task)
    _ = [output async for output in first_bus.stream_output(task.task_id)]
    before_restart = first_bus.task_snapshots()[0]

    second_bus = TaskBus(RecordingAdapter(), task_store=store)
    assert store.load_task_snapshots()[0].status is TaskStatus.RUNNING
    second_bus.recover_startup_state()
    after_restart = second_bus.task_snapshots()[0]

    assert second_bus.task_record("task-1") == task
    assert after_restart.task_id == "task-1"
    assert after_restart.status is TaskStatus.INTERRUPTED
    assert after_restart.reason == RUNTIME_RESTART_INTERRUPTED_REASON
    assert after_restart.adapter_name == before_restart.adapter_name
    assert after_restart.risk_level == before_restart.risk_level
    assert after_restart.metadata == before_restart.metadata
    assert after_restart.created_at == before_restart.created_at
    assert [event.event_type for event in second_bus.audit_events()] == [
        AuditEventType.TASK_INTERRUPTED
    ]
    assert second_bus.audit_events()[0].detail == RUNTIME_RESTART_INTERRUPTED_REASON
    assert second_bus.audit_events()[0].trace_id == task.trace_id

    inbox = inbox_message(
        project_id="aico",
        task_snapshots=second_bus.task_snapshots(limit=None),
    ).text
    morning = morning_message(
        project_id="aico",
        task_snapshots=second_bus.task_snapshots(limit=None),
    ).text

    assert "Running:" not in inbox
    assert "recover task-1 [default] interrupted" in inbox
    assert "Blocked:" in morning
    assert "task-1 interrupted" in morning

    third_bus = TaskBus(RecordingAdapter(), task_store=store)

    assert third_bus.task_snapshots()[0].status is TaskStatus.INTERRUPTED
    assert third_bus.audit_events() == ()


async def test_task_bus_restart_preserves_terminal_task_state(tmp_path: Path) -> None:
    store = SQLiteTaskStateStore(tmp_path / "aico-state.db")
    first_bus = TaskBus(RecordingAdapter(output_type=OutputType.DONE), task_store=store)
    task = Task(
        task_id="task-done",
        payload="do work",
        requester_id="user-1",
        target_persona="default",
    )

    await first_bus.submit(task)
    _ = [output async for output in first_bus.stream_output(task.task_id)]
    before_restart = first_bus.task_snapshots()[0]

    second_bus = TaskBus(RecordingAdapter(), task_store=store)
    second_bus.recover_startup_state()

    assert second_bus.task_snapshots()[0] == before_restart
    assert second_bus.audit_events() == ()


async def test_task_bus_restart_persists_one_reconciliation_audit(tmp_path: Path) -> None:
    store = SQLiteTaskStateStore(tmp_path / "aico-state.db")
    first_bus = TaskBus(RecordingAdapter(), task_store=store)
    task = Task(
        task_id="task-orphan",
        payload="do work",
        requester_id="user-1",
        target_persona="default",
    )

    await first_bus.submit(task)
    _ = [output async for output in first_bus.stream_output(task.task_id)]

    audit_path = tmp_path / "audit.jsonl"
    audit_log = InMemoryAuditLog(sinks=(JsonlAuditSink(audit_path),))
    second_bus = TaskBus(RecordingAdapter(), audit_log=audit_log, task_store=store)
    second_bus.recover_startup_state()
    third_bus = TaskBus(RecordingAdapter(), audit_log=audit_log, task_store=store)
    third_bus.recover_startup_state()

    events = read_jsonl_audit_events(audit_path)
    assert [event.event_type for event in events] == [AuditEventType.TASK_INTERRUPTED]
    assert events[0].task_id == task.task_id
    assert events[0].detail == RUNTIME_RESTART_INTERRUPTED_REASON


async def test_task_bus_retries_pending_recovery_audit_after_sink_failure(
    tmp_path: Path,
) -> None:
    store = SQLiteTaskStateStore(tmp_path / "aico-state.db")
    first_bus = TaskBus(RecordingAdapter(), task_store=store)
    task = Task(
        task_id="task-sink-failure",
        payload="do work",
        requester_id="user-1",
        target_persona="default",
    )
    await first_bus.submit(task)
    _ = [output async for output in first_bus.stream_output(task.task_id)]

    with pytest.raises(RuntimeError, match="audit sink unavailable"):
        failed_bus = TaskBus(
            RecordingAdapter(),
            audit_log=InMemoryAuditLog(sinks=(FailingAuditSink(),)),
            task_store=store,
        )
        failed_bus.recover_startup_state()

    assert store.load_task_snapshots()[0].status is TaskStatus.INTERRUPTED
    pending = store.load_pending_recovery_audit_events()
    assert len(pending) == 1

    audit_path = tmp_path / "audit.jsonl"
    recovered_bus = TaskBus(
        RecordingAdapter(),
        audit_log=InMemoryAuditLog(sinks=(JsonlAuditSink(audit_path),)),
        task_store=store,
    )
    recovered_bus.recover_startup_state()

    assert store.load_pending_recovery_audit_events() == ()
    assert read_jsonl_audit_events(audit_path) == pending


async def test_task_bus_deduplicates_audit_written_before_outbox_ack(tmp_path: Path) -> None:
    store = SQLiteTaskStateStore(tmp_path / "aico-state.db")
    first_bus = TaskBus(RecordingAdapter(), task_store=store)
    task = Task(
        task_id="task-before-ack",
        payload="do work",
        requester_id="user-1",
        target_persona="default",
    )
    await first_bus.submit(task)
    _ = [output async for output in first_bus.stream_output(task.task_id)]

    store.reconcile_running_tasks(reason=RUNTIME_RESTART_INTERRUPTED_REASON)
    pending = store.load_pending_recovery_audit_events()
    audit_path = tmp_path / "audit.jsonl"
    JsonlAuditSink(audit_path).write(pending[0])

    recovered_bus = TaskBus(
        RecordingAdapter(),
        audit_log=InMemoryAuditLog(sinks=(JsonlAuditSink(audit_path),)),
        task_store=store,
    )
    recovered_bus.recover_startup_state()

    assert store.load_pending_recovery_audit_events() == ()
    assert read_jsonl_audit_events(audit_path) == pending


async def test_task_bus_denies_rejection_from_unlisted_reviewer() -> None:
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(AdapterRegistry([adapter]))
    task = Task(
        task_id="task-approval",
        payload="delete src/aico/core/models.py",
        requester_id="user-1",
        target_persona="claude-code",
    )

    await bus.submit(task)
    ack = await bus.reject_approval(task.task_id, reviewer_id="user-2")

    assert ack.status is AckStatus.REJECTED
    assert ack.reason == "approver not authorized"
    assert bus.task_snapshots()[0].status is TaskStatus.WAITING_APPROVAL
    assert bus.audit_events()[-1].event_type is AuditEventType.APPROVAL_DENIED


async def test_task_bus_rejects_only_pending_approval_without_id() -> None:
    adapter = RecordingAdapter("claude-code")
    bus = TaskBus(AdapterRegistry([adapter]))
    task = Task(
        task_id="task-approval",
        payload="delete src/aico/core/models.py",
        requester_id="user-1",
        target_persona="claude-code",
    )

    await bus.submit(task)
    ack = await bus.reject_approval(None, reviewer_id="user-1")

    assert ack.status is AckStatus.REJECTED
    assert ack.task_id == "task-approval"
    assert adapter.received_tasks == []
    assert bus.task_snapshots()[0].status is TaskStatus.REJECTED


async def test_task_bus_marks_task_done_after_done_output() -> None:
    adapter = RecordingAdapter(output_type=OutputType.DONE)
    bus = TaskBus(adapter)
    task = Task(
        task_id="task-1",
        payload="do work",
        requester_id="user-1",
        target_persona="default",
    )

    await bus.submit(task)
    outputs = [output async for output in bus.stream_output(task.task_id)]

    assert outputs[0].type is OutputType.DONE
    assert bus.task_snapshots()[0].status is TaskStatus.DONE
    assert bus.audit_events()[-1].event_type is AuditEventType.TASK_COMPLETED


async def test_task_bus_marks_task_failed_after_error_output() -> None:
    adapter = RecordingAdapter(output_type=OutputType.ERROR)
    bus = TaskBus(adapter)
    task = Task(
        task_id="task-1",
        payload="do work",
        requester_id="user-1",
        target_persona="default",
    )

    await bus.submit(task)
    outputs = [output async for output in bus.stream_output(task.task_id)]

    assert outputs[0].type is OutputType.ERROR
    assert bus.task_snapshots()[0].status is TaskStatus.FAILED
    assert bus.task_snapshots()[0].reason == "ok"
    assert bus.audit_events()[-1].event_type is AuditEventType.TASK_FAILED


async def test_task_bus_marks_task_interrupted() -> None:
    adapter = RecordingAdapter()
    bus = TaskBus(adapter)
    task = Task(
        task_id="task-1",
        payload="do work",
        requester_id="user-1",
        target_persona="default",
    )

    await bus.submit(task)
    await bus.interrupt(task.task_id)

    assert adapter.interrupted_task_ids == ["task-1"]
    assert bus.task_snapshots()[0].status is TaskStatus.INTERRUPTED


async def test_task_bus_propagates_trace_id_to_audit_event() -> None:
    adapter = RecordingAdapter()
    bus = TaskBus(adapter)
    task = Task(
        task_id="task-trace",
        payload="do work",
        requester_id="user-1",
        target_persona="default",
        trace_id="trace-orchestration-7",
    )

    await bus.submit(task)

    events = bus.audit_events()
    assert events
    assert all(event.trace_id == "trace-orchestration-7" for event in events)


async def test_task_bus_falls_back_trace_id_to_task_id() -> None:
    adapter = RecordingAdapter()
    bus = TaskBus(adapter)
    task = Task(
        task_id="task-no-trace",
        payload="do work",
        requester_id="user-1",
        target_persona="default",
    )

    await bus.submit(task)

    events = bus.audit_events()
    assert events
    assert all(event.trace_id == "task-no-trace" for event in events)
