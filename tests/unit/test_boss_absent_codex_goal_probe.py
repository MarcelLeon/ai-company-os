from __future__ import annotations

from pathlib import Path

import pytest

from aico.app.boss_absent_codex_goal_probe import (
    _clear_cleanup_intent,
    _read_cleanup_intent,
    _recover_cleanup_intent,
    _write_cleanup_intent,
    run_goal_lifecycle,
)


def test_goal_lifecycle_uses_persistent_thread_and_cleans_it_without_usage(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    lifecycle: list[tuple[str, str]] = []

    def request(method: str, params: dict[str, object]) -> dict[str, object]:
        calls.append((method, params))
        if method == "thread/start":
            return {
                "thread": {"id": "thread-probe", "ephemeral": False},
                "model": "gpt-5.6-sol",
                "approvalPolicy": "never",
                "sandbox": {"type": "readOnly", "networkAccess": False},
            }
        if method == "thread/goal/get":
            return {
                "goal": {
                    "status": "active",
                    "tokenBudget": 50_000,
                    "tokensUsed": 0,
                    "timeUsedSeconds": 0,
                }
            }
        return {}

    receipt = run_goal_lifecycle(
        request,
        codex_cli_version="0.144.5",
        model="gpt-5.6-sol",
        token_budget=50_000,
        cwd=tmp_path,
        on_thread_started=lambda thread_id: lifecycle.append(("started", thread_id)),
        on_thread_deleted=lambda thread_id: lifecycle.append(("deleted", thread_id)),
    )

    assert receipt.tokens_used == 0
    assert receipt.thread_deleted
    assert [method for method, _ in calls] == [
        "thread/start",
        "thread/goal/set",
        "thread/goal/get",
        "thread/goal/clear",
        "thread/delete",
    ]
    assert calls[0][1]["ephemeral"] is False
    assert calls[1][1]["tokenBudget"] == 50_000
    assert lifecycle == [
        ("started", "thread-probe"),
        ("deleted", "thread-probe"),
    ]


@pytest.mark.parametrize(
    ("ephemeral", "tokens_used", "message"),
    [
        (True, 0, "persistent"),
        (False, 1, "usage or goal settings"),
    ],
)
def test_goal_lifecycle_fails_closed_and_deletes_probe_thread(
    tmp_path: Path,
    ephemeral: bool,
    tokens_used: int,
    message: str,
) -> None:
    deleted: list[str] = []

    def request(method: str, params: dict[str, object]) -> dict[str, object]:
        if method == "thread/start":
            return {
                "thread": {"id": "thread-probe", "ephemeral": ephemeral},
                "model": "gpt-5.6-sol",
                "approvalPolicy": "never",
                "sandbox": {"type": "readOnly", "networkAccess": False},
            }
        if method == "thread/goal/get":
            return {
                "goal": {
                    "status": "active",
                    "tokenBudget": 50_000,
                    "tokensUsed": tokens_used,
                    "timeUsedSeconds": 0,
                }
            }
        if method == "thread/delete":
            deleted.append(str(params["threadId"]))
        return {}

    with pytest.raises(ValueError, match=message):
        run_goal_lifecycle(
            request,
            codex_cli_version="0.144.5",
            model="gpt-5.6-sol",
            token_budget=50_000,
            cwd=tmp_path,
        )

    assert deleted == ["thread-probe"]


def test_cleanup_intent_is_owner_only_bounded_and_removable(tmp_path: Path) -> None:
    intent_path = tmp_path / "goal.cleanup-intent.json"

    _write_cleanup_intent(intent_path, "thread-probe")

    assert intent_path.stat().st_mode & 0o777 == 0o600
    assert _read_cleanup_intent(intent_path).thread_id == "thread-probe"
    _clear_cleanup_intent(intent_path)
    assert not intent_path.exists()


def test_stale_cleanup_intent_reconnects_and_deletes_thread(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intent_path = tmp_path / "goal.cleanup-intent.json"
    isolated_home = tmp_path / "codex-home"
    isolated_home.mkdir()
    _write_cleanup_intent(intent_path, "thread-probe")
    deleted: list[str] = []

    class FakeConnection:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        def initialize(self) -> None:
            pass

        def request(self, method: str, params: dict[str, object]) -> dict[str, object]:
            assert method == "thread/delete"
            deleted.append(str(params["threadId"]))
            return {}

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        "aico.app.boss_absent_codex_goal_probe._AppServerConnection",
        FakeConnection,
    )

    assert _recover_cleanup_intent(
        "codex",
        intent_path,
        isolated_home_path=isolated_home,
        timeout_seconds=1,
    )
    assert deleted == ["thread-probe"]
    assert not intent_path.exists()
