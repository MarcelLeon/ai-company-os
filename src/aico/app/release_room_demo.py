"""No-token Release Room demo runner."""

from __future__ import annotations

import asyncio
import json
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

from aico.adapter import AIAdapter
from aico.channel import IMChannel, IncomingMessageHandler
from aico.core import (
    AckStatus,
    AdapterRegistry,
    AdapterStatus,
    Capability,
    ChannelTarget,
    HealthStatus,
    IncomingMessage,
    JsonlMemoryStore,
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

DEMO_COMMANDS = (
    "/use project release-room",
    "/team",
    "/remember v0.2 不接受没有测试的功能。",
    "/ask pm 阅读 STATUS.md 和 issues/003-v02-release.md，把 v0.2 拆成任务、验收标准和风险。",
    "/ask implementer update src/notes_cli/__main__.py, README and CHANGELOG, then run pytest.",
    "/approve",
    "/ask tester 检查 tests/test_v02_contract.py 的回归策略并报告失败项。",
    "/ask reviewer review v0.2 release risk, test gaps, README and CHANGELOG consistency.",
    "/overnight 推进 v0.2 release room，早上给我 done/blocked/risks/next actions。",
    "/daily release-room",
    "/audit",
)


def main() -> None:
    print(asyncio.run(run_demo()))


async def run_demo() -> str:
    with tempfile.TemporaryDirectory(prefix="aico-release-room-") as temp_dir:
        channel = _RecordingChannel()
        task_ids = iter(f"demo-task-{index:03d}" for index in range(1, 40))
        orchestrator = Orchestrator(
            channel=channel,
            router=MessageRouter(
                default_persona="claude",
                task_id_factory=lambda: next(task_ids),
            ),
            task_bus=TaskBus(
                AdapterRegistry(
                    [_ReleaseRoomAdapter("claude-code"), _ReleaseRoomAdapter("codex")],
                    aliases={
                        "claude": "claude-code",
                        "codex": "codex",
                        "pm": "claude-code",
                        "implementer": "claude-code",
                        "tester": "codex",
                        "reviewer": "codex",
                        "release-manager": "claude-code",
                    },
                )
            ),
            project_directory=_release_room_directory(),
            memory_store=JsonlMemoryStore(Path(temp_dir) / "memory.jsonl"),
        )

        for command in DEMO_COMMANDS:
            channel.record_boss(command)
            await _send(orchestrator, command)

        return _transcript(channel)


class _ReleaseRoomAdapter(AIAdapter):
    def __init__(self, name: str) -> None:
        self._name = name
        self._tasks: dict[str, Task] = {}

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
        self._tasks[task.task_id] = task
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        return self._outputs(task_id)

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        _ = task_id

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK

    async def _outputs(self, task_id: str) -> AsyncIterator[TaskOutput]:
        yield TaskOutput(
            task_id=task_id,
            sequence=0,
            type=OutputType.TEXT,
            content=_release_room_response(self._tasks[task_id]),
        )
        yield TaskOutput(task_id=task_id, sequence=1, type=OutputType.DONE, content="")


class _RecordingChannel(IMChannel):
    def __init__(self) -> None:
        self.sent_messages: list[MessageContent] = []
        self.edited_messages: list[MessageContent] = []
        self.events: list[str] = []
        self._handler: IncomingMessageHandler | None = None

    @property
    def name(self) -> str:
        return "demo"

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> SentMessage:
        self.sent_messages.append(content)
        self.events.append(f"AICO:\n{content.text}")
        return SentMessage(message_id=f"message-{len(self.sent_messages)}", target=target)

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> None:
        _ = target, message_id
        self.edited_messages.append(content)
        self.events.append(f"AICO update:\n{content.text}")

    async def delete_message(self, target: ChannelTarget, message_id: str) -> None:
        _ = target, message_id

    def on_incoming(self, handler: IncomingMessageHandler) -> None:
        self._handler = handler

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK

    def record_boss(self, command: str) -> None:
        self.events.append(f"Boss:\n{command}")


async def _send(orchestrator: Orchestrator, text: str) -> None:
    await orchestrator.handle_incoming(
        IncomingMessage(
            channel_name="demo",
            source=ChannelTarget(channel_name="demo", target_id="release-room"),
            sender_id="boss-demo",
            content=MessageContent(text=text),
            raw_ref=f"demo:{text[:24]}",
        )
    )


def _release_room_directory() -> ProjectAssignmentDirectory:
    config_path = Path("examples/release-room/aico-project.json")
    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    return ProjectAssignmentDirectory(ProjectAssignmentConfig.model_validate(raw_config))


def _release_room_response(task: Task) -> str:
    intent = _metadata_value(task, "aico.intent")
    role = _metadata_value(task, "aico.assignment_role")
    if intent == "project_summary":
        return (
            "Done:\n"
            "- team, memory, approval, tester, reviewer and overnight handoff are visible\n"
            "Blocked:\n"
            "- no real provider token was used in this demo\n"
            "Risks:\n"
            "- keep public claims scoped to what is already implemented\n"
            "Next actions:\n"
            "- run the same script through Telegram for dogfooding evidence"
        )
    if intent == "offline_delegation":
        return (
            "Morning handoff:\n"
            "done: release plan and review chain staged\n"
            "blocked: real code changes require a real adapter run\n"
            "risks: skipped contract tests\n"
            "next actions: implement, unskip tests, update release notes"
        )
    if role == "pm":
        return (
            "Release plan:\n"
            "- implementer owns tags/search/export and bug fix\n"
            "- tester owns contract tests\n"
            "- reviewer owns behavior and docs risk\n"
            "- release-manager owns notes and go/no-go"
        )
    if role == "tester":
        return "Test report:\n- v0.2 contracts cover tags, search, JSON export and exit codes"
    if role == "reviewer":
        return "Review findings:\n- do not release until skipped contracts are enabled"
    return "Implementation handoff:\n- code, docs and tests are ready for independent checks"


def _metadata_value(task: Task, key: str) -> object | None:
    for entry in task.metadata:
        if entry.key == key:
            return entry.value
    return None


def _transcript(channel: _RecordingChannel) -> str:
    lines = ["# AICO Release Room no-token demo", ""]
    lines.append(
        "This local demo uses fake adapters. No Telegram bot token or LLM API is required."
    )
    for event in channel.events:
        lines.extend(("", event))
    return "\n".join(lines)
