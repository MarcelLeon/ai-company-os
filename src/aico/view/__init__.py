"""AICO read-only mobile-friendly Web view.

Strict scope (ADR-0033):
- Read-only. Every mutation belongs in IM commands.
- One process per AICO instance — point it at the same JSONL/SQLite
  files as the running orchestrator and you can browse what happened.
- Three views: Timeline (cross-source events), Task Trace (one trace_id
  end-to-end), Memory Tree (fact + experience relationships).
- No JS framework; one CSS file, mobile-first.
"""

from __future__ import annotations

from aico.view.app import build_view_app

__all__ = ["build_view_app"]
