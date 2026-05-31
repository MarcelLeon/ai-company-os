import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from aico.channel import IMChannel, IncomingMessageHandler
from aico.core import (
    STREAM_MESSAGE_TEXT_LIMIT,
    AckStatus,
    AdapterRegistry,
    AdapterStatus,
    AgentCard,
    AgentDirectory,
    AgentSessionStatus,
    AssignmentProfile,
    AuditEventType,
    Capability,
    ChannelTarget,
    CompanyAgentProfile,
    HealthStatus,
    IncomingMessage,
    InMemoryAgentSessionStore,
    JsonlMemoryStore,
    MemoryAtom,
    MemoryBroadcastService,
    MemoryEvidence,
    MemoryPurpose,
    MemoryScope,
    MemoryStatus,
    MessageContent,
    MessageNativeFormat,
    MessageRouter,
    MetadataEntry,
    Orchestrator,
    OutputType,
    PersonaProfile,
    PersonaRegistry,
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
    ProjectProfile,
    ProjectRoleProfile,
    ProviderSessionMode,
    ProviderSessionRef,
    RoleProfile,
    SentMessage,
    SQLiteOfflineDelegationStore,
    Task,
    TaskAck,
    TaskBus,
    TaskOutput,
    TaskStatus,
    provider_session_from_task,
)


class ScriptedAdapter:
    def __init__(
        self,
        ack_status: AckStatus = AckStatus.ACCEPTED,
        name: str = "scripted",
        output_texts: tuple[str, ...] = ("hello", " world"),
    ) -> None:
        self.ack_status = ack_status
        self._name = name
        self._output_texts = output_texts
        self.received_tasks: list[Task] = []
        self.interrupted_task_ids: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    def capabilities(self) -> frozenset[Capability]:
        return frozenset(
            {
                Capability.CODE_EDIT,
                Capability.SHELL_EXEC,
                Capability.STREAM_OUTPUT,
            }
        )

    async def receive_task(self, task: Task) -> TaskAck:
        self.received_tasks.append(task)
        return TaskAck(task_id=task.task_id, status=self.ack_status, reason="adapter unavailable")

    async def _outputs(self, task_id: str) -> AsyncIterator[TaskOutput]:
        for sequence, text in enumerate(self._output_texts):
            yield TaskOutput(task_id=task_id, sequence=sequence, type=OutputType.TEXT, content=text)
        yield TaskOutput(
            task_id=task_id,
            sequence=len(self._output_texts),
            type=OutputType.DONE,
            content="",
        )

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        return self._outputs(task_id)

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        self.interrupted_task_ids.append(task_id)

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


class RecordingChannel:
    def __init__(self) -> None:
        self.handler: IncomingMessageHandler | None = None
        self.sent_messages: list[MessageContent] = []
        self.edited_messages: list[MessageContent] = []

    @property
    def name(self) -> str:
        return "telegram"

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> SentMessage:
        _ = target
        self.sent_messages.append(content)
        return SentMessage(
            message_id=f"message-{len(self.sent_messages)}",
            target=target,
        )

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> None:
        _ = (target, message_id)
        self.edited_messages.append(content)

    async def delete_message(self, target: ChannelTarget, message_id: str) -> None:
        _ = (target, message_id)

    def on_incoming(self, handler: IncomingMessageHandler) -> None:
        self.handler = handler

    async def emit(self, message: IncomingMessage) -> None:
        if self.handler is None:
            raise AssertionError("channel handler is not registered")
        await self.handler(message)

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


async def test_orchestrator_runs_fake_channel_to_fake_adapter_flow() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-1"),
        task_bus=TaskBus(adapter),
    )

    orchestrator.bind()
    await channel.emit(_incoming_message())

    assert isinstance(channel, IMChannel)
    assert adapter.received_tasks[0].payload == "please inspect"
    assert adapter.received_tasks[0].target_persona == "lao-zhang"
    assert channel.sent_messages == [MessageContent(text="Task accepted: task-1")]
    assert channel.edited_messages == [
        MessageContent(text="hello"),
        MessageContent(text="hello world"),
    ]


async def test_orchestrator_reports_rejected_task_without_streaming() -> None:
    adapter = ScriptedAdapter(ack_status=AckStatus.BUSY)
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-2"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message())

    assert channel.sent_messages == [MessageContent(text="Task busy: adapter unavailable")]
    assert channel.edited_messages == []


async def test_orchestrator_reports_adapter_status_without_submitting_task() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-3"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/status"))

    assert adapter.received_tasks == []
    assert channel.sent_messages == [MessageContent(text="scripted: idle 0/1 running")]
    assert channel.edited_messages == []


async def test_orchestrator_status_includes_recent_tasks() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-4"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message())
    await orchestrator.handle_incoming(_incoming_message(text="/status"))

    assert channel.sent_messages[-1].text == (
        "scripted: idle 0/1 running\n\nRecent tasks:\ntask-4 [scripted]: done"
    )


async def test_orchestrator_reports_local_metrics_without_submitting_task() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    task_ids = iter(("task-done", "task-approval"))
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="scripted", task_id_factory=lambda: next(task_ids)),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="ship this", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="modify src/aico/core/task_bus.py", mentions=())
    )
    parent_task = bus.task_record("task-done")
    child_task = Task(
        task_id="task-child",
        payload="review it",
        requester_id="user-1",
        target_persona="codex",
    )
    assert parent_task is not None
    bus.record_collaboration_requested(parent_task, child_task)
    await orchestrator.handle_incoming(_incoming_message(text="/metrics"))

    metrics = channel.sent_messages[-1].text
    assert metrics.startswith("Metrics (local state + audit replay)\n\nglance\n")
    assert "status: needs_approval" in metrics
    assert "open: 1 (running=0, waiting_approval=1)" in metrics
    assert "\n\n24h\n" in metrics
    assert "tasks: 2\n" in metrics
    assert "done=1" in metrics
    assert "waiting_approval=1" in metrics
    assert "agents: scripted=2" in metrics
    assert "collaboration: 1" in metrics
    assert "open work:\n• task-approval [scripted]: waiting_approval" in metrics
    assert "token/cost: unavailable from current CLI adapters" in metrics
    assert len(adapter.received_tasks) == 1


async def test_orchestrator_lists_recent_tasks_without_submitting_task() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-4"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message())
    await orchestrator.handle_incoming(_incoming_message(text="/tasks"))

    assert adapter.received_tasks[0].task_id == "task-4"
    assert len(adapter.received_tasks) == 1
    assert channel.sent_messages[-1].text == (
        "Recent tasks:\ntask-4 [scripted]: done\n\nUse /task <task_id> for details."
    )


async def test_orchestrator_reports_task_detail_and_available_actions() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-approval"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message(text="modify src/aico/core/task_bus.py"))
    await orchestrator.handle_incoming(_incoming_message(text="/task task-app"))

    detail = channel.sent_messages[-1].text
    assert detail.startswith("Task: task-app\n")
    assert "id: task-approval\n" in detail
    assert "target: lao-zhang\n" in detail
    assert "status: waiting_approval\n" in detail
    assert "risk: write_files\n" in detail
    assert "Actions:\n• /approve task-app\n• /reject task-app" in detail
    assert adapter.received_tasks == []


async def test_orchestrator_reports_task_usage_and_unknown_task() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-3"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/task"))
    await orchestrator.handle_incoming(_incoming_message(text="/task missing"))

    assert channel.sent_messages[0] == MessageContent(text="Usage: /task <task_id>")
    assert channel.sent_messages[1] == MessageContent(text="Task rejected: unknown task: missing")
    assert adapter.received_tasks == []


async def test_orchestrator_requests_approval_for_risky_task() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-approval"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message(text="modify src/aico/core/task_bus.py"))

    assert adapter.received_tasks == []
    assert channel.sent_messages[0].text.startswith("Approval required: task-app")
    assert "Send /approve to continue" in channel.sent_messages[0].text
    assert channel.edited_messages == []


async def test_orchestrator_approves_only_waiting_task_without_id_and_streams_output() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-approval"),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="run pytest"))
    await orchestrator.handle_incoming(_incoming_message(text="/approve"))

    assert adapter.received_tasks[0].payload == "run pytest"
    assert channel.sent_messages[1] == MessageContent(text="Task approved: task-app")
    assert channel.edited_messages[-1] == MessageContent(text="hello world")
    assert bus.task_snapshots()[0].status is TaskStatus.DONE


async def test_orchestrator_denies_approval_from_different_sender() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-approval"),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="run pytest", sender_id="user-1"))
    await orchestrator.handle_incoming(_incoming_message(text="/approve", sender_id="user-2"))

    assert adapter.received_tasks == []
    assert channel.sent_messages[1] == MessageContent(text="Task rejected: approver not authorized")
    assert bus.task_snapshots()[0].status is TaskStatus.WAITING_APPROVAL


async def test_orchestrator_approves_waiting_task_by_short_id() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(
            default_persona="default",
            task_id_factory=lambda: "abcdef12-3456",
        ),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="run pytest"))
    await orchestrator.handle_incoming(_incoming_message(text="/approve abcdef12"))

    assert adapter.received_tasks[0].payload == "run pytest"
    assert channel.sent_messages[1] == MessageContent(text="Task approved: abcdef12")


async def test_orchestrator_lists_short_ids_when_approval_without_id_is_ambiguous() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    task_ids = iter(("abcdef12-3456", "12345678-abcd"))
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: next(task_ids)),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="run pytest"))
    await orchestrator.handle_incoming(_incoming_message(text="modify docs/human/daily-ops.md"))
    await orchestrator.handle_incoming(_incoming_message(text="/approve"))

    assert channel.sent_messages[-1] == MessageContent(
        text="Task rejected: multiple pending approvals: abcdef12, 12345678"
    )
    assert adapter.received_tasks == []


