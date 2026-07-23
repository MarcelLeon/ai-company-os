"""Codex CLI adapter for Phase 2 multi-adapter routing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aico.adapter.claude_code import (
    DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS,
    ClaudeCodeAdapter,
    ProcessFactory,
)
from aico.core.agent_session import ProviderSessionMode, provider_session_from_task
from aico.core.models import Capability, Task, TaskUsage
from aico.core.preauthorized_execution import (
    PreauthorizedExecutionMode,
    preauthorized_execution_mode,
    preauthorized_max_total_tokens,
    preauthorized_model_contract,
)
from aico.core.standing_result import MAX_STANDING_RESULT_CHARS

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
STANDING_RESULT_SCHEMA_PATH = Path(__file__).with_name("schemas") / "standing-result-v1.schema.json"
MIN_PREAUTHORIZED_TOTAL_TOKENS = 16_384
MAX_PREAUTHORIZED_TOTAL_TOKENS = 1_000_000
_PREAUTHORIZED_DISABLED_FEATURES = (
    "shell_tool",
    "unified_exec",
    "multi_agent",
    "apps",
    "browser_use",
    "browser_use_external",
    "computer_use",
    "image_generation",
    "standalone_web_search",
    "search_tool",
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
        self._json_tasks: set[str] = set()
        self._bounded_result_tasks: set[str] = set()
        self._task_usage: dict[str, TaskUsage] = {}

    def capabilities(self) -> frozenset[Capability]:
        return frozenset(
            {
                Capability.CODE_REVIEW,
                Capability.LONG_RUNNING,
                Capability.STREAM_OUTPUT,
                Capability.INTERRUPTIBLE,
            }
        )

    def supports_preauthorized_execution(self, mode: str) -> bool:
        return (
            mode == PreauthorizedExecutionMode.READ_ONLY.value
            and Path(self._command[0]).name == "codex"
            and STANDING_RESULT_SCHEMA_PATH.is_file()
        )

    def supports_preauthorized_budget(self, max_total_tokens: int) -> bool:
        return (
            Path(self._command[0]).name == "codex"
            and MIN_PREAUTHORIZED_TOTAL_TOKENS <= max_total_tokens <= MAX_PREAUTHORIZED_TOTAL_TOKENS
        )

    def supports_preauthorized_model(self, model: str, reasoning_effort: str) -> bool:
        return (
            Path(self._command[0]).name == "codex"
            and bool(model.strip())
            and 0 < len(reasoning_effort) <= 32
            and all(char.isalnum() or char in {"-", "_"} for char in reasoning_effort)
        )

    def task_usage(self, task_id: str) -> TaskUsage | None:
        return self._task_usage.get(task_id)

    def _command_for_task(self, task: Task) -> tuple[str, ...]:
        if preauthorized_execution_mode(task) is not None:
            max_total_tokens = preauthorized_max_total_tokens(task)
            if max_total_tokens is None:
                raise ValueError("preauthorized task is missing a single-run token budget")
            command = _preauthorized_read_only_command(
                self._command[0],
                task.payload,
                max_total_tokens=max_total_tokens,
                model_contract=preauthorized_model_contract(task),
            )
            self._json_tasks.add(task.task_id)
            self._bounded_result_tasks.add(task.task_id)
            return command
        provider_session = provider_session_from_task(task)
        if (
            provider_session is None
            or provider_session.provider_name != self.name
            or provider_session.mode is ProviderSessionMode.NEW
        ):
            command = (*self._command, task.payload)
            if "--json" in command:
                self._json_tasks.add(task.task_id)
            return command

        command = _codex_exec_resume_command(self._command)
        command = (*command, provider_session.session_id, task.payload)
        if "--json" in command:
            self._json_tasks.add(task.task_id)
        return command

    def _process_stdout_line_for_task(self, task_id: str, content: str) -> str | None:
        if task_id not in self._json_tasks:
            return self._process_stdout_line(content)
        try:
            event = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(event, dict):
            return None
        if event.get("type") == "turn.completed":
            usage = _task_usage_from_event(event)
            if usage is not None:
                self._task_usage[task_id] = usage
            return None
        if event.get("type") != "item.completed":
            return None
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "agent_message":
            return None
        text = item.get("text")
        if not isinstance(text, str) or not text:
            return None
        normalized = text if text.endswith("\n") else f"{text}\n"
        if task_id in self._bounded_result_tasks:
            return normalized[: MAX_STANDING_RESULT_CHARS + 1]
        return normalized

    def _process_stdout_line(self, content: str) -> str | None:
        return None if _is_codex_noise(content) else content

    def _process_error_content(self, stderr_text: str, return_code: int) -> str:
        cleaned = "\n".join(
            line for line in stderr_text.splitlines() if not _is_codex_noise(f"{line}\n")
        ).strip()
        if cleaned:
            return cleaned
        return f"Codex exited with code {return_code}"


def _preauthorized_read_only_command(
    executable: str,
    payload: str,
    *,
    max_total_tokens: int,
    model_contract: tuple[str, str] | None = None,
) -> tuple[str, ...]:
    reminder_tokens = max(1, max_total_tokens // 2)
    rollout_budget = (
        "features.rollout_budget={"
        f"limit_tokens={max_total_tokens},"
        f"reminder_at_remaining_tokens=[{reminder_tokens}],"
        "sampling_token_weight=1.0,prefill_token_weight=1.0}"
    )
    disabled_features = tuple(
        part for feature in _PREAUTHORIZED_DISABLED_FEATURES for part in ("--disable", feature)
    )
    model_options: tuple[str, ...] = ()
    if model_contract is not None:
        model, reasoning_effort = model_contract
        model_options = (
            "--model",
            model,
            "-c",
            f'model_reasoning_effort="{reasoning_effort}"',
        )
    return (
        executable,
        "--ask-for-approval",
        "never",
        "--sandbox",
        "read-only",
        *model_options,
        *disabled_features,
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--strict-config",
        "-c",
        rollout_budget,
        "-c",
        f"model_context_window={max_total_tokens}",
        "-c",
        'web_search="disabled"',
        "--output-schema",
        str(STANDING_RESULT_SCHEMA_PATH),
        "--color",
        "never",
        "--json",
        payload,
    )


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


def _task_usage_from_event(event: dict[str, Any]) -> TaskUsage | None:
    usage = event.get("usage")
    if not isinstance(usage, dict):
        return None
    input_tokens = _non_negative_int(usage.get("input_tokens"))
    output_tokens = _non_negative_int(usage.get("output_tokens"))
    if input_tokens is None or output_tokens is None:
        return None
    return TaskUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cached_input_tokens=_non_negative_int(usage.get("cached_input_tokens")) or 0,
        cache_write_input_tokens=(_non_negative_int(usage.get("cache_write_input_tokens")) or 0),
        reasoning_output_tokens=(_non_negative_int(usage.get("reasoning_output_tokens")) or 0),
    )


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value
