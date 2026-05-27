"""Lead decision workflow helpers for Phase 8."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from aico.channel import IMChannel
from aico.core.agent_session import AgentSession
from aico.core.memory import (
    MemoryAtom,
    MemoryEvidence,
    MemoryPacket,
    MemoryPacketItem,
    MemoryPurpose,
    MemoryRetriever,
    MemoryScope,
    MemoryStore,
)
from aico.core.models import AuditEvent, IncomingMessage, MessageContent, MetadataEntry, Task
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectAssignmentDirectory,
    ProjectProfile,
)

LEAD_DECISION_INTENT = "lead_decision"
LEAD_DECISION_INTENT_KEY = "aico.intent"
LEAD_DECISION_ORIGINAL_TASK_KEY = "aico.decision_task"
DECISION_MEMORY_PURPOSES = (
    MemoryPurpose.PUBLIC_BROADCAST,
    MemoryPurpose.TASK_KEY_PROGRESS,
    MemoryPurpose.DECISION_REVIEW,
)

_DECISION_MARKERS = (
    "decide",
    "decision",
    "choose",
    "should we",
    "whether",
    "tradeoff",
    "trade-off",
    "approve ",
    "go/no-go",
    "决策",
    "决定",
    "是否",
    "要不要",
    "该不该",
    "选哪个",
    "取舍",
    "拍板",
    "评审",
    "方案选择",
)


@dataclass(frozen=True)
class DecisionConsultation:
    role: str
    agent: str
    task_id: str
    output: str


class DecisionAuditRecorder(Protocol):
    def record_collaboration_requested(self, source_task: Task, child_task: Task) -> None: ...

    def record_lead_decision(self, task: Task, *, detail: str) -> AuditEvent: ...


ProjectTaskFactory = Callable[
    [IncomingMessage, str, AssignmentProfile, str, MemoryPacket | None],
    tuple[Task, AgentSession | None],
]
DecisionTaskRunner = Callable[
    [IncomingMessage, Task, AgentSession | None, int],
    Awaitable[str],
]


class LeadDecisionWorkflow:
    """Coordinate read-only lead decision reviews without owning adapter execution."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        project_directory: ProjectAssignmentDirectory,
        memory_store: MemoryStore | None,
        audit_recorder: DecisionAuditRecorder,
        task_for_assignment: ProjectTaskFactory,
        run_decision_task: DecisionTaskRunner,
    ) -> None:
        self._channel = channel
        self._project_directory = project_directory
        self._memory_store = memory_store
        self._audit_recorder = audit_recorder
        self._task_for_assignment = task_for_assignment
        self._run_decision_task = run_decision_task

    async def run(
        self,
        message: IncomingMessage,
        *,
        project_id: str,
        assignment: AssignmentProfile,
        boss_task: str,
    ) -> None:
        project = self._project_directory.project(project_id)
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Project not found: {project_id}"),
            )
            return
        missing_roles = self._project_directory.missing_required_team_roles(project.id)
        if missing_roles:
            await self._channel.send_message(
                message.source,
                _missing_team_message(project.id, missing_roles),
            )
            return

        memory_packet = self._decision_memory_packet(
            boss_id=message.sender_id,
            project_id=project.id,
            assignment=assignment,
            query=boss_task,
        )
        consultations, consultation_tasks = await self._consult_roles(
            message,
            project,
            assignment,
            boss_task,
            memory_packet,
        )
        lead_task, session = self._task_for_assignment(
            message,
            project.id,
            assignment,
            decision_memo_prompt(
                boss_task=boss_task,
                memory_packet=memory_packet,
                consultations=consultations,
            ),
            memory_packet,
        )
        lead_task = task_with_decision_metadata(lead_task, boss_task=boss_task)
        for child_task in consultation_tasks:
            self._audit_recorder.record_collaboration_requested(lead_task, child_task)
        memo = await self._run_decision_task(message, lead_task, session, 0)
        audit_event = self._audit_recorder.record_lead_decision(
            lead_task,
            detail=decision_audit_detail(
                project=project,
                lead=assignment,
                boss_task=boss_task,
                memory_packet=memory_packet,
                consultations=consultations,
                memo=memo,
            ),
        )
        append_decision_review_memory(
            self._memory_store,
            project=project,
            lead=assignment,
            audit_event=audit_event,
            boss_task=boss_task,
            memo=memo,
        )

    async def _consult_roles(
        self,
        message: IncomingMessage,
        project: ProjectProfile,
        lead: AssignmentProfile,
        boss_task: str,
        memory_packet: MemoryPacket | None,
    ) -> tuple[tuple[DecisionConsultation, ...], tuple[Task, ...]]:
        consultations: list[DecisionConsultation] = []
        consultation_tasks: list[Task] = []
        for reviewer in self._decision_reviewers(project.id, lead):
            task, session = self._task_for_assignment(
                message,
                project.id,
                reviewer,
                consultation_prompt(
                    project=project,
                    lead=lead,
                    reviewer=reviewer,
                    boss_task=boss_task,
                    memory_packet=memory_packet,
                ),
                memory_packet,
            )
            task = task_with_decision_metadata(task, boss_task=boss_task)
            output = await self._run_decision_task(message, task, session, 1)
            consultations.append(
                DecisionConsultation(
                    role=reviewer.role,
                    agent=reviewer.agent,
                    task_id=task.task_id,
                    output=output,
                )
            )
            consultation_tasks.append(task)
        return tuple(consultations), tuple(consultation_tasks)

    def _decision_reviewers(
        self,
        project_id: str,
        lead: AssignmentProfile,
    ) -> tuple[AssignmentProfile, ...]:
        reviewers: list[AssignmentProfile] = []
        seen_seats = {lead.seat}
        for role in ("challenger", "reviewer"):
            appointment = self._project_directory.appointment_for_role(project_id, role)
            if appointment is None or appointment.seat in seen_seats:
                continue
            seen_seats.add(appointment.seat)
            reviewers.append(appointment)
        return tuple(reviewers)

    def _decision_memory_packet(
        self,
        *,
        boss_id: str,
        project_id: str,
        assignment: AssignmentProfile,
        query: str,
    ) -> MemoryPacket | None:
        if self._memory_store is None:
            return None
        scopes = (
            MemoryScope.boss(boss_id),
            MemoryScope.project(project_id),
            MemoryScope.team(project_id, "default"),
            MemoryScope.role(project_id, "default", assignment.role),
            MemoryScope.agent(project_id, "default", assignment.agent),
        )
        return MemoryRetriever(self._memory_store).retrieve_packet(
            scopes=scopes,
            query=query,
            top_k=8,
            max_tokens=900,
            allowed_purposes=DECISION_MEMORY_PURPOSES,
        )


