from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

import aico.app.phase1 as phase1_app
from aico.adapter.claude_code import ClaudeCodeAdapter
from aico.app.morning_scheduler import MorningPushScheduler
from aico.app.phase1 import Phase1Runtime, Phase1Settings
from aico.app.recovery_backup_scheduler import RecoveryBackupScheduler
from aico.app.runtime_owner import RuntimeOwnerLock, RuntimeOwnershipError
from aico.channel import IMChannel
from aico.core import (
    AdapterRegistry,
    InMemoryAgentSessionStore,
    Orchestrator,
    PersonaRegistry,
    ProjectAssignmentDirectory,
    SQLiteTaskStateStore,
    Task,
    TaskBus,
    TaskSnapshot,
    TaskStatus,
)


class LifecycleChannel:
    def __init__(self, *, fail_start: bool = False) -> None:
        self.started = 0
        self.stopped = 0
        self.fail_start = fail_start

    async def start(self) -> None:
        self.started += 1
        if self.fail_start:
            raise RuntimeError("channel failed")

    async def stop(self) -> None:
        self.stopped += 1


class LifecycleScheduler:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    def start(self) -> None:
        self.started += 1

    async def stop(self) -> None:
        self.stopped += 1


class LifecycleOrchestrator:
    def __init__(self) -> None:
        self.bound = 0

    def bind(self) -> None:
        self.bound += 1


async def test_phase1_runtime_keeps_morning_scheduler_alive_until_stop() -> None:
    channel = LifecycleChannel()
    scheduler = LifecycleScheduler()
    orchestrator = LifecycleOrchestrator()
    runtime = Phase1Runtime(
        channel=cast(IMChannel, channel),
        adapter=cast(ClaudeCodeAdapter, object()),
        registry=cast(AdapterRegistry, object()),
        persona_registry=cast(PersonaRegistry, object()),
        session_store=InMemoryAgentSessionStore(),
        project_directory=ProjectAssignmentDirectory(),
        orchestrator=cast(Orchestrator, orchestrator),
        morning_scheduler=cast(MorningPushScheduler, scheduler),
    )

    await runtime.start()

    assert channel.started == 1
    assert orchestrator.bound == 1
    assert scheduler.started == 1
    assert scheduler.stopped == 0

    await runtime.stop()

    assert channel.stopped == 1
    assert scheduler.stopped == 1


async def test_phase1_runtime_owns_recovery_backup_scheduler_lifecycle() -> None:
    channel = LifecycleChannel()
    scheduler = LifecycleScheduler()
    runtime = Phase1Runtime(
        channel=cast(IMChannel, channel),
        adapter=cast(ClaudeCodeAdapter, object()),
        registry=cast(AdapterRegistry, object()),
        persona_registry=cast(PersonaRegistry, object()),
        session_store=InMemoryAgentSessionStore(),
        project_directory=ProjectAssignmentDirectory(),
        orchestrator=cast(Orchestrator, LifecycleOrchestrator()),
        recovery_backup_scheduler=cast(RecoveryBackupScheduler, scheduler),
    )

    await runtime.start()
    await runtime.stop()

    assert scheduler.started == 1
    assert scheduler.stopped == 1
    assert channel.started == 1
    assert channel.stopped == 1


async def test_phase1_runtime_stops_scheduler_and_releases_owner_when_channel_start_fails(
    tmp_path: Path,
) -> None:
    channel = LifecycleChannel(fail_start=True)
    scheduler = LifecycleScheduler()
    owner_path = tmp_path / "runtime-owner.lock"
    runtime = Phase1Runtime(
        channel=cast(IMChannel, channel),
        adapter=cast(ClaudeCodeAdapter, object()),
        registry=cast(AdapterRegistry, object()),
        persona_registry=cast(PersonaRegistry, object()),
        session_store=InMemoryAgentSessionStore(),
        project_directory=ProjectAssignmentDirectory(),
        orchestrator=cast(Orchestrator, LifecycleOrchestrator()),
        morning_scheduler=cast(MorningPushScheduler, scheduler),
        owner_lock=RuntimeOwnerLock(owner_path, resource_path=tmp_path / "state.db"),
    )

    with pytest.raises(RuntimeError, match="channel failed"):
        await runtime.start()

    assert scheduler.started == 1
    assert scheduler.stopped == 1
    replacement = RuntimeOwnerLock(owner_path, resource_path=tmp_path / "state.db")
    replacement.acquire()
    replacement.release()


