"""Codex CLI adapter for Phase 2 multi-adapter routing."""

from __future__ import annotations

from pathlib import Path

from aico.adapter.claude_code import ClaudeCodeAdapter, ProcessFactory
from aico.core.agent_session import ProviderSessionMode, provider_session_from_task
from aico.core.models import Capability, Task

DEFAULT_CODEX_COMMAND = (
    "codex",
    "--ask-for-approval",
    "never",
    "exec",
    "--sandbox",
    "read-only",
    "--color",
    "never",
)


class CodexAdapter(ClaudeCodeAdapter):
    """Run text tasks through Codex CLI in non-interactive mode."""

    def __init__(
        self,
        *,
        command: tuple[str, ...] = DEFAULT_CODEX_COMMAND,
        cwd: Path | None = None,
        process_factory: ProcessFactory | None = None,
        interrupt_timeout_seconds: float = 5.0,
    ) -> None:
        super().__init__(
            adapter_name="codex",
            command=command,
            cwd=cwd,
            process_factory=process_factory,
            interrupt_timeout_seconds=interrupt_timeout_seconds,
        )

    def capabilities(self) -> frozenset[Capability]:
        return frozenset(
            {
                Capability.CODE_REVIEW,
                Capability.LONG_RUNNING,
                Capability.STREAM_OUTPUT,
                Capability.INTERRUPTIBLE,
            }
        )

    def _command_for_task(self, task: Task) -> tuple[str, ...]:
        provider_session = provider_session_from_task(task)
        if provider_session is None or provider_session.mode is ProviderSessionMode.NEW:
            return (*self._command, task.payload)

        command = _codex_exec_resume_command(self._command)
        return (*command, provider_session.session_id, task.payload)


def _codex_exec_resume_command(command: tuple[str, ...]) -> tuple[str, ...]:
    try:
        exec_index = command.index("exec")
    except ValueError:
        return (*command, "resume")

    prefix = list(command[:exec_index])
    tail = command[exec_index + 1 :]
    promoted, resume_options = _split_resume_safe_options(tail)
    return (*prefix, *promoted, "exec", "resume", *resume_options)


def _split_resume_safe_options(
    options: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    promoted: list[str] = []
    resume_options: list[str] = []
    index = 0
    while index < len(options):
        option = options[index]
        if option == "--sandbox" and index + 1 < len(options):
            promoted.extend((option, options[index + 1]))
            index += 2
            continue
        if option == "--color":
            index += 2 if index + 1 < len(options) else 1
            continue
        if option in _RESUME_OPTIONS_WITH_VALUE and index + 1 < len(options):
            resume_options.extend((option, options[index + 1]))
            index += 2
            continue
        if option in _RESUME_FLAG_OPTIONS:
            resume_options.append(option)
        index += 1
    return tuple(promoted), tuple(resume_options)


_RESUME_OPTIONS_WITH_VALUE = {
    "--config",
    "-c",
    "--enable",
    "--disable",
    "--image",
    "-i",
    "--model",
    "-m",
    "--output-last-message",
    "-o",
}
_RESUME_FLAG_OPTIONS = {
    "--full-auto",
    "--dangerously-bypass-approvals-and-sandbox",
    "--skip-git-repo-check",
    "--ephemeral",
    "--ignore-user-config",
    "--ignore-rules",
    "--json",
}
