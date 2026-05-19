from typing import Any, cast

import httpx
from fastapi.testclient import TestClient

from aico.app.feishu_webhook import build_feishu_webhook_app
from aico.app.phase1 import Phase1Settings


def test_feishu_webhook_returns_url_verification_challenge() -> None:
    app = build_feishu_webhook_app(
        Phase1Settings(
            channel="feishu",
            feishu_app_id="app-id",
            feishu_app_secret="app-secret",
            feishu_verification_token="verify-token",
            feishu_event_path="/feishu/events",
            claude_command="claude -p",
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


def test_feishu_webhook_rejects_invalid_verification_token() -> None:
    app = build_feishu_webhook_app(
        Phase1Settings(
            channel="feishu",
            feishu_app_id="app-id",
            feishu_app_secret="app-secret",
            feishu_verification_token="verify-token",
            claude_command="claude -p",
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


def test_feishu_webhook_healthz() -> None:
    app = build_feishu_webhook_app(
        Phase1Settings(
            channel="feishu",
            feishu_app_id="app-id",
            feishu_app_secret="app-secret",
            claude_command="claude -p",
        ),
        feishu_client=cast(httpx.AsyncClient, FakeFeishuClient()),
    )

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
