from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

import pytest

from aico.app.boss_absent_aico_approval import AicoApprovalActionReceipt
from aico.app.boss_absent_aico_evidence import finalize_aico_benchmark_result
from aico.app.boss_absent_aico_observer import (
    AicoExternalCheckReceipt,
    AicoTakeoverAckReceipt,
    AicoTerminalObservationReceipt,
    IndependentAicoScenarioObserver,
    JsonAicoScenarioObservationStore,
)
from aico.app.boss_absent_aico_runner import (
    AicoApprovalCheckpoint,
    AicoBenchmarkRunPhase,
    AicoBenchmarkRunState,
    AicoRoleCheckpoint,
    AicoRoleObservation,
    AicoRoleStatus,
)
from aico.app.boss_absent_benchmark_cli import run
from aico.core.boss_absent_benchmark import (
    BenchmarkScenario,
    BenchmarkTerminalStatus,
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    BossAbsentTaskSet,
    canonical_sha256,
)
from aico.core.models import TaskUsage


def _contract() -> BossAbsentBenchmarkContract:
    return BossAbsentBenchmarkContract(
        benchmark_id="boss-absent-observer",
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


def _task(scenario: BenchmarkScenario) -> BossAbsentTask:
    approval = scenario is BenchmarkScenario.APPROVAL
    restart = scenario is BenchmarkScenario.RESTART
    pressure = scenario is BenchmarkScenario.BUDGET_PRESSURE
    fixture = (
        '{"action_id":"publish-release-marker","target":"isolated-target.txt","content":"approved"}'
        if approval
        else '{"candidate":"release-17","checks":"green"}'
    )
    return BossAbsentTask(
        task_id=f"observer-{scenario.value.replace('_', '-')}",
        scenario=scenario,
        objective="produce a verified handoff",
        fixture=fixture,
        acceptance=("lead plans", "reviewer verifies"),
        required_roles=("lead", "reviewer"),
        unattended_eligible=not approval,
        collaboration_required=True,
        restart_required=restart,
        im_takeover_required=restart or approval,
        approval_required=approval,
        budget_pressure=pressure,
    )


def _materialize_role_state(
    tmp_path: Path,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
) -> tuple[AicoBenchmarkRunState, Path, Path]:
    artifact_dir = tmp_path / "artifacts"
    receipt_dir = tmp_path / "receipts"
    artifact_dir.mkdir(mode=0o700)
    receipt_dir.mkdir(mode=0o700)
    fixture_sha = _sha(task.fixture.encode())
    checkpoints: list[AicoRoleCheckpoint] = []
    prior: str | None = None
    for sequence, role in enumerate(task.required_roles, start=1):
        artifact = f'{{"role":"{role}","status":"complete"}}'.encode()
        artifact_sha = _sha(artifact)
        dispatch_id = f"{sequence:x}" * 64
        runtime = ("b" if task.restart_required and sequence > 1 else "a") * 64
        usage = TaskUsage(input_tokens=90, output_tokens=10, total_tokens=100)
        observation = AicoRoleObservation(
            dispatch_id=dispatch_id,
            role=role,
            agent_id=f"agent-{role}",
            runtime_instance_sha256=runtime,
            input_fixture_sha256=fixture_sha,
            artifact_sha256=artifact_sha,
            consumed_checkpoint_sha256=prior,
            status=AicoRoleStatus.COMPLETE,
            usage=usage,
        )
        checkpoint = AicoRoleCheckpoint(
            sequence=sequence,
            dispatch_id=dispatch_id,
            role=role,
            agent_id=observation.agent_id,
            runtime_instance_sha256=runtime,
            input_fixture_sha256=fixture_sha,
            artifact_sha256=artifact_sha,
            consumed_checkpoint_sha256=prior,
            usage=usage,
        )
        _write_owner(artifact_dir / f"{artifact_sha}.txt", artifact)
        _write_owner(
            receipt_dir / f"{dispatch_id}.json",
            observation.model_dump_json().encode(),
        )
        checkpoints.append(checkpoint)
        prior = artifact_sha
    state = AicoBenchmarkRunState(
        contract_sha256=canonical_sha256(contract),
        runtime_admission_sha256="e" * 64,
        benchmark_id=contract.benchmark_id,
        task_id=task.task_id,
        phase=AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE,
        checkpoints=tuple(checkpoints),
        approval_request_sha256=(
            _approval_request_sha(contract, task) if task.approval_required else None
        ),
        approval_checkpoint=(
            AicoApprovalCheckpoint(
                after_sequence=1,
                request_sha256=_approval_request_sha(contract, task),
                grant_sha256="2" * 64,
                action_receipt_sha256="9" * 64,
            )
            if task.approval_required
            else None
        ),
        total_tokens=sum(item.usage.total_tokens for item in checkpoints),
        restart_count=int(task.restart_required),
    )
    return state, artifact_dir, receipt_dir


def _external_receipts(
    tmp_path: Path,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    state: AicoBenchmarkRunState,
) -> tuple[Path, Path, Path]:
    final_sha = state.checkpoints[-1].artifact_sha256
    state_sha = canonical_sha256(state)
    paths: list[Path] = []
    for kind in ("acceptance", "test_gate"):
        path = tmp_path / f"{kind}.json"
        _write_owner(
            path,
            AicoExternalCheckReceipt(
                check_kind=kind,
                contract_sha256=canonical_sha256(contract),
                task_id=task.task_id,
                role_state_sha256=state_sha,
                checked_artifact_sha256=final_sha,
                passed=True,
            )
            .model_dump_json()
            .encode(),
        )
        paths.append(path)
    terminal = tmp_path / "terminal.json"
    _write_owner(
        terminal,
        AicoTerminalObservationReceipt(
            contract_sha256=canonical_sha256(contract),
            task_id=task.task_id,
            role_state_sha256=state_sha,
            consumed_checkpoint_sha256=final_sha,
            status=BenchmarkTerminalStatus.COMPLETE,
        )
        .model_dump_json()
        .encode(),
    )
    return paths[0], paths[1], terminal


@pytest.mark.parametrize("scenario", tuple(BenchmarkScenario))
def test_independent_observer_builds_scoreable_receipt_from_real_files(
    tmp_path: Path,
    scenario: BenchmarkScenario,
) -> None:
    contract = _contract()
    task = _task(scenario)
    state, artifacts, receipts = _materialize_role_state(tmp_path, contract, task)
    now = datetime(2026, 7, 23, tzinfo=UTC)
    ticks = iter(now + timedelta(seconds=index) for index in range(30))
    store = JsonAicoScenarioObservationStore((tmp_path / "observations.json").absolute())
    observer = IndependentAicoScenarioObserver(
        contract,
        task,
        store,
        observer_build="observer-test",
        clock=lambda: next(ticks),
    )
    fixture = tmp_path / "fixture.json"
    fixture.write_text(task.fixture, encoding="utf-8")
    observer.observe_fixture(fixture)

    if task.restart_required:
        observer.observe_restart(state)
    if scenario is BenchmarkScenario.EVIDENCE_DRIFT:
        fixture.write_text('{"candidate":"release-18"}', encoding="utf-8")
        observer.observe_drift(fixture)
    if task.approval_required:
        mutation_dir = tmp_path / "mutation-target"
        mutation_dir.mkdir()
        mutation_target = mutation_dir / "isolated-target.txt"
        assert state.approval_request_sha256 is not None
        observer.observe_approval_request(
            state.approval_request_sha256,
            (mutation_target,),
        )
        observer.observe_approval_grant("2" * 64, (mutation_target,))
        mutation_target.write_text("approved", encoding="utf-8")
        mutation_target.chmod(0o600)
        action = AicoApprovalActionReceipt(
            intent_sha256="5" * 64,
            contract_sha256=canonical_sha256(contract),
            task_id=task.task_id,
            request_sha256=state.approval_request_sha256,
            grant_sha256="2" * 64,
            action_id="publish-release-marker",
            target_sha256=_sha(b"isolated-target.txt"),
            content_sha256=_sha(b"approved"),
            reconciled_after_write=False,
        )
        action_path = tmp_path / "approval-action.json"
        action_bytes = action.model_dump_json().encode()
        _write_owner(action_path, action_bytes)
        assert state.approval_checkpoint is not None
        state = state.model_copy(
            update={
                "approval_checkpoint": state.approval_checkpoint.model_copy(
                    update={"action_receipt_sha256": _sha(action_bytes)}
                )
            }
        )
        observer.observe_approval_action(action_path, state, (mutation_target,))
    observer.observe_role_state(state, artifact_dir=artifacts, receipt_dir=receipts)
    if task.budget_pressure:
        irrelevant = tmp_path / "irrelevant.log"
        irrelevant.write_bytes(b"x" * 200_000)
        observer.observe_source_pressure(irrelevant)

    acceptance, test_gate, terminal = _external_receipts(tmp_path, contract, task, state)
    observer.observe_external_check(acceptance)
    observer.observe_external_check(test_gate)
    observer.observe_budget(state)
    if task.im_takeover_required:
        takeover = tmp_path / "takeover.json"
        _write_owner(
            takeover,
            AicoTakeoverAckReceipt(
                contract_sha256=canonical_sha256(contract),
                task_id=task.task_id,
                terminal_checkpoint_sha256=state.checkpoints[-1].artifact_sha256,
                request_sha256="3" * 64,
                delivery_ack_sha256="4" * 64,
                actions=1,
                elapsed_seconds=2,
            )
            .model_dump_json()
            .encode(),
        )
        observer.observe_takeover(takeover)
    observer.observe_terminal(terminal)

    observer = IndependentAicoScenarioObserver(
        contract,
        task,
        store,
        observer_build="observer-test",
        clock=lambda: next(ticks),
    )
    receipt = observer.build_receipt()
    result = finalize_aico_benchmark_result(contract, task, state, receipt)

    assert result.terminal_status is BenchmarkTerminalStatus.COMPLETE
    assert result.total_tokens == state.total_tokens
    assert store.load() is not None
    assert (tmp_path / "observations.json").stat().st_mode & 0o777 == 0o600


def test_observer_rejects_mutation_before_approval(tmp_path: Path) -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.APPROVAL)
    store = JsonAicoScenarioObservationStore((tmp_path / "observations.json").absolute())
    observer = IndependentAicoScenarioObserver(
        contract,
        task,
        store,
        observer_build="observer-test",
    )
    target_dir = tmp_path / "mutation-target"
    target_dir.mkdir()
    target = target_dir / "target.txt"
    observer.observe_approval_request("1" * 64, (target,))
    target.write_text("mutated", encoding="utf-8")

    with pytest.raises(ValueError, match="mutation before approval"):
        observer.observe_approval_grant("2" * 64, (target,))


