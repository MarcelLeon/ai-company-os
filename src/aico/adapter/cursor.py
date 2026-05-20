"""Cursor Agent CLI adapter for optional multi-agent routing."""

from __future__ import annotations

from pathlib import Path

from aico.adapter.claude_code import ClaudeCodeAdapter, ProcessFactory
from aico.core.agent_session import ProviderSessionMode, provider_session_from_task
from aico.core.models import Capability, Task

DEFAULT_CURSOR_COMMAND = (
    "cursor-agent",
    "-p",
    "--force",
    "--output-format",
    "text",
)


class CursorAdapter(ClaudeCodeAdapter):
    """Run text tasks through Cursor Agent CLI print mode."""

    def __init__(
        self,
        *,
        command: tuple[str, ...] = DEFAULT_CURSOR_COMMAND,
        cwd: Path | None = None,
        process_factory: ProcessFactory | None = None,
        interrupt_timeout_seconds: float = 5.0,
        output_idle_timeout_seconds: float | None = 300.0,
        max_concurrent_tasks: int = 5,
    ) -> None:
        super().__init__(
            adapter_name="cursor",
            command=command,
            cwd=cwd,
            process_factory=process_factory,
            interrupt_timeout_seconds=interrupt_timeout_seconds,
            output_idle_timeout_seconds=output_idle_timeout_seconds,
            max_concurrent_tasks=max_concurrent_tasks,
        )

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

    def _command_for_task(self, task: Task) -> tuple[str, ...]:
        provider_session = provider_session_from_task(task)
        if (
            provider_session is None
            or provider_session.mode is ProviderSessionMode.NEW
            or _has_resume_option(self._command)
        ):
            return (*self._command, task.payload)
        return (*self._command, "--resume", provider_session.session_id, task.payload)


def _has_resume_option(command: tuple[str, ...]) -> bool:
    return any(part.startswith("--resume") for part in command)
