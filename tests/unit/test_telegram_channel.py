import asyncio
import json

import httpx

from aico.channel import IMChannel
from aico.channel.telegram import TelegramAPIError, TelegramChannel
from aico.core import (
    ChannelTarget,
    HealthStatus,
    IncomingMessage,
    MessageAction,
    MessageContent,
    MessageNativeFormat,
    MessageTextSpan,
    MessageTextStyle,
)
from aico.core.message_rendering import rich_text_message


async def test_telegram_channel_parses_text_update_and_advances_offset() -> None:
    requests: list[httpx.Request] = []
    received: list[IncomingMessage] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": [
                    {
                        "update_id": 41,
                        "message": {
                            "message_id": 7,
                            "chat": {"id": -1001},
                            "from": {"id": 99},
                            "text": "@lao_zhang please inspect",
                            "entities": [{"type": "mention", "offset": 0, "length": 10}],
                        },
                    }
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client, poll_timeout_seconds=1)
        channel.on_incoming(lambda message: _record(received, message))

        await channel.poll_once()
        await asyncio.sleep(0)
        await channel.poll_once()
        await asyncio.sleep(0)

    assert isinstance(channel, IMChannel)
    assert len(received) == 2
    assert received[0].source == ChannelTarget(channel_name="telegram", target_id="-1001")
    assert received[0].sender_id == "99"
    assert received[0].mentions == ("lao_zhang",)
    assert received[0].content == MessageContent(text="@lao_zhang please inspect")
    assert requests[0].read() == b'{"timeout":1}'
    assert requests[1].read() == b'{"timeout":1,"offset":42}'


async def test_telegram_channel_does_not_block_polling_on_long_handler() -> None:
    requests: list[bytes] = []
    received: list[str] = []
    release_handler = asyncio.Event()

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.read())
        update_id = len(requests)
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": [
                    {
                        "update_id": update_id,
                        "message": {
                            "message_id": update_id,
                            "chat": {"id": -1001},
                            "from": {"id": 99},
                            "text": f"message {update_id}",
                        },
                    }
                ],
            },
        )

    async def incoming_handler(message: IncomingMessage) -> None:
        received.append(message.content.text)
        await release_handler.wait()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client, poll_timeout_seconds=1)
        channel.on_incoming(incoming_handler)

        await channel.poll_once()
        await asyncio.sleep(0)
        await channel.poll_once()
        await asyncio.sleep(0)
        release_handler.set()
        await asyncio.sleep(0)
        await channel.stop()

    assert received == ["message 1", "message 2"]
    assert requests == [b'{"timeout":1}', b'{"timeout":1,"offset":2}']


async def test_telegram_channel_maps_callback_query_to_incoming_message() -> None:
    requests: list[tuple[str, bytes]] = []
    received: list[IncomingMessage] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.url.path, request.read()))
        method = request.url.path.rsplit("/", maxsplit=1)[-1]
        if method == "answerCallbackQuery":
            return httpx.Response(200, json={"ok": True, "result": True})
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": [
                    {
                        "update_id": 51,
                        "callback_query": {
                            "id": "callback-1",
                            "from": {"id": 99},
                            "data": "/role confirm",
                            "message": {
                                "message_id": 7,
                                "chat": {"id": -1001},
                            },
                        },
                    }
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client, poll_timeout_seconds=1)
        channel.on_incoming(lambda message: _record(received, message))

        await channel.poll_once()
        await asyncio.sleep(0)

    assert received[0].source == ChannelTarget(channel_name="telegram", target_id="-1001")
    assert received[0].sender_id == "99"
    assert received[0].content == MessageContent(text="/role confirm")
    assert received[0].raw_ref == "callback-1"
    assert requests == [
        ("/bottoken/getUpdates", b'{"timeout":1}'),
        ("/bottoken/answerCallbackQuery", b'{"callback_query_id":"callback-1"}'),
    ]


async def test_telegram_channel_send_edit_and_delete_use_bot_api_methods() -> None:
    calls: list[tuple[str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, request.read()))
        method = request.url.path.rsplit("/", maxsplit=1)[-1]
        result = {"message_id": 123} if method == "sendMessage" else True
        return httpx.Response(200, json={"ok": True, "result": result})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client)
        target = ChannelTarget(channel_name="telegram", target_id="chat-1")

        sent = await channel.send_message(target, MessageContent(text="hello"))
        await channel.edit_message(target, sent.message_id, MessageContent(text="updated"))
        await channel.delete_message(target, sent.message_id)

    assert sent.message_id == "123"
    assert calls == [
        ("/bottoken/sendMessage", b'{"chat_id":"chat-1","text":"hello"}'),
        (
            "/bottoken/editMessageText",
            b'{"chat_id":"chat-1","message_id":"123","text":"updated"}',
        ),
        ("/bottoken/deleteMessage", b'{"chat_id":"chat-1","message_id":"123"}'),
    ]


async def test_telegram_channel_sends_document_as_multipart_upload() -> None:
    calls: list[tuple[str, dict[str, str], bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, dict(request.headers), request.read()))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 456}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client)
        target = ChannelTarget(channel_name="telegram", target_id="chat-1")

        sent = await channel.send_document(
            target,
            filename="aico-view-aico.html",
            content=b"<!doctype html><html>AICO</html>",
            media_type="text/html; charset=utf-8",
            caption="AICO view snapshot for aico (read-only)",
        )

    path, headers, body = calls[0]
    assert sent.message_id == "456"
    assert path == "/bottoken/sendDocument"
    assert "multipart/form-data" in headers["content-type"]
    assert b"chat_id" in body
    assert b"chat-1" in body
    assert b"caption" in body
    assert b"aico-view-aico.html" in body
    assert b"<!doctype html><html>AICO</html>" in body


