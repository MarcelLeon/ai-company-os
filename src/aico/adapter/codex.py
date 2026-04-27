"""Codex CLI adapter for Phase 2 multi-adapter routing."""

from __future__ import annotations

from pathlib import Path

from aico.adapter.claude_code import ClaudeCodeAdapter, ProcessFactory
from aico.core.models import Capability

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
