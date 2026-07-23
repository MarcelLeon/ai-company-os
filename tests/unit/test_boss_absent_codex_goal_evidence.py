from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest

from aico.app.boss_absent_benchmark_cli import run
from aico.app.boss_absent_codex_goal_evidence import (
    CodexGoalRoleEvidence,
    CodexGoalScenarioEvidenceReceipt,
    finalize_codex_goal_benchmark_result,
)
from aico.app.boss_absent_codex_goal_host import (
    CodexGoalHostAdmissionReceipt,
    CodexGoalHostKind,
    CodexGoalHostRunReceipt,
    CodexGoalHostTurnReceipt,
    CodexGoalTurnSource,
)
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


def _contract(task_set_sha256: str = "b" * 64) -> BossAbsentBenchmarkContract:
    return BossAbsentBenchmarkContract(
        benchmark_id="boss-absent-codex-evidence",
        frozen_at=datetime(2026, 7, 23, tzinfo=UTC),
        model="gpt-5.6-sol",
        reasoning_effort="high",
        repo_revision="a" * 40,
        aico_version="test",
        codex_cli_version="0.144.5",
        wall_window_seconds=600,
        max_total_tokens=1_000,
        task_set_sha256=task_set_sha256,
        project_id="benchmark-project",
        project_assignment_sha256="c" * 64,
    )


def _task(scenario: BenchmarkScenario = BenchmarkScenario.NORMAL) -> BossAbsentTask:
    restart = scenario is BenchmarkScenario.RESTART
    approval = scenario is BenchmarkScenario.APPROVAL
    budget = scenario is BenchmarkScenario.BUDGET_PRESSURE
    return BossAbsentTask(
        task_id=f"task-{scenario.value.replace('_', '-')}",
        scenario=scenario,
        objective="produce a verified terminal handoff",
        fixture='{"release":"candidate-17","tests":"green"}',
        acceptance=("lead plans", "reviewer verifies"),
        required_roles=("lead", "reviewer"),
        unattended_eligible=not approval,
        collaboration_required=True,
        restart_required=restart,
        im_takeover_required=restart or approval,
        approval_required=approval,
        budget_pressure=budget,
    )


def _admission(contract: BossAbsentBenchmarkContract) -> CodexGoalHostAdmissionReceipt:
    return CodexGoalHostAdmissionReceipt(
        contract_sha256=canonical_sha256(contract),
        host_build="codex-desktop-2026.07.23",
        host_kind=CodexGoalHostKind.NATIVE_CODEX_HOST,
    )


