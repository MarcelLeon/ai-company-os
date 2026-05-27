from aico.channel import IMChannel, IncomingMessageHandler
from aico.core.models import (
    ChannelTarget,
    HealthStatus,
    MessageContent,
    MessageNativeFormat,
    SentMessage,
)
from aico.core.streaming import StreamedMessageWriter


class RecordingChannel:
    def __init__(self) -> None:
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
        self.sent_messages.append(content)
        return SentMessage(message_id="message-new", target=target)

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
        _ = handler

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


async def test_streamed_writer_keeps_status_out_of_native_final_output() -> None:
    channel = RecordingChannel()
    target = ChannelTarget(channel_name="telegram", target_id="chat-1")
    writer = StreamedMessageWriter(
        channel,
        target,
        SentMessage(message_id="message-1", target=target),
        preferred_format=MessageNativeFormat.TELEGRAM_HTML,
    )

    await writer.show_status(
        "Still running: no adapter output for 120s. "
        "Use /task <id> for details or /interrupt <id> to stop."
    )
    await writer.append("<b>1. verdict:</b> pass")

    assert isinstance(channel, IMChannel)
    assert channel.edited_messages[0].text.startswith("Still running")
    assert channel.edited_messages[0].native_format is None
    assert channel.edited_messages[-1] == MessageContent(
        text="<b>1. verdict:</b> pass",
        native_format=MessageNativeFormat.TELEGRAM_HTML,
    )


async def test_streamed_writer_ignores_late_status_after_output_started() -> None:
    channel = RecordingChannel()
    target = ChannelTarget(channel_name="telegram", target_id="chat-1")
    writer = StreamedMessageWriter(
        channel,
        target,
        SentMessage(message_id="message-1", target=target),
    )

    await writer.append("partial")
    await writer.show_status("Still running: no adapter output for 120s.")

    assert [message.text for message in channel.edited_messages] == ["partial"]
