from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.app.boss_absent_aico_runner import (
    AicoApprovalCheckpoint,
    AicoBenchmarkRunPhase,
    AicoBenchmarkRuntimeAdmission,
    AicoBenchmarkRuntimeCapabilities,
    AicoRoleObservation,
    AicoRoleRequest,
    AicoRoleStatus,
    JsonAicoBenchmarkStateStore,
    admit_aico_benchmark_runtime,
    advance_aico_benchmark_task,
    record_aico_approval_checkpoint,
)
from aico.core.boss_absent_benchmark import (
    BenchmarkScenario,
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    canonical_sha256,
)
from aico.core.models import TaskUsage


class FakeRuntime:
    def __init__(self, *, instance: str = "1", tokens: int = 100) -> None:
        self.instance = instance * 64
        self.tokens = tokens
        self.requests: list[AicoRoleRequest] = []
        self.recovered: dict[str, AicoRoleObservation] = {}

    def preflight_role(self, request: AicoRoleRequest) -> str | None:
        return None

    async def execute_role(self, request: AicoRoleRequest) -> AicoRoleObservation:
        self.requests.append(request)
        observation = _observation(request, instance=self.instance, tokens=self.tokens)
        self.recovered[request.dispatch_id] = observation
        return observation

    async def recover_role(self, dispatch_id: str) -> AicoRoleObservation | None:
        return self.recovered.get(dispatch_id)


def _contract(*, budget: int = 1_000) -> BossAbsentBenchmarkContract:
    return BossAbsentBenchmarkContract(
        benchmark_id="boss-absent-test",
        frozen_at=datetime(2026, 7, 23, tzinfo=UTC),
        model="gpt-5.6-sol",
        reasoning_effort="high",
        repo_revision="a" * 40,
        aico_version="test",
        codex_cli_version="0.144.5",
        wall_window_seconds=600,
        max_total_tokens=budget,
        task_set_sha256="b" * 64,
    )


def _task(*, restart: bool = False) -> BossAbsentTask:
    return BossAbsentTask(
        task_id="normal-role-chain" if not restart else "restart-role-chain",
        scenario=(BenchmarkScenario.NORMAL if not restart else BenchmarkScenario.RESTART),
        objective="produce a bounded verified handoff",
        fixture='{"release":"candidate-17","tests":"green"}',
        acceptance=("lead plans", "reviewer verifies"),
        required_roles=("lead", "reviewer"),
        unattended_eligible=True,
        collaboration_required=True,
        restart_required=restart,
        im_takeover_required=restart,
    )


def _admission(contract: BossAbsentBenchmarkContract) -> AicoBenchmarkRuntimeAdmission:
    return admit_aico_benchmark_runtime(
        contract,
        AicoBenchmarkRuntimeCapabilities(
            runtime_build="aico-test",
            model=contract.model,
            reasoning_effort=contract.reasoning_effort,
            isolated_run_state=True,
            managed_role_orchestration=True,
            hard_remaining_token_cap=True,
            provider_usage_observable=True,
            durable_dispatch_reconciliation=True,
        ),
    )


def _observation(
    request: AicoRoleRequest,
    *,
    instance: str,
    tokens: int,
    status: AicoRoleStatus = AicoRoleStatus.COMPLETE,
) -> AicoRoleObservation:
    return AicoRoleObservation(
        dispatch_id=request.dispatch_id,
        role=request.role,
        agent_id=f"agent-{request.role}",
        runtime_instance_sha256=instance,
        input_fixture_sha256=hashlib.sha256(request.fixture.encode()).hexdigest(),
        artifact_sha256=f"{request.sequence + 2:x}" * 64,
        consumed_checkpoint_sha256=request.prior_checkpoint_sha256,
        status=status,
        usage=TaskUsage(
            input_tokens=tokens - 10,
            output_tokens=10,
            total_tokens=tokens,
        ),
    )


