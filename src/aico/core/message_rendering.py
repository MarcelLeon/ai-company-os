"""Platform-neutral rich text rendering helpers."""

from __future__ import annotations

import re

from aico.core.models import MessageContent, MessageTextSpan, MessageTextStyle


def rich_text_message(text: str) -> MessageContent:
    """Render lightweight Markdown-like structure as MessageContent spans.

    This intentionally supports only a small subset that maps well to IM channels:
    headings, section labels, slash commands, and inline bold/italic/code.
    """

    rendered_text, spans = rich_text_and_spans(text)
    return MessageContent(text=rendered_text, spans=spans)


def rich_text_and_spans(text: str) -> tuple[str, tuple[MessageTextSpan, ...]]:
    lines: list[str] = []
    spans: list[MessageTextSpan] = []
    offset = 0
    previous_blank = True
    in_code_block = False
    for raw_line in _prepare_markdown_for_im(text).splitlines():
        stripped = raw_line.strip()
        force_code = False
        if _is_single_line_fenced_code(stripped):
            raw_line = stripped[3:-3].strip()
            force_code = True
        elif stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        else:
            force_code = in_code_block
        if _is_wrapped_code_line(raw_line):
            raw_line = raw_line[1:-1]
            force_code = True
        line_spans: tuple[MessageTextSpan, ...]
        if force_code:
            line = raw_line
            line_spans = (
                (MessageTextSpan(offset=0, length=len(line), style=MessageTextStyle.CODE),)
                if line
                else ()
            )
        else:
            line, line_spans = _line_text_and_spans(raw_line, is_first_line=not lines)
        if _needs_heading_gap(line, lines, previous_blank):
            lines.append("")
            offset += 1
            previous_blank = True
        lines.append(line)
        spans.extend(
            span.model_copy(update={"offset": span.offset + offset}) for span in line_spans
        )
        offset += len(line) + 1
        previous_blank = not line.strip()
    rendered = "\n".join(lines)
    return rendered or text, tuple(spans)


