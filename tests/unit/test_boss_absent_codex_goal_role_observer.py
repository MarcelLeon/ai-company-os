from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.app.boss_absent_codex_goal_host import (
    CodexGoalHostRunReceipt,
    CodexGoalHostTurnReceipt,
    CodexGoalTurnSource,
)
from aico.app.boss_absent_codex_goal_role_observer import (
    CodexGoalRoleAssignment,
    observe_codex_goal_role_chain,
)
from aico.core.boss_absent_benchmark import (
    BenchmarkScenario,
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    canonical_sha256,
)

_PARENT_ID = "019f9000-0000-7000-8000-000000000001"
_CHILD_IDS = (
    "019f9000-0000-7000-8000-000000000002",
    "019f9000-0000-7000-8000-000000000003",
)
_PARENT_TURNS = ("parent-turn-lead", "parent-turn-reviewer")
_CHILD_TURNS = ("child-turn-lead", "child-turn-reviewer")
_OUTPUTS = ("bounded lead artifact", "reviewer consumed lead and accepted")


def test_native_sessions_derive_distinct_role_chain(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    host_run = _host_run(contract, task)
    parent, children = _sessions(tmp_path, contract, task)

    receipt = observe_codex_goal_role_chain(
        contract,
        task,
        host_run,
        codex_home=tmp_path,
        parent_session_path=parent,
        child_session_paths=children,
    )

    assert tuple(role.role for role in receipt.roles) == task.required_roles
    assert len({role.agent_identity_sha256 for role in receipt.roles}) == 2
    assert len({role.provider_execution_sha256 for role in receipt.roles}) == 2
    assert receipt.roles[1].consumed_checkpoint_sha256 == receipt.roles[0].artifact_sha256
    assert receipt.roles[0].source_turn_sha256 == _domain_sha(
        "codex-turn-v1",
        _PARENT_TURNS[0],
    )
    assert receipt.roles[0].runtime_instance_sha256 == "a" * 64


def test_role_observer_rejects_reused_child_or_parent_spawn_drift(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    host_run = _host_run(contract, task)
    parent, children = _sessions(tmp_path, contract, task)

    with pytest.raises(ValueError, match="reused a child thread"):
        observe_codex_goal_role_chain(
            contract,
            task,
            host_run,
            codex_home=tmp_path,
            parent_session_path=parent,
            child_session_paths=(children[0], children[0]),
        )
    events = _read_events(parent)
    events.append(
        {
            "type": "event_msg",
            "payload": {
                "type": "sub_agent_activity",
                "event_id": "call-hidden",
                "agent_thread_id": "019f9000-0000-7000-8000-000000000098",
                "agent_path": "/root/hidden",
                "kind": "started",
            },
        }
    )
    _write_events(parent, events)
    with pytest.raises(ValueError, match="hidden or missing subagent"):
        observe_codex_goal_role_chain(
            contract,
            task,
            host_run,
            codex_home=tmp_path,
            parent_session_path=parent,
            child_session_paths=children,
        )

    parent, children = _sessions(tmp_path, contract, task)
    events = _read_events(parent)
    activity = events[2]["payload"]
    assert isinstance(activity, dict)
    activity["agent_thread_id"] = "019f9000-0000-7000-8000-000000000099"
    _write_events(parent, events)
    with pytest.raises(ValueError, match="hidden or missing subagent"):
        observe_codex_goal_role_chain(
            contract,
            task,
            host_run,
            codex_home=tmp_path,
            parent_session_path=parent,
            child_session_paths=children,
        )


def test_role_observer_rejects_assignment_chain_or_model_drift(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    host_run = _host_run(contract, task)
    parent, children = _sessions(tmp_path, contract, task)
    events = _read_events(children[1])
    user = events[1]["payload"]
    assert isinstance(user, dict)
    content = user["content"]
    assert isinstance(content, list) and isinstance(content[0], dict)
    wrong = _assignment(contract, task, 2, consumed="0" * 64)
    content[0]["text"] = wrong.as_marked_text()
    _write_events(children[1], events)
    with pytest.raises(ValueError, match="assignment drifted"):
        observe_codex_goal_role_chain(
            contract,
            task,
            host_run,
            codex_home=tmp_path,
            parent_session_path=parent,
            child_session_paths=children,
        )

    parent, children = _sessions(tmp_path, contract, task)
    events = _read_events(children[0])
    context = events[3]["payload"]
    assert isinstance(context, dict)
    context["model"] = "wrong-model"
    _write_events(children[0], events)
    with pytest.raises(ValueError, match="identity or safety drifted"):
        observe_codex_goal_role_chain(
            contract,
            task,
            host_run,
            codex_home=tmp_path,
            parent_session_path=parent,
            child_session_paths=children,
        )


def test_role_observer_rejects_terminal_artifact_or_source_turn_drift(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    host_run = _host_run(contract, task)
    parent, children = _sessions(tmp_path, contract, task)
    events = _read_events(children[0])
    completed = events[-1]["payload"]
    assert isinstance(completed, dict)
    completed["last_agent_message"] = "different artifact"
    _write_events(children[0], events)
    with pytest.raises(ValueError, match="identity or safety drifted"):
        observe_codex_goal_role_chain(
            contract,
            task,
            host_run,
            codex_home=tmp_path,
            parent_session_path=parent,
            child_session_paths=children,
        )

    parent, children = _sessions(tmp_path, contract, task)
    missing_turn = host_run.model_copy(update={"turns": (host_run.turns[0],)})
    with pytest.raises(ValueError, match="absent from the host run"):
        observe_codex_goal_role_chain(
            contract,
            task,
            missing_turn,
            codex_home=tmp_path,
            parent_session_path=parent,
            child_session_paths=children,
        )


def test_role_observer_rejects_unsafe_or_duplicate_json_session(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    host_run = _host_run(contract, task)
    parent, children = _sessions(tmp_path, contract, task)
    os.chmod(children[0], 0o622)
    with pytest.raises(ValueError, match="permissions are unsafe"):
        observe_codex_goal_role_chain(
            contract,
            task,
            host_run,
            codex_home=tmp_path,
            parent_session_path=parent,
            child_session_paths=children,
        )
    os.chmod(children[0], 0o600)
    children[0].write_text('{"type":"session_meta","type":"session_meta"}\n')
    with pytest.raises(ValueError, match="duplicate keys"):
        observe_codex_goal_role_chain(
            contract,
            task,
            host_run,
            codex_home=tmp_path,
            parent_session_path=parent,
            child_session_paths=children,
        )


def _contract() -> BossAbsentBenchmarkContract:
    return BossAbsentBenchmarkContract(
        benchmark_id="codex-role-observer",
        frozen_at=datetime(2026, 7, 23, tzinfo=UTC),
        model="gpt-5.6-sol",
        reasoning_effort="high",
        repo_revision="a" * 40,
        aico_version="test",
        codex_cli_version="0.145.0-alpha.30",
        wall_window_seconds=600,
        max_total_tokens=1_000,
        task_set_sha256="b" * 64,
        project_id="benchmark-project",
        project_assignment_sha256="c" * 64,
    )


def _task() -> BossAbsentTask:
    return BossAbsentTask(
        task_id="normal-release-audit",
        scenario=BenchmarkScenario.NORMAL,
        objective="produce a verified terminal handoff",
        fixture='{"release":"candidate-17","tests":"green"}',
        acceptance=("lead plans", "reviewer verifies"),
        required_roles=("lead", "reviewer"),
        unattended_eligible=True,
        collaboration_required=True,
    )


def _host_run(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
) -> CodexGoalHostRunReceipt:
    first = _host_turn(contract, task, 1, before=0, after=100)
    second = _host_turn(contract, task, 2, before=100, after=220, previous=first.turn_sha256)
    return CodexGoalHostRunReceipt(
        contract_sha256=canonical_sha256(contract),
        host_admission_sha256="d" * 64,
        turns=(first, second),
        total_tokens=220,
        human_interventions=0,
        terminal_status="complete",
    )


def _host_turn(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    sequence: int,
    *,
    before: int,
    after: int,
    previous: str | None = None,
) -> CodexGoalHostTurnReceipt:
    return CodexGoalHostTurnReceipt(
        sequence=sequence,
        source=(
            CodexGoalTurnSource.INITIAL_TASK
            if sequence == 1
            else CodexGoalTurnSource.NATIVE_HOST_CONTINUATION
        ),
        previous_turn_sha256=previous,
        turn_sha256=_domain_sha("codex-turn-v1", _PARENT_TURNS[sequence - 1]),
        opaque_input_sha256=(canonical_sha256(task) if sequence == 1 else "9" * 64),
        runtime_instance_sha256="a" * 64,
        goal_status_after=("active" if sequence == 1 else "complete"),
        goal_tokens_before=before,
        goal_tokens_after=after,
        goal_token_budget=contract.max_total_tokens,
        provider_total_tokens=after - before,
    )


def _sessions(
    root: Path,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
) -> tuple[Path, tuple[Path, Path]]:
    sessions = root / "sessions"
    sessions.mkdir(exist_ok=True)
    parent = sessions / f"rollout-parent-{_PARENT_ID}.jsonl"
    parent_events: list[dict[str, object]] = [_parent_meta()]
    children: list[Path] = []
    previous: str | None = None
    for index, role in enumerate(task.required_roles):
        child_id = _CHILD_IDS[index]
        call_id = f"call-{index + 1}"
        path = sessions / f"rollout-child-{child_id}.jsonl"
        assignment = _assignment(contract, task, index + 1, consumed=previous)
        _write_events(
            path,
            _child_events(
                child_id,
                role,
                call_id,
                assignment,
                turn_id=_CHILD_TURNS[index],
                output=_OUTPUTS[index],
            ),
        )
        parent_events.extend(_spawn_events(child_id, role, call_id, _PARENT_TURNS[index]))
        children.append(path)
        previous = hashlib.sha256(_OUTPUTS[index].encode()).hexdigest()
    _write_events(parent, parent_events)
    return parent, (children[0], children[1])


def _assignment(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    sequence: int,
    *,
    consumed: str | None,
) -> CodexGoalRoleAssignment:
    return CodexGoalRoleAssignment(
        contract_sha256=canonical_sha256(contract),
        task_sha256=canonical_sha256(task),
        task=task,
        sequence=sequence,
        role=task.required_roles[sequence - 1],
        consumed_checkpoint_sha256=consumed,
    )


def _parent_meta() -> dict[str, object]:
    return {
        "type": "session_meta",
        "payload": {"id": _PARENT_ID, "originator": "Codex Desktop"},
    }


def _spawn_events(
    child_id: str,
    role: str,
    call_id: str,
    turn_id: str,
) -> list[dict[str, object]]:
    path = f"/root/benchmark-{role}"
    return [
        {
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "namespace": "collaboration",
                "name": "spawn_agent",
                "call_id": call_id,
                "internal_chat_message_metadata_passthrough": {"turn_id": turn_id},
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "sub_agent_activity",
                "event_id": call_id,
                "agent_thread_id": child_id,
                "agent_path": path,
                "kind": "started",
            },
        },
    ]


def _child_events(
    child_id: str,
    role: str,
    call_id: str,
    assignment: CodexGoalRoleAssignment,
    *,
    turn_id: str,
    output: str,
) -> list[dict[str, object]]:
    path = f"/root/benchmark-{role}"
    return [
        {
            "type": "session_meta",
            "payload": {
                "id": child_id,
                "originator": "Codex Desktop",
                "parent_thread_id": _PARENT_ID,
                "agent_path": path,
                "source": {
                    "subagent": {
                        "thread_spawn": {
                            "parent_thread_id": _PARENT_ID,
                            "agent_path": path,
                        }
                    }
                },
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": assignment.as_marked_text()}],
            },
        },
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": turn_id}},
        {
            "type": "turn_context",
            "payload": {
                "turn_id": turn_id,
                "model": "gpt-5.6-sol",
                "effort": "high",
                "approval_policy": "never",
                "sandbox_policy": {"type": "readOnly", "networkAccess": False},
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": output}],
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "task_complete",
                "turn_id": turn_id,
                "last_agent_message": output,
                "event_id": call_id,
            },
        },
    ]


def _write_events(path: Path, events: list[dict[str, object]]) -> None:
    path.write_text("".join(f"{json.dumps(event)}\n" for event in events))
    os.chmod(path, 0o600)


def _read_events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def _domain_sha(domain: str, value: str) -> str:
    return hashlib.sha256(f"{domain}\0{value}".encode()).hexdigest()
