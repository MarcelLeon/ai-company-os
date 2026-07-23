from __future__ import annotations

import pytest

from aico.app.boss_absent_codex_goal_host import (
    CodexGoalHostCapabilities,
    CodexGoalHostKind,
    CodexGoalHostRunReceipt,
    CodexGoalHostTurnReceipt,
    CodexGoalTurnSource,
    GoalStatus,
    admit_codex_goal_host,
)

_CONTRACT_SHA = "a" * 64
_ADMISSION_SHA = "b" * 64


def _capabilities(**updates: object) -> CodexGoalHostCapabilities:
    payload: dict[str, object] = {
        "contract_sha256": _CONTRACT_SHA,
        "host_build": "codex-desktop-2026.07.23",
        "host_kind": CodexGoalHostKind.NATIVE_CODEX_HOST,
        "native_continuation_available": True,
        "runner_constructs_continuation_input": False,
        "persistent_thread_resume": True,
        "isolated_run_state": True,
        "provider_usage_observable": True,
        "default_capabilities_only": True,
    }
    return CodexGoalHostCapabilities.model_validate(payload | updates)


def _turn(
    sequence: int,
    *,
    source: CodexGoalTurnSource,
    before: int,
    after: int,
    status: GoalStatus = "active",
    previous: str | None = None,
) -> CodexGoalHostTurnReceipt:
    return CodexGoalHostTurnReceipt(
        sequence=sequence,
        source=source,
        previous_turn_sha256=previous,
        turn_sha256=f"{sequence:x}" * 64,
        opaque_input_sha256=f"{sequence + 8:x}" * 64,
        goal_status_after=status,
        goal_tokens_before=before,
        goal_tokens_after=after,
        goal_token_budget=1_000,
        provider_total_tokens=after - before,
        human_interventions=int(source is CodexGoalTurnSource.OWNER_TAKEOVER),
    )


def test_native_host_admission_keeps_continuation_input_opaque() -> None:
    receipt = admit_codex_goal_host(_capabilities())

    assert receipt.formal_run_admitted
    assert receipt.continuation_owner == "native_codex_host"
    assert receipt.continuation_input_opaque


@pytest.mark.parametrize(
    "updates",
    (
        {"host_kind": CodexGoalHostKind.STANDALONE_APP_SERVER},
        {"native_continuation_available": False},
        {"persistent_thread_resume": False},
        {"isolated_run_state": False},
        {"provider_usage_observable": False},
        {"default_capabilities_only": False},
        {"runner_constructs_continuation_input": True},
    ),
)
def test_host_admission_rejects_invalid_baseline_boundaries(updates: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        admit_codex_goal_host(_capabilities(**updates))


def test_host_run_accepts_native_continuation_with_closed_usage_chain() -> None:
    first = _turn(
        1,
        source=CodexGoalTurnSource.INITIAL_TASK,
        before=0,
        after=100,
    )
    second = _turn(
        2,
        source=CodexGoalTurnSource.NATIVE_HOST_CONTINUATION,
        before=100,
        after=220,
        status="complete",
        previous=first.turn_sha256,
    )

    receipt = CodexGoalHostRunReceipt(
        contract_sha256=_CONTRACT_SHA,
        host_admission_sha256=_ADMISSION_SHA,
        turns=(first, second),
        total_tokens=220,
        human_interventions=0,
        terminal_status="complete",
    )

    assert receipt.total_tokens == 220
    assert receipt.terminal_status == "complete"


def test_host_run_rejects_runner_usage_or_chain_drift() -> None:
    first = _turn(
        1,
        source=CodexGoalTurnSource.INITIAL_TASK,
        before=0,
        after=100,
    )
    broken = _turn(
        2,
        source=CodexGoalTurnSource.NATIVE_HOST_CONTINUATION,
        before=101,
        after=221,
        status="complete",
        previous="f" * 64,
    )

    with pytest.raises(ValueError, match="chain is broken"):
        CodexGoalHostRunReceipt(
            contract_sha256=_CONTRACT_SHA,
            host_admission_sha256=_ADMISSION_SHA,
            turns=(first, broken),
            total_tokens=220,
            human_interventions=0,
            terminal_status="complete",
        )


def test_host_run_rejects_continuation_after_nonactive_goal() -> None:
    first = _turn(
        1,
        source=CodexGoalTurnSource.INITIAL_TASK,
        before=0,
        after=100,
        status="blocked",
    )
    second = _turn(
        2,
        source=CodexGoalTurnSource.OWNER_TAKEOVER,
        before=100,
        after=120,
        status="complete",
        previous=first.turn_sha256,
    )

    with pytest.raises(ValueError, match="continued after"):
        CodexGoalHostRunReceipt(
            contract_sha256=_CONTRACT_SHA,
            host_admission_sha256=_ADMISSION_SHA,
            turns=(first, second),
            total_tokens=120,
            human_interventions=1,
            terminal_status="complete",
        )


def test_turn_rejects_goal_provider_usage_mismatch_and_hidden_human_input() -> None:
    with pytest.raises(ValueError, match="usage do not match"):
        CodexGoalHostTurnReceipt(
            sequence=1,
            source=CodexGoalTurnSource.INITIAL_TASK,
            turn_sha256="1" * 64,
            opaque_input_sha256="9" * 64,
            goal_status_after="active",
            goal_tokens_before=0,
            goal_tokens_after=101,
            goal_token_budget=1_000,
            provider_total_tokens=100,
        )
    with pytest.raises(ValueError, match="intervention count"):
        turn = _turn(
            1,
            source=CodexGoalTurnSource.INITIAL_TASK,
            before=0,
            after=100,
        )
        CodexGoalHostTurnReceipt.model_validate(turn.model_dump() | {"human_interventions": 1})
