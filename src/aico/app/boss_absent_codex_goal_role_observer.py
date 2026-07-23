"""Derive Codex Goal role evidence from native parent and subagent sessions."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, cast

from pydantic import Field, model_validator

from aico.app.boss_absent_codex_goal_evidence import CodexGoalRoleEvidence
from aico.app.boss_absent_codex_goal_host import (
    CodexGoalHostRunReceipt,
    CodexGoalHostTurnReceipt,
)
from aico.core.boss_absent_benchmark import (
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    canonical_sha256,
)
from aico.core.models import FrozenModel

_ASSIGNMENT_START = "<aico_boss_absent_role_assignment>"
_ASSIGNMENT_END = "</aico_boss_absent_role_assignment>"
_MAX_SESSION_BYTES = 268_435_456
_MAX_EVENT_LINE_BYTES = 4_194_304
_MAX_SESSION_EVENTS = 100_000


class CodexGoalRoleAssignment(FrozenModel):
    """Exact role envelope the native Goal agent passes to one subagent."""

    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task: BossAbsentTask
    sequence: int = Field(ge=1, le=32)
    role: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,31}$")
    consumed_checkpoint_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    artifact_contract: Literal["final_agent_message_sha256"] = "final_agent_message_sha256"

    def as_marked_text(self) -> str:
        return f"{_ASSIGNMENT_START}{self.model_dump_json()}{_ASSIGNMENT_END}"


class CodexGoalRoleChainObservationReceipt(FrozenModel):
    """Owner-safe projection of raw parent and subagent JSONL evidence."""

    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    host_run_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parent_session_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    child_session_sha256s: tuple[str, ...] = Field(min_length=1, max_length=32)
    roles: tuple[CodexGoalRoleEvidence, ...] = Field(min_length=1, max_length=32)
    observer_kind: Literal["native_session_parser"] = "native_session_parser"

    @model_validator(mode="after")
    def validate_role_sessions(self) -> CodexGoalRoleChainObservationReceipt:
        if (
            len(self.child_session_sha256s) != len(self.roles)
            or len(set(self.child_session_sha256s)) != len(self.child_session_sha256s)
            or tuple(role.sequence for role in self.roles) != tuple(range(1, len(self.roles) + 1))
        ):
            raise ValueError("Codex Goal role-chain session projection is invalid")
        return self


class _SessionEvidence:
    def __init__(self, path: Path, events: tuple[dict[str, object], ...], digest: str) -> None:
        self.path = path
        self.events = events
        self.digest = digest
        self.meta = _session_meta(events)

    @property
    def thread_id(self) -> str:
        return _text(self.meta, "id")


def observe_codex_goal_role_chain(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    host_run: CodexGoalHostRunReceipt,
    *,
    codex_home: Path,
    parent_session_path: Path,
    child_session_paths: Sequence[Path],
) -> CodexGoalRoleChainObservationReceipt:
    """Reject role labels unless native parent/child session facts prove every execution."""
    if host_run.contract_sha256 != canonical_sha256(contract):
        raise ValueError("Codex Goal role observer host run contract drifted")
    if len(child_session_paths) != len(task.required_roles):
        raise ValueError("Codex Goal role observer child session count drifted")
    parent = _read_session(codex_home, parent_session_path)
    _validate_parent(parent)
    children = tuple(_read_session(codex_home, path) for path in child_session_paths)
    if len({child.thread_id for child in children}) != len(children):
        raise ValueError("Codex Goal role observer reused a child thread")
    _validate_spawn_set(parent.events, children)
    turns_by_sha = {turn.turn_sha256: turn for turn in host_run.turns}
    observed_roles: list[CodexGoalRoleEvidence] = []
    for sequence, (role, child) in enumerate(
        zip(task.required_roles, children, strict=True),
        start=1,
    ):
        observed_roles.append(
            _observe_role(
                contract,
                task,
                parent,
                child,
                expected_role=role,
                sequence=sequence,
                previous_artifact=(
                    None if not observed_roles else observed_roles[-1].artifact_sha256
                ),
                turns_by_sha=turns_by_sha,
            )
        )
    roles = tuple(observed_roles)
    return CodexGoalRoleChainObservationReceipt(
        contract_sha256=canonical_sha256(contract),
        task_id=task.task_id,
        host_run_sha256=canonical_sha256(host_run),
        parent_session_sha256=parent.digest,
        child_session_sha256s=tuple(child.digest for child in children),
        roles=roles,
    )


def _observe_role(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    parent: _SessionEvidence,
    child: _SessionEvidence,
    *,
    expected_role: str,
    sequence: int,
    previous_artifact: str | None,
    turns_by_sha: dict[str, CodexGoalHostTurnReceipt],
) -> CodexGoalRoleEvidence:
    _validate_child_meta(parent, child)
    assignment = _role_assignment(child.events)
    _validate_assignment(contract, task, assignment, expected_role, sequence, previous_artifact)
    source_turn_id = _source_parent_turn(parent.events, child)
    source_turn_sha = _domain_sha("codex-turn-v1", source_turn_id)
    source_turn = turns_by_sha.get(source_turn_sha)
    if source_turn is None:
        raise ValueError("Codex Goal subagent source turn is absent from the host run")
    turn_id, artifact = _completed_child_execution(contract, child.events)
    return CodexGoalRoleEvidence(
        sequence=sequence,
        role=expected_role,
        agent_identity_sha256=_domain_sha("codex-agent-v1", child.thread_id),
        provider_execution_sha256=_domain_sha("codex-execution-v1", turn_id),
        runtime_instance_sha256=source_turn.runtime_instance_sha256,
        source_turn_sha256=source_turn_sha,
        input_fixture_sha256=hashlib.sha256(task.fixture.encode()).hexdigest(),
        artifact_sha256=hashlib.sha256(artifact.encode()).hexdigest(),
        consumed_checkpoint_sha256=previous_artifact,
    )


def _validate_assignment(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    assignment: CodexGoalRoleAssignment,
    role: str,
    sequence: int,
    previous_artifact: str | None,
) -> None:
    identity = (
        assignment.contract_sha256 == canonical_sha256(contract)
        and assignment.task_sha256 == canonical_sha256(task)
        and assignment.task == task
        and assignment.role == role
        and assignment.sequence == sequence
        and assignment.consumed_checkpoint_sha256 == previous_artifact
    )
    if not identity:
        raise ValueError("Codex Goal subagent role assignment drifted")


def _validate_parent(parent: _SessionEvidence) -> None:
    if parent.meta.get("originator") != "Codex Desktop":
        raise ValueError("Codex Goal parent session is not owned by Codex Desktop")


def _validate_child_meta(parent: _SessionEvidence, child: _SessionEvidence) -> None:
    source = child.meta.get("source")
    subagent = source.get("subagent") if isinstance(source, dict) else None
    spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
    identity = (
        child.meta.get("originator") == "Codex Desktop"
        and child.meta.get("parent_thread_id") == parent.thread_id
        and isinstance(spawn, dict)
        and spawn.get("parent_thread_id") == parent.thread_id
        and spawn.get("agent_path") == child.meta.get("agent_path")
    )
    if not identity:
        raise ValueError("Codex Goal child session parent identity drifted")


def _validate_spawn_set(
    parent_events: tuple[dict[str, object], ...],
    children: tuple[_SessionEvidence, ...],
) -> None:
    started: list[str] = []
    for event in parent_events:
        payload = event.get("payload")
        if (
            isinstance(payload, dict)
            and payload.get("type") == "sub_agent_activity"
            and payload.get("kind") == "started"
        ):
            started.append(_text(payload, "agent_thread_id"))
    expected = [child.thread_id for child in children]
    if len(started) != len(expected) or set(started) != set(expected):
        raise ValueError("Codex Goal parent session contains hidden or missing subagent execution")


def _source_parent_turn(
    parent_events: tuple[dict[str, object], ...],
    child: _SessionEvidence,
) -> str:
    matches: list[str] = []
    for event in parent_events:
        payload = event.get("payload")
        if not _is_spawn_call(payload):
            continue
        spawn = cast(dict[str, object], payload)
        call_id = _text(spawn, "call_id")
        turn_id = _metadata_turn(spawn)
        if _has_child_activity(parent_events, call_id, child):
            matches.append(turn_id)
    if len(matches) != 1:
        raise ValueError("Codex Goal child session lacks one native parent spawn")
    return matches[0]


def _is_spawn_call(payload: object) -> bool:
    return (
        isinstance(payload, dict)
        and payload.get("type") == "function_call"
        and payload.get("namespace") == "collaboration"
        and payload.get("name") == "spawn_agent"
    )


def _has_child_activity(
    events: tuple[dict[str, object], ...],
    call_id: str,
    child: _SessionEvidence,
) -> bool:
    matches = 0
    for event in events:
        payload = event.get("payload")
        if (
            isinstance(payload, dict)
            and payload.get("type") == "sub_agent_activity"
            and payload.get("event_id") == call_id
            and payload.get("kind") == "started"
            and payload.get("agent_thread_id") == child.thread_id
            and payload.get("agent_path") == child.meta.get("agent_path")
        ):
            matches += 1
    return matches == 1


def _metadata_turn(payload: dict[str, object]) -> str:
    metadata = payload.get("internal_chat_message_metadata_passthrough")
    if not isinstance(metadata, dict):
        raise ValueError("Codex Goal parent spawn lacks turn metadata")
    return _text(metadata, "turn_id")


def _role_assignment(events: tuple[dict[str, object], ...]) -> CodexGoalRoleAssignment:
    marked: list[str] = []
    for event in events:
        payload = event.get("payload")
        if (
            event.get("type") != "response_item"
            or not isinstance(payload, dict)
            or payload.get("type") != "message"
            or payload.get("role") != "user"
        ):
            continue
        marked.extend(_marked_texts(payload.get("content")))
    if len(marked) != 1:
        raise ValueError("Codex Goal child session lacks one exact role assignment")
    try:
        return CodexGoalRoleAssignment.model_validate_json(marked[0])
    except ValueError:
        raise ValueError("Codex Goal child role assignment is invalid") from None


def _marked_texts(content: object) -> list[str]:
    if not isinstance(content, list):
        return []
    result: list[str] = []
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "input_text":
            continue
        text = item.get("text")
        if (
            isinstance(text, str)
            and text.startswith(_ASSIGNMENT_START)
            and text.endswith(_ASSIGNMENT_END)
        ):
            result.append(text[len(_ASSIGNMENT_START) : -len(_ASSIGNMENT_END)])
    return result


def _completed_child_execution(
    contract: BossAbsentBenchmarkContract,
    events: tuple[dict[str, object], ...],
) -> tuple[str, str]:
    if any(_is_spawn_call(event.get("payload")) for event in events):
        raise ValueError("Codex Goal required role delegated to an unobserved nested Agent")
    started = _events_of_kind(events, "event_msg", "task_started")
    completed = _events_of_kind(events, "event_msg", "task_complete")
    contexts = tuple(event for event in events if event.get("type") == "turn_context")
    if len(started) != 1 or len(completed) != 1 or len(contexts) != 1:
        raise ValueError("Codex Goal child execution is not one bounded turn")
    turn_id = _text(cast(dict[str, object], started[0]["payload"]), "turn_id")
    completed_payload = cast(dict[str, object], completed[0]["payload"])
    context = cast(dict[str, object], contexts[0]["payload"])
    artifact = _text(completed_payload, "last_agent_message")
    if (
        _text(completed_payload, "turn_id") != turn_id
        or _text(context, "turn_id") != turn_id
        or not _safe_context(contract, context)
        or _last_assistant_output(events) != artifact
    ):
        raise ValueError("Codex Goal child execution identity or safety drifted")
    return turn_id, artifact


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


def _last_assistant_output(events: tuple[dict[str, object], ...]) -> str | None:
    observed: str | None = None
    for event in events:
        payload = event.get("payload")
        if (
            event.get("type") != "response_item"
            or not isinstance(payload, dict)
            or payload.get("type") != "message"
            or payload.get("role") != "assistant"
        ):
            continue
        content = payload.get("content")
        if not isinstance(content, list):
            continue
        observed = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "output_text"
        )
    return observed


def _events_of_kind(
    events: tuple[dict[str, object], ...],
    envelope_type: str,
    payload_type: str,
) -> tuple[dict[str, object], ...]:
    return tuple(
        event
        for event in events
        if event.get("type") == envelope_type
        and isinstance(event.get("payload"), dict)
        and cast(dict[str, object], event["payload"]).get("type") == payload_type
    )


def _read_session(codex_home: Path, path: Path) -> _SessionEvidence:
    _validate_session_path(codex_home, path)
    payload = path.read_bytes()
    if not payload or len(payload) > _MAX_SESSION_BYTES or not payload.endswith(b"\n"):
        raise ValueError("Codex Goal role session size or termination is invalid")
    lines = payload.splitlines()
    if len(lines) > _MAX_SESSION_EVENTS:
        raise ValueError("Codex Goal role session has too many events")
    events = tuple(_load_event(line) for line in lines)
    evidence = _SessionEvidence(path, events, hashlib.sha256(payload).hexdigest())
    if not path.name.endswith(f"-{evidence.thread_id}.jsonl"):
        raise ValueError("Codex Goal role session filename identity drifted")
    return evidence


def _validate_session_path(codex_home: Path, path: Path) -> None:
    if (
        not codex_home.is_absolute()
        or codex_home != codex_home.resolve()
        or not path.is_absolute()
        or path != path.resolve()
        or not path.is_relative_to(codex_home / "sessions")
        or path.is_symlink()
        or not path.is_file()
    ):
        raise ValueError("Codex Goal role session path is unsafe")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o022:
        raise ValueError("Codex Goal role session ownership or permissions are unsafe")


def _load_event(line: bytes) -> dict[str, object]:
    if not line or len(line) > _MAX_EVENT_LINE_BYTES:
        raise ValueError("Codex Goal role session event line is invalid")

    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Codex Goal role session event contains duplicate keys")
            result[key] = value
        return result

    try:
        event = json.loads(line, object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError("Codex Goal role session event JSON is invalid") from None
    if not isinstance(event, dict):
        raise ValueError("Codex Goal role session event envelope is invalid")
    return event


def _session_meta(events: tuple[dict[str, object], ...]) -> dict[str, object]:
    if not events or events[0].get("type") != "session_meta":
        raise ValueError("Codex Goal role session metadata is missing")
    payload = events[0].get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Codex Goal role session metadata is invalid")
    return payload


def _text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError("Codex Goal role session is missing an identifier")
    return value


def _domain_sha(domain: str, value: str) -> str:
    return hashlib.sha256(f"{domain}\0{value}".encode()).hexdigest()