@pytest.mark.asyncio
async def test_runner_manages_exact_roles_and_one_shared_budget(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    runtime = FakeRuntime(tokens=100)
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())

    first = await advance_aico_benchmark_task(contract, task, _admission(contract), runtime, store)
    second = await advance_aico_benchmark_task(contract, task, _admission(contract), runtime, store)

    assert first.phase is AicoBenchmarkRunPhase.RUNNING
    assert second.phase is AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE
    assert [request.role for request in runtime.requests] == ["lead", "reviewer"]
    assert [request.remaining_tokens for request in runtime.requests] == [1_000, 900]
    assert runtime.requests[1].prior_checkpoint_sha256 == first.checkpoints[0].artifact_sha256
    assert second.total_tokens == 200
    assert (tmp_path / "state.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_runner_fails_closed_when_role_exceeds_remaining_budget(tmp_path: Path) -> None:
    contract = _contract(budget=1_000)
    runtime = FakeRuntime(tokens=1_001)
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())

    state = await advance_aico_benchmark_task(
        contract, _task(), _admission(contract), runtime, store
    )

    assert state.phase is AicoBenchmarkRunPhase.FAILED
    assert state.total_tokens == 1_001
    assert state.failed_observation_sha256 is not None
    assert state.failure == "role exceeded shared remaining token budget"


@pytest.mark.asyncio
async def test_restart_task_requires_a_different_runtime_instance(tmp_path: Path) -> None:
    contract = _contract()
    task = _task(restart=True)
    first_runtime = FakeRuntime(instance="1")
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())

    first = await advance_aico_benchmark_task(
        contract, task, _admission(contract), first_runtime, store
    )
    assert first.phase is AicoBenchmarkRunPhase.RESTART_PENDING

    second = await advance_aico_benchmark_task(
        contract, task, _admission(contract), FakeRuntime(instance="2"), store
    )
    assert second.phase is AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE
    assert second.restart_count == 1


@pytest.mark.asyncio
async def test_restart_task_rejects_same_runtime_instance(tmp_path: Path) -> None:
    contract = _contract()
    task = _task(restart=True)
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())
    await advance_aico_benchmark_task(
        contract, task, _admission(contract), FakeRuntime(instance="1"), store
    )

    with pytest.raises(ValueError, match="reused the prior runtime"):
        await advance_aico_benchmark_task(
            contract, task, _admission(contract), FakeRuntime(instance="1"), store
        )


@pytest.mark.asyncio
async def test_approval_task_cannot_dispatch_reviewer_before_action_checkpoint(
    tmp_path: Path,
) -> None:
    contract = _contract()
    task = BossAbsentTask(
        task_id="approval-role-chain",
        scenario=BenchmarkScenario.APPROVAL,
        objective="stop at the exact approval boundary",
        fixture='{"action":"write exact isolated marker"}',
        acceptance=("request approval", "execute once", "review"),
        required_roles=("implementer", "reviewer"),
        unattended_eligible=False,
        collaboration_required=True,
        im_takeover_required=True,
        approval_required=True,
    )
    runtime = FakeRuntime()
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())
    admission = _admission(contract)

    pending = await advance_aico_benchmark_task(
        contract,
        task,
        admission,
        runtime,
        store,
    )
    unchanged = await advance_aico_benchmark_task(
        contract,
        task,
        admission,
        runtime,
        store,
    )

    assert pending.phase is AicoBenchmarkRunPhase.APPROVAL_PENDING
    assert unchanged == pending
    assert [request.role for request in runtime.requests] == ["implementer"]
    assert pending.approval_request_sha256 is not None

    resumed = record_aico_approval_checkpoint(
        contract,
        task,
        admission,
        AicoApprovalCheckpoint(
            after_sequence=1,
            request_sha256=pending.approval_request_sha256,
            grant_sha256="8" * 64,
            action_receipt_sha256="9" * 64,
        ),
        store,
    )
    completed = await advance_aico_benchmark_task(
        contract,
        task,
        admission,
        runtime,
        store,
    )

    assert resumed.phase is AicoBenchmarkRunPhase.RUNNING
    assert completed.phase is AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE
    assert [request.role for request in runtime.requests] == ["implementer", "reviewer"]


