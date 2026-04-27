import asyncio
import sys
from pathlib import Path

from aico.adapter import AIAdapter
from aico.adapter.claude_code import ClaudeCodeAdapter
from aico.core import AckStatus, AdapterStatus, HealthStatus, OutputType, Task, TaskOutput


class FakeLineReader:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    async def readline(self) -> bytes:
        await asyncio.sleep(0)
        if not self._lines:
            return b""
        return self._lines.pop(0)


class FakeProcess:
    def __init__(
        self,
        *,
        stdout: list[bytes],
        stderr: list[bytes] | None = None,
        return_code: int = 0,
        wait_event: asyncio.Event | None = None,
    ) -> None:
        self.stdout = FakeLineReader(stdout)
        self.stderr = FakeLineReader(stderr or [])
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False
        self._return_code = return_code
        self._wait_event = wait_event

    def terminate(self) -> None:
        self.terminated = True
        if self._wait_event is not None:
            self._wait_event.set()

    def kill(self) -> None:
        self.killed = True
        if self._wait_event is not None:
            self._wait_event.set()

    async def wait(self) -> int:
        if self._wait_event is not None:
            await self._wait_event.wait()
        self.returncode = self._return_code
        return self._return_code


async def test_claude_code_adapter_streams_stdout_and_done() -> None:
    calls: list[tuple[tuple[str, ...], Path | None]] = []

    async def factory(command: tuple[str, ...], cwd: Path | None) -> FakeProcess:
        calls.append((command, cwd))
        return FakeProcess(stdout=[b"hello\n", b"world\n"])

    adapter = ClaudeCodeAdapter(
        command=("claude", "-p"),
        cwd=Path("/tmp/work"),
        process_factory=factory,
    )
    task = _task("task-1", "inspect this repo")

    ack = await adapter.receive_task(task)
    outputs = [output async for output in adapter.stream_output(task.task_id)]

    assert isinstance(adapter, AIAdapter)
    assert ack.status is AckStatus.ACCEPTED
    assert calls == [(("claude", "-p", "inspect this repo"), Path("/tmp/work"))]
    assert _without_timestamps(outputs) == _without_timestamps(
        [
            TaskOutput(task_id="task-1", sequence=0, type=OutputType.TEXT, content="hello\n"),
            TaskOutput(task_id="task-1", sequence=1, type=OutputType.TEXT, content="world\n"),
            TaskOutput(task_id="task-1", sequence=2, type=OutputType.DONE, content=""),
        ]
    )
    assert adapter.status() is AdapterStatus.IDLE


async def test_claude_code_adapter_rejects_second_task_while_busy() -> None:
    wait_event = asyncio.Event()

    async def factory(command: tuple[str, ...], cwd: Path | None) -> FakeProcess:
        _ = (command, cwd)
        return FakeProcess(stdout=[], wait_event=wait_event)

    adapter = ClaudeCodeAdapter(process_factory=factory)

    first_ack = await adapter.receive_task(_task("task-1", "first"))
    second_ack = await adapter.receive_task(_task("task-2", "second"))
    wait_event.set()
    _ = [output async for output in adapter.stream_output("task-1")]

    assert first_ack.status is AckStatus.ACCEPTED
    assert second_ack.status is AckStatus.BUSY
    assert second_ack.reason == "adapter is busy"


async def test_claude_code_adapter_emits_stderr_when_process_fails() -> None:
    async def factory(command: tuple[str, ...], cwd: Path | None) -> FakeProcess:
        _ = (command, cwd)
        return FakeProcess(stdout=[], stderr=[b"bad credentials\n"], return_code=1)

    adapter = ClaudeCodeAdapter(process_factory=factory)

    ack = await adapter.receive_task(_task("task-1", "run"))
    outputs = [output async for output in adapter.stream_output("task-1")]

    assert ack.status is AckStatus.ACCEPTED
    assert len(outputs) == 1
    assert outputs[0].type is OutputType.ERROR
    assert outputs[0].content == "bad credentials"


async def test_claude_code_adapter_interrupt_terminates_running_process() -> None:
    process: FakeProcess | None = None
    wait_event = asyncio.Event()

    async def factory(command: tuple[str, ...], cwd: Path | None) -> FakeProcess:
        nonlocal process
        _ = (command, cwd)
        process = FakeProcess(stdout=[], wait_event=wait_event)
        return process

    adapter = ClaudeCodeAdapter(process_factory=factory)

    await adapter.receive_task(_task("task-1", "long running"))
    await asyncio.sleep(0)
    await adapter.interrupt("task-1")
    outputs = [output async for output in adapter.stream_output("task-1")]

    assert process is not None
    assert process.terminated
    assert outputs[-1].type is OutputType.ERROR
    assert outputs[-1].content == "task interrupted"
    assert adapter.status() is AdapterStatus.IDLE


async def test_claude_code_adapter_unknown_task_stream_reports_error() -> None:
    adapter = ClaudeCodeAdapter()

    outputs = [output async for output in adapter.stream_output("missing")]

    assert len(outputs) == 1
    assert outputs[0].type is OutputType.ERROR
    assert outputs[0].content == "unknown task id"


async def test_claude_code_adapter_health_check_uses_executable_lookup() -> None:
    adapter = ClaudeCodeAdapter(command=(sys.executable,))
    missing = ClaudeCodeAdapter(command=("definitely-missing-aico-command",))

    assert await adapter.health_check() is HealthStatus.OK
    assert await missing.health_check() is HealthStatus.FAILED


def _task(task_id: str, payload: str) -> Task:
    return Task(
        task_id=task_id,
        payload=payload,
        requester_id="user-1",
        target_persona="default",
    )


def _without_timestamps(outputs: list[TaskOutput]) -> list[dict[str, object]]:
    return [output.model_dump(exclude={"timestamp"}) for output in outputs]