async def test_orchestrator_rejects_only_waiting_task_without_id() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-approval"),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="delete generated output"))
    await orchestrator.handle_incoming(_incoming_message(text="/reject"))

    assert adapter.received_tasks == []
    assert channel.sent_messages[-1] == MessageContent(text="Task rejected: approval rejected")
    assert channel.edited_messages == []
    assert bus.task_snapshots()[0].status is TaskStatus.REJECTED


async def test_orchestrator_interrupts_running_task_by_short_id() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default"),
        task_bus=bus,
    )
    task = Task(
        task_id="abcdef12-3456",
        payload="review slowly",
        requester_id="user-1",
        target_persona="default",
    )
    await bus.submit(task)

    await orchestrator.handle_incoming(_incoming_message(text="/interrupt abcdef12"))

    assert adapter.interrupted_task_ids == ["abcdef12-3456"]
    assert channel.sent_messages[-1] == MessageContent(text="Task interrupted: abcdef12")
    assert bus.task_snapshots()[0].status is TaskStatus.INTERRUPTED


async def test_orchestrator_reports_interrupt_usage() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/interrupt"))

    assert channel.sent_messages == [MessageContent(text="Usage: /interrupt <task_id>")]


async def test_orchestrator_status_includes_waiting_approval_risk() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-approval"),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="delete generated output"))
    await orchestrator.handle_incoming(_incoming_message(text="/status"))

    assert "waiting_approval (destructive)" in channel.sent_messages[-1].text


async def test_orchestrator_reports_empty_audit_log_without_submitting_task() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-audit"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/audit"))

    assert adapter.received_tasks == []
    assert channel.sent_messages == [MessageContent(text="No audit events")]
    assert channel.edited_messages == []


async def test_orchestrator_reports_recent_audit_events() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-audit"),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="run pytest"))
    await orchestrator.handle_incoming(_incoming_message(text="/audit"))

    audit_text = channel.sent_messages[-1].text
    assert audit_text.startswith("Recent audit events:")
    assert "• task_submitted\n" in audit_text
    assert "  task: task-audit\n" in audit_text
    assert "  actor: user-1\n" in audit_text
    assert "  target: lao-zhang\n" in audit_text
    assert "• approval_requested\n" in audit_text
    assert "  risk: shell_exec" in audit_text
    assert adapter.received_tasks == []


async def test_orchestrator_reports_help_without_submitting_task() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-5"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/help"))

    assert adapter.received_tasks == []
    assert channel.sent_messages[0].text.startswith("Commands:")
    assert "/audit" in channel.sent_messages[0].text
    assert "/sessions" in channel.sent_messages[0].text
    assert "/approve [task_id]" in channel.sent_messages[0].text
    assert "/codex <task>" in channel.sent_messages[0].text
    assert channel.edited_messages == []


async def test_orchestrator_language_command_scopes_future_agent_replies() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    task_ids = iter(("task-language-1", "task-language-2", "task-language-3"))
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: next(task_ids)),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/language"))
    await orchestrator.handle_incoming(_incoming_message(text="/language zh"))
    await orchestrator.handle_incoming(_incoming_message(text="please inspect"))
    await orchestrator.handle_incoming(_incoming_message(text="/language en"))
    await orchestrator.handle_incoming(_incoming_message(text="please inspect again"))

    assert channel.sent_messages[0].text.startswith("Agent response language\n")
    assert "current: English" in channel.sent_messages[0].text
    assert channel.sent_messages[1].text.startswith("Agent response language updated\n")
    assert "current: Simplified Chinese" in channel.sent_messages[1].text
    assert "Response language:\n- Reply to the boss in Simplified Chinese." in (
        adapter.received_tasks[0].payload
    )
    assert "Current task:" not in adapter.received_tasks[0].payload
    assert adapter.received_tasks[0].metadata[-1].key == "aico.response_language"
    assert "Response language:" not in adapter.received_tasks[1].payload


async def test_orchestrator_language_command_injects_project_role_tasks() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-language"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/language zh", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/ask implementer summarize status", mentions=())
    )

    payload = adapter.received_tasks[0].payload
    assert payload.startswith("Response language:\n")
    assert "Reply to the boss in Simplified Chinese." in payload
    assert "Current task:\nsummarize status" in payload


async def test_orchestrator_can_pilot_native_telegram_agent_output() -> None:
    adapter = ScriptedAdapter(output_texts=("<b>Status</b>\n<pre>Inbox | OK</pre>",))
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-native"),
        task_bus=TaskBus(adapter),
        prefer_native_channel_format=True,
    )

    await orchestrator.handle_incoming(_incoming_message(text="summarize status"))

    task = adapter.received_tasks[0]
    assert task.payload.startswith("Output format for Telegram:\n")
    assert task.payload.endswith("\n\nsummarize status")
    assert task.metadata[-1].key == "aico.native_output_format"
    assert task.metadata[-1].value == MessageNativeFormat.TELEGRAM_HTML.value
    assert channel.edited_messages[-1] == MessageContent(
        text="<b>Status</b>\n<pre>Inbox | OK</pre>",
        native_format=MessageNativeFormat.TELEGRAM_HTML,
    )


async def test_orchestrator_broadcasts_to_persona_targets() -> None:
    implementer = ScriptedAdapter(name="claude-code")
    reviewer = ScriptedAdapter(name="codex")
    persona_registry = PersonaRegistry(
        [
            PersonaProfile(
                name="implementer",
                adapter_name="claude-code",
                role_instruction="Role: implementer.",
            ),
            PersonaProfile(
                name="reviewer",
                adapter_name="codex",
                role_instruction="Role: reviewer.",
            ),
        ]
    )
    channel = RecordingChannel()
    task_ids = iter(("task-6", "task-7"))
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: next(task_ids)),
        task_bus=TaskBus(
            AdapterRegistry([implementer, reviewer]),
            persona_registry=persona_registry,
        ),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/broadcast inspect this"))

    assert implementer.received_tasks[0].target_persona == "implementer"
    assert implementer.received_tasks[0].payload == "Role: implementer.\n\ninspect this"
    assert reviewer.received_tasks[0].target_persona == "reviewer"
    assert reviewer.received_tasks[0].payload == "Role: reviewer.\n\ninspect this"
    assert channel.sent_messages[0] == MessageContent(text="Broadcast accepted: 2 targets")
    assert MessageContent(text="Task accepted: task-6 [implementer]") in channel.sent_messages
    assert MessageContent(text="Task accepted: task-7 [reviewer]") in channel.sent_messages


async def test_orchestrator_routes_adapter_collaboration_directive_to_target_persona() -> None:
    implementer = ScriptedAdapter(
        name="claude-code",
        output_texts=("@reviewer: inspect this implementation\n",),
    )
    reviewer = ScriptedAdapter(name="codex", output_texts=("looks good",))
    persona_registry = PersonaRegistry(
        [
            PersonaProfile(
                name="implementer",
                adapter_name="claude-code",
                role_instruction="Role: implementer.",
            ),
            PersonaProfile(
                name="reviewer",
                adapter_name="codex",
                role_instruction="Role: reviewer.",
            ),
        ]
    )
    channel = RecordingChannel()
    task_ids = iter(("task-parent", "task-child"))
    bus = TaskBus(
        AdapterRegistry([implementer, reviewer]),
        persona_registry=persona_registry,
    )
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(
            default_persona="implementer",
            task_id_factory=lambda: next(task_ids),
        ),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/implementer implement feature"))

    assert implementer.received_tasks[0].target_persona == "implementer"
    assert reviewer.received_tasks[0].target_persona == "reviewer"
    assert reviewer.received_tasks[0].payload == (
        "Role: reviewer.\n\nCollaboration request from implementer:\n\ninspect this implementation"
    )
    assert any(
        message.text == "Collaboration requested\nsource: implementer\ntarget: reviewer"
        and message.spans
        for message in channel.sent_messages
    )
    assert MessageContent(text="Task accepted: task-child [reviewer]") in channel.sent_messages
    assert MessageContent(text="looks good") in channel.edited_messages
    collaboration_events = [
        event
        for event in bus.audit_events(limit=None)
        if event.event_type is AuditEventType.COLLABORATION_REQUESTED
    ]
    assert len(collaboration_events) == 1
    assert collaboration_events[0].task_id == "task-child"
    assert collaboration_events[0].actor_id == "implementer"
    assert collaboration_events[0].target_persona == "reviewer"
    assert collaboration_events[0].detail == "parent_task=task-parent"

    await orchestrator.handle_incoming(_incoming_message(text="/task task-child"))
    child_detail = channel.sent_messages[-1].text
    assert "Collaboration:\n• requested by: implementer\n" in child_detail
    assert "• parent: task-par (/task task-par)" in child_detail

    await orchestrator.handle_incoming(_incoming_message(text="/task task-parent"))
    parent_detail = channel.sent_messages[-1].text
    assert "Collaboration:\n• children:\n  • task-chi -> reviewer (/task task-chi)" in parent_detail


