from __future__ import annotations

import json
import subprocess
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest

from aico.app.boss_absent_benchmark_cli import run
from aico.app.boss_absent_benchmark_restart_probe import BenchmarkRestartProbeReceipt
from aico.app.boss_absent_codex_goal_probe import CodexGoalProtocolReceipt
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
    MetricComparison,
    canonical_sha256,
    compare_boss_absent_summaries,
    score_boss_absent_system,
)
from aico.core.boss_absent_benchmark_harness import (
    HarnessEventType,
    run_synthetic_benchmark_harness,
)
from aico.core.models import (
    AckStatus,
    AdapterStatus,
    Capability,
    HealthStatus,
    OutputType,
    Task,
    TaskAck,
    TaskOutput,
    TaskUsage,
)
from aico.core.project_assignment import ProjectAssignmentConfig

_TASKS_PATH = Path("benchmarks/boss-absent-v1/tasks.json")
_PROJECT_PATH = Path("benchmarks/boss-absent-v1/project.json")
_TASKS_SHA256 = "f0acbd3317466f8709cf408ba1403bc0dbda17f0f5367cbd21630861c9462031"
_PROJECT_SHA256 = "40f61edf9d7b931e9538c8b79ec76742dfb3bc11b501c27df8cc362654c33832"


class CliRecordingAdapter:
    name = "codex"

    def __init__(self) -> None:
        self.tasks: list[Task] = []
        self._usage: dict[str, TaskUsage] = {}
        self._executions: dict[str, str] = {}

    def capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.CODE_REVIEW, Capability.STREAM_OUTPUT})

    def supports_preauthorized_execution(self, mode: str) -> bool:
        return mode == "read_only"

    def supports_preauthorized_budget(self, max_total_tokens: int) -> bool:
        return max_total_tokens >= 100

    def supports_preauthorized_model(self, model: str, reasoning_effort: str) -> bool:
        return model == "gpt-5.6-sol" and reasoning_effort == "high"

    async def receive_task(self, task: Task) -> TaskAck:
        self.tasks.append(task)
        self._usage[task.task_id] = TaskUsage(
            input_tokens=90,
            output_tokens=10,
            total_tokens=100,
        )
        self._executions[task.task_id] = f"execution-{task.task_id}"
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    async def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        yield TaskOutput(
            task_id=task_id,
            sequence=1,
            type=OutputType.TEXT,
            content='{"status":"complete"}',
        )
        yield TaskOutput(
            task_id=task_id,
            sequence=2,
            type=OutputType.DONE,
            content="",
        )

    def task_usage(self, task_id: str) -> TaskUsage | None:
        return self._usage.get(task_id)

    def provider_execution_id(self, task_id: str) -> str | None:
        return self._executions.get(task_id)

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        return None

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


def test_frozen_task_set_embeds_bounded_distinct_fixtures() -> None:
    tasks = _tasks()

    assert canonical_sha256(tasks) == _TASKS_SHA256
    assert len({task.fixture for task in tasks.tasks}) == len(tasks.tasks)
    assert all(0 < len(task.fixture.encode("utf-8")) <= 16_384 for task in tasks.tasks)


def test_frozen_project_uses_distinct_formal_agent_appointments() -> None:
    project = _project_config()

    assert canonical_sha256(project) == _PROJECT_SHA256
    assert len({item.agent for item in project.appointments}) == len(project.appointments)


def test_boss_absent_scorer_requires_all_five_win_metrics() -> None:
    tasks = _tasks()
    contract = _contract(tasks)
    results = _winning_results(contract, tasks)

    aico = score_boss_absent_system(contract, tasks, results, BenchmarkSystem.AICO)
    codex = score_boss_absent_system(contract, tasks, results, BenchmarkSystem.CODEX_GOAL)
    verdict = compare_boss_absent_summaries(contract, aico, codex)

    assert aico.unattended_completion.numerator == 4
    assert aico.collaboration_completion.numerator == 4
    assert aico.budget_loss.numerator == 0
    assert aico.evidence_completeness.numerator == 25
    assert codex.budget_loss.numerator == 2
    assert verdict.aico_wins
    assert verdict.strict_better_metrics == 5
    assert set(verdict.comparisons.values()) == {MetricComparison.BETTER}
    assert all(verdict.gates.values())


