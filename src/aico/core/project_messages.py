"""Text rendering helpers for project office commands."""

from __future__ import annotations

import re
from datetime import timedelta

from aico.core.models import (
    AuditEvent,
    AuditEventType,
    MessageAction,
    MessageContent,
    MessageTextSpan,
    MessageTextStyle,
    RiskLevel,
    TaskSnapshot,
    TaskStatus,
    utc_now,
)
from aico.core.project_assignment import (
    AssignmentProfile,
    CompanyAgentProfile,
    ProjectProfile,
    RoleProfile,
)
from aico.core.project_docs import ProjectDocumentSnippet

_CORE_ROLE_IDS = ("pm", "implementer", "reviewer", "challenger", "golden-tester")
_SPECIALIST_ROLE_IDS = ("senior-architect", "security", "legal-compliance", "market-risk")
_SUPPORT_ROLE_IDS = ("tester", "docs", "ops", "analyst", "designer")
_ROLE_GROUPS = (
    ("Core", _CORE_ROLE_IDS),
    ("Specialists", _SPECIALIST_ROLE_IDS),
    ("Support", _SUPPORT_ROLE_IDS),
)
_COMPACT_ROLE_IDS = set(_CORE_ROLE_IDS + _SPECIALIST_ROLE_IDS)
_RISK_LADDER = "read_only -> write_files -> shell_exec -> destructive"


def projects_message(
    projects: tuple[ProjectProfile, ...],
    active_project: ProjectProfile | None,
) -> MessageContent:
    if not projects:
        return MessageContent(text="No projects configured")
    active_id = None if active_project is None else active_project.id
    lines = ["Projects:"]
    for project in projects:
        marker = " *" if project.id == active_id else ""
        phase = f" - {project.current_phase}" if project.current_phase else ""
        lines.append(f"- {project.id}{marker}: {project.name}{phase}")
    return _heading_message(lines)


def project_office_message(
    project: ProjectProfile,
    appointments: tuple[AssignmentProfile, ...],
    default_appointment: AssignmentProfile | None,
) -> MessageContent:
    default_text = _appointment_ref(default_appointment)
    lines = [
        f"Project active: {project.id} [{project.name}]",
        f"repo: {project.repo}",
        f"lead: {default_text}",
    ]
    if project.current_phase:
        lines.append(f"phase: {project.current_phase}")
    lines.append("")
    lines.append("Team:")
    if appointments:
        lines.extend(f"- {_appointment_ref(appointment)}" for appointment in appointments)
    else:
        lines.append("- none")
    lines.extend(("", *_team_readiness_lines(appointments, default_appointment)))
    lines.extend(_next_lines(("/brief", "/team", "/next", "/daily", "/weekly")))
    return _heading_message(lines)


def project_brief_message(
    project: ProjectProfile,
    appointments: tuple[AssignmentProfile, ...],
    default_appointment: AssignmentProfile | None,
    task_snapshots: tuple[TaskSnapshot, ...],
    audit_events: tuple[AuditEvent, ...],
    document_snippets: tuple[ProjectDocumentSnippet, ...] = (),
) -> MessageContent:
    lines = [
        f"Brief: {project.id} [{project.name}]",
        f"repo: {project.repo}",
    ]
    if project.current_phase:
        lines.append(f"phase: {project.current_phase}")
    if project.brief:
        lines.append(f"brief: {project.brief}")
    if project.north_star:
        lines.append(f"north_star: {project.north_star}")
    if project.status_doc:
        lines.append(f"status_doc: {project.status_doc}")
    if project.journal:
        lines.append(f"journal: {project.journal}")
    lines.extend(
        (
            "",
            f"lead: {_appointment_ref(default_appointment)}",
            "team:",
            *(_team_lines(appointments) or ("- none",)),
            "",
            "recent tasks:",
            *(_recent_task_lines(task_snapshots) or ("- none",)),
            "",
            "recent audit:",
            *(_recent_audit_lines(audit_events) or ("- none",)),
            "",
            "documents:",
            *(_document_lines(document_snippets) or ("- none",)),
        )
    )
    return _heading_message(lines)