async def test_orchestrator_routes_later_collaboration_directive_and_keeps_text() -> None:
    implementer = ScriptedAdapter(
        name="claude-code",
        output_texts=("Plan:\n- implement inbox list\n@reviewer: inspect this implementation\n",),
    )
    reviewer = ScriptedAdapter(name="codex", output_texts=("looks good",))
    persona_registry = PersonaRegistry(
        [
            PersonaProfile(
                name="implementer",
                adapter_name="claude-code",
                role_instruction="Role: implementer.",
            ),
            PersonaProfile(
                name="reviewer",
                adapter_name="codex",
                role_instruction="Role: reviewer.",
            ),
        ]
    )
    channel = RecordingChannel()
    task_ids = iter(("task-parent", "task-child"))
    bus = TaskBus(
        AdapterRegistry([implementer, reviewer]),
        persona_registry=persona_registry,
    )
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(
            default_persona="implementer",
            task_id_factory=lambda: next(task_ids),
        ),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/implementer implement feature"))

    assert reviewer.received_tasks[0].payload == (
        "Role: reviewer.\n\n"
        "Collaboration request from implementer:\n\n"
        "Context from implementer output so far:\n"
        "Plan:\n- implement inbox list\n\n"
        "Request:\n"
        "inspect this implementation"
    )
    assert any(
        message.text == "Plan:\n• implement inbox list" for message in channel.edited_messages
    )
    assert any(
        message.text == "Collaboration requested\nsource: implementer\ntarget: reviewer"
        and message.spans
        for message in channel.sent_messages
    )


async def test_orchestrator_collaboration_uses_assignment_role_and_parent_context() -> None:
    adapter = ScriptedAdapter(
        name="claude-code",
        output_texts=(
            "Findings:\n"
            "(a) keep /inbox read-only.\n"
            "(b) do not normalize batched approvals.\n"
            "@implementer: reflect (a)-(b) in the inbox plan\n",
        ),
    )
    channel = RecordingChannel()
    task_ids = iter(("task-parent", "task-child"))
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(
            default_persona="implementer",
            task_id_factory=lambda: next(task_ids),
        ),
        task_bus=bus,
    )
    task = Task(
        task_id="task-parent",
        payload="review plan",
        requester_id="user-1",
        target_persona="implementer",
        metadata=(MetadataEntry(key="aico.assignment_role", value="reviewer"),),
    )
    await bus.submit(task)

    sent_message = await channel.send_message(
        _incoming_message().source,
        MessageContent(text="Task accepted: task-parent [reviewer]"),
    )
    await orchestrator._stream_outputs_for_task(
        _incoming_message(),
        sent_message,
        task,
    )

    assert adapter.received_tasks[0].task_id == "task-parent"
    assert adapter.received_tasks[1].payload == (
        "Collaboration request from reviewer:\n\n"
        "Context from reviewer output so far:\n"
        "Findings:\n"
        "(a) keep /inbox read-only.\n"
        "(b) do not normalize batched approvals.\n\n"
        "Request:\n"
        "reflect (a)-(b) in the inbox plan"
    )
    assert any(
        message.text == "Collaboration requested\nsource: reviewer\ntarget: implementer"
        and message.spans
        for message in channel.sent_messages
    )
    collaboration_event = next(
        event
        for event in bus.audit_events(limit=None)
        if event.event_type is AuditEventType.COLLABORATION_REQUESTED
    )
    assert collaboration_event.actor_id == "reviewer"


async def test_orchestrator_splits_long_stream_output_across_messages() -> None:
    long_output = "x" * (STREAM_MESSAGE_TEXT_LIMIT + 120)
    adapter = ScriptedAdapter(output_texts=(long_output,))
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-long"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message())

    assert channel.sent_messages[0] == MessageContent(text="Task accepted: task-long")
    assert len(channel.edited_messages[-1].text) == STREAM_MESSAGE_TEXT_LIMIT
    assert channel.sent_messages[1].text == "x" * 120
    assert all(
        len(message.text) <= STREAM_MESSAGE_TEXT_LIMIT
        for message in (*channel.sent_messages[1:], *channel.edited_messages)
    )
    assert channel.edited_messages[-1].text + channel.sent_messages[1].text == long_output


async def test_orchestrator_reports_broadcast_usage_without_payload() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-8"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/broadcast"))

    assert adapter.received_tasks == []
    assert channel.sent_messages == [MessageContent(text="Usage: /broadcast <task>")]


async def test_orchestrator_manages_sessions_and_routes_plain_message_to_active_session() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    store = InMemoryAgentSessionStore(session_id_factory=lambda: "abcdef12-3456")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-session"),
        task_bus=TaskBus(adapter),
        session_store=store,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/sessions", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/new claude", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/use abcdef12", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="continue this", mentions=()))

    assert channel.sent_messages[0] == MessageContent(text="No sessions")
    assert channel.sent_messages[1].text.startswith("Session created: abcdef12")
    assert channel.sent_messages[2] == MessageContent(text="Session active: abcdef12 [claude]")
    assert adapter.received_tasks[0].target_persona == "claude"
    assert adapter.received_tasks[0].payload == "continue this"
    session = store.get("abcdef12-3456")
    assert session is not None
    assert session.status is AgentSessionStatus.IDLE


async def test_orchestrator_reports_agents_and_agent_card() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    directory = AgentDirectory(
        (
            AgentCard(
                name="implementer",
                adapter_name="claude-code",
                provider_name="claude-code",
                role_description="Role: implementer.",
                aliases=("claude",),
                capabilities=(Capability.CODE_EDIT, Capability.STREAM_OUTPUT),
                session_features=("new", "resume"),
            ),
        )
    )
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-agent"),
        task_bus=TaskBus(adapter),
        agent_directory=directory,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/agents", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/agent claude", mentions=()))

    assert channel.sent_messages[0].text == (
        "Agents:\n"
        "• claude -> claude-code (idle 0/1 running, max 1 concurrent) "
        "[role: implementer]\n\n"
        "Next:\n"
        "• /agent <agent>\n"
        "• /roles\n"
        "• /appoint <agent> as <role>"
    )
    assert channel.sent_messages[1].text.startswith("Agent: claude\n")
    assert "role: implementer" in channel.sent_messages[1].text
    assert "provider: claude-code\n" in channel.sent_messages[1].text
    assert "max_concurrent: 1\n" in channel.sent_messages[1].text
    assert "recommended_appointments: <= 1\n" in channel.sent_messages[1].text
    assert "skills: provider_cli via /skills claude" in channel.sent_messages[1].text
    assert (
        "Next:\n• /roles\n• /appoint claude as <role>\n• /new claude"
        in channel.sent_messages[1].text
    )
    assert adapter.received_tasks == []


async def test_orchestrator_reports_projects_and_assignments() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    directory = _agent_directory()
    project_directory = _project_directory()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        agent_directory=directory,
        project_directory=project_directory,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/projects", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/assignments aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/assignment aico-implementer", mentions=())
    )

    assert channel.sent_messages[0].text == "Projects:\n• aico: AI Company OS - Phase 5"
    assert channel.sent_messages[1].text.startswith("Project active: aico [AI Company OS]\n")
    assert "Team:\n• implementer -> claude" in channel.sent_messages[1].text
    assert channel.sent_messages[2].text.startswith("Assignments for aico:\n")
    assert channel.sent_messages[3].text.startswith("Assignment: aico-implementer\n")
    assert "provider: claude-code\n" in channel.sent_messages[3].text
    assert adapter.received_tasks == []


async def test_orchestrator_shows_active_project_office_with_project_command() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/project", mentions=()))

    assert channel.sent_messages[0] == MessageContent(
        text="No active project. Use /project <project> first."
    )
    assert channel.sent_messages[1].text.startswith("Project active: aico [AI Company OS]\n")
    assert channel.sent_messages[2].text == channel.sent_messages[1].text
    assert adapter.received_tasks == []


async def test_orchestrator_handles_team_who_appoint_default_and_ask_commands() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    store = InMemoryAgentSessionStore(session_id_factory=lambda: "appointment-session-1")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        session_store=store,
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        provider_session_factory=lambda session: ProviderSessionRef(
            provider_name="claude-code",
            session_id=session.session_id,
        ),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/team", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/who implementer", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/appoint claude as tester read_repo run_tests", mentions=())
    )
    await orchestrator.handle_incoming(
        _incoming_message(text="/appoint claude as tester read_repo run_tests", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="/lead tester", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/team", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/ask tester verify tests", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="plain project task", mentions=()))

    assert channel.sent_messages[1].text.startswith("Team for aico:\n")
    assert channel.sent_messages[2].text.startswith("aico / implementer\n")
    assert channel.sent_messages[3].text.startswith("Appointment active\n\nclaude is appointed")
    assert channel.sent_messages[4].text.startswith("Appointment active\n\nclaude is appointed")
    assert channel.sent_messages[5].text == (
        "Lead role for aico: tester -> claude\nPlain messages will go to this lead role."
    )
    team_after_lead = channel.sent_messages[6].text
    assert team_after_lead.count("• tester -> claude") == 1
    assert "lead: tester -> claude" in team_after_lead
    assert "• tester -> claude (read_repo, run_tests) [lead]" in team_after_lead
    assert "Role: tester" in adapter.received_tasks[0].payload
    assert "Appointment contract:" in adapter.received_tasks[0].payload
    assert "Current task:\nverify tests" in adapter.received_tasks[0].payload
    assert adapter.received_tasks[0].metadata[1].value == "aico-tester"
    assert "Current task:\nplain project task" in adapter.received_tasks[1].payload
    assert adapter.received_tasks[1].metadata[1].value == "aico-tester"


