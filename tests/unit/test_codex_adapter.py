from aico.adapter.codex import DEFAULT_CODEX_COMMAND, CodexAdapter
from aico.core import (
    Capability,
    OutputType,
    ProviderSessionMode,
    ProviderSessionRef,
    Task,
    task_with_provider_session,
)


class FakeLineReader:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    async def readline(self) -> bytes:
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
    ) -> None:
        self.stdout = FakeLineReader(stdout)
        self.stderr = FakeLineReader(stderr or [])
        self.returncode: int | None = None
        self._return_code = return_code

    def terminate(self) -> None:
        self.returncode = self._return_code

    def kill(self) -> None:
        self.returncode = self._return_code

    async def wait(self) -> int:
        self.returncode = self._return_code
        return self._return_code


def test_codex_adapter_uses_safe_non_interactive_defaults() -> None:
    adapter = CodexAdapter()

    assert adapter.name == "codex"
    assert adapter._output_idle_timeout_seconds == 90.0  # noqa: SLF001
    assert DEFAULT_CODEX_COMMAND == (
        "codex",
        "--ask-for-approval",
        "never",
        "exec",
        "--sandbox",
        "read-only",
        "--color",
        "never",
    )
    assert adapter.capabilities() == frozenset(
        {
            Capability.CODE_REVIEW,
            Capability.LONG_RUNNING,
            Capability.STREAM_OUTPUT,
            Capability.INTERRUPTIBLE,
        }
    )


def test_codex_adapter_builds_exec_resume_command_when_provider_ref_exists() -> None:
    adapter = CodexAdapter()
    task = task_with_provider_session(
        _task("inspect"),
        ProviderSessionRef(
            provider_name="codex",
            session_id="provider-session-1",
            initialized=True,
        ),
        ProviderSessionMode.RESUME,
    )

    assert adapter._command_for_task(task) == (  # noqa: SLF001
        "codex",
        "--ask-for-approval",
        "never",
        "--sandbox",
        "read-only",
        "exec",
        "resume",
        "provider-session-1",
        "inspect",
    )


def test_codex_adapter_does_not_resume_uninitialized_provider_ref() -> None:
    adapter = CodexAdapter(command=("codex", "exec"))
    task = task_with_provider_session(
        _task("inspect"),
        ProviderSessionRef(provider_name="codex", session_id="provider-session-1"),
        ProviderSessionMode.NEW,
    )

    assert adapter._command_for_task(task) == ("codex", "exec", "inspect")  # noqa: SLF001


def test_codex_adapter_ignores_other_provider_session_ref() -> None:
    adapter = CodexAdapter(command=("codex", "exec"))
    task = task_with_provider_session(
        _task("inspect"),
        ProviderSessionRef(
            provider_name="claude-code",
            session_id="provider-session-1",
            initialized=True,
        ),
        ProviderSessionMode.RESUME,
    )

    assert adapter._command_for_task(task) == ("codex", "exec", "inspect")  # noqa: SLF001


def test_codex_adapter_keeps_resume_safe_exec_options() -> None:
    adapter = CodexAdapter(command=("codex", "exec", "--sandbox", "read-only", "--json"))
    task = task_with_provider_session(
        _task("inspect"),
        ProviderSessionRef(
            provider_name="codex",
            session_id="provider-session-1",
            initialized=True,
        ),
        ProviderSessionMode.RESUME,
    )

    assert adapter._command_for_task(task) == (  # noqa: SLF001
        "codex",
        "--sandbox",
        "read-only",
        "exec",
        "resume",
        "--json",
        "provider-session-1",
        "inspect",
    )


async def test_codex_adapter_filters_cli_noise_from_stdout() -> None:
    async def factory(command: tuple[str, ...], cwd: object) -> FakeProcess:
        _ = (command, cwd)
        return FakeProcess(
            stdout=[
                b"2026-05-18T12:13:44.718545Z WARN "
                b"codex_core_plugins::manifest: ignoring interface.defaultPrompt\n",
                b"<html>\n",
                b"Release plan: implementer, tester, reviewer, release-manager.\n",
                b"2026-05-18T12:13:44.804581Z WARN sqlx::query: slow statement\n",
            ]
        )

    adapter = CodexAdapter(command=("codex", "exec"), process_factory=factory)

    ack = await adapter.receive_task(_task("inspect"))
    outputs = [output async for output in adapter.stream_output("task-1")]

    assert ack.status.value == "accepted"
    assert [output.content for output in outputs if output.type is OutputType.TEXT] == [
        "Release plan: implementer, tester, reviewer, release-manager.\n"
    ]


def _task(payload: str) -> Task:
    return Task(
        task_id="task-1",
        payload=payload,
        requester_id="user-1",
        target_persona="reviewer",
    )
