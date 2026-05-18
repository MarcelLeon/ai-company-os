import json
from collections.abc import AsyncIterator
from io import StringIO
from pathlib import Path

from aico.app.glance_cli import run as run_glance_cli
from aico.app.metrics_cli import run as run_metrics_cli
from aico.channel import IncomingMessageHandler
from aico.core import (
    AckStatus,
    AdapterStatus,
    Capability,
    ChannelTarget,
    HealthStatus,
    IncomingMessage,
    InMemoryAuditLog,
    JsonlAuditSink,
    MessageContent,
    MessageRouter,
    Orchestrator,
    OutputType,
    SentMessage,
    Task,
    TaskAck,
    TaskBus,
    TaskOutput,
    read_jsonl_audit_events,
)


async def test_phase6_metrics_no_token_acceptance_covers_live_and_restart(
    tmp_path: Path,
) -> None:
    audit_path = tmp_path / "audit" / "events.jsonl"
    adapter = NoTokenAdapter()
    bus = TaskBus(adapter, audit_log=InMemoryAuditLog(sinks=(JsonlAuditSink(audit_path),)))
    channel = RecordingChannel()
    task_ids = iter(("task-done", "task-approval"))
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="implementer", task_id_factory=lambda: next(task_ids)),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming("summarize status without edits"))
    await orchestrator.handle_incoming(_incoming("modify docs/human/daily-ops.md"))
    parent_task = bus.task_record("task-done")
    assert parent_task is not None
    bus.record_collaboration_requested(
        parent_task,
        Task(
            task_id="task-review",
            payload="review the done task",
            requester_id="user-1",
            target_persona="reviewer",
        ),
    )
    await orchestrator.handle_incoming(_incoming("/metrics"))

    live_metrics = channel.sent_messages[-1].text
    _assert_metrics_acceptance(live_metrics)
    assert adapter.received_payloads == ["summarize status without edits"]

    restored_events = read_jsonl_audit_events(audit_path)
    restored_channel = RecordingChannel()
    restored_orchestrator = Orchestrator(
        channel=restored_channel,
        router=MessageRouter(default_persona="implementer"),
        task_bus=TaskBus(
            NoTokenAdapter(),
            audit_log=InMemoryAuditLog(initial_events=restored_events),
        ),
    )
    await restored_orchestrator.handle_incoming(_incoming("/metrics"))

    restored_metrics = restored_channel.sent_messages[-1].text
    _assert_metrics_acceptance(restored_metrics)

    metrics_stdout = StringIO()
    assert run_metrics_cli(["--audit-log", str(audit_path)], stdout=metrics_stdout) == 0
    _assert_metrics_acceptance(metrics_stdout.getvalue())

    metrics_json_stdout = StringIO()
    assert (
        run_metrics_cli(
            ["--audit-log", str(audit_path), "--format", "json"],
            stdout=metrics_json_stdout,
        )
        == 0
    )
    metrics_payload = json.loads(metrics_json_stdout.getvalue())
    assert metrics_payload["glance"]["status"] == "needs_approval"
    assert metrics_payload["summaries"][0]["total_tasks"] == 2
    assert metrics_payload["summaries"][0]["collaboration_requests"] == 1

    glance_stdout = StringIO()
    assert run_glance_cli(["--audit-log", str(audit_path)], stdout=glance_stdout) == 0
    glance_text = glance_stdout.getvalue()
    assert glance_text.startswith("AICO needs approval:")
    assert "- task-app [scripted] waiting_approval" in glance_text
    assert "/approve task-app" in glance_text

    glance_json_stdout = StringIO()
    assert (
        run_glance_cli(
            ["--audit-log", str(audit_path), "--format", "json"],
            stdout=glance_json_stdout,
        )
        == 0
    )
    glance_payload = json.loads(glance_json_stdout.getvalue())
    assert glance_payload["title"] == "AICO needs approval"
    assert glance_payload["recent_tasks"][0]["commands"] == [
        "/task task-app",
        "/approve task-app",
        "/reject task-app",
    ]


class NoTokenAdapter:
    def __init__(self) -> None:
        self.received_payloads: list[str] = []

    @property
    def name(self) -> str:
        return "scripted"

    def capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.CODE_EDIT, Capability.STREAM_OUTPUT})

    async def receive_task(self, task: Task) -> TaskAck:
        self.received_payloads.append(task.payload)
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    async def _outputs(self, task_id: str) -> AsyncIterator[TaskOutput]:
        yield TaskOutput(task_id=task_id, sequence=0, type=OutputType.TEXT, content="ok")
        yield TaskOutput(task_id=task_id, sequence=1, type=OutputType.DONE, content="")

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        return self._outputs(task_id)

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        _ = task_id

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


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


def _incoming(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="user-1",
        mentions=(),
        content=MessageContent(text=text),
        raw_ref="message-1",
    )


def _assert_metrics_acceptance(metrics: str) -> None:
    assert metrics.startswith("Metrics (local state + audit replay)\n\nglance\n")
    assert "status: needs_approval" in metrics
    assert "open: 1 (running=0, waiting_approval=1)" in metrics
    assert "\n\n24h\n" in metrics
    assert "tasks: 2\n" in metrics
    assert "done=1" in metrics
    assert "waiting_approval=1" in metrics
    assert "agents: scripted=2" in metrics
    assert "collaboration: 1" in metrics
    assert "open work:\n- task-approval [scripted]: waiting_approval" in metrics
    assert "token/cost: unavailable from current CLI adapters" in metrics