async def test_orchestrator_goal_command_attaches_goal_brief_to_project_role() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-goal-1"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(
            text="/goal implementer inspect release plan 验收: summarize blockers",
            mentions=(),
        )
    )
    await orchestrator.handle_incoming(_incoming_message(text="/task task-goa", mentions=()))

    goal_notice = channel.sent_messages[1].text
    task = adapter.received_tasks[0]

    assert goal_notice.startswith("Goal queued. goal-task-goa\n")
    assert "owner: implementer -> claude\n" in goal_notice
    assert "objective: inspect release plan" in goal_notice
    assert "acceptance:\n• summarize blockers" in goal_notice
    assert channel.sent_messages[1].spans
    assert "AICO Goal Brief" in task.payload
    assert "goal_id: goal-task-goa" in task.payload
    assert "objective: inspect release plan" in task.payload
    assert "Do not claim done until every acceptance criterion has evidence." in task.payload
    assert _metadata_value(task, "aico.intent") == "goal_brief"
    assert _metadata_value(task, "aico.goal_id") == "goal-task-goa"
    detail = channel.sent_messages[-1].text
    assert "Goal brief:\nid: goal-task-goa" in detail
    assert "objective: inspect release plan" in detail
    assert "acceptance: summarize blockers" in detail


async def test_orchestrator_ask_with_acceptance_attaches_goal_brief_conservatively() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-goal-2"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(
            text="/ask implementer inspect release plan 验收: summarize blockers",
            mentions=(),
        )
    )

    goal_notice = channel.sent_messages[1].text
    task = adapter.received_tasks[0]

    assert goal_notice.startswith("Verifiable task detected. Goal brief attached. goal-task-goa\n")
    assert "owner: implementer -> claude\n" in goal_notice
    assert "AICO Goal Brief" in task.payload
    assert _metadata_value(task, "aico.intent") == "goal_brief"
    assert _metadata_value(task, "aico.goal_acceptance") == "summarize blockers"


async def test_orchestrator_reports_project_roles_and_appointment_gaps() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/roles", mentions=()))

    roles = channel.sent_messages[-1].text
    assert roles.startswith("Roles: aico [AI Company OS]\n")
    assert "Core\n• implementer | Implementation Lead | claude" in roles
    assert "Hidden: tester" in roles
    assert "permissions:" not in roles

    await orchestrator.handle_incoming(_incoming_message(text="/roles all", mentions=()))

    all_roles = channel.sent_messages[-1].text
    assert "Support\n• tester | Test Lead | open" in all_roles

    await orchestrator.handle_incoming(_incoming_message(text="/role implementer", mentions=()))

    detail = channel.sent_messages[-1].text
    assert detail.startswith("Role: implementer [aico]\n")
    assert "scope: code, tests, docs" in detail
    assert "risk ladder: read_only -> write_files -> shell_exec -> destructive" in detail


async def test_orchestrator_proposes_and_confirms_project_role() -> None:
    adapter = ScriptedAdapter(
        name="claude-code",
        output_texts=(
            """
            {
              "id": "growth-analyst",
              "title": "Growth Analyst",
              "summary": "Analyze activation and retention opportunities.",
              "default_permissions": ["docs", "audit"],
              "approval_required": ["destructive"],
              "inline_prompt": "Focus on measurable product opportunities."
            }
            """,
        ),
    )
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-role"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/role propose 需要一个增长分析岗位", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="/role confirm", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/roles", mentions=()))

    assert channel.sent_messages[1] == MessageContent(text="Drafting role proposal for aico...")
    proposal = channel.sent_messages[2].text
    assert proposal.startswith("Role proposal for aico\n")
    assert "id: growth-analyst" in proposal
    assert "Send /role confirm" in proposal
    assert [action.value for action in channel.sent_messages[2].actions] == [
        "/role confirm",
        "/role discard",
    ]
    assert channel.sent_messages[3].text.startswith("Role added to aico: growth-analyst\n")
    roles = channel.sent_messages[4].text
    assert "Custom\n• growth-analyst | Growth Analyst | open" in roles
    assert adapter.received_tasks[0].metadata[-1].key == "aico.intent"
    assert adapter.received_tasks[0].metadata[-1].value == "role_proposal"


async def test_orchestrator_unappoints_project_role_and_updates_roles_view() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/appoint claude as tester read_repo run_tests", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="/unappoint tester", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/roles", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/who tester", mentions=()))

    assert channel.sent_messages[2].text.startswith("Appointment removed\n\n")
    assert "claude is no longer appointed to aico as tester" in channel.sent_messages[2].text
    roles = channel.sent_messages[3].text
    assert "Hidden: tester" in roles
    assert channel.sent_messages[4] == MessageContent(text="Role not appointed in aico: tester")


async def test_orchestrator_project_team_acceptance_flow() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    task_ids = iter(
        (
            "task-summary-brief",
            "task-summary-risks",
            "task-summary-blockers",
            "task-summary-next",
            "task-summary-daily",
            "task-summary-weekly",
            "task-ask",
            "task-plain-tester",
            "task-plain-fallback",
        )
    )
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: next(task_ids)),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    readonly_commands = (
        "/project aico",
        "/project",
        "/brief",
        "/risks",
        "/blockers",
        "/next",
        "/daily",
        "/weekly",
        "/roles",
        "/team",
        "/who implementer",
    )
    for command in readonly_commands:
        await orchestrator.handle_incoming(_incoming_message(text=command, mentions=()))

    await orchestrator.handle_incoming(
        _incoming_message(text="/appoint claude as tester read_repo run_tests", mentions=())
    )
    await orchestrator.handle_incoming(
        _incoming_message(text="/ask tester verify tests", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="/lead tester", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="plain tester task", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/unappoint tester", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/roles", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/who tester", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="plain fallback task", mentions=()))

    assert channel.sent_messages[0].text.startswith("Project active: aico [AI Company OS]\n")
    assert channel.sent_messages[1].text == channel.sent_messages[0].text
    sent_texts = tuple(message.text for message in channel.sent_messages)
    assert any("Brief: aico [AI Company OS]\n" in text for text in sent_texts)
    assert any("Risks: aico [AI Company OS]\n" in text for text in sent_texts)
    assert any("Blockers: aico [AI Company OS]\n" in text for text in sent_texts)
    assert any("Next actions: aico [AI Company OS]\n" in text for text in sent_texts)
    assert any("Daily report: aico [AI Company OS]\n" in text for text in sent_texts)
    assert any("Weekly report: aico [AI Company OS]\n" in text for text in sent_texts)
    assert any("Hidden: tester" in text for text in sent_texts)
    assert any(
        "Appointment active\n\nclaude is appointed to aico as tester" in text for text in sent_texts
    )
    assert any("Lead role for aico: tester -> claude" in text for text in sent_texts)
    assert any(
        "Appointment removed\n\nclaude is no longer appointed to aico as tester" in text
        for text in sent_texts
    )
    assert channel.sent_messages[-2] == MessageContent(text="Role not appointed in aico: tester")
    work_tasks = tuple(
        task
        for task in adapter.received_tasks
        if _metadata_value(task, "aico.intent") != "project_summary"
    )
    assert [task.target_persona for task in work_tasks] == [
        "implementer",
        "implementer",
        "implementer",
    ]
    assert [_metadata_value(task, "aico.assignment_role") for task in work_tasks] == [
        "tester",
        "tester",
        "implementer",
    ]
    assert "Current task:\nverify tests" in work_tasks[0].payload
    assert "Current task:\nplain tester task" in work_tasks[1].payload
    assert "Current task:\nplain fallback task" in work_tasks[2].payload


async def test_orchestrator_lead_can_answer_project_questions_without_false_approval() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    project_directory = _project_directory_with_risky_role_prompt()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-question"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=project_directory,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="这个项目现在团队分工和下一步重点是什么?", mentions=())
    )

    assert adapter.received_tasks
    assert (
        "Current task:\n这个项目现在团队分工和下一步重点是什么?"
        in adapter.received_tasks[0].payload
    )
    assert all("Approval required" not in message.text for message in channel.sent_messages)


async def test_orchestrator_reports_project_brief_and_risks() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/brief", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/claude please delete all logs", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="/risks", mentions=()))

    assert channel.sent_messages[1].text.startswith("Boss summary\nhello world\n\nFacts\n")
    assert "Brief: aico [AI Company OS]\n" in channel.sent_messages[1].text
    assert "lead: implementer -> claude" in channel.sent_messages[1].text
    assert "team:\n• implementer -> claude" in channel.sent_messages[1].text
    assert channel.sent_messages[-1].text.startswith("Boss summary\nhello world\n\nFacts\n")
    assert "Risks: aico [AI Company OS]\n" in channel.sent_messages[-1].text
    assert "destructive" in channel.sent_messages[-1].text
    assert [task.metadata[-1].value for task in adapter.received_tasks] == [
        "project_summary",
        "project_summary",
    ]


async def test_orchestrator_project_summary_failure_keeps_facts_visible() -> None:
    adapter = ScriptedAdapter(name="claude-code", ack_status=AckStatus.BUSY)
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-summary"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/brief", mentions=()))

    assert channel.sent_messages[1].text.startswith("Brief: aico [AI Company OS]\n")
    assert "Boss summary" not in channel.sent_messages[1].text
    assert adapter.received_tasks[0].metadata[-1].value == "project_summary"


async def test_orchestrator_risks_omit_write_approval_and_unknown_persona_noise() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    bus = TaskBus(AdapterRegistry([adapter]))
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=bus,
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await bus.submit(
        Task(
            task_id="task-unknown",
            payload="inspect this",
            requester_id="user-1",
            target_persona="risky",
        )
    )
    await bus.submit(
        Task(
            task_id="task-write",
            payload="modify docs/human/daily-ops.md",
            requester_id="user-1",
            target_persona="claude-code",
        )
    )
    await bus.submit(
        Task(
            task_id="task-delete",
            payload="delete all logs",
            requester_id="user-1",
            target_persona="claude-code",
        )
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/risks", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/blockers", mentions=()))

    risks = channel.sent_messages[-2].text
    blockers = channel.sent_messages[-1].text
    assert risks.startswith("Risks: aico [AI Company OS]\n")
    assert "destructive task task-delete" in risks
    assert "task-write" not in risks
    assert "write_files" not in risks
    assert "task-unknown" not in risks
    assert "unknown adapter or persona" not in risks
    assert "approval_requested" not in risks
    assert blockers.startswith("Blockers: aico [AI Company OS]\n")
    assert "waiting decisions:" in blockers
    assert "task-wri" in blockers
    assert "use /approve task-wri or /reject task-wri" in blockers
    assert "failed / rejected work:" in blockers
    assert "task-unknown" in blockers
    assert "unknown adapter or persona: risky" in blockers