def test_observer_rejects_mutation_reverted_before_approval(tmp_path: Path) -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.APPROVAL)
    observer = IndependentAicoScenarioObserver(
        contract,
        task,
        JsonAicoScenarioObservationStore((tmp_path / "observations.json").absolute()),
        observer_build="observer-test",
    )
    target_dir = tmp_path / "mutation-target"
    target_dir.mkdir()
    target = target_dir / "target.txt"
    observer.observe_approval_request("1" * 64, (target,))
    target.write_text("transient mutation", encoding="utf-8")
    target.unlink()

    with pytest.raises(ValueError, match="mutation before approval"):
        observer.observe_approval_grant("2" * 64, (target,))


def test_observer_rejects_tampered_role_receipt(tmp_path: Path) -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.NORMAL)
    state, artifacts, receipts = _materialize_role_state(tmp_path, contract, task)
    receipt_path = receipts / f"{state.checkpoints[0].dispatch_id}.json"
    payload = receipt_path.read_text(encoding="utf-8").replace("agent-lead", "agent-fake")
    receipt_path.write_text(payload, encoding="utf-8")
    receipt_path.chmod(0o600)
    observer = IndependentAicoScenarioObserver(
        contract,
        task,
        JsonAicoScenarioObservationStore((tmp_path / "observations.json").absolute()),
        observer_build="observer-test",
    )

    with pytest.raises(ValueError, match="drifted from state"):
        observer.observe_role_state(state, artifact_dir=artifacts, receipt_dir=receipts)