def project_risks_message(
    project: ProjectProfile,
    task_snapshots: tuple[TaskSnapshot, ...],
    audit_events: tuple[AuditEvent, ...],
    document_snippets: tuple[ProjectDocumentSnippet, ...] = (),
) -> MessageContent:
    task_risks = tuple(_project_task_risk_lines(task_snapshots))
    audit_risks = tuple(_project_audit_risk_lines(audit_events))
    documented_risks = tuple(_document_lines(document_snippets))
    lines = [f"Risks: {project.id} [{project.name}]"]
    if not task_risks and not audit_risks and not documented_risks:
        lines.append("- no current project delivery risks found")
        return _heading_message(lines)
    if task_risks or audit_risks:
        lines.extend(("", "delivery risks:"))
        lines.extend(task_risks)
        lines.extend(audit_risks)
    if documented_risks:
        lines.extend(("", "documented blockers / pitfalls:"))
        lines.extend(documented_risks)
    return _heading_message(lines)


def project_blockers_message(
    project: ProjectProfile,
    task_snapshots: tuple[TaskSnapshot, ...],
    document_snippets: tuple[ProjectDocumentSnippet, ...] = (),
) -> MessageContent:
    decision_lines = tuple(_decision_blocker_lines(task_snapshots))
    failed_lines = tuple(_failed_blocker_lines(task_snapshots))
    document_lines = tuple(_document_lines(document_snippets))
    lines = [f"Blockers: {project.id} [{project.name}]"]
    if not decision_lines and not failed_lines and not document_lines:
        lines.append("- no current blockers in local state")
        return _heading_message(lines)
    if decision_lines:
        lines.extend(("", "waiting decisions:"))
        lines.extend(decision_lines)
    if failed_lines:
        lines.extend(("", "failed / rejected work:"))
        lines.extend(failed_lines)
    if document_lines:
        lines.extend(("", "documented blockers:"))
        lines.extend(document_lines)
    return _heading_message(lines)


def project_next_message(
    project: ProjectProfile,
    appointments: tuple[AssignmentProfile, ...],
    default_appointment: AssignmentProfile | None,
    task_snapshots: tuple[TaskSnapshot, ...],
    blocker_snippets: tuple[ProjectDocumentSnippet, ...] = (),
) -> MessageContent:
    lines = [f"Next actions: {project.id} [{project.name}]"]
    if project.current_phase:
        lines.append(f"phase: {project.current_phase}")
    lines.append(f"lead: {_appointment_ref(default_appointment)}")
    lines.append("")
    lines.extend(_next_action_lines(project, appointments, default_appointment, task_snapshots))
    if blocker_snippets:
        lines.extend(("", "check documented blockers:", *(_document_lines(blocker_snippets))))
    return _heading_message(lines)


def roles_message(
    project: ProjectProfile,
    roles: tuple[RoleProfile, ...],
    appointments: tuple[AssignmentProfile, ...],
    *,
    include_all: bool = False,
) -> MessageContent:
    if not roles:
        return MessageContent(text=f"No roles configured for {project.id}")
    appointments_by_role = {appointment.role: appointment for appointment in appointments}
    roles_by_id = {role.id: role for role in roles}
    built_in_ids = set(_CORE_ROLE_IDS + _SPECIALIST_ROLE_IDS + _SUPPORT_ROLE_IDS)
    custom_ids = set(roles_by_id) - built_in_ids
    visible_ids = (
        set(roles_by_id)
        if include_all
        else _COMPACT_ROLE_IDS | custom_ids | set(appointments_by_role)
    )
    lines = [f"Roles: {project.id} [{project.name}]"]
    rendered: set[str] = set()
    for group_name, role_ids in _ROLE_GROUPS:
        group_lines = tuple(
            _compact_role_line(roles_by_id[role_id], appointments_by_role.get(role_id))
            for role_id in role_ids
            if role_id in roles_by_id and role_id in visible_ids
        )
        if not group_lines:
            continue
        lines.extend(("", group_name, *group_lines))
        rendered.update(role_id for role_id in role_ids if role_id in roles_by_id)
    custom_lines = tuple(
        _compact_role_line(role, appointments_by_role.get(role.id))
        for role in roles
        if role.id not in rendered and role.id in visible_ids
    )
    if custom_lines:
        lines.extend(("", "Custom", *custom_lines))
    hidden = tuple(role.id for role in roles if role.id not in visible_ids)
    if hidden:
        lines.extend(("", f"Hidden: {', '.join(hidden)}", "Use /roles all or /role <id>."))
    else:
        lines.extend(("", "Use /role <id> for scope, approvals, and prompt."))
    next_items = (
        ("/role <role>", "/agents", "/appoint <agent> as <role>", "/roles all")
        if not include_all
        else ("/role <role>", "/team", "/agents")
    )
    lines.extend(_next_lines(next_items))
    return _heading_message(lines)