async def test_orchestrator_reports_next_project_actions() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    bus = TaskBus(AdapterRegistry([adapter]))
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=bus,
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await bus.submit(
        Task(
            task_id="task-write",
            payload="modify docs/human/daily-ops.md",
            requester_id="user-1",
            target_persona="claude-code",
        )
    )
    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/next", mentions=()))

    next_actions = channel.sent_messages[-1].text
    assert next_actions.startswith("Next actions: aico [AI Company OS]\n")
    assert "lead: implementer -> claude" in next_actions
    assert "Decide pending write_files task task-wri" in next_actions
    assert "/approve task-wri or /reject task-wri" in next_actions


async def test_orchestrator_reports_daily_and_weekly_project_state() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-report"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/ask implementer inspect", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="/daily", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/weekly", mentions=()))

    daily = channel.sent_messages[-2].text
    weekly = channel.sent_messages[-1].text

    assert daily.startswith("Boss summary\nhello world\n\nFacts\n")
    assert "Daily report: aico [AI Company OS]\n" in daily
    assert "window: last 24h in local AICO state" in daily
    assert "progress:\n• task-report [claude-code]: done" in daily
    assert "team:\n• implementer -> claude" in daily
    assert weekly.startswith("Boss summary\nhello world\n\nFacts\n")
    assert "Weekly report: aico [AI Company OS]\n" in weekly
    assert "window: last 7d in local AICO state" in weekly
    assert "context:" in weekly


async def test_orchestrator_queues_overnight_delegation_to_project_lead() -> None:
    adapter = ScriptedAdapter(name="claude-code", output_texts=("overnight done",))
    channel = RecordingChannel()
    store = InMemoryAgentSessionStore(session_id_factory=lambda: "overnight-session-1")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-night-1"),
        task_bus=TaskBus(adapter),
        session_store=store,
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        provider_session_factory=lambda session: ProviderSessionRef(
            provider_name="claude-code",
            session_id=session.session_id,
        ),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/overnight finish the phase 8 plan", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="/overnight", mentions=()))

    queued = channel.sent_messages[1].text
    task = adapter.received_tasks[0]
    provider = provider_session_from_task(task)

    assert queued.startswith("Overnight delegation queued: night-task-nig\n")
    assert "project: aico [AI Company OS]\n" in queued
    assert "lead: implementer -> claude\n" in queued
    assert "tracking: /task task-nig\n" in queued
    assert "Morning:\n- /daily aico\n- /tasks" in queued
    assert "Offline delegation request for the project lead." in task.payload
    assert "Boss goal: finish the phase 8 plan" in task.payload
    assert "Leave a morning handoff with: done, blocked, risks, and next 3 actions." in task.payload
    assert _metadata_value(task, "aico.intent") == "offline_delegation"
    assert _metadata_value(task, "aico.offline_delegation_id") == "night-task-nig"
    assert provider is not None
    assert provider.mode is ProviderSessionMode.NEW
    assert channel.sent_messages[-1].text.startswith("Overnight delegations for aico:\n")
    assert "• night-task-nig: implementer -> claude (task-nig)" in channel.sent_messages[-1].text


async def test_orchestrator_inbox_summarizes_project_attention_and_handoffs() -> None:
    adapter = ScriptedAdapter(name="claude-code", output_texts=("overnight done",))
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-night-1"),
        task_bus=bus,
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/overnight finish the phase 8 plan", mentions=())
    )
    await bus.submit(
        _project_task(
            "task-running-1",
            target_persona="reviewer",
            payload="review quietly",
        )
    )
    await bus.submit(
        _project_task(
            "task-approval-1",
            target_persona="implementer",
            payload="update docs",
        )
    )
    await bus.submit(
        _project_task(
            "task-goal-1",
            target_persona="tester",
            payload="check acceptance evidence",
            metadata=(MetadataEntry(key="aico.intent", value="goal_brief"),),
        )
    )

    await orchestrator.handle_incoming(_incoming_message(text="/inbox", mentions=()))

    inbox = channel.sent_messages[-1].text
    assert "Inbox: aico\n" in inbox
    assert "scope: current project (aico)\n" in inbox
    assert "First action:\n• decide task-app -> /approve task-app or /reject task-app" in inbox
    assert "decide task-app [implementer]" in inbox
    assert "-> /approve task-app or /reject task-app" in inbox
    assert "monitor task-run [reviewer/claude-code] running" in inbox
    assert "-> /task task-run or /interrupt task-run" in inbox
    assert "inspect handoff night-task-nig: implementer -> claude (task-nig)" in inbox
    assert "inspect goal_brief: task-goa [running] -> /task task-goa" in inbox
    assert "Next:\n• /inbox\n• /daily aico\n• /tasks\n• /audit" in inbox


async def test_orchestrator_morning_handoff_summarizes_absence_recovery() -> None:
    adapter = ScriptedAdapter(name="claude-code", output_texts=("morning evidence",))
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-night-2"),
        task_bus=bus,
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/overnight finish the morning report", mentions=())
    )
    await bus.submit(
        _project_task(
            "task-approval-2",
            target_persona="implementer",
            payload="update docs",
        )
    )
    await bus.submit(
        _project_task(
            "task-running-2",
            target_persona="tester",
            payload="check status",
        )
    )

    await orchestrator.handle_incoming(_incoming_message(text="/morning", mentions=()))

    handoff = channel.sent_messages[-1].text
    assert "Morning handoff: aico\n" in handoff
    assert "Done:\n• task-nig [implementer] done" in handoff
    assert "Blocked:\n• task-app waiting approval" in handoff
    assert "Risks:\n• task-app [write_files] waiting_approval" in handoff
    assert "Overnight handoffs:\n• night-task-nig: implementer -> claude" in handoff
    assert "Next actions:\n• /approve task-app or /reject task-app" in handoff
    assert "• /task task-run or /interrupt task-run" in handoff
    assert "• /dream" in handoff


async def test_orchestrator_goal_runs_outcome_grader_when_tester_is_appointed() -> None:
    adapter = ScriptedAdapter(
        name="claude-code",
        output_texts=("Evidence: summarized blockers and next action.",),
    )
    channel = RecordingChannel()
    task_ids = iter(("task-goal-3", "task-grade-3"))
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: next(task_ids)),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory_with_tester(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(
            text="/goal implementer inspect release plan 验收: summarize blockers",
            mentions=(),
        )
    )

    owner_task = adapter.received_tasks[0]
    grader_task = adapter.received_tasks[1]
    assert "AICO Goal Brief" in owner_task.payload
    assert "AICO Outcome Grader" in grader_task.payload
    assert "graded_task_id: task-goal-3" in grader_task.payload
    assert "Evidence: summarized blockers and next action." in grader_task.payload
    assert _metadata_value(grader_task, "aico.intent") == "outcome_grader"
    assert _metadata_value(grader_task, "aico.graded_task_id") == "task-goal-3"
    assert _metadata_value(grader_task, "aico.outcome_goal_id") == "goal-task-goa"
    assert any(
        message.text.startswith("Outcome grading queued: task-gra")
        for message in channel.sent_messages
    )


async def test_orchestrator_dream_writes_reviewable_candidate_memory(tmp_path: Path) -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    memory_store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default"),
        task_bus=bus,
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        memory_store=memory_store,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await bus.submit(
        _project_task(
            "task-approval-3",
            target_persona="implementer",
            payload="update docs",
        )
    )
    await orchestrator.handle_incoming(_incoming_message(text="/dream", mentions=()))

    dream = channel.sent_messages[-1].text
    atoms = memory_store.list_atoms(MemoryScope.project("aico"))
    assert dream.startswith("Dream review: aico\n")
    assert "status: candidate experience only" in dream
    assert "Meaning:\n• These are reusable lessons" in dream
    assert "1 task(s) are blocked on approval (task-app)" in dream
    assert channel.sent_messages[-1].spans
    assert "active experience unchanged" not in dream
    assert len(atoms) == 1
    assert atoms[0].status is MemoryStatus.CANDIDATE
    assert atoms[0].source == "dream_review"
    assert atoms[0].tags == ("dream", "runbook-candidate")


async def test_orchestrator_promoted_experience_injects_into_role_prompt(tmp_path: Path) -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    memory_store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default"),
        task_bus=bus,
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        memory_store=memory_store,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await bus.submit(
        _project_task(
            "task-approval-promote",
            target_persona="implementer",
            payload="update docs",
        )
    )
    await orchestrator.handle_incoming(_incoming_message(text="/dream", mentions=()))
    candidate = memory_store.list_atoms(MemoryScope.project("aico"))[0]
    await orchestrator.handle_incoming(
        _incoming_message(
            text=f"/experience promote {candidate.memory_id} as implementer",
            mentions=(),
        )
    )
    adapter.received_tasks.clear()
    await orchestrator.handle_incoming(
        _incoming_message(text="/ask implementer ship it", mentions=())
    )

    assert adapter.received_tasks, "implementer task should have been dispatched"
    payload = adapter.received_tasks[-1].payload
    assert "Reusable experience (promoted lessons):" in payload
    assert candidate.memory_id in payload
    injected_ids = _metadata_value(
        adapter.received_tasks[-1],
        "aico.injected_experience_ids",
    )
    assert injected_ids is not None
    assert candidate.memory_id in injected_ids


