"""No-model live admission probe for the Codex Goal app-server baseline."""

from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import IO, Literal

from pydantic import Field

from aico.core.models import FrozenModel

_MAX_PROTOCOL_LINE_BYTES = 1_048_576
GoalRequest = Callable[[str, dict[str, object]], dict[str, object]]


class CodexGoalStateObservation(FrozenModel):
    thread_id: str = Field(min_length=1, max_length=128)
    status: Literal[
        "active",
        "paused",
        "blocked",
        "usageLimited",
        "budgetLimited",
        "complete",
    ]
    token_budget: int = Field(ge=1)
    tokens_used: int = Field(ge=0)
    time_used_seconds: int = Field(ge=0)


class CodexGoalProtocolReceipt(FrozenModel):
    version: Literal[1] = 1
    codex_cli_version: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=128)
    token_budget: int = Field(ge=1)
    persistent_thread: Literal[True] = True
    approval_policy: Literal["never"] = "never"
    sandbox: Literal["read-only"] = "read-only"
    network_access: Literal[False] = False
    goal_status: Literal["active"] = "active"
    tokens_used: Literal[0] = 0
    time_used_seconds: Literal[0] = 0
    goal_cleared: Literal[True] = True
    thread_deleted: Literal[True] = True
    stale_cleanup_recovered: bool = False
    isolated_codex_home: Literal[True] = True


class CodexGoalCleanupIntent(FrozenModel):
    version: Literal[1] = 1
    thread_id: str = Field(min_length=1, max_length=128)


def probe_codex_goal_protocol(
    *,
    executable: str,
    expected_cli_version: str,
    model: str,
    token_budget: int,
    cwd: Path,
    cleanup_intent_path: Path,
    isolated_home_path: Path,
    timeout_seconds: float = 10,
) -> CodexGoalProtocolReceipt:
    version = _codex_version(executable, timeout_seconds)
    if version != expected_cli_version:
        raise ValueError("Codex Goal probe CLI version does not match frozen contract")
    _prepare_isolated_home(isolated_home_path, stale=cleanup_intent_path.exists())
    connection: _AppServerConnection | None = None
    try:
        recovered = _recover_cleanup_intent(
            executable,
            cleanup_intent_path,
            isolated_home_path=isolated_home_path,
            timeout_seconds=timeout_seconds,
        )
        connection = _AppServerConnection(
            executable,
            isolated_home_path=isolated_home_path,
            timeout_seconds=timeout_seconds,
        )
        connection.initialize()
        receipt = run_goal_lifecycle(
            connection.request,
            codex_cli_version=version,
            model=model,
            token_budget=token_budget,
            cwd=cwd,
            on_thread_started=lambda thread_id: _write_cleanup_intent(
                cleanup_intent_path, thread_id
            ),
            on_thread_deleted=lambda _: _clear_cleanup_intent(cleanup_intent_path),
        )
        return receipt.model_copy(update={"stale_cleanup_recovered": recovered})
    finally:
        if connection is not None:
            connection.close()
        if not cleanup_intent_path.exists() and isolated_home_path.is_dir():
            shutil.rmtree(isolated_home_path)


def observe_codex_goal_state(
    *,
    executable: str,
    codex_home: Path,
    thread_id: str,
    timeout_seconds: float = 10,
) -> CodexGoalStateObservation:
    """Read one persistent Goal without starting a turn or changing its state."""
    connection = _AppServerConnection(
        executable,
        isolated_home_path=codex_home,
        timeout_seconds=timeout_seconds,
    )
    try:
        connection.initialize()
        goal = _mapping(connection.request("thread/goal/get", {"threadId": thread_id}), "goal")
        return CodexGoalStateObservation.model_validate(
            {
                "thread_id": _text(goal, "threadId"),
                "status": _text(goal, "status"),
                "token_budget": _integer(goal, "tokenBudget"),
                "tokens_used": _integer(goal, "tokensUsed", minimum=0),
                "time_used_seconds": _integer(goal, "timeUsedSeconds", minimum=0),
            }
        )
    finally:
        connection.close()