def is_decision_task(text: str) -> bool:
    normalized = text.casefold()
    return any(marker in normalized for marker in _DECISION_MARKERS)


def consultation_prompt(
    *,
    project: ProjectProfile,
    lead: AssignmentProfile,
    reviewer: AssignmentProfile,
    boss_task: str,
    memory_packet: MemoryPacket | None,
) -> str:
    memory_refs = _memory_refs(memory_packet)
    return (
        "Decision consultation request.\n"
        f"Project: {project.id} [{project.name}]\n"
        f"Lead role: {lead.role}\n"
        f"Consulted role: {reviewer.role}\n"
        f"Boss decision task: {boss_task}\n"
        f"Memory refs: {memory_refs}\n\n"
        "Return a concise review for the lead decision memo:\n"
        "- recommended decision or objection\n"
        "- strongest evidence or missing evidence\n"
        "- rejected alternative or opportunity cost\n"
        "- risks and whether boss approval is needed\n\n"
        "Do not execute code, edit files, or make irreversible changes."
    )


def decision_memo_prompt(
    *,
    boss_task: str,
    memory_packet: MemoryPacket | None,
    consultations: tuple[DecisionConsultation, ...],
) -> str:
    return (
        "Lead decision workflow.\n"
        f"Boss decision task: {boss_task}\n\n"
        "Decision inputs:\n"
        f"{_memory_summary(memory_packet)}\n"
        f"{_consultation_summary(consultations)}\n\n"
        "Output a decision memo with exactly these sections:\n"
        "Decision, Why, Evidence / memory refs, Consulted roles, "
        "Rejected alternatives, Risks / approval need, Next actions.\n"
        "Make only bounded low-risk decisions. Escalate irreversible, public-release, "
        "credential, payment, destructive, or unclear decisions to the boss."
    )


