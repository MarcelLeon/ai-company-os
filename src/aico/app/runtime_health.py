"""Secret-free component health aggregation for the local AICO runtime."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from aico.channel import IMChannel
from aico.core.adapter_registry import AdapterRegistry
from aico.core.models import HealthStatus

ComponentKind = Literal["channel", "adapter", "scheduler", "configuration"]


class _HealthCheckable(Protocol):
    async def health_check(self) -> HealthStatus: ...


@dataclass(frozen=True)
class RuntimeComponentHealth:
    kind: ComponentKind
    name: str
    required: bool
    status: HealthStatus

    def to_payload(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "name": self.name,
            "required": self.required,
            "status": self.status.value,
        }


@dataclass(frozen=True)
class RuntimeHealthSnapshot:
    status: HealthStatus
    checked_at: datetime
    components: tuple[RuntimeComponentHealth, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
            "components": [component.to_payload() for component in self.components],
        }

    def failed_component_names(self) -> tuple[str, ...]:
        return tuple(
            f"{component.kind}:{component.name}"
            for component in self.components
            if component.status is HealthStatus.FAILED
        )


class RuntimeHealthProbe:
    """Check runtime plugins concurrently without persisting failure details."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        registry: AdapterRegistry,
        morning_scheduler: _HealthCheckable | None = None,
        recovery_backup_scheduler: _HealthCheckable | None = None,
        configuration: _HealthCheckable | None = None,
        commissioning: _HealthCheckable | None = None,
        timeout_seconds: float = 5,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._channel = channel
        self._registry = registry
        self._morning_scheduler = morning_scheduler
        self._recovery_backup_scheduler = recovery_backup_scheduler
        self._configuration = configuration
        self._commissioning = commissioning
        self._timeout_seconds = timeout_seconds
        self._clock = clock or (lambda: datetime.now(UTC))

    async def check(self) -> RuntimeHealthSnapshot:
        default_adapter = self._registry.default()
        components: list[tuple[ComponentKind, str, bool, _HealthCheckable]] = [
            ("channel", self._channel.name, True, self._channel),
        ]
        components.extend(
            (
                "adapter",
                adapter.name,
                adapter is default_adapter,
                adapter,
            )
            for adapter in self._registry.adapters()
        )
        if self._morning_scheduler is not None:
            components.append(("scheduler", "morning-push", True, self._morning_scheduler))
        if self._recovery_backup_scheduler is not None:
            components.append(
                ("scheduler", "recovery-backup", True, self._recovery_backup_scheduler)
            )
        if self._configuration is not None:
            components.append(("configuration", "dotenv-generation", True, self._configuration))
        if self._commissioning is not None:
            components.append(("configuration", "commissioning-receipt", True, self._commissioning))
        checked = await asyncio.gather(
            *(self._check_component(*component) for component in components)
        )
        return RuntimeHealthSnapshot(
            status=_aggregate_health(tuple(checked)),
            checked_at=self._clock(),
            components=tuple(checked),
        )

    async def _check_component(
        self,
        kind: ComponentKind,
        name: str,
        required: bool,
        component: _HealthCheckable,
    ) -> RuntimeComponentHealth:
        try:
            status = await asyncio.wait_for(component.health_check(), timeout=self._timeout_seconds)
        except Exception:
            status = HealthStatus.FAILED
        if not isinstance(status, HealthStatus):
            status = HealthStatus.FAILED
        return RuntimeComponentHealth(
            kind=kind,
            name=name,
            required=required,
            status=status,
        )


def _aggregate_health(
    components: tuple[RuntimeComponentHealth, ...],
) -> HealthStatus:
    if any(
        component.required and component.status is HealthStatus.FAILED for component in components
    ):
        return HealthStatus.FAILED
    if any(component.status is not HealthStatus.OK for component in components):
        return HealthStatus.DEGRADED
    return HealthStatus.OK