def role_detail_message(
    project: ProjectProfile,
    role: RoleProfile,
    appointment: AssignmentProfile | None,
) -> MessageContent:
    owner = "open" if appointment is None else appointment.agent
    scope = ", ".join(appointment.permissions if appointment else role.default_permissions) or "-"
    approval_required = ", ".join(role.approval_required) or "-"
    lines = [
        f"Role: {role.id} [{project.id}]",
        f"title: {role.title}",
        f"owner: {owner}",
        f"scope: {scope}",
        f"approval: {approval_required}",
        f"risk ladder: {_RISK_LADDER}",
    ]
    if role.summary:
        lines.append(f"summary: {role.summary}")
    if role.inline_prompt:
        lines.append(f"prompt: {role.inline_prompt}")
    if appointment is None:
        lines.extend(_next_lines(("/agents", f"/appoint <agent> as {role.id}", "/roles")))
    else:
        scope_hint = " ".join(appointment.permissions or role.default_permissions) or "<scope>"
        lines.extend(
            _next_lines(
                (
                    f"/ask {role.id} <task>",
                    f"/lead {role.id}",
                    f"/appoint {appointment.agent} as {role.id} {scope_hint}",
                    f"/unappoint {role.id}",
                )
            )
        )
    return _heading_message(lines)


def _compact_role_line(role: RoleProfile, appointment: AssignmentProfile | None) -> str:
    owner = "open" if appointment is None else appointment.agent
    return f"- {role.id} | {role.title} | {owner}"


def role_proposal_message(project: ProjectProfile, role: RoleProfile) -> MessageContent:
    scope = ", ".join(role.default_permissions) or "-"
    approval_required = ", ".join(role.approval_required) or "-"
    return _heading_message(
        (
            f"Role proposal for {project.id}",
            f"id: {role.id}",
            f"title: {role.title}",
            f"summary: {role.summary or '-'}",
            f"scope: {scope}",
            f"approval_required: {approval_required}",
            f"prompt: {role.inline_prompt or '-'}",
            "",
            "Send /role confirm to add it to this project, or /role discard to cancel.",
        ),
        actions=(
            MessageAction(label="Confirm", value="/role confirm"),
            MessageAction(label="Discard", value="/role discard"),
        ),
    )


def role_added_message(project: ProjectProfile, role: RoleProfile) -> MessageContent:
    return _heading_message(
        (
            f"Role added to {project.id}: {role.id}",
            f"title: {role.title}",
            f"Use /roles to review it, then /appoint <agent> as {role.id} [scope] when ready.",
        )
    )


