"""Morning handoff for absence-first project recovery."""

from __future__ import annotations

import hashlib
import json

from pydantic import Field, model_validator

from aico.core.command_messages import short_id_text, task_error_summary
from aico.core.memory import MemoryAtom
from aico.core.message_rendering import rich_text_message
from aico.core.models import (
    AuditEvent,
    FrozenModel,
    MessageContent,
    RiskLevel,
    TaskSnapshot,
    TaskStatus,
)
from aico.core.offline_delegation import OfflineDelegationRecord
from aico.core.standing_autonomy import StandingAutonomyReceipt
from aico.core.standing_proposal import StandingProposal
from aico.core.unified_event import UnifiedEvent

_PROJECT_ID_KEY = "aico.project_id"


class MorningHandoffEnvelope(FrozenModel):
    """Exact, retry-stable morning content and its source receipt fingerprints."""

    schema_version: int = Field(default=1, ge=1, le=1)
    delivery_id: str = Field(pattern=r"^morning-[a-f0-9]{32}$")
    project_id: str = Field(min_length=1)
    content: MessageContent
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    autonomy_receipt_sha256: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_fingerprints(self) -> MorningHandoffEnvelope:
        if self.content_sha256 != _model_sha256(self.content):
            raise ValueError("morning handoff content fingerprint mismatch")
        if any(
            len(value) != 64 or any(character not in "0123456789abcdef" for character in value)
            for value in self.autonomy_receipt_sha256
        ):
            raise ValueError("morning handoff autonomy receipt fingerprint is invalid")
        return self


def morning_handoff_envelope(
    *,
    delivery_id: str,
    project_id: str,
    task_snapshots: tuple[TaskSnapshot, ...],
    overnight_records: tuple[OfflineDelegationRecord, ...] = (),
    audit_events: tuple[AuditEvent, ...] = (),
    recent_events: tuple[UnifiedEvent, ...] = (),
    experience_candidates: tuple[MemoryAtom, ...] = (),
    standing_proposals: tuple[StandingProposal, ...] = (),
    standing_autonomy_receipts: tuple[StandingAutonomyReceipt, ...] = (),
) -> MorningHandoffEnvelope:
    content = morning_message(
        project_id=project_id,
        task_snapshots=task_snapshots,
        overnight_records=overnight_records,
        audit_events=audit_events,
        recent_events=recent_events,
        experience_candidates=experience_candidates,
        standing_proposals=standing_proposals,
        standing_autonomy_receipts=standing_autonomy_receipts,
    )
    content = content.model_copy(update={"text": f"{content.text}\n\nDelivery: {delivery_id}"})
    return MorningHandoffEnvelope(
        delivery_id=delivery_id,
        project_id=project_id,
        content=content,
        content_sha256=_model_sha256(content),
        autonomy_receipt_sha256=tuple(
            _model_sha256(receipt) for receipt in standing_autonomy_receipts
        ),
    )


def _model_sha256(model: FrozenModel) -> str:
    payload = json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def morning_message(
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
    lines = [f"Morning handoff: {project_id}", f"scope: current project ({project_id})"]
    lines.extend(_done_lines(scoped_tasks))
    lines.extend(_blocked_lines(scoped_tasks))
    lines.extend(_standing_autonomy_receipt_lines(standing_autonomy_receipts))
    lines.extend(_risk_lines(scoped_tasks, audit_events))
    lines.extend(_handoff_lines(overnight_records))
    lines.extend(_experience_candidate_lines(experience_candidates))
    lines.extend(_standing_proposal_lines(standing_proposals))
    lines.extend(_recent_activity_lines(recent_events))
    lines.extend(
        _next_action_lines(
            scoped_tasks,
            overnight_records,
            experience_candidates,
            standing_proposals,
            standing_autonomy_receipts,
        )
    )
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


def _experience_candidate_lines(candidates: tuple[MemoryAtom, ...]) -> list[str]:
    lines = ["", "Experience candidates:"]
    if not candidates:
        lines.append("- none")
        return lines
    lines.extend(
        f"- {candidate.memory_id}: {candidate.claim} -> /experience review"
        for candidate in candidates[:5]
    )
    return lines


def _standing_proposal_lines(proposals: tuple[StandingProposal, ...]) -> list[str]:
    lines = ["", "Standing proposals:"]
    if not proposals:
        lines.append("- none")
        return lines
    lines.extend(
        f"- {short_id_text(proposal.proposal_id)} [{proposal.role}] {proposal.objective}"
        for proposal in proposals[:5]
    )
    return lines


def _standing_autonomy_receipt_lines(
    receipts: tuple[StandingAutonomyReceipt, ...],
) -> list[str]:
    lines = ["", "Standing autonomy receipts:"]
    if not receipts:
        lines.append("- none")
        return lines
    for receipt in receipts[-5:]:
        proposal_id = short_id_text(receipt.proposal_id)
        authorization = short_id_text(receipt.authorization_id or "unknown")
        task = short_id_text(receipt.task_id) if receipt.task_id else "missing"
        elapsed = (
            f" elapsed={receipt.elapsed_seconds:.1f}s"
            if receipt.elapsed_seconds is not None
            else ""
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
            f" evidence={receipt.evidence_status.value}"
            if receipt.evidence_status is not None
            else ""
        )
        action = f"/task {task}" if receipt.task_id else "/proposals"
        lines.append(
            f"- {proposal_id} [{receipt.status.value}] charter={receipt.charter_id} "
            f"task={task} auth={authorization}{elapsed}{tokens}{outcome}{coverage}{evidence} "
            f"-> {action}"
        )
    return lines


def _next_action_lines(
    task_snapshots: tuple[TaskSnapshot, ...],
    overnight_records: tuple[OfflineDelegationRecord, ...],
    experience_candidates: tuple[MemoryAtom, ...],
    standing_proposals: tuple[StandingProposal, ...],
    standing_autonomy_receipts: tuple[StandingAutonomyReceipt, ...],
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
    for proposal in standing_proposals[:3]:
        short_id = short_id_text(proposal.proposal_id)
        actions.append(f"/proposal accept {short_id} or /proposal reject {short_id}")
    actions.extend(
        f"/task {short_id_text(receipt.task_id)}"
        for receipt in standing_autonomy_receipts[-3:]
        if receipt.task_id is not None
    )
    if experience_candidates:
        actions.append("/experience review")
    actions.extend(("/inbox", "/dream"))
    lines = ["", "Next actions:"]
    for action in _dedupe(actions)[:8]:
        lines.append(f"- {action}")
    return lines


def _blocked_line(snapshot: TaskSnapshot) -> str:
    short_id = short_id_text(snapshot.task_id)
    reason = f" - {task_error_summary(snapshot.reason)}" if snapshot.reason else ""
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
