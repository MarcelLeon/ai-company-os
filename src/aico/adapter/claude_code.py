"""Claude Code CLI adapter for the Phase 1 MVP."""

from __future__ import annotations

import asyncio
import logging
import shutil
from asyncio.subprocess import DEVNULL, PIPE, create_subprocess_exec
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from aico.core.agent_session import ProviderSessionMode, provider_session_from_task
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

DEFAULT_CLAUDE_COMMAND = (
    "claude",
    "-p",
    "--output-format",
    "text",
    "--permission-mode",
    "bypassPermissions",
)
DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS = 1800.0
DEFAULT_QUIET_STATUS_INTERVAL_SECONDS = 120.0
_FINISHED = object()
_MAX_STDERR_TAIL_CHARS = 8000


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


class AdapterOutputIdleTimeoutError(TimeoutError):
    """Raised when an adapter process stays alive without producing output."""

    def __init__(self, *, timeout_seconds: float, sequence: int) -> None:
        self.sequence = sequence
        super().__init__(f"adapter output idle timeout after {timeout_seconds:g}s")


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
        output_idle_timeout_seconds: float | None = None,
        quiet_status_interval_seconds: float | None = DEFAULT_QUIET_STATUS_INTERVAL_SECONDS,
        max_concurrent_tasks: int = 5,
    ) -> None:
        if not adapter_name:
            raise ValueError("adapter_name must not be empty")
        if not command:
            raise ValueError("command must not be empty")
        if interrupt_timeout_seconds <= 0:
            raise ValueError("interrupt_timeout_seconds must be positive")
        if output_idle_timeout_seconds is not None and output_idle_timeout_seconds <= 0:
            raise ValueError("output_idle_timeout_seconds must be positive")
        if quiet_status_interval_seconds is not None and quiet_status_interval_seconds <= 0:
            raise ValueError("quiet_status_interval_seconds must be positive")
        if max_concurrent_tasks <= 0:
            raise ValueError("max_concurrent_tasks must be positive")

        self._name = adapter_name
        self._command = command
        self._cwd = cwd
        self._process_factory = process_factory or _create_process
        self._interrupt_timeout_seconds = interrupt_timeout_seconds
        self._output_idle_timeout_seconds = output_idle_timeout_seconds
        self._quiet_status_interval_seconds = quiet_status_interval_seconds
        self._max_concurrent_tasks = max_concurrent_tasks
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

    def max_concurrent_tasks(self) -> int:
        return self._max_concurrent_tasks

    def running_task_count(self) -> int:
        return sum(1 for handle in self._tasks.values() if not handle.done)

    async def receive_task(self, task: Task) -> TaskAck:
        running_tasks = self.running_task_count()
        if running_tasks >= self._max_concurrent_tasks:
            log.info("Adapter busy: adapter=%s rejected_task=%s", self._name, task.task_id)
            return TaskAck(
                task_id=task.task_id,
                status=AckStatus.BUSY,
                reason=(
                    f"adapter is at max concurrency ({running_tasks}/{self._max_concurrent_tasks})"
                ),
            )
        if task.task_id in self._tasks:
            return TaskAck(
                task_id=task.task_id,
                status=AckStatus.REJECTED,
                reason="duplicate task id",
            )

        queue: asyncio.Queue[QueueItem] = asyncio.Queue()
        runner = asyncio.create_task(self._run_task(task, queue))
        self._tasks[task.task_id] = _TaskHandle(queue=queue, runner=runner)
        log.info(
            "Adapter accepted task: adapter=%s task_id=%s payload_chars=%s",
            self._name,
            task.task_id,
            len(task.payload),
        )
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
        if self.running_task_count() >= self._max_concurrent_tasks:
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
        stderr_task: asyncio.Task[None] | None = None
        try:
            log.info(
                "Adapter process starting: adapter=%s task_id=%s cwd=%s",
                self._name,
                task.task_id,
                self._cwd,
            )
            command = self._command_for_task(task)
            provider_session = provider_session_from_task(task)
            log.info(
                "Adapter command prepared: adapter=%s task_id=%s argc=%s "
                "provider_session_mode=%s provider_session_id=%s",
                self._name,
                task.task_id,
                len(command),
                None if provider_session is None else provider_session.mode.value,
                None if provider_session is None else provider_session.session_id[:8],
            )
            process = await self._process_factory(command, self._cwd)
            handle.process = process
            stderr_tail = _TextTailBuffer(max_chars=_MAX_STDERR_TAIL_CHARS)
            stderr_task = asyncio.create_task(_drain_stderr(process.stderr, stderr_tail))
            try:
                sequence = await self._stream_reader(task.task_id, process.stdout, queue, sequence)
            except AdapterOutputIdleTimeoutError as exc:
                sequence = exc.sequence
                log.warning(
                    "Adapter output idle timeout: adapter=%s task_id=%s timeout=%ss",
                    self._name,
                    task.task_id,
                    self._output_idle_timeout_seconds,
                )
                await self._stop_process(process)
                await _finish_stderr_task(stderr_task)
                await queue.put(_output(task.task_id, sequence, OutputType.ERROR, str(exc)))
                return
            return_code = await process.wait()
            await _finish_stderr_task(stderr_task)
            log.info(
                "Adapter process exited: adapter=%s task_id=%s return_code=%s stdout_chunks=%s",
                self._name,
                task.task_id,
                return_code,
                sequence,
            )
            if handle.interrupted:
                await queue.put(
                    _output(task.task_id, sequence, OutputType.ERROR, "task interrupted")
                )
                return
            if return_code == 0:
                await queue.put(_output(task.task_id, sequence, OutputType.DONE, ""))
                return

            content = self._process_error_content(stderr_tail.text(), return_code)
            await queue.put(_output(task.task_id, sequence, OutputType.ERROR, content))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("Claude Code task failed: task_id=%s", task.task_id)
            await queue.put(_output(task.task_id, sequence, OutputType.ERROR, str(exc)))
        finally:
            if stderr_task is not None and not stderr_task.done():
                stderr_task.cancel()
                await _suppress_cancelled(stderr_task)
            handle.done = True
            await queue.put(_FINISHED)
            log.info("Adapter task finished: adapter=%s task_id=%s", self._name, task.task_id)

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
        loop = asyncio.get_running_loop()
        last_adapter_output_at = loop.time()
        last_status_at = last_adapter_output_at
        while line := await self._readline(
            reader,
            sequence,
            last_adapter_output_at=last_adapter_output_at,
            last_status_at=last_status_at,
        ):
            if line is _QUIET_STATUS:
                now = loop.time()
                elapsed = now - last_adapter_output_at
                await queue.put(
                    _output(
                        task_id,
                        sequence,
                        OutputType.STATUS,
                        _quiet_status_message(elapsed),
                    )
                )
                last_status_at = now
                continue
            if not isinstance(line, bytes):
                continue
            last_adapter_output_at = loop.time()
            last_status_at = last_adapter_output_at
            content = self._process_stdout_line(_decode(line))
            if content is None:
                continue
            await queue.put(_output(task_id, sequence, OutputType.TEXT, content))
            sequence += 1
        return sequence

    def _process_stdout_line(self, content: str) -> str | None:
        return content

    def _process_error_content(self, stderr_text: str, return_code: int) -> str:
        return stderr_text or f"Claude Code exited with code {return_code}"

    async def _readline(
        self,
        reader: AsyncLineReader,
        sequence: int,
        *,
        last_adapter_output_at: float,
        last_status_at: float,
    ) -> bytes | object:
        timeout = self._next_read_timeout(
            last_adapter_output_at=last_adapter_output_at,
            last_status_at=last_status_at,
        )
        if timeout is None:
            return await reader.readline()
        try:
            return await asyncio.wait_for(reader.readline(), timeout=timeout)
        except TimeoutError as exc:
            elapsed = asyncio.get_running_loop().time() - last_adapter_output_at
            if (
                self._output_idle_timeout_seconds is not None
                and elapsed >= self._output_idle_timeout_seconds
            ):
                raise AdapterOutputIdleTimeoutError(
                    timeout_seconds=self._output_idle_timeout_seconds,
                    sequence=sequence,
                ) from exc
            return _QUIET_STATUS

    def _next_read_timeout(
        self,
        *,
        last_adapter_output_at: float,
        last_status_at: float,
    ) -> float | None:
        loop_time = asyncio.get_running_loop().time()
        deadlines: list[float] = []
        if self._output_idle_timeout_seconds is not None:
            deadlines.append(
                max(self._output_idle_timeout_seconds - (loop_time - last_adapter_output_at), 0)
            )
        if self._quiet_status_interval_seconds is not None:
            deadlines.append(
                max(self._quiet_status_interval_seconds - (loop_time - last_status_at), 0)
            )
        return min(deadlines) if deadlines else None

    async def _stop_process(self, process: AdapterProcess) -> None:
        if process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=self._interrupt_timeout_seconds)
        except TimeoutError:
            process.kill()
            await process.wait()

    def _command_for_task(self, task: Task) -> tuple[str, ...]:
        provider_session = provider_session_from_task(task)
        if (
            provider_session is None
            or provider_session.provider_name != self._name
            or _has_claude_session_option(self._command)
        ):
            return (*self._command, task.payload)

        if provider_session.mode is ProviderSessionMode.NEW:
            return (*self._command, "--session-id", provider_session.session_id, task.payload)
        return (*self._command, "--resume", provider_session.session_id, task.payload)


