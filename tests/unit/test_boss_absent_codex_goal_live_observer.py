from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aico.app.boss_absent_codex_goal_capability import (
    CodexGoalNativeHostCandidateReceipt,
)
from aico.app.boss_absent_codex_goal_live_observer import (
    CodexDesktopHostProcessObservation,
    admit_codex_goal_host_from_live_observation,
    begin_codex_goal_live_observation,
    finalize_codex_goal_live_observation,
    inspect_codex_desktop_host,
)
from aico.app.boss_absent_codex_goal_probe import CodexGoalStateObservation

_THREAD_ID = "019f83fb-dde5-7c93-a163-81211d22d7ff"
_CONTRACT_SHA = "a" * 64
_COMMAND_SHA = "b" * 64
_PARENT_SHA = "c" * 64
_BASE_TIME = datetime(2026, 7, 23, 4, 0, tzinfo=UTC)


def test_live_observer_admits_same_session_native_continuation_after_restart(
    tmp_path: Path,
) -> None:
    session = tmp_path / "rollout.jsonl"
    _write_prefix(session)
    candidate = _candidate()
    intent = begin_codex_goal_live_observation(
        candidate,
        session_path=session,
        thread_id=_THREAD_ID,
        host=_host(100, started_at=_BASE_TIME, observed_at=_BASE_TIME + timedelta(minutes=1)),
        goal=_goal(tokens=100),
        observed_at=_BASE_TIME + timedelta(minutes=1),
    )
    _append_native_continuation(session)

    receipt = finalize_codex_goal_live_observation(
        intent,
        candidate,
        session_path=session,
        thread_id=_THREAD_ID,
        host_after=_host(
            200,
            started_at=_BASE_TIME + timedelta(minutes=2),
            observed_at=_BASE_TIME + timedelta(minutes=6),
        ),
        goal_after=_goal(tokens=220),
        old_host_terminated=True,
        observed_at=_BASE_TIME + timedelta(minutes=6),
    )

    assert receipt.formal_run_admitted
    assert receipt.host_restart_observed
    assert receipt.persistent_session_resumed
    assert receipt.native_continuation_observed
    assert receipt.runner_protocol_writes == 0
    assert receipt.goal_token_delta == 120
    assert receipt.provider_token_delta == 100
    assert receipt.continuation.automatic_start_delay_ms == 2
    admission = admit_codex_goal_host_from_live_observation(candidate, receipt)
    assert admission.formal_run_admitted
    assert admission.continuation_owner == "native_codex_host"


@pytest.mark.parametrize(
    "mutation",
    (
        "same_pid",
        "old_host_alive",
        "manual_context",
        "capability_drift",
        "missing_completion",
        "goal_usage_static",
        "provider_usage_static",
    ),
)
def test_live_observer_rejects_weak_or_runner_managed_evidence(
    tmp_path: Path,
    mutation: str,
) -> None:
    session = tmp_path / "rollout.jsonl"
    _write_prefix(session)
    candidate = _candidate()
    intent = begin_codex_goal_live_observation(
        candidate,
        session_path=session,
        thread_id=_THREAD_ID,
        host=_host(100, started_at=_BASE_TIME, observed_at=_BASE_TIME + timedelta(minutes=1)),
        goal=_goal(tokens=100),
        observed_at=_BASE_TIME + timedelta(minutes=1),
    )
    _append_native_continuation(
        session,
        manual_context=mutation == "manual_context",
        capability_drift=mutation == "capability_drift",
        include_completion=mutation != "missing_completion",
        provider_total=100 if mutation == "provider_usage_static" else 200,
    )
    pid = 100 if mutation == "same_pid" else 200
    goal_tokens = 100 if mutation == "goal_usage_static" else 220

    with pytest.raises(ValueError):
        finalize_codex_goal_live_observation(
            intent,
            candidate,
            session_path=session,
            thread_id=_THREAD_ID,
            host_after=_host(
                pid,
                started_at=_BASE_TIME + timedelta(minutes=2),
                observed_at=_BASE_TIME + timedelta(minutes=6),
            ),
            goal_after=_goal(tokens=goal_tokens),
            old_host_terminated=mutation != "old_host_alive",
            observed_at=_BASE_TIME + timedelta(minutes=6),
        )


def test_live_observer_rejects_rewritten_session_prefix(tmp_path: Path) -> None:
    session = tmp_path / "rollout.jsonl"
    _write_prefix(session)
    candidate = _candidate()
    intent = begin_codex_goal_live_observation(
        candidate,
        session_path=session,
        thread_id=_THREAD_ID,
        host=_host(100, started_at=_BASE_TIME, observed_at=_BASE_TIME + timedelta(minutes=1)),
        goal=_goal(tokens=100),
        observed_at=_BASE_TIME + timedelta(minutes=1),
    )
    payload = session.read_bytes()
    session.write_bytes(payload.replace(b"Codex Desktop", b"Codex Forgery") + b"{}\n")

    with pytest.raises(ValueError, match="prefix was rewritten"):
        finalize_codex_goal_live_observation(
            intent,
            candidate,
            session_path=session,
            thread_id=_THREAD_ID,
            host_after=_host(
                200,
                started_at=_BASE_TIME + timedelta(minutes=2),
                observed_at=_BASE_TIME + timedelta(minutes=6),
            ),
            goal_after=_goal(tokens=220),
            old_host_terminated=True,
            observed_at=_BASE_TIME + timedelta(minutes=6),
        )


