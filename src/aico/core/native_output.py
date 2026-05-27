"""Channel-native agent output formatting contracts and validation."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from aico.core.message_rendering import rich_text_message
from aico.core.models import MessageContent, MessageNativeFormat, MetadataEntry, Task

NATIVE_OUTPUT_FORMAT_METADATA_KEY = "aico.native_output_format"


def task_with_native_output_format(
    task: Task,
    *,
    channel_name: str,
    enabled: bool,
) -> Task:
    if not enabled or _metadata_value(task, NATIVE_OUTPUT_FORMAT_METADATA_KEY) is not None:
        return task
    if channel_name != "telegram":
        return task
    return task.model_copy(
        update={
            "payload": f"{_TELEGRAM_HTML_INSTRUCTION}\n\n{task.payload}",
            "metadata": (
                *task.metadata,
                MetadataEntry(
                    key=NATIVE_OUTPUT_FORMAT_METADATA_KEY,
                    value=MessageNativeFormat.TELEGRAM_HTML.value,
                ),
            ),
        }
    )


def native_output_format_from_task(task: Task) -> MessageNativeFormat | None:
    value = _metadata_value(task, NATIVE_OUTPUT_FORMAT_METADATA_KEY)
    if value == MessageNativeFormat.TELEGRAM_HTML.value:
        return MessageNativeFormat.TELEGRAM_HTML
    return None


def agent_output_message(
    text: str,
    *,
    preferred_format: MessageNativeFormat | None = None,
) -> MessageContent:
    if preferred_format is MessageNativeFormat.TELEGRAM_HTML:
        if message := telegram_html_message(text):
            return message
    return rich_text_message(text)


def telegram_html_message(text: str) -> MessageContent | None:
    if _contains_markdown_structure(text):
        return None
    try:
        sanitized = _sanitize_telegram_html(text)
    except ValueError:
        return None
    if not sanitized.strip():
        return None
    return MessageContent(
        text=sanitized,
        native_format=MessageNativeFormat.TELEGRAM_HTML,
    )


def _contains_markdown_structure(text: str) -> bool:
    if "```" in text:
        return True
    return bool(re.search(r"(?m)^\s*\|.+\|\s*$\n^\s*\|[\s\-:|]+\|\s*$", text))


def _sanitize_telegram_html(text: str) -> str:
    parser = _TelegramHTMLSanitizer()
    parser.feed(text)
    parser.close()
    return parser.output


def _metadata_value(task: Task, key: str) -> object | None:
    for entry in task.metadata:
        if entry.key == key:
            return entry.value
    return None


class _TelegramHTMLSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._open_tags: list[str] = []

    @property
    def output(self) -> str:
        if self._open_tags:
            raise ValueError("unclosed Telegram HTML tag")
        return "".join(self._parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.casefold()
        if normalized not in _ALLOWED_TELEGRAM_HTML_TAGS or attrs:
            if self._inside_literal_tag():
                self._parts.append(html.escape(self.get_starttag_text() or f"<{tag}>", quote=False))
                return
            raise ValueError("unsupported Telegram HTML tag")
        self._parts.append(f"<{normalized}>")
        self._open_tags.append(normalized)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if not self._open_tags or self._open_tags[-1] != normalized:
            if self._inside_literal_tag():
                self._parts.append(html.escape(f"</{tag}>", quote=False))
                return
            raise ValueError("mismatched Telegram HTML tag")
        self._open_tags.pop()
        self._parts.append(f"</{normalized}>")

    def handle_data(self, data: str) -> None:
        self._parts.append(html.escape(data, quote=False))

    def _inside_literal_tag(self) -> bool:
        return any(tag in _TELEGRAM_LITERAL_TAGS for tag in self._open_tags)


_ALLOWED_TELEGRAM_HTML_TAGS = frozenset(
    {
        "b",
        "strong",
        "i",
        "em",
        "u",
        "ins",
        "s",
        "strike",
        "del",
        "code",
        "pre",
        "blockquote",
    }
)

_TELEGRAM_LITERAL_TAGS = frozenset({"code", "pre"})

_TELEGRAM_HTML_INSTRUCTION = (
    "Output format for Telegram:\n"
    "- Prefer Telegram Bot API HTML in the final answer.\n"
    "- Allowed tags: <b>, <i>, <u>, <s>, <code>, <pre>, <blockquote>.\n"
    "- Use <b> for short headings and field labels.\n"
    "- Use <pre> for aligned tables or multi-line monospace blocks.\n"
    "- Put headings, paragraphs, and list items on separate lines.\n"
    "- Use '• ' for bullets; do not use Markdown '- ' bullets.\n"
    "- Do not use Markdown headings, Markdown tables, or triple-backtick fences.\n"
    "- Do not use unsupported HTML tags or attributes."
)
