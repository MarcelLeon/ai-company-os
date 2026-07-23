"""Restart-safe AICO role orchestration for the boss-absent benchmark."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol

from pydantic import Field, model_validator

from aico.core.boss_absent_benchmark import (
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    canonical_sha256,
)
from aico.core.models import FrozenModel, TaskUsage

Sha256 = str


class AicoBenchmarkRunPhase(StrEnum):
    RUNNING = "running"
    DISPATCH_PENDING = "dispatch_pending"
    DISPATCH_AMBIGUOUS = "dispatch_ambiguous"
    RESTART_PENDING = "restart_pending"
    APPROVAL_PENDING = "approval_pending"
    ROLE_CHAIN_COMPLETE = "role_chain_complete"
    BLOCKED = "blocked"
    FAILED = "failed"


class AicoRoleStatus(StrEnum):
    COMPLETE = "complete"
    BLOCKED = "blocked"
    FAILED = "failed"


class AicoBenchmarkRuntimeCapabilities(FrozenModel):
    runtime_build: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=128)
    reasoning_effort: str = Field(min_length=1, max_length=32)
    isolated_run_state: bool
    managed_role_orchestration: bool
    hard_remaining_token_cap: bool
    provider_usage_observable: bool
    durable_dispatch_reconciliation: bool


class AicoBenchmarkRuntimeAdmission(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_build: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=128)
    reasoning_effort: str = Field(min_length=1, max_length=32)
    admitted: Literal[True] = True


class AicoRoleRequest(FrozenModel):
    version: Literal[1] = 1
    dispatch_id: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    sequence: int = Field(ge=1, le=32)
    role: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,31}$")
    objective: str = Field(min_length=1, max_length=2_000)
    fixture: str = Field(min_length=1, max_length=16_384)
    acceptance: tuple[str, ...] = Field(min_length=1, max_length=12)
    model: str = Field(min_length=1, max_length=128)
    reasoning_effort: str = Field(min_length=1, max_length=32)
    remaining_tokens: int = Field(ge=1)
    prior_checkpoint_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    restart_from_runtime_instance_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )


class AicoRoleObservation(FrozenModel):
    version: Literal[1] = 1
    dispatch_id: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    role: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,31}$")
    agent_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,63}$")
    assignment_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    provider_execution_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_instance_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    input_fixture_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    consumed_checkpoint_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    status: AicoRoleStatus
    usage: TaskUsage

    @model_validator(mode="after")
    def validate_usage(self) -> AicoRoleObservation:
        if self.usage.total_tokens != self.usage.input_tokens + self.usage.output_tokens:
            raise ValueError("AICO role provider usage total is inconsistent")
        if self.usage.total_tokens <= 0:
            raise ValueError("AICO role provider usage must be positive")
        return self


class AicoRoleCheckpoint(FrozenModel):
    sequence: int = Field(ge=1, le=32)
    dispatch_id: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    role: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,31}$")
    agent_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,63}$")
    assignment_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    provider_execution_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_instance_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    input_fixture_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    consumed_checkpoint_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    usage: TaskUsage


class AicoApprovalCheckpoint(FrozenModel):
    version: Literal[1] = 1
    after_sequence: int = Field(ge=1, le=32)
    request_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    grant_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    action_receipt_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")


class AicoBenchmarkRunState(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_admission_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    benchmark_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    phase: AicoBenchmarkRunPhase = AicoBenchmarkRunPhase.RUNNING
    checkpoints: tuple[AicoRoleCheckpoint, ...] = Field(default=(), max_length=32)
    approval_request_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    approval_checkpoint: AicoApprovalCheckpoint | None = None
    pending_role: AicoRoleRequest | None = None
    total_tokens: int = Field(default=0, ge=0)
    unaccepted_usage: TaskUsage | None = None
    failed_observation_sha256: Sha256 | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    restart_count: int = Field(default=0, ge=0, le=8)
    failure: str | None = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def validate_state(self) -> AicoBenchmarkRunState:
        pending_phase = self.phase in {
            AicoBenchmarkRunPhase.DISPATCH_PENDING,
            AicoBenchmarkRunPhase.DISPATCH_AMBIGUOUS,
        }
        if pending_phase != (self.pending_role is not None):
            raise ValueError("AICO runner pending phase and role intent do not match")
        expected_tokens = sum(item.usage.total_tokens for item in self.checkpoints)
        if self.unaccepted_usage is not None:
            expected_tokens += self.unaccepted_usage.total_tokens
        if self.total_tokens != expected_tokens:
            raise ValueError("AICO runner total tokens do not match checkpoints")
        if tuple(item.sequence for item in self.checkpoints) != tuple(
            range(1, len(self.checkpoints) + 1)
        ):
            raise ValueError("AICO runner checkpoint sequence is not contiguous")
        if (self.failure is not None) != (
            self.phase in {AicoBenchmarkRunPhase.BLOCKED, AicoBenchmarkRunPhase.FAILED}
        ):
            raise ValueError("AICO runner failure reason does not match phase")
        if (self.unaccepted_usage is None) != (self.failed_observation_sha256 is None):
            raise ValueError("AICO runner failed observation evidence is incomplete")
        if self.approval_checkpoint is not None:
            if (
                self.approval_request_sha256 != self.approval_checkpoint.request_sha256
                or self.approval_checkpoint.after_sequence > len(self.checkpoints)
            ):
                raise ValueError("AICO runner approval checkpoint is inconsistent")
        if self.phase is AicoBenchmarkRunPhase.APPROVAL_PENDING and (
            self.approval_request_sha256 is None or self.approval_checkpoint is not None
        ):
            raise ValueError("AICO runner approval pending state is inconsistent")
        return self


class AicoBenchmarkRuntime(Protocol):
    def preflight_role(self, request: AicoRoleRequest) -> str | None: ...

    async def execute_role(self, request: AicoRoleRequest) -> AicoRoleObservation: ...

    async def recover_role(self, dispatch_id: str) -> AicoRoleObservation | None: ...


class AicoBenchmarkStateStore(Protocol):
    def load(self) -> AicoBenchmarkRunState | None: ...

    def save(self, state: AicoBenchmarkRunState) -> None: ...


class JsonAicoBenchmarkStateStore:
    """Owner-only atomic state used by separate benchmark runner processes."""

    def __init__(self, path: Path) -> None:
        if not path.is_absolute():
            raise ValueError("AICO benchmark state path must be absolute")
        self._path = path

    def load(self) -> AicoBenchmarkRunState | None:
        if self._path.is_symlink():
            raise ValueError("AICO benchmark state must be a regular non-symlink file")
        if not self._path.exists():
            return None
        _validate_owner_file(self._path)
        try:
            return AicoBenchmarkRunState.model_validate_json(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            raise ValueError("AICO benchmark state is invalid") from None

    def save(self, state: AicoBenchmarkRunState) -> None:
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self._path.is_symlink():
            raise ValueError("AICO benchmark state must be a regular non-symlink file")
        if self._path.exists():
            _validate_owner_file(self._path)
        payload = state.model_dump_json(indent=2).encode("utf-8") + b"\n"
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f".{self._path.name}.", suffix=".tmp", dir=self._path.parent
        )
        temporary = Path(raw_path)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self._path)
            _fsync_directory(self._path.parent)
        finally:
            if temporary.exists():
                temporary.unlink()


def admit_aico_benchmark_runtime(
    contract: BossAbsentBenchmarkContract,
    capabilities: AicoBenchmarkRuntimeCapabilities,
) -> AicoBenchmarkRuntimeAdmission:
    if capabilities.model != contract.model or capabilities.reasoning_effort != (
        contract.reasoning_effort
    ):
        raise ValueError("AICO benchmark runtime model contract drifted")
    required = (
        capabilities.isolated_run_state,
        capabilities.managed_role_orchestration,
        capabilities.hard_remaining_token_cap,
        capabilities.provider_usage_observable,
        capabilities.durable_dispatch_reconciliation,
    )
    if not all(required):
        raise ValueError("AICO benchmark runtime is missing a required capability")
    return AicoBenchmarkRuntimeAdmission(
        contract_sha256=canonical_sha256(contract),
        runtime_build=capabilities.runtime_build,
        model=capabilities.model,
        reasoning_effort=capabilities.reasoning_effort,
    )


async def advance_aico_benchmark_task(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: AicoBenchmarkRuntimeAdmission,
    runtime: AicoBenchmarkRuntime,
    store: AicoBenchmarkStateStore,
) -> AicoBenchmarkRunState:
    contract_sha = canonical_sha256(contract)
    _validate_admission(contract, admission, contract_sha)
    state = store.load() or _new_state(contract, task, admission, contract_sha)
    _validate_loaded_state(state, contract, task, admission, contract_sha)
    if state.phase in {
        AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE,
        AicoBenchmarkRunPhase.APPROVAL_PENDING,
        AicoBenchmarkRunPhase.BLOCKED,
        AicoBenchmarkRunPhase.FAILED,
    }:
        return state
    if state.pending_role is not None:
        return await _reconcile_pending(state, task, runtime, store)
    return await _dispatch_next(state, contract, task, runtime, store)


async def _dispatch_next(
    state: AicoBenchmarkRunState,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    runtime: AicoBenchmarkRuntime,
    store: AicoBenchmarkStateStore,
) -> AicoBenchmarkRunState:
    if len(state.checkpoints) >= len(task.required_roles):
        completed = _updated_state(state, phase=AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE)
        store.save(completed)
        return completed
    remaining = contract.max_total_tokens - state.total_tokens
    if remaining <= 0:
        return _fail(state, store, "shared token budget exhausted", blocked=True)
    request = _role_request(state, contract, task, remaining)
    refusal = runtime.preflight_role(request)
    if refusal is not None:
        return _fail(state, store, f"role preflight refused: {refusal}", blocked=True)
    pending = _updated_state(
        state,
        phase=AicoBenchmarkRunPhase.DISPATCH_PENDING,
        pending_role=request,
    )
    store.save(pending)
    observation = await runtime.execute_role(request)
    return _commit_observation(pending, task, observation, store)


async def _reconcile_pending(
    state: AicoBenchmarkRunState,
    task: BossAbsentTask,
    runtime: AicoBenchmarkRuntime,
    store: AicoBenchmarkStateStore,
) -> AicoBenchmarkRunState:
    assert state.pending_role is not None
    observation = await runtime.recover_role(state.pending_role.dispatch_id)
    if observation is None:
        ambiguous = _updated_state(state, phase=AicoBenchmarkRunPhase.DISPATCH_AMBIGUOUS)
        store.save(ambiguous)
        return ambiguous
    return _commit_observation(state, task, observation, store)


def _commit_observation(
    state: AicoBenchmarkRunState,
    task: BossAbsentTask,
    observation: AicoRoleObservation,
    store: AicoBenchmarkStateStore,
) -> AicoBenchmarkRunState:
    request = state.pending_role
    assert request is not None
    _validate_observation(state, task, request, observation)
    if observation.usage.total_tokens > request.remaining_tokens:
        return _fail_with_observation(
            state,
            store,
            observation,
            "role exceeded shared remaining token budget",
        )
    if observation.status is AicoRoleStatus.BLOCKED:
        return _fail_with_observation(
            state,
            store,
            observation,
            "role reported blocked",
            blocked=True,
        )
    if observation.status is AicoRoleStatus.FAILED:
        return _fail_with_observation(state, store, observation, "role reported failed")
    checkpoint = AicoRoleCheckpoint(
        sequence=request.sequence,
        dispatch_id=request.dispatch_id,
        role=request.role,
        agent_id=observation.agent_id,
        assignment_sha256=observation.assignment_sha256,
        provider_execution_sha256=observation.provider_execution_sha256,
        runtime_instance_sha256=observation.runtime_instance_sha256,
        input_fixture_sha256=observation.input_fixture_sha256,
        artifact_sha256=observation.artifact_sha256,
        consumed_checkpoint_sha256=observation.consumed_checkpoint_sha256,
        usage=observation.usage,
    )
    checkpoints = (*state.checkpoints, checkpoint)
    approval_request_sha = state.approval_request_sha256
    if task.approval_required and len(checkpoints) == 1 and state.approval_checkpoint is None:
        approval_request_sha = _approval_request_sha(state.contract_sha256, task)
        phase = AicoBenchmarkRunPhase.APPROVAL_PENDING
    else:
        phase = _next_phase(task, checkpoints)
    restart_count = state.restart_count
    if request.restart_from_runtime_instance_sha256 is not None:
        restart_count += 1
    updated = _updated_state(
        state,
        phase=phase,
        checkpoints=checkpoints,
        approval_request_sha256=approval_request_sha,
        pending_role=None,
        total_tokens=state.total_tokens + observation.usage.total_tokens,
        restart_count=restart_count,
    )
    store.save(updated)
    return updated


def _validate_observation(
    state: AicoBenchmarkRunState,
    task: BossAbsentTask,
    request: AicoRoleRequest,
    observation: AicoRoleObservation,
) -> None:
    if observation.dispatch_id != request.dispatch_id or observation.role != request.role:
        raise ValueError("AICO role observation identity drifted")
    if observation.consumed_checkpoint_sha256 != request.prior_checkpoint_sha256:
        raise ValueError("AICO role did not consume the exact prior checkpoint")
    if observation.input_fixture_sha256 != hashlib.sha256(request.fixture.encode()).hexdigest():
        raise ValueError("AICO role did not consume the exact frozen fixture")
    if task.collaboration_required and any(
        checkpoint.agent_id == observation.agent_id for checkpoint in state.checkpoints
    ):
        raise ValueError("AICO collaboration reused an earlier benchmark agent")
    if task.collaboration_required and any(
        checkpoint.provider_execution_sha256 == observation.provider_execution_sha256
        for checkpoint in state.checkpoints
    ):
        raise ValueError("AICO collaboration reused an earlier provider execution")
    if request.restart_from_runtime_instance_sha256 is not None:
        if observation.runtime_instance_sha256 == request.restart_from_runtime_instance_sha256:
            raise ValueError("AICO restart scenario reused the prior runtime instance")


def _next_phase(
    task: BossAbsentTask,
    checkpoints: tuple[AicoRoleCheckpoint, ...],
) -> AicoBenchmarkRunPhase:
    if task.restart_required and len(checkpoints) == 1:
        return AicoBenchmarkRunPhase.RESTART_PENDING
    if len(checkpoints) == len(task.required_roles):
        return AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE
    return AicoBenchmarkRunPhase.RUNNING


def record_aico_approval_checkpoint(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: AicoBenchmarkRuntimeAdmission,
    checkpoint: AicoApprovalCheckpoint,
    store: AicoBenchmarkStateStore,
) -> AicoBenchmarkRunState:
    contract_sha = canonical_sha256(contract)
    _validate_admission(contract, admission, contract_sha)
    state = store.load()
    if state is None:
        raise ValueError("AICO approval cannot precede role execution")
    _validate_loaded_state(state, contract, task, admission, contract_sha)
    expected_request = _approval_request_sha(contract_sha, task)
    identity = (
        task.approval_required
        and state.phase is AicoBenchmarkRunPhase.APPROVAL_PENDING
        and len(state.checkpoints) == 1
        and state.approval_request_sha256 == expected_request
        and checkpoint.after_sequence == 1
        and checkpoint.request_sha256 == expected_request
    )
    if not identity:
        raise ValueError("AICO approval checkpoint does not match the pending boundary")
    updated = _updated_state(
        state,
        phase=AicoBenchmarkRunPhase.RUNNING,
        approval_checkpoint=checkpoint,
    )
    store.save(updated)
    return updated


def _role_request(
    state: AicoBenchmarkRunState,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    remaining: int,
) -> AicoRoleRequest:
    sequence = len(state.checkpoints) + 1
    role = task.required_roles[sequence - 1]
    dispatch_id = _dispatch_id(state, task.task_id, sequence)
    return AicoRoleRequest(
        dispatch_id=dispatch_id,
        contract_sha256=state.contract_sha256,
        benchmark_id=contract.benchmark_id,
        task_id=task.task_id,
        sequence=sequence,
        role=role,
        objective=task.objective,
        fixture=task.fixture,
        acceptance=task.acceptance,
        model=contract.model,
        reasoning_effort=contract.reasoning_effort,
        remaining_tokens=remaining,
        prior_checkpoint_sha256=(
            None if not state.checkpoints else state.checkpoints[-1].artifact_sha256
        ),
        restart_from_runtime_instance_sha256=(
            state.checkpoints[-1].runtime_instance_sha256
            if state.phase is AicoBenchmarkRunPhase.RESTART_PENDING
            else None
        ),
    )


def _dispatch_id(state: AicoBenchmarkRunState, task_id: str, sequence: int) -> str:
    return hashlib.sha256(
        f"aico-benchmark-role-v1\0{state.contract_sha256}\0{task_id}\0{sequence}".encode()
    ).hexdigest()


def _approval_request_sha(contract_sha: str, task: BossAbsentTask) -> str:
    return hashlib.sha256(
        (f"aico-benchmark-approval-v1\0{contract_sha}\0{task.task_id}\0{task.fixture}").encode()
    ).hexdigest()


def _new_state(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: AicoBenchmarkRuntimeAdmission,
    contract_sha: str,
) -> AicoBenchmarkRunState:
    return AicoBenchmarkRunState(
        contract_sha256=contract_sha,
        runtime_admission_sha256=canonical_sha256(admission),
        benchmark_id=contract.benchmark_id,
        task_id=task.task_id,
    )


def _validate_admission(
    contract: BossAbsentBenchmarkContract,
    admission: AicoBenchmarkRuntimeAdmission,
    contract_sha: str,
) -> None:
    if admission.contract_sha256 != contract_sha:
        raise ValueError("AICO benchmark runtime admission is for another contract")
    if admission.model != contract.model or admission.reasoning_effort != contract.reasoning_effort:
        raise ValueError("AICO benchmark runtime admission model drifted")


def _validate_loaded_state(
    state: AicoBenchmarkRunState,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: AicoBenchmarkRuntimeAdmission,
    contract_sha: str,
) -> None:
    identity = (
        state.contract_sha256 == contract_sha
        and state.runtime_admission_sha256 == canonical_sha256(admission)
        and state.benchmark_id == contract.benchmark_id
        and state.task_id == task.task_id
    )
    if not identity:
        raise ValueError("AICO benchmark persisted state identity drifted")
    if len(state.checkpoints) > len(task.required_roles):
        raise ValueError("AICO benchmark state has excess role checkpoints")
    if task.collaboration_required and len(
        {checkpoint.agent_id for checkpoint in state.checkpoints}
    ) != len(state.checkpoints):
        raise ValueError("AICO benchmark persisted collaboration reused an agent")
    if task.collaboration_required and len(
        {checkpoint.provider_execution_sha256 for checkpoint in state.checkpoints}
    ) != len(state.checkpoints):
        raise ValueError("AICO benchmark persisted collaboration reused a provider execution")
    if len({checkpoint.artifact_sha256 for checkpoint in state.checkpoints}) != len(
        state.checkpoints
    ):
        raise ValueError("AICO benchmark persisted checkpoint artifacts are not unique")
    if task.approval_required:
        expected_request = _approval_request_sha(contract_sha, task)
        if len(state.checkpoints) >= 1 and state.approval_request_sha256 != expected_request:
            raise ValueError("AICO benchmark approval request drifted")
        if len(state.checkpoints) >= 2 and state.approval_checkpoint is None:
            raise ValueError("AICO benchmark advanced past approval without a checkpoint")
        if state.approval_checkpoint is not None and (
            state.approval_checkpoint.after_sequence != 1
            or state.approval_checkpoint.request_sha256 != expected_request
        ):
            raise ValueError("AICO benchmark approval checkpoint drifted")
        if (state.phase is AicoBenchmarkRunPhase.APPROVAL_PENDING) != (
            len(state.checkpoints) == 1 and state.approval_checkpoint is None
        ):
            raise ValueError("AICO benchmark approval phase drifted")
    elif state.approval_request_sha256 is not None or state.approval_checkpoint is not None:
        raise ValueError("AICO non-approval task contains approval state")
    for index, checkpoint in enumerate(state.checkpoints):
        if checkpoint.role != task.required_roles[index]:
            raise ValueError("AICO benchmark role checkpoint order drifted")
        if checkpoint.input_fixture_sha256 != hashlib.sha256(task.fixture.encode()).hexdigest():
            raise ValueError("AICO benchmark persisted fixture fingerprint drifted")
        expected = None if index == 0 else state.checkpoints[index - 1].artifact_sha256
        if checkpoint.consumed_checkpoint_sha256 != expected:
            raise ValueError("AICO benchmark persisted checkpoint chain drifted")
    if (
        state.total_tokens > contract.max_total_tokens
        and state.phase is not AicoBenchmarkRunPhase.FAILED
    ):
        raise ValueError("AICO benchmark persisted usage exceeded the contract")
    if state.pending_role is not None:
        _validate_pending_role(state, contract, task)


def _validate_pending_role(
    state: AicoBenchmarkRunState,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
) -> None:
    request = state.pending_role
    assert request is not None
    sequence = len(state.checkpoints) + 1
    if sequence > len(task.required_roles):
        raise ValueError("AICO benchmark pending role exceeds the frozen role chain")
    expected_restart = (
        state.checkpoints[-1].runtime_instance_sha256
        if task.restart_required and len(state.checkpoints) == 1
        else None
    )
    identity = (
        request.contract_sha256 == state.contract_sha256
        and request.benchmark_id == contract.benchmark_id
        and request.task_id == task.task_id
        and request.sequence == sequence
        and request.role == task.required_roles[sequence - 1]
        and request.objective == task.objective
        and request.fixture == task.fixture
        and request.acceptance == task.acceptance
        and request.model == contract.model
        and request.reasoning_effort == contract.reasoning_effort
        and request.remaining_tokens == contract.max_total_tokens - state.total_tokens
        and request.prior_checkpoint_sha256
        == (None if not state.checkpoints else state.checkpoints[-1].artifact_sha256)
        and request.restart_from_runtime_instance_sha256 == expected_restart
    )
    if not identity or request.dispatch_id != _dispatch_id(state, task.task_id, sequence):
        raise ValueError("AICO benchmark pending role intent drifted")


def _fail(
    state: AicoBenchmarkRunState,
    store: AicoBenchmarkStateStore,
    reason: str,
    *,
    blocked: bool = False,
) -> AicoBenchmarkRunState:
    failed = _updated_state(
        state,
        phase=(AicoBenchmarkRunPhase.BLOCKED if blocked else AicoBenchmarkRunPhase.FAILED),
        pending_role=None,
        failure=reason,
    )
    store.save(failed)
    return failed


def _fail_with_observation(
    state: AicoBenchmarkRunState,
    store: AicoBenchmarkStateStore,
    observation: AicoRoleObservation,
    reason: str,
    *,
    blocked: bool = False,
) -> AicoBenchmarkRunState:
    failed = _updated_state(
        state,
        phase=(AicoBenchmarkRunPhase.BLOCKED if blocked else AicoBenchmarkRunPhase.FAILED),
        pending_role=None,
        total_tokens=state.total_tokens + observation.usage.total_tokens,
        unaccepted_usage=observation.usage,
        failed_observation_sha256=canonical_sha256(observation),
        failure=reason,
    )
    store.save(failed)
    return failed


def _updated_state(
    state: AicoBenchmarkRunState,
    **updates: object,
) -> AicoBenchmarkRunState:
    return AicoBenchmarkRunState.model_validate(state.model_dump() | updates)


def _validate_owner_file(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError("AICO benchmark state must be a regular non-symlink file")
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("AICO benchmark state must be owner-only")
    if info.st_size > 1_048_576:
        raise ValueError("AICO benchmark state is too large")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