def test_desktop_host_inspector_binds_exact_app_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = Path("/Applications/ChatGPT.app")
    embedded = app / "Contents/Resources/codex"
    outputs = iter(
        (
            subprocess.CompletedProcess(
                (),
                0,
                (
                    "69495 Thu Jul 23 12:07:36 2026     "
                    f"{embedded} -c features.code_mode_host=true "
                    "app-server --analytics-default-enabled\n"
                ),
                "",
            ),
            subprocess.CompletedProcess(
                (),
                0,
                f"{app}/Contents/MacOS/ChatGPT\n",
                "",
            ),
        )
    )
    monkeypatch.setattr(
        "aico.app.boss_absent_codex_goal_live_observer.subprocess.run",
        lambda *_, **__: next(outputs),
    )

    observed = inspect_codex_desktop_host(
        69964,
        app_bundle=app,
        embedded_codex=embedded,
        observed_at=datetime(2026, 7, 23, 5, tzinfo=UTC),
    )

    assert observed is not None
    assert observed.pid == 69964
    assert observed.parent_pid == 69495
    assert observed.started_at < observed.observed_at


def _candidate() -> CodexGoalNativeHostCandidateReceipt:
    return CodexGoalNativeHostCandidateReceipt(
        contract_sha256=_CONTRACT_SHA,
        app_version="26.715.72359",
        app_build="5718",
        app_cdhash_sha256="d" * 64,
        embedded_cli_cdhash_sha256="e" * 64,
        team_identifier="2DC432GLL2",
        codex_cli_version="0.145.0-alpha.30",
        schema_bundle_sha256="f" * 64,
    )


def _goal(*, tokens: int) -> CodexGoalStateObservation:
    return CodexGoalStateObservation(
        thread_id=_THREAD_ID,
        status="active",
        token_budget=1_000,
        tokens_used=tokens,
        time_used_seconds=tokens,
    )


def _host(
    pid: int,
    *,
    started_at: datetime,
    observed_at: datetime,
) -> CodexDesktopHostProcessObservation:
    return CodexDesktopHostProcessObservation(
        pid=pid,
        parent_pid=pid - 1,
        started_at=started_at,
        observed_at=observed_at,
        command_sha256=_COMMAND_SHA,
        parent_command_sha256=_PARENT_SHA,
    )


def _write_prefix(path: Path) -> None:
    events = (
        {
            "timestamp": _time(0),
            "type": "session_meta",
            "payload": {
                "id": _THREAD_ID,
                "originator": "Codex Desktop",
            },
        },
        {
            "timestamp": _time(0),
            "type": "turn_context",
            "payload": _context_payload("initial-turn"),
        },
        _token_event(100, minute=1),
        {
            "timestamp": _time(1),
            "type": "event_msg",
            "payload": {
                "type": "task_started",
                "turn_id": "pre-restart-turn",
            },
        },
    )
    path.write_text("".join(f"{json.dumps(event)}\n" for event in events))


def _append_native_continuation(
    path: Path,
    *,
    manual_context: bool = False,
    capability_drift: bool = False,
    include_completion: bool = True,
    provider_total: int = 200,
) -> None:
    previous = "pre-restart-turn"
    continued = "native-continuation-turn"
    marker = (
        '<codex_internal_context source="user">'
        if manual_context
        else '<codex_internal_context source="goal">'
    )
    events: list[dict[str, object]] = [
        _task_event("task_complete", previous, minute=3),
        _task_event("task_started", continued, minute=3, milliseconds=2),
        {
            "timestamp": _time(3, milliseconds=3),
            "type": "turn_context",
            "payload": _context_payload(
                continued,
                model="gpt-5.6-terra" if capability_drift else "gpt-5.6-sol",
            ),
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
                        "text": f"{marker}\nredacted\n</codex_internal_context>",
                    }
                ],
                "internal_chat_message_metadata_passthrough": {"turn_id": continued},
            },
        },
        _token_event(provider_total, minute=4),
    ]
    if include_completion:
        events.append(_task_event("task_complete", continued, minute=5))
    with path.open("a") as output:
        output.write("".join(f"{json.dumps(event)}\n" for event in events))


def _task_event(
    event_type: str,
    turn_id: str,
    *,
    minute: int,
    milliseconds: int = 0,
) -> dict[str, object]:
    return {
        "timestamp": _time(minute, milliseconds=milliseconds),
        "type": "event_msg",
        "payload": {"type": event_type, "turn_id": turn_id},
    }


def _context_payload(turn_id: str, *, model: str = "gpt-5.6-sol") -> dict[str, object]:
    return {
        "turn_id": turn_id,
        "model": model,
        "effort": "high",
        "approval_policy": "never",
        "approvals_reviewer": "auto_review",
        "sandbox_policy": "workspace-write",
        "collaboration_mode": {"mode": "default"},
        "multi_agent_mode": "disabled",
        "multi_agent_version": 1,
        "workspace_roots": ["/private/isolated-checkout"],
    }


def _token_event(total: int, *, minute: int) -> dict[str, object]:
    return {
        "timestamp": _time(minute),
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"total_token_usage": {"total_tokens": total}},
        },
    }


def _time(minute: int, *, milliseconds: int = 0) -> str:
    observed = _BASE_TIME + timedelta(minutes=minute, milliseconds=milliseconds)
    return observed.isoformat().replace("+00:00", "Z")