def run_goal_lifecycle(
    request: GoalRequest,
    *,
    codex_cli_version: str,
    model: str,
    token_budget: int,
    cwd: Path,
    on_thread_started: Callable[[str], None] | None = None,
    on_thread_deleted: Callable[[str], None] | None = None,
) -> CodexGoalProtocolReceipt:
    thread_id: str | None = None
    try:
        started = request(
            "thread/start",
            {
                "cwd": str(cwd.resolve()),
                "model": model,
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "ephemeral": False,
            },
        )
        thread = _mapping(started, "thread")
        thread_id = _text(thread, "id")
        if on_thread_started is not None:
            on_thread_started(thread_id)
        if thread.get("ephemeral") is not False:
            raise ValueError("Codex Goal probe requires a persistent thread")
        if started.get("model") != model or started.get("approvalPolicy") != "never":
            raise ValueError("Codex Goal probe thread settings drifted")
        sandbox = _mapping(started, "sandbox")
        if sandbox.get("type") != "readOnly" or sandbox.get("networkAccess") is not False:
            raise ValueError("Codex Goal probe sandbox settings drifted")
        request(
            "thread/goal/set",
            {
                "threadId": thread_id,
                "objective": "AICO benchmark protocol admission probe",
                "status": "active",
                "tokenBudget": token_budget,
            },
        )
        observed = _mapping(request("thread/goal/get", {"threadId": thread_id}), "goal")
        if (
            observed.get("status") != "active"
            or observed.get("tokenBudget") != token_budget
            or observed.get("tokensUsed") != 0
            or observed.get("timeUsedSeconds") != 0
        ):
            raise ValueError("Codex Goal probe usage or goal settings drifted")
        request("thread/goal/clear", {"threadId": thread_id})
        request("thread/delete", {"threadId": thread_id})
        if on_thread_deleted is not None:
            on_thread_deleted(thread_id)
        thread_id = None
        return CodexGoalProtocolReceipt(
            codex_cli_version=codex_cli_version,
            model=model,
            token_budget=token_budget,
        )
    finally:
        if thread_id is not None:
            try:
                request("thread/delete", {"threadId": thread_id})
                if on_thread_deleted is not None:
                    on_thread_deleted(thread_id)
            except (OSError, ValueError):
                pass