def _host_run(
    contract: BossAbsentBenchmarkContract,
    admission: CodexGoalHostAdmissionReceipt,
    task: BossAbsentTask,
) -> CodexGoalHostRunReceipt:
    first = CodexGoalHostTurnReceipt(
        sequence=1,
        source=CodexGoalTurnSource.INITIAL_TASK,
        turn_sha256="1" * 64,
        opaque_input_sha256=canonical_sha256(task),
        runtime_instance_sha256="a" * 64,
        goal_status_after="active",
        goal_tokens_before=0,
        goal_tokens_after=100,
        goal_token_budget=contract.max_total_tokens,
        provider_total_tokens=100,
    )
    source = (
        CodexGoalTurnSource.OWNER_TAKEOVER
        if task.approval_required
        else CodexGoalTurnSource.NATIVE_HOST_CONTINUATION
    )
    second = CodexGoalHostTurnReceipt(
        sequence=2,
        source=source,
        previous_turn_sha256=first.turn_sha256,
        turn_sha256="2" * 64,
        opaque_input_sha256=("a" * 64 if task.approval_required else "9" * 64),
        runtime_instance_sha256=("b" if task.restart_required else "a") * 64,
        goal_status_after="complete",
        goal_tokens_before=100,
        goal_tokens_after=220,
        goal_token_budget=contract.max_total_tokens,
        provider_total_tokens=120,
        human_interventions=int(task.approval_required),
    )
    return CodexGoalHostRunReceipt(
        contract_sha256=canonical_sha256(contract),
        host_admission_sha256=canonical_sha256(admission),
        turns=(first, second),
        total_tokens=220,
        human_interventions=int(task.approval_required),
        terminal_status="complete",
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


def _roles(task: BossAbsentTask) -> tuple[CodexGoalRoleEvidence, ...]:
    fixture_sha = hashlib.sha256(task.fixture.encode()).hexdigest()
    first = CodexGoalRoleEvidence(
        sequence=1,
        role="lead",
        agent_identity_sha256="e" * 64,
        provider_execution_sha256="a" * 64,
        runtime_instance_sha256="a" * 64,
        source_turn_sha256="1" * 64,
        input_fixture_sha256=fixture_sha,
        artifact_sha256="c" * 64,
    )
    second = CodexGoalRoleEvidence(
        sequence=2,
        role="reviewer",
        agent_identity_sha256="f" * 64,
        provider_execution_sha256="b" * 64,
        runtime_instance_sha256=("b" if task.restart_required else "a") * 64,
        source_turn_sha256="2" * 64,
        input_fixture_sha256=fixture_sha,
        artifact_sha256="d" * 64,
        consumed_checkpoint_sha256=first.artifact_sha256,
    )
    return first, second


def _receipt(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
    host_run: CodexGoalHostRunReceipt,
    **updates: object,
) -> CodexGoalScenarioEvidenceReceipt:
    approval = task.approval_required
    payload: dict[str, object] = {
        "contract_sha256": canonical_sha256(contract),
        "task_id": task.task_id,
        "host_admission_sha256": canonical_sha256(admission),
        "host_run_sha256": canonical_sha256(host_run),
        "role_chain_observation_sha256": "c" * 64,
        "observer_build": "harness-test",
        "events_sha256": "f" * 64,
        "terminal_status": BenchmarkTerminalStatus.COMPLETE,
        "terminal_consumed_checkpoint_sha256": "d" * 64,
        "wall_seconds": 12,
        "human_interventions": int(approval),
        "evidence": _evidence(),
        "roles": _roles(task),
        "restart_observed": task.restart_required,
        "replayed_turns": 0,
        "restart_evidence_sha256": "6" * 64 if task.restart_required else None,
        "takeover_actions": 1 if task.im_takeover_required else None,
        "takeover_seconds": 2 if task.im_takeover_required else None,
        "takeover_evidence_sha256": "7" * 64 if task.im_takeover_required else None,
        "approval_requests": int(approval),
        "approval_grants": int(approval),
        "approval_evidence_sha256": "8" * 64 if approval else None,
        "approval_request_sha256": "9" * 64 if approval else None,
        "approval_grant_sha256": "a" * 64 if approval else None,
        "approval_action_receipt_sha256": "b" * 64 if approval else None,
        "approval_turn_sha256": "2" * 64 if approval else None,
        "evidence_drift_injected": task.scenario is BenchmarkScenario.EVIDENCE_DRIFT,
        "evidence_drift_detected": task.scenario is BenchmarkScenario.EVIDENCE_DRIFT,
        "irrelevant_source_exposed": task.budget_pressure,
    }
    return CodexGoalScenarioEvidenceReceipt.model_validate(payload | updates)


@pytest.mark.parametrize("scenario", tuple(BenchmarkScenario))
def test_finalizer_closes_each_frozen_scenario(scenario: BenchmarkScenario) -> None:
    contract = _contract()
    task = _task(scenario)
    admission = _admission(contract)
    host_run = _host_run(contract, admission, task)

    result = finalize_codex_goal_benchmark_result(
        contract,
        task,
        admission,
        host_run,
        _receipt(contract, task, admission, host_run),
    )

    assert result.system.value == "codex_goal"
    assert result.total_tokens == 220
    assert len({item.agent_id for item in result.role_checkpoints}) == 2
    assert result.role_checkpoints[-1].consumed_by == ("terminal",)


def test_finalizer_rejects_role_labels_reusing_one_provider_execution() -> None:
    contract = _contract()
    task = _task()
    admission = _admission(contract)
    host_run = _host_run(contract, admission, task)
    roles = _roles(task)
    reused = (roles[0], roles[1].model_copy(update={"provider_execution_sha256": "a" * 64}))

    with pytest.raises(ValueError, match="reused a provider execution"):
        finalize_codex_goal_benchmark_result(
            contract,
            task,
            admission,
            host_run,
            _receipt(contract, task, admission, host_run, roles=reused),
        )
    reused_agent = (
        roles[0],
        roles[1].model_copy(update={"agent_identity_sha256": "e" * 64}),
    )
    with pytest.raises(ValueError, match="reused an Agent identity"):
        finalize_codex_goal_benchmark_result(
            contract,
            task,
            admission,
            host_run,
            _receipt(contract, task, admission, host_run, roles=reused_agent),
        )


def test_finalizer_rejects_unobserved_turn_or_same_restart_instance() -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.RESTART)
    admission = _admission(contract)
    host_run = _host_run(contract, admission, task)
    roles = _roles(task)
    unobserved = (roles[0], roles[1].model_copy(update={"source_turn_sha256": "e" * 64}))
    with pytest.raises(ValueError, match="unobserved host turn"):
        finalize_codex_goal_benchmark_result(
            contract,
            task,
            admission,
            host_run,
            _receipt(contract, task, admission, host_run, roles=unobserved),
        )
    same_runtime = (roles[0], roles[1].model_copy(update={"runtime_instance_sha256": "a" * 64}))
    with pytest.raises(ValueError, match="runtime drifted"):
        finalize_codex_goal_benchmark_result(
            contract,
            task,
            admission,
            host_run,
            _receipt(contract, task, admission, host_run, roles=same_runtime),
        )
    second_turn = host_run.turns[1].model_copy(update={"runtime_instance_sha256": "a" * 64})
    same_host_run = host_run.model_copy(update={"turns": (host_run.turns[0], second_turn)})
    with pytest.raises(ValueError, match="no-replay restart"):
        finalize_codex_goal_benchmark_result(
            contract,
            task,
            admission,
            same_host_run,
            _receipt(contract, task, admission, same_host_run, roles=same_runtime),
        )


