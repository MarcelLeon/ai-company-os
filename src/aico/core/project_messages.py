"""Text rendering helpers for project office commands."""

from __future__ import annotations

from datetime import timedelta

from aico.core.models import (
    AuditEvent,
    AuditEventType,
    MessageContent,
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
    return MessageContent(text="\n".join(lines))


def project_office_message(
    project: ProjectProfile,
    appointments: tuple[AssignmentProfile, ...],
    default_appointment: AssignmentProfile | None,
) -> MessageContent:
    default_text = _appointment_ref(default_appointment)
    lines = [
        f"Project active: {project.id} [{project.name}]",
        f"repo: {project.repo}",
        f"default role: {default_text}",
    ]
    if project.current_phase:
        lines.append(f"phase: {project.current_phase}")
    lines.append("")
    lines.append("Team:")
    if appointments:
        lines.extend(f"- {_appointment_ref(appointment)}" for appointment in appointments)
    else:
        lines.append("- none")
    return MessageContent(text="\n".join(lines))


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
    return MessageContent(text="\n".join(lines))


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
        return MessageContent(text="\n".join(lines))
    if task_risks or audit_risks:
        lines.extend(("", "delivery risks:"))
        lines.extend(task_risks)
        lines.extend(audit_risks)
    if documented_risks:
        lines.extend(("", "documented blockers / pitfalls:"))
        lines.extend(documented_risks)
    return MessageContent(text="\n".join(lines))


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
        return MessageContent(text="\n".join(lines))
    if decision_lines:
        lines.extend(("", "waiting decisions:"))
        lines.extend(decision_lines)
    if failed_lines:
        lines.extend(("", "failed / rejected work:"))
        lines.extend(failed_lines)
    if document_lines:
        lines.extend(("", "documented blockers:"))
        lines.extend(document_lines)
    return MessageContent(text="\n".join(lines))


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
    return MessageContent(text="\n".join(lines))


def roles_message(
    project: ProjectProfile,
    roles: tuple[RoleProfile, ...],
    appointments: tuple[AssignmentProfile, ...],
) -> MessageContent:
    if not roles:
        return MessageContent(text=f"No roles configured for {project.id}")
    appointments_by_role = {appointment.role: appointment for appointment in appointments}
    project_role_ids = {role.id for role in roles}
    lines = [f"Roles for {project.id} [{project.name}]:"]
    for role in roles:
        if role.id not in project_role_ids and role.id not in appointments_by_role:
            continue
        appointment = appointments_by_role.get(role.id)
        owner = "unappointed" if appointment is None else appointment.agent
        permissions = ", ".join(role.default_permissions) or "-"
        summary = f" - {role.summary}" if role.summary else ""
        lines.append(f"- {role.id}: {role.title} -> {owner}")
        lines.append(f"  permissions: {permissions}")
        if summary:
            lines.append(f"  summary:{summary}")
    return MessageContent(text="\n".join(lines))


def role_proposal_message(project: ProjectProfile, role: RoleProfile) -> MessageContent:
    permissions = ", ".join(role.default_permissions) or "-"
    approval_required = ", ".join(role.approval_required) or "-"
    return MessageContent(
        text=(
            f"Role proposal for {project.id}\n"
            f"id: {role.id}\n"
            f"title: {role.title}\n"
            f"summary: {role.summary or '-'}\n"
            f"permissions: {permissions}\n"
            f"approval_required: {approval_required}\n"
            f"prompt: {role.inline_prompt or '-'}\n\n"
            "Send /role confirm to add it to this project, or /role discard to cancel."
        )
    )


def role_added_message(project: ProjectProfile, role: RoleProfile) -> MessageContent:
    return MessageContent(
        text=(
            f"Role added to {project.id}: {role.id}\n"
            f"title: {role.title}\n"
            "Use /roles to review it, then /appoint <agent> as "
            f"{role.id} [permissions] when ready."
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
    return MessageContent(text="\n".join(lines))


def team_message(
    project: ProjectProfile,
    appointments: tuple[AssignmentProfile, ...],
    default_appointment: AssignmentProfile | None = None,
) -> MessageContent:
    if not appointments:
        return MessageContent(text=f"No team appointments for {project.id}")
    lines = [f"Team for {project.id}:"]
    if default_appointment is not None:
        lines.append(f"lead: {_appointment_ref(default_appointment)}")
    for appointment in appointments:
        permissions = ", ".join(appointment.permissions) or appointment.risk_policy
        lead_marker = " [lead]" if _same_appointment(appointment, default_appointment) else ""
        lines.append(f"- {appointment.role} -> {appointment.agent} ({permissions}){lead_marker}")
    return MessageContent(text="\n".join(lines))


def who_message(
    project: ProjectProfile,
    appointment: AssignmentProfile,
    agent: CompanyAgentProfile | None,
    role: RoleProfile | None,
) -> MessageContent:
    title = "-" if role is None else role.title
    agent_title = "-" if agent is None else agent.title
    permissions = ", ".join(appointment.permissions) or appointment.risk_policy
    workspace = appointment.workspace or project.repo
    return MessageContent(
        text=(
            f"{project.id} / {appointment.role}\n"
            f"agent: {appointment.agent}\n"
            f"title: {agent_title}\n"
            f"role_title: {title}\n"
            f"permissions: {permissions}\n"
            f"workspace: {workspace}\n"
            f"seat: {appointment.seat}"
        )
    )


def appointment_created_message(
    project: ProjectProfile,
    appointment: AssignmentProfile,
    agent: CompanyAgentProfile | None,
    role: RoleProfile | None,
) -> MessageContent:
    agent_title = "-" if agent is None else agent.title
    role_title = appointment.role if role is None else role.title
    permissions = ", ".join(appointment.permissions) or appointment.risk_policy
    return MessageContent(
        text=(
            "Appointment active\n\n"
            f"{appointment.agent} is appointed to {project.id} as {appointment.role}.\n"
            f"agent_title: {agent_title}\n"
            f"role: {role_title}\n"
            f"workspace: {appointment.workspace or project.repo}\n"
            f"permissions: {permissions}\n"
            f"seat: {appointment.seat}"
        )
    )


def appointment_removed_message(
    project: ProjectProfile, appointment: AssignmentProfile
) -> MessageContent:
    return MessageContent(
        text=(
            "Appointment removed\n\n"
            f"{appointment.agent} is no longer appointed to {project.id} as "
            f"{appointment.role}.\n"
            f"seat: {appointment.seat}"
        )
    )


def default_role_message(project: ProjectProfile, appointment: AssignmentProfile) -> MessageContent:
    return MessageContent(
        text=(
            f"Lead role for {project.id}: {appointment.role} -> {appointment.agent}\n"
            "Plain messages will go to this lead role."
        )
    )


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
            "- Appoint an implementer: "
            "/appoint claude as implementer read_repo write_code run_tests",
            "- Appoint a reviewer when available: /appoint codex as reviewer readonly",
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
