import os
import shlex
from io import StringIO
from pathlib import Path

import pytest

from aico.adapter.claude_code import ClaudeCodeAdapter
from aico.app.metrics_cli import run as run_metrics_cli
from aico.channel import IncomingMessageHandler
from aico.core import (
    ChannelTarget,
    HealthStatus,
    IncomingMessage,
    InMemoryAuditLog,
    JsonlAuditSink,
    MessageContent,
    MessageRouter,
    Orchestrator,
    SentMessage,
    TaskBus,
    read_jsonl_audit_events,
)


@pytest.mark.skipif(
    os.environ.get("AICO_RUN_TOKEN_GOLDEN") != "1",
    reason="set AICO_RUN_TOKEN_GOLDEN=1 to spend provider tokens",
)
async def test_phase6_metrics_with_real_provider_token_task(tmp_path: Path) -> None:
    command = _token_golden_command()
    audit_path = tmp_path / "audit" / "events.jsonl"
    adapter = ClaudeCodeAdapter(
        adapter_name="token-smoke",
        command=command,
        cwd=Path.cwd(),
        output_idle_timeout_seconds=180,
    )
    bus = TaskBus(adapter, audit_log=InMemoryAuditLog(sinks=(JsonlAuditSink(audit_path),)))
    channel = RecordingChannel()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(
            default_persona="token-smoke",
            task_id_factory=lambda: "task-token-golden",
        ),
        task_bus=bus,
    )

    await orchestrator.handle_incoming(_incoming(_token_golden_prompt()))
    assert any("AICO_METRICS_TOKEN_SMOKE_OK" in message.text for message in channel.edited_messages)
    await orchestrator.handle_incoming(_incoming("/metrics"))

    live_metrics = channel.sent_messages[-1].text
    _assert_token_metrics_golden(live_metrics)

    restored_events = read_jsonl_audit_events(audit_path)
    restored_channel = RecordingChannel()
    restored_orchestrator = Orchestrator(
        channel=restored_channel,
        router=MessageRouter(default_persona="token-smoke"),
        task_bus=TaskBus(
            ClaudeCodeAdapter(
                adapter_name="token-smoke",
                command=command,
                output_idle_timeout_seconds=180,
            ),
            audit_log=InMemoryAuditLog(initial_events=restored_events),
        ),
    )
    await restored_orchestrator.handle_incoming(_incoming("/metrics"))
    _assert_token_metrics_golden(restored_channel.sent_messages[-1].text)

    metrics_stdout = StringIO()
    assert run_metrics_cli(["--audit-log", str(audit_path)], stdout=metrics_stdout) == 0
    _assert_token_metrics_golden(metrics_stdout.getvalue())


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


def _token_golden_command() -> tuple[str, ...]:
    value = os.environ.get("AICO_TOKEN_GOLDEN_COMMAND")
    if not value:
        return (
            "claude",
            "-p",
            "--output-format",
            "text",
            "--permission-mode",
            "bypassPermissions",
        )
    return tuple(shlex.split(value))


def _token_golden_prompt() -> str:
    return "Return exactly this text: AICO_METRICS_TOKEN_SMOKE_OK"


def _incoming(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="user-1",
        mentions=(),
        content=MessageContent(text=text),
        raw_ref="message-1",
    )


def _assert_token_metrics_golden(metrics: str) -> None:
    assert metrics.startswith("Metrics (local state + audit replay)\n\nglance\n")
    assert "status: quiet" in metrics
    assert "open: 0 (running=0, waiting_approval=0)" in metrics
    assert "\n\n24h\n" in metrics
    assert "tasks: 1\n" in metrics
    assert "done=1" in metrics
    assert "agents: token-smoke=1" in metrics
    assert "collaboration: 0" in metrics
    assert "open work:\n- none" in metrics
    assert "token/cost: unavailable from current CLI adapters" in metrics
