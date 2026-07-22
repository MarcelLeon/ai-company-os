import json
from pathlib import Path
from typing import Any, cast

import httpx
from fastapi.testclient import TestClient

from aico.app.feishu_webhook import build_feishu_webhook_app
from aico.app.phase1 import Phase1Settings
from aico.app.runtime_owner import runtime_owner_lock_path, runtime_owner_status


def test_feishu_webhook_returns_url_verification_challenge(tmp_path: Path) -> None:
    app = build_feishu_webhook_app(
        Phase1Settings(
            channel="feishu",
            feishu_app_id="app-id",
            feishu_app_secret="app-secret",
            feishu_verification_token="verify-token",
            feishu_event_path="/feishu/events",
            claude_command="claude -p",
            runtime_heartbeat_path=None,
            state_db_path=tmp_path / "state.db",
        ),
        feishu_client=cast(httpx.AsyncClient, FakeFeishuClient()),
    )

    with TestClient(app) as client:
        response = client.post(
            "/feishu/events",
            json={
                "type": "url_verification",
                "token": "verify-token",
                "challenge": "challenge-code",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"challenge": "challenge-code"}


def test_feishu_webhook_rejects_invalid_verification_token(tmp_path: Path) -> None:
    app = build_feishu_webhook_app(
        Phase1Settings(
            channel="feishu",
            feishu_app_id="app-id",
            feishu_app_secret="app-secret",
            feishu_verification_token="verify-token",
            claude_command="claude -p",
            runtime_heartbeat_path=None,
            state_db_path=tmp_path / "state.db",
        ),
        feishu_client=cast(httpx.AsyncClient, FakeFeishuClient()),
    )

    with TestClient(app) as client:
        response = client.post(
            "/feishu/events",
            json={"type": "url_verification", "token": "wrong", "challenge": "nope"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid Feishu verification token"


def test_feishu_webhook_healthz(tmp_path: Path) -> None:
    app = build_feishu_webhook_app(
        Phase1Settings(
            channel="feishu",
            feishu_app_id="app-id",
            feishu_app_secret="app-secret",
            claude_command="claude -p",
            runtime_heartbeat_path=None,
            state_db_path=tmp_path / "state.db",
        ),
        feishu_client=cast(httpx.AsyncClient, FakeFeishuClient()),
    )

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_feishu_webhook_lifespan_owns_runtime_heartbeat(tmp_path: Path) -> None:
    heartbeat_path = tmp_path / "feishu-heartbeat.json"
    state_db_path = tmp_path / "state.db"
    owner_path = runtime_owner_lock_path(state_db_path, base_dir=tmp_path)
    app = build_feishu_webhook_app(
        Phase1Settings(
            channel="feishu",
            feishu_app_id="app-id",
            feishu_app_secret="app-secret",
            claude_command="claude -p",
            runtime_heartbeat_path=heartbeat_path,
            state_db_path=state_db_path,
        ),
        feishu_client=cast(httpx.AsyncClient, FakeFeishuClient()),
    )

    with TestClient(app) as client:
        client.get("/healthz")
        running = json.loads(heartbeat_path.read_text(encoding="utf-8"))
        assert running["schema_version"] == 5
        assert running["state"] == "running"
        assert running["self_healing"] == {
            "status": "healthy",
            "checked_at": running["self_healing"]["checked_at"],
            "components": [],
        }
        assert running["alerting"] == {
            "status": "disabled",
            "checked_at": running["alerting"]["checked_at"],
            "pending_events": 0,
        }
        assert running["liveness"] == {
            "status": "disabled",
            "checked_at": running["liveness"]["checked_at"],
            "last_success_at": None,
            "expires_at": None,
        }
        assert runtime_owner_status(owner_path).active is True

    stopped = json.loads(heartbeat_path.read_text(encoding="utf-8"))
    assert stopped["state"] == "stopped"
    assert runtime_owner_status(owner_path).active is False


class FakeFeishuClient:
    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        if url.endswith("/tenant_access_token/internal"):
            return _json_response({"code": 0, "tenant_access_token": "tenant-token"})
        return _json_response({"code": 0, "data": {"message_id": "om_message"}})

    async def aclose(self) -> None:
        return None


def _json_response(data: dict[str, Any]) -> httpx.Response:
    request = httpx.Request("POST", "https://open.feishu.cn")
    return httpx.Response(200, json=data, request=request)
