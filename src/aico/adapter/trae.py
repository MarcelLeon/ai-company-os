"""Trae CLI adapter for optional multi-agent routing."""

from __future__ import annotations

from pathlib import Path

from aico.adapter.claude_code import ClaudeCodeAdapter, ProcessFactory
from aico.core.agent_session import ProviderSessionMode, provider_session_from_task
from aico.core.models import Capability, Task

DEFAULT_TRAE_COMMAND = (
    "trae-cli",
    "--print",
    "--yolo",
)


class TraeAdapter(ClaudeCodeAdapter):
    """Run text tasks through Trae CLI print mode."""

    def __init__(
        self,
        *,
        command: tuple[str, ...] = DEFAULT_TRAE_COMMAND,
        cwd: Path | None = None,
        process_factory: ProcessFactory | None = None,
        interrupt_timeout_seconds: float = 5.0,
        output_idle_timeout_seconds: float | None = 90.0,
    ) -> None:
        super().__init__(
            adapter_name="trae",
            command=command,
            cwd=cwd,
            process_factory=process_factory,
            interrupt_timeout_seconds=interrupt_timeout_seconds,
            output_idle_timeout_seconds=output_idle_timeout_seconds,
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
        command = self._command
        provider_session = provider_session_from_task(task)
        if provider_session is None:
            return (*command, task.payload)
        if provider_session.mode is ProviderSessionMode.NEW and "--session-id" not in command:
            return (*command, "--session-id", provider_session.session_id, task.payload)
        if provider_session.mode is ProviderSessionMode.RESUME and "--resume" not in command:
            return (*command, "--resume", provider_session.session_id, task.payload)
        return (*command, task.payload)
