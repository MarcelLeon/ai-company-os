"""Evidence-first app-server turn supervision for the Codex Goal baseline."""

from __future__ import annotations

from typing import Literal, Protocol, cast, runtime_checkable

from pydantic import Field

from aico.core.models import FrozenModel


@runtime_checkable
class CodexGoalTurnTransport(Protocol):
    def request(self, method: str, params: dict[str, object]) -> dict[str, object]: ...

    def next_notification(
        self,
        method: str,
        *,
        thread_id: str,
        turn_id: str,
    ) -> dict[str, object]: ...


class CodexGoalTurnReceipt(FrozenModel):
    version: Literal[1] = 1
    model: str = Field(min_length=1, max_length=128)
    reasoning_effort: str = Field(min_length=1, max_length=32)
    terminal_status: Literal["completed"] = "completed"
    turn_total_tokens: int = Field(ge=1)
    goal_tokens_before: int = Field(ge=0)
    goal_tokens_after: int = Field(ge=1)
    goal_token_delta: int = Field(ge=1)
    usage_consistent: Literal[True] = True
    goal_status_after: Literal["active", "complete", "blocked"]


class CodexGoalResumeReceipt(FrozenModel):
    version: Literal[1] = 1
    model: str = Field(min_length=1, max_length=128)
    approval_policy: Literal["never"] = "never"
    sandbox: Literal["read-only"] = "read-only"
    network_access: Literal[False] = False
    goal_tokens_preserved: int = Field(ge=0)
    goal_status: Literal["active", "complete", "blocked"]


class CodexGoalInterruptReceipt(FrozenModel):
    version: Literal[1] = 1
    terminal_status: Literal["interrupted"] = "interrupted"


def supervise_codex_goal_turn(
    transport: CodexGoalTurnTransport,
    *,
    thread_id: str,
    prompt: str,
    model: str,
    reasoning_effort: str,
) -> CodexGoalTurnReceipt:
    before = _goal(transport.request("thread/goal/get", {"threadId": thread_id}))
    tokens_before = _non_negative_int(before, "tokensUsed")
    started = transport.request(
        "turn/start",
        {
            "threadId": thread_id,
            "input": [{"type": "text", "text": prompt}],
            "model": model,
            "effort": reasoning_effort,
            "approvalPolicy": "never",
        },
    )
    turn = _mapping(started, "turn")
    turn_id = _text(turn, "id")
    completed = transport.next_notification(
        "turn/completed",
        thread_id=thread_id,
        turn_id=turn_id,
    )
    completed_turn = _mapping(completed, "turn")
    if completed_turn.get("id") != turn_id or completed_turn.get("status") != "completed":
        raise ValueError("Codex Goal turn did not reach completed status")
    usage = transport.next_notification(
        "thread/tokenUsage/updated",
        thread_id=thread_id,
        turn_id=turn_id,
    )
    total = _mapping(_mapping(usage, "tokenUsage"), "total")
    turn_total_tokens = _positive_int(total, "totalTokens")
    after = _goal(transport.request("thread/goal/get", {"threadId": thread_id}))
    tokens_after = _positive_int(after, "tokensUsed")
    delta = tokens_after - tokens_before
    if delta != turn_total_tokens:
        raise ValueError("Codex Goal and turn provider usage do not match")
    status = after.get("status")
    if status not in {"active", "complete", "blocked"}:
        raise ValueError("Codex Goal returned an unsupported post-turn status")
    goal_status = cast(Literal["active", "complete", "blocked"], status)
    return CodexGoalTurnReceipt(
        model=model,
        reasoning_effort=reasoning_effort,
        turn_total_tokens=turn_total_tokens,
        goal_tokens_before=tokens_before,
        goal_tokens_after=tokens_after,
        goal_token_delta=delta,
        goal_status_after=goal_status,
    )


def resume_codex_goal_thread(
    transport: CodexGoalTurnTransport,
    *,
    thread_id: str,
    model: str,
    expected_goal_tokens: int,
) -> CodexGoalResumeReceipt:
    resumed = transport.request(
        "thread/resume",
        {
            "threadId": thread_id,
            "model": model,
            "approvalPolicy": "never",
            "sandbox": "read-only",
            "excludeTurns": True,
        },
    )
    thread = _mapping(resumed, "thread")
    if thread.get("id") != thread_id or resumed.get("model") != model:
        raise ValueError("Codex Goal resumed thread identity or model drifted")
    if resumed.get("approvalPolicy") != "never":
        raise ValueError("Codex Goal resumed approval policy drifted")
    sandbox = _mapping(resumed, "sandbox")
    if sandbox.get("type") != "readOnly" or sandbox.get("networkAccess") is not False:
        raise ValueError("Codex Goal resumed sandbox drifted")
    goal = _goal(transport.request("thread/goal/get", {"threadId": thread_id}))
    tokens = _non_negative_int(goal, "tokensUsed")
    if tokens != expected_goal_tokens:
        raise ValueError("Codex Goal tokens were not preserved across restart")
    status = goal.get("status")
    if status not in {"active", "complete", "blocked"}:
        raise ValueError("Codex Goal resumed with unsupported status")
    goal_status = cast(Literal["active", "complete", "blocked"], status)
    return CodexGoalResumeReceipt(
        model=model,
        goal_tokens_preserved=tokens,
        goal_status=goal_status,
    )


def interrupt_codex_goal_turn(
    transport: CodexGoalTurnTransport,
    *,
    thread_id: str,
    turn_id: str,
) -> CodexGoalInterruptReceipt:
    transport.request("turn/interrupt", {"threadId": thread_id, "turnId": turn_id})
    completed = transport.next_notification(
        "turn/completed",
        thread_id=thread_id,
        turn_id=turn_id,
    )
    turn = _mapping(completed, "turn")
    if turn.get("id") != turn_id or turn.get("status") != "interrupted":
        raise ValueError("Codex Goal turn interrupt was not durably observed")
    return CodexGoalInterruptReceipt()


def _goal(payload: dict[str, object]) -> dict[str, object]:
    return _mapping(payload, "goal")


def _mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError("Codex Goal turn evidence is missing a required object")
    return value


def _text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError("Codex Goal turn evidence is missing an identifier")
    return value


def _non_negative_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Codex Goal turn evidence has invalid usage")
    return value


def _positive_int(payload: dict[str, object], key: str) -> int:
    value = _non_negative_int(payload, key)
    if value == 0:
        raise ValueError("Codex Goal turn evidence is missing positive usage")
    return value
