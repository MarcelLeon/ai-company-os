from __future__ import annotations

import json
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aico.app.boss_absent_codex_goal_capability import (
    CodexGoalNativeHostCandidateReceipt,
)
from aico.app.boss_absent_codex_goal_live_observer import (
    CodexDesktopHostProcessObservation,
    CodexGoalLiveHostObservationReceipt,
)
from aico.app.boss_absent_codex_goal_observer_cli import run
from aico.app.boss_absent_codex_goal_probe import CodexGoalStateObservation
from aico.core.boss_absent_benchmark import (
    BossAbsentBenchmarkContract,
    canonical_sha256,
)

_THREAD_ID = "019f83fb-dde5-7c93-a163-81211d22d7ff"
_BASE_TIME = datetime(2026, 7, 23, 4, 0, tzinfo=UTC)


def test_observer_cli_writes_owner_only_intent_and_live_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = _contract()
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(contract.model_dump_json())
    candidate = _candidate(canonical_sha256(contract))
    session = tmp_path / "sessions" / f"rollout-2026-07-23T04-00-00-{_THREAD_ID}.jsonl"
    session.parent.mkdir()
    _write_prefix(session)
    before = _host(100, _BASE_TIME, _BASE_TIME + timedelta(minutes=1))
    after = _host(
        200,
        _BASE_TIME + timedelta(minutes=2),
        _BASE_TIME + timedelta(minutes=6),
    )
    monkeypatch.setattr(
        "aico.app.boss_absent_codex_goal_observer_cli.probe_codex_goal_native_host_candidate",
        lambda **_: candidate,
    )
    monkeypatch.setattr(
        "aico.app.boss_absent_codex_goal_observer_cli.inspect_codex_desktop_host",
        lambda *_args, **_kwargs: before,
    )
    monkeypatch.setattr(
        "aico.app.boss_absent_codex_goal_observer_cli.observe_codex_goal_state",
        lambda **_: _goal(100),
    )
    intent_path = tmp_path / "private" / "intent.json"

    assert run(_args("start", contract_path, session, intent_path)) == 0
    assert stat.S_IMODE(intent_path.stat().st_mode) == 0o600
    _append_continuation(session)
    hosts = iter((after, None))
    monkeypatch.setattr(
        "aico.app.boss_absent_codex_goal_observer_cli.inspect_codex_desktop_host",
        lambda *_args, **_kwargs: next(hosts),
    )
    monkeypatch.setattr(
        "aico.app.boss_absent_codex_goal_observer_cli.observe_codex_goal_state",
        lambda **_: _goal(220),
    )
    receipt_path = tmp_path / "private" / "receipt.json"

    assert (
        run(
            _args(
                "finish",
                contract_path,
                session,
                receipt_path,
                intent=intent_path,
            )
        )
        == 0
    )
    receipt = CodexGoalLiveHostObservationReceipt.model_validate_json(receipt_path.read_text())
    assert receipt.formal_run_admitted
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o600


def _args(
    command: str,
    contract: Path,
    session: Path,
    output: Path,
    *,
    intent: Path | None = None,
) -> list[str]:
    args = [
        command,
        "--contract",
        str(contract),
        "--session",
        str(session),
        "--thread-id",
        _THREAD_ID,
        "--host-pid",
        "100" if command == "start" else "200",
        "--codex-home",
        str(contract.parent),
        "--output",
        str(output),
    ]
    if intent is not None:
        args.extend(("--intent", str(intent)))
    return args


def _contract() -> BossAbsentBenchmarkContract:
    return BossAbsentBenchmarkContract(
        benchmark_id="live-host-probe",
        frozen_at=_BASE_TIME,
        model="gpt-5.6-sol",
        reasoning_effort="high",
        repo_revision="1" * 40,
        aico_version="test",
        codex_cli_version="0.145.0-alpha.30",
        wall_window_seconds=600,
        max_total_tokens=10_000,
        task_set_sha256="2" * 64,
        project_id="live-host-project",
        project_assignment_sha256="3" * 64,
    )