def project_report_message(
    project: ProjectProfile,
    appointments: tuple[AssignmentProfile, ...],
    default_appointment: AssignmentProfile | None,
    task_snapshots: tuple[TaskSnapshot, ...],
    audit_events: tuple[AuditEvent, ...],
    context_snippets: tuple[ProjectDocumentSnippet, ...],
    risk_snippets: tuple[ProjectDocumentSnippet, ...],
    *,
    title: str,
    window_label: str,
    window_days: int,
) -> MessageContent:
    cutoff = utc_now() - timedelta(days=window_days)
    recent_tasks = tuple(snapshot for snapshot in task_snapshots if snapshot.updated_at >= cutoff)
    recent_audit = tuple(event for event in audit_events if event.timestamp >= cutoff)
    risk_lines = (
        *_project_task_risk_lines(recent_tasks),
        *_project_audit_risk_lines(recent_audit),
        *_document_lines(risk_snippets),
    )
    lines = [
        f"{title}: {project.id} [{project.name}]",
        f"window: {window_label}",
    ]
    if project.current_phase:
        lines.append(f"phase: {project.current_phase}")
    lines.extend(
        (
            f"lead: {_appointment_ref(default_appointment)}",
            "",
            "team:",
            *(_team_lines(appointments) or ("- none",)),
            "",
            "progress:",
            *(_progress_lines(recent_tasks, recent_audit) or ("- no completed work recorded")),
            "",
            "open work:",
            *(_open_work_lines(recent_tasks) or ("- none",)),
            "",
            "risks:",
            *(risk_lines or ("- no active risks in recent local state",)),
            "",
            "context:",
            *(_document_lines(context_snippets) or ("- none",)),
        )
    )
    return _heading_message(lines)


def team_message(
    project: ProjectProfile,
    appointments: tuple[AssignmentProfile, ...],
    default_appointment: AssignmentProfile | None = None,
) -> MessageContent:
    if not appointments:
        return _heading_message(
            [
                f"No team appointments for {project.id}",
                *_next_lines(("/roles", "/agents", "/appoint <agent> as <role>")),
            ]
        )
    lines = [f"Team for {project.id}:"]
    if default_appointment is not None:
        lines.append(f"lead: {_appointment_ref(default_appointment)}")
    for appointment in appointments:
        scope = ", ".join(appointment.permissions) or appointment.risk_policy
        lead_marker = " [lead]" if _same_appointment(appointment, default_appointment) else ""
        lines.append(f"- {appointment.role} -> {appointment.agent} ({scope}){lead_marker}")
    lines.extend(("", *_team_readiness_lines(appointments, default_appointment)))
    if default_appointment is None:
        lines.extend(_next_lines(("/roles", "/who <role>", "/appoint <agent> as <role>")))
    else:
        lines.extend(
            _next_lines(
                (
                    f"/ask {default_appointment.role} <task>",
                    f"/who {default_appointment.role}",
                    "/roles",
                    "/lead <role>",
                )
            )
        )
    return _heading_message(lines)


def _team_readiness_lines(
    appointments: tuple[AssignmentProfile, ...],
    default_appointment: AssignmentProfile | None,
) -> tuple[str, ...]:
    missing = []
    if default_appointment is None:
        missing.append("lead")
    if not any(appointment.role == "challenger" for appointment in appointments):
        missing.append("challenger")
    if not missing:
        return ("team readiness: complete",)
    return (
        "team readiness: incomplete",
        f"missing: {', '.join(missing)}",
        "required: lead + challenger",
    )


def who_message(
    project: ProjectProfile,
    appointment: AssignmentProfile,
    agent: CompanyAgentProfile | None,
    role: RoleProfile | None,
) -> MessageContent:
    title = "-" if role is None else role.title
    agent_title = "-" if agent is None else agent.title
    scope = ", ".join(appointment.permissions) or appointment.risk_policy
    workspace = appointment.workspace or project.repo
    return _heading_message(
        (
            f"{project.id} / {appointment.role}",
            f"agent: {appointment.agent}",
            f"title: {agent_title}",
            f"role_title: {title}",
            f"scope: {scope}",
            f"workspace: {workspace}",
            f"seat: {appointment.seat}",
        )
    )


