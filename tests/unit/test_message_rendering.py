from aico.core.message_rendering import rich_text_message
from aico.core.models import MessageTextStyle


def test_rich_text_message_bolds_markdown_headings_and_adds_heading_gaps() -> None:
    message = rich_text_message("Intro\n## Decision\nShip Goal Brief v0\nRisks:\n- **Too broad**")

    assert message.text == "Intro\n\nDecision\nShip Goal Brief v0\n\nRisks:\n• Too broad"
    styles = [(span.offset, span.length, span.style) for span in message.spans]
    assert (message.text.index("Decision"), len("Decision"), MessageTextStyle.BOLD) in styles
    assert (message.text.index("Risks:"), len("Risks:"), MessageTextStyle.BOLD) in styles
    assert (message.text.index("Too broad"), len("Too broad"), MessageTextStyle.BOLD) in styles


def test_rich_text_message_keeps_simple_stream_text_plain() -> None:
    message = rich_text_message("hello world")

    assert message.text == "hello world"
    assert message.spans == ()


def test_rich_text_message_marks_slash_commands_as_code() -> None:
    message = rich_text_message("Next:\n- /approve abcdef12")

    assert message.text == "Next:\n• /approve abcdef12"
    assert (
        message.text.index("/approve"),
        len("/approve"),
        MessageTextStyle.CODE,
    ) in [(span.offset, span.length, span.style) for span in message.spans]


def test_rich_text_message_bolds_label_left_of_colon() -> None:
    message = rich_text_message("Memories: aico\n\nagent_title: Codex\nrole: Tester")

    styles = [(span.offset, span.length, span.style) for span in message.spans]
    assert (message.text.index("Memories"), len("Memories"), MessageTextStyle.BOLD) in styles
    assert (message.text.index("agent_title"), len("agent_title"), MessageTextStyle.BOLD) in styles
    assert (message.text.index("role"), len("role"), MessageTextStyle.BOLD) in styles


def test_rich_text_message_bolds_chinese_boss_labels() -> None:
    message = rich_text_message(
        "结论: 先修 Telegram 展示\n风险: Claude 仍可能输出坏表\n下一步: /view"
    )

    styles = [(span.offset, span.length, span.style) for span in message.spans]
    assert (message.text.index("结论"), len("结论"), MessageTextStyle.BOLD) in styles
    assert (message.text.index("风险"), len("风险"), MessageTextStyle.BOLD) in styles
    assert (message.text.index("下一步"), len("下一步"), MessageTextStyle.BOLD) in styles
    assert (message.text.index("/view"), len("/view"), MessageTextStyle.CODE) in styles


def test_rich_text_message_renders_agent_list_as_im_friendly_bullets() -> None:
    message = rich_text_message(
        "Agents:\n"
        "- claude -> claude-code (idle 0/5 running, max 5 concurrent)\n\n"
        "Next:\n"
        "- /agent <agent>"
    )

    assert message.text == (
        "Agents:\n"
        "• claude -> claude-code (idle 0/5 running, max 5 concurrent)\n\n"
        "Next:\n"
        "• /agent <agent>"
    )


def test_rich_text_message_splits_glued_agent_markdown_headings() -> None:
    message = rich_text_message(
        "Decision Memo — Phase 8 Kickoff## DecisionYes — 启动。## Why1. State exists."
    )

    assert message.text == (
        "Decision Memo — Phase 8 Kickoff\n\nDecision\nYes — 启动。\n\nWhy\n1. State exists."
    )
    styles = [(span.offset, span.length, span.style) for span in message.spans]
    decision_offset = message.text.index("\nDecision\n") + 1
    assert (decision_offset, len("Decision"), MessageTextStyle.BOLD) in styles
    assert (message.text.index("Why"), len("Why"), MessageTextStyle.BOLD) in styles


def test_rich_text_message_renders_small_markdown_tables_as_compact_table() -> None:
    message = rich_text_message(
        "| Sprint | Status |\n|---|---|\n| Inbox | OK |\n| Dream | Needs review |"
    )

    assert "Sprint" in message.text
    assert "Status" in message.text
    assert "Inbox" in message.text
    assert "Dream" in message.text
    assert "Needs review" in message.text
    assert "• Sprint:" not in message.text
    styles = [(span.offset, span.length, span.style) for span in message.spans]
    assert any(span_style is MessageTextStyle.CODE for _, _, span_style in styles)


def test_rich_text_message_separates_detail_command_glued_to_table_row() -> None:
    message = rich_text_message(
        "ROUND192 Telegram 表格验收\n"
        "| 场景 | 状态 | 负责人 | 说明 |\n"
        "|---|---|---|---|\n"
        "| 小表 | 通过 | reviewer | 单块等宽展示 |\n"
        "| 宽表 | 受控 | lead | 超宽内容需截断并通过 view 查看详情 |详情命令: /view"
    )

    assert "补充1" not in message.text
    assert "详情命" not in message.text
    assert message.text.count("/view") == 1
    assert "详情: /view 查看完整表格" in message.text


def test_rich_text_message_preserves_unclosed_extra_table_cell() -> None:
    message = rich_text_message(
        "| 角色 | 状态 | 交付 |\n|---|---|---|\n| lead | active | 决策 | 这是额外说明"
    )

    assert "补充1" in message.text
    assert "这是额外…" in message.text


def test_rich_text_message_preserves_fenced_code_blocks_as_code_spans() -> None:
    message = rich_text_message("Run:\n```bash\nuv run pytest\n```")

    assert message.text == "Run:\nuv run pytest"
    assert (
        message.text.index("uv run pytest"),
        len("uv run pytest"),
        MessageTextStyle.CODE,
    ) in [(span.offset, span.length, span.style) for span in message.spans]


def test_rich_text_message_preserves_single_line_fenced_code_as_code_span() -> None:
    message = rich_text_message("```uv run pytest```")

    assert message.text == "uv run pytest"
    assert (
        0,
        len("uv run pytest"),
        MessageTextStyle.CODE,
    ) in [(span.offset, span.length, span.style) for span in message.spans]
