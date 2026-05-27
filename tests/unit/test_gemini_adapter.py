from aico.adapter.claude_code import DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS
from aico.adapter.gemini import DEFAULT_GEMINI_COMMAND, GeminiAdapter
from aico.core import (
    Capability,
    ProviderSessionMode,
    ProviderSessionRef,
    Task,
    task_with_provider_session,
)


def test_gemini_adapter_uses_non_interactive_defaults() -> None:
    adapter = GeminiAdapter()

    assert adapter.name == "gemini"
    assert (  # noqa: SLF001
        adapter._output_idle_timeout_seconds == DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS
    )
    assert DEFAULT_GEMINI_COMMAND == (
        "gemini",
        "--approval-mode",
        "yolo",
        "--output-format",
        "text",
    )
    assert adapter.capabilities() == frozenset(
        {
            Capability.CODE_EDIT,
            Capability.CODE_REVIEW,
            Capability.SHELL_EXEC,
            Capability.LONG_RUNNING,
            Capability.STREAM_OUTPUT,
            Capability.INTERRUPTIBLE,
        }
    )


def test_gemini_adapter_resumes_bound_provider_session() -> None:
    adapter = GeminiAdapter()
    task = task_with_provider_session(
        _task("continue"),
        ProviderSessionRef(provider_name="gemini", session_id="session-5"),
        ProviderSessionMode.RESUME,
    )

    assert adapter._command_for_task(task) == (  # noqa: SLF001
        *DEFAULT_GEMINI_COMMAND,
        "--resume",
        "session-5",
        "continue",
    )


def _task(payload: str) -> Task:
    return Task(
        task_id="task-1",
        payload=payload,
        requester_id="user-1",
        target_persona="gemini",
    )