_QUIET_STATUS = object()


class _TextTailBuffer:
    def __init__(self, *, max_chars: int) -> None:
        self._max_chars = max_chars
        self._chunks: list[str] = []
        self._size = 0

    def append(self, value: str) -> None:
        if not value:
            return
        self._chunks.append(value)
        self._size += len(value)
        while self._size > self._max_chars and self._chunks:
            removed = self._chunks.pop(0)
            self._size -= len(removed)

    def text(self) -> str:
        return "".join(self._chunks).strip()


def _quiet_status_message(elapsed_seconds: float) -> str:
    elapsed = max(0, int(elapsed_seconds))
    return (
        f"Still running: no adapter output for {elapsed}s. "
        "Use /task <id> for details or /interrupt <id> to stop."
    )


async def _drain_stderr(reader: AsyncLineReader | None, tail: _TextTailBuffer) -> None:
    if reader is None:
        return
    while line := await reader.readline():
        tail.append(_decode(line))


async def _finish_stderr_task(task: asyncio.Task[None]) -> None:
    try:
        await task
    except asyncio.CancelledError:
        raise


async def _create_process(command: tuple[str, ...], cwd: Path | None) -> AdapterProcess:
    return await create_subprocess_exec(
        *command,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=PIPE,
        cwd=None if cwd is None else str(cwd),
    )


async def _suppress_cancelled(task: asyncio.Task[None]) -> None:
    try:
        await task
    except asyncio.CancelledError:
        pass


def _output(task_id: str, sequence: int, output_type: OutputType, content: str) -> TaskOutput:
    return TaskOutput(task_id=task_id, sequence=sequence, type=output_type, content=content)


def _decode(line: bytes) -> str:
    return line.decode("utf-8", errors="replace")


def _has_claude_session_option(command: tuple[str, ...]) -> bool:
    return any(part in {"--session-id", "--resume", "-r", "--continue", "-c"} for part in command)
