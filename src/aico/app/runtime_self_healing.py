"""Bounded recovery for background tasks owned by the local runtime."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

log = logging.getLogger(__name__)


class RecoveryStatus(StrEnum):
    HEALTHY = "healthy"
    RECOVERING = "recovering"
    OPEN = "open"


@dataclass(frozen=True)
class OwnedTaskRecovery:
    name: str
    is_alive: Callable[[], bool]
    restart: Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class OwnedTaskRecoveryHealth:
    name: str
    status: RecoveryStatus
    attempts: int

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status.value,
            "attempts": self.attempts,
        }


@dataclass(frozen=True)
class RuntimeSelfHealingSnapshot:
    status: RecoveryStatus
    checked_at: datetime
    components: tuple[OwnedTaskRecoveryHealth, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
            "components": [component.to_payload() for component in self.components],
        }


@dataclass
class _RecoveryState:
    attempts: int = 0
    stabilizing_since: datetime | None = None
    circuit_until: datetime | None = None


class BoundedOwnedTaskSupervisor:
    """Restart dead owned tasks with stabilization and cooldown bounds."""

    def __init__(
        self,
        tasks: Iterable[OwnedTaskRecovery],
        *,
        max_attempts: int = 3,
        stabilization_seconds: float = 60,
        cooldown_seconds: float = 900,
        restart_timeout_seconds: float = 5,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        recoveries = tuple(tasks)
        names = tuple(recovery.name for recovery in recoveries)
        if len(names) != len(set(names)):
            raise ValueError("owned task recovery names must be unique")
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if stabilization_seconds <= 0:
            raise ValueError("stabilization_seconds must be positive")
        if cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be positive")
        if restart_timeout_seconds <= 0:
            raise ValueError("restart_timeout_seconds must be positive")
        self._recoveries = recoveries
        self._max_attempts = max_attempts
        self._stabilization = timedelta(seconds=stabilization_seconds)
        self._cooldown = timedelta(seconds=cooldown_seconds)
        self._restart_timeout_seconds = restart_timeout_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self._states = {recovery.name: _RecoveryState() for recovery in recoveries}

    async def check(self) -> RuntimeSelfHealingSnapshot:
        now = self._clock()
        components = tuple([await self._check_task(recovery, now) for recovery in self._recoveries])
        return RuntimeSelfHealingSnapshot(
            status=_aggregate_status(components),
            checked_at=now,
            components=components,
        )

    async def _check_task(
        self,
        recovery: OwnedTaskRecovery,
        now: datetime,
    ) -> OwnedTaskRecoveryHealth:
        state = self._states[recovery.name]
        if _is_alive(recovery):
            return _alive_health(recovery.name, state, now, self._stabilization)
        if state.circuit_until is not None and now < state.circuit_until:
            return _recovery_health(recovery.name, RecoveryStatus.OPEN, state)
        if state.circuit_until is not None:
            _reset_state(state)
        if state.attempts >= self._max_attempts:
            return self._open_circuit(recovery.name, state, now)
        state.attempts += 1
        state.stabilizing_since = now
        try:
            await asyncio.wait_for(
                recovery.restart(),
                timeout=self._restart_timeout_seconds,
            )
        except Exception as exc:
            log.error(
                "Owned task recovery failed: component=%s type=%s attempt=%s",
                recovery.name,
                type(exc).__name__,
                state.attempts,
            )
        if not _is_alive(recovery) and state.attempts >= self._max_attempts:
            return self._open_circuit(recovery.name, state, now)
        return _recovery_health(recovery.name, RecoveryStatus.RECOVERING, state)

    def _open_circuit(
        self,
        name: str,
        state: _RecoveryState,
        now: datetime,
    ) -> OwnedTaskRecoveryHealth:
        state.stabilizing_since = None
        state.circuit_until = now + self._cooldown
        log.error(
            "Owned task recovery circuit opened: component=%s attempts=%s",
            name,
            state.attempts,
        )
        return _recovery_health(name, RecoveryStatus.OPEN, state)


def _is_alive(recovery: OwnedTaskRecovery) -> bool:
    try:
        return recovery.is_alive()
    except Exception as exc:
        log.error(
            "Owned task liveness check failed: component=%s type=%s",
            recovery.name,
            type(exc).__name__,
        )
        return False


def _alive_health(
    name: str,
    state: _RecoveryState,
    now: datetime,
    stabilization: timedelta,
) -> OwnedTaskRecoveryHealth:
    if state.stabilizing_since is None:
        _reset_state(state)
        return _recovery_health(name, RecoveryStatus.HEALTHY, state)
    if now - state.stabilizing_since >= stabilization:
        _reset_state(state)
        return _recovery_health(name, RecoveryStatus.HEALTHY, state)
    return _recovery_health(name, RecoveryStatus.RECOVERING, state)


def _reset_state(state: _RecoveryState) -> None:
    state.attempts = 0
    state.stabilizing_since = None
    state.circuit_until = None


def _recovery_health(
    name: str,
    status: RecoveryStatus,
    state: _RecoveryState,
) -> OwnedTaskRecoveryHealth:
    return OwnedTaskRecoveryHealth(name=name, status=status, attempts=state.attempts)


def _aggregate_status(
    components: tuple[OwnedTaskRecoveryHealth, ...],
) -> RecoveryStatus:
    if any(component.status is RecoveryStatus.OPEN for component in components):
        return RecoveryStatus.OPEN
    if any(component.status is RecoveryStatus.RECOVERING for component in components):
        return RecoveryStatus.RECOVERING
    return RecoveryStatus.HEALTHY
