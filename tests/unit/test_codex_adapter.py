import json
from datetime import UTC, datetime

from aico.adapter.claude_code import DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS
from aico.adapter.codex import (
    DEFAULT_CODEX_COMMAND,
    STANDING_RESULT_SCHEMA_PATH,
    CodexAdapter,
)
from aico.core import (
    Capability,
    OutputType,
    ProviderSessionMode,
    ProviderSessionRef,
    Task,
    task_with_provider_session,
)
from aico.core.collaboration import task_with_exact_output_constraint
from aico.core.preauthorized_execution import task_with_preauthorized_execution
from aico.core.standing_result import MAX_STANDING_RESULT_CHARS


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
    assert (  # noqa: SLF001
        adapter._output_idle_timeout_seconds == DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS
    )
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


def test_codex_adapter_forces_ephemeral_read_only_command_for_preauthorized_task() -> None:
    adapter = CodexAdapter(
        command=(
            "codex",
            "--dangerously-bypass-approvals-and-sandbox",
            "exec",
            "--search",
            "--sandbox",
            "danger-full-access",
        )
    )
    task = task_with_exact_output_constraint(_task("Inspect recovery evidence."))
    task = task_with_preauthorized_execution(
        task,
        grant_id="grant-1",
        expires_at=datetime(2027, 1, 1, tzinfo=UTC),
        max_duration_seconds=60,
        max_total_tokens=50_000,
    )

    assert adapter.supports_preauthorized_execution("read_only") is True
    assert adapter.supports_preauthorized_budget(50_000) is True
    assert adapter._command_for_task(task) == (  # noqa: SLF001
        "codex",
        "--ask-for-approval",
        "never",
        "--sandbox",
        "read-only",
        "--disable",
        "shell_tool",
        "--disable",
        "unified_exec",
        "--disable",
        "multi_agent",
        "--disable",
        "apps",
        "--disable",
        "browser_use",
        "--disable",
        "browser_use_external",
        "--disable",
        "computer_use",
        "--disable",
        "image_generation",
        "--disable",
        "standalone_web_search",
        "--disable",
        "search_tool",
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--strict-config",
        "-c",
        "features.rollout_budget={limit_tokens=50000,reminder_at_remaining_tokens=[25000],sampling_token_weight=1.0,prefill_token_weight=1.0}",
        "-c",
        "model_context_window=50000",
        "-c",
        'web_search="disabled"',
        "--output-schema",
        str(STANDING_RESULT_SCHEMA_PATH),
        "--color",
        "never",
        "--json",
        task.payload,
    )
    assert STANDING_RESULT_SCHEMA_PATH.is_file()


def test_codex_adapter_binds_exact_model_and_effort_for_benchmark_task() -> None:
    adapter = CodexAdapter(command=("codex", "exec"))
    task = task_with_exact_output_constraint(_task("Inspect frozen evidence."))
    task = task_with_preauthorized_execution(
        task,
        grant_id="benchmark-dispatch",
        expires_at=datetime(2027, 1, 1, tzinfo=UTC),
        max_duration_seconds=60,
        max_total_tokens=50_000,
        model="gpt-5.6-sol",
        reasoning_effort="high",
    )

    command = adapter._command_for_task(task)  # noqa: SLF001

    assert adapter.supports_preauthorized_model("gpt-5.6-sol", "high")
    assert command[command.index("--model") + 1] == "gpt-5.6-sol"
    assert 'model_reasoning_effort="high"' in command


def test_codex_adapter_refuses_preauthorized_mode_for_non_codex_executable() -> None:
    adapter = CodexAdapter(command=("custom-provider-wrapper", "exec"))

    assert adapter.supports_preauthorized_execution("read_only") is False


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


async def test_codex_adapter_extracts_json_message_and_post_run_usage() -> None:
    async def factory(command: tuple[str, ...], cwd: object) -> FakeProcess:
        _ = (command, cwd)
        return FakeProcess(
            stdout=[
                b'{"type":"thread.started","thread_id":"thread-1"}\n',
                b'{"type":"item.completed","item":{"id":"item-1",'
                b'"type":"agent_message","text":"inspection complete"}}\n',
                b'{"type":"turn.completed","usage":{"input_tokens":80,'
                b'"cached_input_tokens":40,"cache_write_input_tokens":10,'
                b'"output_tokens":20,"reasoning_output_tokens":12}}\n',
            ]
        )

    adapter = CodexAdapter(command=("codex", "exec", "--json"), process_factory=factory)

    await adapter.receive_task(_task("inspect"))
    outputs = [output async for output in adapter.stream_output("task-1")]

    assert [output.content for output in outputs if output.type is OutputType.TEXT] == [
        "inspection complete\n"
    ]
    assert adapter.task_usage("task-1") is not None
    assert adapter.task_usage("task-1").model_dump() == {  # type: ignore[union-attr]
        "input_tokens": 80,
        "output_tokens": 20,
        "total_tokens": 100,
        "cached_input_tokens": 40,
        "cache_write_input_tokens": 10,
        "reasoning_output_tokens": 12,
    }


async def test_codex_adapter_bounds_preauthorized_final_message() -> None:
    oversized = "x" * (MAX_STANDING_RESULT_CHARS + 100)

    async def factory(command: tuple[str, ...], cwd: object) -> FakeProcess:
        _ = (command, cwd)
        event = {
            "type": "item.completed",
            "item": {"id": "item-1", "type": "agent_message", "text": oversized},
        }
        return FakeProcess(stdout=[f"{json.dumps(event)}\n".encode()])

    adapter = CodexAdapter(process_factory=factory)
    task = task_with_exact_output_constraint(_task("Inspect recovery evidence."))
    task = task_with_preauthorized_execution(
        task,
        grant_id="grant-1",
        expires_at=datetime(2027, 1, 1, tzinfo=UTC),
        max_duration_seconds=60,
        max_total_tokens=50_000,
    )

    await adapter.receive_task(task)
    outputs = [output async for output in adapter.stream_output(task.task_id)]
    text_outputs = [output.content for output in outputs if output.type is OutputType.TEXT]

    assert len(text_outputs) == 1
    assert len(text_outputs[0]) == MAX_STANDING_RESULT_CHARS + 1


def _task(payload: str) -> Task:
    return Task(
        task_id="task-1",
        payload=payload,
        requester_id="user-1",
        target_persona="reviewer",
    )
