from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

import pytest

from aico.app.boss_absent_codex_goal_host import (
    CodexGoalHostAdmissionReceipt,
    CodexGoalHostKind,
)
from aico.app.boss_absent_codex_goal_live_observer import (
    CodexDesktopHostProcessObservation,
)
from aico.app.boss_absent_codex_goal_probe import CodexGoalStateObservation
from aico.app.boss_absent_codex_goal_run_observer import (
    CodexGoalHostRunObservationIntent,
    CodexGoalHostRunObservationReceipt,
    CodexGoalInitialTaskEnvelope,
    CodexGoalOwnerDecisionEnvelope,
    begin_codex_goal_host_run_observation,
    finalize_codex_goal_host_run_observation,
)
from aico.core.boss_absent_benchmark import (
    BenchmarkScenario,
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    canonical_sha256,
)

_THREAD_ID = "019f9000-0000-7000-8000-000000000010"
_BASE = datetime(2026, 7, 23, 10, 0, tzinfo=UTC)


def test_native_session_derives_complete_host_run_across_restart(tmp_path: Path) -> None:
    contract, task, admission = _fixtures()
    session = _session(tmp_path)
    intent = _begin(contract, task, admission, tmp_path, session)
    _append_run(session, contract, task)

    receipt = finalize_codex_goal_host_run_observation(
        intent,
        contract,
        task,
        admission,
        _goal(contract, status="complete", used=220),
        _runtimes(),
        codex_home=tmp_path,
        session_path=session,
        thread_id=_THREAD_ID,
    )

    assert receipt.host_run.total_tokens == 220
    assert tuple(turn.source.value for turn in receipt.host_run.turns) == (
        "initial_task",
        "native_host_continuation",
    )
    assert receipt.host_run.turns[0].opaque_input_sha256 == canonical_sha256(task)
    assert receipt.host_run.turns[0].runtime_instance_sha256 != (
        receipt.host_run.turns[1].runtime_instance_sha256
    )
    assert receipt.host_run.human_interventions == 0
    assert receipt.provider_tokens_after - receipt.provider_tokens_before == 220


def test_owner_decision_is_the_only_observed_human_intervention(tmp_path: Path) -> None:
    contract, task, admission = _fixtures(approval=True)
    session = _session(tmp_path)
    intent = _begin(contract, task, admission, tmp_path, session)
    grant_sha = "d" * 64
    _append_run(session, contract, task, owner_grant=grant_sha)

    receipt = finalize_codex_goal_host_run_observation(
        intent,
        contract,
        task,
        admission,
        _goal(contract, status="complete", used=220),
        _runtimes(),
        codex_home=tmp_path,
        session_path=session,
        thread_id=_THREAD_ID,
    )

    owner = receipt.host_run.turns[1]
    assert owner.source.value == "owner_takeover"
    assert owner.opaque_input_sha256 == grant_sha
    assert owner.human_interventions == 1
    assert receipt.host_run.human_interventions == 1


def test_observer_rejects_unmarked_turn_or_context_drift(tmp_path: Path) -> None:
    contract, task, admission = _fixtures()
    session = _session(tmp_path)
    intent = _begin(contract, task, admission, tmp_path, session)
    _append_run(session, contract, task)
    events = _events(session)
    user = next(event for event in events if _is_user_event(event))
    user_payload = cast(dict[str, object], user["payload"])
    content = cast(list[dict[str, object]], user_payload["content"])
    content[0]["text"] = "continue please"
    _write(session, events)
    with pytest.raises(ValueError, match="unclassified client turn"):
        _finish(intent, contract, task, admission, tmp_path, session)

    session = _session(tmp_path)
    intent = _begin(contract, task, admission, tmp_path, session)
    _append_run(session, contract, task)
    events = _events(session)
    context = next(event for event in events if event.get("type") == "turn_context")
    context_payload = cast(dict[str, object], context["payload"])
    context_payload["model"] = "other-model"
    _write(session, events)
    with pytest.raises(ValueError, match="safety context drifted"):
        _finish(intent, contract, task, admission, tmp_path, session)


def test_observer_rejects_usage_or_runtime_attribution_drift(tmp_path: Path) -> None:
    contract, task, admission = _fixtures()
    session = _session(tmp_path)
    intent = _begin(contract, task, admission, tmp_path, session)
    _append_run(session, contract, task)
    with pytest.raises(ValueError, match="Goal/provider usage drifted"):
        _finish(
            intent,
            contract,
            task,
            admission,
            tmp_path,
            session,
            goal_used=219,
        )
    with pytest.raises(ValueError, match="one signed runtime"):
        _finish(
            intent,
            contract,
            task,
            admission,
            tmp_path,
            session,
            runtimes=(_runtimes()[1],),
        )


