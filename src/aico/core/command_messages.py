"""Text rendering helpers for built-in IM commands."""

from __future__ import annotations

from aico.core.agent_session import AgentCard
from aico.core.metrics import MetricsReport, MetricsSummary, build_metrics_report
from aico.core.models import (
    AckStatus,
    AdapterSnapshot,
    AuditEvent,
    AuditEventType,
    MessageContent,
    RiskLevel,
    TaskSnapshot,
    TaskStatus,
)

SKILLS_PROMPT = (
    "List the skills currently available to you in this provider CLI/session. "
    "Only describe skills you can actually use now, include important limits, "
    "and do not take actions beyond answering."
)
TOOLS_PROMPT = (
    "List the tools currently available to you in this provider CLI/session. "
    "Only describe tools you can actually call now, include important limits, "
    "and do not take actions beyond answering."
)


def ack_failure_message(status: AckStatus, reason: str | None) -> MessageContent:
    reason_text = f": {reason}" if reason else ""
    return MessageContent(text=f"Task {status.value}{reason_text}")


def approval_required_message(task_id: str, reason: str | None) -> MessageContent:
    reason_text = f"\n{reason}" if reason else ""
    short_id = short_id_text(task_id)
    return MessageContent(
        text=(
            f"Approval required: {short_id}{reason_text}\n"
            "Send /approve to continue, or /reject to stop.\n"
            f"If several approvals are pending, use /approve {short_id}."
        )
    )


def status_message(
    adapter_snapshots: tuple[AdapterSnapshot, ...],
    task_snapshots: tuple[TaskSnapshot, ...],
) -> MessageContent:
    lines = [f"{snapshot.name}: {_adapter_status_text(snapshot)}" for snapshot in adapter_snapshots]
    if task_snapshots:
        lines.append("")
        lines.append("Recent tasks:")
        lines.extend(_task_status_line(snapshot) for snapshot in task_snapshots)
    return MessageContent(text="\n".join(lines))


def tasks_message(task_snapshots: tuple[TaskSnapshot, ...]) -> MessageContent:
    if not task_snapshots:
        return MessageContent(text="No recent tasks")
    lines = ["Recent tasks:"]
    lines.extend(_task_status_line(snapshot) for snapshot in task_snapshots)
    lines.append("")
    lines.append("Use /task <task_id> for details.")
    return MessageContent(text="\n".join(lines))


def metrics_message(
    task_snapshots: tuple[TaskSnapshot, ...],
    audit_events: tuple[AuditEvent, ...],
) -> MessageContent:
    report = build_metrics_report(task_snapshots, audit_events)
    return MessageContent(text=metrics_report_text(report))


def metrics_report_text(report: MetricsReport) -> str:
    blocks = [
        f"Metrics ({report.source_label})",
        _metrics_glance_block(report),
    ]
    blocks.extend(_metrics_window_block(summary) for summary in report.summaries)
    blocks.append(_token_cost_line(report))
    return "\n\n".join(blocks)


def task_detail_message(
    snapshot: TaskSnapshot,
    audit_events: tuple[AuditEvent, ...] = (),
) -> MessageContent:
    short_id = short_id_text(snapshot.task_id)
    lines = [
        f"Task: {short_id}",
        f"id: {snapshot.task_id}",
        f"target: {snapshot.target_persona}",
        f"adapter: {snapshot.adapter_name or '-'}",
        f"status: {snapshot.status.value}",
        f"risk: {snapshot.risk_level.value}",
        f"created: {snapshot.created_at.isoformat()}",
        f"updated: {snapshot.updated_at.isoformat()}",
    ]
    if snapshot.reason:
        lines.append(f"reason: {snapshot.reason}")
    collaboration_lines = _task_collaboration_lines(snapshot, audit_events)
    if collaboration_lines:
        lines.append("")
        lines.append("Collaboration:")
        lines.extend(collaboration_lines)
    actions = _task_action_lines(snapshot, short_id)
    if actions:
        lines.append("")
        lines.append("Actions:")
        lines.extend(actions)
    return MessageContent(text="\n".join(lines))


def audit_message(events: tuple[AuditEvent, ...]) -> MessageContent:
    if not events:
        return MessageContent(text="No audit events")
    blocks = ["Recent audit events:"]
    blocks.extend(_audit_event_block(event) for event in events)
    return MessageContent(text="\n\n".join(blocks))


