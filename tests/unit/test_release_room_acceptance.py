from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

from aico.channel import IncomingMessageHandler
from aico.core import (
    AckStatus,
    AdapterRegistry,
    AdapterStatus,
    AuditEventType,
    Capability,
    ChannelTarget,
    HealthStatus,
    IncomingMessage,
    JsonlMemoryStore,
    MemoryScope,
    MessageContent,
    MessageRouter,
    Orchestrator,
    OutputType,
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
    SentMessage,
    Task,
    TaskAck,
    TaskBus,
    TaskOutput,
)


async def test_release_room_stage2_local_acceptance_transcript(tmp_path: Path) -> None:
    channel = RecordingChannel()
    claude = ReleaseRoomAdapter("claude-code")
    codex = ReleaseRoomAdapter("codex")
    task_ids = iter(f"release-task-{index:03d}" for index in range(1, 20))
    task_bus = TaskBus(
        AdapterRegistry(
            [claude, codex],
            aliases={
                "claude": "claude-code",
                "codex": "codex",
                "pm": "claude-code",
                "implementer": "claude-code",
                "release-manager": "claude-code",
                "tester": "codex",
                "reviewer": "codex",
            },
        )
    )
    memory_store = JsonlMemoryStore(tmp_path / "release-room-memory.jsonl")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="claude", task_id_factory=lambda: next(task_ids)),
        task_bus=task_bus,
        project_directory=_release_room_directory(),
        memory_store=memory_store,
    )

    await _send(orchestrator, "/use project release-room")
    await _send(orchestrator, "/team")
    assert "Team for release-room" in channel.sent_messages[-1].text
    assert "lead: pm -> claude" in channel.sent_messages[-1].text
    assert "reviewer -> codex" in channel.sent_messages[-1].text

    await _send(orchestrator, "/remember v0.2 不接受没有测试的功能。")
    await _send(orchestrator, "/remember README 必须面向第一次使用 CLI 的开源用户。")
    await _send(
        orchestrator,
        "/remember release notes 必须包含 Added / Fixed / Changed / Verification。",
    )
    assert len(memory_store.list_atoms(MemoryScope.project("release-room"))) == 3

    await _send(
        orchestrator,
        "/ask pm 阅读 STATUS.md 和 issues/003-v02-release.md，把 v0.2 "
        "拆成角色任务、验收标准和风险清单。",
    )
    pm_task = claude.task_for_role("pm")
    assert "Shared memory:" in pm_task.payload
    assert "v0.2 不接受没有测试的功能" in pm_task.payload
    assert "Release plan:" in channel.edited_messages[-1].text

    before_implementation_count = len(claude.received_tasks)
    await _send(
        orchestrator,
        "/ask implementer update src/notes_cli/__main__.py, README and CHANGELOG, "
        "then run pytest for v0.2.",
    )
    assert len(claude.received_tasks) == before_implementation_count
    assert "Approval required: release-" in channel.sent_messages[-1].text

    await _send(orchestrator, "/approve")
    implementation_task = claude.task_for_role("implementer")
    assert "README 必须面向第一次使用 CLI 的开源用户" in implementation_task.payload
    assert "Task approved: release-" in channel.sent_messages[-1].text

    await _send(
        orchestrator,
        "/ask tester 检查 tests/test_v02_contract.py 的回归策略并报告失败项。",
    )
    await _send(
        orchestrator,
        "/ask reviewer review v0.2 release risk, test gaps, README and CHANGELOG consistency.",
    )
    assert "Test report:" in channel.edited_messages[-2].text
    assert "Review findings:" in channel.edited_messages[-1].text
    assert codex.task_for_role("tester").target_persona == "codex"
    assert codex.task_for_role("reviewer").target_persona == "codex"

    await _send(
        orchestrator,
        "/ask release-manager draft the v0.2 release notes and go/no-go checklist.",
    )
    assert "Release notes draft:" in channel.edited_messages[-1].text

    await _send(
        orchestrator,
        "/overnight 推进 v0.2 release room，早上给我 done/blocked/risks/next actions。",
    )
    assert any("Overnight delegation queued" in message.text for message in channel.sent_messages)
    overnight_task = claude.latest_task_with_metadata("aico.intent", "offline_delegation")
    assert overnight_task is not None
    assert "Morning handoff:" in channel.edited_messages[-1].text

    await _send(orchestrator, "/morning")
    assert "Morning handoff: release-room" in channel.sent_messages[-1].text
    assert "Done:" in channel.sent_messages[-1].text
    assert "Risks:" in channel.sent_messages[-1].text

    await _send(orchestrator, "/tasks")
    assert "Recent tasks:" in channel.sent_messages[-1].text
    assert "release-task-" in channel.sent_messages[-1].text

    await _send(orchestrator, "/metrics")
    assert "Metrics" in channel.sent_messages[-1].text
    assert "tasks:" in channel.sent_messages[-1].text

    await _send(orchestrator, "/audit")
    assert "Recent audit events:" in channel.sent_messages[-1].text
    assert "task_completed" in channel.sent_messages[-1].text
    event_types = {event.event_type for event in task_bus.audit_events(limit=None)}
    assert AuditEventType.APPROVAL_REQUESTED in event_types
    assert AuditEventType.APPROVAL_APPROVED in event_types


