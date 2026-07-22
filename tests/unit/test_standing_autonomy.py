import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.core import (
    AckStatus,
    AdapterStatus,
    AuditEventType,
    Capability,
    HealthStatus,
    MetadataEntry,
    OutputType,
    ProviderSessionMode,
    ProviderSessionRef,
    Task,
    TaskAck,
    TaskBus,
    TaskOutput,
    TaskUsage,
    task_with_provider_session,
)
from aico.core.authorization_clock import AUTHORIZATION_CLOCK_ROLLBACK_REASON
from aico.core.collaboration import task_with_exact_output_constraint
from aico.core.preauthorized_execution import (
    PREAUTHORIZED_MODE_KEY,
    PreauthorizedExecutionMode,
    task_with_preauthorized_execution,
)
from aico.core.standing_autonomy import (
    StandingAutonomyConfigError,
    StandingAutonomyGrant,
    StandingAutonomyGrantSet,
    load_standing_autonomy_grants,
)


class RecordingAdapter:
    def __init__(self, *, enforced: bool) -> None:
        self._enforced = enforced
        self.received_tasks: list[Task] = []

    @property
    def name(self) -> str:
        return "recording"

    def capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.CODE_REVIEW, Capability.STREAM_OUTPUT})

    def supports_preauthorized_execution(self, mode: str) -> bool:
        return self._enforced and mode == PreauthorizedExecutionMode.READ_ONLY.value

    async def receive_task(self, task: Task) -> TaskAck:
        self.received_tasks.append(task)
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    async def _outputs(self, task_id: str) -> AsyncIterator[TaskOutput]:
        yield TaskOutput(task_id=task_id, sequence=0, type=OutputType.DONE, content="")

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        return self._outputs(task_id)

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        del task_id

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK

    def task_usage(self, task_id: str) -> TaskUsage | None:
        _ = task_id
        return TaskUsage(input_tokens=80, output_tokens=20, total_tokens=100)


def test_load_standing_autonomy_grants_requires_external_owner_only_file(
    tmp_path: Path,
) -> None:
    grant_path = tmp_path / "standing-autonomy.json"
    _write_grants(grant_path)
    grant_path.chmod(0o600)

    loaded = load_standing_autonomy_grants(
        grant_path,
        forbidden_roots=(Path.cwd(),),
    )

    assert loaded == StandingAutonomyGrantSet(grants=(_grant(),))

    with pytest.raises(StandingAutonomyConfigError, match="absolute"):
        load_standing_autonomy_grants(Path("relative-grant.json"))


@pytest.mark.parametrize("mode", [0o640, 0o604, 0o666])
def test_load_standing_autonomy_grants_rejects_broad_permissions_without_path(
    tmp_path: Path,
    mode: int,
) -> None:
    grant_path = tmp_path / "private-owner-identifier.json"
    _write_grants(grant_path)
    grant_path.chmod(mode)

    with pytest.raises(StandingAutonomyConfigError) as caught:
        load_standing_autonomy_grants(grant_path)

    assert "owner-only" in str(caught.value)
    assert str(grant_path) not in str(caught.value)


def test_load_standing_autonomy_grants_rejects_symlink_repo_and_wrong_owner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grant_path = tmp_path / "grant.json"
    _write_grants(grant_path)
    grant_path.chmod(0o600)
    link = tmp_path / "grant-link.json"
    link.symlink_to(grant_path)

    with pytest.raises(StandingAutonomyConfigError, match="regular non-symlink"):
        load_standing_autonomy_grants(link)
    with pytest.raises(StandingAutonomyConfigError, match="outside managed repositories"):
        load_standing_autonomy_grants(grant_path, forbidden_roots=(tmp_path,))

    current_uid = os.getuid()
    monkeypatch.setattr("aico.core.standing_autonomy.os.getuid", lambda: current_uid + 1)
    with pytest.raises(StandingAutonomyConfigError, match="current user"):
        load_standing_autonomy_grants(grant_path)


def test_load_standing_autonomy_grants_rejects_malformed_duplicate_and_oversized(
    tmp_path: Path,
) -> None:
    grant_path = tmp_path / "grant.json"
    grant_path.write_text("not-json", encoding="utf-8")
    grant_path.chmod(0o600)
    with pytest.raises(StandingAutonomyConfigError, match="invalid") as malformed:
        load_standing_autonomy_grants(grant_path)
    assert "not-json" not in str(malformed.value)

    duplicate = {"version": 1, "grants": [_grant().model_dump(mode="json")] * 2}
    grant_path.write_text(json.dumps(duplicate), encoding="utf-8")
    with pytest.raises(StandingAutonomyConfigError, match="invalid"):
        load_standing_autonomy_grants(grant_path)

    grant_path.write_bytes(b" " * 65_537)
    with pytest.raises(StandingAutonomyConfigError, match="too large"):
        load_standing_autonomy_grants(grant_path)


def test_standing_autonomy_grants_require_aware_expiry_and_unique_binding() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _grant().model_copy(update={"expires_at": datetime(2027, 1, 1)}).model_validate(
            _grant().model_dump() | {"expires_at": datetime(2027, 1, 1)}
        )

    second = _grant().model_copy(update={"grant_id": "grant-2"})
    with pytest.raises(ValueError, match="duplicate standing autonomy binding"):
        StandingAutonomyGrantSet(grants=(_grant(), second))


