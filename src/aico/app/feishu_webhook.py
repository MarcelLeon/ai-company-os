"""FastAPI deployment entrypoint for Feishu event callbacks."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request

from aico.app.phase1 import Phase1Runtime, Phase1Settings, build_phase1_runtime, configure_logging
from aico.channel import FeishuAPIError, FeishuChannel

log = logging.getLogger(__name__)


def build_feishu_webhook_app(
    settings: Phase1Settings,
    *,
    feishu_client: httpx.AsyncClient | None = None,
) -> FastAPI:
    """Build a FastAPI app that exposes Feishu callbacks to the AICO orchestrator."""

    feishu_settings = settings.model_copy(update={"channel": "feishu"})
    runtime = build_phase1_runtime(feishu_settings, feishu_client=feishu_client)
    channel = _feishu_channel(runtime)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.aico_runtime = runtime
        await runtime.start()
        try:
            yield
        finally:
            await runtime.stop()

    app = FastAPI(title="AI Company OS Feishu Webhook", lifespan=lifespan)
    app.state.aico_runtime = runtime

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(feishu_settings.feishu_event_path)
    async def feishu_events(request: Request) -> dict[str, Any]:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Feishu payload must be a JSON object")
        try:
            result = await channel.handle_event(payload)
        except FeishuAPIError as exc:
            log.warning("Feishu event rejected: %s", exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ok": True} if result is None else result

    return app


def main() -> None:
    settings = Phase1Settings()
    configure_logging(settings)
    uvicorn.run(
        build_feishu_webhook_app(settings),
        host=settings.feishu_webhook_host,
        port=settings.feishu_webhook_port,
    )


def _feishu_channel(runtime: Phase1Runtime) -> FeishuChannel:
    if not isinstance(runtime.channel, FeishuChannel):
        raise ValueError("Feishu webhook runtime requires AICO_CHANNEL=feishu")
    return runtime.channel
