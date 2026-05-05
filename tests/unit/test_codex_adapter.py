from aico.adapter.codex import DEFAULT_CODEX_COMMAND, CodexAdapter
from aico.core import (
    Capability,
    ProviderSessionMode,
    ProviderSessionRef,
    Task,
    task_with_provider_session,
)


def test_codex_adapter_uses_safe_non_interactive_defaults() -> None:
    adapter = CodexAdapter()

    assert adapter.name == "codex"
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


def _task(payload: str) -> Task:
    return Task(
        task_id="task-1",
        payload=payload,
        requester_id="user-1",
        target_persona="reviewer",
    )
