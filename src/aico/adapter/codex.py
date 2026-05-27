"""Codex CLI adapter for Phase 2 multi-adapter routing."""

from __future__ import annotations

import re
from pathlib import Path

from aico.adapter.claude_code import (
    DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS,
    ClaudeCodeAdapter,
    ProcessFactory,
)
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
        output_idle_timeout_seconds: float | None = DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS,
        max_concurrent_tasks: int = 5,
    ) -> None:
        super().__init__(
            adapter_name="codex",
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
                Capability.CODE_REVIEW,
                Capability.LONG_RUNNING,
                Capability.STREAM_OUTPUT,
                Capability.INTERRUPTIBLE,
            }
        )

    def _command_for_task(self, task: Task) -> tuple[str, ...]:
        provider_session = provider_session_from_task(task)
        if (
            provider_session is None
            or provider_session.provider_name != self.name
            or provider_session.mode is ProviderSessionMode.NEW
        ):
            return (*self._command, task.payload)

        command = _codex_exec_resume_command(self._command)
        return (*command, provider_session.session_id, task.payload)

    def _process_stdout_line(self, content: str) -> str | None:
        return None if _is_codex_noise(content) else content

    def _process_error_content(self, stderr_text: str, return_code: int) -> str:
        cleaned = "\n".join(
            line for line in stderr_text.splitlines() if not _is_codex_noise(f"{line}\n")
        ).strip()
        if cleaned:
            return cleaned
        return f"Codex exited with code {return_code}"


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

_CODEX_TIMESTAMPED_NOISE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\s+(?:WARN|INFO|DEBUG|ERROR)\s+"
)


def _is_codex_noise(content: str) -> bool:
    stripped = content.strip()
    if not stripped:
        return False
    if _CODEX_TIMESTAMPED_NOISE.match(stripped):
        return True
    if stripped.startswith("<") and stripped.endswith(">"):
        return True
    if stripped.lower() in {"<html>", "</html>", "<body>", "</body>", "<head>", "</head>"}:
        return True
    if "codex_core_plugins::manifest:" in stripped:
        return True
    if "sqlx::query:" in stripped:
        return True
    if "thread/resume failed:" in stripped:
        return True
    return False
