"""CLI prototype for local status-island glance surfaces."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from aico.core.audit import read_jsonl_audit_events
from aico.core.metrics import build_metrics_report
from aico.core.status_island import (
    build_status_island_snapshot,
    status_island_text,
    status_island_to_dict,
)


def run(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = _build_parser()
    args = parser.parse_args(argv)
    audit_log_path = args.audit_log or _audit_log_path_from_env()
    try:
        audit_events = read_jsonl_audit_events(audit_log_path) if audit_log_path else ()
    except ValueError as exc:
        error_output.write(f"failed to read audit log: {exc}\n")
        return 2
    report = build_metrics_report((), audit_events)
    snapshot = build_status_island_snapshot(report, max_tasks=args.max_tasks)
    if args.format == "json":
        output.write(
            json.dumps(status_island_to_dict(snapshot), ensure_ascii=False, sort_keys=True)
        )
        output.write("\n")
    else:
        output.write(status_island_text(snapshot))
        output.write("\n")
    return 0


def main() -> None:
    raise SystemExit(run())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aico-glance",
        description="Render a compact AICO status-island snapshot from audit JSONL.",
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=None,
        help="Path to audit JSONL. Defaults to AICO_AUDIT_LOG_PATH.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=5,
        help="Maximum recent tasks to include.",
    )
    return parser


def _audit_log_path_from_env() -> Path | None:
    value = os.environ.get("AICO_AUDIT_LOG_PATH")
    if not value:
        return None
    return Path(value)
