"""Text rendering helpers for built-in IM commands."""

from __future__ import annotations

from aico.core.agent_session import AgentCard
from aico.core.models import (
    AckStatus,
    AdapterSnapshot,
    AuditEvent,
    MessageContent,
    RiskLevel,
    TaskSnapshot,
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
    lines = [f"{snapshot.name}: {snapshot.status.value}" for snapshot in adapter_snapshots]
    if task_snapshots:
        lines.append("")
        lines.append("Recent tasks:")
        lines.extend(_task_status_line(snapshot) for snapshot in task_snapshots)
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
        f"- {card.name} -> {card.adapter_name} ({statuses.get(card.adapter_name, 'unknown')})"
        for card in cards
    )
    return MessageContent(text="\n".join(lines))


def agent_card_message(
    card: AgentCard,
    adapter_snapshots: tuple[AdapterSnapshot, ...],
) -> MessageContent:
    statuses = _adapter_statuses(adapter_snapshots)
    capabilities = ", ".join(sorted(capability.value for capability in card.capabilities)) or "-"
    aliases = ", ".join(card.aliases) or "-"
    sessions = ", ".join(card.session_features) or "-"
    return MessageContent(
        text=(
            f"Agent: {card.name}\n"
            f"adapter: {card.adapter_name}\n"
            f"provider: {card.provider_name}\n"
            f"status: {statuses.get(card.adapter_name, 'unknown')}\n"
            f"role: {card.role_description}\n"
            f"aliases: {aliases}\n"
            f"capabilities: {capabilities}\n"
            f"tools: {card.tools_source.value} via /tools {card.name}\n"
            f"skills: {card.skills_source.value} via /skills {card.name}\n"
            f"sessions: {sessions}"
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
    return {snapshot.name: snapshot.status.value for snapshot in adapter_snapshots}