def appointment_created_message(
    project: ProjectProfile,
    appointment: AssignmentProfile,
    agent: CompanyAgentProfile | None,
    role: RoleProfile | None,
) -> MessageContent:
    agent_title = "-" if agent is None else agent.title
    max_concurrent = 1 if agent is None else agent.max_concurrent_tasks
    recommended_appointments = 1 if agent is None else agent.recommended_max_appointments
    role_title = appointment.role if role is None else role.title
    scope = ", ".join(appointment.permissions) or appointment.risk_policy
    return _heading_message(
        (
            "Appointment active",
            "",
            f"{appointment.agent} is appointed to {project.id} as {appointment.role}.",
            f"agent_title: {agent_title}",
            f"role: {role_title}",
            f"workspace: {appointment.workspace or project.repo}",
            f"scope: {scope}",
            f"agent_max_concurrent: {max_concurrent}",
            f"recommended_appointments: <= {recommended_appointments}",
            f"seat: {appointment.seat}",
        )
    )


def appointment_removed_message(
    project: ProjectProfile, appointment: AssignmentProfile
) -> MessageContent:
    return _heading_message(
        (
            "Appointment removed",
            "",
            f"{appointment.agent} is no longer appointed to {project.id} as {appointment.role}.",
            f"seat: {appointment.seat}",
        )
    )


def default_role_message(project: ProjectProfile, appointment: AssignmentProfile) -> MessageContent:
    return _heading_message(
        (
            f"Lead role for {project.id}: {appointment.role} -> {appointment.agent}",
            "Plain messages will go to this lead role.",
        )
    )


def project_summary_message(facts: MessageContent, summary: str | None) -> MessageContent:
    if not summary:
        return facts
    summary_text, summary_spans = _summary_text_and_spans(summary.strip())
    summary_offset = len("Boss summary\n")
    facts_prefix = "\n\nFacts\n"
    facts_offset = summary_offset + len(summary_text) + len(facts_prefix)
    text = f"Boss summary\n{summary_text}{facts_prefix}{facts.text}"
    spans = (
        MessageTextSpan(offset=0, length=len("Boss summary"), style=MessageTextStyle.BOLD),
        *(
            span.model_copy(update={"offset": span.offset + summary_offset})
            for span in summary_spans
        ),
        MessageTextSpan(
            offset=summary_offset + len(summary_text) + len("\n\n"),
            length=len("Facts"),
            style=MessageTextStyle.BOLD,
        ),
        *(span.model_copy(update={"offset": span.offset + facts_offset}) for span in facts.spans),
    )
    return MessageContent(text=text, spans=spans, actions=facts.actions)


def assignments_message(
    assignments: tuple[AssignmentProfile, ...],
    *,
    project_id: str | None = None,
) -> MessageContent:
    if not assignments:
        target = f" for {project_id}" if project_id else ""
        return MessageContent(text=f"No assignments{target}")
    heading = f"Assignments for {project_id}:" if project_id else "Assignments:"
    lines = [heading]
    lines.extend(
        f"- {assignment.seat}: project={assignment.project}, agent={assignment.agent}, "
        f"role={assignment.role}, session={assignment.session_policy}, "
        f"risk={assignment.risk_policy}"
        for assignment in assignments
    )
    return MessageContent(text="\n".join(lines))


def assignment_message(
    assignment: AssignmentProfile,
    agent: CompanyAgentProfile | None,
    project: ProjectProfile | None,
) -> MessageContent:
    title = "-" if agent is None else agent.title
    provider = "-" if agent is None else agent.provider
    project_name = "-" if project is None else project.name
    workspace = assignment.workspace or (None if project is None else project.repo) or "-"
    return MessageContent(
        text=(
            f"Assignment: {assignment.seat}\n"
            f"project: {assignment.project} ({project_name})\n"
            f"agent: {assignment.agent}\n"
            f"title: {title}\n"
            f"provider: {provider}\n"
            f"role: {assignment.role}\n"
            f"workspace: {workspace}\n"
            f"session_policy: {assignment.session_policy}\n"
            f"risk_policy: {assignment.risk_policy}\n"
            f"prompt: {assignment.prompt or '-'}"
        )
    )


def short_id_text(value: str) -> str:
    return value[:8]


