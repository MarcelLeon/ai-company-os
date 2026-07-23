"""Derive a Codex Goal host-run ledger from native desktop session evidence."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Literal, TypeVar, cast

from pydantic import BaseModel, Field, model_validator

from aico.app.boss_absent_codex_goal_host import (
    CodexGoalHostAdmissionReceipt,
    CodexGoalHostRunReceipt,
    CodexGoalHostTurnReceipt,
    CodexGoalTurnSource,
)
from aico.app.boss_absent_codex_goal_live_observer import (
    CodexDesktopHostProcessObservation,
)
from aico.app.boss_absent_codex_goal_probe import CodexGoalStateObservation
from aico.core.boss_absent_benchmark import (
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    canonical_sha256,
)
from aico.core.models import FrozenModel, utc_now

_MAX_SESSION_BYTES = 268_435_456
_MAX_EVENT_LINE_BYTES = 4_194_304
_MAX_SESSION_EVENTS = 200_000
_INITIAL_OPEN = "<aico_boss_absent_initial_task>"
_INITIAL_CLOSE = "</aico_boss_absent_initial_task>"
_OWNER_OPEN = "<aico_boss_absent_owner_decision>"
_OWNER_CLOSE = "</aico_boss_absent_owner_decision>"
_GOAL_OPEN = '<codex_internal_context source="goal">'
_GOAL_CLOSE = "</codex_internal_context>"
Sha256 = str
ModelT = TypeVar("ModelT", bound=BaseModel)


class CodexGoalInitialTaskEnvelope(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    task_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    task: BossAbsentTask

    def as_marked_text(self) -> str:
        return f"{_INITIAL_OPEN}{self.model_dump_json()}{_INITIAL_CLOSE}"


class CodexGoalOwnerDecisionEnvelope(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    decision_receipt_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")

    def as_marked_text(self) -> str:
        return f"{_OWNER_OPEN}{self.model_dump_json()}{_OWNER_CLOSE}"


class CodexGoalHostRunSessionAnchor(FrozenModel):
    device: int = Field(ge=0)
    inode: int = Field(ge=1)
    size_bytes: int = Field(ge=1, le=_MAX_SESSION_BYTES)
    content_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    provider_total_tokens: int = Field(ge=0)
    observed_at: datetime

    @model_validator(mode="after")
    def validate_time(self) -> CodexGoalHostRunSessionAnchor:
        if self.observed_at.tzinfo is None:
            raise ValueError("Codex Goal host-run anchor timestamp must be timezone-aware")
        return self


class CodexGoalHostRunObservationIntent(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    task_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    host_admission_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    thread_id_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    session_before: CodexGoalHostRunSessionAnchor
    goal_token_budget: int = Field(ge=1)
    goal_tokens_before: Literal[0] = 0
    runner_turn_start_writes: Literal[0] = 0


class CodexGoalHostRunObservationReceipt(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    task_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    host_admission_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    intent_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    thread_id_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    session_before: CodexGoalHostRunSessionAnchor
    session_after_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    session_after_size_bytes: int = Field(ge=1, le=_MAX_SESSION_BYTES)
    runtime_observations: tuple[CodexDesktopHostProcessObservation, ...] = Field(
        min_length=1,
        max_length=256,
    )
    provider_tokens_before: int = Field(ge=0)
    provider_tokens_after: int = Field(ge=1)
    goal_tokens_after: int = Field(ge=1)
    host_run: CodexGoalHostRunReceipt
    observer_kind: Literal["native_codex_session"] = "native_codex_session"
    runner_turn_start_writes: Literal[0] = 0

    @model_validator(mode="after")
    def validate_receipt(self) -> CodexGoalHostRunObservationReceipt:
        identity = (
            self.contract_sha256 == self.host_run.contract_sha256
            and self.host_admission_sha256 == self.host_run.host_admission_sha256
            and self.session_before.provider_total_tokens == self.provider_tokens_before
            and self.provider_tokens_after - self.provider_tokens_before
            == self.host_run.total_tokens
            and self.goal_tokens_after == self.host_run.total_tokens
            and self.session_after_size_bytes > self.session_before.size_bytes
        )
        if not identity:
            raise ValueError("Codex Goal host-run observation receipt drifted")
        return self


class _SessionSlice:
    def __init__(
        self,
        payload: bytes,
        suffix: tuple[dict[str, object], ...],
        *,
        device: int,
        inode: int,
    ) -> None:
        self.payload = payload
        self.suffix = suffix
        self.device = device
        self.inode = inode


class _ObservedTurn:
    def __init__(
        self,
        *,
        turn_id: str,
        source: CodexGoalTurnSource,
        opaque_input_sha256: str,
        provider_total_after: int,
        started_at: datetime,
        completed_at: datetime,
    ) -> None:
        self.turn_id = turn_id
        self.source = source
        self.opaque_input_sha256 = opaque_input_sha256
        self.provider_total_after = provider_total_after
        self.started_at = started_at
        self.completed_at = completed_at


def begin_codex_goal_host_run_observation(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
    goal: CodexGoalStateObservation,
    *,
    codex_home: Path,
    session_path: Path,
    thread_id: str,
    observed_at: datetime | None = None,
) -> CodexGoalHostRunObservationIntent:
    """Freeze a zero-usage native Goal run before the initial benchmark turn."""
    _validate_identity(contract, task, admission)
    if (
        goal.thread_id != thread_id
        or goal.status != "active"
        or goal.token_budget != contract.max_total_tokens
        or goal.tokens_used != 0
    ):
        raise ValueError("Codex Goal host-run observation must start at frozen zero usage")
    session = _read_session(codex_home, session_path, thread_id=thread_id)
    return CodexGoalHostRunObservationIntent(
        contract_sha256=canonical_sha256(contract),
        task_sha256=canonical_sha256(task),
        host_admission_sha256=canonical_sha256(admission),
        thread_id_sha256=_domain_sha("codex-thread-v1", thread_id),
        session_before=CodexGoalHostRunSessionAnchor(
            device=session.device,
            inode=session.inode,
            size_bytes=len(session.payload),
            content_sha256=hashlib.sha256(session.payload).hexdigest(),
            provider_total_tokens=_last_provider_total(session.suffix) or 0,
            observed_at=observed_at or utc_now(),
        ),
        goal_token_budget=goal.token_budget,
    )


def finalize_codex_goal_host_run_observation(
    intent: CodexGoalHostRunObservationIntent,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
    goal_after: CodexGoalStateObservation,
    runtime_observations: tuple[CodexDesktopHostProcessObservation, ...],
    *,
    codex_home: Path,
    session_path: Path,
    thread_id: str,
) -> CodexGoalHostRunObservationReceipt:
    """Build the host run only from append-only native session and live Goal facts."""
    _validate_final_identity(intent, contract, task, admission, goal_after, thread_id)
    session = _read_session(
        codex_home,
        session_path,
        thread_id=thread_id,
        anchor=intent.session_before,
    )
    observed = _observe_turns(
        session.suffix,
        contract,
        task,
        intent.session_before.provider_total_tokens,
    )
    host_run = _build_host_run(intent, admission, goal_after, observed, runtime_observations)
    final_provider = observed[-1].provider_total_after
    if (
        final_provider - intent.session_before.provider_total_tokens != goal_after.tokens_used
        or host_run.total_tokens != goal_after.tokens_used
    ):
        raise ValueError("Codex Goal host-run Goal/provider usage drifted")
    return CodexGoalHostRunObservationReceipt(
        contract_sha256=intent.contract_sha256,
        task_sha256=intent.task_sha256,
        host_admission_sha256=intent.host_admission_sha256,
        intent_sha256=canonical_sha256(intent),
        thread_id_sha256=intent.thread_id_sha256,
        session_before=intent.session_before,
        session_after_sha256=hashlib.sha256(session.payload).hexdigest(),
        session_after_size_bytes=len(session.payload),
        runtime_observations=runtime_observations,
        provider_tokens_before=intent.session_before.provider_total_tokens,
        provider_tokens_after=final_provider,
        goal_tokens_after=goal_after.tokens_used,
        host_run=host_run,
    )


def _validate_identity(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
) -> None:
    contract_sha = canonical_sha256(contract)
    if admission.contract_sha256 != contract_sha:
        raise ValueError("Codex Goal host-run admission contract drifted")


def _validate_final_identity(
    intent: CodexGoalHostRunObservationIntent,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
    goal: CodexGoalStateObservation,
    thread_id: str,
) -> None:
    _validate_identity(contract, task, admission)
    identity = (
        intent.contract_sha256 == canonical_sha256(contract)
        and intent.task_sha256 == canonical_sha256(task)
        and intent.host_admission_sha256 == canonical_sha256(admission)
        and intent.thread_id_sha256 == _domain_sha("codex-thread-v1", thread_id)
        and goal.thread_id == thread_id
        and goal.token_budget == intent.goal_token_budget
        and 0 < goal.tokens_used <= goal.token_budget
    )
    if not identity:
        raise ValueError("Codex Goal host-run final identity or budget drifted")


def _observe_turns(
    events: tuple[dict[str, object], ...],
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    provider_before: int,
) -> tuple[_ObservedTurn, ...]:
    starts = [
        index
        for index, event in enumerate(events)
        if _event_turn(event, "task_started") is not None
    ]
    if not starts:
        raise ValueError("Codex Goal host-run session has no completed benchmark turn")
    turns: list[_ObservedTurn] = []
    provider_total = provider_before
    for sequence, start in enumerate(starts, start=1):
        end = starts[sequence] if sequence < len(starts) else len(events)
        observed = _observe_turn(
            events,
            start,
            end,
            contract,
            task,
            provider_total,
            sequence,
        )
        turns.append(observed)
        provider_total = observed.provider_total_after
    return tuple(turns)


def _observe_turn(
    events: tuple[dict[str, object], ...],
    start: int,
    end: int,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    provider_before: int,
    sequence: int,
) -> _ObservedTurn:
    turn_id = _required_event_turn(events[start], "task_started")
    segment = events[start:end]
    completions = [event for event in segment if _event_turn(event, "task_complete") == turn_id]
    contexts = [
        cast(dict[str, object], event["payload"])
        for event in segment
        if event.get("type") == "turn_context"
        and isinstance(event.get("payload"), dict)
        and cast(dict[str, object], event["payload"]).get("turn_id") == turn_id
    ]
    if len(completions) != 1 or len(contexts) != 1 or not _safe_context(contract, contexts[0]):
        raise ValueError("Codex Goal host-run turn completion or safety context drifted")
    completion_index = events.index(completions[0], start, end)
    text, input_index = _turn_input(events, turn_id, start, completion_index)
    source, opaque_sha = _classify_input(contract, task, text, sequence)
    _validate_input_position(events, source, start, input_index, turn_id)
    provider_after = _last_provider_total(segment)
    if provider_after is None or provider_after <= provider_before:
        raise ValueError("Codex Goal host-run provider usage did not advance per turn")
    return _ObservedTurn(
        turn_id=turn_id,
        source=source,
        opaque_input_sha256=opaque_sha,
        provider_total_after=provider_after,
        started_at=_event_time(events[start]),
        completed_at=_event_time(completions[0]),
    )


def _turn_input(
    events: tuple[dict[str, object], ...],
    turn_id: str,
    start: int,
    completion: int,
) -> tuple[str, int]:
    matched: list[tuple[str, int]] = []
    for index, event in enumerate(events):
        text, metadata_turn = _user_text(event)
        if text is None:
            continue
        if metadata_turn == turn_id:
            matched.append((text, index))
    if len(matched) != 1:
        raise ValueError("Codex Goal host-run turn input is missing or ambiguous")
    if completion <= start:
        raise ValueError("Codex Goal host-run turn completion precedes its start")
    return matched[0]


def _validate_input_position(
    events: tuple[dict[str, object], ...],
    source: CodexGoalTurnSource,
    start: int,
    input_index: int,
    turn_id: str,
) -> None:
    if source is not CodexGoalTurnSource.NATIVE_HOST_CONTINUATION:
        if input_index >= start:
            raise ValueError("Codex Goal client turn input did not precede task start")
        return
    if start < 1 or start + 2 >= len(events) or input_index != start + 2:
        raise ValueError("Codex Goal native continuation is not an automatic transition")
    previous_turn = _event_turn(events[start - 1], "task_complete")
    context = events[start + 1]
    context_payload = context.get("payload")
    if (
        previous_turn is None
        or context.get("type") != "turn_context"
        or not isinstance(context_payload, dict)
        or context_payload.get("turn_id") != turn_id
    ):
        raise ValueError("Codex Goal native continuation transition chain drifted")
    completed_at = _event_time(events[start - 1])
    started_at = _event_time(events[start])
    delay_ms = round((started_at - completed_at).total_seconds() * 1_000)
    if delay_ms < 0 or delay_ms > 5_000:
        raise ValueError("Codex Goal native continuation did not start automatically")


def _classify_input(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    text: str,
    sequence: int,
) -> tuple[CodexGoalTurnSource, str]:
    initial = _marked_model(text, _INITIAL_OPEN, _INITIAL_CLOSE, CodexGoalInitialTaskEnvelope)
    if initial is not None:
        if sequence != 1 or (
            initial.contract_sha256 != canonical_sha256(contract)
            or initial.task_sha256 != canonical_sha256(task)
            or initial.task != task
        ):
            raise ValueError("Codex Goal host-run initial task envelope drifted")
        return CodexGoalTurnSource.INITIAL_TASK, canonical_sha256(task)
    owner = _marked_model(text, _OWNER_OPEN, _OWNER_CLOSE, CodexGoalOwnerDecisionEnvelope)
    if owner is not None:
        if (
            sequence == 1
            or owner.contract_sha256 != canonical_sha256(contract)
            or owner.task_id != task.task_id
        ):
            raise ValueError("Codex Goal host-run owner decision envelope drifted")
        return CodexGoalTurnSource.OWNER_TAKEOVER, owner.decision_receipt_sha256
    if text.startswith(_GOAL_OPEN) and text.endswith(_GOAL_CLOSE):
        if sequence == 1:
            raise ValueError("Codex Goal host-run cannot start from continuation context")
        return CodexGoalTurnSource.NATIVE_HOST_CONTINUATION, hashlib.sha256(
            text.encode()
        ).hexdigest()
    raise ValueError("Codex Goal host-run contains an unclassified client turn")


def _marked_model(
    text: str,
    opening: str,
    closing: str,
    model_type: type[ModelT],
) -> ModelT | None:
    if not text.startswith(opening) or not text.endswith(closing):
        return None
    payload = text[len(opening) : -len(closing)]
    try:
        return model_type.model_validate_json(payload)
    except ValueError:
        raise ValueError("Codex Goal host-run marked input is invalid") from None


def _build_host_run(
    intent: CodexGoalHostRunObservationIntent,
    admission: CodexGoalHostAdmissionReceipt,
    goal: CodexGoalStateObservation,
    observed: tuple[_ObservedTurn, ...],
    runtimes: tuple[CodexDesktopHostProcessObservation, ...],
) -> CodexGoalHostRunReceipt:
    if not runtimes:
        raise ValueError("Codex Goal host-run has no signed runtime observations")
    turns: list[CodexGoalHostTurnReceipt] = []
    provider_before = intent.session_before.provider_total_tokens
    goal_before = 0
    for sequence, item in enumerate(observed, start=1):
        provider_delta = item.provider_total_after - provider_before
        goal_after = goal_before + provider_delta
        runtime_sha = _turn_runtime(item, runtimes)
        turns.append(
            CodexGoalHostTurnReceipt(
                sequence=sequence,
                source=item.source,
                previous_turn_sha256=None if not turns else turns[-1].turn_sha256,
                turn_sha256=_domain_sha("codex-turn-v1", item.turn_id),
                opaque_input_sha256=item.opaque_input_sha256,
                runtime_instance_sha256=runtime_sha,
                goal_status_after="active" if sequence < len(observed) else goal.status,
                goal_tokens_before=goal_before,
                goal_tokens_after=goal_after,
                goal_token_budget=goal.token_budget,
                provider_total_tokens=provider_delta,
                human_interventions=int(item.source is CodexGoalTurnSource.OWNER_TAKEOVER),
            )
        )
        provider_before = item.provider_total_after
        goal_before = goal_after
    return CodexGoalHostRunReceipt(
        contract_sha256=intent.contract_sha256,
        host_admission_sha256=canonical_sha256(admission),
        turns=tuple(turns),
        total_tokens=goal_before,
        human_interventions=sum(turn.human_interventions for turn in turns),
        terminal_status=goal.status,
    )


def _turn_runtime(
    turn: _ObservedTurn,
    runtimes: tuple[CodexDesktopHostProcessObservation, ...],
) -> str:
    candidates = {
        _runtime_sha(runtime)
        for runtime in runtimes
        if runtime.started_at <= turn.started_at and runtime.observed_at >= turn.completed_at
    }
    if len(candidates) != 1:
        raise ValueError("Codex Goal host-run turn does not map to one signed runtime")
    return candidates.pop()


def _runtime_sha(runtime: CodexDesktopHostProcessObservation) -> str:
    identity = (
        f"{runtime.pid}\0{runtime.started_at.isoformat()}\0"
        f"{runtime.command_sha256}\0{runtime.parent_command_sha256}"
    )
    return _domain_sha("codex-runtime-v1", identity)


def _safe_context(contract: BossAbsentBenchmarkContract, context: dict[str, object]) -> bool:
    sandbox = context.get("sandbox_policy")
    if isinstance(sandbox, str):
        read_only = sandbox in {"read-only", "readOnly"}
        network_disabled = True
    elif isinstance(sandbox, dict):
        read_only = sandbox.get("type") in {"read-only", "readOnly"}
        network_disabled = sandbox.get("network_access", sandbox.get("networkAccess")) is False
    else:
        return False
    return (
        context.get("model") == contract.model
        and context.get("effort") == contract.reasoning_effort
        and context.get("approval_policy") == "never"
        and read_only
        and network_disabled
    )


def _read_session(
    codex_home: Path,
    path: Path,
    *,
    thread_id: str,
    anchor: CodexGoalHostRunSessionAnchor | None = None,
) -> _SessionSlice:
    _validate_session_path(codex_home, path, thread_id)
    metadata = path.stat()
    payload = path.read_bytes()
    if (
        not payload
        or len(payload) != metadata.st_size
        or len(payload) > _MAX_SESSION_BYTES
        or not payload.endswith(b"\n")
    ):
        raise ValueError("Codex Goal host-run session size or termination is invalid")
    start = 0
    if anchor is not None:
        if (
            metadata.st_dev != anchor.device
            or metadata.st_ino != anchor.inode
            or len(payload) <= anchor.size_bytes
            or hashlib.sha256(payload[: anchor.size_bytes]).hexdigest() != anchor.content_sha256
        ):
            raise ValueError("Codex Goal host-run session prefix was replaced or rewritten")
        start = anchor.size_bytes
    events = tuple(_load_event(line) for line in payload.splitlines())
    _validate_meta(events, thread_id)
    suffix = tuple(_load_event(line) for line in payload[start:].splitlines())
    return _SessionSlice(
        payload,
        suffix,
        device=metadata.st_dev,
        inode=metadata.st_ino,
    )


def _validate_session_path(codex_home: Path, path: Path, thread_id: str) -> None:
    if (
        not codex_home.is_absolute()
        or codex_home != codex_home.resolve()
        or not path.is_absolute()
        or path != path.resolve()
        or not path.is_relative_to(codex_home / "sessions")
        or not path.name.endswith(f"-{thread_id}.jsonl")
        or path.is_symlink()
        or not path.is_file()
    ):
        raise ValueError("Codex Goal host-run session path is unsafe")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o022:
        raise ValueError("Codex Goal host-run session ownership or permissions are unsafe")


def _load_event(line: bytes) -> dict[str, object]:
    if not line or len(line) > _MAX_EVENT_LINE_BYTES:
        raise ValueError("Codex Goal host-run session event line is invalid")

    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Codex Goal host-run session event contains duplicate keys")
            result[key] = value
        return result

    try:
        event = json.loads(line, object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("Codex Goal host-run session event JSON is invalid") from None
    if not isinstance(event, dict):
        raise ValueError("Codex Goal host-run session event envelope is invalid")
    return event


def _validate_meta(events: tuple[dict[str, object], ...], thread_id: str) -> None:
    if not events or events[0].get("type") != "session_meta":
        raise ValueError("Codex Goal host-run session metadata is missing")
    payload = events[0].get("payload")
    if (
        not isinstance(payload, dict)
        or payload.get("id") != thread_id
        or payload.get("originator") != "Codex Desktop"
    ):
        raise ValueError("Codex Goal host-run session metadata identity drifted")
    if len(events) > _MAX_SESSION_EVENTS:
        raise ValueError("Codex Goal host-run session has too many events")


def _user_text(event: dict[str, object]) -> tuple[str | None, str | None]:
    payload = event.get("payload")
    if (
        event.get("type") != "response_item"
        or not isinstance(payload, dict)
        or payload.get("type") != "message"
        or payload.get("role") != "user"
    ):
        return None, None
    content = payload.get("content")
    if not isinstance(content, list):
        return None, None
    text = "".join(
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and item.get("type") == "input_text"
    )
    metadata = payload.get("internal_chat_message_metadata_passthrough")
    turn = metadata.get("turn_id") if isinstance(metadata, dict) else None
    return (text or None), (turn if isinstance(turn, str) and turn else None)


def _last_provider_total(events: tuple[dict[str, object], ...]) -> int | None:
    observed: int | None = None
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "token_count":
            continue
        info = payload.get("info")
        usage = info.get("total_token_usage") if isinstance(info, dict) else None
        value = usage.get("total_tokens") if isinstance(usage, dict) else None
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            or (observed is not None and value < observed)
        ):
            raise ValueError("Codex Goal host-run provider usage is invalid")
        observed = value
    return observed


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


def _required_event_turn(event: dict[str, object], event_type: str) -> str:
    value = _event_turn(event, event_type)
    if value is None:
        raise ValueError("Codex Goal host-run event turn is missing")
    return value


def _event_time(event: dict[str, object]) -> datetime:
    value = event.get("timestamp")
    if not isinstance(value, str):
        raise ValueError("Codex Goal host-run event timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Codex Goal host-run event timestamp is invalid") from None
    if parsed.tzinfo is None:
        raise ValueError("Codex Goal host-run event timestamp is not timezone-aware")
    return parsed


def _domain_sha(domain: str, value: str) -> str:
    return hashlib.sha256(f"{domain}\0{value}".encode()).hexdigest()