async def test_run_phase1_starts_health_heartbeat_after_runtime_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class Runtime:
        async def start(self) -> None:
            events.append("runtime-start")

        async def stop(self) -> None:
            events.append("runtime-stop")

    class Heartbeat:
        async def start(self) -> None:
            events.append("heartbeat-start")

        async def stop(self) -> None:
            events.append("heartbeat-stop")

    runtime = Runtime()
    heartbeat = Heartbeat()

    def build_heartbeat(settings: object, built_runtime: object) -> Heartbeat:
        _ = settings
        assert built_runtime is runtime
        events.append("heartbeat-build")
        return heartbeat

    async def wait_once() -> None:
        events.append("wait")

    monkeypatch.setattr(phase1_app, "build_phase1_runtime", lambda settings: runtime)
    monkeypatch.setattr(
        phase1_app,
        "_runtime_heartbeat",
        build_heartbeat,
    )
    monkeypatch.setattr(phase1_app, "_wait_forever", wait_once)

    await phase1_app.run_phase1(Phase1Settings(telegram_bot_token="token", log_path=None))

    assert events == [
        "runtime-start",
        "heartbeat-build",
        "heartbeat-start",
        "wait",
        "heartbeat-stop",
        "runtime-stop",
    ]


async def test_phase1_runtime_acquires_owner_before_recovery_and_releases_last() -> None:
    events: list[str] = []

    class Owner:
        def acquire(self) -> None:
            events.append("owner-acquire")

        def release(self) -> None:
            events.append("owner-release")

    class Recovery:
        def recover_startup_state(self) -> None:
            events.append("task-recovery")

    class Channel:
        async def start(self) -> None:
            events.append("channel-start")

        async def stop(self) -> None:
            events.append("channel-stop")

    runtime = Phase1Runtime(
        channel=cast(IMChannel, Channel()),
        adapter=cast(ClaudeCodeAdapter, object()),
        registry=cast(AdapterRegistry, object()),
        persona_registry=cast(PersonaRegistry, object()),
        session_store=InMemoryAgentSessionStore(),
        project_directory=ProjectAssignmentDirectory(),
        orchestrator=cast(Orchestrator, LifecycleOrchestrator()),
        task_bus=cast(TaskBus, Recovery()),
        owner_lock=cast(RuntimeOwnerLock, Owner()),
    )

    await runtime.start()
    await runtime.stop()

    assert events == [
        "owner-acquire",
        "task-recovery",
        "channel-start",
        "channel-stop",
        "owner-release",
    ]


async def test_competing_runtime_cannot_reconcile_live_task(tmp_path: Path) -> None:
    lock_path = tmp_path / "state.db.owner.lock"
    first_runtime = Phase1Runtime(
        channel=cast(IMChannel, LifecycleChannel()),
        adapter=cast(ClaudeCodeAdapter, object()),
        registry=cast(AdapterRegistry, object()),
        persona_registry=cast(PersonaRegistry, object()),
        session_store=InMemoryAgentSessionStore(),
        project_directory=ProjectAssignmentDirectory(),
        orchestrator=cast(Orchestrator, LifecycleOrchestrator()),
        owner_lock=RuntimeOwnerLock(lock_path, resource_path=tmp_path / "state.db"),
    )
    await first_runtime.start()

    store = SQLiteTaskStateStore(tmp_path / "state.db")
    task = Task(
        task_id="task-live-owner",
        payload="do work",
        requester_id="boss",
        target_persona="default",
    )
    store.upsert_task_record(task)
    store.upsert_task_snapshot(
        TaskSnapshot(
            task_id=task.task_id,
            target_persona=task.target_persona,
            status=TaskStatus.RUNNING,
            created_at=task.created_at,
        )
    )
    second_channel = LifecycleChannel()
    second_runtime = Phase1Runtime(
        channel=cast(IMChannel, second_channel),
        adapter=cast(ClaudeCodeAdapter, object()),
        registry=cast(AdapterRegistry, object()),
        persona_registry=cast(PersonaRegistry, object()),
        session_store=InMemoryAgentSessionStore(),
        project_directory=ProjectAssignmentDirectory(),
        orchestrator=cast(Orchestrator, LifecycleOrchestrator()),
        task_bus=TaskBus(ClaudeCodeAdapter(command=("true",)), task_store=store),
        owner_lock=RuntimeOwnerLock(lock_path, resource_path=tmp_path / "state.db"),
    )

    with pytest.raises(RuntimeOwnershipError, match="runtime owner already active"):
        await second_runtime.start()

    assert store.load_task_snapshots()[0].status is TaskStatus.RUNNING
    assert second_channel.started == 0

    await first_runtime.stop()
    await second_runtime.start()
    assert store.load_task_snapshots()[0].status is TaskStatus.INTERRUPTED
    await second_runtime.stop()
