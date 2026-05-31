"""CLI entrypoint that boots the read-only aico-view FastAPI app."""

from __future__ import annotations

import logging
import os

import uvicorn

from aico.view.app import build_view_app, load_view_settings_from_env

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("AICO_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_view_settings_from_env()
    host = os.environ.get("AICO_VIEW_HOST", "127.0.0.1")
    port = int(os.environ.get("AICO_VIEW_PORT", "8765"))
    log.info(
        "aico-view starting at http://%s:%d (audit=%s memory=%s state_db=%s)",
        host,
        port,
        settings.audit_log_path,
        settings.memory_path,
        settings.state_db_path,
    )
    uvicorn.run(build_view_app(settings), host=host, port=port)


if __name__ == "__main__":
    main()
