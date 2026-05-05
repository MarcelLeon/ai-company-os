"""Helpers for streaming long text back through IM channels."""

from __future__ import annotations

import logging

from aico.channel import IMChannel
from aico.core.models import ChannelTarget, MessageContent, SentMessage

STREAM_MESSAGE_TEXT_LIMIT = 3900
log = logging.getLogger(__name__)


class StreamedMessageWriter:
    """Keep streamed text under conservative IM message length limits."""

    def __init__(
        self,
        channel: IMChannel,
        target: ChannelTarget,
        sent_message: SentMessage,
        *,
        max_text_length: int = STREAM_MESSAGE_TEXT_LIMIT,
    ) -> None:
        if max_text_length <= 0:
            raise ValueError("max_text_length must be positive")
        self._channel = channel
        self._target = target
        self._sent_message = sent_message
        self._max_text_length = max_text_length
        self._current_text = ""

    async def append(self, text: str) -> None:
        remaining = text
        while remaining:
            available = self._max_text_length - len(self._current_text)
            if available <= 0:
                log.info(
                    "Stream message split: target=%s next_chars=%s",
                    self._target.target_id,
                    min(len(remaining), self._max_text_length),
                )
                await self._send_next_message(remaining[: self._max_text_length])
                remaining = remaining[self._max_text_length :]
                continue

            self._current_text += remaining[:available]
            remaining = remaining[available:]
            await self._edit_current_message()

    async def _edit_current_message(self) -> None:
        await self._channel.edit_message(
            self._target,
            self._sent_message.message_id,
            MessageContent(text=self._current_text),
        )

    async def _send_next_message(self, text: str) -> None:
        self._current_text = text
        self._sent_message = await self._channel.send_message(
            self._target,
            MessageContent(text=text),
        )