def test_observer_rejects_client_injected_goal_marker(tmp_path: Path) -> None:
    contract, task, admission = _fixtures()
    session = _session(tmp_path)
    intent = _begin(contract, task, admission, tmp_path, session)
    _append_run(session, contract, task)
    events = _events(session)
    start = next(index for index, event in enumerate(events) if _event_turn(event) == "turn-second")
    goal_input = events.pop(start + 2)
    events.insert(start, goal_input)
    _write(session, events)

    with pytest.raises(ValueError, match="not an automatic transition"):
        _finish(intent, contract, task, admission, tmp_path, session)


def test_observer_rejects_rewritten_prefix_unsafe_file_or_duplicate_json(
    tmp_path: Path,
) -> None:
    contract, task, admission = _fixtures()
    session = _session(tmp_path)
    intent = _begin(contract, task, admission, tmp_path, session)
    original = session.read_bytes()
    session.write_bytes(
        original.replace(
            b'"originator": "Codex Desktop"',
            b'"originator": "Codex DesktoP"',
        )
    )
    with pytest.raises(ValueError, match="prefix was replaced or rewritten"):
        _finish(intent, contract, task, admission, tmp_path, session)

    session = _session(tmp_path)
    os.chmod(session, 0o622)
    with pytest.raises(ValueError, match="permissions are unsafe"):
        _begin(contract, task, admission, tmp_path, session)

    session = _session(tmp_path)
    with session.open("ab") as output:
        output.write(b'{"type":"event_msg","type":"event_msg"}\n')
    with pytest.raises(ValueError, match="duplicate keys"):
        _begin(contract, task, admission, tmp_path, session)


def test_begin_requires_zero_usage_and_exact_contract(tmp_path: Path) -> None:
    contract, task, admission = _fixtures()
    session = _session(tmp_path)
    with pytest.raises(ValueError, match="zero usage"):
        begin_codex_goal_host_run_observation(
            contract,
            task,
            admission,
            _goal(contract, status="active", used=1),
            codex_home=tmp_path,
            session_path=session,
            thread_id=_THREAD_ID,
        )
    drifted = admission.model_copy(update={"contract_sha256": "f" * 64})
    with pytest.raises(ValueError, match="admission contract drifted"):
        _begin(contract, task, drifted, tmp_path, session)