def _heading_message(
    lines: tuple[str, ...] | list[str],
    *,
    actions: tuple[MessageAction, ...] = (),
) -> MessageContent:
    rendered_lines: list[str] = []
    spans: list[MessageTextSpan] = []
    offset = 0
    in_next_section = False
    for index, raw_line in enumerate(lines):
        is_linkable_command_line = in_next_section and _is_bulleted_command_line(raw_line)
        line, line_spans = _project_line_text_and_spans(
            raw_line,
            is_first_line=index == 0,
            linkable_command_line=is_linkable_command_line,
        )
        rendered_lines.append(line)
        spans.extend(
            span.model_copy(update={"offset": span.offset + offset}) for span in line_spans
        )
        offset += len(line) + 1
        stripped = raw_line.strip()
        if stripped == "Next:":
            in_next_section = True
        elif in_next_section and (not stripped or not _is_bulleted_command_line(raw_line)):
            in_next_section = False
    return MessageContent(text="\n".join(rendered_lines), spans=tuple(spans), actions=actions)


def _next_lines(commands: tuple[str, ...]) -> tuple[str, ...]:
    return ("", "Next:", *(f"- {command}" for command in commands))


def _project_line_text_and_spans(
    line: str,
    *,
    is_first_line: bool,
    linkable_command_line: bool = False,
) -> tuple[str, tuple[MessageTextSpan, ...]]:
    if not linkable_command_line:
        line = _normalize_bullet_prefix(line)
    line, heading_spans = _markdown_heading_text_and_spans(line)
    line, markdown_spans = _inline_markdown_spans(line)
    structural_spans = _project_structural_spans(
        line,
        is_first_line=is_first_line,
        linkable_commands=linkable_command_line,
    )
    return line, (*structural_spans, *heading_spans, *markdown_spans)


def _project_structural_spans(
    line: str,
    *,
    is_first_line: bool,
    linkable_commands: bool = False,
) -> tuple[MessageTextSpan, ...]:
    spans: list[MessageTextSpan] = []
    stripped = line.strip()
    if is_first_line and line:
        spans.append(MessageTextSpan(offset=0, length=len(line), style=MessageTextStyle.BOLD))
    elif _is_section_heading(stripped):
        leading_spaces = len(line) - len(line.lstrip())
        spans.append(
            MessageTextSpan(
                offset=leading_spaces,
                length=len(stripped),
                style=MessageTextStyle.BOLD,
            )
        )
    elif label_span := _label_value_span(line):
        spans.append(label_span)
    if not linkable_commands:
        for start, end in _slash_command_ranges(line):
            spans.append(
                MessageTextSpan(
                    offset=start,
                    length=end - start,
                    style=MessageTextStyle.CODE,
                )
            )
    return tuple(spans)


def _is_section_heading(stripped: str) -> bool:
    if not stripped or stripped.startswith(("- ", "* ", "• ")):
        return False
    return stripped.endswith(":")


def _label_value_span(line: str) -> MessageTextSpan | None:
    stripped = line.lstrip()
    if not stripped or stripped.startswith(("- ", "* ", "• ")):
        return None
    colon_index = stripped.find(":")
    if colon_index <= 0 or colon_index > 32:
        return None
    label = stripped[:colon_index]
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_ -]*", label):
        return None
    if label not in _LABEL_KEYS:
        return None
    leading_spaces = len(line) - len(stripped)
    return MessageTextSpan(
        offset=leading_spaces,
        length=colon_index,
        style=MessageTextStyle.BOLD,
    )


def _slash_command_ranges(line: str) -> tuple[tuple[int, int], ...]:
    return tuple(
        (match.start(), match.end()) for match in re.finditer(r"(?<!\S)/[A-Za-z][\w-]*", line)
    )


_LABEL_KEYS = {
    "agent",
    "agent_max_concurrent",
    "agent_title",
    "missing",
    "project",
    "provider",
    "recommended_appointments",
    "risk_policy",
    "role",
    "role_title",
    "scope",
    "seat",
    "session_policy",
    "status",
    "team readiness",
    "title",
    "workspace",
}


def _is_bulleted_command_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith(("- /", "* /"))


