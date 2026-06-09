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


async def test_streamed_writer_keeps_glued_agent_sections_readable() -> None:
    channel = RecordingChannel()
    target = ChannelTarget(channel_name="telegram", target_id="chat-1")
    writer = StreamedMessageWriter(
        channel,
        target,
        SentMessage(message_id="message-1", target=target),
        preferred_format=MessageNativeFormat.TELEGRAM_HTML,
    )

    await writer.append('<b>Goal received</b>"prepare launch"')
    await writer.append("<b>Decision</b>Ship docs only.。")
    await writer.append("• High — Quickstart promise needs tightening.")

    assert channel.edited_messages[-1] == MessageContent(
        text=(
            "<b>Goal received</b>\n"
            '"prepare launch"\n'
            "<b>Decision</b>\n"
            "Ship docs only.。\n\n"
            "• High — Quickstart promise needs tightening."
        ),
        native_format=MessageNativeFormat.TELEGRAM_HTML,
    )


async def test_streamed_writer_splits_long_output_at_readable_boundary() -> None:
    channel = RecordingChannel()
    target = ChannelTarget(channel_name="telegram", target_id="chat-1")
    writer = StreamedMessageWriter(
        channel,
        target,
        SentMessage(message_id="message-1", target=target),
        max_text_length=120,
    )

    await writer.append(
        "Review summary. "
        "• High — workspace is dirty before tagging and should be resolved first. "
        "Details include several changed files and status docs. "
        "• Medium — release notes need a final consistency pass."
    )

    assert len(channel.edited_messages[-1].text) <= 120
    assert channel.sent_messages
    assert all(len(message.text) <= 120 for message in channel.sent_messages)
    assert "\n\n• High" in channel.edited_messages[-1].text
    assert any("• Medium" in message.text for message in channel.sent_messages)
