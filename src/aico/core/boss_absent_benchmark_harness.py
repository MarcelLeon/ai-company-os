"""Deterministic no-model harness used to verify benchmark artifact plumbing."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from aico.core.boss_absent_benchmark import (
    BenchmarkEvidenceProof,
    BenchmarkEvidenceSet,
    BenchmarkEvidenceStatus,
    BenchmarkRoleCheckpoint,
    BenchmarkSystem,
    BenchmarkTerminalStatus,
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    BossAbsentTaskResult,
    BossAbsentTaskSet,
    canonical_sha256,
)
from aico.core.models import FrozenModel


class HarnessEventType(StrEnum):
    DISPATCHED = "task_dispatched"
    ROLE_CHECKPOINT = "role_checkpoint"
    PROCESS_STOPPED = "process_stopped"
    PROCESS_RESTARTED = "process_restarted"
    SOURCE_DRIFTED = "source_drifted"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    IRRELEVANT_SOURCE_EXPOSED = "irrelevant_source_exposed"
    SOURCE_INTEGRITY_CHECKED = "source_integrity_checked"
    ACCEPTANCE_CHECKED = "acceptance_checked"
    TEST_GATE_CHECKED = "test_gate_checked"
    BUDGET_OBSERVED = "budget_observed"
    OWNER_TAKEOVER = "owner_takeover"
    TERMINAL_RECORDED = "terminal_recorded"


class BenchmarkHarnessEvent(FrozenModel):
    version: Literal[1] = 1
    benchmark_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    system: BenchmarkSystem
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    sequence: int = Field(ge=1)
    event_type: HarnessEventType
    role: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{1,31}$")
    total_tokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_event_payload(self) -> BenchmarkHarnessEvent:
        if (self.event_type is HarnessEventType.ROLE_CHECKPOINT) != (self.role is not None):
            raise ValueError("only role checkpoint events carry a role")
        if (self.event_type is HarnessEventType.BUDGET_OBSERVED) != (self.total_tokens is not None):
            raise ValueError("only budget observation events carry provider usage")
        return self


class SyntheticHarnessRun(FrozenModel):
    events: tuple[BenchmarkHarnessEvent, ...]
    results: tuple[BossAbsentTaskResult, ...]


def run_synthetic_benchmark_harness(
    contract: BossAbsentBenchmarkContract,
    task_set: BossAbsentTaskSet,
) -> SyntheticHarnessRun:
    """Build equal, perfect fake observations; this validates plumbing, never superiority."""
    if canonical_sha256(task_set) != contract.task_set_sha256:
        raise ValueError("benchmark task set fingerprint mismatch")
    events: list[BenchmarkHarnessEvent] = []
    results: list[BossAbsentTaskResult] = []
    for system in BenchmarkSystem:
        for task in task_set.tasks:
            task_events, result = _run_synthetic_task(contract, task, system)
            events.extend(task_events)
            results.append(result)
    return SyntheticHarnessRun(events=tuple(events), results=tuple(results))


def _run_synthetic_task(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    system: BenchmarkSystem,
) -> tuple[tuple[BenchmarkHarnessEvent, ...], BossAbsentTaskResult]:
    events: list[BenchmarkHarnessEvent] = []

    def record(
        event_type: HarnessEventType,
        *,
        role: str | None = None,
        total_tokens: int | None = None,
    ) -> BenchmarkHarnessEvent:
        event = BenchmarkHarnessEvent(
            benchmark_id=contract.benchmark_id,
            contract_sha256=canonical_sha256(contract),
            system=system,
            task_id=task.task_id,
            sequence=len(events) + 1,
            event_type=event_type,
            role=role,
            total_tokens=total_tokens,
        )
        events.append(event)
        return event

    record(HarnessEventType.DISPATCHED)
    first_role, *remaining_roles = task.required_roles
    checkpoint_events = [record(HarnessEventType.ROLE_CHECKPOINT, role=first_role)]
    restart = None
    approval = None
    if task.restart_required:
        record(HarnessEventType.PROCESS_STOPPED)
        restart = record(HarnessEventType.PROCESS_RESTARTED)
    checkpoint_events.extend(
        record(HarnessEventType.ROLE_CHECKPOINT, role=role) for role in remaining_roles
    )
    if task.scenario.value == "evidence_drift":
        record(HarnessEventType.SOURCE_DRIFTED)
    if task.approval_required:
        record(HarnessEventType.APPROVAL_REQUESTED)
        approval = record(HarnessEventType.APPROVAL_GRANTED)
    if task.budget_pressure:
        record(HarnessEventType.IRRELEVANT_SOURCE_EXPOSED)
    source = record(HarnessEventType.SOURCE_INTEGRITY_CHECKED)
    acceptance = record(HarnessEventType.ACCEPTANCE_CHECKED)
    test_gate = record(HarnessEventType.TEST_GATE_CHECKED)
    total_tokens = min(10_000, contract.max_total_tokens)
    budget = record(HarnessEventType.BUDGET_OBSERVED, total_tokens=total_tokens)
    takeover = record(HarnessEventType.OWNER_TAKEOVER) if task.im_takeover_required else None
    terminal = record(HarnessEventType.TERMINAL_RECORDED)

    def proof(event: BenchmarkHarnessEvent) -> BenchmarkEvidenceProof:
        return BenchmarkEvidenceProof(
            status=BenchmarkEvidenceStatus.PRESENT,
            sha256=canonical_sha256(event),
        )

    result = BossAbsentTaskResult(
        benchmark_id=contract.benchmark_id,
        contract_sha256=canonical_sha256(contract),
        system=system,
        task_id=task.task_id,
        dispatched=True,
        terminal_status=BenchmarkTerminalStatus.COMPLETE,
        wall_seconds=1,
        human_interventions=1 if task.approval_required else 0,
        total_tokens=total_tokens,
        evidence=BenchmarkEvidenceSet(
            terminal=proof(terminal),
            acceptance=proof(acceptance),
            source_integrity=proof(source),
            test_gate=proof(test_gate),
            budget_receipt=proof(budget),
        ),
        role_checkpoints=tuple(
            BenchmarkRoleCheckpoint(
                checkpoint_id=f"checkpoint-{index}",
                role=role,
                agent_id=f"synthetic-{system.value}-{role}",
                artifact_sha256=canonical_sha256(event),
                consumed_by=("terminal",),
            )
            for index, (role, event) in enumerate(
                zip(task.required_roles, checkpoint_events, strict=True), start=1
            )
        ),
        takeover_actions=1 if takeover is not None else None,
        takeover_seconds=1 if takeover is not None else None,
        takeover_evidence_sha256=canonical_sha256(takeover) if takeover is not None else None,
        restart_evidence_sha256=canonical_sha256(restart) if restart is not None else None,
        approval_evidence_sha256=canonical_sha256(approval) if approval is not None else None,
    )
    return tuple(events), result
