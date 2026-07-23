"""TaskBus-backed runtime transport for managed AICO benchmark roles."""

from __future__ import annotations

import asyncio
import hashlib
import os
import stat
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from pydantic import Field

from aico.app.boss_absent_aico_runner import (
    AicoBenchmarkRuntimeCapabilities,
    AicoRoleObservation,
    AicoRoleRequest,
    AicoRoleStatus,
)
from aico.core.boss_absent_benchmark import canonical_sha256
from aico.core.collaboration import task_with_exact_output_constraint
from aico.core.models import (
    AckStatus,
    FrozenModel,
    MetadataEntry,
    OutputType,
    Task,
    TaskSnapshot,
    TaskStatus,
    utc_now,
)
from aico.core.preauthorized_execution import task_with_preauthorized_execution
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectAssignmentDirectory,
    task_with_assignment_context,
)
from aico.core.task_bus import (
    TaskBus,
    provider_execution_id_for_task,
    task_usage_for_task,
)

_MAX_ARTIFACT_BYTES = 65_536
_MAX_RECEIPT_BYTES = 65_536
_BENCHMARK_AGENT_KEY = "aico.benchmark_agent_id"


class AicoBenchmarkRoleTarget(FrozenModel):
    role: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,31}$")
    agent_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,63}$")
    assignment_seat: str = Field(min_length=1, max_length=128)
    target_persona: str = Field(min_length=1, max_length=128)