async def test_orchestrator_restores_overnight_delegations_from_sqlite(
    tmp_path: Path,
) -> None:
    state_db_path = tmp_path / "aico-state.db"
    first_adapter = ScriptedAdapter(name="claude-code", output_texts=("queued",))
    first_channel = RecordingChannel()
    first_orchestrator = Orchestrator(
        channel=first_channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-night-1"),
        task_bus=TaskBus(first_adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        offline_delegation_store=SQLiteOfflineDelegationStore(state_db_path),
    )

    await first_orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await first_orchestrator.handle_incoming(
        _incoming_message(text="/overnight finish the phase 8 plan", mentions=())
    )

    restored_adapter = ScriptedAdapter(name="claude-code")
    restored_channel = RecordingChannel()
    restored_orchestrator = Orchestrator(
        channel=restored_channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-new"),
        task_bus=TaskBus(restored_adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        offline_delegation_store=SQLiteOfflineDelegationStore(state_db_path),
    )

    await restored_orchestrator.handle_incoming(
        _incoming_message(text="/project aico", mentions=())
    )
    await restored_orchestrator.handle_incoming(_incoming_message(text="/overnight", mentions=()))

    assert restored_channel.sent_messages[-1].text.startswith("Overnight delegations for aico:\n")
    assert (
        "• night-task-nig: implementer -> claude (task-nig)"
        in restored_channel.sent_messages[-1].text
    )
    assert restored_adapter.received_tasks == []


async def test_orchestrator_overnight_requires_challenger() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    directory = _project_directory()
    directory.remove_appointment_for_role("aico", "challenger")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-night-1"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=directory,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/overnight finish the phase 8 plan", mentions=())
    )

    assert channel.sent_messages[-1].text == (
        "Team incomplete for aico: missing challenger.\n"
        "Offline delegation needs a project lead and challenger.\n\n"
        "Next:\n"
        "- /team\n"
        "- /appoint <agent> as challenger"
    )
    assert adapter.received_tasks == []


async def test_orchestrator_overnight_requires_active_project() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-night"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(
        _incoming_message(text="/overnight finish the phase 8 plan", mentions=())
    )

    assert channel.sent_messages == [
        MessageContent(text="No active project. Use /project <project> first.")
    ]
    assert adapter.received_tasks == []


async def test_orchestrator_overnight_keeps_risky_goal_waiting_for_approval() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-night-risk"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/overnight update docs", mentions=())
    )

    assert channel.sent_messages[1].text.startswith("Overnight delegation queued: night-task-nig\n")
    assert channel.sent_messages[2].text.startswith("Approval required: task-nig\n")
    assert adapter.received_tasks == []


async def test_orchestrator_routes_plain_message_to_active_project_default_assignment() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    store = InMemoryAgentSessionStore(session_id_factory=lambda: "assignment-session-1")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        session_store=store,
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        provider_session_factory=lambda session: ProviderSessionRef(
            provider_name="claude-code",
            session_id=session.session_id,
        ),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/use project aico", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="continue project", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="next project task", mentions=()))

    first_task = adapter.received_tasks[0]
    second_task = adapter.received_tasks[1]
    first_provider = provider_session_from_task(first_task)
    second_provider = provider_session_from_task(second_task)
    metadata = {entry.key: entry.value for entry in first_task.metadata}

    assert channel.sent_messages[0] == MessageContent(
        text="Project active: aico [AI Company OS]\ndefault assignment: aico-implementer"
    )
    assert first_task.target_persona == "implementer"
    assert "Role: implementer" in first_task.payload
    assert "Appointment contract:" in first_task.payload
    assert "Current task:\ncontinue project" in first_task.payload
    assert first_task.context_ref == "aico"
    assert metadata["aico.assignment_seat"] == "aico-implementer"
    assert first_provider is not None
    assert first_provider.mode is ProviderSessionMode.NEW
    assert second_provider is not None
    assert second_provider.session_id == first_provider.session_id
    assert second_provider.mode is ProviderSessionMode.RESUME


async def test_orchestrator_rebuilds_assignment_session_after_reappointing_role() -> None:
    claude = ScriptedAdapter(name="claude-code", output_texts=("claude done",))
    codex = ScriptedAdapter(name="codex", output_texts=("codex done",))
    channel = RecordingChannel()
    store = InMemoryAgentSessionStore(
        session_id_factory=iter(("claude-session-1", "codex-session-1")).__next__
    )
    directory = AgentDirectory(
        (
            AgentCard(
                name="claude",
                adapter_name="claude-code",
                provider_name="claude-code",
                role_description="Role: implementer.",
                aliases=("implementer",),
            ),
            AgentCard(
                name="codex",
                adapter_name="codex",
                provider_name="codex",
                role_description="Role: reviewer.",
            ),
        )
    )
    projects = ProjectAssignmentDirectory(
        ProjectAssignmentConfig(
            agents={
                "claude": CompanyAgentProfile(
                    id="claude",
                    provider="claude-code",
                    title="Claude",
                ),
                "codex": CompanyAgentProfile(id="codex", provider="codex", title="Codex"),
            },
            roles={"pm": RoleProfile(id="pm", title="Release PM")},
            projects={
                "release-room": ProjectProfile(
                    id="release-room",
                    name="Release Room",
                    repo="/repo/release-room",
                    default_role="pm",
                    default_assignment="release-room-pm",
                    roles={"pm": ProjectRoleProfile(role="pm")},
                )
            },
            assignments=(
                AssignmentProfile(
                    project="release-room",
                    agent="claude",
                    role="pm",
                    seat="release-room-pm",
                ),
            ),
        )
    )
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-pm"),
        task_bus=TaskBus(
            AdapterRegistry([claude, codex]),
            persona_registry=PersonaRegistry(
                (
                    PersonaProfile(
                        name="claude",
                        adapter_name="claude-code",
                        role_instruction="Role: implementer.",
                    ),
                    PersonaProfile(
                        name="codex",
                        adapter_name="codex",
                        role_instruction="Role: reviewer.",
                    ),
                )
            ),
        ),
        session_store=store,
        agent_directory=directory,
        project_directory=projects,
        provider_session_factory=lambda session: ProviderSessionRef(
            provider_name=session.adapter_name,
            session_id=session.session_id,
        ),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/use project release-room"))
    await orchestrator.handle_incoming(_incoming_message(text="/ask pm first plan"))
    await orchestrator.handle_incoming(_incoming_message(text="/appoint codex as pm docs audit"))
    await orchestrator.handle_incoming(_incoming_message(text="/ask pm second plan"))

    claude_provider = provider_session_from_task(claude.received_tasks[0])
    codex_provider = provider_session_from_task(codex.received_tasks[0])

    assert claude_provider is not None
    assert claude_provider.provider_name == "claude-code"
    assert claude_provider.mode is ProviderSessionMode.NEW
    assert codex_provider is not None
    assert codex_provider.provider_name == "codex"
    assert codex_provider.session_id == "codex-session-1"
    assert codex_provider.mode is ProviderSessionMode.NEW


async def test_orchestrator_injects_project_memory_for_active_project_task(
    tmp_path: Path,
) -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    memory_store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    memory_store.append_atom(
        MemoryAtom(
            memory_id="mem-aico",
            claim="AICO memory must be agent-driven.",
            evidence=(
                MemoryEvidence(
                    ref="audit:event-1",
                    source="test",
                    captured_at=datetime(2026, 5, 15, tzinfo=UTC),
                ),
            ),
            scope=MemoryScope.project("aico"),
            source="test",
            confidence=0.92,
            created_by="tester",
            tags=("memory",),
        )
    )
    memory_store.append_atom(
        MemoryAtom(
            memory_id="mem-other",
            claim="Other project memory must not leak.",
            evidence=(
                MemoryEvidence(
                    ref="audit:event-2",
                    source="test",
                    captured_at=datetime(2026, 5, 15, tzinfo=UTC),
                ),
            ),
            scope=MemoryScope.project("other"),
            source="test",
            confidence=0.99,
            created_by="tester",
            tags=("memory",),
        )
    )
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        memory_store=memory_store,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/use project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="continue memory design", mentions=())
    )

    payload = adapter.received_tasks[0].payload

    assert "Shared memory:\n- [mem-aico] AICO memory must be agent-driven." in payload
    assert "Other project memory must not leak" not in payload
    assert payload.index("Shared memory:") < payload.index("Current task:")


async def test_orchestrator_injects_broadcast_team_memory_for_active_project_task(
    tmp_path: Path,
) -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    memory_store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    source = memory_store.append_atom(
        MemoryAtom(
            memory_id="mem-source",
            claim="Team consensus: memory broadcasts should reduce repeated A2A context.",
            evidence=(
                MemoryEvidence(
                    ref="audit:event-1",
                    source="test",
                    captured_at=datetime(2026, 5, 15, tzinfo=UTC),
                ),
            ),
            scope=MemoryScope.project("aico"),
            source="test",
            confidence=0.92,
            created_by="tester",
            tags=("broadcast", "memory"),
        )
    )
    MemoryBroadcastService(memory_store).broadcast_to_team(
        source_memory_id=source.memory_id,
        team_scope=MemoryScope.team("aico", "default"),
        recipients=("claude",),
        created_by="lead-agent",
        reason="team consensus",
    )
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        memory_store=memory_store,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/use project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="review broadcast memory", mentions=())
    )

    payload = adapter.received_tasks[0].payload
    assert "Shared memory:" in payload
    assert "Team consensus: memory broadcasts should reduce repeated A2A context." in payload
    assert "scope: team:aico/default" in payload