def test_missing_task_cannot_be_hidden_from_denominators_or_win_gate() -> None:
    tasks = _tasks()
    contract = _contract(tasks)
    results = tuple(
        result
        for result in _winning_results(contract, tasks)
        if not (
            result.system is BenchmarkSystem.AICO and result.task_id == "bounded-budget-pressure"
        )
    )

    aico = score_boss_absent_system(contract, tasks, results, BenchmarkSystem.AICO)
    codex = score_boss_absent_system(contract, tasks, results, BenchmarkSystem.CODEX_GOAL)
    verdict = compare_boss_absent_summaries(contract, aico, codex)

    assert aico.received_tasks == 4
    assert aico.evidence_completeness.denominator == 25
    assert aico.evidence_completeness.numerator == 20
    assert not verdict.aico_wins
    assert not verdict.gates["aico_full_task_coverage"]


def test_missing_or_excess_provider_usage_is_budget_loss() -> None:
    tasks = _tasks()
    contract = _contract(tasks)
    task = tasks.tasks[0]
    missing_payload = _result(contract, task, BenchmarkSystem.AICO, strong=True).model_dump()
    missing_payload["total_tokens"] = None
    missing_payload["evidence"]["budget_receipt"] = _proof(
        BenchmarkEvidenceStatus.MISSING, "budget"
    ).model_dump()
    missing = BossAbsentTaskResult.model_validate(missing_payload)
    excess = _result(contract, tasks.tasks[1], BenchmarkSystem.AICO, strong=True).model_copy(
        update={"total_tokens": contract.max_total_tokens + 1}
    )

    summary = score_boss_absent_system(
        contract,
        tasks,
        (missing, excess),
        BenchmarkSystem.AICO,
    )

    assert summary.budget_loss.numerator == 2
    assert summary.budget_loss.denominator == 2


def test_one_agent_role_play_cannot_count_as_multi_agent_collaboration() -> None:
    tasks = _tasks()
    contract = _contract(tasks)
    task = next(item for item in tasks.tasks if len(item.required_roles) > 1)
    result = _result(contract, task, BenchmarkSystem.AICO, strong=True)
    checkpoints = tuple(
        checkpoint.model_copy(update={"agent_id": "agent-shared"})
        for checkpoint in result.role_checkpoints
    )
    role_played = BossAbsentTaskResult.model_validate(
        result.model_dump() | {"role_checkpoints": checkpoints}
    )

    summary = score_boss_absent_system(
        contract,
        tasks,
        (role_played,),
        BenchmarkSystem.AICO,
    )

    assert summary.collaboration_completion.numerator == 0
    assert summary.collaboration_completion.denominator == 4


@pytest.mark.parametrize(
    ("task_id", "update", "failed_gate"),
    [
        (
            "normal-release-audit",
            {"total_tokens": 50_001},
            "aico_zero_budget_loss",
        ),
        (
            "restart-mid-handoff",
            {"role_checkpoints": ()},
            "aico_all_collaboration_complete",
        ),
        (
            "approval-fence-resume",
            {"approval_evidence_sha256": None},
            "aico_approval_evidence",
        ),
    ],
)
def test_absolute_aico_gates_cannot_be_bypassed_by_relative_scores(
    task_id: str,
    update: dict[str, object],
    failed_gate: str,
) -> None:
    tasks = _tasks()
    contract = _contract(tasks)
    results = list(_winning_results(contract, tasks))
    index = next(
        index
        for index, result in enumerate(results)
        if result.system is BenchmarkSystem.AICO and result.task_id == task_id
    )
    results[index] = BossAbsentTaskResult.model_validate(results[index].model_dump() | update)

    aico = score_boss_absent_system(contract, tasks, tuple(results), BenchmarkSystem.AICO)
    codex = score_boss_absent_system(contract, tasks, tuple(results), BenchmarkSystem.CODEX_GOAL)
    verdict = compare_boss_absent_summaries(contract, aico, codex)

    assert not verdict.aico_wins
    assert not verdict.gates[failed_gate]


def test_scorer_rejects_task_drift_duplicate_results_and_wrong_contract() -> None:
    tasks = _tasks()
    contract = _contract(tasks)
    result = _result(contract, tasks.tasks[0], BenchmarkSystem.AICO, strong=True)

    with pytest.raises(ValueError, match="task set fingerprint"):
        score_boss_absent_system(
            contract.model_copy(update={"task_set_sha256": "0" * 64}),
            tasks,
            (result,),
            BenchmarkSystem.AICO,
        )
    with pytest.raises(ValueError, match="duplicate benchmark result"):
        score_boss_absent_system(
            contract,
            tasks,
            (result, result),
            BenchmarkSystem.AICO,
        )
    with pytest.raises(ValueError, match="frozen contract"):
        score_boss_absent_system(
            contract,
            tasks,
            (result.model_copy(update={"contract_sha256": "0" * 64}),),
            BenchmarkSystem.AICO,
        )


