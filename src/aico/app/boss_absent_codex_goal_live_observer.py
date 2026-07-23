"""Independent live evidence for signed Codex Goal host continuation and restart."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from aico.app.boss_absent_codex_goal_capability import (
    CodexGoalNativeHostCandidateReceipt,
)
from aico.app.boss_absent_codex_goal_host import (
    CodexGoalHostAdmissionReceipt,
    CodexGoalHostCapabilities,
    CodexGoalHostKind,
    admit_codex_goal_host,
)
from aico.app.boss_absent_codex_goal_probe import CodexGoalStateObservation
from aico.core.boss_absent_benchmark import canonical_sha256
from aico.core.models import FrozenModel, utc_now

_MAX_SESSION_BYTES = 268_435_456
_MAX_EVENT_LINE_BYTES = 4_194_304
_MAX_SUFFIX_EVENTS = 100_000
_MAX_PS_OUTPUT_BYTES = 8_192
_PS_PATTERN = re.compile(
    r"^\s*(?P<ppid>[0-9]+)\s+"
    r"(?P<started>[A-Z][a-z]{2} [A-Z][a-z]{2}\s+[0-9]{1,2} "
    r"[0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]{4})\s+"
    r"(?P<command>.+)\s*$"
)


class CodexDesktopHostProcessObservation(FrozenModel):
    pid: int = Field(ge=2)
    parent_pid: int = Field(ge=1)
    started_at: datetime
    observed_at: datetime
    command_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parent_command_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    signed_embedded_cli: Literal[True] = True
    codex_desktop_parent: Literal[True] = True

    @model_validator(mode="after")
    def validate_times(self) -> CodexDesktopHostProcessObservation:
        if self.started_at.tzinfo is None or self.observed_at.tzinfo is None:
            raise ValueError("Codex desktop host process timestamps must be timezone-aware")
        if self.started_at > self.observed_at:
            raise ValueError("Codex desktop host process starts after observation")
        return self


class CodexGoalSessionSnapshot(FrozenModel):
    thread_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    device: int = Field(ge=0)
    inode: int = Field(ge=1)
    size_bytes: int = Field(ge=1, le=_MAX_SESSION_BYTES)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_total_tokens: int = Field(ge=0)
    capability_context_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: datetime


class CodexGoalLiveObservationIntent(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    thread_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    session_before: CodexGoalSessionSnapshot
    host_before: CodexDesktopHostProcessObservation
    goal_before: CodexGoalStateObservation
    runner_protocol_writes: Literal[0] = 0
    read_only_goal_queries: Literal[True] = True

    @model_validator(mode="after")
    def validate_identity(self) -> CodexGoalLiveObservationIntent:
        if self.thread_id_sha256 != self.session_before.thread_id_sha256:
            raise ValueError("Codex Goal observation intent session identity drifted")
        if _sha256_text(self.goal_before.thread_id) != self.thread_id_sha256:
            raise ValueError("Codex Goal observation intent Goal identity drifted")
        return self


class CodexGoalNativeContinuationObservation(FrozenModel):
    previous_turn_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    continuation_turn_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    opaque_goal_context_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability_context_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_completed_at: datetime
    continuation_started_at: datetime
    continuation_completed_at: datetime
    automatic_start_delay_ms: int = Field(ge=0, le=5_000)
    source: Literal["codex_internal_goal"] = "codex_internal_goal"
    runner_turn_start_observed: Literal[False] = False


class CodexGoalLiveHostObservationReceipt(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    intent_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    thread_id_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    session_before: CodexGoalSessionSnapshot
    session_after: CodexGoalSessionSnapshot
    host_before: CodexDesktopHostProcessObservation
    host_after: CodexDesktopHostProcessObservation
    continuation: CodexGoalNativeContinuationObservation
    goal_tokens_before: int = Field(ge=0)
    goal_tokens_after: int = Field(ge=1)
    goal_token_delta: int = Field(ge=1)
    provider_tokens_before: int = Field(ge=0)
    provider_tokens_after: int = Field(ge=1)
    provider_token_delta: int = Field(ge=1)
    host_restart_observed: Literal[True] = True
    old_host_terminated: Literal[True] = True
    persistent_session_resumed: Literal[True] = True
    native_continuation_observed: Literal[True] = True
    isolated_run_state_observed: Literal[True] = True
    provider_usage_observed: Literal[True] = True
    goal_usage_observed: Literal[True] = True
    runner_protocol_writes: Literal[0] = 0
    formal_run_admitted: Literal[True] = True

    @model_validator(mode="after")
    def validate_deltas(self) -> CodexGoalLiveHostObservationReceipt:
        if self.goal_tokens_after - self.goal_tokens_before != self.goal_token_delta:
            raise ValueError("Codex Goal live observation Goal usage delta drifted")
        if self.provider_tokens_after - self.provider_tokens_before != self.provider_token_delta:
            raise ValueError("Codex Goal live observation provider usage delta drifted")
        if (
            self.session_before.thread_id_sha256 != self.thread_id_sha256
            or self.session_after.thread_id_sha256 != self.thread_id_sha256
            or self.session_before.device != self.session_after.device
            or self.session_before.inode != self.session_after.inode
            or self.session_after.size_bytes <= self.session_before.size_bytes
        ):
            raise ValueError("Codex Goal live observation session chain drifted")
        if (
            self.host_before.pid == self.host_after.pid
            or self.host_after.started_at <= self.host_before.observed_at
            or self.host_before.command_sha256 != self.host_after.command_sha256
        ):
            raise ValueError("Codex Goal live observation host restart drifted")
        if (
            self.continuation.continuation_started_at < self.host_after.started_at
            or self.continuation.capability_context_sha256
            != self.session_before.capability_context_sha256
        ):
            raise ValueError("Codex Goal live observation continuation boundary drifted")
        return self


def begin_codex_goal_live_observation(
    candidate: CodexGoalNativeHostCandidateReceipt,
    *,
    session_path: Path,
    thread_id: str,
    host: CodexDesktopHostProcessObservation,
    goal: CodexGoalStateObservation,
    observed_at: datetime | None = None,
) -> CodexGoalLiveObservationIntent:
    """Freeze append-only session, host process, and read-only Goal state before restart."""
    now = observed_at or utc_now()
    if goal.thread_id != thread_id or goal.status != "active":
        raise ValueError("Codex Goal live observation requires the active frozen thread")
    if goal.tokens_used > goal.token_budget:
        raise ValueError("Codex Goal live observation starts over budget")
    snapshot, _ = _read_session(session_path, thread_id=thread_id, observed_at=now)
    return CodexGoalLiveObservationIntent(
        contract_sha256=candidate.contract_sha256,
        candidate_receipt_sha256=canonical_sha256(candidate),
        thread_id_sha256=_sha256_text(thread_id),
        session_before=snapshot,
        host_before=host,
        goal_before=goal,
    )


def finalize_codex_goal_live_observation(
    intent: CodexGoalLiveObservationIntent,
    candidate: CodexGoalNativeHostCandidateReceipt,
    *,
    session_path: Path,
    thread_id: str,
    host_after: CodexDesktopHostProcessObservation,
    goal_after: CodexGoalStateObservation,
    old_host_terminated: bool,
    observed_at: datetime | None = None,
) -> CodexGoalLiveHostObservationReceipt:
    """Admit only an append-only same-session continuation after a real host restart."""
    now = observed_at or utc_now()
    _validate_final_identity(intent, candidate, thread_id, host_after, old_host_terminated)
    session_after, suffix = _read_session(
        session_path,
        thread_id=thread_id,
        observed_at=now,
        prefix=intent.session_before,
    )
    continuation = _find_native_continuation(suffix, host_after.started_at)
    if continuation.capability_context_sha256 != intent.session_before.capability_context_sha256:
        raise ValueError("Codex Goal live observation capability context drifted")
    _validate_final_usage(intent, goal_after, session_after)
    return CodexGoalLiveHostObservationReceipt(
        contract_sha256=intent.contract_sha256,
        candidate_receipt_sha256=intent.candidate_receipt_sha256,
        intent_sha256=canonical_sha256(intent),
        thread_id_sha256=intent.thread_id_sha256,
        session_before=intent.session_before,
        session_after=session_after,
        host_before=intent.host_before,
        host_after=host_after,
        continuation=continuation,
        goal_tokens_before=intent.goal_before.tokens_used,
        goal_tokens_after=goal_after.tokens_used,
        goal_token_delta=goal_after.tokens_used - intent.goal_before.tokens_used,
        provider_tokens_before=intent.session_before.provider_total_tokens,
        provider_tokens_after=session_after.provider_total_tokens,
        provider_token_delta=(
            session_after.provider_total_tokens - intent.session_before.provider_total_tokens
        ),
    )


def admit_codex_goal_host_from_live_observation(
    candidate: CodexGoalNativeHostCandidateReceipt,
    observation: CodexGoalLiveHostObservationReceipt,
) -> CodexGoalHostAdmissionReceipt:
    """Translate a complete signed live observation into the existing formal admission."""
    if (
        canonical_sha256(candidate) != observation.candidate_receipt_sha256
        or candidate.contract_sha256 != observation.contract_sha256
    ):
        raise ValueError("Codex Goal live host admission identity drifted")
    host_build = (
        f"{candidate.app_bundle_identifier}/{candidate.app_version}+{candidate.app_build}/"
        f"codex-{candidate.codex_cli_version}"
    )
    return admit_codex_goal_host(
        CodexGoalHostCapabilities(
            contract_sha256=observation.contract_sha256,
            host_build=host_build,
            host_kind=CodexGoalHostKind.NATIVE_CODEX_HOST,
            native_continuation_available=True,
            runner_constructs_continuation_input=False,
            persistent_thread_resume=True,
            isolated_run_state=True,
            provider_usage_observable=True,
            default_capabilities_only=True,
        )
    )


def inspect_codex_desktop_host(
    pid: int,
    *,
    app_bundle: Path,
    embedded_codex: Path,
    observed_at: datetime | None = None,
    timeout_seconds: float = 5,
) -> CodexDesktopHostProcessObservation | None:
    """Read one exact signed desktop app-server process without mutating it."""
    completed = _run_ps(pid, "ppid=,lstart=,command=", timeout_seconds)
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    match = _PS_PATTERN.fullmatch(completed.stdout)
    if match is None:
        raise ValueError("Codex desktop host process output is invalid")
    command = match.group("command")
    expected = (
        str(embedded_codex),
        "-c",
        "features.code_mode_host=true",
        "app-server",
        "--analytics-default-enabled",
    )
    if tuple(shlex.split(command)) != expected:
        raise ValueError("Codex desktop host process command does not match the signed App")
    parent_pid = int(match.group("ppid"))
    parent = _run_ps(parent_pid, "command=", timeout_seconds)
    expected_parent = str(app_bundle / "Contents/MacOS/ChatGPT")
    if parent.returncode != 0 or parent.stdout.strip() != expected_parent:
        raise ValueError("Codex desktop host process parent is not the signed App")
    local_zone = datetime.now().astimezone().tzinfo
    started = datetime.strptime(
        match.group("started"),
        "%a %b %d %H:%M:%S %Y",
    ).replace(tzinfo=local_zone)
    return CodexDesktopHostProcessObservation(
        pid=pid,
        parent_pid=parent_pid,
        started_at=started.astimezone(UTC),
        observed_at=observed_at or utc_now(),
        command_sha256=_sha256_text(command),
        parent_command_sha256=_sha256_text(parent.stdout.strip()),
    )


def _validate_final_identity(
    intent: CodexGoalLiveObservationIntent,
    candidate: CodexGoalNativeHostCandidateReceipt,
    thread_id: str,
    host_after: CodexDesktopHostProcessObservation,
    old_host_terminated: bool,
) -> None:
    if canonical_sha256(candidate) != intent.candidate_receipt_sha256:
        raise ValueError("Codex Goal live observation candidate receipt drifted")
    if candidate.contract_sha256 != intent.contract_sha256:
        raise ValueError("Codex Goal live observation contract drifted")
    if _sha256_text(thread_id) != intent.thread_id_sha256:
        raise ValueError("Codex Goal live observation thread identity drifted")
    if not old_host_terminated or host_after.pid == intent.host_before.pid:
        raise ValueError("Codex Goal live observation did not cross a host restart")
    if host_after.started_at <= intent.host_before.observed_at:
        raise ValueError("Codex Goal replacement host did not start after the intent")
    if host_after.command_sha256 != intent.host_before.command_sha256:
        raise ValueError("Codex Goal replacement host command drifted")


def _validate_final_usage(
    intent: CodexGoalLiveObservationIntent,
    goal_after: CodexGoalStateObservation,
    session_after: CodexGoalSessionSnapshot,
) -> None:
    before = intent.goal_before
    if goal_after.thread_id != before.thread_id or goal_after.token_budget != before.token_budget:
        raise ValueError("Codex Goal live observation Goal contract drifted")
    if goal_after.tokens_used <= before.tokens_used:
        raise ValueError("Codex Goal live observation Goal usage did not advance")
    if goal_after.tokens_used > goal_after.token_budget:
        raise ValueError("Codex Goal live observation exceeded its frozen token budget")
    if session_after.provider_total_tokens <= intent.session_before.provider_total_tokens:
        raise ValueError("Codex Goal live observation provider usage did not advance")


def _read_session(
    path: Path,
    *,
    thread_id: str,
    observed_at: datetime,
    prefix: CodexGoalSessionSnapshot | None = None,
) -> tuple[CodexGoalSessionSnapshot, tuple[dict[str, object], ...]]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("Codex Goal live session path is unsafe")
    stat = path.stat()
    if stat.st_size < 1 or stat.st_size > _MAX_SESSION_BYTES:
        raise ValueError("Codex Goal live session size is invalid")
    with path.open("rb") as source:
        payload = source.read(stat.st_size)
    if len(payload) != stat.st_size or not payload.endswith(b"\n"):
        raise ValueError("Codex Goal live session snapshot is incomplete")
    if prefix is not None:
        _validate_prefix(prefix, stat.st_dev, stat.st_ino, payload)
    start = 0 if prefix is None else prefix.size_bytes
    events = _parse_events(payload[start:])
    first_line = payload.split(b"\n", 1)[0]
    meta_events = _parse_events(first_line + b"\n")
    _validate_session_meta(meta_events, thread_id)
    provider_tokens = _last_provider_tokens(events)
    if provider_tokens is None and prefix is not None:
        provider_tokens = prefix.provider_total_tokens
    if provider_tokens is None:
        provider_tokens = 0
    capability_context = _last_capability_context(events)
    if capability_context is None and prefix is not None:
        capability_context = prefix.capability_context_sha256
    if capability_context is None:
        raise ValueError("Codex Goal live session capability context is missing")
    snapshot = CodexGoalSessionSnapshot(
        thread_id_sha256=_sha256_text(thread_id),
        device=stat.st_dev,
        inode=stat.st_ino,
        size_bytes=stat.st_size,
        content_sha256=hashlib.sha256(payload).hexdigest(),
        provider_total_tokens=provider_tokens,
        capability_context_sha256=capability_context,
        observed_at=observed_at,
    )
    return snapshot, events


def _validate_prefix(
    prefix: CodexGoalSessionSnapshot,
    device: int,
    inode: int,
    payload: bytes,
) -> None:
    if device != prefix.device or inode != prefix.inode or len(payload) <= prefix.size_bytes:
        raise ValueError("Codex Goal live session was replaced or did not grow")
    if hashlib.sha256(payload[: prefix.size_bytes]).hexdigest() != prefix.content_sha256:
        raise ValueError("Codex Goal live session prefix was rewritten")


def _parse_events(payload: bytes) -> tuple[dict[str, object], ...]:
    if not payload:
        return ()
    lines = payload.splitlines()
    if len(lines) > _MAX_SUFFIX_EVENTS:
        raise ValueError("Codex Goal live session event slice is oversized")
    events: list[dict[str, object]] = []
    for line in lines:
        if not line or len(line) > _MAX_EVENT_LINE_BYTES:
            raise ValueError("Codex Goal live session event line is invalid")
        try:
            event = json.loads(line)
        except (UnicodeError, json.JSONDecodeError):
            raise ValueError("Codex Goal live session event JSON is invalid") from None
        if not isinstance(event, dict):
            raise ValueError("Codex Goal live session event envelope is invalid")
        events.append(event)
    return tuple(events)


def _validate_session_meta(events: tuple[dict[str, object], ...], thread_id: str) -> None:
    if not events:
        raise ValueError("Codex Goal live session metadata is missing")
    event = events[0]
    payload = event.get("payload")
    if (
        event.get("type") != "session_meta"
        or not isinstance(payload, dict)
        or payload.get("id") != thread_id
        or payload.get("originator") != "Codex Desktop"
    ):
        raise ValueError("Codex Goal live session metadata does not match the desktop thread")


def _last_provider_tokens(events: tuple[dict[str, object], ...]) -> int | None:
    observed: int | None = None
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "token_count":
            continue
        info = payload.get("info")
        usage = info.get("total_token_usage") if isinstance(info, dict) else None
        value = usage.get("total_tokens") if isinstance(usage, dict) else None
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("Codex Goal live session provider usage is invalid")
        if observed is not None and value < observed:
            raise ValueError("Codex Goal live session provider usage regressed")
        observed = value
    return observed


def _last_capability_context(events: tuple[dict[str, object], ...]) -> str | None:
    observed: str | None = None
    for event in events:
        payload = event.get("payload")
        if event.get("type") == "turn_context" and isinstance(payload, dict):
            observed = _capability_context_sha256(payload)
    return observed


def _capability_context_sha256(payload: dict[str, object]) -> str:
    keys = (
        "model",
        "effort",
        "approval_policy",
        "approvals_reviewer",
        "sandbox_policy",
        "collaboration_mode",
        "multi_agent_mode",
        "multi_agent_version",
        "workspace_roots",
    )
    selected = {key: payload.get(key) for key in keys}
    if any(value is None for value in selected.values()):
        raise ValueError("Codex Goal live session capability context is incomplete")
    encoded = json.dumps(selected, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _find_native_continuation(
    events: tuple[dict[str, object], ...],
    host_started_at: datetime,
) -> CodexGoalNativeContinuationObservation:
    for index in range(len(events) - 3):
        transition = _transition_at(events, index, host_started_at)
        if transition is not None:
            return transition
    raise ValueError("Codex Goal live session lacks a completed native continuation")


def _transition_at(
    events: tuple[dict[str, object], ...],
    index: int,
    host_started_at: datetime,
) -> CodexGoalNativeContinuationObservation | None:
    completed, started, context, message = events[index : index + 4]
    completed_turn = _event_turn(completed, "task_complete")
    started_turn = _event_turn(started, "task_started")
    context_payload = context.get("payload")
    if (
        completed_turn is None
        or started_turn is None
        or not isinstance(context_payload, dict)
        or context.get("type") != "turn_context"
        or context_payload.get("turn_id") != started_turn
    ):
        return None
    goal_context = _goal_context(message, started_turn)
    if goal_context is None:
        return None
    completed_at = _event_time(completed)
    started_at = _event_time(started)
    if started_at < host_started_at or started_at < completed_at:
        return None
    delay_ms = round((started_at - completed_at).total_seconds() * 1_000)
    continuation_completed_at = _find_turn_completion(events[index + 4 :], started_turn)
    if continuation_completed_at is None:
        return None
    return CodexGoalNativeContinuationObservation(
        previous_turn_sha256=_sha256_text(completed_turn),
        continuation_turn_sha256=_sha256_text(started_turn),
        opaque_goal_context_sha256=hashlib.sha256(goal_context.encode()).hexdigest(),
        capability_context_sha256=_capability_context_sha256(context_payload),
        previous_completed_at=completed_at,
        continuation_started_at=started_at,
        continuation_completed_at=continuation_completed_at,
        automatic_start_delay_ms=delay_ms,
    )


def _goal_context(event: dict[str, object], turn_id: str) -> str | None:
    payload = event.get("payload")
    if (
        event.get("type") != "response_item"
        or not isinstance(payload, dict)
        or payload.get("type") != "message"
        or payload.get("role") != "user"
    ):
        return None
    metadata = payload.get("internal_chat_message_metadata_passthrough")
    if not isinstance(metadata, dict) or metadata.get("turn_id") != turn_id:
        return None
    content = payload.get("content")
    if not isinstance(content, list):
        return None
    text = "".join(
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and item.get("type") == "input_text"
    )
    marker = '<codex_internal_context source="goal">'
    return text if text.startswith(marker) and text.endswith("</codex_internal_context>") else None


def _find_turn_completion(
    events: tuple[dict[str, object], ...],
    turn_id: str,
) -> datetime | None:
    for event in events:
        if _event_turn(event, "task_complete") == turn_id:
            return _event_time(event)
    return None


def _event_turn(event: dict[str, object], event_type: str) -> str | None:
    payload = event.get("payload")
    if (
        event.get("type") != "event_msg"
        or not isinstance(payload, dict)
        or payload.get("type") != event_type
    ):
        return None
    turn_id = payload.get("turn_id")
    return turn_id if isinstance(turn_id, str) and turn_id else None


def _event_time(event: dict[str, object]) -> datetime:
    value = event.get("timestamp")
    if not isinstance(value, str):
        raise ValueError("Codex Goal live session event timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Codex Goal live session event timestamp is invalid") from None
    if parsed.tzinfo is None:
        raise ValueError("Codex Goal live session event timestamp is not timezone-aware")
    return parsed


def _run_ps(
    pid: int,
    fields: str,
    timeout_seconds: float,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            ("ps", "-p", str(pid), "-o", fields),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.SubprocessError):
        raise ValueError("Codex desktop host process inspection failed") from None
    if len(completed.stdout.encode()) + len(completed.stderr.encode()) > _MAX_PS_OUTPUT_BYTES:
        raise ValueError("Codex desktop host process output is oversized")
    return completed


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
