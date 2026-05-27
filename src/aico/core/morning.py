"""Morning handoff for absence-first project recovery."""

from __future__ import annotations

from aico.core.command_messages import short_id_text
from aico.core.message_rendering import rich_text_message
from aico.core.models import AuditEvent, MessageContent, RiskLevel, TaskSnapshot, TaskStatus
from aico.core.offline_delegation import OfflineDelegationRecord

_PROJECT_ID_KEY = "aico.project_id"


def morning_message(
    *,
    project_id: str,
    task_snapshots: tuple[TaskSnapshot, ...],
    overnight_records: tuple[OfflineDelegationRecord, ...] = (),
    audit_events: tuple[AuditEvent, ...] = (),
) -> MessageContent:
    scoped_tasks = _scoped_tasks(task_snapshots, project_id)
    lines = [f"Morning handoff: {project_id}", f"scope: current project ({project_id})"]
    lines.extend(_done_lines(scoped_tasks))
    lines.extend(_blocked_lines(scoped_tasks))
    lines.extend(_risk_lines(scoped_tasks, audit_events))
    lines.extend(_handoff_lines(overnight_records))
    lines.extend(_next_action_lines(scoped_tasks, overnight_records))
    return rich_text_message("\n".join(lines))


def _done_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> list[str]:
    done = tuple(snapshot for snapshot in task_snapshots if snapshot.status is TaskStatus.DONE)
    lines = ["", "Done:"]
    if not done:
        lines.append("- none")
        return lines
    lines.extend(
        f"- {short_id_text(snapshot.task_id)} [{snapshot.target_persona}] done"
        for snapshot in done[-6:]
    )
    return lines


def _blocked_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> list[str]:
    blocked_statuses = {
        TaskStatus.WAITING_APPROVAL,
        TaskStatus.FAILED,
        TaskStatus.INTERRUPTED,
        TaskStatus.REJECTED,
    }
    blocked = tuple(snapshot for snapshot in task_snapshots if snapshot.status in blocked_statuses)
    lines = ["", "Blocked:"]
    if not blocked:
        lines.append("- none")
        return lines
    lines.extend(_blocked_line(snapshot) for snapshot in blocked[:8])
    return lines


def _risk_lines(
    task_snapshots: tuple[TaskSnapshot, ...],
    audit_events: tuple[AuditEvent, ...],
) -> list[str]:
    task_ids = {snapshot.task_id for snapshot in task_snapshots}
    risky_events = tuple(
        event
        for event in audit_events
        if event.task_id in task_ids and event.risk_level is not RiskLevel.READ_ONLY
    )
    risky_tasks = tuple(
        snapshot for snapshot in task_snapshots if snapshot.risk_level is not RiskLevel.READ_ONLY
    )
    lines = ["", "Risks:"]
    if not risky_events and not risky_tasks:
        lines.append("- none")
        return lines
    seen: set[str] = set()
    for snapshot in risky_tasks[-6:]:
        seen.add(snapshot.task_id)
        reason = f" - {snapshot.reason}" if snapshot.reason else ""
        lines.append(
            f"- {short_id_text(snapshot.task_id)} [{snapshot.risk_level.value}] "
            f"{snapshot.status.value}{reason}"
        )
    for event in risky_events[-6:]:
        if event.task_id in seen:
            continue
        detail = f" - {event.detail}" if event.detail else ""
        lines.append(
            f"- {short_id_text(event.task_id)} [{event.risk_level.value}] "
            f"{event.event_type.value}{detail}"
        )
    return lines


def _handoff_lines(records: tuple[OfflineDelegationRecord, ...]) -> list[str]:
    lines = ["", "Overnight handoffs:"]
    if not records:
        lines.append("- none")
        return lines
    lines.extend(
        f"- {record.delegation_id}: {record.role} -> {record.agent} "
        f"({short_id_text(record.task_id)}) {record.goal}"
        for record in records[-5:]
    )
    return lines


def _next_action_lines(
    task_snapshots: tuple[TaskSnapshot, ...],
    overnight_records: tuple[OfflineDelegationRecord, ...],
) -> list[str]:
    actions: list[str] = []
    for snapshot in task_snapshots:
        short_id = short_id_text(snapshot.task_id)
        if snapshot.status is TaskStatus.WAITING_APPROVAL:
            actions.append(f"/approve {short_id} or /reject {short_id}")
        elif snapshot.status in {TaskStatus.FAILED, TaskStatus.INTERRUPTED, TaskStatus.REJECTED}:
            actions.append(f"/task {short_id}")
        elif snapshot.status is TaskStatus.RUNNING:
            actions.append(f"/task {short_id} or /interrupt {short_id}")
    actions.extend(f"/task {short_id_text(record.task_id)}" for record in overnight_records[-3:])
    actions.extend(("/inbox", "/dream"))
    lines = ["", "Next actions:"]
    for action in _dedupe(actions)[:8]:
        lines.append(f"- {action}")
    return lines


def _blocked_line(snapshot: TaskSnapshot) -> str:
    short_id = short_id_text(snapshot.task_id)
    reason = f" - {snapshot.reason}" if snapshot.reason else ""
    if snapshot.status is TaskStatus.WAITING_APPROVAL:
        return f"- {short_id} waiting approval{reason} -> /approve {short_id} or /reject {short_id}"
    return f"- {short_id} {snapshot.status.value}{reason} -> /task {short_id}"


def _scoped_tasks(
    task_snapshots: tuple[TaskSnapshot, ...],
    project_id: str,
) -> tuple[TaskSnapshot, ...]:
    scoped = tuple(
        snapshot
        for snapshot in task_snapshots
        if _metadata_value(snapshot, _PROJECT_ID_KEY) == project_id
    )
    return tuple(sorted(scoped, key=lambda snapshot: snapshot.updated_at))


def _metadata_value(snapshot: TaskSnapshot, key: str) -> str | None:
    for entry in snapshot.metadata:
        if entry.key == key and entry.value is not None:
            return str(entry.value)
    return None


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return tuple(deduped)
