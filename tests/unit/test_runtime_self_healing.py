from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast

from aico.app.phase1 import Phase1Runtime, _owned_task_supervisor
from aico.app.runtime_self_healing import (
    BoundedOwnedTaskSupervisor,
    OwnedTaskRecovery,
    RecoveryStatus,
)


class RecoverableTask:
    def __init__(self, *, restart_succeeds: bool) -> None:
        self.alive = False
        self.restart_succeeds = restart_succeeds
        self.restart_count = 0

    def is_alive(self) -> bool:
        return self.alive

    async def restart(self) -> None:
        self.restart_count += 1
        self.alive = self.restart_succeeds


async def test_supervisor_requires_grace_period_before_recovery_is_stable() -> None:
    now = [datetime(2026, 7, 21, 14, tzinfo=UTC)]
    task = RecoverableTask(restart_succeeds=True)
    supervisor = BoundedOwnedTaskSupervisor(
        [OwnedTaskRecovery("channel:telegram-polling", task.is_alive, task.restart)],
        stabilization_seconds=60,
        clock=lambda: now[0],
    )

    first = await supervisor.check()
    now[0] += timedelta(seconds=59)
    stabilizing = await supervisor.check()
    now[0] += timedelta(seconds=1)
    stable = await supervisor.check()

    assert first.status is RecoveryStatus.RECOVERING
    assert first.components[0].attempts == 1
    assert stabilizing.status is RecoveryStatus.RECOVERING
    assert stable.status is RecoveryStatus.HEALTHY
    assert stable.components[0].attempts == 0
    assert task.restart_count == 1


async def test_supervisor_opens_circuit_after_bounded_failed_restarts() -> None:
    now = [datetime(2026, 7, 21, 14, tzinfo=UTC)]
    task = RecoverableTask(restart_succeeds=False)
    supervisor = BoundedOwnedTaskSupervisor(
        [OwnedTaskRecovery("scheduler:morning-push", task.is_alive, task.restart)],
        max_attempts=3,
        cooldown_seconds=900,
        clock=lambda: now[0],
    )

    assert (await supervisor.check()).status is RecoveryStatus.RECOVERING
    assert (await supervisor.check()).status is RecoveryStatus.RECOVERING
    opened = await supervisor.check()
    during_cooldown = await supervisor.check()
    now[0] += timedelta(seconds=900)
    retried = await supervisor.check()

    assert opened.status is RecoveryStatus.OPEN
    assert opened.components[0].attempts == 3
    assert during_cooldown.status is RecoveryStatus.OPEN
    assert task.restart_count == 4
    assert retried.status is RecoveryStatus.RECOVERING
    assert retried.components[0].attempts == 1


async def test_supervisor_clears_open_circuit_when_task_recovers_elsewhere() -> None:
    now = [datetime(2026, 7, 21, 14, tzinfo=UTC)]
    task = RecoverableTask(restart_succeeds=False)
    supervisor = BoundedOwnedTaskSupervisor(
        [OwnedTaskRecovery("scheduler:morning-push", task.is_alive, task.restart)],
        max_attempts=1,
        clock=lambda: now[0],
    )

    assert (await supervisor.check()).status is RecoveryStatus.OPEN
    task.alive = True

    recovered = await supervisor.check()

    assert recovered.status is RecoveryStatus.HEALTHY
    assert recovered.components[0].attempts == 0


async def test_supervisor_payload_never_contains_restart_exception_detail() -> None:
    now = datetime(2026, 7, 21, 14, tzinfo=UTC)

    async def explode() -> None:
        raise RuntimeError("secret recovery detail")

    supervisor = BoundedOwnedTaskSupervisor(
        [OwnedTaskRecovery("channel:telegram-polling", lambda: False, explode)],
        clock=lambda: now,
    )

    snapshot = await supervisor.check()

    assert "secret recovery detail" not in str(snapshot.to_payload())
    assert snapshot.components[0].attempts == 1


async def test_supervisor_bounds_a_hanging_restart_attempt() -> None:
    async def hang() -> None:
        await asyncio.Event().wait()

    supervisor = BoundedOwnedTaskSupervisor(
        [OwnedTaskRecovery("scheduler:morning-push", lambda: False, hang)],
        max_attempts=1,
        restart_timeout_seconds=0.001,
    )

    snapshot = await supervisor.check()

    assert snapshot.status is RecoveryStatus.OPEN
    assert snapshot.components[0].attempts == 1


async def test_runtime_supervisor_excludes_external_component_health_failures() -> None:
    class ExternalChannel:
        restart_count = 0

        def owned_task_alive(self) -> bool:
            return False

        async def restart_owned_task(self) -> None:
            self.restart_count += 1

    channel = ExternalChannel()
    runtime = cast(
        Phase1Runtime,
        SimpleNamespace(channel=channel, morning_scheduler=None),
    )

    snapshot = await _owned_task_supervisor(runtime).check()

    assert snapshot.status is RecoveryStatus.HEALTHY
    assert snapshot.components == ()
    assert channel.restart_count == 0


async def test_runtime_supervisor_restarts_owned_recovery_backup_task() -> None:
    task = RecoverableTask(restart_succeeds=True)
    scheduler = SimpleNamespace(
        owned_task_alive=task.is_alive,
        restart_owned_task=task.restart,
    )
    runtime = cast(
        Phase1Runtime,
        SimpleNamespace(
            channel=object(),
            morning_scheduler=None,
            recovery_backup_scheduler=scheduler,
        ),
    )

    snapshot = await _owned_task_supervisor(runtime).check()

    assert snapshot.status is RecoveryStatus.RECOVERING
    assert snapshot.components[0].name == "scheduler:recovery-backup"
    assert task.restart_count == 1
