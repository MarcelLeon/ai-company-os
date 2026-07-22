"""Owner-bound grants for scheduled read-only standing-charter execution."""

from __future__ import annotations

import hashlib
import logging
import os
import stat
from collections.abc import Awaitable, Callable
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from aico.channel import IMChannel
from aico.core.agent_session import AgentSession, task_without_provider_session
from aico.core.collaboration import task_with_exact_output_constraint
from aico.core.command_messages import short_id_text
from aico.core.models import (
    ChannelTarget,
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
from aico.core.preauthorized_execution import (
    PREAUTHORIZED_GRANT_ID_KEY,
    task_with_preauthorized_execution,
)
from aico.core.standing_proposal import (
    StandingProposal,
    StandingProposalCoordinator,
    StandingProposalDecisionMode,
    StandingProposalStatus,
)
from aico.core.standing_result import (
    MAX_STANDING_RESULT_CHARS,
    MAX_STANDING_SOURCE_FILE_BYTES,
    MAX_STANDING_VERIFIED_SOURCES,
    StandingEvidenceStatus,
    StandingResultContractStatus,
    StandingResultFailure,
    standing_result_evidence_status,
    validate_standing_result,
)

_MAX_GRANT_FILE_BYTES = 65_536
_MAX_RECEIPT_EVIDENCE_CHECKS = 5
_PLACEHOLDER_ID_FRAGMENTS = ("replace-with", "replace-me", "<", ">")
SCHEDULED_AUTONOMY_INTENT_ID_KEY = "aico.scheduled_autonomy_intent_id"
log = logging.getLogger(__name__)

PreauthorizedTaskRunner = Callable[
    [IncomingMessage, Task, AgentSession | None, float],
    Awaitable[str],
]
PreauthorizedPreflight = Callable[[Task], str | None]
TaskUsageLookup = Callable[[str], TaskUsage | None]
TaskStatusLookup = Callable[[str], TaskStatus | None]
EvidenceRootLookup = Callable[[str], Path | None]
AuthorizationTimeRefusal = Callable[[], str | None]


class StandingAutonomyConfigError(RuntimeError):
    pass


class StandingAutonomyGrant(FrozenModel):
    grant_id: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    channel_name: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    thread_id: str | None = None
    project_id: str = Field(min_length=1)
    charter_id: str = Field(min_length=1)
    mode: Literal["read_only"] = "read_only"
    expires_at: datetime
    max_runs: int = Field(ge=1, le=1000)
    max_duration_seconds: float = Field(ge=0.01, le=3600)
    token_stop_threshold: int = Field(ge=1, le=1_000_000_000)

    @model_validator(mode="after")
    def _require_concrete_binding(self) -> StandingAutonomyGrant:
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("standing autonomy expiry must be timezone-aware")
        binding_values = (
            self.grant_id,
            self.owner_id,
            self.channel_name,
            self.target_id,
            self.thread_id or "",
            self.project_id,
            self.charter_id,
        )
        if any(
            fragment in value.casefold()
            for value in binding_values
            for fragment in _PLACEHOLDER_ID_FRAGMENTS
        ):
            raise ValueError("standing autonomy grant contains a placeholder binding")
        return self


class StandingAutonomyGrantSet(FrozenModel):
    version: Literal[1] = 1
    grants: tuple[StandingAutonomyGrant, ...] = ()

    @model_validator(mode="after")
    def _require_unique_grants(self) -> StandingAutonomyGrantSet:
        grant_ids: set[str] = set()
        bindings: set[tuple[str, ...]] = set()
        for grant in self.grants:
            if grant.grant_id in grant_ids:
                raise ValueError("duplicate standing autonomy grant id")
            grant_ids.add(grant.grant_id)
            binding = (
                grant.channel_name,
                grant.target_id,
                grant.thread_id or "",
                grant.project_id,
                grant.charter_id,
            )
            if binding in bindings:
                raise ValueError("duplicate standing autonomy binding")
            bindings.add(binding)
        return self


class StandingAutonomyReceiptStatus(StrEnum):
    EVIDENCE_MISSING = "evidence_missing"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    REJECTED = "rejected"


class StandingAutonomyOutcomeStatus(StrEnum):
    PENDING = "pending"
    MISSING = "missing"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    INVALID = "invalid"
    DRIFTED = "drifted"


class StandingAutonomyRunDisposition(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    HELD = "held"
    DISPATCH_RECORDED = "dispatch_recorded"


class StandingAutonomyRunReceipt(FrozenModel):
    intent_id: str = Field(pattern=r"^autonomy-[a-f0-9]{32}$")
    project_id: str = Field(min_length=1)
    disposition: StandingAutonomyRunDisposition
    proposal_id: str | None = None
    task_id: str | None = None

    @model_validator(mode="after")
    def validate_evidence(self) -> StandingAutonomyRunReceipt:
        recorded = self.disposition is StandingAutonomyRunDisposition.DISPATCH_RECORDED
        if recorded != (self.proposal_id is not None and self.task_id is not None):
            raise ValueError("recorded autonomy dispatch requires proposal and task evidence")
        return self


class StandingAutonomyOutcomeEnvelope(FrozenModel):
    version: Literal[1] = 1
    intent_id: str = Field(pattern=r"^autonomy-[a-f0-9]{32}$")
    project_id: str = Field(min_length=1)
    run_receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_status: StandingAutonomyReceiptStatus
    outcome_status: StandingAutonomyOutcomeStatus
    content: MessageContent
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_content(self) -> StandingAutonomyOutcomeEnvelope:
        if _model_sha256(self.content) != self.content_sha256:
            raise ValueError("scheduled autonomy outcome content fingerprint mismatch")
        return self


class StandingAutonomyReceipt(FrozenModel):
    proposal_id: str
    task_id: str | None = None
    charter_id: str
    authorization_id: str | None = None
    status: StandingAutonomyReceiptStatus
    decided_at: datetime
    finished_at: datetime | None = None
    elapsed_seconds: float | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    outcome_status: StandingAutonomyOutcomeStatus
    criteria_met: int | None = Field(default=None, ge=0)
    criteria_total: int | None = Field(default=None, ge=1)
    verified_sources: int | None = Field(default=None, ge=0)
    evidence_status: StandingEvidenceStatus | None = None
    result_failure: StandingResultFailure | None = None


def standing_autonomy_receipts(
    proposals: tuple[StandingProposal, ...],
    task_snapshots: tuple[TaskSnapshot, ...],
    *,
    evidence_root: Path | None = None,
) -> tuple[StandingAutonomyReceipt, ...]:
    """Project restart-safe receipts from existing proposal and task truth."""
    snapshots = {snapshot.task_id: snapshot for snapshot in task_snapshots}
    accepted = tuple(
        proposal
        for proposal in proposals
        if proposal.status is StandingProposalStatus.ACCEPTED
        and proposal.decision_mode is StandingProposalDecisionMode.PREAUTHORIZED
    )
    evidence_start = max(0, len(accepted) - _MAX_RECEIPT_EVIDENCE_CHECKS)
    receipts = tuple(
        _standing_autonomy_receipt(
            proposal,
            snapshots.get(proposal.task_id or ""),
            evidence_root if index >= evidence_start else None,
        )
        for index, proposal in enumerate(accepted)
    )
    return tuple(sorted(receipts, key=lambda receipt: receipt.decided_at))


class StandingAutonomyCoordinator:
    """Consume one exact grant only from the scheduled morning path."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        proposals: StandingProposalCoordinator,
        grants: StandingAutonomyGrantSet | None,
        preflight: PreauthorizedPreflight,
        run_task: PreauthorizedTaskRunner,
        usage_for_task: TaskUsageLookup,
        status_for_task: TaskStatusLookup,
        evidence_root_for_project: EvidenceRootLookup,
        authorization_time_refusal: AuthorizationTimeRefusal,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._channel = channel
        self._proposals = proposals
        self._grants = grants or StandingAutonomyGrantSet()
        self._preflight = preflight
        self._run_task = run_task
        self._usage_for_task = usage_for_task
        self._status_for_task = status_for_task
        self._evidence_root_for_project = evidence_root_for_project
        self._authorization_time_refusal = authorization_time_refusal
        self._clock = clock

    async def run_once(
        self,
        target: ChannelTarget,
        *,
        project_id: str,
        task_snapshots: tuple[TaskSnapshot, ...],
        intent_id: str,
    ) -> StandingAutonomyRunReceipt:
        candidates = self._proposals.refresh(project_id, task_snapshots)
        if not candidates:
            return _run_receipt(intent_id, project_id)
        proposal = candidates[0]
        grant = self._matching_grant(target, proposal)
        if grant is None:
            return _run_receipt(intent_id, project_id)
        clock_refusal = self._authorization_time_refusal()
        if clock_refusal is not None:
            return await self._hold(target, proposal, clock_refusal, intent_id=intent_id)
        if grant.expires_at <= self._clock():
            return await self._hold(
                target,
                proposal,
                "authorization expired",
                intent_id=intent_id,
            )
        if self._consumed_runs(grant) >= grant.max_runs:
            return await self._hold(
                target,
                proposal,
                "run budget exhausted",
                intent_id=intent_id,
            )
        result_refusal = self._result_refusal(grant)
        if result_refusal is not None:
            return await self._hold(target, proposal, result_refusal, intent_id=intent_id)
        usage_refusal = self._usage_refusal(grant)
        if usage_refusal is not None:
            return await self._hold(target, proposal, usage_refusal, intent_id=intent_id)
        message = _grant_message(target, grant, proposal)
        prepared = self._proposals.prepare_task(
            message,
            proposal,
            payload=_preauthorized_prompt(proposal),
        )
        if prepared is None:
            return await self._hold(
                target,
                proposal,
                "appointed role is unavailable",
                intent_id=intent_id,
            )
        task, _ = prepared
        task = _secure_preauthorized_task(task, grant)
        task = _task_with_scheduled_intent(task, intent_id)
        refusal = self._preflight(task)
        if refusal is not None:
            return await self._hold(target, proposal, refusal, intent_id=intent_id)
        accepted = self._proposals.record_accepted(
            proposal,
            task,
            decision_mode=StandingProposalDecisionMode.PREAUTHORIZED,
            authorization_id=grant.grant_id,
            scheduled_intent_id=intent_id,
        )
        try:
            await self._channel.send_message(
                target,
                MessageContent(
                    text=f"Preauthorized proposal started: "
                    f"{short_id_text(proposal.proposal_id)} "
                    f"-> task {short_id_text(task.task_id)}"
                ),
            )
        except Exception as exc:
            log.warning(
                "Standing autonomy start notification failed: type=%s",
                type(exc).__name__,
            )
        output = await self._run_task(message, task, None, grant.max_duration_seconds)
        return await self._record_completed_dispatch(
            target,
            proposal=proposal,
            accepted=accepted,
            task=task,
            output=output,
            intent_id=intent_id,
        )

    async def _record_completed_dispatch(
        self,
        target: ChannelTarget,
        *,
        proposal: StandingProposal,
        accepted: StandingProposal,
        task: Task,
        output: str,
        intent_id: str,
    ) -> StandingAutonomyRunReceipt:
        usage = self._usage_for_task(task.task_id)
        if usage is None:
            await self._hold(
                target,
                accepted,
                "provider usage evidence missing",
                intent_id=intent_id,
            )
            return _recorded_run_receipt(intent_id, accepted)
        recorded = self._proposals.record_usage(accepted, usage)
        if self._status_for_task(task.task_id) is not TaskStatus.DONE:
            await self._hold(
                target,
                recorded,
                "transport did not complete",
                intent_id=intent_id,
            )
            return _recorded_run_receipt(intent_id, recorded)
        result = validate_standing_result(
            output,
            acceptance_evidence=proposal.acceptance_evidence,
            stop_conditions=proposal.stop_conditions,
            evidence_root=self._evidence_root_for_project(proposal.project_id),
            clock=self._clock,
        )
        self._proposals.record_result(recorded, result)
        return _recorded_run_receipt(intent_id, recorded)

    def evidence_for_intent(
        self,
        *,
        project_id: str,
        intent_id: str,
    ) -> StandingAutonomyRunReceipt | None:
        proposal = next(
            (
                item
                for item in self._proposals.history(project_id)
                if item.scheduled_intent_id == intent_id
                and item.status is StandingProposalStatus.ACCEPTED
                and item.task_id is not None
            ),
            None,
        )
        if proposal is None:
            return None
        return _recorded_run_receipt(intent_id, proposal)

    def _matching_grant(
        self,
        target: ChannelTarget,
        proposal: StandingProposal,
    ) -> StandingAutonomyGrant | None:
        return next(
            (
                grant
                for grant in self._grants.grants
                if grant.project_id == proposal.project_id
                and grant.charter_id == proposal.charter_id
                and grant.channel_name == target.channel_name
                and grant.target_id == target.target_id
                and grant.thread_id == target.thread_id
            ),
            None,
        )

    def _consumed_runs(self, grant: StandingAutonomyGrant) -> int:
        return sum(
            1
            for proposal in self._proposals.history(grant.project_id)
            if proposal.decision_mode is StandingProposalDecisionMode.PREAUTHORIZED
            and proposal.authorization_id == grant.grant_id
        )

    def _usage_refusal(self, grant: StandingAutonomyGrant) -> str | None:
        prior = tuple(
            proposal
            for proposal in self._proposals.history(grant.project_id)
            if proposal.decision_mode is StandingProposalDecisionMode.PREAUTHORIZED
            and proposal.authorization_id == grant.grant_id
        )
        if any(proposal.usage is None for proposal in prior):
            return "provider usage evidence missing"
        observed_tokens = sum(
            proposal.usage.total_tokens for proposal in prior if proposal.usage is not None
        )
        if observed_tokens >= grant.token_stop_threshold:
            return "observed token threshold reached"
        return None

    def _result_refusal(self, grant: StandingAutonomyGrant) -> str | None:
        prior = tuple(
            proposal
            for proposal in self._proposals.history(grant.project_id)
            if proposal.decision_mode is StandingProposalDecisionMode.PREAUTHORIZED
            and proposal.authorization_id == grant.grant_id
        )
        if any(proposal.result_receipt is None for proposal in prior):
            return "result contract evidence missing"
        statuses = {proposal.result_receipt.status for proposal in prior if proposal.result_receipt}
        if StandingResultContractStatus.INVALID in statuses:
            return "result contract invalid"
        if StandingResultContractStatus.BLOCKED in statuses:
            return "prior result blocked"
        if prior:
            result = prior[-1].result_receipt
            assert result is not None
        else:
            result = None
        if result is not None and result.status is StandingResultContractStatus.COMPLETE:
            evidence = standing_result_evidence_status(
                result,
                self._evidence_root_for_project(grant.project_id),
            )
            if evidence is StandingEvidenceStatus.DRIFTED:
                return "result evidence drifted"
            if evidence is StandingEvidenceStatus.MISSING:
                return "result evidence missing"
        return None

    async def _hold(
        self,
        target: ChannelTarget,
        proposal: StandingProposal,
        reason: str,
        *,
        intent_id: str,
    ) -> StandingAutonomyRunReceipt:
        await self._channel.send_message(
            target,
            MessageContent(
                text=f"Autonomy held: {reason} for proposal "
                f"{short_id_text(proposal.proposal_id)}; manual decision remains available."
                f" Intent: {intent_id}"
            ),
        )
        return StandingAutonomyRunReceipt(
            intent_id=intent_id,
            project_id=proposal.project_id,
            proposal_id=proposal.proposal_id,
            disposition=StandingAutonomyRunDisposition.HELD,
        )


def load_standing_autonomy_grants(
    path: Path,
    *,
    forbidden_roots: tuple[Path, ...] = (),
) -> StandingAutonomyGrantSet:
    expanded = path.expanduser()
    if not expanded.is_absolute():
        raise StandingAutonomyConfigError("standing autonomy grant path must be absolute")
    candidate = expanded.absolute()
    try:
        info = candidate.lstat()
    except OSError:
        raise StandingAutonomyConfigError("standing autonomy grant file is missing") from None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise StandingAutonomyConfigError(
            "standing autonomy grant must be a regular non-symlink file"
        )
    if info.st_uid != os.getuid():
        raise StandingAutonomyConfigError(
            "standing autonomy grant must be owned by the current user"
        )
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise StandingAutonomyConfigError("standing autonomy grant must be owner-only")
    if info.st_size > _MAX_GRANT_FILE_BYTES:
        raise StandingAutonomyConfigError("standing autonomy grant file is too large")
    resolved = candidate.resolve()
    if any(_is_within(resolved, root.expanduser().resolve()) for root in forbidden_roots):
        raise StandingAutonomyConfigError(
            "standing autonomy grant must stay outside managed repositories"
        )
    try:
        return StandingAutonomyGrantSet.model_validate_json(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise StandingAutonomyConfigError("standing autonomy grant file is invalid") from None


def _is_within(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def standing_autonomy_outcome_envelope(
    run_receipt: StandingAutonomyRunReceipt,
    outcome: StandingAutonomyReceipt,
) -> StandingAutonomyOutcomeEnvelope:
    if run_receipt.disposition is not StandingAutonomyRunDisposition.DISPATCH_RECORDED:
        raise ValueError("scheduled autonomy outcome requires recorded dispatch")
    if run_receipt.proposal_id != outcome.proposal_id or run_receipt.task_id != outcome.task_id:
        raise ValueError("scheduled autonomy outcome source mismatch")
    details = [
        f"Scheduled autonomy outcome: status={outcome.status.value}",
        f"outcome={outcome.outcome_status.value}",
        f"proposal={short_id_text(outcome.proposal_id)}",
        f"task={short_id_text(outcome.task_id or 'missing')}",
    ]
    if outcome.criteria_total is not None:
        details.append(f"criteria={outcome.criteria_met or 0}/{outcome.criteria_total}")
    if outcome.verified_sources is not None:
        details.append(f"sources={outcome.verified_sources}")
    if outcome.evidence_status is not None:
        details.append(f"evidence={outcome.evidence_status.value}")
    if outcome.result_failure is not None:
        details.append(f"failure={outcome.result_failure.value}")
    details.append(f"intent={run_receipt.intent_id}")
    content = MessageContent(text=" ".join(details))
    return StandingAutonomyOutcomeEnvelope(
        intent_id=run_receipt.intent_id,
        project_id=run_receipt.project_id,
        run_receipt_sha256=_model_sha256(run_receipt),
        source_status=outcome.status,
        outcome_status=outcome.outcome_status,
        content=content,
        content_sha256=_model_sha256(content),
    )


def _model_sha256(model: FrozenModel) -> str:
    return hashlib.sha256(model.model_dump_json().encode("utf-8")).hexdigest()


def _grant_message(
    target: ChannelTarget,
    grant: StandingAutonomyGrant,
    proposal: StandingProposal,
) -> IncomingMessage:
    return IncomingMessage(
        channel_name=target.channel_name,
        source=target,
        sender_id=grant.owner_id,
        content=MessageContent(text="Scheduled owner-preauthorized standing work."),
        raw_ref=f"standing-autonomy:{grant.grant_id}:{proposal.proposal_id}",
    )


def _preauthorized_prompt(proposal: StandingProposal) -> str:
    evidence = "\n".join(
        f"A{index}: {item}" for index, item in enumerate(proposal.acceptance_evidence, start=1)
    )
    stops = "\n".join(
        f"S{index}: {item}" for index, item in enumerate(proposal.stop_conditions, start=1)
    )
    return (
        "Owner-preauthorized standing-charter inspection.\n"
        f"proposal_id: {proposal.proposal_id}\n"
        f"charter_id: {proposal.charter_id}\n"
        f"objective: {proposal.objective}\n\n"
        f"Acceptance evidence:\n{evidence}\n\n"
        f"Stop conditions:\n{stops}\n\n"
        "Observe and report only. The enforced execution boundary is read-only. "
        "Return JSON only under the enforced schema. Cite repository-relative source paths "
        "and 1-based line numbers for every criterion. Mark complete only when every A item "
        "is met and gaps is empty; otherwise mark blocked with at least one gap. Confirm every "
        f"S item with observed=true. Keep the entire serialized JSON at or below "
        f"{MAX_STANDING_RESULT_CHARS} characters. Use no more than "
        f"{MAX_STANDING_VERIFIED_SOURCES} distinct source references and cite only files at "
        f"or below {MAX_STANDING_SOURCE_FILE_BYTES} bytes."
    )


def _secure_preauthorized_task(task: Task, grant: StandingAutonomyGrant) -> Task:
    secured = task_without_provider_session(task)
    secured = task_with_exact_output_constraint(secured)
    return task_with_preauthorized_execution(
        secured,
        grant_id=grant.grant_id,
        expires_at=grant.expires_at,
        max_duration_seconds=grant.max_duration_seconds,
    )


def _task_with_scheduled_intent(task: Task, intent_id: str) -> Task:
    metadata = tuple(
        entry for entry in task.metadata if entry.key != SCHEDULED_AUTONOMY_INTENT_ID_KEY
    )
    return task.model_copy(
        update={
            "metadata": (
                *metadata,
                MetadataEntry(key=SCHEDULED_AUTONOMY_INTENT_ID_KEY, value=intent_id),
            )
        }
    )


def _run_receipt(intent_id: str, project_id: str) -> StandingAutonomyRunReceipt:
    return StandingAutonomyRunReceipt(
        intent_id=intent_id,
        project_id=project_id,
        disposition=StandingAutonomyRunDisposition.NOT_APPLICABLE,
    )


def _recorded_run_receipt(
    intent_id: str,
    proposal: StandingProposal,
) -> StandingAutonomyRunReceipt:
    assert proposal.task_id is not None
    return StandingAutonomyRunReceipt(
        intent_id=intent_id,
        project_id=proposal.project_id,
        disposition=StandingAutonomyRunDisposition.DISPATCH_RECORDED,
        proposal_id=proposal.proposal_id,
        task_id=proposal.task_id,
    )


def _standing_autonomy_receipt(
    proposal: StandingProposal,
    snapshot: TaskSnapshot | None,
    evidence_root: Path | None,
) -> StandingAutonomyReceipt:
    decided_at = proposal.decided_at or proposal.created_at
    if not _snapshot_matches_proposal(snapshot, proposal):
        return StandingAutonomyReceipt(
            proposal_id=proposal.proposal_id,
            task_id=proposal.task_id,
            charter_id=proposal.charter_id,
            authorization_id=proposal.authorization_id,
            status=StandingAutonomyReceiptStatus.EVIDENCE_MISSING,
            decided_at=decided_at,
            outcome_status=StandingAutonomyOutcomeStatus.MISSING,
        )
    assert snapshot is not None
    if snapshot.status not in _ACTIVE_TASK_STATUSES and proposal.usage is None:
        return StandingAutonomyReceipt(
            proposal_id=proposal.proposal_id,
            task_id=proposal.task_id,
            charter_id=proposal.charter_id,
            authorization_id=proposal.authorization_id,
            status=StandingAutonomyReceiptStatus.EVIDENCE_MISSING,
            decided_at=decided_at,
            finished_at=snapshot.updated_at,
            elapsed_seconds=max(0.0, (snapshot.updated_at - decided_at).total_seconds()),
            outcome_status=StandingAutonomyOutcomeStatus.MISSING,
        )
    status = StandingAutonomyReceiptStatus(snapshot.status.value)
    terminal = snapshot.status in {
        TaskStatus.DONE,
        TaskStatus.FAILED,
        TaskStatus.INTERRUPTED,
        TaskStatus.REJECTED,
    }
    result = proposal.result_receipt
    outcome = StandingAutonomyOutcomeStatus.PENDING
    if terminal:
        outcome = StandingAutonomyOutcomeStatus.MISSING
    if snapshot.status is TaskStatus.DONE and result is not None:
        outcome = StandingAutonomyOutcomeStatus(result.status.value)
    evidence_status = None
    if (
        snapshot.status is TaskStatus.DONE
        and result is not None
        and result.status is StandingResultContractStatus.COMPLETE
        and evidence_root is not None
    ):
        evidence_status = standing_result_evidence_status(result, evidence_root)
        if evidence_status is StandingEvidenceStatus.DRIFTED:
            outcome = StandingAutonomyOutcomeStatus.DRIFTED
        elif evidence_status is StandingEvidenceStatus.MISSING:
            outcome = StandingAutonomyOutcomeStatus.MISSING
    return StandingAutonomyReceipt(
        proposal_id=proposal.proposal_id,
        task_id=proposal.task_id,
        charter_id=proposal.charter_id,
        authorization_id=proposal.authorization_id,
        status=status,
        decided_at=decided_at,
        finished_at=snapshot.updated_at if terminal else None,
        elapsed_seconds=(
            max(0.0, (snapshot.updated_at - decided_at).total_seconds()) if terminal else None
        ),
        total_tokens=None if proposal.usage is None else proposal.usage.total_tokens,
        outcome_status=outcome,
        criteria_met=None if result is None else result.criteria_met,
        criteria_total=None if result is None else result.criteria_total,
        verified_sources=None if result is None else result.verified_sources,
        evidence_status=evidence_status,
        result_failure=None if result is None else result.failure,
    )


def _snapshot_matches_proposal(
    snapshot: TaskSnapshot | None,
    proposal: StandingProposal,
) -> bool:
    if snapshot is None or proposal.authorization_id is None:
        return False
    metadata = {entry.key: str(entry.value) for entry in snapshot.metadata}
    return (
        metadata.get("aico.standing_proposal_id") == proposal.proposal_id
        and metadata.get(PREAUTHORIZED_GRANT_ID_KEY) == proposal.authorization_id
    )


_ACTIVE_TASK_STATUSES = {TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL}
