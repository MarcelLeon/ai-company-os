import httpx

from aico.channel import IMChannel
from aico.channel.telegram import TelegramAPIError, TelegramChannel
from aico.core import ChannelTarget, HealthStatus, IncomingMessage, MessageContent


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
        await channel.poll_once()

    assert isinstance(channel, IMChannel)
    assert len(received) == 2
    assert received[0].source == ChannelTarget(channel_name="telegram", target_id="-1001")
    assert received[0].sender_id == "99"
    assert received[0].mentions == ("lao_zhang",)
    assert received[0].content == MessageContent(text="@lao_zhang please inspect")
    assert requests[0].read() == b'{"timeout":1}'
    assert requests[1].read() == b'{"timeout":1,"offset":42}'


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


async def _record(received: list[IncomingMessage], message: IncomingMessage) -> None:
    received.append(message)
