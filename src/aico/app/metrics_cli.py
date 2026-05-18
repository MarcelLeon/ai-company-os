"""CLI reader for persisted observability metrics."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from aico.core.audit import read_jsonl_audit_events
from aico.core.command_messages import metrics_report_text
from aico.core.metrics import build_metrics_report, metrics_report_to_dict


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
    if args.format == "json":
        output.write(json.dumps(metrics_report_to_dict(report), ensure_ascii=False, sort_keys=True))
        output.write("\n")
    else:
        output.write(metrics_report_text(report))
        output.write("\n")
    return 0


def main() -> None:
    raise SystemExit(run())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aico-metrics",
        description="Render AICO metrics from persisted audit JSONL.",
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
    return parser


def _audit_log_path_from_env() -> Path | None:
    value = os.environ.get("AICO_AUDIT_LOG_PATH")
    if not value:
        return None
    return Path(value)
