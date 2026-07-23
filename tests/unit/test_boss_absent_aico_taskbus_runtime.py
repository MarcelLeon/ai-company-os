from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.app.boss_absent_aico_runner import (
    AicoBenchmarkRunPhase,
    AicoRoleRequest,
    JsonAicoBenchmarkStateStore,
    admit_aico_benchmark_runtime,
    advance_aico_benchmark_task,
)
from aico.app.boss_absent_aico_taskbus_runtime import (
    AicoBenchmarkRoleTarget,
    TaskBusAicoBenchmarkRuntime,
)
from aico.core.boss_absent_benchmark import (
    BenchmarkScenario,
    BossAbsentBenchmarkContract,
    BossAbsentTask,
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
from aico.core.preauthorized_execution import preauthorized_model_contract
from aico.core.project_assignment import (
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
)
from aico.core.task_bus import TaskBus


class RecordingAdapter:
    name = "recording"

    def __init__(self, *, exact_model: bool = True) -> None:
        self.tasks: list[Task] = []
        self._usage: dict[str, TaskUsage] = {}
        self._executions: dict[str, str] = {}
        self._exact_model = exact_model

    def capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.CODE_REVIEW, Capability.STREAM_OUTPUT})

    def supports_preauthorized_execution(self, mode: str) -> bool:
        return mode == "read_only"

    def supports_preauthorized_budget(self, max_total_tokens: int) -> bool:
        return max_total_tokens >= 100

    def supports_preauthorized_model(self, model: str, reasoning_effort: str) -> bool:
        return self._exact_model and model == "gpt-5.6-sol" and reasoning_effort == "high"

    async def receive_task(self, task: Task) -> TaskAck:
        self.tasks.append(task)
        self._usage[task.task_id] = TaskUsage(
            input_tokens=90,
            output_tokens=10,
            total_tokens=100,
        )
        self._executions[task.task_id] = f"provider-execution-{task.task_id}"
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    async def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        yield TaskOutput(
            task_id=task_id,
            sequence=1,
            type=OutputType.TEXT,
            content='{"status":"complete","artifact":"bounded"}',
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


def _request(*, prior: str | None = None, role: str = "lead") -> AicoRoleRequest:
    return AicoRoleRequest(
        dispatch_id=("1" if role == "lead" else "2") * 64,
        contract_sha256="a" * 64,
        benchmark_id="boss-absent-runtime",
        task_id="normal-role-chain",
        sequence=1 if role == "lead" else 2,
        role=role,
        objective="produce a verified handoff",
        fixture='{"release":"candidate-17","tests":"green"}',
        acceptance=("plan exists", "review exists"),
        model="gpt-5.6-sol",
        reasoning_effort="high",
        remaining_tokens=1_000,
        prior_checkpoint_sha256=prior,
    )


def _runtime(
    tmp_path: Path,
    adapter: RecordingAdapter,
    *,
    instance: str = "a",
) -> TaskBusAicoBenchmarkRuntime:
    return TaskBusAicoBenchmarkRuntime(
        task_bus=TaskBus(adapter),
        project_directory=_directory(),
        project_id="benchmark-project",
        role_targets=(
            AicoBenchmarkRoleTarget(
                role="lead",
                agent_id="agent-lead",
                assignment_seat="lead-seat",
                target_persona="recording",
            ),
            AicoBenchmarkRoleTarget(
                role="reviewer",
                agent_id="agent-reviewer",
                assignment_seat="reviewer-seat",
                target_persona="recording",
            ),
        ),
        runtime_build="aico-test",
        runtime_instance_sha256=instance * 64,
        artifact_dir=(tmp_path / "artifacts").absolute(),
        receipt_dir=(tmp_path / "receipts").absolute(),
        expires_at=datetime(2027, 1, 1, tzinfo=UTC),
        max_duration_seconds=10,
    )


def _directory() -> ProjectAssignmentDirectory:
    return ProjectAssignmentDirectory(
        ProjectAssignmentConfig.model_validate(
            {
                "agents": {
                    "agent-lead": {
                        "id": "agent-lead",
                        "provider": "recording",
                        "title": "Lead",
                    },
                    "agent-reviewer": {
                        "id": "agent-reviewer",
                        "provider": "recording",
                        "title": "Reviewer",
                    },
                },
                "roles": {
                    "lead": {"id": "lead", "title": "Lead"},
                    "reviewer": {"id": "reviewer", "title": "Reviewer"},
                },
                "projects": {
                    "benchmark-project": {
                        "id": "benchmark-project",
                        "name": "Benchmark",
                        "repo": ".",
                        "roles": {
                            "lead": {"role": "lead"},
                            "reviewer": {"role": "reviewer"},
                        },
                    }
                },
                "appointments": [
                    {
                        "seat": "lead-seat",
                        "project": "benchmark-project",
                        "agent": "agent-lead",
                        "role": "lead",
                    },
                    {
                        "seat": "reviewer-seat",
                        "project": "benchmark-project",
                        "agent": "agent-reviewer",
                        "role": "reviewer",
                    },
                ],
            }
        )
    )


@pytest.mark.asyncio
async def test_taskbus_runtime_binds_exact_model_budget_and_durable_receipt(
    tmp_path: Path,
) -> None:
    adapter = RecordingAdapter()
    runtime = _runtime(tmp_path, adapter)
    request = _request()

    observation = await runtime.execute_role(request)
    recovered = await _runtime(tmp_path, RecordingAdapter()).recover_role(request.dispatch_id)

    assert observation == recovered
    assert observation.agent_id == "agent-lead"
    assert observation.usage.total_tokens == 100
    assert len(adapter.tasks) == 1
    assert preauthorized_model_contract(adapter.tasks[0]) == ("gpt-5.6-sol", "high")
    assert any(
        entry.key == "aico.preauthorized_max_total_tokens" and entry.value == 1_000
        for entry in adapter.tasks[0].metadata
    )
    assert (tmp_path / "receipts" / f"{request.dispatch_id}.json").stat().st_mode & 0o777 == (0o600)


@pytest.mark.asyncio
async def test_taskbus_runtime_passes_exact_prior_artifact_to_next_agent(
    tmp_path: Path,
) -> None:
    adapter = RecordingAdapter()
    runtime = _runtime(tmp_path, adapter)
    first = await runtime.execute_role(_request())

    second = await runtime.execute_role(_request(prior=first.artifact_sha256, role="reviewer"))

    assert second.consumed_checkpoint_sha256 == first.artifact_sha256
    assert second.agent_id == "agent-reviewer"
    assert first.artifact_sha256 in (tmp_path / "artifacts" / f"{first.artifact_sha256}.txt").name
    assert "Prior role artifact" in adapter.tasks[1].payload
    assert 'Frozen fixture:\n{"release":"candidate-17","tests":"green"}' in (
        adapter.tasks[1].payload
    )
    assert '"artifact":"bounded"' in adapter.tasks[1].payload


def test_taskbus_runtime_preflight_rejects_missing_exact_model_boundary(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path, RecordingAdapter(exact_model=False))

    refusal = runtime.preflight_role(_request())

    assert refusal == "adapter lacks an enforced exact model boundary"


def test_taskbus_runtime_preflight_rejects_expired_authorization(tmp_path: Path) -> None:
    runtime = TaskBusAicoBenchmarkRuntime(
        task_bus=TaskBus(RecordingAdapter()),
        project_directory=_directory(),
        project_id="benchmark-project",
        role_targets=(
            AicoBenchmarkRoleTarget(
                role="lead",
                agent_id="agent-lead",
                assignment_seat="lead-seat",
                target_persona="recording",
            ),
        ),
        runtime_build="aico-test",
        runtime_instance_sha256="a" * 64,
        artifact_dir=(tmp_path / "artifacts").absolute(),
        receipt_dir=(tmp_path / "receipts").absolute(),
        expires_at=datetime(2026, 7, 22, tzinfo=UTC),
        max_duration_seconds=10,
        clock=lambda: datetime(2026, 7, 23, tzinfo=UTC),
    )

    assert runtime.preflight_role(_request()) == ("AICO benchmark runtime authorization expired")


def test_taskbus_runtime_requires_distinct_agent_targets(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="agents must be distinct"):
        TaskBusAicoBenchmarkRuntime(
            task_bus=TaskBus(RecordingAdapter()),
            project_directory=_directory(),
            project_id="benchmark-project",
            role_targets=(
                AicoBenchmarkRoleTarget(
                    role="lead",
                    agent_id="agent-shared",
                    assignment_seat="lead-seat",
                    target_persona="recording",
                ),
                AicoBenchmarkRoleTarget(
                    role="reviewer",
                    agent_id="agent-shared",
                    assignment_seat="reviewer-seat",
                    target_persona="recording",
                ),
            ),
            runtime_build="aico-test",
            runtime_instance_sha256="a" * 64,
            artifact_dir=(tmp_path / "artifacts").absolute(),
            receipt_dir=(tmp_path / "receipts").absolute(),
            expires_at=datetime(2027, 1, 1, tzinfo=UTC),
            max_duration_seconds=10,
        )


def test_taskbus_runtime_rejects_target_that_drifted_from_project_assignment(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="drifted from project assignment"):
        TaskBusAicoBenchmarkRuntime(
            task_bus=TaskBus(RecordingAdapter()),
            project_directory=_directory(),
            project_id="benchmark-project",
            role_targets=(
                AicoBenchmarkRoleTarget(
                    role="lead",
                    agent_id="agent-reviewer",
                    assignment_seat="reviewer-seat",
                    target_persona="recording",
                ),
            ),
            runtime_build="aico-test",
            runtime_instance_sha256="a" * 64,
            artifact_dir=(tmp_path / "artifacts").absolute(),
            receipt_dir=(tmp_path / "receipts").absolute(),
            expires_at=datetime(2027, 1, 1, tzinfo=UTC),
            max_duration_seconds=10,
        )


@pytest.mark.asyncio
async def test_taskbus_runtime_continues_role_chain_after_runtime_restart(
    tmp_path: Path,
) -> None:
    contract = BossAbsentBenchmarkContract(
        benchmark_id="boss-absent-runtime",
        frozen_at=datetime(2026, 7, 23, tzinfo=UTC),
        model="gpt-5.6-sol",
        reasoning_effort="high",
        repo_revision="a" * 40,
        aico_version="test",
        codex_cli_version="0.144.5",
        wall_window_seconds=600,
        max_total_tokens=1_000,
        task_set_sha256="b" * 64,
        project_id="benchmark-project",
        project_assignment_sha256="c" * 64,
    )
    task = BossAbsentTask(
        task_id="restart-role-chain",
        scenario=BenchmarkScenario.RESTART,
        objective="produce a bounded verified handoff",
        fixture='{"release":"candidate-17","tests":"green"}',
        acceptance=("lead plans", "reviewer verifies"),
        required_roles=("lead", "reviewer"),
        unattended_eligible=True,
        collaboration_required=True,
        restart_required=True,
        im_takeover_required=True,
    )
    state_store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())
    first_runtime = _runtime(tmp_path, RecordingAdapter(), instance="a")
    admission = admit_aico_benchmark_runtime(
        contract,
        first_runtime.capabilities(
            model=contract.model,
            reasoning_effort=contract.reasoning_effort,
        ),
    )

    first = await advance_aico_benchmark_task(
        contract,
        task,
        admission,
        first_runtime,
        state_store,
    )
    second_adapter = RecordingAdapter()
    second_runtime = _runtime(tmp_path, second_adapter, instance="b")
    completed = await advance_aico_benchmark_task(
        contract,
        task,
        admission,
        second_runtime,
        state_store,
    )

    assert first.phase is AicoBenchmarkRunPhase.RESTART_PENDING
    assert completed.phase is AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE
    assert completed.restart_count == 1
    assert completed.total_tokens == 200
    assert [checkpoint.agent_id for checkpoint in completed.checkpoints] == [
        "agent-lead",
        "agent-reviewer",
    ]
    assert second_adapter.tasks[0].payload.find("Prior role artifact") >= 0
    assert preauthorized_model_contract(second_adapter.tasks[0]) == (
        contract.model,
        contract.reasoning_effort,
    )
