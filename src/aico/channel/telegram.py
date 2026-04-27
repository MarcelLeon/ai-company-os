"""Telegram text channel implementation for the Phase 1 MVP."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from aico.channel.base import IncomingMessageHandler
from aico.core.models import (
    ChannelTarget,
    HealthStatus,
    IncomingMessage,
    MessageContent,
    SentMessage,
)

log = logging.getLogger(__name__)


class TelegramAPIError(RuntimeError):
    """Raised when Telegram Bot API returns an unsuccessful response."""


class TelegramChannel:
    """Long-polling Telegram channel limited to text messages."""

    def __init__(
        self,
        bot_token: str,
        *,
        api_base_url: str = "https://api.telegram.org",
        client: httpx.AsyncClient | None = None,
        poll_timeout_seconds: int = 30,
        name: str = "telegram",
    ) -> None:
        if not bot_token:
            raise ValueError("bot_token must not be empty")
        if poll_timeout_seconds <= 0:
            raise ValueError("poll_timeout_seconds must be positive")

        self._name = name
        self._api_base_url = api_base_url.rstrip("/")
        self._bot_token = bot_token
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._poll_timeout_seconds = poll_timeout_seconds
        self._handler: IncomingMessageHandler | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self._running = False
        self._offset: int | None = None

    @property
    def name(self) -> str:
        return self._name

    async def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        self._running = False
        if self._poll_task is not None:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        if self._owns_client:
            await self._client.aclose()

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> SentMessage:
        result = await self._post(
            "sendMessage",
            {
                "chat_id": target.target_id,
                "text": content.text,
            },
        )
        return SentMessage(message_id=str(result["message_id"]), target=target)

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> None:
        await self._post(
            "editMessageText",
            {
                "chat_id": target.target_id,
                "message_id": message_id,
                "text": content.text,
            },
        )

    async def delete_message(self, target: ChannelTarget, message_id: str) -> None:
        await self._post(
            "deleteMessage",
            {
                "chat_id": target.target_id,
                "message_id": message_id,
            },
        )

    def on_incoming(self, handler: IncomingMessageHandler) -> None:
        self._handler = handler

    async def health_check(self) -> HealthStatus:
        try:
            await self._post("getMe", {})
        except (httpx.HTTPError, KeyError, TelegramAPIError):
            return HealthStatus.FAILED
        return HealthStatus.OK

    async def poll_once(self) -> None:
        payload: dict[str, int] = {"timeout": self._poll_timeout_seconds}
        if self._offset is not None:
            payload["offset"] = self._offset

        result = await self._post("getUpdates", payload)
        for update in result:
            update_id = update["update_id"]
            self._offset = int(update_id) + 1
            message = _to_incoming_message(self._name, update)
            if message is not None and self._handler is not None:
                await self._handler(message)

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                raise
            except (httpx.HTTPError, KeyError, TelegramAPIError) as exc:
                log.warning("Telegram polling failed: %s", exc)
                await asyncio.sleep(1)

    async def _post(self, method: str, payload: dict[str, Any]) -> Any:
        response = await self._client.post(self._method_url(method), json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            description = data.get("description", "unknown Telegram API error")
            raise TelegramAPIError(str(description))
        return data["result"]

    def _method_url(self, method: str) -> str:
        return f"{self._api_base_url}/bot{self._bot_token}/{method}"


def _to_incoming_message(channel_name: str, update: dict[str, Any]) -> IncomingMessage | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None

    text = message.get("text")
    if not isinstance(text, str) or not text:
        return None

    chat = message["chat"]
    sender = message.get("from", {})
    target = ChannelTarget(
        channel_name=channel_name,
        target_id=str(chat["id"]),
        thread_id=_optional_str(message.get("message_thread_id")),
    )
    return IncomingMessage(
        channel_name=channel_name,
        source=target,
        sender_id=str(sender.get("id", "unknown")),
        mentions=_extract_mentions(text, message.get("entities", [])),
        content=MessageContent(text=text),
        raw_ref=str(message["message_id"]),
    )


def _extract_mentions(text: str, entities: Any) -> tuple[str, ...]:
    if not isinstance(entities, list):
        return ()

    mentions: list[str] = []
    for entity in entities:
        if not isinstance(entity, dict) or entity.get("type") != "mention":
            continue
        offset = entity.get("offset")
        length = entity.get("length")
        if not isinstance(offset, int) or not isinstance(length, int):
            continue
        mentions.append(text[offset : offset + length].lstrip("@"))
    return tuple(mentions)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
