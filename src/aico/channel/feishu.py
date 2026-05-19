"""Feishu/Lark text channel implementation."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
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


class FeishuAPIError(RuntimeError):
    """Raised when Feishu Open Platform returns an unsuccessful response."""


class FeishuChannel:
    """Feishu custom app channel for text messages and event callbacks."""

    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        verification_token: str | None = None,
        api_base_url: str = "https://open.feishu.cn",
        event_dedupe_ttl_seconds: float = 8 * 60 * 60,
        event_dedupe_max_entries: int = 4096,
        client: httpx.AsyncClient | None = None,
        name: str = "feishu",
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not app_id:
            raise ValueError("app_id must not be empty")
        if not app_secret:
            raise ValueError("app_secret must not be empty")
        if event_dedupe_ttl_seconds <= 0:
            raise ValueError("event_dedupe_ttl_seconds must be positive")
        if event_dedupe_max_entries <= 0:
            raise ValueError("event_dedupe_max_entries must be positive")
        self._name = name
        self._app_id = app_id
        self._app_secret = app_secret
        self._verification_token = verification_token
        self._api_base_url = api_base_url.rstrip("/")
        self._event_dedupe_ttl_seconds = event_dedupe_ttl_seconds
        self._event_dedupe_max_entries = event_dedupe_max_entries
        self._seen_event_ids: dict[str, float] = {}
        self._clock = clock
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._handler: IncomingMessageHandler | None = None
        self._handler_tasks: set[asyncio.Task[None]] = set()
        self._tenant_access_token: str | None = None

    @property
    def name(self) -> str:
        return self._name

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        for task in tuple(self._handler_tasks):
            task.cancel()
        if self._handler_tasks:
            await asyncio.gather(*self._handler_tasks, return_exceptions=True)
            self._handler_tasks.clear()
        if self._owns_client:
            await self._client.aclose()

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> SentMessage:
        token = await self._access_token()
        response = await self._client.post(
            f"{self._api_base_url}/open-apis/im/v1/messages",
            params={"receive_id_type": "chat_id"},
            headers=_auth_headers(token),
            json={
                "receive_id": target.target_id,
                "msg_type": "text",
                "content": json.dumps({"text": _plain_text(content)}, ensure_ascii=False),
            },
        )
        data = _feishu_response_json(response)
        message_id = data.get("data", {}).get("message_id")
        if not isinstance(message_id, str) or not message_id:
            raise FeishuAPIError("missing Feishu message_id")
        return SentMessage(message_id=message_id, target=target)

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> None:
        token = await self._access_token()
        response = await self._client.patch(
            f"{self._api_base_url}/open-apis/im/v1/messages/{message_id}",
            headers=_auth_headers(token),
            json={
                "msg_type": "text",
                "content": json.dumps({"text": _plain_text(content)}, ensure_ascii=False),
            },
        )
        _feishu_response_json(response)

    async def delete_message(self, target: ChannelTarget, message_id: str) -> None:
        token = await self._access_token()
        response = await self._client.delete(
            f"{self._api_base_url}/open-apis/im/v1/messages/{message_id}",
            headers=_auth_headers(token),
        )
        _feishu_response_json(response)

    def on_incoming(self, handler: IncomingMessageHandler) -> None:
        self._handler = handler

    async def health_check(self) -> HealthStatus:
        try:
            await self._access_token()
        except (httpx.HTTPError, FeishuAPIError, KeyError):
            return HealthStatus.FAILED
        return HealthStatus.OK

    async def handle_event(self, payload: dict[str, Any]) -> dict[str, str] | None:
        """Handle one Feishu event callback payload.

        Deployment code can call this from a FastAPI route. URL verification returns
        the challenge response body; normal message events are dispatched to the
        registered incoming handler.
        """

        challenge = _challenge_response(payload, self._verification_token)
        if challenge is not None:
            return challenge

        if not _token_matches(payload, self._verification_token):
            raise FeishuAPIError("invalid Feishu verification token")
        message = _to_incoming_message(self._name, payload)
        if message is not None and self._handler is not None:
            if self._is_duplicate_event(payload):
                log.info("Feishu duplicate event skipped: raw_ref=%s", message.raw_ref)
                return None
            self._schedule_handler(message)
        return None

    async def _access_token(self) -> str:
        if self._tenant_access_token is not None:
            return self._tenant_access_token

        response = await self._client.post(
            f"{self._api_base_url}/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": self._app_id, "app_secret": self._app_secret},
        )
        data = _feishu_response_json(response)
        token = data.get("tenant_access_token")
        if not isinstance(token, str) or not token:
            raise FeishuAPIError("missing tenant_access_token")
        self._tenant_access_token = token
        return token

    def _schedule_handler(self, message: IncomingMessage) -> None:
        if self._handler is None:
            return
        task = asyncio.create_task(self._dispatch_message(message))
        self._handler_tasks.add(task)
        task.add_done_callback(self._handler_tasks.discard)

    async def _dispatch_message(self, message: IncomingMessage) -> None:
        if self._handler is None:
            return
        try:
            await self._handler(message)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Feishu incoming message handler failed: raw_ref=%s", message.raw_ref)

    def _is_duplicate_event(self, payload: dict[str, Any]) -> bool:
        event_id = _event_unique_id(payload)
        if event_id is None:
            return False
        now = self._clock()
        self._prune_seen_event_ids(now)
        if event_id in self._seen_event_ids:
            return True
        self._seen_event_ids[event_id] = now
        return False

    def _prune_seen_event_ids(self, now: float) -> None:
        expires_before = now - self._event_dedupe_ttl_seconds
        expired_ids = [
            event_id
            for event_id, seen_at in self._seen_event_ids.items()
            if seen_at < expires_before
        ]
        for event_id in expired_ids:
            del self._seen_event_ids[event_id]
        overflow = len(self._seen_event_ids) - self._event_dedupe_max_entries
        if overflow <= 0:
            return
        oldest_ids = sorted(
            self._seen_event_ids,
            key=self._seen_event_ids.__getitem__,
        )[:overflow]
        for event_id in oldest_ids:
            del self._seen_event_ids[event_id]


def _challenge_response(
    payload: dict[str, Any],
    verification_token: str | None,
) -> dict[str, str] | None:
    if payload.get("type") != "url_verification":
        return None
    if not _token_matches(payload, verification_token):
        raise FeishuAPIError("invalid Feishu verification token")
    challenge = payload.get("challenge")
    if not isinstance(challenge, str) or not challenge:
        raise FeishuAPIError("missing Feishu challenge")
    return {"challenge": challenge}


def _token_matches(payload: dict[str, Any], verification_token: str | None) -> bool:
    if verification_token is None:
        return True
    token = payload.get("token")
    if token is None:
        header = payload.get("header", {})
        token = header.get("token") if isinstance(header, dict) else None
    return token == verification_token


def _to_incoming_message(channel_name: str, payload: dict[str, Any]) -> IncomingMessage | None:
    header = payload.get("header", {})
    if header.get("event_type") != "im.message.receive_v1":
        return None
    event = payload.get("event", {})
    raw_message = event.get("message", {})
    text = _event_text(raw_message)
    if not text:
        return None
    chat_id = raw_message.get("chat_id")
    message_id = raw_message.get("message_id")
    if not isinstance(chat_id, str) or not isinstance(message_id, str):
        return None
    sender_id = _sender_id(event.get("sender", {}))
    return IncomingMessage(
        channel_name=channel_name,
        source=ChannelTarget(channel_name=channel_name, target_id=chat_id),
        sender_id=sender_id,
        mentions=_mentions(raw_message),
        content=MessageContent(text=text),
        raw_ref=message_id,
    )


def _event_unique_id(payload: dict[str, Any]) -> str | None:
    header = payload.get("header", {})
    if isinstance(header, dict):
        event_id = header.get("event_id")
        if isinstance(event_id, str) and event_id:
            return event_id
    uuid = payload.get("uuid")
    return uuid if isinstance(uuid, str) and uuid else None


def _event_text(message: dict[str, Any]) -> str | None:
    if message.get("message_type") != "text":
        return None
    content = message.get("content")
    if not isinstance(content, str):
        return None
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError:
        return None
    text = decoded.get("text")
    return text if isinstance(text, str) and text else None


def _sender_id(sender: dict[str, Any]) -> str:
    sender_id = sender.get("sender_id", {})
    for key in ("open_id", "union_id", "user_id"):
        value = sender_id.get(key)
        if isinstance(value, str) and value:
            return value
    return "unknown"


def _mentions(message: dict[str, Any]) -> tuple[str, ...]:
    mentions = message.get("mentions", [])
    if not isinstance(mentions, list):
        return ()
    names: list[str] = []
    for mention in mentions:
        if not isinstance(mention, dict):
            continue
        name = mention.get("name") or mention.get("key")
        if isinstance(name, str) and name:
            names.append(name.lstrip("@"))
    return tuple(names)


def _plain_text(content: MessageContent) -> str:
    if not content.actions:
        return content.text
    actions = " ".join(f"[{action.label}: {action.value}]" for action in content.actions)
    return f"{content.text}\n{actions}"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _feishu_response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        response.raise_for_status()
        raise FeishuAPIError("invalid Feishu API response") from None
    if not isinstance(data, dict):
        raise FeishuAPIError("invalid Feishu API response")
    code = data.get("code", 0)
    if code != 0:
        raise FeishuAPIError(str(data.get("msg", "unknown Feishu API error")))
    response.raise_for_status()
    return data