def agent_list_message(
    cards: tuple[AgentCard, ...],
    adapter_snapshots: tuple[AdapterSnapshot, ...],
) -> MessageContent:
    if not cards:
        return MessageContent(text="No agents")
    statuses = _adapter_statuses(adapter_snapshots)
    lines = ["Agents:"]
    lines.extend(
        _agent_list_line(card, statuses.get(card.adapter_name, "unknown")) for card in cards
    )
    lines.extend(_next_lines(("/agent <agent>", "/roles", "/appoint <agent> as <role>")))
    return MessageContent(text="\n".join(lines))


def agent_card_message(
    card: AgentCard,
    adapter_snapshots: tuple[AdapterSnapshot, ...],
) -> MessageContent:
    statuses = _adapter_statuses(adapter_snapshots)
    capabilities = ", ".join(sorted(capability.value for capability in card.capabilities)) or "-"
    aliases = ", ".join(card.aliases) or "-"
    sessions = ", ".join(card.session_features) or "-"
    display_name = _agent_display_name(card)
    role = card.name if display_name != card.name else card.role_description
    status = statuses.get(card.adapter_name, "unknown")
    next_lines = _agent_next_lines(display_name, status)
    return MessageContent(
        text=(
            f"Agent: {display_name}\n"
            f"adapter: {card.adapter_name}\n"
            f"provider: {card.provider_name}\n"
            f"status: {status}\n"
            f"max_concurrent: {card.max_concurrent_tasks}\n"
            f"recommended_appointments: <= {card.max_concurrent_tasks}\n"
            f"role: {role}\n"
            f"aliases: {aliases}\n"
            f"capabilities: {capabilities}\n"
            f"tools: {card.tools_source.value} via /tools {display_name}\n"
            f"skills: {card.skills_source.value} via /skills {display_name}\n"
            f"sessions: {sessions}"
            f"{next_lines}"
        )
    )


def _agent_list_line(card: AgentCard, status: str) -> str:
    display_name = _agent_display_name(card)
    role = f" [role: {card.name}]" if display_name != card.name else ""
    capacity = f", max {card.max_concurrent_tasks} concurrent"
    return f"- {display_name} -> {card.adapter_name} ({status}{capacity}){role}"


def _agent_display_name(card: AgentCard) -> str:
    if card.name in {"implementer", "reviewer"} and card.aliases:
        return card.aliases[0]
    return card.name


def _agent_next_lines(agent_name: str, status: str) -> str:
    if status.startswith(("idle", "available")):
        commands = ("/roles", f"/appoint {agent_name} as <role>", f"/new {agent_name}")
    else:
        commands = ("/tasks", "/status", f"/agent {agent_name}")
    return "\n" + "\n".join(_next_lines(commands))


def _next_lines(commands: tuple[str, ...]) -> tuple[str, ...]:
    return ("", "Next:", *(f"- {command}" for command in commands))


def short_id_text(value: str) -> str:
    return value[:8]


def _metrics_window_block(summary: MetricsSummary) -> str:
    lines = [
        summary.window.label,
        f"tasks: {summary.total_tasks}",
        f"status: {_status_count_text(summary)}",
        f"agents: {_adapter_count_text(summary)}",
        f"collaboration: {summary.collaboration_requests}",
        f"avg terminal duration: {_duration_text(summary.avg_terminal_seconds)}",
        "open work:",
    ]
    lines.extend(_metrics_open_work_lines(summary.open_tasks))
    return "\n".join(lines)


def _metrics_glance_block(report: MetricsReport) -> str:
    return (
        "glance\n"
        f"status: {report.glance.status}\n"
        f"open: {report.glance.open_tasks} "
        f"(running={report.glance.running_tasks}, "
        f"waiting_approval={report.glance.waiting_approval_tasks})\n"
        f"failed: {report.glance.failed_tasks}"
    )


def _token_cost_line(report: MetricsReport) -> str:
    token_cost = report.token_cost
    if not token_cost.available:
        return f"token/cost: {token_cost.reason}"
    cost = "-" if token_cost.cost_usd is None else f"${token_cost.cost_usd:.4f}"
    return (
        "token/cost: "
        f"total={token_cost.total_tokens}, "
        f"input={token_cost.input_tokens}, "
        f"output={token_cost.output_tokens}, "
        f"cost={cost}"
    )


