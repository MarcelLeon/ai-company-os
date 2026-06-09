from aico.core.models import MessageNativeFormat, MessageTextStyle, Task
from aico.core.native_output import (
    NATIVE_OUTPUT_FORMAT_METADATA_KEY,
    agent_output_message,
    task_with_native_output_format,
    telegram_html_message,
)


def test_telegram_html_message_accepts_sanitized_supported_html() -> None:
    message = telegram_html_message("<b>Inbox</b>\n<pre>Name | Status</pre>")

    assert message is not None
    assert message.native_format is MessageNativeFormat.TELEGRAM_HTML
    assert message.text == "<b>Inbox</b>\n<pre>Name | Status</pre>"
    assert message.spans == ()


def test_telegram_html_message_rejects_unsupported_html_and_markdown() -> None:
    assert telegram_html_message("<table><tr><td>Inbox</td></tr></table>") is None
    assert telegram_html_message("```uv run pytest```") is None
    assert telegram_html_message("| Feature | Status |\n|---|---|\n| Inbox | OK |") is None


def test_telegram_html_message_escapes_placeholders_inside_pre_blocks() -> None:
    message = telegram_html_message("<b>Next actions</b><pre>/task <id>\n/approve <task_id></pre>")

    assert message is not None
    assert message.native_format is MessageNativeFormat.TELEGRAM_HTML
    assert message.text == (
        "<b>Next actions</b><pre>/task &lt;id&gt;\n/approve &lt;task_id&gt;</pre>"
    )


def test_agent_output_message_prefers_native_format_and_falls_back_to_rich_text() -> None:
    native = agent_output_message(
        "<b>Status</b>\n<pre>Inbox | OK</pre>",
        preferred_format=MessageNativeFormat.TELEGRAM_HTML,
    )
    fallback = agent_output_message(
        "## Status\n```uv run pytest```",
        preferred_format=MessageNativeFormat.TELEGRAM_HTML,
    )

    assert native.native_format is MessageNativeFormat.TELEGRAM_HTML
    assert fallback.native_format is None
    assert fallback.text == "Status\nuv run pytest"
    assert any(span.style is MessageTextStyle.CODE for span in fallback.spans)


def test_agent_output_message_splits_glued_native_html_sections() -> None:
    message = agent_output_message(
        "<b>Overnight delegation handoff — GitHub launch</b>"
        '<b>Goal received</b>"prepare launch"'
        "<b>Decision</b>Ship docs only."
        "<b>Why</b>:Scope is frozen."
        "• Done — added launch playbook.",
        preferred_format=MessageNativeFormat.TELEGRAM_HTML,
    )

    assert message.native_format is MessageNativeFormat.TELEGRAM_HTML
    assert message.text == (
        "<b>Overnight delegation handoff — GitHub launch</b>\n\n"
        "<b>Goal received</b>\n"
        '"prepare launch"\n'
        "<b>Decision</b>\n"
        "Ship docs only.\n"
        "<b>Why:</b>\n"
        "Scope is frozen.\n\n"
        "• Done — added launch playbook."
    )


def test_agent_output_message_splits_glued_review_bullets() -> None:
    message = agent_output_message(
        "• High — Quickstart promise is too strong."
        "docs/contributors/quickstart.md:22-46 needs GitHub CLI."
        "。• Medium — Show HN details are mostly defensible."
        "。• Recommendation — tighten public copy before launch."
    )

    assert message.text == (
        "• High — Quickstart promise is too strong."
        "docs/contributors/quickstart.md:22-46 needs GitHub CLI."
        "。\n\n"
        "• Medium — Show HN details are mostly defensible."
        "。\n\n"
        "• Recommendation — tighten public copy before launch."
    )


def test_task_with_native_output_format_injects_telegram_contract_when_enabled() -> None:
    task = Task(
        task_id="task-1",
        payload="summarize status",
        requester_id="user-1",
        target_persona="implementer",
    )

    formatted = task_with_native_output_format(task, channel_name="telegram", enabled=True)
    disabled = task_with_native_output_format(task, channel_name="telegram", enabled=False)
    feishu = task_with_native_output_format(task, channel_name="feishu", enabled=True)

    assert formatted.payload.startswith("Output format for Telegram:\n")
    assert formatted.payload.endswith("\n\nsummarize status")
    assert formatted.metadata[-1].key == NATIVE_OUTPUT_FORMAT_METADATA_KEY
    assert formatted.metadata[-1].value == MessageNativeFormat.TELEGRAM_HTML.value
    assert disabled == task
    assert feishu == task
