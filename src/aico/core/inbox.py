"""Boss-facing inbox for absence-first project handoff."""

from __future__ import annotations

from datetime import datetime

from aico.core.command_messages import task_error_summary
from aico.core.memory import MemoryAtom
from aico.core.message_rendering import rich_text_message
from aico.core.models import AuditEvent, MessageContent, TaskSnapshot, TaskStatus, utc_now
from aico.core.offline_delegation import OfflineDelegationRecord
from aico.core.standing_autonomy import (
    StandingAutonomyOutcomeStatus,
    StandingAutonomyReceipt,
    StandingAutonomyReceiptStatus,
)
from aico.core.standing_proposal import StandingProposal
from aico.core.unified_event import UnifiedEvent

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
    recent_events: tuple[UnifiedEvent, ...] = (),
    experience_candidates: tuple[MemoryAtom, ...] = (),
    standing_proposals: tuple[StandingProposal, ...] = (),
    standing_autonomy_receipts: tuple[StandingAutonomyReceipt, ...] = (),
) -> MessageContent:
    scoped_tasks = _scoped_tasks(task_snapshots, project_id)
    action = _first_action(
        scoped_tasks,
        overnight_records,
        audit_events,
        experience_candidates,
        standing_proposals,
        standing_autonomy_receipts,
    )
    lines = [f"Inbox: {project_id}", "范围: 当前项目"]
    if action is None:
        lines.extend(("", "当前无待处理事项。"))
        lines.extend(_autonomy_receipt_section(standing_autonomy_receipts))
        lines.extend(("", "下一步:", f"- /daily {project_id}", "- /view"))
        return rich_text_message("\n".join(lines))

    lines.extend(("", "下一步:", f"- {action}"))
    attention = _attention_items(scoped_tasks)
    if attention:
        lines.extend(("", "需要关注:", *(_attention_line(snapshot) for snapshot in attention[:3])))
    running = _running_items(scoped_tasks)
    if running:
        lines.extend(("", "运行中:", *(_running_line(snapshot) for snapshot in running[:3])))
    handoffs = _handoff_items(overnight_records)
    if handoffs:
        lines.extend(("", "交接:", *handoffs[:3]))
    followups = _decision_goal_items(scoped_tasks)
    if followups:
        lines.extend(
            (
                "",
                "可深挖:",
                *(_decision_goal_line(snapshot) for snapshot in followups[-3:]),
            )
        )
    proposal_lines = _standing_proposal_lines(standing_proposals)
    if proposal_lines:
        lines.extend(("", "主动提案:", *proposal_lines))
    lines.extend(_autonomy_receipt_section(standing_autonomy_receipts))
    candidate_lines = _experience_candidate_lines(experience_candidates)
    if candidate_lines:
        lines.extend(("", "经验候选:", *candidate_lines))
    lines.extend(("", "更多:", f"- /daily {project_id}", "- /tasks", "- /view"))
    return rich_text_message("\n".join(lines))


def _recent_activity_lines(events: tuple[UnifiedEvent, ...]) -> list[str]:
    if not events:
        return []
    lines = ["", "Recent activity:"]
    for event in events:
        ts = event.timestamp.strftime("%H:%M")
        lines.append(
            f"- {ts} [{event.source.value}] {event.kind} {event.short_id} — "
            f"{task_error_summary(event.summary)}"
        )
    lines.append("- ask /why <short_id> for the full trace")
    return lines


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
    experience_candidates: tuple[MemoryAtom, ...] = (),
    standing_proposals: tuple[StandingProposal, ...] = (),
    standing_autonomy_receipts: tuple[StandingAutonomyReceipt, ...] = (),
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
    for receipt in reversed(standing_autonomy_receipts):
        unhealthy_outcome = receipt.outcome_status in {
            StandingAutonomyOutcomeStatus.MISSING,
            StandingAutonomyOutcomeStatus.BLOCKED,
            StandingAutonomyOutcomeStatus.INVALID,
            StandingAutonomyOutcomeStatus.DRIFTED,
        }
        if not unhealthy_outcome and receipt.status not in {
            StandingAutonomyReceiptStatus.EVIDENCE_MISSING,
            StandingAutonomyReceiptStatus.FAILED,
            StandingAutonomyReceiptStatus.INTERRUPTED,
            StandingAutonomyReceiptStatus.REJECTED,
        }:
            continue
        if receipt.task_id:
            task_id = _short_id(receipt.task_id)
            return f"recover autonomy {task_id} -> /task {task_id}"
        proposal_id = _short_id(receipt.proposal_id)
        return f"inspect autonomy {proposal_id} -> /proposals"
    for receipt in reversed(standing_autonomy_receipts):
        if receipt.status is StandingAutonomyReceiptStatus.RUNNING and receipt.task_id:
            task_id = _short_id(receipt.task_id)
            return f"monitor autonomy {task_id} -> /task {task_id} or /interrupt {task_id}"
    if overnight_records:
        record = overnight_records[-1]
        return f"inspect handoff {_short_id(record.task_id)} -> /task {_short_id(record.task_id)}"
    collaboration = _collaboration_events(audit_events, task_snapshots)
    if collaboration:
        short_id = _short_id(collaboration[-1].task_id)
        return f"follow collaboration {short_id} -> /task {short_id}"
    if standing_proposals:
        proposal_id = _short_id(standing_proposals[0].proposal_id)
        return (
            f"decide proposal {proposal_id} -> /proposal accept {proposal_id} "
            f"or /proposal reject {proposal_id}"
        )
    if experience_candidates:
        candidate = experience_candidates[0]
        return f"review experience {candidate.memory_id} -> /experience review"
    return None


