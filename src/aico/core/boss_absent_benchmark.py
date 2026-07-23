"""Deterministic, evidence-first scoring for the boss-absent benchmark."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from fractions import Fraction
from statistics import median
from typing import Annotated, Literal

from pydantic import Field, model_validator

from aico.core.models import FrozenModel

BENCHMARK_SYSTEMS = ("aico", "codex_goal")
EVIDENCE_CATEGORY_COUNT = 5
BoundedText = Annotated[str, Field(min_length=1, max_length=1_000)]
FixtureText = Annotated[str, Field(min_length=1, max_length=16_384)]
RoleId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{1,31}$")]
CheckpointId = Annotated[str, Field(pattern=r"^(?:[a-z0-9][a-z0-9-]{2,63}|terminal)$")]


class BenchmarkScenario(StrEnum):
    NORMAL = "normal_completion"
    RESTART = "cross_restart"
    EVIDENCE_DRIFT = "evidence_drift"
    APPROVAL = "approval_required"
    BUDGET_PRESSURE = "budget_pressure"


class BenchmarkSystem(StrEnum):
    AICO = "aico"
    CODEX_GOAL = "codex_goal"


class BenchmarkTerminalStatus(StrEnum):
    COMPLETE = "complete"
    BLOCKED = "blocked"
    FAILED = "failed"
    INCOMPLETE = "incomplete"


class BenchmarkEvidenceStatus(StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    FAILED = "failed"


class MetricComparison(StrEnum):
    BETTER = "better"
    EQUAL = "equal"
    WORSE = "worse"
    UNSCORABLE = "unscorable"


class BossAbsentTask(FrozenModel):
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    scenario: BenchmarkScenario
    objective: str = Field(min_length=1, max_length=2_000)
    fixture: FixtureText
    acceptance: tuple[BoundedText, ...] = Field(min_length=1, max_length=12)
    required_roles: tuple[RoleId, ...] = Field(min_length=1, max_length=8)
    unattended_eligible: bool
    collaboration_required: bool
    restart_required: bool = False
    im_takeover_required: bool = False
    approval_required: bool = False
    budget_pressure: bool = False

    @model_validator(mode="after")
    def validate_scenario_contract(self) -> BossAbsentTask:
        if len(set(self.required_roles)) != len(self.required_roles):
            raise ValueError("benchmark task roles must be unique")
        required_flag = {
            BenchmarkScenario.RESTART: self.restart_required,
            BenchmarkScenario.APPROVAL: self.approval_required,
            BenchmarkScenario.BUDGET_PRESSURE: self.budget_pressure,
        }.get(self.scenario, True)
        if not required_flag:
            raise ValueError("benchmark task scenario flag is missing")
        if self.scenario is BenchmarkScenario.APPROVAL and self.unattended_eligible:
            raise ValueError("approval task cannot be unattended eligible")
        return self


class BossAbsentTaskSet(FrozenModel):
    version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=128)
    tasks: tuple[BossAbsentTask, ...] = Field(min_length=5, max_length=64)

    @model_validator(mode="after")
    def validate_frozen_scenarios(self) -> BossAbsentTaskSet:
        task_ids = [task.task_id for task in self.tasks]
        if len(set(task_ids)) != len(task_ids):
            raise ValueError("benchmark task ids must be unique")
        scenarios = {task.scenario for task in self.tasks}
        if scenarios != set(BenchmarkScenario):
            raise ValueError("benchmark v1 requires all five frozen scenarios")
        if not any(task.collaboration_required for task in self.tasks):
            raise ValueError("benchmark requires a collaboration task")
        if not any(task.im_takeover_required for task in self.tasks):
            raise ValueError("benchmark requires an IM takeover task")
        return self


class BossAbsentBenchmarkContract(FrozenModel):
    version: Literal[1] = 1
    benchmark_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    frozen_at: datetime
    model: str = Field(min_length=1, max_length=128)
    reasoning_effort: str = Field(min_length=1, max_length=32)
    repo_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    aico_version: str = Field(min_length=1, max_length=128)
    codex_cli_version: str = Field(min_length=1, max_length=128)
    wall_window_seconds: int = Field(ge=60, le=604_800)
    max_total_tokens: int = Field(ge=1_000, le=100_000_000)
    takeover_action_cap: int = Field(default=20, ge=1, le=1_000)
    takeover_seconds_cap: int = Field(default=900, ge=1, le=86_400)
    task_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    project_assignment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_frozen_at(self) -> BossAbsentBenchmarkContract:
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise ValueError("benchmark freeze time must be timezone-aware")
        return self


class BenchmarkEvidenceProof(FrozenModel):
    status: BenchmarkEvidenceStatus
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_proof(self) -> BenchmarkEvidenceProof:
        if self.status is BenchmarkEvidenceStatus.MISSING and self.sha256 is not None:
            raise ValueError("missing benchmark evidence cannot carry a SHA-256")
        if self.status is not BenchmarkEvidenceStatus.MISSING and self.sha256 is None:
            raise ValueError("observed benchmark evidence requires a SHA-256")
        return self


class BenchmarkEvidenceSet(FrozenModel):
    terminal: BenchmarkEvidenceProof
    acceptance: BenchmarkEvidenceProof
    source_integrity: BenchmarkEvidenceProof
    test_gate: BenchmarkEvidenceProof
    budget_receipt: BenchmarkEvidenceProof

    def proofs(self) -> tuple[BenchmarkEvidenceProof, ...]:
        return (
            self.terminal,
            self.acceptance,
            self.source_integrity,
            self.test_gate,
            self.budget_receipt,
        )


class BenchmarkRoleCheckpoint(FrozenModel):
    checkpoint_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    role: RoleId
    agent_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,63}$")
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumed_by: tuple[CheckpointId, ...] = Field(min_length=1, max_length=8)


class BossAbsentTaskResult(FrozenModel):
    version: Literal[1] = 1
    benchmark_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    system: BenchmarkSystem
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    dispatched: bool
    terminal_status: BenchmarkTerminalStatus
    wall_seconds: float | None = Field(default=None, ge=0)
    human_interventions: int = Field(default=0, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    evidence: BenchmarkEvidenceSet
    role_checkpoints: tuple[BenchmarkRoleCheckpoint, ...] = Field(default=(), max_length=32)
    takeover_actions: int | None = Field(default=None, ge=0)
    takeover_seconds: float | None = Field(default=None, ge=0)
    takeover_evidence_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    restart_evidence_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    approval_evidence_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_observations(self) -> BossAbsentTaskResult:
        if self.dispatched != (self.wall_seconds is not None):
            raise ValueError("dispatched benchmark result requires wall time")
        takeover_fields = (
            self.takeover_actions,
            self.takeover_seconds,
            self.takeover_evidence_sha256,
        )
        if any(value is not None for value in takeover_fields) and not all(
            value is not None for value in takeover_fields
        ):
            raise ValueError("takeover observation must be complete")
        checkpoint_ids = [item.checkpoint_id for item in self.role_checkpoints]
        if len(set(checkpoint_ids)) != len(checkpoint_ids):
            raise ValueError("benchmark checkpoint ids must be unique")
        valid_consumers = {*checkpoint_ids, "terminal"}
        if any(
            checkpoint.checkpoint_id in checkpoint.consumed_by
            or not set(checkpoint.consumed_by).issubset(valid_consumers)
            for checkpoint in self.role_checkpoints
        ):
            raise ValueError("benchmark checkpoint consumer is invalid")
        if not self.dispatched and (
            self.terminal_status is not BenchmarkTerminalStatus.INCOMPLETE
            or self.total_tokens is not None
            or self.role_checkpoints
            or any(value is not None for value in takeover_fields)
            or self.restart_evidence_sha256 is not None
            or self.approval_evidence_sha256 is not None
        ):
            raise ValueError("undispatched benchmark result cannot claim execution evidence")
        if (
            self.dispatched
            and self.evidence.budget_receipt.status is BenchmarkEvidenceStatus.PRESENT
            and self.total_tokens is None
        ):
            raise ValueError("present budget receipt requires provider usage")
        return self


class BenchmarkRate(FrozenModel):
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    value: float | None = Field(default=None, ge=0, le=1)


class BenchmarkTakeoverCost(FrozenModel):
    eligible_tasks: int = Field(ge=0)
    completed_takeovers: int = Field(ge=0)
    median_effective_actions: float | None = Field(default=None, ge=0)
    median_effective_seconds: float | None = Field(default=None, ge=0)


class BossAbsentBenchmarkSummary(FrozenModel):
    version: Literal[1] = 1
    benchmark_id: str
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    system: BenchmarkSystem
    expected_tasks: int = Field(ge=1)
    received_tasks: int = Field(ge=0)
    dispatched_tasks: int = Field(ge=0)
    complete_tasks: int = Field(ge=0)
    unattended_completion: BenchmarkRate
    collaboration_completion: BenchmarkRate
    takeover_cost: BenchmarkTakeoverCost
    budget_loss: BenchmarkRate
    evidence_completeness: BenchmarkRate
    completed_samples_have_full_evidence: bool
    restart_evidence_present: bool
    im_takeover_evidence_present: bool
    approval_evidence_present: bool


class BossAbsentBenchmarkVerdict(FrozenModel):
    version: Literal[1] = 1
    benchmark_id: str
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    aico_wins: bool
    strict_better_metrics: int = Field(ge=0, le=5)
    comparisons: dict[str, MetricComparison]
    gates: dict[str, bool]
    reasons: tuple[str, ...]


def canonical_sha256(model: FrozenModel) -> str:
    payload = json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def score_boss_absent_system(
    contract: BossAbsentBenchmarkContract,
    task_set: BossAbsentTaskSet,
    results: tuple[BossAbsentTaskResult, ...],
    system: BenchmarkSystem,
) -> BossAbsentBenchmarkSummary:
    expected_contract_sha = canonical_sha256(contract)
    _validate_task_set(contract, task_set)
    by_task = _validated_results(contract, task_set, results, system, expected_contract_sha)
    unattended_tasks = tuple(task for task in task_set.tasks if task.unattended_eligible)
    collaboration_tasks = tuple(task for task in task_set.tasks if task.collaboration_required)
    takeover_tasks = tuple(task for task in task_set.tasks if task.im_takeover_required)
    received = tuple(by_task.values())
    completed = tuple(
        result for result in received if result.terminal_status is BenchmarkTerminalStatus.COMPLETE
    )
    return BossAbsentBenchmarkSummary(
        benchmark_id=contract.benchmark_id,
        contract_sha256=expected_contract_sha,
        system=system,
        expected_tasks=len(task_set.tasks),
        received_tasks=len(received),
        dispatched_tasks=sum(result.dispatched for result in received),
        complete_tasks=len(completed),
        unattended_completion=_rate(
            sum(
                _is_unattended_complete(task, by_task.get(task.task_id), contract)
                for task in unattended_tasks
            ),
            len(unattended_tasks),
        ),
        collaboration_completion=_rate(
            sum(
                _collaboration_complete(task, by_task.get(task.task_id))
                for task in collaboration_tasks
            ),
            len(collaboration_tasks),
        ),
        takeover_cost=_takeover_cost(contract, takeover_tasks, by_task),
        budget_loss=_budget_loss(contract, received),
        evidence_completeness=_evidence_completeness(task_set, by_task),
        completed_samples_have_full_evidence=bool(completed)
        and all(_evidence_count(result) == EVIDENCE_CATEGORY_COUNT for result in completed),
        restart_evidence_present=any(
            task.restart_required
            and (result := by_task.get(task.task_id)) is not None
            and result.restart_evidence_sha256 is not None
            for task in task_set.tasks
        ),
        im_takeover_evidence_present=any(
            task.im_takeover_required
            and (result := by_task.get(task.task_id)) is not None
            and result.takeover_evidence_sha256 is not None
            for task in task_set.tasks
        ),
        approval_evidence_present=all(
            (result := by_task.get(task.task_id)) is not None
            and result.approval_evidence_sha256 is not None
            for task in task_set.tasks
            if task.approval_required
        ),
    )


def compare_boss_absent_summaries(
    contract: BossAbsentBenchmarkContract,
    aico: BossAbsentBenchmarkSummary,
    codex_goal: BossAbsentBenchmarkSummary,
) -> BossAbsentBenchmarkVerdict:
    contract_sha = canonical_sha256(contract)
    if any(
        summary.benchmark_id != contract.benchmark_id
        or summary.contract_sha256 != contract_sha
        or summary.system is not expected
        for summary, expected in (
            (aico, BenchmarkSystem.AICO),
            (codex_goal, BenchmarkSystem.CODEX_GOAL),
        )
    ):
        raise ValueError("benchmark summary does not match frozen contract")
    comparisons = {
        "unattended_completion": _compare_rate(
            aico.unattended_completion, codex_goal.unattended_completion, higher_is_better=True
        ),
        "collaboration_completion": _compare_rate(
            aico.collaboration_completion,
            codex_goal.collaboration_completion,
            higher_is_better=True,
        ),
        "takeover_cost": _compare_takeover(aico.takeover_cost, codex_goal.takeover_cost),
        "budget_loss": _compare_rate(
            aico.budget_loss,
            codex_goal.budget_loss,
            higher_is_better=False,
        ),
        "evidence_completeness": _compare_rate(
            aico.evidence_completeness,
            codex_goal.evidence_completeness,
            higher_is_better=True,
        ),
    }
    strict_better = sum(value is MetricComparison.BETTER for value in comparisons.values())
    gates = {
        "all_metrics_scorable": all(
            value is not MetricComparison.UNSCORABLE for value in comparisons.values()
        ),
        "no_metric_regression": all(
            value not in {MetricComparison.WORSE, MetricComparison.UNSCORABLE}
            for value in comparisons.values()
        ),
        "at_least_four_strictly_better": strict_better >= 4,
        "unattended_strictly_better": comparisons["unattended_completion"]
        is MetricComparison.BETTER,
        "budget_loss_strictly_better": comparisons["budget_loss"] is MetricComparison.BETTER,
        "aico_full_task_coverage": aico.received_tasks == aico.expected_tasks
        and aico.dispatched_tasks == aico.expected_tasks,
        "codex_goal_full_task_coverage": codex_goal.received_tasks == codex_goal.expected_tasks
        and codex_goal.dispatched_tasks == codex_goal.expected_tasks,
        "aico_complete_evidence": aico.completed_samples_have_full_evidence,
        "aico_all_tasks_complete": aico.complete_tasks == aico.expected_tasks,
        "aico_all_collaboration_complete": (
            aico.collaboration_completion.denominator > 0
            and aico.collaboration_completion.numerator == aico.collaboration_completion.denominator
        ),
        "aico_zero_budget_loss": aico.budget_loss.denominator > 0
        and aico.budget_loss.numerator == 0,
        "aico_restart_evidence": aico.restart_evidence_present,
        "aico_im_takeover_evidence": aico.im_takeover_evidence_present,
        "aico_approval_evidence": aico.approval_evidence_present,
    }
    failed = tuple(name for name, passed in gates.items() if not passed)
    return BossAbsentBenchmarkVerdict(
        benchmark_id=contract.benchmark_id,
        contract_sha256=contract_sha,
        aico_wins=not failed,
        strict_better_metrics=strict_better,
        comparisons=comparisons,
        gates=gates,
        reasons=("all benchmark win conditions satisfied",)
        if not failed
        else tuple(f"gate failed: {name}" for name in failed),
    )


def _validate_task_set(
    contract: BossAbsentBenchmarkContract,
    task_set: BossAbsentTaskSet,
) -> None:
    if canonical_sha256(task_set) != contract.task_set_sha256:
        raise ValueError("benchmark task set fingerprint mismatch")


def _validated_results(
    contract: BossAbsentBenchmarkContract,
    task_set: BossAbsentTaskSet,
    results: tuple[BossAbsentTaskResult, ...],
    system: BenchmarkSystem,
    contract_sha: str,
) -> dict[str, BossAbsentTaskResult]:
    task_ids = {task.task_id for task in task_set.tasks}
    selected: dict[str, BossAbsentTaskResult] = {}
    for result in results:
        if result.system is not system:
            continue
        if result.benchmark_id != contract.benchmark_id or result.contract_sha256 != contract_sha:
            raise ValueError("benchmark result does not match frozen contract")
        if result.task_id not in task_ids:
            raise ValueError("benchmark result references unknown task")
        if result.task_id in selected:
            raise ValueError("duplicate benchmark result")
        selected[result.task_id] = result
    return selected


def _rate(numerator: int, denominator: int) -> BenchmarkRate:
    return BenchmarkRate(
        numerator=numerator,
        denominator=denominator,
        value=None if denominator == 0 else numerator / denominator,
    )


def _is_unattended_complete(
    task: BossAbsentTask,
    result: BossAbsentTaskResult | None,
    contract: BossAbsentBenchmarkContract,
) -> bool:
    if result is None or not result.dispatched or result.wall_seconds is None:
        return False
    approval_ok = not task.approval_required or result.approval_evidence_sha256 is not None
    return (
        result.terminal_status is BenchmarkTerminalStatus.COMPLETE
        and result.human_interventions == 0
        and result.wall_seconds <= contract.wall_window_seconds
        and result.evidence.acceptance.status is BenchmarkEvidenceStatus.PRESENT
        and approval_ok
    )


def _collaboration_complete(
    task: BossAbsentTask,
    result: BossAbsentTaskResult | None,
) -> bool:
    if result is None:
        return False
    required = tuple(
        checkpoint
        for checkpoint in result.role_checkpoints
        if checkpoint.role in task.required_roles
    )
    roles = {checkpoint.role for checkpoint in required}
    agents = {checkpoint.agent_id for checkpoint in required}
    return (
        set(task.required_roles).issubset(roles)
        and len(required) == len(task.required_roles)
        and len(agents) >= len(task.required_roles)
        and all(checkpoint.consumed_by for checkpoint in required)
    )


def _takeover_cost(
    contract: BossAbsentBenchmarkContract,
    tasks: tuple[BossAbsentTask, ...],
    results: dict[str, BossAbsentTaskResult],
) -> BenchmarkTakeoverCost:
    effective_actions: list[float] = []
    effective_seconds: list[float] = []
    completed = 0
    for task in tasks:
        result = results.get(task.task_id)
        if result is None or result.takeover_evidence_sha256 is None:
            effective_actions.append(float(contract.takeover_action_cap + 1))
            effective_seconds.append(float(contract.takeover_seconds_cap + 1))
            continue
        assert result.takeover_actions is not None and result.takeover_seconds is not None
        completed += 1
        effective_actions.append(
            float(min(result.takeover_actions, contract.takeover_action_cap + 1))
        )
        effective_seconds.append(min(result.takeover_seconds, contract.takeover_seconds_cap + 1))
    return BenchmarkTakeoverCost(
        eligible_tasks=len(tasks),
        completed_takeovers=completed,
        median_effective_actions=None if not tasks else median(effective_actions),
        median_effective_seconds=None if not tasks else median(effective_seconds),
    )


def _budget_loss(
    contract: BossAbsentBenchmarkContract,
    results: tuple[BossAbsentTaskResult, ...],
) -> BenchmarkRate:
    dispatched = tuple(result for result in results if result.dispatched)
    losses = sum(
        result.total_tokens is None or result.total_tokens > contract.max_total_tokens
        for result in dispatched
    )
    return _rate(losses, len(dispatched))


def _evidence_completeness(
    task_set: BossAbsentTaskSet,
    results: dict[str, BossAbsentTaskResult],
) -> BenchmarkRate:
    present = sum(_evidence_count(result) for result in results.values())
    return _rate(present, len(task_set.tasks) * EVIDENCE_CATEGORY_COUNT)


def _evidence_count(result: BossAbsentTaskResult) -> int:
    return sum(
        proof.status is BenchmarkEvidenceStatus.PRESENT for proof in result.evidence.proofs()
    )


def _compare_rate(
    left: BenchmarkRate,
    right: BenchmarkRate,
    *,
    higher_is_better: bool,
) -> MetricComparison:
    if left.denominator == 0 or right.denominator == 0:
        return MetricComparison.UNSCORABLE
    left_value = Fraction(left.numerator, left.denominator)
    right_value = Fraction(right.numerator, right.denominator)
    if left_value == right_value:
        return MetricComparison.EQUAL
    left_better = left_value > right_value if higher_is_better else left_value < right_value
    return MetricComparison.BETTER if left_better else MetricComparison.WORSE


def _compare_takeover(
    left: BenchmarkTakeoverCost,
    right: BenchmarkTakeoverCost,
) -> MetricComparison:
    if left.eligible_tasks == 0 or right.eligible_tasks == 0:
        return MetricComparison.UNSCORABLE
    assert left.median_effective_actions is not None
    assert left.median_effective_seconds is not None
    assert right.median_effective_actions is not None
    assert right.median_effective_seconds is not None
    left_value = (left.median_effective_actions, left.median_effective_seconds)
    right_value = (right.median_effective_actions, right.median_effective_seconds)
    if left_value == right_value:
        return MetricComparison.EQUAL
    return MetricComparison.BETTER if left_value < right_value else MetricComparison.WORSE
