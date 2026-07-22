from datetime import UTC, datetime, timedelta
from pathlib import Path

from aico.core.authorization_clock import (
    AUTHORIZATION_CLOCK_ROLLBACK_REASON,
    AuthorizationClockGuard,
    InMemoryAuthorizationClockStore,
)
from aico.core.sqlite_state import SQLiteStateDatabase


def test_authorization_clock_uses_monotonic_elapsed_time_and_recovers_after_catchup() -> None:
    wall = [datetime(2026, 7, 22, 8, tzinfo=UTC)]
    steady = [100.0]
    guard = AuthorizationClockGuard(
        InMemoryAuthorizationClockStore(),
        clock=lambda: wall[0],
        monotonic_clock=lambda: steady[0],
    )

    assert guard.refusal() is None

    wall[0] += timedelta(seconds=1)
    steady[0] += 10
    rolled_back = guard.observe()

    assert rolled_back.rolled_back
    assert rolled_back.high_water_at == datetime(2026, 7, 22, 8, 0, 10, tzinfo=UTC)
    assert guard.refusal() == AUTHORIZATION_CLOCK_ROLLBACK_REASON

    wall[0] = datetime(2026, 7, 22, 8, 0, 20, tzinfo=UTC)
    steady[0] = 120.0
    assert guard.refusal() is None


def test_authorization_clock_persists_high_water_across_restart(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    high_water = datetime(2026, 7, 22, 8, tzinfo=UTC)
    first = SQLiteStateDatabase(path)

    seeded = first.observe_authorization_time(
        high_water,
        minimum_expected_at=high_water,
        rollback_tolerance_seconds=5,
    )
    restarted = SQLiteStateDatabase(path).observe_authorization_time(
        high_water - timedelta(seconds=60),
        minimum_expected_at=high_water - timedelta(seconds=60),
        rollback_tolerance_seconds=5,
    )

    assert not seeded.rolled_back
    assert restarted.rolled_back
    assert restarted.high_water_at == high_water
    assert SQLiteStateDatabase(path).table_counts()["authorization_clock_state"] == 1


def test_authorization_clock_tolerates_small_wall_clock_correction() -> None:
    wall = [datetime(2026, 7, 22, 8, tzinfo=UTC)]
    steady = [0.0]
    guard = AuthorizationClockGuard(
        clock=lambda: wall[0],
        monotonic_clock=lambda: steady[0],
    )

    assert guard.refusal() is None
    wall[0] -= timedelta(seconds=5)

    assert guard.refusal() is None

    steady[0] += 1
    assert guard.refusal() == AUTHORIZATION_CLOCK_ROLLBACK_REASON
