"""Reviewable lead proposals generated from explicit project standing charters."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from pydantic import Field

from aico.channel import IMChannel
from aico.core.agent_session import AgentSession
from aico.core.command_messages import short_id_text
from aico.core.message_rendering import rich_text_message
from aico.core.models import (
    FrozenModel,
    IncomingMessage,
    MessageContent,
    MetadataEntry,
    Task,
    TaskSnapshot,
    TaskStatus,
    TaskUsage,
    utc_now,
)
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectAssignmentDirectory,
    StandingCharterItem,
)
from aico.core.session_commands import session_scope
from aico.core.sqlite_state import SQLiteStateDatabase
from aico.core.standing_result import StandingResultReceipt

STANDING_PROPOSAL_INTENT = "standing_charter"
_PROJECT_ID_KEY = "aico.project_id"
_PROPOSAL_METADATA_KEYS = {
    "aico.intent",
    "aico.standing_proposal_id",
    "aico.standing_charter_id",
}
_ACTIVE_STATUSES = {TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL}

ProjectTaskFactory = Callable[
    [IncomingMessage, str, AssignmentProfile, str],
    tuple[Task, AgentSession | None],
]
DelegatedTaskRunner = Callable[[IncomingMessage, Task, AgentSession | None], Awaitable[str]]


class StandingProposalStatus(StrEnum):
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class StandingProposalDecisionMode(StrEnum):
    MANUAL = "manual"
    PREAUTHORIZED = "preauthorized"


class StandingProposal(FrozenModel):
    proposal_id: str
    project_id: str
    charter_id: str
    role: str
    objective: str
    acceptance_evidence: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    cooldown_hours: int
    status: StandingProposalStatus = StandingProposalStatus.CANDIDATE
    task_id: str | None = None
    decision_reason: str | None = None
    decision_mode: StandingProposalDecisionMode | None = None
    authorization_id: str | None = None
    scheduled_intent_id: str | None = Field(
        default=None,
        pattern=r"^autonomy-[a-f0-9]{32}$",
    )
    usage: TaskUsage | None = None
    usage_recorded_at: datetime | None = None
    result_receipt: StandingResultReceipt | None = None
    created_at: datetime = Field(default_factory=utc_now)
    decided_at: datetime | None = None


class StandingProposalStore(Protocol):
    def list_project(self, project_id: str) -> tuple[StandingProposal, ...]: ...

    def upsert(self, proposal: StandingProposal) -> None: ...


class InMemoryStandingProposalStore:
    def __init__(self) -> None:
        self._records: dict[str, StandingProposal] = {}

    def list_project(self, project_id: str) -> tuple[StandingProposal, ...]:
        return tuple(
            sorted(
                (item for item in self._records.values() if item.project_id == project_id),
                key=lambda item: item.created_at,
            )
        )

    def upsert(self, proposal: StandingProposal) -> None:
        self._records[proposal.proposal_id] = proposal


class SQLiteStandingProposalStore:
    def __init__(self, path: Path | str) -> None:
        self._database = SQLiteStateDatabase(path)
        self._init_schema()

    def list_project(self, project_id: str) -> tuple[StandingProposal, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT payload FROM standing_proposals
                WHERE project_id = ?
                ORDER BY created_at ASC
                """,
                (project_id,),
            ).fetchall()
        return tuple(StandingProposal.model_validate_json(str(row[0])) for row in rows)

    def upsert(self, proposal: StandingProposal) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO standing_proposals (proposal_id, project_id, created_at, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(proposal_id) DO UPDATE SET
                    project_id = excluded.project_id,
                    created_at = excluded.created_at,
                    payload = excluded.payload
                """,
                (
                    proposal.proposal_id,
                    proposal.project_id,
                    proposal.created_at.isoformat(),
                    proposal.model_dump_json(),
                ),
            )

    def _init_schema(self) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS standing_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )


class StandingProposalCoordinator:
    """Refresh and decide project-scoped standing-charter proposals."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        project_directory: ProjectAssignmentDirectory,
        task_for_assignment: ProjectTaskFactory,
        run_delegated_task: DelegatedTaskRunner,
        store: StandingProposalStore | None = None,
        proposal_id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._channel = channel
        self._projects = project_directory
        self._task_for_assignment = task_for_assignment
        self._run_delegated_task = run_delegated_task
        self._store = store or InMemoryStandingProposalStore()
        self._proposal_id_factory = proposal_id_factory or (lambda: f"prop-{uuid4()}")
        self._clock = clock

    def refresh(
        self,
        project_id: str,
        task_snapshots: tuple[TaskSnapshot, ...],
    ) -> tuple[StandingProposal, ...]:
        existing = self._candidates(project_id)
        project = self._projects.project(project_id)
        if existing or project is None or not project.standing_charter:
            return existing
        if self._projects.missing_required_team_roles(project.id):
            return ()
        if _has_active_project_work(task_snapshots, project.id):
            return ()
        history = self._store.list_project(project.id)
        for charter in project.standing_charter:
            if not self._is_due(charter, history):
                continue
            proposal = self._new_proposal(project.id, charter)
            self._store.upsert(proposal)
            return (proposal,)
        return ()

    def candidates(self, project_id: str) -> tuple[StandingProposal, ...]:
        return self._candidates(project_id)

    async def handle_list(self, message: IncomingMessage) -> None:
        project = self._projects.active_project(session_scope(message))
        if project is None:
            await self._send(message, "No active project. Use /project <project> first.")
            return
        proposals = self._store.list_project(project.id)
        await self._channel.send_message(message.source, proposals_message(project.id, proposals))

    async def handle_proposal(self, message: IncomingMessage, payload: str) -> None:
        project = self._projects.active_project(session_scope(message))
        if project is None:
            await self._send(message, "No active project. Use /project <project> first.")
            return
        action, proposal_ref, reason = _proposal_parts(payload)
        if action not in {"accept", "reject"} or not proposal_ref:
            await self._send(
                message,
                "Usage: /proposal accept <id> or /proposal reject <id> [reason]",
            )
            return
        proposal = _resolve_candidate(self._store.list_project(project.id), proposal_ref)
        if proposal is None:
            await self._send(message, f"Candidate proposal not found or ambiguous: {proposal_ref}")
            return
        if action == "reject":
            rejected = proposal.model_copy(
                update={
                    "status": StandingProposalStatus.REJECTED,
                    "decision_reason": reason,
                    "decision_mode": StandingProposalDecisionMode.MANUAL,
                    "decided_at": self._clock(),
                }
            )
            self._store.upsert(rejected)
            await self._send(message, f"Proposal rejected: {short_id_text(proposal.proposal_id)}")
            return
        await self._accept(message, proposal)

    async def _accept(self, message: IncomingMessage, proposal: StandingProposal) -> None:
        prepared = self.prepare_task(message, proposal)
        if prepared is None:
            await self._send(
                message,
                f"No appointed role for proposal: {proposal.role}. Use /team first.",
            )
            return
        task, session = prepared
        self.record_accepted(
            proposal,
            task,
            decision_mode=StandingProposalDecisionMode.MANUAL,
        )
        await self._send(
            message,
            f"Proposal accepted: {short_id_text(proposal.proposal_id)} -> "
            f"task {short_id_text(task.task_id)}",
        )
        await self._run_delegated_task(message, task, session)

    def history(self, project_id: str) -> tuple[StandingProposal, ...]:
        return self._store.list_project(project_id)

    def prepare_task(
        self,
        message: IncomingMessage,
        proposal: StandingProposal,
        *,
        payload: str | None = None,
    ) -> tuple[Task, AgentSession | None] | None:
        assignment = self._projects.appointment_for_role(proposal.project_id, proposal.role)
        if assignment is None:
            return None
        task, session = self._task_for_assignment(
            message,
            proposal.project_id,
            assignment,
            payload or standing_proposal_prompt(proposal),
        )
        return _task_with_proposal_metadata(task, proposal), session

    def record_accepted(
        self,
        proposal: StandingProposal,
        task: Task,
        *,
        decision_mode: StandingProposalDecisionMode,
        authorization_id: str | None = None,
        scheduled_intent_id: str | None = None,
    ) -> StandingProposal:
        accepted = proposal.model_copy(
            update={
                "status": StandingProposalStatus.ACCEPTED,
                "task_id": task.task_id,
                "decision_mode": decision_mode,
                "authorization_id": authorization_id,
                "scheduled_intent_id": scheduled_intent_id,
                "decided_at": self._clock(),
            }
        )
        self._store.upsert(accepted)
        return accepted

    def record_usage(self, proposal: StandingProposal, usage: TaskUsage) -> StandingProposal:
        recorded = proposal.model_copy(update={"usage": usage, "usage_recorded_at": self._clock()})
        self._store.upsert(recorded)
        return recorded

    def record_result(
        self,
        proposal: StandingProposal,
        receipt: StandingResultReceipt,
    ) -> StandingProposal:
        recorded = proposal.model_copy(update={"result_receipt": receipt})
        self._store.upsert(recorded)
        return recorded

    def _candidates(self, project_id: str) -> tuple[StandingProposal, ...]:
        return tuple(
            item
            for item in self._store.list_project(project_id)
            if item.status is StandingProposalStatus.CANDIDATE
        )

    def _is_due(
        self,
        charter: StandingCharterItem,
        history: tuple[StandingProposal, ...],
    ) -> bool:
        prior = [item for item in history if item.charter_id == charter.id]
        if not prior:
            return True
        latest = prior[-1]
        reference = latest.decided_at or latest.created_at
        return self._clock() - reference >= timedelta(hours=charter.cooldown_hours)

    def _new_proposal(self, project_id: str, charter: StandingCharterItem) -> StandingProposal:
        return StandingProposal(
            proposal_id=self._proposal_id_factory(),
            project_id=project_id,
            charter_id=charter.id,
            role=charter.role,
            objective=charter.objective,
            acceptance_evidence=charter.acceptance_evidence,
            stop_conditions=charter.stop_conditions,
            cooldown_hours=charter.cooldown_hours,
            created_at=self._clock(),
        )

    async def _send(self, message: IncomingMessage, text: str) -> None:
        await self._channel.send_message(message.source, MessageContent(text=text))


def proposals_message(
    project_id: str,
    proposals: tuple[StandingProposal, ...],
) -> MessageContent:
    lines = [f"Standing proposals: {project_id}"]
    if not proposals:
        lines.append("- none")
    for proposal in proposals[-8:]:
        short_id = short_id_text(proposal.proposal_id)
        task = f" -> task {short_id_text(proposal.task_id)}" if proposal.task_id else ""
        lines.append(
            f"- {short_id} [{proposal.status.value}] {proposal.role}: {proposal.objective}{task}"
        )
        if proposal.status is StandingProposalStatus.CANDIDATE:
            lines.append(f"  /proposal accept {short_id}")
            lines.append(f"  /proposal reject {short_id} [reason]")
    return rich_text_message("\n".join(lines))


def standing_proposal_prompt(proposal: StandingProposal) -> str:
    evidence = "\n".join(f"- {item}" for item in proposal.acceptance_evidence)
    stops = "\n".join(f"- {item}" for item in proposal.stop_conditions)
    return (
        "Boss accepted standing-charter proposal.\n"
        f"proposal_id: {proposal.proposal_id}\n"
        f"charter_id: {proposal.charter_id}\n"
        f"objective: {proposal.objective}\n\n"
        f"Acceptance evidence:\n{evidence}\n\n"
        f"Stop conditions:\n{stops}\n\n"
        "Stay within this bounded objective. Use normal risk and approval controls. "
        "Return done, blocked, risks, evidence, and next actions."
    )


def _has_active_project_work(
    snapshots: tuple[TaskSnapshot, ...],
    project_id: str,
) -> bool:
    return any(
        snapshot.status in _ACTIVE_STATUSES
        and _metadata_value(snapshot.metadata, _PROJECT_ID_KEY) == project_id
        for snapshot in snapshots
    )


def _metadata_value(metadata: tuple[MetadataEntry, ...], key: str) -> str | None:
    return next((str(item.value) for item in metadata if item.key == key), None)


def _proposal_parts(payload: str) -> tuple[str, str, str | None]:
    action, _, remainder = payload.strip().partition(" ")
    proposal_ref, separator, reason = remainder.strip().partition(" ")
    return action.casefold(), proposal_ref, reason.strip() if separator and reason.strip() else None


def _resolve_candidate(
    proposals: tuple[StandingProposal, ...],
    proposal_ref: str,
) -> StandingProposal | None:
    matches = tuple(
        proposal
        for proposal in proposals
        if proposal.status is StandingProposalStatus.CANDIDATE
        and (proposal.proposal_id == proposal_ref or proposal.proposal_id.startswith(proposal_ref))
    )
    return matches[0] if len(matches) == 1 else None


def _task_with_proposal_metadata(task: Task, proposal: StandingProposal) -> Task:
    metadata = tuple(item for item in task.metadata if item.key not in _PROPOSAL_METADATA_KEYS)
    return task.model_copy(
        update={
            "metadata": (
                *metadata,
                MetadataEntry(key="aico.intent", value=STANDING_PROPOSAL_INTENT),
                MetadataEntry(
                    key="aico.standing_proposal_id",
                    value=proposal.proposal_id,
                ),
                MetadataEntry(key="aico.standing_charter_id", value=proposal.charter_id),
            )
        }
    )
