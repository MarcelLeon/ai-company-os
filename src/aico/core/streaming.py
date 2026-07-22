"""Helpers for streaming long text back through IM channels."""

from __future__ import annotations

import logging
import re

from aico.channel import IMChannel
from aico.core.message_rendering import rich_text_message
from aico.core.models import ChannelTarget, MessageNativeFormat, SentMessage
from aico.core.native_output import agent_output_message, normalize_agent_output_for_im

STREAM_MESSAGE_TEXT_LIMIT = 1400
_TINY_TAIL_LIMIT = 80
_SEMANTIC_CARD_HEADINGS = frozenset(
    {
        "acceptance",
        "decision",
        "done",
        "evidence",
        "findings",
        "missing tests",
        "next",
        "next actions",
        "recommendation",
        "risks",
        "status",
        "summary",
        "verdict",
        "why",
    }
)
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
        preferred_format: MessageNativeFormat | None = None,
    ) -> None:
        if max_text_length <= 0:
            raise ValueError("max_text_length must be positive")
        self._channel = channel
        self._target = target
        self._sent_message = sent_message
        self._max_text_length = max_text_length
        self._current_text = ""
        self._preferred_format = preferred_format

    async def append(self, text: str) -> None:
        if not text:
            return
        segments = _readable_segments(
            normalize_agent_output_for_im(f"{self._current_text}{text}"),
            self._max_text_length,
        )
        if not segments:
            return

        self._current_text = segments[0]
        await self._edit_current_message()
        for segment in segments[1:]:
            log.info(
                "Stream message split: target=%s next_chars=%s",
                self._target.target_id,
                len(segment),
            )
            await self._send_next_message(segment)

    async def show_status(self, text: str) -> None:
        """Show a transient progress hint without adding it to final output."""

        if self._current_text:
            return
        await self._channel.edit_message(
            self._target,
            self._sent_message.message_id,
            rich_text_message(text),
        )

    async def _edit_current_message(self) -> None:
        await self._channel.edit_message(
            self._target,
            self._sent_message.message_id,
            agent_output_message(self._current_text, preferred_format=self._preferred_format),
        )

    async def _send_next_message(self, text: str) -> None:
        self._current_text = text
        self._sent_message = await self._channel.send_message(
            self._target,
            agent_output_message(text, preferred_format=self._preferred_format),
        )


def _readable_segments(text: str, max_length: int) -> tuple[str, ...]:
    if len(text) <= max_length + _TINY_TAIL_LIMIT:
        return (text,)
    semantic_cards = _semantic_cards(text)
    if len(semantic_cards) > 1:
        segments: list[str] = []
        for card in semantic_cards:
            if len(card) <= max_length + _TINY_TAIL_LIMIT:
                segments.append(card)
            else:
                segments.extend(_length_segments(card, max_length))
        return tuple(segment for segment in segments if segment)
    return _length_segments(text, max_length)


def _length_segments(text: str, max_length: int) -> tuple[str, ...]:
    remaining = text
    segments: list[str] = []
    while len(remaining) > max_length:
        split_at = _readable_split_index(remaining, max_length)
        segment = remaining[:split_at].rstrip()
        if segment:
            segments.append(segment)
        remaining = remaining[split_at:].lstrip()
    if remaining or not segments:
        segments.append(remaining)
    return tuple(segments)


def _semantic_cards(text: str) -> tuple[str, ...]:
    lines = text.splitlines()
    cards: list[str] = []
    current: list[str] = []
    for line in lines:
        if _is_semantic_card_heading(line) and _has_content(current):
            card = "\n".join(current).strip()
            if card:
                cards.append(card)
            current = [line]
            continue
        current.append(line)
    final_card = "\n".join(current).strip()
    if final_card:
        cards.append(final_card)
    return tuple(cards)


def _has_content(lines: list[str]) -> bool:
    return any(line.strip() for line in lines)


def _is_semantic_card_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    plain = re.sub(r"</?(?:b|strong)>", "", stripped, flags=re.IGNORECASE)
    plain = plain.rstrip(":").strip().casefold()
    return plain in _SEMANTIC_CARD_HEADINGS


def _readable_split_index(text: str, max_length: int) -> int:
    lower_bound = max(1, max_length // 2)
    for separator in ("\n\n", "\n"):
        index = text.rfind(separator, 0, max_length + 1)
        if index >= lower_bound:
            return index + len(separator)
    punctuation_index = max(
        text.rfind(separator, 0, max_length + 1) for separator in ("。", ". ", "；", "; ")
    )
    if punctuation_index >= lower_bound:
        return punctuation_index + 1
    space_index = text.rfind(" ", 0, max_length + 1)
    if space_index >= lower_bound:
        return space_index + 1
    return max_length
