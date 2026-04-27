from collections.abc import AsyncIterator

from aico.channel import IMChannel, IncomingMessageHandler
from aico.core import (
    AckStatus,
    AdapterRegistry,
    AdapterStatus,
    Capability,
    ChannelTarget,
    HealthStatus,
    IncomingMessage,
    MessageContent,
    MessageRouter,
    Orchestrator,
    OutputType,
    PersonaProfile,
    PersonaRegistry,
    SentMessage,
    Task,
    TaskAck,
    TaskBus,
    TaskOutput,
    TaskStatus,
)


class ScriptedAdapter:
    def __init__(
        self,
        ack_status: AckStatus = AckStatus.ACCEPTED,
        name: str = "scripted",
    ) -> None:
        self.ack_status = ack_status
        self._name = name
        self.received_tasks: list[Task] = []

    @property
    def name(self) -> str:
        return self._name

    def capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.STREAM_OUTPUT})

    async def receive_task(self, task: Task) -> TaskAck:
        self.received_tasks.append(task)
        return TaskAck(task_id=task.task_id, status=self.ack_status, reason="adapter unavailable")

    async def _outputs(self, task_id: str) -> AsyncIterator[TaskOutput]:
        yield TaskOutput(task_id=task_id, sequence=0, type=OutputType.TEXT, content="hello")
        yield TaskOutput(task_id=task_id, sequence=1, type=OutputType.TEXT, content=" world")
        yield TaskOutput(task_id=task_id, sequence=2, type=OutputType.DONE, content="")

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        return self._outputs(task_id)

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        _ = task_id

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
    assert channel.sent_messages[0].text.startswith("Approval required: task-approval")
    assert "/approve task-approval" in channel.sent_messages[0].text
    assert channel.edited_messages == []


async def test_orchestrator_approves_waiting_task_and_streams_output() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-approval"),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="run pytest"))
    await orchestrator.handle_incoming(_incoming_message(text="/approve task-approval"))

    assert adapter.received_tasks[0].payload == "run pytest"
    assert channel.sent_messages[1] == MessageContent(text="Task approved: task-approval")
    assert channel.edited_messages[-1] == MessageContent(text="hello world")
    assert bus.task_snapshots()[0].status is TaskStatus.DONE


async def test_orchestrator_rejects_waiting_task_without_streaming() -> None:
    adapter = ScriptedAdapter()
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="default", task_id_factory=lambda: "task-approval"),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming_message(text="delete generated output"))
    await orchestrator.handle_incoming(_incoming_message(text="/reject task-approval too broad"))

    assert adapter.received_tasks == []
    assert channel.sent_messages[-1] == MessageContent(text="Task rejected: too broad")
    assert channel.edited_messages == []
    assert bus.task_snapshots()[0].status is TaskStatus.REJECTED


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
    assert "/approve <task_id>" in channel.sent_messages[0].text
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


def _incoming_message(text: str = "please inspect") -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="user-1",
        mentions=("lao-zhang",),
        content=MessageContent(text=text),
        raw_ref="message-1",
    )
