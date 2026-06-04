"""Telegram text channel implementation for the Phase 1 MVP."""

from __future__ import annotations

import asyncio
import html
import logging
from typing import Any

import httpx

from aico.channel.base import IncomingMessageHandler
from aico.core.models import (
    ChannelTarget,
    HealthStatus,
    IncomingMessage,
    MessageContent,
    MessageNativeFormat,
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
        self._handler_tasks: set[asyncio.Task[None]] = set()
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

        for task in tuple(self._handler_tasks):
            task.cancel()
        if self._handler_tasks:
            await asyncio.gather(*self._handler_tasks, return_exceptions=True)
            self._handler_tasks.clear()

        if self._owns_client:
            await self._client.aclose()

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> SentMessage:
        log.info(
            "Telegram sendMessage: target=%s text_chars=%s",
            target.target_id,
            len(content.text),
        )
        result = await self._post(
            "sendMessage",
            _telegram_text_payload(target, content),
        )
        return SentMessage(message_id=str(result["message_id"]), target=target)

    async def send_document(
        self,
        target: ChannelTarget,
        *,
        filename: str,
        content: bytes,
        media_type: str,
        caption: str | None = None,
    ) -> SentMessage:
        log.info(
            "Telegram sendDocument: target=%s filename=%s bytes=%s",
            target.target_id,
            filename,
            len(content),
        )
        payload: dict[str, Any] = {"chat_id": target.target_id}
        if caption:
            payload["caption"] = caption
        files = {"document": (filename, content, media_type)}
        result = await self._post_multipart("sendDocument", payload, files)
        return SentMessage(message_id=str(result["message_id"]), target=target)

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> None:
        log.info(
            "Telegram editMessageText: target=%s message_id=%s text_chars=%s",
            target.target_id,
            message_id,
            len(content.text),
        )
        try:
            payload = _telegram_text_payload(target, content)
            payload = {
                "chat_id": payload.pop("chat_id"),
                "message_id": message_id,
                **payload,
            }
            await self._post(
                "editMessageText",
                payload,
            )
        except TelegramAPIError as exc:
            if _is_noop_edit_error(exc):
                log.info(
                    "Telegram editMessageText ignored no-op: target=%s message_id=%s",
                    target.target_id,
                    message_id,
                )
                return
            raise

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
                log.info(
                    "Telegram incoming text: update_id=%s raw_ref=%s sender=%s chars=%s",
                    update_id,
                    message.raw_ref,
                    message.sender_id,
                    len(message.content.text),
                )
                self._schedule_handler(message)
                callback_query_id = _callback_query_id(update)
                if callback_query_id is not None:
                    await self._post(
                        "answerCallbackQuery",
                        {"callback_query_id": callback_query_id},
                    )

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
        data = _telegram_response_json(response)
        if not data.get("ok"):
            description = data.get("description", "unknown Telegram API error")
            raise TelegramAPIError(str(description))
        response.raise_for_status()
        return data["result"]

    async def _post_multipart(
        self,
        method: str,
        payload: dict[str, Any],
        files: dict[str, tuple[str, bytes, str]],
    ) -> Any:
        response = await self._client.post(
            self._method_url(method),
            data=payload,
            files=files,
        )
        data = _telegram_response_json(response)
        if not data.get("ok"):
            description = data.get("description", "unknown Telegram API error")
            raise TelegramAPIError(str(description))
        response.raise_for_status()
        return data["result"]

    def _method_url(self, method: str) -> str:
        return f"{self._api_base_url}/bot{self._bot_token}/{method}"

    def _schedule_handler(self, message: IncomingMessage) -> None:
        if self._handler is None:
            return

        task = asyncio.create_task(self._dispatch_message(message))
        log.info("Telegram handler scheduled: raw_ref=%s", message.raw_ref)
        self._handler_tasks.add(task)
        task.add_done_callback(self._handler_tasks.discard)

    async def _dispatch_message(self, message: IncomingMessage) -> None:
        if self._handler is None:
            return
        try:
            log.info("Telegram handler started: raw_ref=%s", message.raw_ref)
            await self._handler(message)
            log.info("Telegram handler finished: raw_ref=%s", message.raw_ref)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Telegram incoming message handler failed: raw_ref=%s", message.raw_ref)


def _to_incoming_message(channel_name: str, update: dict[str, Any]) -> IncomingMessage | None:
    callback_message = _to_callback_message(channel_name, update)
    if callback_message is not None:
        return callback_message

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


def _to_callback_message(channel_name: str, update: dict[str, Any]) -> IncomingMessage | None:
    callback = update.get("callback_query")
    if not isinstance(callback, dict):
        return None

    data = callback.get("data")
    message = callback.get("message")
    if not isinstance(data, str) or not data:
        return None
    if not isinstance(message, dict):
        return None

    chat = message["chat"]
    sender = callback.get("from", {})
    target = ChannelTarget(
        channel_name=channel_name,
        target_id=str(chat["id"]),
        thread_id=_optional_str(message.get("message_thread_id")),
    )
    return IncomingMessage(
        channel_name=channel_name,
        source=target,
        sender_id=str(sender.get("id", "unknown")),
        content=MessageContent(text=data),
        raw_ref=str(callback["id"]),
    )


def _callback_query_id(update: dict[str, Any]) -> str | None:
    callback = update.get("callback_query")
    if not isinstance(callback, dict):
        return None
    callback_id = callback.get("id")
    if not isinstance(callback_id, str) or not callback_id:
        return None
    return callback_id


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


def _telegram_response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        response.raise_for_status()
        raise TelegramAPIError("invalid Telegram API response") from None
    if not isinstance(data, dict):
        raise TelegramAPIError("invalid Telegram API response")
    return data


def _is_noop_edit_error(exc: TelegramAPIError) -> bool:
    return "message is not modified" in str(exc).lower()


def _telegram_text_payload(target: ChannelTarget, content: MessageContent) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "chat_id": target.target_id,
        "text": content.text,
    }
    if content.native_format is MessageNativeFormat.TELEGRAM_HTML:
        payload["parse_mode"] = "HTML"
    elif content.spans:
        payload["text"] = _html_text(content)
        payload["parse_mode"] = "HTML"
    if content.actions:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {"text": action.label, "callback_data": action.value}
                    for action in content.actions
                ]
            ]
        }
    return payload


def _html_text(content: MessageContent) -> str:
    parts: list[str] = []
    cursor = 0
    text = content.text
    for span in sorted(content.spans, key=lambda item: item.offset):
        start = span.offset
        end = min(span.offset + span.length, len(text))
        if start < cursor or start >= len(text) or end <= start:
            continue
        parts.append(html.escape(text[cursor:start], quote=False))
        parts.append(_html_tag(span.style.value, html.escape(text[start:end], quote=False)))
        cursor = end
    parts.append(html.escape(text[cursor:], quote=False))
    return "".join(parts)


def _html_tag(style: str, text: str) -> str:
    tags = {
        "bold": "b",
        "italic": "i",
        "code": "code",
    }
    tag = tags.get(style)
    if tag is None:
        return text
    return f"<{tag}>{text}</{tag}>"