def _summary_text_and_spans(summary: str) -> tuple[str, tuple[MessageTextSpan, ...]]:
    lines: list[str] = []
    spans: list[MessageTextSpan] = []
    offset = 0
    for raw_line in summary.splitlines():
        line, line_spans = _summary_line_and_spans(raw_line)
        lines.append(line)
        spans.extend(
            span.model_copy(update={"offset": span.offset + offset}) for span in line_spans
        )
        offset += len(line) + 1
    return "\n".join(lines), tuple(spans)


def _summary_line_and_spans(line: str) -> tuple[str, tuple[MessageTextSpan, ...]]:
    line = _normalize_bullet_prefix(line)
    line, heading_spans = _markdown_heading_text_and_spans(line)
    line, markdown_spans = _inline_markdown_spans(line)
    return line, (*heading_spans, *markdown_spans)


def _normalize_bullet_prefix(line: str) -> str:
    stripped = line.lstrip()
    leading = line[: len(line) - len(stripped)]
    if stripped.startswith(("- ", "* ")):
        return f"{leading}• {stripped[2:]}"
    return line


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


def _task_status_line(snapshot: TaskSnapshot) -> str:
    adapter_name = snapshot.adapter_name or snapshot.target_persona
    line = f"{snapshot.task_id} [{adapter_name}]: {snapshot.status.value}"
    if snapshot.risk_level is not RiskLevel.READ_ONLY:
        line = f"{line} ({snapshot.risk_level.value})"
    if snapshot.reason:
        line = f"{line} - {snapshot.reason}"
    return line


def _appointment_ref(appointment: AssignmentProfile | None) -> str:
    if appointment is None:
        return "-"
    return f"{appointment.role} -> {appointment.agent}"


def _same_appointment(
    left: AssignmentProfile,
    right: AssignmentProfile | None,
) -> bool:
    return right is not None and left.seat == right.seat


def _team_lines(appointments: tuple[AssignmentProfile, ...]) -> tuple[str, ...]:
    return tuple(f"- {_appointment_ref(appointment)}" for appointment in appointments)


def _recent_task_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[str, ...]:
    return tuple(f"- {_task_status_line(snapshot)}" for snapshot in task_snapshots[:5])


def _recent_audit_lines(audit_events: tuple[AuditEvent, ...]) -> tuple[str, ...]:
    return tuple(
        f"- {event.event_type.value}: {event.target_persona}" for event in audit_events[:5]
    )


