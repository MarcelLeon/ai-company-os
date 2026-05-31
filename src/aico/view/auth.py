"""Token auth dependency for aico-view.

When AICO_VIEW_TOKEN is set in the environment, every request must carry
the token either as a query string (?token=...) or as the X-AICO-Token
header. Missing or wrong token → 401.

Behavior matrix (ADR-0035):
- Token in env, request matches            -> request passes through
- Token in env, request missing/wrong      -> 401 Unauthorized
- Token NOT in env, AICO_VIEW_HOST is loopback (127.* / ::1 / localhost)
                                           -> request passes through (local dev)
- Token NOT in env, AICO_VIEW_HOST != loopback
                                           -> ALL requests rejected with 401
                                              (refuse to expose unauth'd view)
"""

from __future__ import annotations

import logging
import os
import secrets

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


def is_loopback_host(host: str) -> bool:
    host = (host or "").strip().lower()
    if not host:
        return True
    if host in _LOOPBACK_HOSTS:
        return True
    return host.startswith("127.")


def token_from_env() -> str | None:
    value = os.environ.get("AICO_VIEW_TOKEN", "").strip()
    return value or None


def host_from_env() -> str:
    return os.environ.get("AICO_VIEW_HOST", "127.0.0.1")


class TokenGuard:
    """Resolved auth posture used by the FastAPI dependency."""

    def __init__(self, *, token: str | None, allow_unauthenticated: bool) -> None:
        self._token = token
        self._allow_unauthenticated = allow_unauthenticated

    @classmethod
    def from_env(cls) -> TokenGuard:
        token = token_from_env()
        host = host_from_env()
        allow_unauthenticated = token is None and is_loopback_host(host)
        if token is None and not allow_unauthenticated:
            logger.warning(
                "aico-view is bound to %s without AICO_VIEW_TOKEN; "
                "every request will be rejected. Set AICO_VIEW_TOKEN to enable.",
                host,
            )
        return cls(token=token, allow_unauthenticated=allow_unauthenticated)

    def check(self, request: Request) -> None:
        if self._allow_unauthenticated:
            return
        if self._token is None:
            raise HTTPException(
                status_code=401,
                detail=(
                    "aico-view is bound to a non-loopback host without "
                    "AICO_VIEW_TOKEN. Set AICO_VIEW_TOKEN before exposing."
                ),
            )
        supplied = request.headers.get("X-AICO-Token") or request.query_params.get("token") or ""
        if not supplied or not secrets.compare_digest(supplied, self._token):
            raise HTTPException(status_code=401, detail="invalid or missing aico-view token")
