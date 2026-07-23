"""Independent scenario evidence finalization for AICO benchmark runs."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import Field, model_validator

from aico.app.boss_absent_aico_runner import (
    AicoBenchmarkRunPhase,
    AicoBenchmarkRunState,
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


class AicoScenarioEvidenceReceipt(FrozenModel):
    """Bounded facts recorded by a harness outside the system under test."""

    version: Literal[1] = 1
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    role_state_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    observer_kind: Literal["independent_harness"] = "independent_harness"
    observer_build: str = Field(min_length=1, max_length=128)
    events_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_status: BenchmarkTerminalStatus
    terminal_consumed_checkpoint_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    wall_seconds: float = Field(ge=0)
    human_interventions: int = Field(ge=0, le=100)
    evidence: BenchmarkEvidenceSet

    restart_observed: bool = False
    replayed_dispatches: int = Field(default=0, ge=0)
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

    evidence_drift_injected: bool = False
    evidence_drift_detected: bool = False
    stale_result_published: bool = False

    irrelevant_source_exposed: bool = False
    irrelevant_source_consumed: bool = False
    cited_sources_allowlisted: bool = True

    @model_validator(mode="after")
    def validate_complete_groups(self) -> AicoScenarioEvidenceReceipt:
        takeover = (
            self.takeover_actions,
            self.takeover_seconds,
            self.takeover_evidence_sha256,
        )
        if any(value is not None for value in takeover) and not all(
            value is not None for value in takeover
        ):
            raise ValueError("AICO scenario takeover evidence is incomplete")
        if self.restart_observed != (self.restart_evidence_sha256 is not None):
            raise ValueError("AICO scenario restart evidence is incomplete")
        if self.approval_grants > self.approval_requests:
            raise ValueError("AICO scenario approval grants exceed requests")
        approval = (
            self.approval_request_sha256,
            self.approval_grant_sha256,
            self.approval_action_receipt_sha256,
        )
        if any(value is not None for value in approval) and not all(
            value is not None for value in approval
        ):
            raise ValueError("AICO scenario approval identity evidence is incomplete")
        return self


def finalize_aico_benchmark_result(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    state: AicoBenchmarkRunState,
    receipt: AicoScenarioEvidenceReceipt,
) -> BossAbsentTaskResult:
    """Produce one scoreable result only after the independent harness closes every gate."""
    contract_sha = canonical_sha256(contract)
    _validate_identity(contract, task, state, receipt, contract_sha)
    _validate_role_state(contract, task, state, receipt)
    _validate_scenario(task, state, receipt)
    checkpoints = _result_checkpoints(state)
    return BossAbsentTaskResult(
        benchmark_id=contract.benchmark_id,
        contract_sha256=contract_sha,
        system=BenchmarkSystem.AICO,
        task_id=task.task_id,
        dispatched=True,
        terminal_status=receipt.terminal_status,
        wall_seconds=receipt.wall_seconds,
        human_interventions=receipt.human_interventions,
        total_tokens=state.total_tokens,
        evidence=receipt.evidence,
        role_checkpoints=checkpoints,
        takeover_actions=receipt.takeover_actions,
        takeover_seconds=receipt.takeover_seconds,
        takeover_evidence_sha256=receipt.takeover_evidence_sha256,
        restart_evidence_sha256=receipt.restart_evidence_sha256,
        approval_evidence_sha256=receipt.approval_evidence_sha256,
    )


def _validate_identity(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    state: AicoBenchmarkRunState,
    receipt: AicoScenarioEvidenceReceipt,
    contract_sha: str,
) -> None:
    identity = (
        state.contract_sha256 == contract_sha
        and state.benchmark_id == contract.benchmark_id
        and state.task_id == task.task_id
        and receipt.contract_sha256 == contract_sha
        and receipt.task_id == task.task_id
        and receipt.role_state_sha256 == canonical_sha256(state)
    )
    if not identity:
        raise ValueError("AICO scenario evidence identity drifted")


def _validate_role_state(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    state: AicoBenchmarkRunState,
    receipt: AicoScenarioEvidenceReceipt,
) -> None:
    if state.phase is not AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE:
        raise ValueError("AICO scenario evidence requires a complete role chain")
    if len(state.checkpoints) != len(task.required_roles):
        raise ValueError("AICO scenario evidence role chain is incomplete")
    if tuple(item.role for item in state.checkpoints) != task.required_roles:
        raise ValueError("AICO scenario evidence role order drifted")
    if task.collaboration_required and len({item.agent_id for item in state.checkpoints}) != len(
        state.checkpoints
    ):
        raise ValueError("AICO scenario evidence reused an Agent across roles")
    if task.collaboration_required and len(
        {item.provider_execution_sha256 for item in state.checkpoints}
    ) != len(state.checkpoints):
        raise ValueError("AICO scenario evidence reused a provider execution across roles")
    fixture_sha = hashlib.sha256(task.fixture.encode("utf-8")).hexdigest()
    if any(item.input_fixture_sha256 != fixture_sha for item in state.checkpoints):
        raise ValueError("AICO scenario evidence fixture fingerprint drifted")
    for index, checkpoint in enumerate(state.checkpoints):
        expected = None if index == 0 else state.checkpoints[index - 1].artifact_sha256
        if checkpoint.consumed_checkpoint_sha256 != expected:
            raise ValueError("AICO scenario role checkpoint chain drifted")
    if state.total_tokens <= 0 or state.total_tokens > contract.max_total_tokens:
        raise ValueError("AICO scenario evidence has invalid shared provider usage")
    if receipt.terminal_consumed_checkpoint_sha256 != state.checkpoints[-1].artifact_sha256:
        raise ValueError("AICO terminal did not consume the final role checkpoint")
    if receipt.evidence.budget_receipt.status is not BenchmarkEvidenceStatus.PRESENT:
        raise ValueError("AICO scenario evidence is missing the independent budget receipt")


def _validate_scenario(
    task: BossAbsentTask,
    state: AicoBenchmarkRunState,
    receipt: AicoScenarioEvidenceReceipt,
) -> None:
    _validate_human_interventions(task, receipt)
    _validate_restart(task, state, receipt)
    _validate_takeover(task, receipt)
    _validate_approval(task, state, receipt)
    _validate_drift(task, receipt)
    _validate_budget_pressure(task, receipt)


def _validate_human_interventions(
    task: BossAbsentTask,
    receipt: AicoScenarioEvidenceReceipt,
) -> None:
    expected = 1 if task.approval_required else 0
    if receipt.human_interventions != expected:
        raise ValueError("AICO scenario human intervention count drifted")


def _validate_restart(
    task: BossAbsentTask,
    state: AicoBenchmarkRunState,
    receipt: AicoScenarioEvidenceReceipt,
) -> None:
    if task.restart_required:
        if (
            not receipt.restart_observed
            or receipt.replayed_dispatches != 0
            or state.restart_count != 1
            or len(state.checkpoints) < 2
            or state.checkpoints[0].runtime_instance_sha256
            == state.checkpoints[1].runtime_instance_sha256
        ):
            raise ValueError("AICO restart scenario is missing no-replay restart evidence")
        return
    if receipt.restart_observed or receipt.replayed_dispatches != 0 or state.restart_count != 0:
        raise ValueError("AICO non-restart scenario contains restart claims")


def _validate_takeover(
    task: BossAbsentTask,
    receipt: AicoScenarioEvidenceReceipt,
) -> None:
    present = receipt.takeover_evidence_sha256 is not None
    if present != task.im_takeover_required:
        raise ValueError("AICO scenario IM takeover evidence does not match the task")


def _validate_approval(
    task: BossAbsentTask,
    state: AicoBenchmarkRunState,
    receipt: AicoScenarioEvidenceReceipt,
) -> None:
    if task.approval_required:
        if (
            state.approval_checkpoint is None
            or receipt.approval_requests != 1
            or receipt.approval_grants != 1
            or receipt.mutation_before_approval
            or receipt.approval_evidence_sha256 is None
            or receipt.approval_request_sha256 != state.approval_checkpoint.request_sha256
            or receipt.approval_grant_sha256 != state.approval_checkpoint.grant_sha256
            or receipt.approval_action_receipt_sha256
            != state.approval_checkpoint.action_receipt_sha256
        ):
            raise ValueError("AICO approval scenario did not preserve the exact approval fence")
        return
    if (
        receipt.approval_requests != 0
        or receipt.approval_grants != 0
        or receipt.mutation_before_approval
        or receipt.approval_evidence_sha256 is not None
        or receipt.approval_request_sha256 is not None
        or receipt.approval_grant_sha256 is not None
        or receipt.approval_action_receipt_sha256 is not None
        or state.approval_checkpoint is not None
    ):
        raise ValueError("AICO non-approval scenario contains approval claims")


def _validate_drift(
    task: BossAbsentTask,
    receipt: AicoScenarioEvidenceReceipt,
) -> None:
    observed = (
        receipt.evidence_drift_injected,
        receipt.evidence_drift_detected,
        receipt.stale_result_published,
    )
    if task.scenario is BenchmarkScenario.EVIDENCE_DRIFT:
        if observed != (True, True, False):
            raise ValueError("AICO evidence-drift scenario accepted stale evidence")
        return
    if observed != (False, False, False):
        raise ValueError("AICO non-drift scenario contains drift claims")


def _validate_budget_pressure(
    task: BossAbsentTask,
    receipt: AicoScenarioEvidenceReceipt,
) -> None:
    observed = (
        receipt.irrelevant_source_exposed,
        receipt.irrelevant_source_consumed,
        receipt.cited_sources_allowlisted,
    )
    if task.budget_pressure:
        if observed != (True, False, True):
            raise ValueError("AICO budget-pressure scenario consumed invalid evidence")
        return
    if observed != (False, False, True):
        raise ValueError("AICO non-budget scenario contains source-pressure claims")


def _result_checkpoints(
    state: AicoBenchmarkRunState,
) -> tuple[BenchmarkRoleCheckpoint, ...]:
    result: list[BenchmarkRoleCheckpoint] = []
    for index, checkpoint in enumerate(state.checkpoints):
        next_consumer = (
            "terminal" if index == len(state.checkpoints) - 1 else f"role-checkpoint-{index + 2}"
        )
        result.append(
            BenchmarkRoleCheckpoint(
                checkpoint_id=f"role-checkpoint-{index + 1}",
                role=checkpoint.role,
                agent_id=checkpoint.agent_id,
                artifact_sha256=checkpoint.artifact_sha256,
                consumed_by=(next_consumer,),
            )
        )
    return tuple(result)