async def test_orchestrator_lead_decision_workflow_consults_roles_records_audit_and_memory(
    tmp_path: Path,
) -> None:
    adapter = ScriptedAdapter(name="claude-code", output_texts=("decision output",))
    channel = RecordingChannel()
    task_ids = iter(("task-challenger", "task-reviewer", "task-lead"))
    memory_store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    _append_memory(
        memory_store,
        "mem-public",
        "Release policy: public GIF must show audit and approvals.",
        purpose_tags=(MemoryPurpose.PUBLIC_BROADCAST,),
    )
    _append_memory(
        memory_store,
        "mem-progress",
        "Release progress: Stage 3 README GIF is ready.",
        purpose_tags=(MemoryPurpose.TASK_KEY_PROGRESS,),
    )
    _append_memory(
        memory_store,
        "mem-review",
        "Prior decision review: do not ship without challenger objections.",
        purpose_tags=(MemoryPurpose.DECISION_REVIEW,),
    )
    _append_memory(
        memory_store,
        "mem-private",
        "Private scratchpad: release secret must not leak.",
        purpose_tags=(MemoryPurpose.TASK_PRIVATE,),
    )
    _append_memory(
        memory_store,
        "mem-general",
        "General context: release wording should stay concise.",
        purpose_tags=(MemoryPurpose.GENERAL_CONTEXT,),
    )
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: next(task_ids)),
        task_bus=bus,
        agent_directory=_agent_directory(),
        project_directory=_project_directory_with_reviewer(),
        memory_store=memory_store,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="decide whether release Stage 3 now", mentions=())
    )

    assert len(adapter.received_tasks) == 3
    challenger_task, reviewer_task, lead_task = adapter.received_tasks
    assert "Role: challenger" in challenger_task.payload
    assert "Decision consultation request." in challenger_task.payload
    assert "Role: reviewer" in reviewer_task.payload
    assert "Decision consultation request." in reviewer_task.payload
    assert "Role: implementer" in lead_task.payload
    assert "Lead decision workflow." in lead_task.payload
    assert "Output a decision memo with exactly these sections:" in lead_task.payload
    assert "mem-public" in lead_task.payload
    assert "mem-progress" in lead_task.payload
    assert "mem-review" in lead_task.payload
    assert "mem-private" not in lead_task.payload
    assert "mem-general" not in lead_task.payload
    assert "challenger -> claude (task-challenger): decision output" in lead_task.payload
    assert "reviewer -> claude (task-reviewer): decision output" in lead_task.payload

    decision_events = [
        event
        for event in bus.audit_events(limit=None)
        if event.event_type is AuditEventType.LEAD_DECISION_RECORDED
    ]
    assert len(decision_events) == 1
    assert decision_events[0].task_id == "task-lead"
    detail = json.loads(decision_events[0].detail or "{}")
    assert detail["project_id"] == "aico"
    assert set(detail["memory_refs"]) == {"mem-public", "mem-progress", "mem-review"}
    assert [item["role"] for item in detail["consultations"]] == ["challenger", "reviewer"]

    decision_memories = [
        atom
        for atom in memory_store.list_atoms(MemoryScope.project("aico"))
        if MemoryPurpose.DECISION_REVIEW in atom.purpose_tags
        and atom.source == "lead_decision_workflow"
    ]
    assert len(decision_memories) == 1
    assert "decision output" in decision_memories[0].claim
    assert decision_memories[0].evidence[0].ref == f"audit:{decision_events[0].event_id}"


async def test_orchestrator_ask_lead_alias_runs_lead_decision_workflow() -> None:
    adapter = ScriptedAdapter(name="claude-code", output_texts=("decision output",))
    channel = RecordingChannel()
    task_ids = iter(("task-challenger", "task-reviewer", "task-lead"))
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: next(task_ids)),
        task_bus=bus,
        agent_directory=_agent_directory(),
        project_directory=_project_directory_with_reviewer(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(
            text="/ask lead decide whether Phase 8 operator inbox should start now",
            mentions=(),
        )
    )

    assert len(adapter.received_tasks) == 3
    assert adapter.received_tasks[-1].task_id == "task-lead"
    assert "Lead decision workflow." in adapter.received_tasks[-1].payload
    assert any(
        event.event_type is AuditEventType.LEAD_DECISION_RECORDED
        for event in bus.audit_events(limit=None)
    )


async def test_orchestrator_memory_commands_require_active_project(tmp_path: Path) -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    memory_store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        memory_store=memory_store,
    )

    await orchestrator.handle_incoming(
        _incoming_message(text="/remember memory is project-scoped", mentions=())
    )

    assert channel.sent_messages == [
        MessageContent(text="No active project. Use /project <project> first.")
    ]
    assert memory_store.list_atoms(MemoryScope.project("aico")) == ()
    assert adapter.received_tasks == []


async def test_orchestrator_memory_commands_explain_how_to_enable_store() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/use project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/remember memory is project-scoped", mentions=())
    )

    assert channel.sent_messages[-1] == MessageContent(
        text=(
            "Shared memory is not enabled for this running AICO process.\n\n"
            "Set AICO_MEMORY_PATH before starting aico-phase1, then restart it:\n"
            'export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"\n\n'
            "After restart:\n"
            "- /use project <project>\n"
            "- /remember <fact>"
        )
    )
    assert adapter.received_tasks == []


async def test_orchestrator_remember_recall_and_forget_project_memory(
    tmp_path: Path,
) -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    memory_store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        memory_store=memory_store,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/use project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/remember Phase 7 memory must be agent-driven.", mentions=())
    )
    memory_store.append_atom(
        MemoryAtom(
            memory_id="mem-other-project",
            claim="Other project memory must not be archived from aico.",
            evidence=(
                MemoryEvidence(
                    ref="audit:event-1",
                    source="test",
                    captured_at=datetime(2026, 5, 15, tzinfo=UTC),
                ),
            ),
            scope=MemoryScope.project("other"),
            source="test",
            confidence=1.0,
            created_by="tester",
        )
    )
    atom = memory_store.list_atoms(MemoryScope.project("aico"))[0]
    await orchestrator.handle_incoming(_incoming_message(text="/recall agent-driven", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="/forget mem-other-project", mentions=())
    )
    await orchestrator.handle_incoming(
        _incoming_message(text=f"/forget {atom.memory_id}", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="/recall agent-driven", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="continue memory design", mentions=())
    )

    assert channel.sent_messages[1].text.startswith("Memory remembered\n")
    assert f"id: {atom.memory_id}" in channel.sent_messages[1].text
    assert "scope: project:aico" in channel.sent_messages[1].text
    assert "project: aico" in channel.sent_messages[1].text
    assert "Phase 7 memory must be agent-driven." in channel.sent_messages[2].text
    assert channel.sent_messages[1].spans
    assert f"• {atom.memory_id} | confidence: 1.00 | scope: project:aico" in (
        channel.sent_messages[2].text
    )
    assert channel.sent_messages[2].spans
    assert "| purpose: general_context" in channel.sent_messages[2].text
    assert channel.sent_messages[3].text == "Memory not found in active project: mem-other-project"
    assert channel.sent_messages[4].text == (
        f"Memory archived\nid: {atom.memory_id}\nscope: project:aico"
    )
    assert channel.sent_messages[5].text == (
        "No memories found for aico\n\nNext:\n• /remember <fact>"
    )
    assert "Phase 7 memory must be agent-driven." not in adapter.received_tasks[0].payload
    assert memory_store.list_atoms(MemoryScope.project("other"))[0].memory_id == "mem-other-project"


async def test_orchestrator_captures_boss_feedback_for_active_project(
    tmp_path: Path,
) -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    memory_store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-project"),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        memory_store=memory_store,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/use project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="以后这个项目汇报进度一定要告诉我还剩几阶段", mentions=())
    )

    atoms = memory_store.list_atoms(MemoryScope.project("aico"))
    assert len(atoms) == 1
    assert atoms[0].source == "boss_feedback_capture"
    assert atoms[0].status is MemoryStatus.ACTIVE
    assert "以后这个项目汇报进度一定要告诉我还剩几阶段" in atoms[0].claim
    assert "Shared memory:" in adapter.received_tasks[0].payload
    assert atoms[0].memory_id in adapter.received_tasks[0].payload


async def test_orchestrator_candidate_boss_feedback_stays_out_of_prompt(
    tmp_path: Path,
) -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    memory_store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    task_ids = iter(("task-feedback", "task-next"))
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: next(task_ids)),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        memory_store=memory_store,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/use project aico", mentions=()))
    await orchestrator.handle_incoming(
        _incoming_message(text="这个项目我可能更喜欢先少写一点状态汇总", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="继续项目", mentions=()))

    atoms = memory_store.list_atoms(MemoryScope.project("aico"))
    assert len(atoms) == 1
    assert atoms[0].status is MemoryStatus.CANDIDATE
    assert "Shared memory:" not in adapter.received_tasks[1].payload


async def test_orchestrator_injects_captured_boss_global_preference(
    tmp_path: Path,
) -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    memory_store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    task_ids = iter(("task-preference", "task-progress"))
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: next(task_ids)),
        task_bus=TaskBus(adapter),
        agent_directory=_agent_directory(),
        project_directory=_project_directory(),
        memory_store=memory_store,
    )

    await orchestrator.handle_incoming(
        _incoming_message(text="我更喜欢汇报进度时告诉我还有几阶段", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="/use project aico", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="汇报进度", mentions=()))

    atoms = memory_store.list_atoms(MemoryScope.boss("user-1"))
    assert len(atoms) == 1
    assert atoms[0].status is MemoryStatus.ACTIVE
    assert atoms[0].memory_id in adapter.received_tasks[1].payload
    assert "scope: boss:user-1" in adapter.received_tasks[1].payload