def _document_lines(snippets: tuple[ProjectDocumentSnippet, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    for snippet in snippets:
        lines.append(f"- {snippet.label}: {snippet.path}")
        lines.extend(f"  {line}" for line in snippet.lines)
    return tuple(lines)


def _progress_lines(
    task_snapshots: tuple[TaskSnapshot, ...],
    audit_events: tuple[AuditEvent, ...],
) -> tuple[str, ...]:
    lines = [
        f"- {_task_status_line(snapshot)}"
        for snapshot in task_snapshots
        if snapshot.status is TaskStatus.DONE
    ]
    lines.extend(
        f"- audit {event.event_type.value}: {event.target_persona}"
        for event in audit_events
        if event.event_type is AuditEventType.TASK_COMPLETED
    )
    return tuple(lines[:5])


def _open_work_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[str, ...]:
    open_statuses = {
        TaskStatus.RUNNING,
        TaskStatus.WAITING_APPROVAL,
        TaskStatus.FAILED,
        TaskStatus.INTERRUPTED,
        TaskStatus.REJECTED,
    }
    return tuple(
        f"- {_task_status_line(snapshot)}"
        for snapshot in task_snapshots
        if snapshot.status in open_statuses
    )


def _decision_blocker_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    for snapshot in task_snapshots:
        if snapshot.status is not TaskStatus.WAITING_APPROVAL:
            continue
        short_id = short_id_text(snapshot.task_id)
        reason = f" - {snapshot.reason}" if snapshot.reason else ""
        lines.append(
            f"- task {short_id} [{snapshot.target_persona}] needs decision "
            f"({snapshot.risk_level.value}){reason}; use /approve {short_id} or /reject {short_id}"
        )
    return tuple(lines)


def _failed_blocker_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[str, ...]:
    blocked_statuses = {
        TaskStatus.FAILED,
        TaskStatus.INTERRUPTED,
        TaskStatus.REJECTED,
    }
    lines: list[str] = []
    for snapshot in task_snapshots:
        if snapshot.status not in blocked_statuses:
            continue
        reason = f" - {snapshot.reason}" if snapshot.reason else ""
        lines.append(
            f"- task {snapshot.task_id} [{snapshot.target_persona}] {snapshot.status.value}{reason}"
        )
    return tuple(lines)


def _next_action_lines(
    project: ProjectProfile,
    appointments: tuple[AssignmentProfile, ...],
    default_appointment: AssignmentProfile | None,
    task_snapshots: tuple[TaskSnapshot, ...],
) -> tuple[str, ...]:
    actions: list[str] = []
    if not appointments:
        return (
            "- Appoint an implementer: /appoint claude as implementer",
            "- Appoint a reviewer when available: /appoint codex as reviewer",
        )
    if default_appointment is None:
        actions.append("- Choose a lead role for plain messages: /lead implementer")
    actions.extend(_approval_action_lines(task_snapshots))
    actions.extend(_failed_action_lines(task_snapshots))
    if not actions:
        lead_role = "implementer" if default_appointment is None else default_appointment.role
        actions.extend(
            (
                f"- Ask {lead_role} to continue the highest-priority work: "
                f"/ask {lead_role} 继续推进当前最高优先级任务",
                "- Review status after work completes: /brief",
                "- Check blockers before a long task: /blockers",
            )
        )
    return tuple(actions[:6])


def _approval_action_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    for snapshot in task_snapshots:
        if snapshot.status is not TaskStatus.WAITING_APPROVAL:
            continue
        short_id = short_id_text(snapshot.task_id)
        lines.append(
            f"- Decide pending {snapshot.risk_level.value} task {short_id}: "
            f"/approve {short_id} or /reject {short_id}"
        )
    return tuple(lines)


def _failed_action_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    for snapshot in task_snapshots:
        if snapshot.status not in {TaskStatus.FAILED, TaskStatus.INTERRUPTED, TaskStatus.REJECTED}:
            continue
        if _is_system_noise(snapshot.reason):
            lines.append(f"- Fix route/config issue for task {snapshot.task_id}: /blockers")
        else:
            role = snapshot.target_persona
            lines.append(f"- Ask {role} to recover task {snapshot.task_id}: /ask {role} 复盘并修复")
    return tuple(lines)


def _project_task_risk_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    for snapshot in task_snapshots:
        if _is_system_noise(snapshot.reason):
            continue
        if snapshot.status in {TaskStatus.FAILED, TaskStatus.INTERRUPTED}:
            reason = f" - {snapshot.reason}" if snapshot.reason else ""
            lines.append(
                f"- task {snapshot.task_id} [{snapshot.target_persona}] "
                f"{snapshot.status.value}{reason}"
            )
        elif snapshot.risk_level is RiskLevel.DESTRUCTIVE:
            reason = f" - {snapshot.reason}" if snapshot.reason else ""
            lines.append(
                f"- destructive task {snapshot.task_id} [{snapshot.target_persona}] "
                f"{snapshot.status.value}{reason}"
            )
    return tuple(lines)


def _project_audit_risk_lines(audit_events: tuple[AuditEvent, ...]) -> tuple[str, ...]:
    risky_events = {
        AuditEventType.TASK_FAILED,
        AuditEventType.TASK_INTERRUPTED,
    }
    lines: list[str] = []
    for event in audit_events:
        if event.event_type not in risky_events or _is_system_noise(event.detail):
            continue
        detail = f" - {event.detail}" if event.detail else ""
        lines.append(f"- audit {event.event_type.value}: {event.target_persona}{detail}")
    return tuple(lines)


def _is_system_noise(reason: str | None) -> bool:
    if reason is None:
        return False
    lowered = reason.lower()
    return "unknown adapter or persona" in lowered
