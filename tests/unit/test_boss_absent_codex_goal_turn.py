from __future__ import annotations

import pytest

from aico.app.boss_absent_codex_goal_turn import (
    interrupt_codex_goal_turn,
    resume_codex_goal_thread,
    supervise_codex_goal_turn,
)


class FakeTurnTransport:
    def __init__(self, *, turn_tokens: int = 120, goal_after: int = 220) -> None:
        self._goal_reads = iter((100, goal_after))
        self._turn_tokens = turn_tokens
        self.requests: list[tuple[str, dict[str, object]]] = []
        self.notifications: list[tuple[str, str, str]] = []

    def request(self, method: str, params: dict[str, object]) -> dict[str, object]:
        self.requests.append((method, params))
        if method == "thread/goal/get":
            return {"goal": {"tokensUsed": next(self._goal_reads), "status": "active"}}
        if method == "turn/start":
            return {"turn": {"id": "turn-1", "status": "inProgress"}}
        raise AssertionError(method)

    def next_notification(
        self,
        method: str,
        *,
        thread_id: str,
        turn_id: str,
    ) -> dict[str, object]:
        self.notifications.append((method, thread_id, turn_id))
        if method == "turn/completed":
            return {"threadId": thread_id, "turn": {"id": turn_id, "status": "completed"}}
        return {
            "threadId": thread_id,
            "turnId": turn_id,
            "tokenUsage": {"total": {"totalTokens": self._turn_tokens}},
        }


def test_turn_supervisor_binds_model_effort_completion_and_dual_usage() -> None:
    transport = FakeTurnTransport()

    receipt = supervise_codex_goal_turn(
        transport,
        thread_id="thread-1",
        prompt="bounded task",
        model="gpt-5.6-sol",
        reasoning_effort="high",
    )

    assert receipt.goal_token_delta == 120
    assert receipt.turn_total_tokens == 120
    assert receipt.usage_consistent
    turn_params = transport.requests[1][1]
    assert turn_params["model"] == "gpt-5.6-sol"
    assert turn_params["effort"] == "high"
    assert turn_params["approvalPolicy"] == "never"
    assert transport.notifications == [
        ("turn/completed", "thread-1", "turn-1"),
        ("thread/tokenUsage/updated", "thread-1", "turn-1"),
    ]


def test_turn_supervisor_rejects_goal_provider_usage_mismatch() -> None:
    transport = FakeTurnTransport(turn_tokens=120, goal_after=221)

    with pytest.raises(ValueError, match="do not match"):
        supervise_codex_goal_turn(
            transport,
            thread_id="thread-1",
            prompt="bounded task",
            model="gpt-5.6-sol",
            reasoning_effort="high",
        )


def test_turn_supervisor_rejects_noncompleted_turn() -> None:
    transport = FakeTurnTransport()

    def failed_notification(
        method: str,
        *,
        thread_id: str,
        turn_id: str,
    ) -> dict[str, object]:
        assert method == "turn/completed"
        return {"threadId": thread_id, "turn": {"id": turn_id, "status": "failed"}}

    transport.next_notification = failed_notification  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="completed"):
        supervise_codex_goal_turn(
            transport,
            thread_id="thread-1",
            prompt="bounded task",
            model="gpt-5.6-sol",
            reasoning_effort="high",
        )


def test_resume_rebinds_safety_and_proves_goal_tokens_survived_restart() -> None:
    class ResumeTransport(FakeTurnTransport):
        def request(self, method: str, params: dict[str, object]) -> dict[str, object]:
            self.requests.append((method, params))
            if method == "thread/resume":
                return {
                    "thread": {"id": "thread-1"},
                    "model": "gpt-5.6-sol",
                    "approvalPolicy": "never",
                    "sandbox": {"type": "readOnly", "networkAccess": False},
                }
            if method == "thread/goal/get":
                return {"goal": {"tokensUsed": 120, "status": "active"}}
            raise AssertionError(method)

    transport = ResumeTransport()

    receipt = resume_codex_goal_thread(
        transport,
        thread_id="thread-1",
        model="gpt-5.6-sol",
        expected_goal_tokens=120,
    )

    assert receipt.goal_tokens_preserved == 120
    assert transport.requests[0][1]["excludeTurns"] is True
    assert transport.requests[0][1]["sandbox"] == "read-only"


def test_interrupt_requires_matching_durable_interrupted_notification() -> None:
    class InterruptTransport(FakeTurnTransport):
        def request(self, method: str, params: dict[str, object]) -> dict[str, object]:
            self.requests.append((method, params))
            return {}

        def next_notification(
            self,
            method: str,
            *,
            thread_id: str,
            turn_id: str,
        ) -> dict[str, object]:
            return {
                "threadId": thread_id,
                "turn": {"id": turn_id, "status": "interrupted"},
            }

    transport = InterruptTransport()

    receipt = interrupt_codex_goal_turn(
        transport,
        thread_id="thread-1",
        turn_id="turn-1",
    )

    assert receipt.terminal_status == "interrupted"
    assert transport.requests == [("turn/interrupt", {"threadId": "thread-1", "turnId": "turn-1"})]