def test_finalizer_rejects_host_run_identity_or_hidden_intervention() -> None:
    contract = _contract()
    task = _task()
    admission = _admission(contract)
    host_run = _host_run(contract, admission, task)
    with pytest.raises(ValueError, match="identity drifted"):
        finalize_codex_goal_benchmark_result(
            contract,
            task,
            admission,
            host_run,
            _receipt(
                contract,
                task,
                admission,
                host_run,
                host_run_sha256="0" * 64,
            ),
        )
    with pytest.raises(ValueError, match="intervention count"):
        finalize_codex_goal_benchmark_result(
            contract,
            task,
            admission,
            host_run,
            _receipt(contract, task, admission, host_run, human_interventions=1),
        )
    first = host_run.turns[0].model_copy(update={"opaque_input_sha256": "8" * 64})
    drifted_run = host_run.model_copy(update={"turns": (first, host_run.turns[1])})
    with pytest.raises(ValueError, match="did not receive the frozen task"):
        finalize_codex_goal_benchmark_result(
            contract,
            task,
            admission,
            drifted_run,
            _receipt(contract, task, admission, drifted_run),
        )


def test_finalizer_binds_approval_evidence_to_the_owner_turn() -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.APPROVAL)
    admission = _admission(contract)
    host_run = _host_run(contract, admission, task)

    with pytest.raises(ValueError, match="approval fence"):
        finalize_codex_goal_benchmark_result(
            contract,
            task,
            admission,
            host_run,
            _receipt(
                contract,
                task,
                admission,
                host_run,
                approval_turn_sha256="1" * 64,
            ),
        )


def test_cli_finalizes_owner_safe_codex_goal_result(tmp_path: Path) -> None:
    tasks = BossAbsentTaskSet(
        name="five-scenario-test",
        tasks=tuple(_task(scenario) for scenario in BenchmarkScenario),
    )
    contract = _contract(canonical_sha256(tasks))
    task = _task()
    admission = _admission(contract)
    host_run = _host_run(contract, admission, task)
    receipt = _receipt(contract, task, admission, host_run)
    models = {
        "contract": contract,
        "tasks": tasks,
        "host-admission": admission,
        "host-run": host_run,
        "scenario-evidence": receipt,
    }
    paths = {name: tmp_path / f"{name}.json" for name in models}
    output = tmp_path / "result.json"
    for name, model in models.items():
        paths[name].write_text(model.model_dump_json(), encoding="utf-8")
    stdout = StringIO()

    exit_code = run(
        (
            "finalize-codex-goal",
            "--contract",
            str(paths["contract"]),
            "--tasks",
            str(paths["tasks"]),
            "--host-admission",
            str(paths["host-admission"]),
            "--host-run",
            str(paths["host-run"]),
            "--scenario-evidence",
            str(paths["scenario-evidence"]),
            "--output",
            str(output),
        ),
        stdout=stdout,
    )

    result = BossAbsentTaskResult.model_validate_json(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert "status=complete tokens=220" in stdout.getvalue()
    assert result.system.value == "codex_goal"
