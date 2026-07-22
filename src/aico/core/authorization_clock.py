"""Fail-closed time boundary for persisted authorization windows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from time import monotonic
from typing import Protocol

from aico.core.models import utc_now

AUTHORIZATION_CLOCK_ROLLBACK_REASON = (
    "authorization clock rollback detected; submit risky work after wall time "
    "catches up for fresh authorization"
)
AUTHORIZATION_CLOCK_ROLLBACK_TOLERANCE_SECONDS = 5


@dataclass(frozen=True)
class AuthorizationClockObservation:
    """Result of atomically advancing and checking an authorization time floor."""

    observed_at: datetime
    high_water_at: datetime
    rolled_back: bool


class AuthorizationClockStore(Protocol):
    """Persist the greatest authorization time the runtime has trusted."""

    def observe_authorization_time(
        self,
        now: datetime,
        *,
        minimum_expected_at: datetime,
        rollback_tolerance_seconds: int,
    ) -> AuthorizationClockObservation: ...


class InMemoryAuthorizationClockStore:
    """Process-local authorization clock state for embedded runtimes and tests."""

    def __init__(self) -> None:
        self._high_water_at: datetime | None = None
        self._lock = Lock()

    def observe_authorization_time(
        self,
        now: datetime,
        *,
        minimum_expected_at: datetime,
        rollback_tolerance_seconds: int,
    ) -> AuthorizationClockObservation:
        _require_aware(now)
        _require_aware(minimum_expected_at)
        with self._lock:
            high_water = max(
                value
                for value in (self._high_water_at, now, minimum_expected_at)
                if value is not None
            )
            self._high_water_at = high_water
        return _observation(now, high_water, rollback_tolerance_seconds)


class AuthorizationClockGuard:
    """Combine a durable wall-clock floor with same-process monotonic elapsed time."""

    def __init__(
        self,
        store: AuthorizationClockStore | None = None,
        *,
        clock: Callable[[], datetime] = utc_now,
        monotonic_clock: Callable[[], float] = monotonic,
        rollback_tolerance_seconds: int = AUTHORIZATION_CLOCK_ROLLBACK_TOLERANCE_SECONDS,
    ) -> None:
        if rollback_tolerance_seconds < 0:
            raise ValueError("authorization clock rollback tolerance must be non-negative")
        self._store = store or InMemoryAuthorizationClockStore()
        self._clock = clock
        self._monotonic_clock = monotonic_clock
        self._rollback_tolerance_seconds = rollback_tolerance_seconds
        self._baseline_wall: datetime | None = None
        self._baseline_monotonic: float | None = None

    def observe(self) -> AuthorizationClockObservation:
        now = self._clock()
        monotonic_now = self._monotonic_clock()
        _require_aware(now)
        minimum_expected = self._minimum_expected(now, monotonic_now)
        observation = self._store.observe_authorization_time(
            now,
            minimum_expected_at=minimum_expected,
            rollback_tolerance_seconds=self._rollback_tolerance_seconds,
        )
        if not observation.rolled_back:
            self._baseline_wall = observation.high_water_at
            self._baseline_monotonic = monotonic_now
        return observation

    def refusal(self) -> str | None:
        observation = self.observe()
        if observation.rolled_back:
            return AUTHORIZATION_CLOCK_ROLLBACK_REASON
        return None

    def _minimum_expected(self, now: datetime, monotonic_now: float) -> datetime:
        if self._baseline_wall is None or self._baseline_monotonic is None:
            return now
        elapsed = max(0.0, monotonic_now - self._baseline_monotonic)
        return self._baseline_wall + timedelta(seconds=elapsed)


def _observation(
    now: datetime,
    high_water: datetime,
    rollback_tolerance_seconds: int,
) -> AuthorizationClockObservation:
    tolerance = timedelta(seconds=rollback_tolerance_seconds)
    return AuthorizationClockObservation(
        observed_at=now,
        high_water_at=high_water,
        rolled_back=now + tolerance < high_water,
    )


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("authorization clock timestamps must be timezone-aware")
