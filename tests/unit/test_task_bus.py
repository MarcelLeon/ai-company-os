from collections.abc import AsyncIterator
from pathlib import Path

from aico.core import (
    AckStatus,
    AdapterRegistry,
    AdapterStatus,
    AuditEventType,
    Capability,
    HealthStatus,
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
)


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
    )

    await first_bus.submit(task)
    _ = [output async for output in first_bus.stream_output(task.task_id)]

    second_bus = TaskBus(RecordingAdapter(), task_store=store)

    assert second_bus.task_record("task-1") == task
    assert second_bus.task_snapshots()[0].task_id == "task-1"
    assert second_bus.task_snapshots()[0].status is TaskStatus.RUNNING


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
