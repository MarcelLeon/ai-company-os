from __future__ import annotations

from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest

from aico.app.boss_absent_aico_evidence import (
    AicoScenarioEvidenceReceipt,
    finalize_aico_benchmark_result,
)
from aico.app.boss_absent_aico_runner import (
    AicoBenchmarkRunPhase,
    AicoBenchmarkRunState,
    AicoRoleCheckpoint,
)
from aico.app.boss_absent_benchmark_cli import run
from aico.core.boss_absent_benchmark import (
    BenchmarkEvidenceProof,
    BenchmarkEvidenceSet,
    BenchmarkEvidenceStatus,
    BenchmarkScenario,
    BenchmarkTerminalStatus,
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    BossAbsentTaskResult,
    BossAbsentTaskSet,
    canonical_sha256,
)
from aico.core.models import TaskUsage


def _contract() -> BossAbsentBenchmarkContract:
    return BossAbsentBenchmarkContract(
        benchmark_id="boss-absent-evidence",
        frozen_at=datetime(2026, 7, 23, tzinfo=UTC),
        model="gpt-5.6-sol",
        reasoning_effort="high",
        repo_revision="a" * 40,
        aico_version="test",
        codex_cli_version="0.144.5",
        wall_window_seconds=600,
        max_total_tokens=1_000,
        task_set_sha256="b" * 64,
    )


def _task(
    scenario: BenchmarkScenario = BenchmarkScenario.NORMAL,
) -> BossAbsentTask:
    restart = scenario is BenchmarkScenario.RESTART
    approval = scenario is BenchmarkScenario.APPROVAL
    budget = scenario is BenchmarkScenario.BUDGET_PRESSURE
    return BossAbsentTask(
        task_id=f"task-{scenario.value.replace('_', '-')}",
        scenario=scenario,
        objective="produce a verified terminal handoff",
        acceptance=("lead plans", "reviewer verifies"),
        required_roles=("lead", "reviewer"),
        unattended_eligible=not approval,
        collaboration_required=True,
        restart_required=restart,
        im_takeover_required=restart or approval,
        approval_required=approval,
        budget_pressure=budget,
    )


def _state(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
) -> AicoBenchmarkRunState:
    first = AicoRoleCheckpoint(
        sequence=1,
        dispatch_id="1" * 64,
        role="lead",
        agent_id="agent-lead",
        runtime_instance_sha256="a" * 64,
        artifact_sha256="c" * 64,
        usage=TaskUsage(input_tokens=90, output_tokens=10, total_tokens=100),
    )
    second = AicoRoleCheckpoint(
        sequence=2,
        dispatch_id="2" * 64,
        role="reviewer",
        agent_id="agent-reviewer",
        runtime_instance_sha256=("b" if task.restart_required else "a") * 64,
        artifact_sha256="d" * 64,
        consumed_checkpoint_sha256=first.artifact_sha256,
        usage=TaskUsage(input_tokens=100, output_tokens=20, total_tokens=120),
    )
    return AicoBenchmarkRunState(
        contract_sha256=canonical_sha256(contract),
        runtime_admission_sha256="e" * 64,
        benchmark_id=contract.benchmark_id,
        task_id=task.task_id,
        phase=AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE,
        checkpoints=(first, second),
        total_tokens=220,
        restart_count=int(task.restart_required),
    )


def _proof(label: str) -> BenchmarkEvidenceProof:
    return BenchmarkEvidenceProof(
        status=BenchmarkEvidenceStatus.PRESENT,
        sha256=(label * 64)[:64],
    )


def _evidence() -> BenchmarkEvidenceSet:
    return BenchmarkEvidenceSet(
        terminal=_proof("1"),
        acceptance=_proof("2"),
        source_integrity=_proof("3"),
        test_gate=_proof("4"),
        budget_receipt=_proof("5"),
    )


def _receipt(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    state: AicoBenchmarkRunState,
    **updates: object,
) -> AicoScenarioEvidenceReceipt:
    payload: dict[str, object] = {
        "contract_sha256": canonical_sha256(contract),
        "task_id": task.task_id,
        "role_state_sha256": canonical_sha256(state),
        "observer_build": "harness-test",
        "events_sha256": "f" * 64,
        "terminal_status": BenchmarkTerminalStatus.COMPLETE,
        "terminal_consumed_checkpoint_sha256": state.checkpoints[-1].artifact_sha256,
        "wall_seconds": 12,
        "human_interventions": int(task.approval_required),
        "evidence": _evidence(),
        "restart_observed": task.restart_required,
        "replayed_dispatches": 0,
        "restart_evidence_sha256": "6" * 64 if task.restart_required else None,
        "takeover_actions": 1 if task.im_takeover_required else None,
        "takeover_seconds": 2 if task.im_takeover_required else None,
        "takeover_evidence_sha256": "7" * 64 if task.im_takeover_required else None,
        "approval_requests": int(task.approval_required),
        "approval_grants": int(task.approval_required),
        "approval_evidence_sha256": "8" * 64 if task.approval_required else None,
        "evidence_drift_injected": task.scenario is BenchmarkScenario.EVIDENCE_DRIFT,
        "evidence_drift_detected": task.scenario is BenchmarkScenario.EVIDENCE_DRIFT,
        "irrelevant_source_exposed": task.budget_pressure,
    }
    return AicoScenarioEvidenceReceipt.model_validate(payload | updates)