def _prepare_markdown_for_im(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _split_glued_markdown_headings(normalized)
    normalized = _split_known_heading_content(normalized)
    normalized = _split_glued_markdown_tables(normalized)
    return _render_markdown_tables(normalized)


def _line_text_and_spans(
    line: str,
    *,
    is_first_line: bool,
) -> tuple[str, tuple[MessageTextSpan, ...]]:
    line = _normalize_bullet_prefix(line)
    line, heading_spans = _markdown_heading_text_and_spans(line)
    line, markdown_spans = _inline_markdown_spans(line)
    structural_spans = _structural_spans(line, is_first_line=is_first_line)
    return line, (*structural_spans, *heading_spans, *markdown_spans)


def _needs_heading_gap(line: str, lines: list[str], previous_blank: bool) -> bool:
    if not lines or previous_blank:
        return False
    stripped = line.strip()
    return bool(stripped) and (_is_section_heading(stripped) or _looks_like_plain_heading(stripped))


def _structural_spans(
    line: str,
    *,
    is_first_line: bool,
) -> tuple[MessageTextSpan, ...]:
    spans: list[MessageTextSpan] = []
    stripped = line.strip()
    leading_spaces = len(line) - len(line.lstrip())
    if _is_section_heading(stripped) or _looks_like_plain_heading(stripped):
        spans.append(
            MessageTextSpan(
                offset=leading_spaces,
                length=len(stripped),
                style=MessageTextStyle.BOLD,
            )
        )
    elif label_span := _label_value_span(line):
        spans.append(label_span)
    for start, end in _slash_command_ranges(line):
        spans.append(MessageTextSpan(offset=start, length=end - start, style=MessageTextStyle.CODE))
    return tuple(spans)


def _is_section_heading(stripped: str) -> bool:
    if not stripped or stripped.startswith(("- ", "* ", "• ")):
        return False
    return stripped.endswith(":")


def _label_value_span(line: str) -> MessageTextSpan | None:
    stripped = line.lstrip()
    if not stripped:
        return None
    leading_spaces = len(line) - len(stripped)
    bullet_prefix_length = 0
    if stripped.startswith(("- ", "* ", "• ")):
        bullet_prefix_length = 2
        stripped = stripped[bullet_prefix_length:]
    colon_index = stripped.find(":")
    if colon_index <= 0 or colon_index > 32:
        return None
    label = stripped[:colon_index]
    label_pattern = (
        r"[A-Za-z][A-Za-z0-9_ -]*|"
        r"[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9_ -]*"
    )
    if not re.fullmatch(label_pattern, label):
        return None
    is_generated_field_row = bullet_prefix_length > 0 or leading_spaces >= 2
    if (
        not is_generated_field_row
        and label.casefold() not in _LABEL_KEYS
        and label not in _CHINESE_LABEL_KEYS
    ):
        return None
    return MessageTextSpan(
        offset=leading_spaces + bullet_prefix_length,
        length=colon_index,
        style=MessageTextStyle.BOLD,
    )


def _looks_like_plain_heading(stripped: str) -> bool:
    if not stripped or stripped.startswith(("- ", "* ", "• ")):
        return False
    if stripped.startswith("|"):
        return False
    if ":" in stripped:
        return False
    if len(stripped) > 80 or stripped.endswith((".", "。", ",", "，", ";", "；")):
        return False
    words = stripped.split()
    if len(words) > 6:
        return False
    title_markers = {
        "acceptance",
        "actions",
        "candidates",
        "consulted",
        "decision",
        "effect",
        "evidence",
        "findings",
        "gaps",
        "meaning",
        "next",
        "risks",
        "status",
        "summary",
        "verdict",
        "why",
    }
    return any(marker in stripped.lower() for marker in title_markers)


def _normalize_bullet_prefix(line: str) -> str:
    stripped = line.lstrip()
    leading = line[: len(line) - len(stripped)]
    if stripped.startswith(("- ", "* ", "+ ")):
        return f"{leading}• {stripped[2:]}"
    return line


_LABEL_KEYS = {
    "acceptance",
    "adapter",
    "agent",
    "agent_max_concurrent",
    "agent_title",
    "agents",
    "aliases",
    "capabilities",
    "collaboration",
    "created",
    "detail",
    "decision",
    "done",
    "evidence",
    "grader",
    "graded_task",
    "goal",
    "id",
    "max_concurrent",
    "memories",
    "objective",
    "open",
    "option",
    "owner",
    "project",
    "provider",
    "purpose",
    "query",
    "reason",
    "recommended_appointments",
    "risk",
    "role",
    "role_title",
    "scope",
    "seat",
    "sessions",
    "skills",
    "status",
    "target",
    "tasks",
    "title",
    "tools",
    "tracking",
    "updated",
    "workspace",
}
_CHINESE_LABEL_KEYS = {
    "补充",
    "详情",
    "风险",
    "建议",
    "结论",
    "下一步",
    "证据",
}


def _slash_command_ranges(line: str) -> tuple[tuple[int, int], ...]:
    return tuple(
        (match.start(), match.end()) for match in re.finditer(r"(?<!\S)/[A-Za-z][\w-]*", line)
    )


def _markdown_heading_text_and_spans(line: str) -> tuple[str, tuple[MessageTextSpan, ...]]:
    stripped = line.lstrip()
    leading = line[: len(line) - len(stripped)]
    match = re.match(r"#{1,6}\s+(.+)", stripped)
    if match is None:
        return line, ()

    heading = match.group(1)
    text = f"{leading}{heading}"
    return (
        text,
        (
            MessageTextSpan(
                offset=len(leading),
                length=len(heading),
                style=MessageTextStyle.BOLD,
            ),
        ),
    )


def _inline_markdown_spans(text: str) -> tuple[str, tuple[MessageTextSpan, ...]]:
    output: list[str] = []
    spans: list[MessageTextSpan] = []
    cursor = 0
    while cursor < len(text):
        marker = _next_inline_marker(text, cursor)
        if marker is None:
            output.append(text[cursor])
            cursor += 1
            continue
        token, style = marker
        end = text.find(token, cursor + len(token))
        if end < 0:
            output.append(text[cursor])
            cursor += 1
            continue
        span_offset = sum(len(part) for part in output)
        inner = text[cursor + len(token) : end]
        output.append(inner)
        if inner:
            spans.append(MessageTextSpan(offset=span_offset, length=len(inner), style=style))
        cursor = end + len(token)
    return "".join(output), tuple(spans)


def _next_inline_marker(
    text: str,
    cursor: int,
) -> tuple[str, MessageTextStyle] | None:
    if text.startswith("**", cursor):
        return "**", MessageTextStyle.BOLD
    if text.startswith("`", cursor):
        return "`", MessageTextStyle.CODE
    if text.startswith("*", cursor) and not text.startswith("* ", cursor):
        return "*", MessageTextStyle.ITALIC
    return None


def _split_glued_markdown_headings(text: str) -> str:
    text = re.sub(r"([^\n#])(#{2,6})\s*", r"\1\n\2 ", text)
    return re.sub(r"(?m)^(#{1,6})([^#\s])", r"\1 \2", text)


def _split_known_heading_content(text: str) -> str:
    headings = sorted(_KNOWN_MARKDOWN_HEADINGS, key=len, reverse=True)
    for heading in headings:
        escaped = re.escape(heading)
        text = re.sub(
            rf"(?im)^(#{{1,6}}\s*)({escaped})(?=\S)",
            lambda match: f"{match.group(1)}{match.group(2)}\n",
            text,
        )
    return text


def _render_markdown_tables(text: str) -> str:
    raw_lines = text.splitlines()
    output: list[str] = []
    index = 0
    while index < len(raw_lines):
        if _is_table_start(raw_lines, index):
            table_lines: list[str] = [raw_lines[index], raw_lines[index + 1]]
            column_count = len(_table_cells(raw_lines[index]))
            trailing_line: str | None = None
            index += 2
            while index < len(raw_lines) and _is_table_row(raw_lines[index]):
                table_row, trailing_line = _split_table_row_suffix(
                    raw_lines[index],
                    column_count,
                )
                table_lines.append(table_row)
                index += 1
                if trailing_line is not None:
                    break
            rendered_table = _render_table_lines(table_lines)
            output.extend(rendered_table)
            if trailing_line and not (
                _is_table_detail_hint(trailing_line) and _TABLE_DETAIL_HINT in rendered_table
            ):
                output.append(trailing_line)
            continue
        output.append(raw_lines[index])
        index += 1
    return "\n".join(output)


def _split_table_row_suffix(line: str, column_count: int) -> tuple[str, str | None]:
    stripped = line.strip()
    if not stripped.startswith("|") or column_count < 1:
        return line, None
    closing_pipe = -1
    for _ in range(column_count + 1):
        closing_pipe = stripped.find("|", closing_pipe + 1)
        if closing_pipe < 0:
            return line, None
    suffix = stripped[closing_pipe + 1 :].strip()
    if not suffix or "|" in suffix or not _is_table_detail_hint(suffix):
        return line, None
    return stripped[: closing_pipe + 1], suffix


def _is_table_detail_hint(line: str) -> bool:
    return re.match(r"^详情(?:命令)?\s*[:：]\s*/view(?:\s|$)", line) is not None


def _split_glued_markdown_tables(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if "||" in line and _GLUED_TABLE_SEPARATOR_RE.search(line):
            if not line.lstrip().startswith("|"):
                line = re.sub(r"([^|\n])(\|[^|\n]+(?:\|[^|\n]+){1,}\|)", r"\1\n\2", line, count=1)
            line = line.replace("||", "|\n|")
        lines.append(line)
    return "\n".join(lines)


def _is_table_start(lines: list[str], index: int) -> bool:
    return (
        index + 1 < len(lines)
        and _is_table_row(lines[index])
        and _is_table_separator(lines[index + 1])
    )


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.count("|") >= 2 and not stripped.startswith("```")


def _is_table_separator(line: str) -> bool:
    stripped = line.strip().strip("|").strip()
    if not stripped:
        return False
    return all(part.strip().replace("-", "").replace(":", "") == "" for part in stripped.split("|"))


def _render_table_lines(lines: list[str]) -> list[str]:
    rows = [_table_cells(line) for line in lines if not _is_table_separator(line)]
    if not rows:
        return []
    rendered: list[str] = []
    for group_index, (headers, body) in enumerate(_table_groups(rows)):
        if group_index > 0 and rendered:
            rendered.append("")
        table_lines, has_lazy_detail = _compact_table_lines(headers, body)
        rendered.extend(table_lines)
        if has_lazy_detail:
            rendered.append(_TABLE_DETAIL_HINT)
    return rendered


def _table_groups(rows: list[list[str]]) -> list[tuple[list[str], list[list[str]]]]:
    headers = rows[0]
    body: list[list[str]] = []
    groups: list[tuple[list[str], list[list[str]]]] = []
    index = 1
    while index < len(rows):
        row = rows[index]
        if _looks_like_embedded_table_header(row, headers, rows[index + 1 :]):
            if body:
                groups.append((headers, body))
            headers = row
            body = []
            index += 1
            continue
        body.append(row)
        index += 1
    groups.append((headers, body or rows[1:] or [headers]))
    return groups


def _looks_like_embedded_table_header(
    row: list[str],
    current_headers: list[str],
    remaining_rows: list[list[str]],
) -> bool:
    return (
        len(row) > len(current_headers)
        and bool(remaining_rows)
        and any(len(candidate) == len(row) for candidate in remaining_rows[:2])
    )


def _compact_table_lines(headers: list[str], body: list[list[str]]) -> tuple[list[str], bool]:
    column_count = max(len(headers), *(len(row) for row in body))
    normalized_headers = _extended_headers(headers, column_count)
    rows = [_pad_row(row, column_count) for row in body]
    all_rows = [normalized_headers, *rows]
    cap = _table_cell_cap(column_count)
    widths = [
        min(max(_display_width(row[index]) for row in all_rows), cap)
        for index in range(column_count)
    ]
    rendered: list[str] = []
    truncated = column_count > 4
    for row_index, row in enumerate(all_rows):
        cells: list[str] = []
        for index, value in enumerate(row):
            cell, cell_truncated = _fit_table_cell(value, widths[index])
            truncated = truncated or cell_truncated
            cells.append(cell)
        rendered.append(f"`{'  '.join(cells).rstrip()}`")
        if row_index == 0 and rows:
            rendered.append(f"`{'  '.join('-' * width for width in widths).rstrip()}`")
    return rendered, truncated


def _extended_headers(headers: list[str], column_count: int) -> list[str]:
    extended = list(headers)
    supplement_index = 1
    while len(extended) < column_count:
        extended.append(f"补充{supplement_index}")
        supplement_index += 1
    return extended


def _pad_row(row: list[str], column_count: int) -> list[str]:
    return [row[index] if index < len(row) else "" for index in range(column_count)]


def _table_cell_cap(column_count: int) -> int:
    if column_count <= 2:
        return 14
    if column_count <= 4:
        return 9
    return 8


def _fit_table_cell(value: str, width: int) -> tuple[str, bool]:
    truncated = _truncate_display(value, width)
    return truncated + " " * max(width - _display_width(truncated), 0), truncated != value


def _truncate_display(value: str, width: int) -> str:
    if _display_width(value) <= width:
        return value
    if width <= 1:
        return "…"
    used = 0
    output: list[str] = []
    for char in value:
        char_width = _char_width(char)
        if used + char_width > width - 1:
            break
        output.append(char)
        used += char_width
    return f"{''.join(output)}…"


def _display_width(value: str) -> int:
    return sum(_char_width(char) for char in value)


def _char_width(char: str) -> int:
    return 2 if ord(char) > 127 else 1


def _table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _is_wrapped_code_line(line: str) -> bool:
    return len(line) >= 2 and line.startswith("`") and line.endswith("`")


def _is_single_line_fenced_code(stripped: str) -> bool:
    return len(stripped) > 6 and stripped.startswith("```") and stripped.endswith("```")


_KNOWN_MARKDOWN_HEADINGS = (
    "Acceptance Criteria",
    "Approval Need",
    "Boss Next Action",
    "Consulted Roles",
    "Decision Memo",
    "Evidence / Memory Refs",
    "Evidence / Memory References",
    "Rejected Alternatives",
    "Next Actions",
    "Operating Rules",
    "Verification Hints",
    "Acceptance",
    "Candidates",
    "Consulted",
    "Decision",
    "Effect",
    "Evidence",
    "Findings",
    "Gaps",
    "Meaning",
    "Next",
    "Risks",
    "Status",
    "Summary",
    "Verdict",
    "Why",
)

_GLUED_TABLE_SEPARATOR_RE = re.compile(r"\|[-: ]+\|")
_TABLE_DETAIL_HINT = "详情: /view 查看完整表格"