def test_result_rejects_fake_checkpoint_links_and_undispatched_evidence() -> None:
    tasks = _tasks()
    contract = _contract(tasks)
    result = _result(contract, tasks.tasks[0], BenchmarkSystem.AICO, strong=True)
    bad_checkpoint = result.role_checkpoints[0].model_copy(update={"consumed_by": ("unknown",)})

    with pytest.raises(ValueError, match="checkpoint consumer"):
        BossAbsentTaskResult.model_validate(
            result.model_dump() | {"role_checkpoints": (bad_checkpoint,)}
        )
    with pytest.raises(ValueError, match="undispatched"):
        BossAbsentTaskResult.model_validate(
            result.model_dump()
            | {
                "dispatched": False,
                "wall_seconds": None,
                "terminal_status": "complete",
            }
        )


def test_evidence_proof_rejects_claims_without_consistent_hash() -> None:
    with pytest.raises(ValueError, match="cannot carry"):
        BenchmarkEvidenceProof(
            status=BenchmarkEvidenceStatus.MISSING,
            sha256="a" * 64,
        )
    with pytest.raises(ValueError, match="requires"):
        BenchmarkEvidenceProof(status=BenchmarkEvidenceStatus.FAILED)


def test_synthetic_harness_exercises_all_scenario_events_without_claiming_win() -> None:
    tasks = _tasks()
    contract = _contract(tasks)
    harness = run_synthetic_benchmark_harness(contract, tasks)
    by_task = {
        task.task_id: {
            event.event_type
            for event in harness.events
            if event.system is BenchmarkSystem.AICO and event.task_id == task.task_id
        }
        for task in tasks.tasks
    }

    assert HarnessEventType.PROCESS_RESTARTED in by_task["restart-mid-handoff"]
    assert HarnessEventType.SOURCE_DRIFTED in by_task["evidence-drift-detection"]
    assert HarnessEventType.APPROVAL_GRANTED in by_task["approval-fence-resume"]
    assert HarnessEventType.IRRELEVANT_SOURCE_EXPOSED in by_task["bounded-budget-pressure"]
    event_hashes = {canonical_sha256(event) for event in harness.events}
    assert all(
        proof.sha256 in event_hashes
        for result in harness.results
        for proof in result.evidence.proofs()
    )

    aico = score_boss_absent_system(contract, tasks, harness.results, BenchmarkSystem.AICO)
    codex = score_boss_absent_system(contract, tasks, harness.results, BenchmarkSystem.CODEX_GOAL)
    verdict = compare_boss_absent_summaries(contract, aico, codex)

    assert len(harness.results) == 10
    assert not verdict.aico_wins
    assert verdict.strict_better_metrics == 0
    assert set(verdict.comparisons.values()) == {MetricComparison.EQUAL}


def test_synthetic_harness_stops_after_first_checkpoint_then_restarts() -> None:
    tasks = _tasks()
    contract = _contract(tasks)
    events = tuple(
        event
        for event in run_synthetic_benchmark_harness(contract, tasks).events
        if event.system is BenchmarkSystem.AICO and event.task_id == "restart-mid-handoff"
    )
    event_types = tuple(event.event_type for event in events)

    first_checkpoint = event_types.index(HarnessEventType.ROLE_CHECKPOINT)
    stopped = event_types.index(HarnessEventType.PROCESS_STOPPED)
    restarted = event_types.index(HarnessEventType.PROCESS_RESTARTED)

    assert first_checkpoint < stopped < restarted
    assert HarnessEventType.ROLE_CHECKPOINT in event_types[restarted + 1 :]