def _candidate(contract_sha256: str) -> CodexGoalNativeHostCandidateReceipt:
    return CodexGoalNativeHostCandidateReceipt(
        contract_sha256=contract_sha256,
        app_version="26.715.72359",
        app_build="5718",
        app_cdhash_sha256="4" * 64,
        embedded_cli_cdhash_sha256="5" * 64,
        team_identifier="2DC432GLL2",
        codex_cli_version="0.145.0-alpha.30",
        schema_bundle_sha256="6" * 64,
    )


def _goal(tokens: int) -> CodexGoalStateObservation:
    return CodexGoalStateObservation(
        thread_id=_THREAD_ID,
        status="active",
        token_budget=1_000,
        tokens_used=tokens,
        time_used_seconds=tokens,
    )


def _host(
    pid: int,
    started_at: datetime,
    observed_at: datetime,
) -> CodexDesktopHostProcessObservation:
    return CodexDesktopHostProcessObservation(
        pid=pid,
        parent_pid=pid - 1,
        started_at=started_at,
        observed_at=observed_at,
        command_sha256="7" * 64,
        parent_command_sha256="8" * 64,
    )


def _write_prefix(path: Path) -> None:
    _write_events(
        path,
        (
            {
                "timestamp": _time(0),
                "type": "session_meta",
                "payload": {"id": _THREAD_ID, "originator": "Codex Desktop"},
            },
            {
                "timestamp": _time(0),
                "type": "turn_context",
                "payload": _context_payload("initial-turn"),
            },
            _token_event(100, 1),
            _task_event("task_started", "pre-restart", 1),
        ),
        mode="w",
    )


def _append_continuation(path: Path) -> None:
    continued = "native-continuation"
    _write_events(
        path,
        (
            _task_event("task_complete", "pre-restart", 3),
            _task_event("task_started", continued, 3, milliseconds=2),
            {
                "timestamp": _time(3, milliseconds=3),
                "type": "turn_context",
                "payload": _context_payload(continued),
            },
            {
                "timestamp": _time(3, milliseconds=4),
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                '<codex_internal_context source="goal">\n'
                                "redacted\n"
                                "</codex_internal_context>"
                            ),
                        }
                    ],
                    "internal_chat_message_metadata_passthrough": {"turn_id": continued},
                },
            },
            _token_event(200, 4),
            _task_event("task_complete", continued, 5),
        ),
        mode="a",
    )


def _write_events(
    path: Path,
    events: tuple[dict[str, object], ...],
    *,
    mode: str,
) -> None:
    with path.open(mode) as output:
        output.write("".join(f"{json.dumps(event)}\n" for event in events))


def _task_event(
    kind: str,
    turn_id: str,
    minute: int,
    *,
    milliseconds: int = 0,
) -> dict[str, object]:
    return {
        "timestamp": _time(minute, milliseconds=milliseconds),
        "type": "event_msg",
        "payload": {"type": kind, "turn_id": turn_id},
    }


def _context_payload(turn_id: str) -> dict[str, object]:
    return {
        "turn_id": turn_id,
        "model": "gpt-5.6-sol",
        "effort": "high",
        "approval_policy": "never",
        "approvals_reviewer": "auto_review",
        "sandbox_policy": "workspace-write",
        "collaboration_mode": {"mode": "default"},
        "multi_agent_mode": "disabled",
        "multi_agent_version": 1,
        "workspace_roots": ["/private/isolated-checkout"],
    }


def _token_event(total: int, minute: int) -> dict[str, object]:
    return {
        "timestamp": _time(minute),
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"total_token_usage": {"total_tokens": total}},
        },
    }


def _time(minute: int, *, milliseconds: int = 0) -> str:
    value = _BASE_TIME + timedelta(minutes=minute, milliseconds=milliseconds)
    return value.isoformat().replace("+00:00", "Z")