def _fixtures(
    *,
    approval: bool = False,
) -> tuple[BossAbsentBenchmarkContract, BossAbsentTask, CodexGoalHostAdmissionReceipt]:
    contract = BossAbsentBenchmarkContract(
        benchmark_id="codex-host-run-observer",
        frozen_at=_BASE,
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
    task = BossAbsentTask(
        task_id="approval-fence-resume" if approval else "normal-release-audit",
        scenario=BenchmarkScenario.APPROVAL if approval else BenchmarkScenario.NORMAL,
        objective="produce a verified terminal handoff",
        fixture='{"release":"candidate-17","tests":"green"}',
        acceptance=("lead plans", "reviewer verifies"),
        required_roles=("lead", "reviewer"),
        unattended_eligible=not approval,
        collaboration_required=True,
        approval_required=approval,
    )
    admission = CodexGoalHostAdmissionReceipt(
        contract_sha256=canonical_sha256(contract),
        host_build="signed-desktop-test",
        host_kind=CodexGoalHostKind.NATIVE_CODEX_HOST,
    )
    return contract, task, admission


def _session(root: Path) -> Path:
    sessions = root / "sessions"
    sessions.mkdir(exist_ok=True)
    path = sessions / f"rollout-parent-{_THREAD_ID}.jsonl"
    _write(
        path,
        [
            {
                "type": "session_meta",
                "payload": {
                    "id": _THREAD_ID,
                    "originator": "Codex Desktop",
                },
            },
            _token_event(50),
        ],
    )
    return path


def _begin(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
    root: Path,
    session: Path,
) -> CodexGoalHostRunObservationIntent:
    return begin_codex_goal_host_run_observation(
        contract,
        task,
        admission,
        _goal(contract, status="active", used=0),
        codex_home=root,
        session_path=session,
        thread_id=_THREAD_ID,
        observed_at=_BASE - timedelta(seconds=30),
    )


def _finish(
    intent: CodexGoalHostRunObservationIntent,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
    root: Path,
    session: Path,
    *,
    goal_used: int = 220,
    runtimes: tuple[CodexDesktopHostProcessObservation, ...] | None = None,
) -> CodexGoalHostRunObservationReceipt:
    return finalize_codex_goal_host_run_observation(
        intent,
        contract,
        task,
        admission,
        _goal(contract, status="complete", used=goal_used),
        runtimes or _runtimes(),
        codex_home=root,
        session_path=session,
        thread_id=_THREAD_ID,
    )


def _goal(
    contract: BossAbsentBenchmarkContract,
    *,
    status: Literal[
        "active",
        "paused",
        "blocked",
        "usageLimited",
        "budgetLimited",
        "complete",
    ],
    used: int,
) -> CodexGoalStateObservation:
    return CodexGoalStateObservation(
        thread_id=_THREAD_ID,
        status=status,
        token_budget=contract.max_total_tokens,
        tokens_used=used,
        time_used_seconds=60,
    )


def _append_run(
    path: Path,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    *,
    owner_grant: str | None = None,
) -> None:
    initial = CodexGoalInitialTaskEnvelope(
        contract_sha256=canonical_sha256(contract),
        task_sha256=canonical_sha256(task),
        task=task,
    ).as_marked_text()
    second = (
        CodexGoalOwnerDecisionEnvelope(
            contract_sha256=canonical_sha256(contract),
            task_id=task.task_id,
            decision_receipt_sha256=owner_grant,
        ).as_marked_text()
        if owner_grant is not None
        else '<codex_internal_context source="goal">continue autonomously</codex_internal_context>'
    )
    events = [
        *_turn_events("turn-initial", initial, 150, _BASE, output="lead complete"),
        *_turn_events(
            "turn-second",
            second,
            270,
            _BASE + timedelta(seconds=32),
            output="review complete",
            automatic=owner_grant is None,
        ),
    ]
    with path.open("a", encoding="utf-8") as output:
        output.write("".join(f"{json.dumps(event)}\n" for event in events))


def _turn_events(
    turn_id: str,
    text: str,
    provider_total: int,
    started_at: datetime,
    *,
    output: str,
    automatic: bool = False,
) -> list[dict[str, object]]:
    completed_at = started_at + timedelta(seconds=30)
    user: dict[str, object] = {
        "timestamp": (
            started_at if automatic else started_at - timedelta(milliseconds=1)
        ).isoformat(),
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": text}],
            "internal_chat_message_metadata_passthrough": {"turn_id": turn_id},
        },
    }
    started: dict[str, object] = {
        "timestamp": started_at.isoformat(),
        "type": "event_msg",
        "payload": {"type": "task_started", "turn_id": turn_id},
    }
    context: dict[str, object] = {
        "timestamp": started_at.isoformat(),
        "type": "turn_context",
        "payload": {
            "turn_id": turn_id,
            "model": "gpt-5.6-sol",
            "effort": "high",
            "approval_policy": "never",
            "sandbox_policy": {"type": "readOnly", "networkAccess": False},
        },
    }
    prefix: list[dict[str, object]] = (
        [started, context, user] if automatic else [user, started, context]
    )
    return [
        *prefix,
        _token_event(provider_total, timestamp=completed_at - timedelta(seconds=1)),
        {
            "timestamp": completed_at.isoformat(),
            "type": "event_msg",
            "payload": {
                "type": "task_complete",
                "turn_id": turn_id,
                "last_agent_message": output,
            },
        },
    ]


def _token_event(
    total: int,
    *,
    timestamp: datetime | None = None,
) -> dict[str, object]:
    event: dict[str, object] = {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"total_token_usage": {"total_tokens": total}},
        },
    }
    if timestamp is not None:
        event["timestamp"] = timestamp.isoformat()
    return event


def _runtimes() -> tuple[CodexDesktopHostProcessObservation, ...]:
    return (
        _runtime(101, _BASE - timedelta(minutes=1), _BASE + timedelta(seconds=31)),
        _runtime(
            202,
            _BASE + timedelta(seconds=31),
            _BASE + timedelta(minutes=2),
        ),
    )


def _runtime(
    pid: int,
    started_at: datetime,
    observed_at: datetime,
) -> CodexDesktopHostProcessObservation:
    return CodexDesktopHostProcessObservation(
        pid=pid,
        parent_pid=pid + 1,
        started_at=started_at,
        observed_at=observed_at,
        command_sha256="a" * 64,
        parent_command_sha256="b" * 64,
    )


def _write(path: Path, events: list[dict[str, object]]) -> None:
    path.write_text("".join(f"{json.dumps(event)}\n" for event in events))
    os.chmod(path, 0o600)


def _events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def _is_user_event(event: dict[str, object]) -> bool:
    payload = event.get("payload")
    return (
        event.get("type") == "response_item"
        and isinstance(payload, dict)
        and payload.get("role") == "user"
    )


def _event_turn(event: dict[str, object]) -> str | None:
    payload = event.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "task_started":
        return None
    value = payload.get("turn_id")
    return value if isinstance(value, str) else None
