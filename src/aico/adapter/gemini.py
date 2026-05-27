"""Gemini CLI adapter for optional multi-agent routing."""

from __future__ import annotations

from pathlib import Path

from aico.adapter.claude_code import (
    DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS,
    ClaudeCodeAdapter,
    ProcessFactory,
)
from aico.core.agent_session import ProviderSessionMode, provider_session_from_task
from aico.core.models import Capability, Task

DEFAULT_GEMINI_COMMAND = (
    "gemini",
    "--approval-mode",
    "yolo",
    "--output-format",
    "text",
)


class GeminiAdapter(ClaudeCodeAdapter):
    """Run text tasks through Gemini CLI non-interactive mode."""

    def __init__(
        self,
        *,
        command: tuple[str, ...] = DEFAULT_GEMINI_COMMAND,
        cwd: Path | None = None,
        process_factory: ProcessFactory | None = None,
        interrupt_timeout_seconds: float = 5.0,
        output_idle_timeout_seconds: float | None = DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS,
        max_concurrent_tasks: int = 5,
    ) -> None:
        super().__init__(
            adapter_name="gemini",
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
            provider_session is not None
            and provider_session.mode is ProviderSessionMode.RESUME
            and "--resume" not in self._command
            and "-r" not in self._command
        ):
            return (*self._command, "--resume", provider_session.session_id, task.payload)
        return (*self._command, task.payload)
