from aico.core import (
    AssignmentProfile,
    MessageContent,
    MessageTextStyle,
    ProjectProfile,
    RiskLevel,
    RoleProfile,
    TaskSnapshot,
    TaskStatus,
)
from aico.core.project_docs import ProjectDocumentSnippet
from aico.core.project_messages import (
    project_blockers_message,
    project_next_message,
    project_office_message,
    project_summary_message,
    role_detail_message,
    roles_message,
    team_message,
)


def test_project_summary_message_converts_summary_markdown_to_render_spans() -> None:
    message = project_summary_message(
        MessageContent(text="Brief: aico\nrepo: /repo/aico"),
        "- **风险**: check `logs`\n- *Next*: approve task",
    )

    assert message.text == (
        "Boss summary\n"
        "• 风险: check logs\n"
        "• Next: approve task\n\n"
        "Facts\n"
        "Brief: aico\n"
        "repo: /repo/aico"
    )
    styles = [(span.offset, span.length, span.style) for span in message.spans]
    assert styles == [
        (0, len("Boss summary"), MessageTextStyle.BOLD),
        (message.text.index("风险"), len("风险"), MessageTextStyle.BOLD),
        (message.text.index("logs"), len("logs"), MessageTextStyle.CODE),
        (message.text.index("Next"), len("Next"), MessageTextStyle.ITALIC),
        (message.text.index("Facts"), len("Facts"), MessageTextStyle.BOLD),
    ]


def test_project_office_message_adds_short_next_actions() -> None:
    message = project_office_message(
        ProjectProfile(id="aico", name="AI Company OS", repo="/repo/aico"),
        (AssignmentProfile(project="aico", agent="claude", role="implementer", seat="seat-1"),),
        AssignmentProfile(project="aico", agent="claude", role="implementer", seat="seat-1"),
    )

    assert "Next:\n- /brief\n- /team\n- /next\n- /daily\n- /weekly" in message.text
    assert _code_texts(message).isdisjoint({"/brief", "/team", "/next", "/daily", "/weekly"})


def test_roles_and_role_detail_messages_guide_next_steps() -> None:
    project = ProjectProfile(id="aico", name="AI Company OS", repo="/repo/aico")
    role = RoleProfile(
        id="implementer",
        title="Implementation Lead",
        default_permissions=("code", "tests", "docs"),
    )
    appointment = AssignmentProfile(
        project="aico",
        agent="claude",
        role="implementer",
        seat="seat-1",
        permissions=("code", "tests", "docs"),
    )

    roles = roles_message(project, (role,), (appointment,))
    detail = role_detail_message(project, role, appointment)
    open_detail = role_detail_message(
        project,
        RoleProfile(id="tester", title="Test Lead", default_permissions=("code", "tests")),
        None,
    )

    assert "Next:\n- /role <role>\n- /agents\n- /appoint <agent> as <role>" in roles.text
    assert "- /ask implementer <task>" in detail.text
    assert "- /appoint claude as implementer code tests docs" in detail.text
    assert "- /agents\n- /appoint <agent> as tester\n- /roles" in open_detail.text
    assert _code_texts_after(roles, "Next:").isdisjoint({"/role", "/agents", "/appoint", "/roles"})
    assert _code_texts_after(detail, "Next:").isdisjoint(
        {"/ask", "/lead", "/appoint", "/unappoint"}
    )
    assert _code_texts_after(open_detail, "Next:").isdisjoint({"/agents", "/appoint", "/roles"})


def test_team_message_guides_role_workflow() -> None:
    appointment = AssignmentProfile(
        project="aico",
        agent="claude",
        role="implementer",
        seat="seat-1",
        permissions=("code", "tests", "docs"),
    )

    message = team_message(
        ProjectProfile(id="aico", name="AI Company OS", repo="/repo/aico"),
        (appointment,),
        appointment,
    )

    assert "Next:\n- /ask implementer <task>\n- /who implementer\n- /roles" in message.text
    assert _code_texts(message).isdisjoint({"/ask", "/who", "/roles"})


def test_project_blockers_message_adds_section_and_command_spans() -> None:
    message = project_blockers_message(
        ProjectProfile(id="aico", name="AI Company OS", repo="/repo/aico"),
        (
            TaskSnapshot(
                task_id="abcdef123456",
                target_persona="implementer",
                status=TaskStatus.WAITING_APPROVAL,
                risk_level=RiskLevel.WRITE_FILES,
                reason="write docs",
            ),
        ),
    )

    styles = [(span.offset, span.length, span.style) for span in message.spans]
    assert (0, len("Blockers: aico [AI Company OS]"), MessageTextStyle.BOLD) in styles
    assert (
        message.text.index("waiting decisions:"),
        len("waiting decisions:"),
        MessageTextStyle.BOLD,
    ) in styles
    assert (
        message.text.index("/approve"),
        len("/approve"),
        MessageTextStyle.CODE,
    ) in styles
    assert (
        message.text.index("/reject"),
        len("/reject"),
        MessageTextStyle.CODE,
    ) in styles