def test_benchmark_cli_freezes_and_scores_new_artifact_directory(tmp_path: Path) -> None:
    tasks = _tasks()
    contract_path = tmp_path / "contract.json"
    stdout = StringIO()
    freeze_args = _freeze_args(contract_path)

    assert run(freeze_args, stdout=stdout) == 0
    contract = BossAbsentBenchmarkContract.model_validate_json(contract_path.read_text())
    results_path = tmp_path / "results.jsonl"
    results_path.write_text(
        "\n".join(result.model_dump_json() for result in _winning_results(contract, tasks)) + "\n",
        encoding="utf-8",
    )
    scored = tmp_path / "scored"
    score_stdout = StringIO()

    exit_code = run(
        [
            "score",
            "--contract",
            str(contract_path),
            "--tasks",
            str(_TASKS_PATH),
            "--results",
            str(results_path),
            "--output-dir",
            str(scored),
        ],
        stdout=score_stdout,
    )

    assert exit_code == 0
    assert "aico_wins=true" in score_stdout.getvalue()
    assert (scored / "aico-summary.json").is_file()
    assert (scored / "codex-goal-summary.json").is_file()
    verdict = json.loads((scored / "verdict.json").read_text(encoding="utf-8"))
    assert verdict["aico_wins"] is True
    assert "| Budget loss | 0/5 | 2/5 | better |" in (scored / "verdict.md").read_text(
        encoding="utf-8"
    )


