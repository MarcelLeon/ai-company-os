"""Boss-facing inbox for absence-first project handoff."""

from __future__ import annotations

from datetime import datetime

from aico.core.message_rendering import rich_text_message
from aico.core.models import AuditEvent, MessageContent, TaskSnapshot, TaskStatus, utc_now
from aico.core.offline_delegation import OfflineDelegationRecord

_PROJECT_ID_KEY = "aico.project_id"
_INTENT_KEY = "aico.intent"
_GOAL_INTENT = "goal_brief"
_LEAD_DECISION_INTENT = "lead_decision"
_OUTCOME_GRADER_INTENT = "outcome_grader"


def inbox_message(
    *,
    project_id: str,
    task_snapshots: tuple[TaskSnapshot, ...],
    overnight_records: tuple[OfflineDelegationRecord, ...] = (),
    audit_events: tuple[AuditEvent, ...] = (),
) -> MessageContent:
    scoped_tasks = _scoped_tasks(task_snapshots, project_id)
    lines = [f"Inbox: {project_id}", f"scope: current project ({project_id})"]
    lines.extend(_first_action_lines(scoped_tasks, overnight_records, audit_events))
    lines.extend(_needs_attention_lines(scoped_tasks))
    lines.extend(_running_lines(scoped_tasks))
    lines.extend(_handoff_lines(overnight_records))
    lines.extend(_decision_goal_lines(scoped_tasks))
    lines.extend(_collaboration_lines(audit_events, scoped_tasks))
    lines.append("")
    lines.append("Next:")
    lines.append("- /inbox")
    lines.append(f"- /daily {project_id}")
    lines.append("- /tasks")
    lines.append("- /audit")
    return rich_text_message("\n".join(lines))


def _first_action_lines(
    task_snapshots: tuple[TaskSnapshot, ...],
    overnight_records: tuple[OfflineDelegationRecord, ...],
    audit_events: tuple[AuditEvent, ...],
) -> list[str]:
    action = _first_action(task_snapshots, overnight_records, audit_events)
    lines = ["", "First action:"]
    lines.append(f"- {action}" if action else "- none")
    return lines


def _first_action(
    task_snapshots: tuple[TaskSnapshot, ...],
    overnight_records: tuple[OfflineDelegationRecord, ...],
    audit_events: tuple[AuditEvent, ...],
) -> str | None:
    for snapshot in task_snapshots:
        if snapshot.status is TaskStatus.WAITING_APPROVAL:
            short_id = _short_id(snapshot.task_id)
            return f"decide {short_id} -> /approve {short_id} or /reject {short_id}"
    for snapshot in task_snapshots:
        if snapshot.status in {TaskStatus.FAILED, TaskStatus.INTERRUPTED, TaskStatus.REJECTED}:
            short_id = _short_id(snapshot.task_id)
            return f"recover {short_id} -> /task {short_id}"
    for snapshot in task_snapshots:
        if snapshot.status is TaskStatus.RUNNING:
            short_id = _short_id(snapshot.task_id)
            return f"monitor {short_id} -> /task {short_id} or /interrupt {short_id}"
    if overnight_records:
        record = overnight_records[-1]
        return f"inspect handoff {_short_id(record.task_id)} -> /task {_short_id(record.task_id)}"
    collaboration = _collaboration_events(audit_events, task_snapshots)
    if collaboration:
        short_id = _short_id(collaboration[-1].task_id)
        return f"follow collaboration {short_id} -> /task {short_id}"
    return None


def _needs_attention_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> list[str]:
    tasks = tuple(
        snapshot
        for snapshot in task_snapshots
        if snapshot.status
        in {
            TaskStatus.WAITING_APPROVAL,
            TaskStatus.FAILED,
            TaskStatus.INTERRUPTED,
            TaskStatus.REJECTED,
        }
    )
    lines = ["", "Needs attention:"]
    if not tasks:
        lines.append("- none")
        return lines
    lines.extend(_attention_line(snapshot) for snapshot in tasks[:8])
    return lines


