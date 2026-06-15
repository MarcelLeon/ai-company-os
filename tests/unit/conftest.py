"""Unit-test isolation for local dogfooding environment variables."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def isolate_aico_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unit tests independent from a running local AICO dogfood shell."""
    for key in tuple(os.environ):
        if key.startswith("AICO_"):
            monkeypatch.delenv(key, raising=False)