def test_release_room_stage2_transcript_documents_the_acceptance_path() -> None:
    transcript = Path("examples/release-room/transcript.md").read_text(encoding="utf-8")

    for command in (
        "/use project release-room",
        "/team",
        "/remember v0.2",
        "/ask pm",
        "/ask implementer",
        "/approve",
        "/ask tester",
        "/ask reviewer",
        "/overnight",
        "/morning",
        "/metrics",
        "/audit",
    ):
        assert command in transcript


class ReleaseRoomAdapter:
    def __init__(self, name: str) -> None:
        self._name = name
        self.received_tasks: list[Task] = []
        self._tasks_by_id: dict[str, Task] = {}

    @property
    def name(self) -> str:
        return self._name

    def capabilities(self) -> frozenset[Capability]:
        return frozenset(
            {
                Capability.CODE_EDIT,
                Capability.CODE_REVIEW,
                Capability.SHELL_EXEC,
                Capability.STREAM_OUTPUT,
                Capability.INTERRUPTIBLE,
            }
        )

    async def receive_task(self, task: Task) -> TaskAck:
        self.received_tasks.append(task)
        self._tasks_by_id[task.task_id] = task
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    async def _outputs(self, task_id: str) -> AsyncIterator[TaskOutput]:
        task = self._tasks_by_id[task_id]
        yield TaskOutput(
            task_id=task_id,
            sequence=0,
            type=OutputType.TEXT,
            content=_release_room_response(task),
        )
        yield TaskOutput(task_id=task_id, sequence=1, type=OutputType.DONE, content="")

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        return self._outputs(task_id)

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        _ = task_id

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK

    def task_for_role(self, role: str) -> Task:
        for task in reversed(self.received_tasks):
            if _metadata_value(task, "aico.assignment_role") == role:
                return task
        raise AssertionError(f"role task not found: {role}")

    def latest_task_with_metadata(self, key: str, value: object) -> Task | None:
        for task in reversed(self.received_tasks):
            if _metadata_value(task, key) == value:
                return task
        return None


class RecordingChannel:
    def __init__(self) -> None:
        self.handler: IncomingMessageHandler | None = None
        self.sent_messages: list[MessageContent] = []
        self.edited_messages: list[MessageContent] = []

    @property
    def name(self) -> str:
        return "telegram"

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> SentMessage:
        _ = target
        self.sent_messages.append(content)
        return SentMessage(message_id=f"message-{len(self.sent_messages)}", target=target)

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> None:
        _ = (target, message_id)
        self.edited_messages.append(content)

    async def delete_message(self, target: ChannelTarget, message_id: str) -> None:
        _ = target, message_id

    def on_incoming(self, handler: IncomingMessageHandler) -> None:
        self.handler = handler

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


async def _send(orchestrator: Orchestrator, text: str) -> None:
    await orchestrator.handle_incoming(
        IncomingMessage(
            channel_name="telegram",
            source=ChannelTarget(channel_name="telegram", target_id="release-room-chat"),
            sender_id="boss-1",
            mentions=(),
            content=MessageContent(text=text),
            raw_ref=f"release-room:{text[:32]}",
        )
    )


def _release_room_directory() -> ProjectAssignmentDirectory:
    config_path = Path("examples/release-room/aico-project.json")
    config = ProjectAssignmentConfig.model_validate(
        json.loads(config_path.read_text(encoding="utf-8"))
    )
    return ProjectAssignmentDirectory(config)


def _release_room_response(task: Task) -> str:
    if _metadata_value(task, "aico.intent") == "project_summary":
        return (
            "- Done: PM, implementer, tester, reviewer, release-manager, and overnight tasks "
            "are visible.\n"
            "- Blocked: v0.2 contract tests are still skipped in the seed repo.\n"
            "- Risks: do not publish until tests are unskipped and passing.\n"
            "- Next actions: implement release, run tests, update release notes."
        )
    if _metadata_value(task, "aico.intent") == "offline_delegation":
        return (
            "Morning handoff:\n"
            "done: release plan and checks staged\n"
            "blocked: real CLI changes still require a real adapter run\n"
            "risks: skipped v0.2 contract tests\n"
            "next actions: implement, unskip, record release notes"
        )

    role = _metadata_value(task, "aico.assignment_role")
    if role == "pm":
        return (
            "Release plan: implementer owns tags/search/export and bug fix; tester owns "
            "contract tests; reviewer owns behavior and docs risk; release-manager owns "
            "notes and go/no-go."
        )
    if role == "implementer":
        return (
            "Implementation handoff: code, tests, README, CHANGELOG, and release notes are "
            "ready for independent checks."
        )
    if role == "tester":
        return (
            "Test report: v0.2 contract covers tags, search, JSON export, and unknown-id exit code."
        )
    if role == "reviewer":
        return (
            "Review findings: no release until skipped contracts are enabled and docs match "
            "behavior."
        )
    if role == "release-manager":
        return (
            "Release notes draft: Added tags/search/export; Fixed missing-id done behavior; "
            "Verification still requires unskipped contract tests."
        )
    return "Release room task complete."


def _metadata_value(task: Task, key: str) -> object | None:
    for entry in task.metadata:
        if entry.key == key:
            return entry.value
    return None