def test_benchmark_cli_runs_equal_no_model_synthetic_harness(tmp_path: Path) -> None:
    contract_path = tmp_path / "contract.json"
    assert run(_freeze_args(contract_path)) == 0
    dry_run = tmp_path / "dry-run"
    stdout = StringIO()

    exit_code = run(
        [
            "dry-run",
            "--contract",
            str(contract_path),
            "--tasks",
            str(_TASKS_PATH),
            "--output-dir",
            str(dry_run),
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    assert "not a benchmark result" in stdout.getvalue()
    assert len((dry_run / "task-results.jsonl").read_text().splitlines()) == 10
    verdict = json.loads((dry_run / "scored" / "verdict.json").read_text())
    assert verdict["aico_wins"] is False
    assert (dry_run / "scenario-events.jsonl").is_file()
    results = tuple(
        BossAbsentTaskResult.model_validate_json(line)
        for line in (dry_run / "task-results.jsonl").read_text().splitlines()
    )
    for system in BenchmarkSystem:
        receipt = BenchmarkRestartProbeReceipt.model_validate_json(
            (dry_run / f"restart-probe-{system.value}.json").read_text()
        )
        restart_result = next(
            result
            for result in results
            if result.system is system and result.task_id == "restart-mid-handoff"
        )
        assert receipt.terminated_returncode < 0
        assert receipt.resumed_from_exact_checkpoint
        assert restart_result.restart_evidence_sha256 == canonical_sha256(receipt)


def test_benchmark_cli_advances_frozen_aico_roles_through_taskbus(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(("git", "init", "-q", str(checkout)), check=True)
    subprocess.run(
        ("git", "-C", str(checkout), "config", "user.email", "benchmark@example.invalid"),
        check=True,
    )
    subprocess.run(
        ("git", "-C", str(checkout), "config", "user.name", "Benchmark Harness"),
        check=True,
    )
    (checkout / "fixture.txt").write_text("clean checkout", encoding="utf-8")
    subprocess.run(("git", "-C", str(checkout), "add", "fixture.txt"), check=True)
    subprocess.run(
        ("git", "-C", str(checkout), "commit", "-q", "-m", "fixture"),
        check=True,
    )
    revision = subprocess.run(
        ("git", "-C", str(checkout), "rev-parse", "HEAD"),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tasks = _tasks()
    contract = _contract(tasks).model_copy(update={"repo_revision": revision})
    contract_path = tmp_path / "contract.json"
    tasks_path = tmp_path / "tasks.json"
    contract_path.write_text(contract.model_dump_json(), encoding="utf-8")
    tasks_path.write_text(tasks.model_dump_json(), encoding="utf-8")
    task = next(item for item in tasks.tasks if item.task_id == "bounded-budget-pressure")
    adapter = CliRecordingAdapter()
    monkeypatch.setattr(
        "aico.app.boss_absent_benchmark_cli.CodexAdapter",
        lambda **_: adapter,
    )
    state_path = (tmp_path / "state.json").absolute()
    common = [
        "advance-aico",
        "--contract",
        str(contract_path),
        "--tasks",
        str(tasks_path),
        "--project-config",
        str(_PROJECT_PATH.absolute()),
        "--project-id",
        "boss-absent-benchmark",
        "--task-id",
        task.task_id,
        "--state",
        str(state_path),
        "--artifact-dir",
        str((tmp_path / "artifacts").absolute()),
        "--receipt-dir",
        str((tmp_path / "receipts").absolute()),
        "--cwd",
        str(checkout.absolute()),
        "--runtime-build",
        "aico-cli-test",
        "--runtime-instance-sha256",
        "a" * 64,
        "--expires-at",
        "2027-01-01T00:00:00+00:00",
        "--max-duration-seconds",
        "10",
        "--role-target",
        "lead=benchmark-lead:codex",
        "--role-target",
        "reviewer=benchmark-reviewer:codex",
    ]
    stdout = StringIO()

    assert run(common, stdout=stdout) == 0
    assert run(common, stdout=stdout) == 0

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["phase"] == "role_chain_complete"
    assert len(adapter.tasks) == 2
    assert all(task.fixture in dispatched.payload for dispatched in adapter.tasks)
    assert state_path.stat().st_mode & 0o777 == 0o600


def test_benchmark_cli_writes_no_model_codex_goal_protocol_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract_path = tmp_path / "contract.json"
    assert run(_freeze_args(contract_path)) == 0
    receipt = CodexGoalProtocolReceipt(
        codex_cli_version="0.144.5",
        model="gpt-5.6-sol",
        token_budget=50_000,
    )
    monkeypatch.setattr(
        "aico.app.boss_absent_benchmark_cli.probe_codex_goal_protocol",
        lambda **_: receipt,
    )
    output_path = tmp_path / "goal-protocol.json"
    stdout = StringIO()

    exit_code = run(
        [
            "probe-codex-goal",
            "--contract",
            str(contract_path),
            "--cwd",
            str(tmp_path),
            "--output",
            str(output_path),
        ],
        stdout=stdout,
    )

    assert exit_code == 0
    assert "tokens_used=0" in stdout.getvalue()
    assert CodexGoalProtocolReceipt.model_validate_json(output_path.read_text()) == receipt


def test_benchmark_cli_refuses_overwrite_duplicate_json_and_valid_non_win(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "contract.json"
    assert run(_freeze_args(contract_path)) == 0
    error = StringIO()
    assert run(_freeze_args(contract_path), stderr=error) == 2
    assert "File exists" in error.getvalue()

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"version":1,"version":1}\n', encoding="utf-8")
    result_error = StringIO()
    exit_code = run(
        [
            "score",
            "--contract",
            str(duplicate),
            "--tasks",
            str(_TASKS_PATH),
            "--results",
            str(duplicate),
            "--output-dir",
            str(tmp_path / "invalid"),
        ],
        stderr=result_error,
    )
    assert exit_code == 2
    assert "duplicate key" in result_error.getvalue()

    non_finite = tmp_path / "non-finite.json"
    non_finite.write_text('{"version":NaN}\n', encoding="utf-8")
    finite_error = StringIO()
    assert (
        run(
            [
                "score",
                "--contract",
                str(non_finite),
                "--tasks",
                str(_TASKS_PATH),
                "--results",
                str(non_finite),
                "--output-dir",
                str(tmp_path / "non-finite-output"),
            ],
            stderr=finite_error,
        )
        == 2
    )
    assert "non-finite number" in finite_error.getvalue()

    contract = BossAbsentBenchmarkContract.model_validate_json(contract_path.read_text())
    tasks = _tasks()
    equal_results = tuple(
        _result(contract, task, system, strong=True)
        for system in BenchmarkSystem
        for task in tasks.tasks
    )
    results_path = tmp_path / "equal.jsonl"
    results_path.write_text(
        "\n".join(result.model_dump_json() for result in equal_results) + "\n",
        encoding="utf-8",
    )
    assert (
        run(
            [
                "score",
                "--contract",
                str(contract_path),
                "--tasks",
                str(_TASKS_PATH),
                "--results",
                str(results_path),
                "--output-dir",
                str(tmp_path / "equal-scored"),
            ]
        )
        == 1
    )


def _tasks() -> BossAbsentTaskSet:
    return BossAbsentTaskSet.model_validate_json(_TASKS_PATH.read_text(encoding="utf-8"))


def _contract(tasks: BossAbsentTaskSet) -> BossAbsentBenchmarkContract:
    return BossAbsentBenchmarkContract(
        benchmark_id="boss-absent-v1-test",
        frozen_at=datetime(2026, 7, 22, tzinfo=UTC),
        model="gpt-5.6-sol",
        reasoning_effort="high",
        repo_revision="a" * 40,
        aico_version="test-aico",
        codex_cli_version="0.144.5",
        wall_window_seconds=3_600,
        max_total_tokens=50_000,
        task_set_sha256=canonical_sha256(tasks),
        project_id="boss-absent-benchmark",
        project_assignment_sha256=canonical_sha256(_project_config()),
    )


def _winning_results(
    contract: BossAbsentBenchmarkContract,
    tasks: BossAbsentTaskSet,
) -> tuple[BossAbsentTaskResult, ...]:
    return tuple(
        _result(contract, task, system, strong=system is BenchmarkSystem.AICO)
        for system in BenchmarkSystem
        for task in tasks.tasks
    )


def _result(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    system: BenchmarkSystem,
    *,
    strong: bool,
) -> BossAbsentTaskResult:
    interventions = 0
    if task.approval_required:
        interventions = 1
    elif not strong and task.task_id in {"normal-release-audit", "bounded-budget-pressure"}:
        interventions = 1
    total_tokens: int | None = 10_000
    if not strong and task.task_id == "evidence-drift-detection":
        total_tokens = None
    elif not strong and task.task_id == "bounded-budget-pressure":
        total_tokens = contract.max_total_tokens + 1
    evidence = _evidence(full=strong, budget_present=total_tokens is not None)
    takeover = task.im_takeover_required and strong
    return BossAbsentTaskResult(
        benchmark_id=contract.benchmark_id,
        contract_sha256=canonical_sha256(contract),
        system=system,
        task_id=task.task_id,
        dispatched=True,
        terminal_status=BenchmarkTerminalStatus.COMPLETE,
        wall_seconds=120,
        human_interventions=interventions,
        total_tokens=total_tokens,
        evidence=evidence,
        role_checkpoints=_checkpoints(task) if strong else (),
        takeover_actions=1 if takeover else None,
        takeover_seconds=10 if takeover else None,
        takeover_evidence_sha256=_sha(f"takeover-{task.task_id}") if takeover else None,
        restart_evidence_sha256=(_sha("restart") if task.restart_required and strong else None),
        approval_evidence_sha256=(_sha("approval") if task.approval_required else None),
    )


def _evidence(*, full: bool, budget_present: bool = True) -> BenchmarkEvidenceSet:
    status = BenchmarkEvidenceStatus.PRESENT
    missing = BenchmarkEvidenceStatus.MISSING
    return BenchmarkEvidenceSet(
        terminal=_proof(status, "terminal"),
        acceptance=_proof(status, "acceptance"),
        source_integrity=_proof(status if full else missing, "source"),
        test_gate=_proof(status, "test"),
        budget_receipt=_proof(status if budget_present else missing, "budget"),
    )


def _proof(status: BenchmarkEvidenceStatus, label: str) -> BenchmarkEvidenceProof:
    return BenchmarkEvidenceProof(
        status=status,
        sha256=None if status is BenchmarkEvidenceStatus.MISSING else _sha(label),
    )


def _checkpoints(task: BossAbsentTask) -> tuple[BenchmarkRoleCheckpoint, ...]:
    return tuple(
        BenchmarkRoleCheckpoint(
            checkpoint_id=f"checkpoint-{index}",
            role=role,
            agent_id=f"agent-{role}",
            artifact_sha256=_sha(f"{task.task_id}-{role}"),
            consumed_by=("terminal",),
        )
        for index, role in enumerate(task.required_roles, start=1)
    )


def _freeze_args(output: Path) -> list[str]:
    return [
        "freeze",
        "--tasks",
        str(_TASKS_PATH),
        "--project-config",
        str(_PROJECT_PATH),
        "--project-id",
        "boss-absent-benchmark",
        "--output",
        str(output),
        "--benchmark-id",
        "boss-absent-v1-test",
        "--model",
        "gpt-5.6-sol",
        "--reasoning-effort",
        "high",
        "--repo-revision",
        "a" * 40,
        "--aico-version",
        "test-aico",
        "--codex-cli-version",
        "0.144.5",
        "--wall-window-seconds",
        "3600",
        "--max-total-tokens",
        "50000",
    ]


def _project_config() -> ProjectAssignmentConfig:
    return ProjectAssignmentConfig.model_validate_json(_PROJECT_PATH.read_text(encoding="utf-8"))


def _sha(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()