class _AppServerConnection:
    def __init__(
        self,
        executable: str,
        *,
        isolated_home_path: Path,
        timeout_seconds: float,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._next_id = 1
        self._notifications: list[dict[str, object]] = []
        self._process = subprocess.Popen(
            (executable, "app-server", "--stdio"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env={**os.environ, "CODEX_HOME": str(isolated_home_path.resolve())},
        )
        if self._process.stdin is None or self._process.stdout is None:
            self.close()
            raise ValueError("Codex Goal app-server pipes are unavailable")
        self._stdin: IO[str] = self._process.stdin
        self._stdout: IO[str] = self._process.stdout

    def initialize(self) -> None:
        self.request(
            "initialize",
            {"clientInfo": {"name": "aico-benchmark", "version": "1"}},
        )
        self._write({"method": "initialized"})

    def request(self, method: str, params: dict[str, object]) -> dict[str, object]:
        request_id = self._next_id
        self._next_id += 1
        self._write({"id": request_id, "method": method, "params": params})
        while True:
            payload = self._read()
            if payload.get("id") != request_id:
                if isinstance(payload.get("method"), str):
                    self._notifications.append(payload)
                continue
            if "error" in payload:
                raise ValueError("Codex Goal app-server rejected the protocol request")
            return _mapping(payload, "result")

    def next_notification(
        self,
        method: str,
        *,
        thread_id: str,
        turn_id: str,
    ) -> dict[str, object]:
        while True:
            for index, payload in enumerate(self._notifications):
                if _matches_notification(payload, method, thread_id, turn_id):
                    return _mapping(self._notifications.pop(index), "params")
            payload = self._read()
            if _matches_notification(payload, method, thread_id, turn_id):
                return _mapping(payload, "params")
            if isinstance(payload.get("method"), str):
                self._notifications.append(payload)
                if len(self._notifications) > 10_000:
                    raise ValueError("Codex Goal app-server notification queue is oversized")

    def close(self) -> None:
        process = self._process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=self._timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=self._timeout_seconds)

    def _write(self, payload: dict[str, object]) -> None:
        try:
            self._stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
            self._stdin.flush()
        except (BrokenPipeError, OSError):
            raise ValueError("Codex Goal app-server connection closed") from None

    def _read(self) -> dict[str, object]:
        ready, _, _ = select.select([self._stdout], [], [], self._timeout_seconds)
        if not ready:
            raise ValueError("Codex Goal app-server response timed out")
        line = self._stdout.readline(_MAX_PROTOCOL_LINE_BYTES + 1)
        if not line or len(line.encode("utf-8")) > _MAX_PROTOCOL_LINE_BYTES:
            raise ValueError("Codex Goal app-server response is missing or oversized")
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            raise ValueError("Codex Goal app-server returned invalid JSON") from None
        if not isinstance(payload, dict):
            raise ValueError("Codex Goal app-server returned an invalid envelope")
        return payload


def _codex_version(executable: str, timeout_seconds: float) -> str:
    try:
        completed = subprocess.run(
            (executable, "--version"),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.SubprocessError):
        raise ValueError("Codex Goal probe could not read the CLI version") from None
    prefix = "codex-cli "
    version = completed.stdout.strip()
    if completed.returncode != 0 or not version.startswith(prefix):
        raise ValueError("Codex Goal probe received an invalid CLI version")
    return version.removeprefix(prefix)


def _recover_cleanup_intent(
    executable: str,
    path: Path,
    *,
    isolated_home_path: Path,
    timeout_seconds: float,
) -> bool:
    if not path.exists():
        return False
    intent = _read_cleanup_intent(path)
    connection = _AppServerConnection(
        executable,
        isolated_home_path=isolated_home_path,
        timeout_seconds=timeout_seconds,
    )
    try:
        connection.initialize()
        connection.request("thread/delete", {"threadId": intent.thread_id})
        _clear_cleanup_intent(path)
        return True
    except (OSError, ValueError):
        raise ValueError(
            "Codex Goal stale probe cleanup is unconfirmed; cleanup intent retained"
        ) from None
    finally:
        connection.close()


def _write_cleanup_intent(path: Path, thread_id: str) -> None:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        output.write(CodexGoalCleanupIntent(thread_id=thread_id).model_dump_json())
        output.write("\n")
    os.chmod(path, 0o600)


def _read_cleanup_intent(path: Path) -> CodexGoalCleanupIntent:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 4_096:
        raise ValueError("Codex Goal cleanup intent is invalid")
    try:
        return CodexGoalCleanupIntent.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise ValueError("Codex Goal cleanup intent is invalid") from None


def _clear_cleanup_intent(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _prepare_isolated_home(path: Path, *, stale: bool) -> None:
    if stale:
        if not path.is_dir() or path.is_symlink():
            raise ValueError("Codex Goal stale cleanup home is missing or unsafe")
        return
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    path.mkdir(mode=0o700, exist_ok=False)


def _mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError("Codex Goal app-server response is missing a required object")
    return value


def _text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError("Codex Goal app-server response is missing a required identifier")
    return value


def _integer(payload: dict[str, object], key: str, *, minimum: int = 1) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"Codex Goal app-server field {key} is invalid")
    return value


def _matches_notification(
    payload: dict[str, object],
    method: str,
    thread_id: str,
    turn_id: str,
) -> bool:
    if payload.get("method") != method:
        return False
    params = payload.get("params")
    if not isinstance(params, dict) or params.get("threadId") != thread_id:
        return False
    if method == "turn/completed":
        turn = params.get("turn")
        return isinstance(turn, dict) and turn.get("id") == turn_id
    return params.get("turnId") == turn_id