def test_standing_autonomy_grants_reject_placeholder_bindings() -> None:
    with pytest.raises(ValueError, match="placeholder binding"):
        _grant().model_copy(update={"owner_id": "replace-with-owner"}).model_validate(
            _grant().model_dump() | {"owner_id": "replace-with-owner"}
        )


def test_standing_autonomy_grants_require_post_run_token_threshold() -> None:
    payload = _grant().model_dump()
    payload.pop("token_stop_threshold")

    with pytest.raises(ValueError, match="token_stop_threshold"):
        StandingAutonomyGrant.model_validate(payload)


async def test_task_bus_accepts_only_enforced_read_only_preauthorized_task() -> None:
    safe_adapter = RecordingAdapter(enforced=True)
    bus = TaskBus(safe_adapter)
    task = _preauthorized_task("Inspect current recovery evidence.")

    ack = await bus.submit(task)

    assert ack.status is AckStatus.ACCEPTED
    assert safe_adapter.received_tasks == [task]

    _ = [output async for output in bus.stream_output(task.task_id)]
    terminal_events = tuple(
        event
        for event in bus.audit_events(limit=None)
        if event.event_type in {AuditEventType.TASK_USAGE_RECORDED, AuditEventType.TASK_COMPLETED}
    )
    assert [event.event_type for event in terminal_events] == [
        AuditEventType.TASK_USAGE_RECORDED,
        AuditEventType.TASK_COMPLETED,
    ]
    usage_event = terminal_events[0]
    assert json.loads(usage_event.detail or "") == {
        "cache_write_input_tokens": 0,
        "cached_input_tokens": 0,
        "input_tokens": 80,
        "output_tokens": 20,
        "reasoning_output_tokens": 0,
        "total_tokens": 100,
    }


async def test_task_bus_rejects_direct_preauthorized_task_after_clock_rollback() -> None:
    wall = [datetime(2026, 7, 22, 8, tzinfo=UTC)]
    adapter = RecordingAdapter(enforced=True)
    bus = TaskBus(adapter, clock=lambda: wall[0])
    assert bus.authorization_time_refusal() is None
    wall[0] = datetime(2026, 7, 22, 7, 59, tzinfo=UTC)

    ack = await bus.submit(_preauthorized_task("Inspect current recovery evidence."))

    assert ack.status is AckStatus.REJECTED
    assert ack.reason == AUTHORIZATION_CLOCK_ROLLBACK_REASON
    assert adapter.received_tasks == []


@pytest.mark.parametrize(
    ("task_factory", "reason"),
    [
        (lambda: _preauthorized_task("Update the recovery file."), "read-only"),
        (
            lambda: _task_with_metadata(
                _preauthorized_task("Inspect recovery."),
                "aico.collaboration_mode",
                "enabled",
            ),
            "collaboration",
        ),
        (
            lambda: task_with_provider_session(
                _preauthorized_task("Inspect recovery."),
                ProviderSessionRef(provider_name="recording", session_id="session-1"),
                ProviderSessionMode.RESUME,
            ),
            "provider session",
        ),
        (
            lambda: _task_with_metadata(
                _preauthorized_task("Inspect recovery."),
                PREAUTHORIZED_MODE_KEY,
                "workspace_write",
            ),
            "unsupported",
        ),
    ],
)
async def test_task_bus_rejects_unsafe_preauthorized_task_shapes(
    task_factory: object,
    reason: str,
) -> None:
    adapter = RecordingAdapter(enforced=True)
    bus = TaskBus(adapter)

    ack = await bus.submit(task_factory())  # type: ignore[operator]

    assert ack.status is AckStatus.REJECTED
    assert reason in (ack.reason or "")
    assert adapter.received_tasks == []


async def test_task_bus_rejects_broad_adapter_even_when_metadata_is_forged() -> None:
    adapter = RecordingAdapter(enforced=False)
    bus = TaskBus(adapter)

    ack = await bus.submit(_preauthorized_task("Inspect recovery evidence."))

    assert ack.status is AckStatus.REJECTED
    assert "enforced read-only" in (ack.reason or "")
    assert adapter.received_tasks == []


def _grant() -> StandingAutonomyGrant:
    return StandingAutonomyGrant(
        grant_id="grant-1",
        owner_id="owner-telegram-123",
        channel_name="telegram",
        target_id="chat-1",
        project_id="aico",
        charter_id="absence-loop",
        expires_at=datetime(2027, 1, 1, tzinfo=UTC),
        max_runs=1,
        max_duration_seconds=0.1,
        token_stop_threshold=100_000,
    )


def _write_grants(path: Path) -> None:
    payload = StandingAutonomyGrantSet(grants=(_grant(),)).model_dump(mode="json")
    path.write_text(json.dumps(payload), encoding="utf-8")


def _preauthorized_task(payload: str) -> Task:
    task = Task(
        task_id="task-autonomy",
        payload=payload,
        requester_id="owner-telegram-123",
        target_persona="recording",
    )
    task = task_with_exact_output_constraint(task)
    return task_with_preauthorized_execution(
        task,
        grant_id="grant-1",
        expires_at=datetime(2027, 1, 1, tzinfo=UTC),
        max_duration_seconds=0.1,
    )


def _task_with_metadata(task: Task, key: str, value: str) -> Task:
    metadata = tuple(entry for entry in task.metadata if entry.key != key)
    return task.model_copy(update={"metadata": (*metadata, MetadataEntry(key=key, value=value))})
