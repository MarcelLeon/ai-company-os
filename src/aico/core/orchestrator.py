"""Phase 1 orchestration loop for one channel and one task bus."""

from __future__ import annotations

import asyncio

from aico.channel import IMChannel
from aico.core.models import (
    AckStatus,
    AdapterSnapshot,
    IncomingMessage,
    MessageContent,
    OutputType,
    RiskLevel,
    SentMessage,
    Task,
    TaskSnapshot,
)
from aico.core.router import MessageRouter
from aico.core.task_bus import TaskBus


class Orchestrator:
    """Handle an incoming IM message by submitting a task and streaming progress back."""

    def __init__(
        self,
        channel: IMChannel,
        router: MessageRouter,
        task_bus: TaskBus,
    ) -> None:
        self._channel = channel
        self._router = router
        self._task_bus = task_bus

    def bind(self) -> None:
        self._channel.on_incoming(self.handle_incoming)

    async def handle_incoming(self, message: IncomingMessage) -> None:
        if _is_help_message(message):
            await self._channel.send_message(message.source, _help_message())
            return

        if _is_status_message(message):
            await self._channel.send_message(
                message.source,
                _status_message(
                    self._task_bus.snapshots(),
                    self._task_bus.task_snapshots(),
                ),
            )
            return

        approval_task_id = _task_id_for_command(message, "approve")
        if approval_task_id is not None:
            await self._handle_approval(message, approval_task_id)
            return

        reject_parts = _reject_parts(message)
        if reject_parts is not None:
            await self._handle_rejection(message, reject_parts[0], reject_parts[1])
            return

        broadcast_payload = _broadcast_payload(message)
        if broadcast_payload is not None:
            await self._handle_broadcast(message, broadcast_payload)
            return

        task = self._router.to_task(message)
        await self._run_task(message, task, include_target=False)

    async def _handle_broadcast(self, message: IncomingMessage, payload: str) -> None:
        if not payload:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /broadcast <task>"),
            )
            return

        targets = self._task_bus.broadcast_targets()
        if not targets:
            await self._channel.send_message(message.source, MessageContent(text="No targets"))
            return

        await self._channel.send_message(
            message.source,
            MessageContent(text=f"Broadcast accepted: {len(targets)} targets"),
        )
        tasks = [self._router.to_task_for_target(message, target, payload) for target in targets]
        await asyncio.gather(
            *(self._run_task(message, task, include_target=True) for task in tasks)
        )

    async def _handle_approval(self, message: IncomingMessage, task_id: str) -> None:
        if not task_id:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /approve <task_id>"),
            )
            return

        ack = await self._task_bus.approve(task_id, reviewer_id=message.sender_id)
        if ack.status is not AckStatus.ACCEPTED:
            await self._channel.send_message(
                message.source,
                _ack_failure_message(ack.status, ack.reason),
            )
            return

        sent_message = await self._channel.send_message(
            message.source,
            MessageContent(text=f"Task approved: {task_id}"),
        )
        await self._stream_outputs(message, sent_message, task_id)

    async def _handle_rejection(
        self,
        message: IncomingMessage,
        task_id: str,
        reason: str | None,
    ) -> None:
        if not task_id:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /reject <task_id> [reason]"),
            )
            return

        ack = await self._task_bus.reject_approval(
            task_id,
            reviewer_id=message.sender_id,
            reason=reason,
        )
        await self._channel.send_message(
            message.source,
            _ack_failure_message(ack.status, ack.reason),
        )

    async def _run_task(
        self,
        message: IncomingMessage,
        task: Task,
        *,
        include_target: bool,
    ) -> None:
        ack = await self._task_bus.submit(task)
        if ack.status is AckStatus.WAITING_APPROVAL:
            await self._channel.send_message(
                message.source,
                _approval_required_message(task.task_id, ack.reason),
            )
            return
        if ack.status is not AckStatus.ACCEPTED:
            await self._channel.send_message(
                message.source,
                _ack_failure_message(ack.status, ack.reason),
            )
            return

        target_text = f" [{task.target_persona}]" if include_target else ""
        sent_message = await self._channel.send_message(
            message.source,
            MessageContent(text=f"Task accepted: {task.task_id}{target_text}"),
        )
        await self._stream_outputs(message, sent_message, task.task_id)

    async def _stream_outputs(
        self,
        message: IncomingMessage,
        sent_message: SentMessage,
        task_id: str,
    ) -> None:
        chunks: list[str] = []
        async for output in self._task_bus.stream_output(task_id):
            if output.type is OutputType.TEXT:
                chunks.append(output.content)
            elif output.type is OutputType.ERROR:
                chunks.append(f"\nERROR: {output.content}")
            elif output.type is OutputType.DONE and output.content:
                chunks.append(output.content)

            if chunks:
                await self._channel.edit_message(
                    message.source,
                    sent_message.message_id,
                    MessageContent(text="".join(chunks)),
                )


