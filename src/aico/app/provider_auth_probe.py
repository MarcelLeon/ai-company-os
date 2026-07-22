"""Constrained live authentication probes for supported AI provider CLIs."""

from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from aico.app.runtime_reinjection import ProviderName

_MAX_STREAM_BYTES = 256 * 1024
_DEFAULT_TIMEOUT_SECONDS = 90.0
_PROVIDER_EXECUTABLES = {
    "claude-code": "claude",
    "codex": "codex",
    "cursor": "cursor-agent",
    "codeflicker": "flickcli",
    "trae": "trae-cli",
    "gemini": "gemini",
}


class ProviderAuthenticationProbeError(RuntimeError):
    """A provider could not produce safe, affirmative live-auth evidence."""


class ProviderProbeResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    terminal_success: Literal[True] = True
    exact_challenge_response: Literal[True] = True
    usage_observed: Literal[True] = True


class ProviderAuthenticationProbe(Protocol):
    """Plugin boundary for provider-specific live authentication evidence."""

    def execute(self, challenge: str) -> ProviderProbeResult: ...


class CliProviderAuthenticationProbe:
    """Run one supported CLI in a private, tool-free, non-persistent environment."""

    def __init__(
        self,
        provider: ProviderName,
        configured_command: str,
        *,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._provider = provider
        self._executable = validated_provider_executable(provider, configured_command)
        self._timeout_seconds = timeout_seconds

    def execute(self, challenge: str) -> ProviderProbeResult:
        command = _probe_command(self._provider, self._executable, challenge)
        output = _run_bounded(command, timeout_seconds=self._timeout_seconds)
        if self._provider == "claude-code":
            valid = _parse_claude_result(output, challenge)
        elif self._provider == "codex":
            valid = _parse_codex_result(output, challenge)
        else:
            raise ProviderAuthenticationProbeError("provider has no approved live-auth probe")
        if not valid:
            raise ProviderAuthenticationProbeError("provider live-auth evidence is invalid")
        return ProviderProbeResult()


def build_cli_provider_probe(
    provider: ProviderName,
    configured_command: str,
) -> ProviderAuthenticationProbe:
    if provider not in {"claude-code", "codex"}:
        raise ProviderAuthenticationProbeError("provider has no approved live-auth probe")
    return CliProviderAuthenticationProbe(provider, configured_command)


def validated_provider_executable(provider: ProviderName, configured_command: str) -> str:
    try:
        parts = shlex.split(configured_command)
    except ValueError:
        raise ProviderAuthenticationProbeError("provider command is invalid") from None
    expected = _PROVIDER_EXECUTABLES[provider]
    if not parts or Path(parts[0]).name != expected:
        raise ProviderAuthenticationProbeError("provider command executable is not approved")
    return parts[0]


def _probe_command(provider: ProviderName, executable: str, challenge: str) -> tuple[str, ...]:
    prompt = (
        "Authentication probe. Return exactly the token below and nothing else. "
        f"Do not use tools.\n{challenge}"
    )
    if provider == "claude-code":
        return (
            executable,
            "-p",
            "--safe-mode",
            "--no-session-persistence",
            "--no-chrome",
            "--tools",
            "",
            "--permission-mode",
            "dontAsk",
            "--output-format",
            "json",
            prompt,
        )
    if provider == "codex":
        return (
            executable,
            "--ask-for-approval",
            "never",
            "exec",
            "--sandbox",
            "read-only",
            "--ignore-user-config",
            "--ignore-rules",
            "--ephemeral",
            "--strict-config",
            "--skip-git-repo-check",
            "--color",
            "never",
            "--json",
            prompt,
        )
    raise ProviderAuthenticationProbeError("provider has no approved live-auth probe")


def _run_bounded(command: tuple[str, ...], *, timeout_seconds: float) -> bytes:
    child_env = {key: value for key, value in os.environ.items() if not key.startswith("AICO_")}
    try:
        with tempfile.TemporaryDirectory(prefix="aico-provider-auth-") as raw:
            directory = Path(raw)
            directory.chmod(0o700)
            stdout_path = directory / "stdout"
            stderr_path = directory / "stderr"
            with stdout_path.open("w+b") as stdout, stderr_path.open("w+b") as stderr:
                process = subprocess.Popen(
                    command,
                    cwd=directory,
                    env=child_env,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=True,
                )
                _wait_bounded(process, stdout_path, stderr_path, timeout_seconds)
                if process.returncode != 0:
                    raise ProviderAuthenticationProbeError("provider live-auth probe failed")
                stdout.flush()
                return stdout_path.read_bytes()
    except ProviderAuthenticationProbeError:
        raise
    except (OSError, subprocess.SubprocessError):
        raise ProviderAuthenticationProbeError("provider live-auth probe failed") from None


def _wait_bounded(
    process: subprocess.Popen[bytes],
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while process.poll() is None:
        if time.monotonic() >= deadline:
            _terminate(process)
            raise ProviderAuthenticationProbeError("provider live-auth probe timed out")
        if _too_large(stdout_path) or _too_large(stderr_path):
            _terminate(process)
            raise ProviderAuthenticationProbeError("provider live-auth output exceeded limit")
        time.sleep(0.02)
    if _too_large(stdout_path) or _too_large(stderr_path):
        raise ProviderAuthenticationProbeError("provider live-auth output exceeded limit")


def _terminate(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)


def _too_large(path: Path) -> bool:
    try:
        return path.stat().st_size > _MAX_STREAM_BYTES
    except OSError:
        return True


def _parse_claude_result(payload: bytes, challenge: str) -> bool:
    try:
        document = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError):
        return False
    return (
        isinstance(document, dict)
        and document.get("result") == challenge
        and document.get("is_error") is not True
        and _usage_observed(document.get("usage"))
    )


def _parse_codex_result(payload: bytes, challenge: str) -> bool:
    response: str | None = None
    usage = False
    try:
        for raw_line in payload.splitlines():
            event = json.loads(raw_line)
            if not isinstance(event, dict):
                return False
            if event.get("type") == "item.completed":
                item = event.get("item")
                if isinstance(item, dict) and item.get("type") == "agent_message":
                    response = item.get("text") if isinstance(item.get("text"), str) else None
            elif event.get("type") == "turn.completed":
                usage = _usage_observed(event.get("usage"))
    except (UnicodeError, json.JSONDecodeError):
        return False
    return response == challenge and usage


def _usage_observed(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    return any(
        isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in value.values()
    )
