"""Claude Code CLI adapter for the Phase 1 MVP."""

from __future__ import annotations

import asyncio
import logging
import shutil
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from aico.core.models import (
    AckStatus,
    AdapterStatus,
    Capability,
    HealthStatus,
    OutputType,
    Task,
    TaskAck,
    TaskOutput,
)

log = logging.getLogger(__name__)

DEFAULT_CLAUDE_COMMAND = ("claude", "-p", "--output-format", "text")
_FINISHED = object()


class AsyncLineReader(Protocol):
    async def readline(self) -> bytes: ...


class AdapterProcess(Protocol):
    @property
    def stdout(self) -> AsyncLineReader | None: ...

    @property
    def stderr(self) -> AsyncLineReader | None: ...

    @property
    def returncode(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    async def wait(self) -> int: ...


ProcessFactory = Callable[[tuple[str, ...], Path | None], Awaitable[AdapterProcess]]
QueueItem = TaskOutput | object


@dataclass
class _TaskHandle:
    queue: asyncio.Queue[QueueItem]
    runner: asyncio.Task[None]
    process: AdapterProcess | None = None
    done: bool = False
    interrupted: bool = False


class ClaudeCodeAdapter:
    """Run text tasks through Claude Code's non-interactive CLI mode."""

    def __init__(
        self,
        *,
        adapter_name: str = "claude-code",
        command: tuple[str, ...] = DEFAULT_CLAUDE_COMMAND,
        cwd: Path | None = None,
        process_factory: ProcessFactory | None = None,
        interrupt_timeout_seconds: float = 5.0,
    ) -> None:
        if not adapter_name:
            raise ValueError("adapter_name must not be empty")
        if not command:
            raise ValueError("command must not be empty")
        if interrupt_timeout_seconds <= 0:
            raise ValueError("interrupt_timeout_seconds must be positive")

        self._name = adapter_name
        self._command = command
        self._cwd = cwd
        self._process_factory = process_factory or _create_process
        self._interrupt_timeout_seconds = interrupt_timeout_seconds
        self._tasks: dict[str, _TaskHandle] = {}

    @property
    def name(self) -> str:
        return self._name

    def capabilities(self) -> frozenset[Capability]:
        return frozenset(
            {
                Capability.CODE_EDIT,
                Capability.CODE_REVIEW,
                Capability.SHELL_EXEC,
                Capability.LONG_RUNNING,
                Capability.STREAM_OUTPUT,
                Capability.INTERRUPTIBLE,
            }
        )

    async def receive_task(self, task: Task) -> TaskAck:
        if self.status() is AdapterStatus.BUSY:
            return TaskAck(task_id=task.task_id, status=AckStatus.BUSY, reason="adapter is busy")
        if task.task_id in self._tasks:
            return TaskAck(
                task_id=task.task_id,
                status=AckStatus.REJECTED,
                reason="duplicate task id",
            )

        queue: asyncio.Queue[QueueItem] = asyncio.Queue()
        runner = asyncio.create_task(self._run_task(task, queue))
        self._tasks[task.task_id] = _TaskHandle(queue=queue, runner=runner)
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    async def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        handle = self._tasks.get(task_id)
        if handle is None:
            yield TaskOutput(
                task_id=task_id,
                sequence=0,
                type=OutputType.ERROR,
                content="unknown task id",
            )
            return

        while True:
            item = await handle.queue.get()
            if item is _FINISHED:
                return
            if isinstance(item, TaskOutput):
                yield item

    def status(self) -> AdapterStatus:
        if any(not handle.done for handle in self._tasks.values()):
            return AdapterStatus.BUSY
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        handle = self._tasks.get(task_id)
        if handle is None or handle.done:
            return

        handle.interrupted = True
        process = handle.process
        if process is None:
            await handle.queue.put(
                TaskOutput(
                    task_id=task_id,
                    sequence=0,
                    type=OutputType.ERROR,
                    content="task interrupted",
                )
            )
            handle.runner.cancel()
            await _suppress_cancelled(handle.runner)
            handle.done = True
            return

        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=self._interrupt_timeout_seconds)
            except TimeoutError:
                process.kill()
                await process.wait()

        await handle.runner

    async def health_check(self) -> HealthStatus:
        executable = self._command[0]
        return HealthStatus.OK if shutil.which(executable) else HealthStatus.FAILED

    async def _run_task(self, task: Task, queue: asyncio.Queue[QueueItem]) -> None:
        handle = self._tasks[task.task_id]
        sequence = 0
        try:
            process = await self._process_factory((*self._command, task.payload), self._cwd)
            handle.process = process
            sequence = await self._stream_reader(task.task_id, process.stdout, queue, sequence)
            return_code = await process.wait()
            if handle.interrupted:
                await queue.put(
                    _output(task.task_id, sequence, OutputType.ERROR, "task interrupted")
                )
                return
            if return_code == 0:
                await queue.put(_output(task.task_id, sequence, OutputType.DONE, ""))
                return

            stderr_text = await _read_remaining(process.stderr)
            content = stderr_text or f"Claude Code exited with code {return_code}"
            await queue.put(_output(task.task_id, sequence, OutputType.ERROR, content))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("Claude Code task failed: task_id=%s", task.task_id)
            await queue.put(_output(task.task_id, sequence, OutputType.ERROR, str(exc)))
        finally:
            handle.done = True
            await queue.put(_FINISHED)

    async def _stream_reader(
        self,
        task_id: str,
        reader: AsyncLineReader | None,
        queue: asyncio.Queue[QueueItem],
        start_sequence: int,
    ) -> int:
        if reader is None:
            return start_sequence

        sequence = start_sequence
        while line := await reader.readline():
            await queue.put(_output(task_id, sequence, OutputType.TEXT, _decode(line)))
            sequence += 1
        return sequence


async def _create_process(command: tuple[str, ...], cwd: Path | None) -> AdapterProcess:
    return await create_subprocess_exec(
        *command,
        stdout=PIPE,
        stderr=PIPE,
        cwd=None if cwd is None else str(cwd),
    )


async def _read_remaining(reader: AsyncLineReader | None) -> str:
    if reader is None:
        return ""

    chunks: list[str] = []
    while line := await reader.readline():
        chunks.append(_decode(line))
    return "".join(chunks).strip()


async def _suppress_cancelled(task: asyncio.Task[None]) -> None:
    try:
        await task
    except asyncio.CancelledError:
        pass


def _output(task_id: str, sequence: int, output_type: OutputType, content: str) -> TaskOutput:
    return TaskOutput(task_id=task_id, sequence=sequence, type=output_type, content=content)


def _decode(line: bytes) -> str:
    return line.decode("utf-8", errors="replace")
