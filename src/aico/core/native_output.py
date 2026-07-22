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
    text = normalize_agent_output_for_im(text)
    if preferred_format is MessageNativeFormat.TELEGRAM_HTML:
        if message := telegram_html_message(text):
            return message
    return rich_text_message(_telegram_html_to_light_markdown(text))


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
    detection_text = _text_for_markdown_structure_detection(text)
    return _contains_markdown_table(detection_text)


def _contains_markdown_table(text: str) -> bool:
    return bool(_MARKDOWN_TABLE_RE.search(text))


def _text_for_markdown_structure_detection(text: str) -> str:
    without_allowed_tags = re.sub(
        r"</?(?:b|strong|i|em|u|ins|s|strike|del|code|pre|blockquote)(?:\s[^>]*)?>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    return html.unescape(without_allowed_tags)


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


def normalize_agent_output_for_im(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _simplify_local_markdown_links(normalized)
    normalized = _normalize_common_html_lists(normalized)
    normalized = _split_glued_native_headings(normalized)
    normalized = _split_glued_plain_sections(normalized)
    normalized = _split_compact_severity_sections(normalized)
    normalized = _split_inline_markdown_bullets(normalized)
    normalized = _split_glued_bullets(normalized)
    return _collapse_excess_blank_lines(normalized)


def _split_glued_native_headings(text: str) -> str:
    text = re.sub(
        r"(</(?:b|strong)>)(?=<(?:b|strong)>)",
        r"\1\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf"(?<!^)(?<!\n)(?=<(?:b|strong)>({_NATIVE_SECTION_HEADING_PATTERN})(?::)?</(?:b|strong)>)",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf"<(b|strong)>({_NATIVE_SECTION_HEADING_PATTERN})</\1>:\s*",
        lambda match: f"<{match.group(1)}>{match.group(2)}:</{match.group(1)}>\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(<(?:b|strong)>[^<:\n]{1,96}</(?:b|strong)>)(?=[^\s<:，,。.;；!?！？])",
        r"\1\n",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _simplify_local_markdown_links(text: str) -> str:
    pattern = r"\[([^\]\n]+)\]\(((?:/Users|/private)/[^)\s]+)\)"

    def replace(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2)
        line_match = re.search(r":(\d+)$", target)
        if line_match and not label.endswith(f":{line_match.group(1)}"):
            return f"{label}:{line_match.group(1)}"
        return label

    return re.sub(pattern, replace, text)


def _normalize_common_html_lists(text: str) -> str:
    text = re.sub(r"</li>\s*<li>", "\n<li>", text, flags=re.IGNORECASE)
    text = re.sub(r"<li>\s*", "\n• ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*</li>", "", text, flags=re.IGNORECASE)
    return re.sub(r"</?(?:ul|ol)>", "", text, flags=re.IGNORECASE)


def _telegram_html_to_light_markdown(text: str) -> str:
    text = re.sub(
        r"<(?:b|strong)>(.*?)</(?:b|strong)>",
        lambda match: f"**{match.group(1)}**",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"<(?:code)>(.*?)</(?:code)>",
        lambda match: f"`{match.group(1)}`",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"<(?:pre)>(.*?)</(?:pre)>",
        _pre_html_to_light_markdown,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(?:i|em|u|s|blockquote)>", "", text, flags=re.IGNORECASE)
    return html.unescape(text)


def _pre_html_to_light_markdown(match: re.Match[str]) -> str:
    content = match.group(1)
    if _contains_markdown_table(html.unescape(content)):
        return f"\n{content}\n"
    return f"```\n{content}\n```"


def _split_glued_bullets(text: str) -> str:
    bullet_pattern = (
        r"(?<!^)(?<!\n)(?P<gap>[ \t]*)"
        r"(?P<bullet>•\s+(?:High|Medium|Low|Critical|Done|Blocked|Risks?|Next|"
        r"Suggestion|Recommendation|[A-Z][A-Za-z0-9_-]*|[\u4e00-\u9fff]))"
    )
    return re.sub(bullet_pattern, r"\n\n\g<bullet>", text)


def _split_inline_markdown_bullets(text: str) -> str:
    bullet_label = (
        r"(?:\*\*)?(?:Critical|High|Medium|Low|Done|Blocked|Risks?|Next|"
        r"Suggestion|Recommendation|[A-Z][A-Za-z0-9_-]*|[\u4e00-\u9fff])"
    )
    return re.sub(
        rf"(?<!^)(?<!\n)[ \t]+-\s+(?={bullet_label})",
        "\n\n- ",
        text,
    )


def _split_compact_severity_sections(text: str) -> str:
    severity_pattern = _SEVERITY_HEADING_PATTERN
    text = re.sub(
        rf"\b(Findings)(?=({severity_pattern}):)",
        r"\1\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf"(?<=[.!?。])(?=({severity_pattern}):)",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?<!^)(?<!\n)(Risks / approval need|Next Actions)-\s*",
        r"\n\n\1\n",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^(Risks / approval need|Next Actions)-\s*",
        r"\1\n",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _split_glued_plain_sections(text: str) -> str:
    heading_pattern = _PLAIN_SECTION_HEADING_PATTERN
    text = re.sub(
        rf"(?<!^)(?<!\n)(?=({heading_pattern})(?:\d+\.|:|[\u4e00-\u9fff]))",
        "\n\n",
        text,
    )
    text = re.sub(
        rf"\b({heading_pattern})(?=\d+\.)",
        r"\1\n\n",
        text,
    )
    text = re.sub(
        rf"\b({heading_pattern})(?=[\u4e00-\u9fff])",
        r"\1\n",
        text,
    )
    text = re.sub(r"(?<=[.!?。])(?=\d+\.\s)", "\n\n", text)
    return re.sub(r"(?<=[\u4e00-\u9fff])(?=\d+\.\s)", "\n\n", text)


def _collapse_excess_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text)


_NATIVE_SECTION_HEADINGS = (
    "Acceptance",
    "Acceptance Criteria",
    "Approval Need",
    "Blocked",
    "Boss Next Action",
    "Consulted Roles",
    "Decision",
    "Decision Memo",
    "Done",
    "Evidence",
    "Evidence / Memory Refs",
    "Evidence / Memory References",
    "Findings",
    "Goal received",
    "Missing Tests",
    "Next",
    "Next Actions",
    "Operating Rules",
    "Recommendation",
    "Rejected Alternatives",
    "Risks",
    "Status",
    "Summary",
    "Verdict",
    "Why",
)
_NATIVE_SECTION_HEADING_PATTERN = "|".join(
    re.escape(heading) for heading in sorted(_NATIVE_SECTION_HEADINGS, key=len, reverse=True)
)
_PLAIN_SECTION_HEADINGS = (
    "Findings",
    "Missing Tests",
    "Notes",
    "Summary",
    "Verdict",
)
_PLAIN_SECTION_HEADING_PATTERN = "|".join(
    re.escape(heading) for heading in sorted(_PLAIN_SECTION_HEADINGS, key=len, reverse=True)
)
_SEVERITY_HEADINGS = (
    "Critical",
    "High",
    "Medium",
    "Low",
)
_SEVERITY_HEADING_PATTERN = "|".join(_SEVERITY_HEADINGS)
_MARKDOWN_TABLE_RE = re.compile(r"(?m)^\s*\|.+\|\s*$\n^\s*\|[\s\-:|]+\|\s*$")


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
    "- Prefer compact Telegram-readable tables for table-like content.\n"
    "- Shorten long cells before rendering tables; keep details for /view or /task.\n"
    "- Use <pre> only for compact tables, code, or log blocks.\n"
    "- Put headings, paragraphs, and list items on separate lines.\n"
    "- Use '• ' for bullets; do not use Markdown '- ' bullets.\n"
    "- Do not use Markdown headings or triple-backtick fences.\n"
    "- Do not use unsupported HTML tags or attributes."
)
