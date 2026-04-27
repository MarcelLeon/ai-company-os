from aico.core import ChannelTarget, IncomingMessage, MessageContent, MessageRouter


def test_router_uses_first_mention_as_target_persona() -> None:
    router = MessageRouter(default_persona="default", task_id_factory=lambda: "task-1")
    message = IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="user-1",
        mentions=("lao-zhang", "xiao-li"),
        content=MessageContent(text="review this"),
        raw_ref="message-1",
    )

    task = router.to_task(message)

    assert task.task_id == "task-1"
    assert task.payload == "review this"
    assert task.requester_id == "user-1"
    assert task.target_persona == "lao-zhang"
    assert task.context_ref == "message-1"


def test_router_falls_back_to_default_persona_without_mentions() -> None:
    router = MessageRouter(default_persona="default", task_id_factory=lambda: "task-2")
    message = IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="user-1",
        content=MessageContent(text="summarize"),
        raw_ref="message-2",
    )

    task = router.to_task(message)

    assert task.target_persona == "default"
    assert task.payload == "summarize"


def test_router_uses_slash_command_as_target_persona_and_strips_prefix() -> None:
    router = MessageRouter(default_persona="default", task_id_factory=lambda: "task-3")
    message = _message("/codex summarize this repo")

    task = router.to_task(message)

    assert task.target_persona == "codex"
    assert task.payload == "summarize this repo"


def test_router_supports_telegram_bot_command_suffix() -> None:
    router = MessageRouter(default_persona="default", task_id_factory=lambda: "task-4")
    message = _message("/codex@ai_company_os_bot summarize")

    task = router.to_task(message)

    assert task.target_persona == "codex"
    assert task.payload == "summarize"


def test_router_uses_leading_at_command_even_without_telegram_entity() -> None:
    router = MessageRouter(default_persona="default", task_id_factory=lambda: "task-5")
    message = _message("@codex summarize")

    task = router.to_task(message)

    assert task.target_persona == "codex"
    assert task.payload == "summarize"


def test_router_uses_colon_prefix_as_target_persona() -> None:
    router = MessageRouter(default_persona="default", task_id_factory=lambda: "task-6")
    message = _message("codex: summarize")

    task = router.to_task(message)

    assert task.target_persona == "codex"
    assert task.payload == "summarize"


def test_router_strips_leading_mention_from_payload_when_entity_exists() -> None:
    router = MessageRouter(default_persona="default", task_id_factory=lambda: "task-7")
    message = _message("@codex summarize", mentions=("codex",))

    task = router.to_task(message)

    assert task.target_persona == "codex"
    assert task.payload == "summarize"


def _message(text: str, mentions: tuple[str, ...] = ()) -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="user-1",
        mentions=mentions,
        content=MessageContent(text=text),
        raw_ref="message-1",
    )
