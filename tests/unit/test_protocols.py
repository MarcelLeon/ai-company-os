from collections.abc import AsyncIterator

from aico.adapter import AIAdapter
from aico.channel import IMChannel, IncomingMessageHandler
from aico.core import (
    AckStatus,
    AdapterStatus,
    Capability,
    ChannelTarget,
    HealthStatus,
    MessageContent,
    OutputType,
    SentMessage,
    Task,
    TaskAck,
    TaskOutput,
)


class FakeAdapter:
    @property
    def name(self) -> str:
        return "fake"

    def capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.CODE_EDIT, Capability.STREAM_OUTPUT})

    async def receive_task(self, task: Task) -> TaskAck:
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    async def _outputs(self, task_id: str) -> AsyncIterator[TaskOutput]:
        yield TaskOutput(task_id=task_id, sequence=0, type=OutputType.TEXT, content="done")

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        return self._outputs(task_id)

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        _ = task_id

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


class FakeChannel:
    def __init__(self) -> None:
        self.handler: IncomingMessageHandler | None = None

    @property
    def name(self) -> str:
        return "fake-channel"

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> SentMessage:
        _ = content
        return SentMessage(message_id="message-1", target=target)

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> None:
        _ = (target, message_id, content)

    async def delete_message(self, target: ChannelTarget, message_id: str) -> None:
        _ = (target, message_id)

    def on_incoming(self, handler: IncomingMessageHandler) -> None:
        self.handler = handler

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


async def test_fake_adapter_satisfies_ai_adapter_protocol() -> None:
    adapter = FakeAdapter()
    task = Task(
        task_id="task-1",
        payload="Do work",
        requester_id="user-1",
        target_persona="lao-zhang",
    )

    assert isinstance(adapter, AIAdapter)
    assert await adapter.receive_task(task) == TaskAck(
        task_id="task-1",
        status=AckStatus.ACCEPTED,
    )
    outputs = [output async for output in adapter.stream_output("task-1")]

    assert len(outputs) == 1
    assert outputs[0].model_dump(exclude={"timestamp"}) == TaskOutput(
        task_id="task-1",
        sequence=0,
        type=OutputType.TEXT,
        content="done",
    ).model_dump(exclude={"timestamp"})


async def test_fake_channel_satisfies_im_channel_protocol() -> None:
    channel = FakeChannel()
    target = ChannelTarget(channel_name="telegram", target_id="chat-1")

    assert isinstance(channel, IMChannel)
    sent_message = await channel.send_message(target, MessageContent(text="hello"))

    assert sent_message.model_dump(exclude={"timestamp"}) == SentMessage(
        message_id="message-1",
        target=target,
    ).model_dump(exclude={"timestamp"})