def task_with_decision_metadata(task: Task, *, boss_task: str) -> Task:
    return task.model_copy(
        update={
            "metadata": (
                *task.metadata,
                MetadataEntry(key=LEAD_DECISION_INTENT_KEY, value=LEAD_DECISION_INTENT),
                MetadataEntry(
                    key=LEAD_DECISION_ORIGINAL_TASK_KEY,
                    value=boss_task[:200],
                ),
            )
        }
    )


def decision_audit_detail(
    *,
    project: ProjectProfile,
    lead: AssignmentProfile,
    boss_task: str,
    memory_packet: MemoryPacket | None,
    consultations: tuple[DecisionConsultation, ...],
    memo: str,
) -> str:
    payload = {
        "project_id": project.id,
        "lead_role": lead.role,
        "lead_agent": lead.agent,
        "boss_task": boss_task,
        "memory_refs": [item.memory_id for item in _memory_items(memory_packet)],
        "consultations": [
            {
                "role": consultation.role,
                "agent": consultation.agent,
                "task_id": consultation.task_id,
            }
            for consultation in consultations
        ],
        "memo_excerpt": _compact_excerpt(memo),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def append_decision_review_memory(
    store: MemoryStore | None,
    *,
    project: ProjectProfile,
    lead: AssignmentProfile,
    audit_event: AuditEvent,
    boss_task: str,
    memo: str,
) -> MemoryAtom | None:
    if store is None or not memo.strip():
        return None
    return store.append_atom(
        MemoryAtom(
            memory_id=f"mem-{uuid4().hex[:12]}",
            claim=f"Decision memo for {project.id}: {boss_task}\n{_compact_excerpt(memo, 900)}",
            evidence=(
                MemoryEvidence(
                    ref=f"audit:{audit_event.event_id}",
                    source="audit",
                    captured_at=audit_event.timestamp,
                    note="lead decision workflow",
                ),
            ),
            scope=MemoryScope.project(project.id),
            source="lead_decision_workflow",
            confidence=0.86,
            created_by=lead.agent,
            tags=("lead-decision", lead.role),
            purpose_tags=(MemoryPurpose.DECISION_REVIEW,),
            reason="decision memo generated by lead decision workflow",
        )
    )


def _memory_items(memory_packet: MemoryPacket | None) -> tuple[MemoryPacketItem, ...]:
    return () if memory_packet is None else memory_packet.items


def _memory_refs(memory_packet: MemoryPacket | None) -> str:
    refs = [item.memory_id for item in _memory_items(memory_packet)]
    return ", ".join(refs) if refs else "none"


def _memory_summary(memory_packet: MemoryPacket | None) -> str:
    items = _memory_items(memory_packet)
    if not items:
        return "- recalled memory: none"
    lines = ["- recalled memory:"]
    lines.extend(f"  - {item.memory_id}: {item.claim}" for item in items)
    return "\n".join(lines)


def _consultation_summary(consultations: tuple[DecisionConsultation, ...]) -> str:
    if not consultations:
        return "- consultations: none"
    lines = ["- consultations:"]
    for consultation in consultations:
        lines.append(
            f"  - {consultation.role} -> {consultation.agent} "
            f"({consultation.task_id}): {_compact_excerpt(consultation.output, 700)}"
        )
    return "\n".join(lines)


def _compact_excerpt(text: str, limit: int = 500) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def _missing_team_message(project_id: str, missing_roles: tuple[str, ...]) -> MessageContent:
    return MessageContent(
        text=(
            f"Team incomplete for {project_id}: missing {', '.join(missing_roles)}.\n"
            "Lead decisions need a project lead and challenger.\n\n"
            "Next:\n"
            "- /team\n"
            "- /appoint <agent> as challenger"
        )
    )
