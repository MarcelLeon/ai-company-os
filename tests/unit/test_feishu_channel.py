import asyncio
import json
from typing import Any, cast

import httpx

from aico.channel import FeishuAPIError, FeishuChannel, IMChannel
from aico.core import ChannelTarget, IncomingMessage, MessageAction, MessageContent


def test_feishu_channel_implements_protocol() -> None:
    channel = FeishuChannel(
        app_id="app",
        app_secret="secret",
        client=cast(httpx.AsyncClient, FakeFeishuClient()),
    )

    assert isinstance(channel, IMChannel)


async def test_feishu_send_message_uses_tenant_token_and_chat_id() -> None:
    client = FakeFeishuClient()
    channel = FeishuChannel(
        app_id="app",
        app_secret="secret",
        client=cast(httpx.AsyncClient, client),
    )
    target = ChannelTarget(channel_name="feishu", target_id="oc_chat")

    sent = await channel.send_message(
        target,
        MessageContent(
            text="Approve?",
            actions=(MessageAction(label="Approve", value="/approve task-1"),),
        ),
    )

    assert sent.message_id == "om_message"
    assert client.posts[0]["url"].endswith("/tenant_access_token/internal")
    assert client.posts[1]["params"] == {"receive_id_type": "chat_id"}
    assert client.posts[1]["headers"] == {"Authorization": "Bearer tenant-token"}
    assert client.posts[1]["json"]["receive_id"] == "oc_chat"
    content = json.loads(client.posts[1]["json"]["content"])
    assert content == {"text": "Approve?\n[Approve: /approve task-1]"}


async def test_feishu_handle_url_verification() -> None:
    channel = FeishuChannel(
        app_id="app",
        app_secret="secret",
        verification_token="verify-token",
        client=cast(httpx.AsyncClient, FakeFeishuClient()),
    )

    result = await channel.handle_event(
        {"type": "url_verification", "token": "verify-token", "challenge": "ok"}
    )

    assert result == {"challenge": "ok"}


async def test_feishu_handle_text_message_dispatches_incoming() -> None:
    channel = FeishuChannel(
        app_id="app",
        app_secret="secret",
        verification_token="verify-token",
        client=cast(httpx.AsyncClient, FakeFeishuClient()),
    )
    received: list[IncomingMessage] = []

    async def handle(message: IncomingMessage) -> None:
        received.append(message)

    channel.on_incoming(handle)
    await channel.handle_event(
        {
            "header": {
                "token": "verify-token",
                "event_type": "im.message.receive_v1",
            },
            "event": {
                "sender": {"sender_id": {"open_id": "ou_user"}},
                "message": {
                    "message_id": "om_1",
                    "chat_id": "oc_1",
                    "message_type": "text",
                    "content": json.dumps({"text": "@codex review this"}),
                    "mentions": [{"name": "codex"}],
                },
            },
        }
    )
    await asyncio.sleep(0)

    assert len(received) == 1
    assert received[0].channel_name == "feishu"
    assert received[0].source.target_id == "oc_1"
    assert received[0].sender_id == "ou_user"
    assert received[0].mentions == ("codex",)
    assert received[0].content.text == "@codex review this"
    assert received[0].raw_ref == "om_1"


async def test_feishu_rejects_invalid_verification_token() -> None:
    channel = FeishuChannel(
        app_id="app",
        app_secret="secret",
        verification_token="verify-token",
        client=cast(httpx.AsyncClient, FakeFeishuClient()),
    )

    try:
        await channel.handle_event({"type": "url_verification", "token": "wrong"})
    except FeishuAPIError as exc:
        assert "invalid Feishu verification token" in str(exc)
    else:
        raise AssertionError("expected invalid token to fail")


class FakeFeishuClient:
    def __init__(self) -> None:
        self.posts: list[dict[str, Any]] = []
        self.patches: list[dict[str, Any]] = []
        self.deletes: list[dict[str, Any]] = []
        self.closed = False

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        self.posts.append({"url": url, **kwargs})
        if url.endswith("/tenant_access_token/internal"):
            return _json_response({"code": 0, "tenant_access_token": "tenant-token"})
        return _json_response({"code": 0, "data": {"message_id": "om_message"}})

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        self.patches.append({"url": url, **kwargs})
        return _json_response({"code": 0})

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        self.deletes.append({"url": url, **kwargs})
        return _json_response({"code": 0})

    async def aclose(self) -> None:
        self.closed = True


def _json_response(data: dict[str, Any]) -> httpx.Response:
    request = httpx.Request("POST", "https://open.feishu.cn")
    return httpx.Response(200, json=data, request=request)
