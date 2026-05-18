from aico.adapter.trae import DEFAULT_TRAE_COMMAND, TraeAdapter
from aico.core import (
    Capability,
    ProviderSessionMode,
    ProviderSessionRef,
    Task,
    task_with_provider_session,
)


def test_trae_adapter_uses_print_yolo_defaults() -> None:
    adapter = TraeAdapter()

    assert adapter.name == "trae"
    assert DEFAULT_TRAE_COMMAND == ("trae-cli", "--print", "--yolo")
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


def test_trae_adapter_sets_new_provider_session_id() -> None:
    adapter = TraeAdapter()
    task = task_with_provider_session(
        _task("build it"),
        ProviderSessionRef(provider_name="trae", session_id="session-123"),
        ProviderSessionMode.NEW,
    )

    assert adapter._command_for_task(task) == (  # noqa: SLF001
        *DEFAULT_TRAE_COMMAND,
        "--session-id",
        "session-123",
        "build it",
    )


def test_trae_adapter_resumes_provider_session() -> None:
    adapter = TraeAdapter()
    task = task_with_provider_session(
        _task("continue"),
        ProviderSessionRef(provider_name="trae", session_id="session-123"),
        ProviderSessionMode.RESUME,
    )

    assert adapter._command_for_task(task) == (  # noqa: SLF001
        *DEFAULT_TRAE_COMMAND,
        "--resume",
        "session-123",
        "continue",
    )


def _task(payload: str) -> Task:
    return Task(
        task_id="task-1",
        payload=payload,
        requester_id="user-1",
        target_persona="trae",
    )
