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


def test_rich_text_message_renders_markdown_tables_as_monospaced_im_table() -> None:
    message = rich_text_message(
        "| Sprint | Status |\n|---|---|\n| Inbox | OK |\n| Dream | Needs review |"
    )

    assert message.text == (
        "Sprint | Status\n-------+-------------\nInbox  | OK\nDream  | Needs review"
    )
    assert all(span.style is MessageTextStyle.CODE for span in message.spans)


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
