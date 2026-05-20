"""Registry for resolving tasks to AI adapters."""

from __future__ import annotations

from collections.abc import Iterable

from aico.adapter import AIAdapter
from aico.core.models import AdapterSnapshot


class AdapterRegistry:
    """Keep adapter lookup and status snapshots out of the orchestrator."""

    def __init__(
        self,
        adapters: Iterable[AIAdapter],
        *,
        default_adapter_name: str | None = None,
        aliases: dict[str, str] | None = None,
    ) -> None:
        self._adapters = {adapter.name: adapter for adapter in adapters}
        if not self._adapters:
            raise ValueError("at least one adapter is required")

        self._aliases = {_normalize(name): name for name in self._adapters}
        for alias, adapter_name in (aliases or {}).items():
            if adapter_name not in self._adapters:
                raise ValueError("aliases must refer to registered adapters")
            self._aliases[_normalize(alias)] = adapter_name
        self._default_adapter_name = default_adapter_name or next(iter(self._adapters))
        if self._default_adapter_name not in self._adapters:
            raise ValueError("default_adapter_name must refer to a registered adapter")

    def default(self) -> AIAdapter:
        return self._adapters[self._default_adapter_name]

    def resolve(self, target_persona: str) -> AIAdapter | None:
        adapter_name = self._aliases.get(_normalize(target_persona))
        if adapter_name is None:
            return None
        return self._adapters[adapter_name]

    def get(self, adapter_name: str) -> AIAdapter | None:
        return self._adapters.get(adapter_name)

    def snapshots(self) -> tuple[AdapterSnapshot, ...]:
        return tuple(
            AdapterSnapshot(
                name=adapter.name,
                status=adapter.status(),
                capabilities=tuple(sorted(adapter.capabilities())),
                running_tasks=_adapter_running_tasks(adapter),
                max_concurrent_tasks=_adapter_max_concurrent_tasks(adapter),
            )
            for adapter in self._adapters.values()
        )


def _normalize(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def _adapter_running_tasks(adapter: AIAdapter) -> int:
    count = getattr(adapter, "running_task_count", None)
    if callable(count):
        value = count()
        if isinstance(value, int) and value >= 0:
            return value
    return 1 if adapter.status().value == "busy" else 0


def _adapter_max_concurrent_tasks(adapter: AIAdapter) -> int:
    max_tasks = getattr(adapter, "max_concurrent_tasks", None)
    if callable(max_tasks):
        value = max_tasks()
        if isinstance(value, int) and value > 0:
            return value
    return 1