async def test_telegram_channel_renders_text_spans_as_telegram_html() -> None:
    calls: list[tuple[str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, request.read()))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 123}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client)
        target = ChannelTarget(channel_name="telegram", target_id="chat-1")

        await channel.send_message(
            target,
            MessageContent(
                text="Project <A> ready",
                spans=(MessageTextSpan(offset=0, length=11, style=MessageTextStyle.BOLD),),
            ),
        )

    assert calls[0][0] == "/bottoken/sendMessage"
    assert json.loads(calls[0][1]) == {
        "chat_id": "chat-1",
        "text": "<b>Project &lt;A&gt;</b> ready",
        "parse_mode": "HTML",
    }


async def test_telegram_channel_renders_agent_markdown_as_html() -> None:
    calls: list[tuple[str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, request.read()))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 123}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client)
        target = ChannelTarget(channel_name="telegram", target_id="chat-1")

        await channel.send_message(
            target,
            rich_text_message(
                "Decision Memo## DecisionYes\n\n| Sprint | Status |\n|---|---|\n| Inbox | OK |"
            ),
        )

    payload = json.loads(calls[0][1])
    assert payload["parse_mode"] == "HTML"
    assert "<b>Decision</b>" in payload["text"]
    assert "<code>Sprint | Status</code>" in payload["text"]


async def test_telegram_channel_sends_native_telegram_html_without_span_rewrite() -> None:
    calls: list[tuple[str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, request.read()))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 123}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client)
        target = ChannelTarget(channel_name="telegram", target_id="chat-1")

        await channel.send_message(
            target,
            MessageContent(
                text="<b>Status</b>\n<pre>Inbox | OK</pre>",
                native_format=MessageNativeFormat.TELEGRAM_HTML,
            ),
        )

    payload = json.loads(calls[0][1])
    assert payload == {
        "chat_id": "chat-1",
        "text": "<b>Status</b>\n<pre>Inbox | OK</pre>",
        "parse_mode": "HTML",
    }


async def test_telegram_channel_renders_actions_as_inline_keyboard() -> None:
    calls: list[tuple[str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, request.read()))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 123}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client)
        target = ChannelTarget(channel_name="telegram", target_id="chat-1")

        await channel.send_message(
            target,
            MessageContent(
                text="Approve task?",
                actions=(
                    MessageAction(label="Approve", value="approve:task-1"),
                    MessageAction(label="Reject", value="reject:task-1"),
                ),
            ),
        )

    assert calls[0][0] == "/bottoken/sendMessage"
    assert json.loads(calls[0][1]) == {
        "chat_id": "chat-1",
        "text": "Approve task?",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "Approve", "callback_data": "approve:task-1"},
                    {"text": "Reject", "callback_data": "reject:task-1"},
                ]
            ]
        },
    }


async def test_telegram_channel_ignores_non_text_updates() -> None:
    received: list[IncomingMessage] = []

    def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": [
                    {"update_id": 1, "message": {"message_id": 1, "chat": {"id": 1}}},
                    {"update_id": 2, "edited_message": {"message_id": 2, "chat": {"id": 1}}},
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client)
        channel.on_incoming(lambda message: _record(received, message))

        await channel.poll_once()

    assert received == []


async def test_telegram_channel_reports_failed_health_when_api_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(200, json={"ok": False, "description": "bad token"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client)

        assert await channel.health_check() is HealthStatus.FAILED


async def test_telegram_channel_raises_when_api_returns_not_ok() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(200, json={"ok": False, "description": "chat not found"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client)

        try:
            await channel.send_message(
                ChannelTarget(channel_name="telegram", target_id="missing"),
                MessageContent(text="hello"),
            )
        except TelegramAPIError as exc:
            assert str(exc) == "chat not found"
        else:
            raise AssertionError("expected TelegramAPIError")


async def test_telegram_channel_surfaces_telegram_description_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(
            400,
            json={"ok": False, "description": "Bad Request: chat not found"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client)

        try:
            await channel.send_message(
                ChannelTarget(channel_name="telegram", target_id="missing"),
                MessageContent(text="hello"),
            )
        except TelegramAPIError as exc:
            assert str(exc) == "Bad Request: chat not found"
        else:
            raise AssertionError("expected TelegramAPIError")


async def test_telegram_channel_ignores_noop_edit_http_error() -> None:
    calls: list[tuple[str, bytes]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, request.read()))
        description = (
            "Bad Request: message is not modified: specified new message content and reply "
            "markup are exactly the same as a current content and reply markup of the message"
        )
        return httpx.Response(
            400,
            json={
                "ok": False,
                "description": description,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        channel = TelegramChannel("token", client=client)
        target = ChannelTarget(channel_name="telegram", target_id="chat-1")

        await channel.edit_message(target, "123", MessageContent(text="same"))

    assert calls == [
        (
            "/bottoken/editMessageText",
            b'{"chat_id":"chat-1","message_id":"123","text":"same"}',
        )
    ]


async def _record(received: list[IncomingMessage], message: IncomingMessage) -> None:
    received.append(message)
