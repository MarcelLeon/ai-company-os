from collections.abc import AsyncIterator

import pytest

from aico.core import (
    AckStatus,
    AdapterRegistry,
    AdapterStatus,
    Capability,
    HealthStatus,
    OutputType,
    Task,
    TaskAck,
    TaskOutput,
)


class NamedAdapter:
    def __init__(self, name: str, status: AdapterStatus = AdapterStatus.IDLE) -> None:
        self._name = name
        self._status = status

    @property
    def name(self) -> str:
        return self._name

    def capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.STREAM_OUTPUT})

    async def receive_task(self, task: Task) -> TaskAck:
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    async def _outputs(self, task_id: str) -> AsyncIterator[TaskOutput]:
        yield TaskOutput(task_id=task_id, sequence=0, type=OutputType.TEXT, content=self.name)

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        return self._outputs(task_id)

    def status(self) -> AdapterStatus:
        return self._status

    async def interrupt(self, task_id: str) -> None:
        _ = task_id

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


def test_adapter_registry_resolves_by_name_and_telegram_safe_alias() -> None:
    claude = NamedAdapter("claude-code")
    codex = NamedAdapter("codex")
    registry = AdapterRegistry([claude, codex])

    assert registry.resolve("claude-code") is claude
    assert registry.resolve("claude_code") is claude
    assert registry.resolve("codex") is codex
    assert registry.resolve("missing") is None


def test_adapter_registry_rejects_empty_or_invalid_default() -> None:
    with pytest.raises(ValueError, match="at least one adapter"):
        AdapterRegistry([])

    with pytest.raises(ValueError, match="default_adapter_name"):
        AdapterRegistry([NamedAdapter("claude-code")], default_adapter_name="missing")


def test_adapter_registry_builds_status_snapshots() -> None:
    registry = AdapterRegistry(
        [
            NamedAdapter("claude-code", AdapterStatus.BUSY),
            NamedAdapter("codex", AdapterStatus.IDLE),
        ]
    )

    snapshots = registry.snapshots()

    assert [snapshot.name for snapshot in snapshots] == ["claude-code", "codex"]
    assert snapshots[0].status is AdapterStatus.BUSY
    assert snapshots[0].capabilities == (Capability.STREAM_OUTPUT,)
    assert snapshots[0].running_tasks == 1
    assert snapshots[0].max_concurrent_tasks == 1


def test_adapter_registry_supports_explicit_aliases() -> None:
    claude = NamedAdapter("claude-code")
    registry = AdapterRegistry([claude], aliases={"claude": "claude-code"})

    assert registry.resolve("claude") is claude


def test_adapter_registry_rejects_alias_for_missing_adapter() -> None:
    with pytest.raises(ValueError, match="aliases"):
        AdapterRegistry([NamedAdapter("claude-code")], aliases={"claude": "missing"})