@pytest.mark.parametrize("scenario", tuple(BenchmarkScenario))
def test_finalizer_closes_each_frozen_scenario(scenario: BenchmarkScenario) -> None:
    contract = _contract()
    task = _task(scenario)
    state = _state(contract, task)

    result = finalize_aico_benchmark_result(
        contract,
        task,
        state,
        _receipt(contract, task, state),
    )

    assert result.terminal_status is BenchmarkTerminalStatus.COMPLETE
    assert result.total_tokens == 220
    assert len({item.agent_id for item in result.role_checkpoints}) == 2
    assert result.role_checkpoints[0].consumed_by == ("role-checkpoint-2",)
    assert result.role_checkpoints[1].consumed_by == ("terminal",)


def test_finalizer_rejects_restart_replay_or_same_process_state() -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.RESTART)
    state = _state(contract, task)

    with pytest.raises(ValueError, match="no-replay"):
        finalize_aico_benchmark_result(
            contract,
            task,
            state,
            _receipt(contract, task, state, replayed_dispatches=1),
        )
    no_restart = state.model_copy(update={"restart_count": 0})
    with pytest.raises(ValueError, match="no-replay"):
        finalize_aico_benchmark_result(
            contract,
            task,
            no_restart,
            _receipt(contract, task, no_restart),
        )
    same_runtime = state.model_copy(
        update={
            "checkpoints": (
                state.checkpoints[0],
                state.checkpoints[1].model_copy(
                    update={
                        "runtime_instance_sha256": (state.checkpoints[0].runtime_instance_sha256)
                    }
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="no-replay"):
        finalize_aico_benchmark_result(
            contract,
            task,
            same_runtime,
            _receipt(contract, task, same_runtime),
        )


def test_finalizer_rejects_stale_drift_result() -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.EVIDENCE_DRIFT)
    state = _state(contract, task)

    with pytest.raises(ValueError, match="accepted stale"):
        finalize_aico_benchmark_result(
            contract,
            task,
            state,
            _receipt(contract, task, state, stale_result_published=True),
        )


def test_finalizer_rejects_approval_mutation_or_extra_intervention() -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.APPROVAL)
    state = _state(contract, task)

    with pytest.raises(ValueError, match="approval fence"):
        finalize_aico_benchmark_result(
            contract,
            task,
            state,
            _receipt(contract, task, state, mutation_before_approval=True),
        )
    with pytest.raises(ValueError, match="intervention count"):
        finalize_aico_benchmark_result(
            contract,
            task,
            state,
            _receipt(contract, task, state, human_interventions=2),
        )


def test_finalizer_rejects_irrelevant_source_consumption() -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.BUDGET_PRESSURE)
    state = _state(contract, task)

    with pytest.raises(ValueError, match="consumed invalid evidence"):
        finalize_aico_benchmark_result(
            contract,
            task,
            state,
            _receipt(contract, task, state, irrelevant_source_consumed=True),
        )


def test_finalizer_rejects_missing_budget_or_terminal_consumption() -> None:
    contract = _contract()
    task = _task()
    state = _state(contract, task)
    evidence = _evidence().model_dump()
    evidence["budget_receipt"] = {"status": "missing", "sha256": None}

    with pytest.raises(ValueError, match="budget receipt"):
        finalize_aico_benchmark_result(
            contract,
            task,
            state,
            _receipt(contract, task, state, evidence=evidence),
        )
    with pytest.raises(ValueError, match="final role checkpoint"):
        finalize_aico_benchmark_result(
            contract,
            task,
            state,
            _receipt(
                contract,
                task,
                state,
                terminal_consumed_checkpoint_sha256="0" * 64,
            ),
        )


def test_cli_finalizes_owner_safe_aico_result(tmp_path: Path) -> None:
    tasks = BossAbsentTaskSet(
        name="five-scenario-test",
        tasks=tuple(_task(scenario) for scenario in BenchmarkScenario),
    )
    contract = _contract().model_copy(update={"task_set_sha256": canonical_sha256(tasks)})
    task = _task()
    state = _state(contract, task)
    receipt = _receipt(contract, task, state)
    paths = {
        "contract": tmp_path / "contract.json",
        "tasks": tmp_path / "tasks.json",
        "state": tmp_path / "state.json",
        "receipt": tmp_path / "receipt.json",
        "output": tmp_path / "result.json",
    }
    paths["contract"].write_text(contract.model_dump_json(), encoding="utf-8")
    paths["tasks"].write_text(tasks.model_dump_json(), encoding="utf-8")
    paths["state"].write_text(state.model_dump_json(), encoding="utf-8")
    paths["receipt"].write_text(receipt.model_dump_json(), encoding="utf-8")
    stdout = StringIO()

    exit_code = run(
        (
            "finalize-aico",
            "--contract",
            str(paths["contract"]),
            "--tasks",
            str(paths["tasks"]),
            "--state",
            str(paths["state"]),
            "--scenario-evidence",
            str(paths["receipt"]),
            "--output",
            str(paths["output"]),
        ),
        stdout=stdout,
    )

    result = BossAbsentTaskResult.model_validate_json(paths["output"].read_text(encoding="utf-8"))
    assert exit_code == 0
    assert "status=complete tokens=220" in stdout.getvalue()
    assert result.system.value == "aico"
