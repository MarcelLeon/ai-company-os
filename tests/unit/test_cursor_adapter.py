from aico.adapter.cursor import DEFAULT_CURSOR_COMMAND, CursorAdapter
from aico.core import (
    Capability,
    ProviderSessionMode,
    ProviderSessionRef,
    Task,
    task_with_provider_session,
)


def test_cursor_adapter_uses_non_interactive_print_defaults() -> None:
    adapter = CursorAdapter()

    assert adapter.name == "cursor"
    assert adapter._output_idle_timeout_seconds == 90.0  # noqa: SLF001
    assert DEFAULT_CURSOR_COMMAND == (
        "cursor-agent",
        "-p",
        "--force",
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


def test_cursor_adapter_resumes_bound_provider_session() -> None:
    adapter = CursorAdapter()
    task = task_with_provider_session(
        _task("continue"),
        ProviderSessionRef(provider_name="cursor", session_id="chat-123"),
        ProviderSessionMode.RESUME,
    )

    assert adapter._command_for_task(task) == (  # noqa: SLF001
        *DEFAULT_CURSOR_COMMAND,
        "--resume",
        "chat-123",
        "continue",
    )


def _task(payload: str) -> Task:
    return Task(
        task_id="task-1",
        payload=payload,
        requester_id="user-1",
        target_persona="cursor",
    )