async def test_orchestrator_routes_skills_command_to_provider_owned_introspection() -> None:
    adapter = ScriptedAdapter(name="claude-code")
    channel = RecordingChannel()
    directory = AgentDirectory(
        (
            AgentCard(
                name="implementer",
                adapter_name="claude-code",
                provider_name="claude-code",
                role_description="Role: implementer.",
                aliases=("claude",),
            ),
        )
    )
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-skills"),
        task_bus=TaskBus(adapter),
        agent_directory=directory,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/skills claude", mentions=()))

    assert adapter.received_tasks[0].target_persona == "implementer"
    assert "List the skills currently available" in adapter.received_tasks[0].payload
    assert channel.sent_messages[0] == MessageContent(
        text="Task accepted: task-skills [implementer]"
    )


async def test_orchestrator_attaches_provider_session_to_active_session_tasks() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    store = InMemoryAgentSessionStore(session_id_factory=lambda: "abcdef12-3456")
    task_ids = iter(("task-first", "task-next"))
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: next(task_ids)),
        task_bus=TaskBus(adapter),
        session_store=store,
        provider_session_factory=lambda session: ProviderSessionRef(
            provider_name="claude-code",
            session_id=session.session_id,
        ),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/new claude", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/use abcdef12", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="first", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="next", mentions=()))

    first_session = provider_session_from_task(adapter.received_tasks[0])
    next_session = provider_session_from_task(adapter.received_tasks[1])
    stored_session = store.get("abcdef12-3456")
    assert first_session is not None
    assert first_session.mode is ProviderSessionMode.NEW
    assert next_session is not None
    assert next_session.mode is ProviderSessionMode.RESUME
    assert stored_session is not None
    assert stored_session.provider_ref is not None
    assert stored_session.provider_ref.initialized


async def test_orchestrator_binds_provider_session_for_agent_and_resumes_plain_messages() -> None:
    adapter = ScriptedAdapter(name="codex")
    channel = RecordingChannel()
    store = InMemoryAgentSessionStore(session_id_factory=lambda: "abcdef12-3456")
    directory = AgentDirectory(
        (
            AgentCard(
                name="reviewer",
                adapter_name="codex",
                provider_name="codex",
                role_description="Role: reviewer.",
                aliases=("codex",),
            ),
        )
    )
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-codex"),
        task_bus=TaskBus(adapter),
        session_store=store,
        agent_directory=directory,
    )

    await orchestrator.handle_incoming(
        _incoming_message(text="/bind codex provider-123", mentions=())
    )
    await orchestrator.handle_incoming(_incoming_message(text="continue review", mentions=()))

    provider_session = provider_session_from_task(adapter.received_tasks[0])
    assert channel.sent_messages[0].text.startswith("Provider session bound: abcdef12 [reviewer]")
    assert adapter.received_tasks[0].target_persona == "reviewer"
    assert provider_session is not None
    assert provider_session.provider_name == "codex"
    assert provider_session.session_id == "provider-123"
    assert provider_session.mode is ProviderSessionMode.RESUME


async def test_orchestrator_keeps_explicit_route_over_active_session() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    store = InMemoryAgentSessionStore(session_id_factory=lambda: "abcdef12-3456")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-session"),
        task_bus=TaskBus(adapter),
        session_store=store,
    )

    await orchestrator.handle_incoming(_incoming_message(text="/new claude", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/use abcdef12", mentions=()))
    await orchestrator.handle_incoming(_incoming_message(text="/codex inspect", mentions=()))

    assert adapter.received_tasks[0].target_persona == "codex"
    assert adapter.received_tasks[0].payload == "inspect"


async def test_orchestrator_reports_new_session_usage_for_invalid_agent_name() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-session"),
        task_bus=TaskBus(adapter),
    )

    await orchestrator.handle_incoming(_incoming_message(text="/new claude extra", mentions=()))

    assert channel.sent_messages == [MessageContent(text="Usage: /new <agent>")]
    assert adapter.received_tasks == []


def _agent_directory() -> AgentDirectory:
    return AgentDirectory(
        (
            AgentCard(
                name="implementer",
                adapter_name="claude-code",
                provider_name="claude-code",
                role_description="Role: implementer.",
                aliases=("claude",),
            ),
        )
    )


def _project_directory() -> ProjectAssignmentDirectory:
    return ProjectAssignmentDirectory(
        ProjectAssignmentConfig(
            agents={
                "claude": CompanyAgentProfile(
                    id="claude",
                    provider="claude-code",
                    title="Senior Implementer",
                )
            },
            roles={
                "implementer": RoleProfile(
                    id="implementer",
                    title="Implementation Lead",
                    default_permissions=("code", "tests", "docs"),
                ),
                "tester": RoleProfile(
                    id="tester",
                    title="Test Lead",
                    default_permissions=("code", "tests"),
                ),
                "challenger": RoleProfile(
                    id="challenger",
                    title="Critical Philosopher",
                    default_permissions=("docs", "audit"),
                ),
            },
            projects={
                "aico": ProjectProfile(
                    id="aico",
                    name="AI Company OS",
                    repo="/repo/aico",
                    current_phase="Phase 5",
                    default_role="implementer",
                    default_assignment="aico-implementer",
                    roles={
                        "implementer": ProjectRoleProfile(role="implementer"),
                        "tester": ProjectRoleProfile(role="tester"),
                        "challenger": ProjectRoleProfile(role="challenger"),
                    },
                )
            },
            assignments=(
                AssignmentProfile(
                    project="aico",
                    agent="claude",
                    role="implementer",
                    seat="aico-implementer",
                    permissions=("code", "tests", "docs"),
                ),
                AssignmentProfile(
                    project="aico",
                    agent="claude",
                    role="challenger",
                    seat="aico-challenger",
                    permissions=("docs", "audit"),
                ),
            ),
        )
    )


def _project_directory_with_reviewer() -> ProjectAssignmentDirectory:
    config = _project_directory()._config  # noqa: SLF001
    project = config.projects["aico"]
    return ProjectAssignmentDirectory(
        config.model_copy(
            update={
                "roles": {
                    **config.roles,
                    "reviewer": RoleProfile(
                        id="reviewer",
                        title="Code Reviewer",
                        default_permissions=("docs", "audit"),
                    ),
                },
                "projects": {
                    **config.projects,
                    "aico": project.model_copy(
                        update={
                            "roles": {
                                **project.roles,
                                "reviewer": ProjectRoleProfile(role="reviewer"),
                            }
                        }
                    ),
                },
                "assignments": (
                    *config.assignments,
                    AssignmentProfile(
                        project="aico",
                        agent="claude",
                        role="reviewer",
                        seat="aico-reviewer",
                        permissions=("docs", "audit"),
                    ),
                ),
            }
        )
    )


def _project_directory_with_tester() -> ProjectAssignmentDirectory:
    config = _project_directory()._config  # noqa: SLF001
    return ProjectAssignmentDirectory(
        config.model_copy(
            update={
                "assignments": (
                    *config.assignments,
                    AssignmentProfile(
                        project="aico",
                        agent="claude",
                        role="tester",
                        seat="aico-tester",
                        permissions=("code", "tests"),
                    ),
                ),
            }
        )
    )


def _project_directory_with_risky_role_prompt() -> ProjectAssignmentDirectory:
    config = _project_directory()._config  # noqa: SLF001
    return ProjectAssignmentDirectory(
        config.model_copy(
            update={
                "roles": {
                    **config.roles,
                    "implementer": RoleProfile(
                        id="implementer",
                        title="Implementation Lead",
                        summary="Write code, run tests, update docs, and keep handoffs current.",
                        default_permissions=("code", "tests", "docs"),
                    ),
                }
            }
        )
    )


def _append_memory(
    store: JsonlMemoryStore,
    memory_id: str,
    claim: str,
    *,
    purpose_tags: tuple[MemoryPurpose, ...],
) -> None:
    store.append_atom(
        MemoryAtom(
            memory_id=memory_id,
            claim=claim,
            evidence=(
                MemoryEvidence(
                    ref=f"audit:{memory_id}",
                    source="test",
                    captured_at=datetime(2026, 5, 15, tzinfo=UTC),
                ),
            ),
            scope=MemoryScope.project("aico"),
            source="test",
            confidence=0.92,
            created_by="tester",
            tags=("release",),
            purpose_tags=purpose_tags,
        )
    )


def _metadata_value(task: Task, key: str) -> str | None:
    for entry in task.metadata:
        if entry.key == key:
            return str(entry.value)
    return None


def _project_task(
    task_id: str,
    *,
    target_persona: str,
    payload: str,
    metadata: tuple[MetadataEntry, ...] = (),
) -> Task:
    return Task(
        task_id=task_id,
        payload=payload,
        requester_id="user-1",
        target_persona=target_persona,
        metadata=(
            MetadataEntry(key="aico.project_id", value="aico"),
            MetadataEntry(key="aico.assignment_role", value=target_persona),
            *metadata,
        ),
    )


def _incoming_message(
    text: str = "please inspect",
    sender_id: str = "user-1",
    mentions: tuple[str, ...] = ("lao-zhang",),
) -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id=sender_id,
        mentions=mentions,
        content=MessageContent(text=text),
        raw_ref="message-1",
    )