class TaskBusAicoBenchmarkRuntime:
    """Run one bounded role turn through the real TaskBus and Adapter contracts."""

    def __init__(
        self,
        *,
        task_bus: TaskBus,
        project_directory: ProjectAssignmentDirectory,
        project_id: str,
        role_targets: tuple[AicoBenchmarkRoleTarget, ...],
        runtime_build: str,
        runtime_instance_sha256: str,
        artifact_dir: Path,
        receipt_dir: Path,
        expires_at: datetime,
        max_duration_seconds: float,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        if not artifact_dir.is_absolute() or not receipt_dir.is_absolute():
            raise ValueError("AICO benchmark runtime directories must be absolute")
        if len({item.role for item in role_targets}) != len(role_targets):
            raise ValueError("AICO benchmark runtime roles must be unique")
        if len({item.agent_id for item in role_targets}) != len(role_targets):
            raise ValueError("AICO benchmark runtime agents must be distinct")
        if len(runtime_instance_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in runtime_instance_sha256
        ):
            raise ValueError("AICO benchmark runtime instance SHA is invalid")
        if expires_at.tzinfo is None or expires_at.utcoffset() is None:
            raise ValueError("AICO benchmark runtime expiry must be timezone-aware")
        if max_duration_seconds <= 0:
            raise ValueError("AICO benchmark runtime duration must be positive")
        self._task_bus = task_bus
        self._project_directory = project_directory
        self._project_id = project_id
        self._targets = {item.role: item for item in role_targets}
        self._runtime_build = runtime_build
        self._runtime_instance_sha256 = runtime_instance_sha256
        self._artifacts = _OwnerFileDirectory(artifact_dir, _MAX_ARTIFACT_BYTES)
        self._receipts = _OwnerFileDirectory(receipt_dir, _MAX_RECEIPT_BYTES)
        self._expires_at = expires_at
        self._max_duration_seconds = max_duration_seconds
        self._clock = clock
        if self._project_directory.project(project_id) is None:
            raise ValueError("AICO benchmark runtime project is unknown")
        for target in role_targets:
            self._validate_target(target)

    def capabilities(
        self,
        *,
        model: str,
        reasoning_effort: str,
    ) -> AicoBenchmarkRuntimeCapabilities:
        return AicoBenchmarkRuntimeCapabilities(
            runtime_build=self._runtime_build,
            model=model,
            reasoning_effort=reasoning_effort,
            isolated_run_state=True,
            managed_role_orchestration=True,
            hard_remaining_token_cap=True,
            provider_usage_observable=True,
            durable_dispatch_reconciliation=True,
        )

    def preflight_role(self, request: AicoRoleRequest) -> str | None:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            return "AICO benchmark runtime clock must be timezone-aware"
        if self._expires_at <= now:
            return "AICO benchmark runtime authorization expired"
        try:
            task = self._task(request)
        except (OSError, UnicodeError, ValueError) as exc:
            return str(exc)
        return self._task_bus.preauthorized_refusal(task)

    async def execute_role(self, request: AicoRoleRequest) -> AicoRoleObservation:
        recovered = await self.recover_role(request.dispatch_id)
        if recovered is not None:
            return recovered
        refusal = self.preflight_role(request)
        if refusal is not None:
            raise ValueError(f"AICO benchmark role preflight refused: {refusal}")
        task = self._task(request)
        ack = await self._task_bus.submit(task)
        if ack.status is not AckStatus.ACCEPTED:
            raise ValueError(f"AICO benchmark role dispatch was not accepted: {ack.status.value}")
        try:
            output = await self._collect_output(task)
        except BaseException:
            try:
                await self._task_bus.interrupt(task.task_id)
            except Exception:
                pass
            raise
        usage = task_usage_for_task(self._task_bus, task.task_id)
        provider_execution_id = provider_execution_id_for_task(self._task_bus, task.task_id)
        snapshot = self._task_bus.task_snapshot(task.task_id)
        if usage is None:
            raise ValueError("AICO benchmark role provider usage is missing")
        if provider_execution_id is None:
            raise ValueError("AICO benchmark role provider execution identity is missing")
        if not isinstance(snapshot, TaskSnapshot) or snapshot.status is not TaskStatus.DONE:
            raise ValueError("AICO benchmark role did not reach done")
        artifact_sha = self._artifacts.write_content(output.encode("utf-8"))
        target = self._target(request.role)
        observation = AicoRoleObservation(
            dispatch_id=request.dispatch_id,
            role=request.role,
            agent_id=target.agent_id,
            assignment_sha256=canonical_sha256(self._assignment(target)),
            provider_execution_sha256=hashlib.sha256(
                provider_execution_id.encode("utf-8")
            ).hexdigest(),
            runtime_instance_sha256=self._runtime_instance_sha256,
            input_fixture_sha256=hashlib.sha256(request.fixture.encode("utf-8")).hexdigest(),
            artifact_sha256=artifact_sha,
            consumed_checkpoint_sha256=request.prior_checkpoint_sha256,
            status=AicoRoleStatus.COMPLETE,
            usage=usage,
        )
        self._receipts.write_named(
            f"{request.dispatch_id}.json",
            observation.model_dump_json(indent=2).encode("utf-8") + b"\n",
        )
        return observation

    async def recover_role(self, dispatch_id: str) -> AicoRoleObservation | None:
        payload = self._receipts.read_named(f"{dispatch_id}.json")
        if payload is None:
            return None
        try:
            observation = AicoRoleObservation.model_validate_json(payload)
        except ValueError:
            raise ValueError("AICO benchmark role receipt is invalid") from None
        target = self._target(observation.role)
        if (
            observation.agent_id != target.agent_id
            or observation.assignment_sha256 != canonical_sha256(self._assignment(target))
        ):
            raise ValueError("AICO benchmark recovered role assignment drifted")
        return observation

    def _task(self, request: AicoRoleRequest) -> Task:
        target = self._target(request.role)
        prior = self._prior_artifact(request)
        task = Task(
            task_id=request.dispatch_id,
            payload=_role_prompt(request, prior),
            requester_id="boss-absent-benchmark-harness",
            target_persona=target.target_persona,
            metadata=(MetadataEntry(key=_BENCHMARK_AGENT_KEY, value=target.agent_id),),
            trace_id=f"benchmark-{request.task_id}",
        )
        project = self._project_directory.project(self._project_id)
        assert project is not None
        task = task_with_assignment_context(
            task,
            project=project,
            assignment=self._assignment(target),
        )
        task = task_with_exact_output_constraint(task)
        return task_with_preauthorized_execution(
            task,
            grant_id=f"benchmark-{request.dispatch_id[:24]}",
            expires_at=self._expires_at,
            max_duration_seconds=self._max_duration_seconds,
            max_total_tokens=request.remaining_tokens,
            model=request.model,
            reasoning_effort=request.reasoning_effort,
        )

    def _prior_artifact(self, request: AicoRoleRequest) -> str | None:
        if request.prior_checkpoint_sha256 is None:
            return None
        payload = self._artifacts.read_named(f"{request.prior_checkpoint_sha256}.txt")
        if payload is None or hashlib.sha256(payload).hexdigest() != (
            request.prior_checkpoint_sha256
        ):
            raise ValueError("AICO benchmark prior role artifact is unavailable")
        try:
            return payload.decode("utf-8")
        except UnicodeError:
            raise ValueError("AICO benchmark prior role artifact is not UTF-8") from None

    def _target(self, role: str) -> AicoBenchmarkRoleTarget:
        target = self._targets.get(role)
        if target is None:
            raise ValueError("AICO benchmark role is not mapped to an Agent")
        return target

    def _assignment(self, target: AicoBenchmarkRoleTarget) -> AssignmentProfile:
        assignment = self._project_directory.assignment(target.assignment_seat)
        if assignment is None:
            raise ValueError("AICO benchmark role assignment disappeared")
        return assignment

    def _validate_target(self, target: AicoBenchmarkRoleTarget) -> None:
        assignment = self._assignment(target)
        agent = self._project_directory.agent(assignment.agent)
        identity = (
            assignment.project == self._project_id
            and assignment.role == target.role
            and assignment.agent == target.agent_id
            and agent is not None
            and agent.provider == target.target_persona
        )
        if not identity:
            raise ValueError("AICO benchmark role target drifted from project assignment")

    async def _collect_output(self, task: Task) -> str:
        captured: list[str] = []
        captured_bytes = 0
        async with asyncio.timeout(self._max_duration_seconds):
            async for output in self._task_bus.stream_output(task.task_id):
                if output.type in {OutputType.TEXT, OutputType.DONE} and output.content:
                    encoded = output.content.encode("utf-8")
                    captured_bytes += len(encoded)
                    if captured_bytes > _MAX_ARTIFACT_BYTES:
                        raise ValueError("AICO benchmark role artifact exceeds bounded size")
                    captured.append(output.content)
                if output.type is OutputType.ERROR:
                    raise ValueError("AICO benchmark role Adapter returned an error")
        text = "".join(captured).strip()
        if not text:
            raise ValueError("AICO benchmark role artifact is empty")
        return text


def _role_prompt(request: AicoRoleRequest, prior: str | None) -> str:
    acceptance = "\n".join(f"- {item}" for item in request.acceptance)
    prior_text = "(none; this is the first role)" if prior is None else prior
    return (
        "AICO managed benchmark role turn.\n"
        f"Task: {request.task_id}\n"
        f"Role: {request.role}\n"
        f"Objective: {request.objective}\n\n"
        f"Frozen fixture:\n{request.fixture}\n\n"
        f"Acceptance:\n{acceptance}\n\n"
        "Prior role artifact:\n"
        f"{prior_text}\n\n"
        "Operate read-only. Do not mutate files, call tools, delegate, or request collaboration. "
        "Inspect only the supplied text. Produce one bounded JSON artifact for the next role or "
        "independent terminal harness."
    )


class _OwnerFileDirectory:
    def __init__(self, path: Path, max_bytes: int) -> None:
        self._path = path
        self._max_bytes = max_bytes

    def write_content(self, payload: bytes) -> str:
        digest = hashlib.sha256(payload).hexdigest()
        self.write_named(f"{digest}.txt", payload)
        return digest

    def write_named(self, name: str, payload: bytes) -> None:
        if len(payload) > self._max_bytes:
            raise ValueError("AICO benchmark runtime artifact exceeds bounded size")
        self._path.mkdir(mode=0o700, parents=True, exist_ok=True)
        target = self._safe_path(name)
        if target.exists() or target.is_symlink():
            existing = self.read_named(name)
            if existing != payload:
                raise ValueError("AICO benchmark runtime artifact identity collision")
            return
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            _fsync_directory(self._path)
        except BaseException:
            if target.exists() and target.stat().st_size == 0:
                target.unlink()
            raise

    def read_named(self, name: str) -> bytes | None:
        target = self._safe_path(name)
        if target.is_symlink():
            raise ValueError("AICO benchmark runtime artifact is unsafe")
        if not target.exists():
            return None
        info = target.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or info.st_size > self._max_bytes
        ):
            raise ValueError("AICO benchmark runtime artifact is unsafe")
        return target.read_bytes()

    def _safe_path(self, name: str) -> Path:
        if not name or "/" in name or name in {".", ".."}:
            raise ValueError("AICO benchmark runtime artifact name is invalid")
        return self._path / name


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