def _ack_failure_message(status: AckStatus, reason: str | None) -> MessageContent:
    reason_text = f": {reason}" if reason else ""
    return MessageContent(text=f"Task {status.value}{reason_text}")


def _approval_required_message(task_id: str, reason: str | None) -> MessageContent:
    reason_text = f"\n{reason}" if reason else ""
    return MessageContent(
        text=(
            f"Approval required: {task_id}{reason_text}\n"
            f"Use /approve {task_id} to continue or /reject {task_id} [reason] to stop."
        )
    )


def _is_status_message(message: IncomingMessage) -> bool:
    return message.content.text.strip().lower() in {"/status", "status"}


def _is_help_message(message: IncomingMessage) -> bool:
    return message.content.text.strip().lower() in {"/help", "help"}


def _broadcast_payload(message: IncomingMessage) -> str | None:
    text = message.content.text.strip()
    first, separator, rest = text.partition(" ")
    command = first[1:].split("@", maxsplit=1)[0].lower() if first.startswith("/") else ""
    if command != "broadcast":
        return None
    return rest.strip() if separator and rest.strip() else ""


def _task_id_for_command(message: IncomingMessage, command_name: str) -> str | None:
    text = message.content.text.strip()
    first, separator, rest = text.partition(" ")
    command = first[1:].split("@", maxsplit=1)[0].lower() if first.startswith("/") else ""
    if command != command_name:
        return None
    return rest.strip() if separator and rest.strip() else ""


def _reject_parts(message: IncomingMessage) -> tuple[str, str | None] | None:
    payload = _task_id_for_command(message, "reject")
    if payload is None:
        return None
    task_id, separator, reason = payload.partition(" ")
    return task_id.strip(), reason.strip() if separator and reason.strip() else None


def _status_message(
    adapter_snapshots: tuple[AdapterSnapshot, ...],
    task_snapshots: tuple[TaskSnapshot, ...],
) -> MessageContent:
    lines = [f"{snapshot.name}: {snapshot.status.value}" for snapshot in adapter_snapshots]
    if task_snapshots:
        lines.append("")
        lines.append("Recent tasks:")
        lines.extend(_task_status_line(snapshot) for snapshot in task_snapshots)
    return MessageContent(text="\n".join(lines))


def _task_status_line(snapshot: TaskSnapshot) -> str:
    adapter_name = snapshot.adapter_name or snapshot.target_persona
    line = f"{snapshot.task_id} [{adapter_name}]: {snapshot.status.value}"
    if snapshot.risk_level is not RiskLevel.READ_ONLY:
        line = f"{line} ({snapshot.risk_level.value})"
    if snapshot.reason:
        line = f"{line} - {snapshot.reason}"
    return line


def _help_message() -> MessageContent:
    return MessageContent(
        text=(
            "Commands:\n"
            "/status - show adapter status\n"
            "/broadcast <task> - send task to every active persona\n"
            "/approve <task_id> - approve a waiting risky task\n"
            "/reject <task_id> [reason] - reject a waiting risky task\n"
            "/claude <task> - send task to Claude Code\n"
            "/codex <task> - send read-only task to Codex\n"
            "@codex <task> or codex: <task> also work"
        )
    )