def test_cli_finalizes_owner_only_independent_observation_receipt(tmp_path: Path) -> None:
    tasks = BossAbsentTaskSet(
        name="observer-cli-suite",
        tasks=tuple(_task(scenario) for scenario in BenchmarkScenario),
    )
    contract = _contract().model_copy(update={"task_set_sha256": canonical_sha256(tasks)})
    task = tasks.tasks[0]
    state, artifacts, receipts = _materialize_role_state(tmp_path, contract, task)
    observation_path = (tmp_path / "observations.json").absolute()
    observer = IndependentAicoScenarioObserver(
        contract,
        task,
        JsonAicoScenarioObservationStore(observation_path),
        observer_build="observer-cli-test",
    )
    fixture = tmp_path / "fixture.json"
    fixture.write_text(task.fixture, encoding="utf-8")
    observer.observe_fixture(fixture)
    observer.observe_role_state(state, artifact_dir=artifacts, receipt_dir=receipts)
    acceptance, test_gate, terminal = _external_receipts(tmp_path, contract, task, state)
    observer.observe_external_check(acceptance)
    observer.observe_external_check(test_gate)
    observer.observe_budget(state)
    observer.observe_terminal(terminal)
    contract_path = tmp_path / "contract.json"
    tasks_path = tmp_path / "tasks.json"
    contract_path.write_text(contract.model_dump_json(), encoding="utf-8")
    tasks_path.write_text(tasks.model_dump_json(), encoding="utf-8")
    output_path = tmp_path / "scenario-receipt.json"
    stdout = StringIO()

    exit_code = run(
        (
            "finalize-aico-observations",
            "--contract",
            str(contract_path),
            "--tasks",
            str(tasks_path),
            "--observations",
            str(observation_path),
            "--output",
            str(output_path),
        ),
        stdout=stdout,
    )

    assert exit_code == 0
    assert "independent observations finalized" in stdout.getvalue()
    assert output_path.stat().st_mode & 0o777 == 0o600


def _write_owner(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)
    path.chmod(0o600)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _approval_request_sha(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
) -> str:
    return hashlib.sha256(
        (
            f"aico-benchmark-approval-v1\0{canonical_sha256(contract)}\0"
            f"{task.task_id}\0{task.fixture}"
        ).encode()
    ).hexdigest()