def _running_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> list[str]:
    running = tuple(
        snapshot for snapshot in task_snapshots if snapshot.status is TaskStatus.RUNNING
    )
    lines = ["", "Running:"]
    if not running:
        lines.append("- none")
        return lines
    lines.extend(_running_line(snapshot) for snapshot in running[:8])
    return lines


def _handoff_lines(records: tuple[OfflineDelegationRecord, ...]) -> list[str]:
    lines = ["", "Morning handoff:"]
    if not records:
        lines.append("- none")
        return lines
    lines.extend(
        f"- inspect handoff {record.delegation_id}: {record.role} -> {record.agent} "
        f"({_short_id(record.task_id)}) {record.goal} -> /task {_short_id(record.task_id)}"
        for record in records[-5:]
    )
    return lines


def _decision_goal_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> list[str]:
    tasks = tuple(
        snapshot
        for snapshot in task_snapshots
        if _metadata_value(snapshot, _INTENT_KEY)
        in {_GOAL_INTENT, _LEAD_DECISION_INTENT, _OUTCOME_GRADER_INTENT}
    )
    lines = ["", "Decision / goal follow-up:"]
    if not tasks:
        lines.append("- none")
        return lines
    lines.extend(_decision_goal_line(snapshot) for snapshot in tasks[-8:])
    return lines


def _collaboration_lines(
    audit_events: tuple[AuditEvent, ...],
    task_snapshots: tuple[TaskSnapshot, ...],
) -> list[str]:
    events = _collaboration_events(audit_events, task_snapshots)
    lines = ["", "Collaboration follow-up:"]
    if not events:
        lines.append("- none")
        return lines
    lines.extend(
        f"- follow {event.actor_id} -> {event.target_persona}: {_short_id(event.task_id)} "
        f"-> /task {_short_id(event.task_id)}"
        for event in events[-8:]
    )
    return lines


def _collaboration_events(
    audit_events: tuple[AuditEvent, ...],
    task_snapshots: tuple[TaskSnapshot, ...],
) -> tuple[AuditEvent, ...]:
    task_ids = {snapshot.task_id for snapshot in task_snapshots}
    return tuple(
        event
        for event in audit_events
        if event.event_type.value == "collaboration_requested" and event.task_id in task_ids
    )


def _attention_line(snapshot: TaskSnapshot) -> str:
    short_id = _short_id(snapshot.task_id)
    reason = f" - {snapshot.reason}" if snapshot.reason else ""
    if snapshot.status is TaskStatus.WAITING_APPROVAL:
        return (
            f"- decide {short_id} [{snapshot.target_persona}]"
            f"{reason} -> /approve {short_id} or /reject {short_id}"
        )
    return (
        f"- recover {short_id} [{snapshot.target_persona}] {snapshot.status.value}"
        f"{reason} -> /task {short_id}"
    )


def _running_line(snapshot: TaskSnapshot) -> str:
    short_id = _short_id(snapshot.task_id)
    reason = f" - {snapshot.reason}" if snapshot.reason else ""
    adapter = snapshot.adapter_name or snapshot.target_persona
    return (
        f"- monitor {short_id} [{snapshot.target_persona}/{adapter}] "
        f"running for {_duration(utc_now(), snapshot.created_at)}{reason} "
        f"-> /task {short_id} or /interrupt {short_id}"
    )


def _decision_goal_line(snapshot: TaskSnapshot) -> str:
    short_id = _short_id(snapshot.task_id)
    intent = _metadata_value(snapshot, _INTENT_KEY) or "-"
    return f"- inspect {intent}: {short_id} [{snapshot.status.value}] -> /task {short_id}"


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


def _duration(now: datetime, started_at: datetime) -> str:
    seconds = max(0, int((now - started_at).total_seconds()))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    return f"{hours}h{minutes % 60:02d}m"


def _short_id(value: str) -> str:
    return value[:8]
