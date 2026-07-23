"""Independent scenario evidence finalization for native Codex Goal runs."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import Field, model_validator

from aico.app.boss_absent_codex_goal_host import (
    CodexGoalHostAdmissionReceipt,
    CodexGoalHostRunReceipt,
    CodexGoalTurnSource,
)
from aico.core.boss_absent_benchmark import (
    BenchmarkEvidenceSet,
    BenchmarkEvidenceStatus,
    BenchmarkRoleCheckpoint,
    BenchmarkScenario,
    BenchmarkSystem,
    BenchmarkTerminalStatus,
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    BossAbsentTaskResult,
    canonical_sha256,
)
from aico.core.models import FrozenModel

Sha256 = str


class CodexGoalRoleEvidence(FrozenModel):
    """One role execution observed outside the native Goal host."""

    sequence: int = Field(ge=1, le=32)
    role: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,31}$")
    agent_identity_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    provider_execution_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_instance_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    source_turn_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    input_fixture_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    consumed_checkpoint_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )


class CodexGoalScenarioEvidenceReceipt(FrozenModel):
    """Bounded facts recorded by a harness outside Codex Goal."""

    version: Literal[1] = 1
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    host_admission_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    host_run_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    role_chain_observation_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    observer_kind: Literal["independent_harness"] = "independent_harness"
    observer_build: str = Field(min_length=1, max_length=128)
    events_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_status: BenchmarkTerminalStatus
    terminal_consumed_checkpoint_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    wall_seconds: float = Field(ge=0)
    human_interventions: int = Field(ge=0, le=100)
    evidence: BenchmarkEvidenceSet
    roles: tuple[CodexGoalRoleEvidence, ...] = Field(min_length=1, max_length=32)

    restart_observed: bool = False
    replayed_turns: int = Field(default=0, ge=0)
    restart_evidence_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    takeover_actions: int | None = Field(default=None, ge=0)
    takeover_seconds: float | None = Field(default=None, ge=0)
    takeover_evidence_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    approval_requests: int = Field(default=0, ge=0)
    approval_grants: int = Field(default=0, ge=0)
    mutation_before_approval: bool = False
    approval_evidence_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    approval_request_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    approval_grant_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    approval_action_receipt_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    approval_turn_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    evidence_drift_injected: bool = False
    evidence_drift_detected: bool = False
    stale_result_published: bool = False
    irrelevant_source_exposed: bool = False
    irrelevant_source_consumed: bool = False
    cited_sources_allowlisted: bool = True

    @model_validator(mode="after")
    def validate_complete_groups(self) -> CodexGoalScenarioEvidenceReceipt:
        takeover = (
            self.takeover_actions,
            self.takeover_seconds,
            self.takeover_evidence_sha256,
        )
        if any(value is not None for value in takeover) and not all(
            value is not None for value in takeover
        ):
            raise ValueError("Codex Goal scenario takeover evidence is incomplete")
        if self.restart_observed != (self.restart_evidence_sha256 is not None):
            raise ValueError("Codex Goal scenario restart evidence is incomplete")
        if self.approval_grants > self.approval_requests:
            raise ValueError("Codex Goal scenario approval grants exceed requests")
        approval = (
            self.approval_request_sha256,
            self.approval_grant_sha256,
            self.approval_action_receipt_sha256,
            self.approval_turn_sha256,
        )
        if any(value is not None for value in approval) and not all(
            value is not None for value in approval
        ):
            raise ValueError("Codex Goal scenario approval identity evidence is incomplete")
        return self


def finalize_codex_goal_benchmark_result(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
    host_run: CodexGoalHostRunReceipt,
    receipt: CodexGoalScenarioEvidenceReceipt,
) -> BossAbsentTaskResult:
    """Produce a scoreable native Goal result only after every evidence gate closes."""
    contract_sha = canonical_sha256(contract)
    _validate_identity(contract_sha, task, admission, host_run, receipt)
    _validate_roles(contract, task, host_run, receipt)
    _validate_scenario(task, host_run, receipt)
    return BossAbsentTaskResult(
        benchmark_id=contract.benchmark_id,
        contract_sha256=contract_sha,
        system=BenchmarkSystem.CODEX_GOAL,
        task_id=task.task_id,
        dispatched=True,
        terminal_status=receipt.terminal_status,
        wall_seconds=receipt.wall_seconds,
        human_interventions=receipt.human_interventions,
        total_tokens=host_run.total_tokens,
        evidence=receipt.evidence,
        role_checkpoints=_result_checkpoints(receipt.roles),
        takeover_actions=receipt.takeover_actions,
        takeover_seconds=receipt.takeover_seconds,
        takeover_evidence_sha256=receipt.takeover_evidence_sha256,
        restart_evidence_sha256=receipt.restart_evidence_sha256,
        approval_evidence_sha256=receipt.approval_evidence_sha256,
    )


def _validate_identity(
    contract_sha: str,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
    host_run: CodexGoalHostRunReceipt,
    receipt: CodexGoalScenarioEvidenceReceipt,
) -> None:
    admission_sha = canonical_sha256(admission)
    identity = (
        admission.contract_sha256 == contract_sha
        and host_run.contract_sha256 == contract_sha
        and host_run.host_admission_sha256 == admission_sha
        and receipt.contract_sha256 == contract_sha
        and receipt.task_id == task.task_id
        and receipt.host_admission_sha256 == admission_sha
        and receipt.host_run_sha256 == canonical_sha256(host_run)
    )
    if not identity:
        raise ValueError("Codex Goal scenario evidence identity drifted")


def _validate_roles(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    host_run: CodexGoalHostRunReceipt,
    receipt: CodexGoalScenarioEvidenceReceipt,
) -> None:
    if host_run.terminal_status != "complete":
        raise ValueError("Codex Goal scenario requires a complete native host run")
    if receipt.terminal_status is not BenchmarkTerminalStatus.COMPLETE:
        raise ValueError("Codex Goal scenario receipt is not complete")
    if host_run.turns[0].opaque_input_sha256 != canonical_sha256(task):
        raise ValueError("Codex Goal initial host turn did not receive the frozen task")
    if len(receipt.roles) != len(task.required_roles):
        raise ValueError("Codex Goal scenario role chain is incomplete")
    if tuple(role.role for role in receipt.roles) != task.required_roles:
        raise ValueError("Codex Goal scenario role order drifted")
    if tuple(role.sequence for role in receipt.roles) != tuple(range(1, len(receipt.roles) + 1)):
        raise ValueError("Codex Goal scenario role sequence is not contiguous")
    if task.collaboration_required and len(
        {role.agent_identity_sha256 for role in receipt.roles}
    ) != len(receipt.roles):
        raise ValueError("Codex Goal scenario reused an Agent identity across roles")
    if task.collaboration_required and len(
        {role.provider_execution_sha256 for role in receipt.roles}
    ) != len(receipt.roles):
        raise ValueError("Codex Goal scenario reused a provider execution across roles")
    fixture_sha = hashlib.sha256(task.fixture.encode("utf-8")).hexdigest()
    if any(role.input_fixture_sha256 != fixture_sha for role in receipt.roles):
        raise ValueError("Codex Goal scenario fixture fingerprint drifted")
    turns_by_sha = {turn.turn_sha256: turn for turn in host_run.turns}
    if any(role.source_turn_sha256 not in turns_by_sha for role in receipt.roles):
        raise ValueError("Codex Goal role evidence references an unobserved host turn")
    if any(
        role.runtime_instance_sha256
        != turns_by_sha[role.source_turn_sha256].runtime_instance_sha256
        for role in receipt.roles
    ):
        raise ValueError("Codex Goal role evidence runtime drifted from its source turn")
    for index, role in enumerate(receipt.roles):
        expected = None if index == 0 else receipt.roles[index - 1].artifact_sha256
        if role.consumed_checkpoint_sha256 != expected:
            raise ValueError("Codex Goal scenario role checkpoint chain drifted")
    if host_run.total_tokens > contract.max_total_tokens:
        raise ValueError("Codex Goal scenario exceeded the shared provider budget")
    if receipt.terminal_consumed_checkpoint_sha256 != receipt.roles[-1].artifact_sha256:
        raise ValueError("Codex Goal terminal did not consume the final role checkpoint")
    if receipt.evidence.budget_receipt.status is not BenchmarkEvidenceStatus.PRESENT:
        raise ValueError("Codex Goal scenario is missing the independent budget receipt")


def _validate_scenario(
    task: BossAbsentTask,
    host_run: CodexGoalHostRunReceipt,
    receipt: CodexGoalScenarioEvidenceReceipt,
) -> None:
    expected_interventions = int(task.approval_required)
    if (
        receipt.human_interventions != expected_interventions
        or host_run.human_interventions != expected_interventions
    ):
        raise ValueError("Codex Goal scenario human intervention count drifted")
    _validate_restart(task, receipt)
    _validate_takeover(task, receipt)
    _validate_approval(task, host_run, receipt)
    _validate_drift(task, receipt)
    _validate_budget_pressure(task, receipt)


def _validate_restart(
    task: BossAbsentTask,
    receipt: CodexGoalScenarioEvidenceReceipt,
) -> None:
    if task.restart_required:
        if (
            not receipt.restart_observed
            or receipt.replayed_turns != 0
            or len(receipt.roles) < 2
            or receipt.roles[0].runtime_instance_sha256 == receipt.roles[1].runtime_instance_sha256
        ):
            raise ValueError("Codex Goal restart scenario is missing no-replay restart evidence")
        return
    if receipt.restart_observed or receipt.replayed_turns != 0:
        raise ValueError("Codex Goal non-restart scenario contains restart claims")


def _validate_takeover(
    task: BossAbsentTask,
    receipt: CodexGoalScenarioEvidenceReceipt,
) -> None:
    present = receipt.takeover_evidence_sha256 is not None
    if present != task.im_takeover_required:
        raise ValueError("Codex Goal scenario IM takeover evidence does not match the task")


def _validate_approval(
    task: BossAbsentTask,
    host_run: CodexGoalHostRunReceipt,
    receipt: CodexGoalScenarioEvidenceReceipt,
) -> None:
    identity = (
        receipt.approval_request_sha256,
        receipt.approval_grant_sha256,
        receipt.approval_action_receipt_sha256,
        receipt.approval_turn_sha256,
    )
    owner_turns = tuple(
        turn for turn in host_run.turns if turn.source is CodexGoalTurnSource.OWNER_TAKEOVER
    )
    if task.approval_required:
        if (
            receipt.approval_requests != 1
            or receipt.approval_grants != 1
            or receipt.mutation_before_approval
            or receipt.approval_evidence_sha256 is None
            or any(value is None for value in identity)
            or len(owner_turns) != 1
            or receipt.approval_turn_sha256 != owner_turns[0].turn_sha256
            or receipt.approval_grant_sha256 != owner_turns[0].opaque_input_sha256
        ):
            raise ValueError("Codex Goal approval scenario did not preserve the approval fence")
        return
    if (
        receipt.approval_requests != 0
        or receipt.approval_grants != 0
        or receipt.mutation_before_approval
        or receipt.approval_evidence_sha256 is not None
        or any(value is not None for value in identity)
        or owner_turns
    ):
        raise ValueError("Codex Goal non-approval scenario contains approval claims")


def _validate_drift(
    task: BossAbsentTask,
    receipt: CodexGoalScenarioEvidenceReceipt,
) -> None:
    observed = (
        receipt.evidence_drift_injected,
        receipt.evidence_drift_detected,
        receipt.stale_result_published,
    )
    expected = (
        (True, True, False)
        if task.scenario is BenchmarkScenario.EVIDENCE_DRIFT
        else (False, False, False)
    )
    if observed != expected:
        raise ValueError("Codex Goal scenario evidence-drift claims are invalid")


def _validate_budget_pressure(
    task: BossAbsentTask,
    receipt: CodexGoalScenarioEvidenceReceipt,
) -> None:
    observed = (
        receipt.irrelevant_source_exposed,
        receipt.irrelevant_source_consumed,
        receipt.cited_sources_allowlisted,
    )
    expected = (True, False, True) if task.budget_pressure else (False, False, True)
    if observed != expected:
        raise ValueError("Codex Goal scenario source-pressure claims are invalid")


def _result_checkpoints(
    roles: tuple[CodexGoalRoleEvidence, ...],
) -> tuple[BenchmarkRoleCheckpoint, ...]:
    return tuple(
        BenchmarkRoleCheckpoint(
            checkpoint_id=f"role-checkpoint-{index}",
            role=role.role,
            agent_id=role.agent_identity_sha256,
            artifact_sha256=role.artifact_sha256,
            consumed_by=("terminal" if index == len(roles) else f"role-checkpoint-{index + 1}",),
        )
        for index, role in enumerate(roles, start=1)
    )