def test_project_next_message_normalizes_fact_bullets_and_inline_markdown() -> None:
    message = project_next_message(
        ProjectProfile(
            id="aico",
            name="AI Company OS",
            repo="/repo/aico",
            current_phase="Phase 5",
        ),
        (AssignmentProfile(project="aico", agent="claude", role="implementer", seat="seat-1"),),
        AssignmentProfile(project="aico", agent="claude", role="implementer", seat="seat-1"),
        (),
    )

    assert "- Ask implementer" not in message.text
    assert "• Ask implementer" in message.text
    assert "/ask" in message.text

    blockers = project_blockers_message(
        ProjectProfile(id="aico", name="AI Company OS", repo="/repo/aico"),
        (),
        (
            ProjectDocumentSnippet(
                label="blockers",
                path="docs/journal/BLOCKERS.md",
                lines=("**当前 workaround**", "- Check /brief", "- /brief"),
            ),
        ),
    )

    assert "**当前 workaround**" not in blockers.text
    assert "当前 workaround" in blockers.text
    assert "  • Check /brief" in blockers.text
    assert "  • /brief" in blockers.text
    styles = [(span.offset, span.length, span.style) for span in blockers.spans]
    assert (
        blockers.text.index("当前 workaround"),
        len("当前 workaround"),
        MessageTextStyle.BOLD,
    ) in styles


def test_project_facts_render_markdown_headings_from_document_snippets() -> None:
    message = project_blockers_message(
        ProjectProfile(id="aico", name="AI Company OS", repo="/repo/aico"),
        (),
        (
            ProjectDocumentSnippet(
                label="blockers",
                path="docs/journal/BLOCKERS.md",
                lines=(
                    "# BLOCKERS.md — 卡点难题",
                    "## 当前活跃卡点",
                    "### 状态变化",
                ),
            ),
        ),
    )

    assert "# BLOCKERS.md" not in message.text
    assert "## 当前活跃卡点" not in message.text
    assert "### 状态变化" not in message.text
    assert "BLOCKERS.md — 卡点难题" in message.text
    assert "当前活跃卡点" in message.text
    assert "状态变化" in message.text
    styles = [(span.offset, span.length, span.style) for span in message.spans]
    assert (
        message.text.index("BLOCKERS.md — 卡点难题"),
        len("BLOCKERS.md — 卡点难题"),
        MessageTextStyle.BOLD,
    ) in styles
    assert (
        message.text.index("当前活跃卡点"),
        len("当前活跃卡点"),
        MessageTextStyle.BOLD,
    ) in styles


def test_project_summary_message_preserves_normalized_fact_rendering() -> None:
    facts = project_next_message(
        ProjectProfile(id="aico", name="AI Company OS", repo="/repo/aico"),
        (AssignmentProfile(project="aico", agent="claude", role="implementer", seat="seat-1"),),
        AssignmentProfile(project="aico", agent="claude", role="implementer", seat="seat-1"),
        (),
    )
    message = project_summary_message(facts, "- **Next**: use `/brief`")

    assert "• Ask implementer" in message.text
    assert "- Ask implementer" not in message.text
    styles = [(span.offset, span.length, span.style) for span in message.spans]
    assert (
        message.text.index("/ask"),
        len("/ask"),
        MessageTextStyle.CODE,
    ) in styles
    assert (
        message.text.index("/brief"),
        len("/brief"),
        MessageTextStyle.CODE,
    ) in styles


def test_project_summary_message_preserves_fact_spans_with_offsets() -> None:
    facts = project_blockers_message(
        ProjectProfile(id="aico", name="AI Company OS", repo="/repo/aico"),
        (
            TaskSnapshot(
                task_id="abcdef123456",
                target_persona="implementer",
                status=TaskStatus.WAITING_APPROVAL,
                risk_level=RiskLevel.WRITE_FILES,
            ),
        ),
    )
    message = project_summary_message(facts, "Needs **decision**")

    styles = [(span.offset, span.length, span.style) for span in message.spans]
    assert (
        message.text.index("Blockers: aico [AI Company OS]"),
        len("Blockers: aico [AI Company OS]"),
        MessageTextStyle.BOLD,
    ) in styles
    assert (
        message.text.index("waiting decisions:"),
        len("waiting decisions:"),
        MessageTextStyle.BOLD,
    ) in styles
    assert (
        message.text.index("/approve"),
        len("/approve"),
        MessageTextStyle.CODE,
    ) in styles


def _code_texts(message: MessageContent) -> set[str]:
    return {
        message.text[span.offset : span.offset + span.length]
        for span in message.spans
        if span.style is MessageTextStyle.CODE
    }


def _code_texts_after(message: MessageContent, marker: str) -> set[str]:
    start = message.text.index(marker)
    return {
        message.text[span.offset : span.offset + span.length]
        for span in message.spans
        if span.style is MessageTextStyle.CODE and span.offset >= start
    }
