from pathlib import Path

from aico.adapter.codeflicker import DEFAULT_CODEFLICKER_COMMAND, CodeFlickerAdapter
from aico.core import (
    Capability,
    ProviderSessionMode,
    ProviderSessionRef,
    Task,
    task_with_provider_session,
)


def test_codeflicker_adapter_uses_safe_quiet_defaults() -> None:
    adapter = CodeFlickerAdapter()

    assert adapter.name == "codeflicker"
    assert adapter._output_idle_timeout_seconds == 90.0  # noqa: SLF001
    assert DEFAULT_CODEFLICKER_COMMAND == (
        "flickcli",
        "-q",
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


def test_codeflicker_adapter_adds_cwd_before_prompt() -> None:
    adapter = CodeFlickerAdapter(cwd=Path("/repo/aico"))

    assert adapter._command_for_task(_task("inspect")) == (  # noqa: SLF001
        *DEFAULT_CODEFLICKER_COMMAND,
        "--cwd",
        "/repo/aico",
        "inspect",
    )


def test_codeflicker_adapter_keeps_explicit_cwd() -> None:
    adapter = CodeFlickerAdapter(command=("flickcli", "-q", "--cwd", "/tmp/work"))

    assert adapter._command_for_task(_task("inspect")) == (  # noqa: SLF001
        "flickcli",
        "-q",
        "--cwd",
        "/tmp/work",
        "inspect",
    )


def test_codeflicker_adapter_resumes_provider_session() -> None:
    adapter = CodeFlickerAdapter()
    task = task_with_provider_session(
        _task("continue"),
        ProviderSessionRef(provider_name="codeflicker", session_id="session-123"),
        ProviderSessionMode.RESUME,
    )

    assert adapter._command_for_task(task) == (  # noqa: SLF001
        *DEFAULT_CODEFLICKER_COMMAND,
        "--resume",
        "session-123",
        "continue",
    )


def _task(payload: str) -> Task:
    return Task(
        task_id="task-1",
        payload=payload,
        requester_id="user-1",
        target_persona="codeflicker",
    )
