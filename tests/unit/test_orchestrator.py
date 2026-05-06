from collections.abc import AsyncIterator

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
    MessageContent,
    MessageRouter,
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
    assert channel.sent_messages == [MessageContent(text="scripted: idle")]
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

    assert channel.sent_messages[-1] == MessageContent(
        text="scripted: idle\n\nRecent tasks:\ntask-4 [scripted]: done"
    )


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
    assert channel.sent_messages[-1] == MessageContent(
        text=("Recent tasks:\ntask-4 [scripted]: done\n\nUse /task <task_id> for details.")
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
    assert "Actions:\n- /approve task-app\n- /reject task-app" in detail
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
    assert "- task_submitted\n" in audit_text
    assert "  task: task-audit\n" in audit_text
    assert "  actor: user-1\n" in audit_text
    assert "  target: lao-zhang\n" in audit_text
    assert "- approval_requested\n" in audit_text
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
    assert (
        MessageContent(text="Collaboration requested: implementer -> reviewer")
        in channel.sent_messages
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
    assert "Collaboration:\n- requested by: implementer\n" in child_detail
    assert "- parent: task-par (/task task-par)" in child_detail

    await orchestrator.handle_incoming(_incoming_message(text="/task task-parent"))
    parent_detail = channel.sent_messages[-1].text
    assert "Collaboration:\n- children:\n  - task-chi -> reviewer (/task task-chi)" in parent_detail


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

    assert channel.sent_messages[0] == MessageContent(
        text="Agents:\n- implementer -> claude-code (idle)"
    )
    assert channel.sent_messages[1].text.startswith("Agent: implementer\n")
    assert "provider: claude-code\n" in channel.sent_messages[1].text
    assert "skills: provider_cli via /skills implementer" in channel.sent_messages[1].text
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
    assert roles.startswith("Roles for aico [AI Company OS]:\n")
    assert "• implementer: Implementation Lead -> claude" in roles
    assert "• tester: Test Lead -> unappointed" in roles
    assert "permissions:" in roles


async def test_orchestrator_proposes_and_confirms_project_role() -> None:
    adapter = ScriptedAdapter(
        name="claude-code",
        output_texts=(
            """
            {
              "id": "growth-analyst",
              "title": "Growth Analyst",
              "summary": "Analyze activation and retention opportunities.",
              "default_permissions": ["read_docs", "read_audit"],
              "approval_required": ["write_docs"],
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
    assert "• growth-analyst: Growth Analyst -> unappointed" in roles
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
    assert "• tester: Test Lead -> unappointed" in roles
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
    assert any("• tester: Test Lead -> unappointed" in text for text in sent_texts)
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
                "implementer": RoleProfile(id="implementer", title="Implementation Lead"),
                "tester": RoleProfile(id="tester", title="Test Lead"),
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
                    },
                )
            },
            assignments=(
                AssignmentProfile(
                    project="aico",
                    agent="claude",
                    role="implementer",
                    seat="aico-implementer",
                ),
            ),
        )
    )


def _metadata_value(task: Task, key: str) -> str | None:
    for entry in task.metadata:
        if entry.key == key:
            return str(entry.value)
    return None


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