def _status_count_text(summary: MetricsSummary) -> str:
    return ", ".join(f"{status.value}={count}" for status, count in summary.status_counts)


def _adapter_count_text(summary: MetricsSummary) -> str:
    if not summary.adapter_counts:
        return "-"
    return ", ".join(f"{adapter}={count}" for adapter, count in summary.adapter_counts)


def _duration_text(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    return f"{seconds:.0f}s"


def _metrics_open_work_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[str, ...]:
    if not task_snapshots:
        return ("- none",)
    return tuple(f"- {_task_status_line(snapshot)}" for snapshot in task_snapshots)


def _task_status_line(snapshot: TaskSnapshot) -> str:
    adapter_name = snapshot.adapter_name or snapshot.target_persona
    line = f"{snapshot.task_id} [{adapter_name}]: {snapshot.status.value}"
    if snapshot.risk_level is not RiskLevel.READ_ONLY:
        line = f"{line} ({snapshot.risk_level.value})"
    if snapshot.reason:
        line = f"{line} - {snapshot.reason}"
    return line


def _task_action_lines(snapshot: TaskSnapshot, short_id: str) -> tuple[str, ...]:
    if snapshot.status is TaskStatus.RUNNING:
        return (f"- /interrupt {short_id}",)
    if snapshot.status is TaskStatus.WAITING_APPROVAL:
        return (f"- /approve {short_id}", f"- /reject {short_id}")
    return ()


def _task_collaboration_lines(
    snapshot: TaskSnapshot,
    audit_events: tuple[AuditEvent, ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    parent_event = next(
        (
            event
            for event in audit_events
            if event.event_type is AuditEventType.COLLABORATION_REQUESTED
            and event.task_id == snapshot.task_id
        ),
        None,
    )
    if parent_event is not None:
        parent_id = _collaboration_parent_task_id(parent_event)
        lines.append(f"- requested by: {parent_event.actor_id}")
        if parent_id is not None:
            parent_short_id = short_id_text(parent_id)
            lines.append(f"- parent: {parent_short_id} (/task {parent_short_id})")

    child_lines = tuple(_collaboration_child_lines(snapshot, audit_events))
    if child_lines:
        lines.append("- children:")
        lines.extend(f"  - {line}" for line in child_lines)
    return tuple(lines)


def _collaboration_child_lines(
    snapshot: TaskSnapshot,
    audit_events: tuple[AuditEvent, ...],
) -> tuple[str, ...]:
    lines: list[str] = []
    for event in audit_events:
        if event.event_type is not AuditEventType.COLLABORATION_REQUESTED:
            continue
        if _collaboration_parent_task_id(event) != snapshot.task_id:
            continue
        child_short_id = short_id_text(event.task_id)
        lines.append(f"{child_short_id} -> {event.target_persona} (/task {child_short_id})")
    return tuple(lines)


def _collaboration_parent_task_id(event: AuditEvent) -> str | None:
    if event.detail is None:
        return None
    key, separator, value = event.detail.partition("=")
    if key != "parent_task" or not separator or not value:
        return None
    return value.strip() or None


def _audit_event_block(event: AuditEvent) -> str:
    lines = [
        f"- {event.event_type.value}",
        f"  id: {event.event_id}",
        f"  task: {event.task_id}",
        f"  actor: {event.actor_id}",
        f"  target: {event.target_persona}",
        f"  risk: {event.risk_level.value}",
    ]
    if event.adapter_name:
        lines.append(f"  adapter: {event.adapter_name}")
    if event.detail:
        lines.append(f"  detail: {event.detail}")
    return "\n".join(lines)


def _adapter_statuses(adapter_snapshots: tuple[AdapterSnapshot, ...]) -> dict[str, str]:
    return {snapshot.name: _adapter_status_text(snapshot) for snapshot in adapter_snapshots}


def _adapter_status_text(snapshot: AdapterSnapshot) -> str:
    label = snapshot.status.value
    if snapshot.running_tasks and snapshot.running_tasks < snapshot.max_concurrent_tasks:
        label = "available"
    return f"{label} {snapshot.running_tasks}/{snapshot.max_concurrent_tasks} running"