def _standing_proposal_lines(proposals: tuple[StandingProposal, ...]) -> list[str]:
    return [
        f"- {_short_id(proposal.proposal_id)} [{proposal.role}] {proposal.objective} -> "
        f"/proposal accept {_short_id(proposal.proposal_id)} or "
        f"/proposal reject {_short_id(proposal.proposal_id)} [reason]"
        for proposal in proposals[:3]
    ]


def _autonomy_receipt_section(
    receipts: tuple[StandingAutonomyReceipt, ...],
) -> list[str]:
    if not receipts:
        return []
    return ["", "自治回执:", *(_autonomy_receipt_line(item) for item in receipts[-5:])]


def _autonomy_receipt_line(receipt: StandingAutonomyReceipt) -> str:
    proposal_id = _short_id(receipt.proposal_id)
    authorization = _short_id(receipt.authorization_id or "unknown")
    task = _short_id(receipt.task_id) if receipt.task_id else "missing"
    elapsed = (
        f" elapsed={receipt.elapsed_seconds:.1f}s" if receipt.elapsed_seconds is not None else ""
    )
    tokens = f" tokens={receipt.total_tokens}" if receipt.total_tokens is not None else ""
    outcome = f" outcome={receipt.outcome_status.value}"
    coverage = (
        f" criteria={receipt.criteria_met}/{receipt.criteria_total} "
        f"sources={receipt.verified_sources}"
        if receipt.criteria_total is not None
        else ""
    )
    evidence = (
        f" evidence={receipt.evidence_status.value}" if receipt.evidence_status is not None else ""
    )
    action = f"/task {task}" if receipt.task_id else "/proposals"
    return (
        f"- {proposal_id} [{receipt.status.value}] charter={receipt.charter_id} "
        f"task={task} auth={authorization}{elapsed}{tokens}{outcome}{coverage}{evidence} "
        f"-> {action}"
    )


def _needs_attention_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> list[str]:
    tasks = _attention_items(task_snapshots)
    lines = ["", "Needs attention:"]
    if not tasks:
        lines.append("- none")
        return lines
    lines.extend(_attention_line(snapshot) for snapshot in tasks[:8])
    return lines


def _running_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> list[str]:
    running = _running_items(task_snapshots)
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
    lines.extend(_handoff_items(records))
    return lines


def _handoff_items(records: tuple[OfflineDelegationRecord, ...]) -> list[str]:
    if not records:
        return []
    return [
        f"- inspect handoff {record.delegation_id}: {record.role} -> {record.agent} "
        f"({_short_id(record.task_id)}) {record.goal} -> /task {_short_id(record.task_id)}"
        for record in records[-5:]
    ]


def _experience_candidate_lines(candidates: tuple[MemoryAtom, ...]) -> list[str]:
    return [
        f"- {candidate.memory_id}: {candidate.claim} -> "
        f"/experience promote {candidate.memory_id} as <role> or "
        f"/experience archive {candidate.memory_id}"
        for candidate in candidates[:3]
    ]


def _attention_items(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[TaskSnapshot, ...]:
    return tuple(
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


def _running_items(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[TaskSnapshot, ...]:
    return tuple(snapshot for snapshot in task_snapshots if snapshot.status is TaskStatus.RUNNING)


def _decision_goal_items(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[TaskSnapshot, ...]:
    return tuple(
        snapshot
        for snapshot in task_snapshots
        if _metadata_value(snapshot, _INTENT_KEY)
        in {_GOAL_INTENT, _LEAD_DECISION_INTENT, _OUTCOME_GRADER_INTENT}
    )


def _decision_goal_lines(task_snapshots: tuple[TaskSnapshot, ...]) -> list[str]:
    tasks = _decision_goal_items(task_snapshots)
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
    reason = f" - {task_error_summary(snapshot.reason)}" if snapshot.reason else ""
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
    reason = f" - {task_error_summary(snapshot.reason)}" if snapshot.reason else ""
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
