"""aico-view token auth posture: loopback bypass + 401 on non-loopback."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aico.core import JsonlMemoryStore
from aico.view.app import ViewSettings, build_view_app
from aico.view.auth import TokenGuard, is_loopback_host


def _settings(tmp_path: Path) -> ViewSettings:
    JsonlMemoryStore(tmp_path / "memory.jsonl")
    return ViewSettings(
        audit_log_path=tmp_path / "audit.jsonl",
        memory_path=tmp_path / "memory.jsonl",
        state_db_path=None,
        project_ids=("aico",),
    )


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("127.0.0.1", True),
        ("localhost", True),
        ("127.5.5.5", True),
        ("::1", True),
        ("0.0.0.0", True),
        ("10.0.0.1", False),
        ("example.com", False),
        ("", True),
    ],
)
def test_is_loopback_host(host: str, expected: bool) -> None:
    assert is_loopback_host(host) is expected


def test_loopback_without_token_allows_access(tmp_path: Path) -> None:
    guard = TokenGuard(token=None, allow_unauthenticated=True)
    client = TestClient(build_view_app(_settings(tmp_path), token_guard=guard))

    response = client.get("/")
    assert response.status_code == 200


def test_non_loopback_without_token_blocks_access(tmp_path: Path) -> None:
    guard = TokenGuard(token=None, allow_unauthenticated=False)
    client = TestClient(build_view_app(_settings(tmp_path), token_guard=guard))

    response = client.get("/")
    assert response.status_code == 401
    assert "AICO_VIEW_TOKEN" in response.json()["detail"]


def test_token_in_header_grants_access(tmp_path: Path) -> None:
    guard = TokenGuard(token="s3cret", allow_unauthenticated=False)
    client = TestClient(build_view_app(_settings(tmp_path), token_guard=guard))

    response = client.get("/", headers={"X-AICO-Token": "s3cret"})
    assert response.status_code == 200


def test_token_in_query_string_grants_access(tmp_path: Path) -> None:
    guard = TokenGuard(token="s3cret", allow_unauthenticated=False)
    client = TestClient(build_view_app(_settings(tmp_path), token_guard=guard))

    response = client.get("/?token=s3cret")
    assert response.status_code == 200


def test_wrong_token_returns_401(tmp_path: Path) -> None:
    guard = TokenGuard(token="s3cret", allow_unauthenticated=False)
    client = TestClient(build_view_app(_settings(tmp_path), token_guard=guard))

    response = client.get("/?token=wrong")
    assert response.status_code == 401
    assert "invalid or missing aico-view token" in response.json()["detail"]


def test_healthz_does_not_require_token(tmp_path: Path) -> None:
    guard = TokenGuard(token="s3cret", allow_unauthenticated=False)
    client = TestClient(build_view_app(_settings(tmp_path), token_guard=guard))

    response = client.get("/healthz")
    assert response.status_code == 200


def test_static_css_does_not_require_token(tmp_path: Path) -> None:
    guard = TokenGuard(token="s3cret", allow_unauthenticated=False)
    client = TestClient(build_view_app(_settings(tmp_path), token_guard=guard))

    response = client.get("/static/style.css")
    assert response.status_code == 200


def test_trace_view_requires_token(tmp_path: Path) -> None:
    guard = TokenGuard(token="s3cret", allow_unauthenticated=False)
    client = TestClient(build_view_app(_settings(tmp_path), token_guard=guard))

    response = client.get("/trace/task-anything")
    assert response.status_code == 401


def test_memory_view_requires_token(tmp_path: Path) -> None:
    guard = TokenGuard(token="s3cret", allow_unauthenticated=False)
    client = TestClient(build_view_app(_settings(tmp_path), token_guard=guard))

    response = client.get("/memory")
    assert response.status_code == 401