@pytest.mark.asyncio
async def test_pending_dispatch_is_reconciled_without_provider_replay(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    runtime = FakeRuntime()
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())
    admission = _admission(contract)

    class CrashAfterProvider(FakeRuntime):
        async def execute_role(self, request: AicoRoleRequest) -> AicoRoleObservation:
            observation = await super().execute_role(request)
            runtime.recovered[request.dispatch_id] = observation
            raise RuntimeError("runner crashed after provider completion")

    with pytest.raises(RuntimeError, match="runner crashed"):
        await advance_aico_benchmark_task(contract, task, admission, CrashAfterProvider(), store)

    recovered = await advance_aico_benchmark_task(contract, task, admission, runtime, store)

    assert recovered.phase is AicoBenchmarkRunPhase.RUNNING
    assert len(recovered.checkpoints) == 1
    assert runtime.requests == []


@pytest.mark.asyncio
async def test_unknown_pending_dispatch_stays_ambiguous_and_is_not_replayed(
    tmp_path: Path,
) -> None:
    contract = _contract()
    task = _task()
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())

    class CrashBeforeProvider(FakeRuntime):
        async def execute_role(self, request: AicoRoleRequest) -> AicoRoleObservation:
            raise RuntimeError("provider outcome unknown")

    with pytest.raises(RuntimeError, match="outcome unknown"):
        await advance_aico_benchmark_task(
            contract, task, _admission(contract), CrashBeforeProvider(), store
        )
    fresh = FakeRuntime()
    state = await advance_aico_benchmark_task(contract, task, _admission(contract), fresh, store)

    assert state.phase is AicoBenchmarkRunPhase.DISPATCH_AMBIGUOUS
    assert fresh.requests == []


@pytest.mark.asyncio
async def test_runner_rejects_one_agent_role_play(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())

    class RolePlayingRuntime(FakeRuntime):
        async def execute_role(self, request: AicoRoleRequest) -> AicoRoleObservation:
            observation = await super().execute_role(request)
            return AicoRoleObservation.model_validate(
                observation.model_dump() | {"agent_id": "agent-shared"}
            )

    runtime = RolePlayingRuntime()
    await advance_aico_benchmark_task(contract, task, _admission(contract), runtime, store)

    with pytest.raises(ValueError, match="reused an earlier benchmark agent"):
        await advance_aico_benchmark_task(
            contract,
            task,
            _admission(contract),
            runtime,
            store,
        )


def test_runtime_admission_rejects_model_or_hard_cap_drift() -> None:
    contract = _contract()
    capabilities = AicoBenchmarkRuntimeCapabilities(
        runtime_build="aico-test",
        model=contract.model,
        reasoning_effort=contract.reasoning_effort,
        isolated_run_state=True,
        managed_role_orchestration=True,
        hard_remaining_token_cap=False,
        provider_usage_observable=True,
        durable_dispatch_reconciliation=True,
    )

    with pytest.raises(ValueError, match="required capability"):
        admit_aico_benchmark_runtime(contract, capabilities)
    with pytest.raises(ValueError, match="model contract"):
        admit_aico_benchmark_runtime(
            contract,
            capabilities.model_copy(
                update={"hard_remaining_token_cap": True, "model": "different"}
            ),
        )


def test_state_store_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    path = tmp_path / "state.json"
    path.symlink_to(target)
    store = JsonAicoBenchmarkStateStore(path.absolute())

    with pytest.raises(ValueError, match="non-symlink"):
        store.load()


@pytest.mark.asyncio
async def test_preflight_refusal_does_not_create_ambiguous_dispatch(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())

    class RefusingRuntime(FakeRuntime):
        def preflight_role(self, request: AicoRoleRequest) -> str | None:
            return "exact model unavailable"

    runtime = RefusingRuntime()
    state = await advance_aico_benchmark_task(
        contract,
        task,
        _admission(contract),
        runtime,
        store,
    )

    assert state.phase is AicoBenchmarkRunPhase.BLOCKED
    assert state.pending_role is None
    assert runtime.requests == []


def test_admission_is_bound_to_canonical_contract() -> None:
    contract = _contract()
    admission = _admission(contract)

    assert admission.contract_sha256 == canonical_sha256(contract)
