"""Inspect and reset the local AICO SQLite state database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from aico.core.sqlite_state import SQLiteStateDatabase


def run_state_cli(argv: list[str] | None = None, *, stdout: TextIO = sys.stdout) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    database = SQLiteStateDatabase(args.db)
    if args.command == "reset":
        if not args.yes:
            stdout.write("Refusing to reset without --yes.\n")
            return 2
        database.reset_state_tables()
        stdout.write(f"Reset AICO state tables in {database.path}\n")
        return 0

    stdout.write(_summary_text(database))
    return 0


def main() -> None:
    raise SystemExit(run_state_cli())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aico-state")
    parser.add_argument("--db", required=True, type=Path, help="Path to AICO SQLite state DB")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("summary", help="Print schema version and state table counts")
    reset = subparsers.add_parser("reset", help="Delete known AICO state rows")
    reset.add_argument("--yes", action="store_true", help="Confirm state table reset")
    parser.set_defaults(command="summary")
    return parser


def _summary_text(database: SQLiteStateDatabase) -> str:
    lines = [
        f"AICO state DB: {database.path}",
        f"schema_version: {database.schema_version()}",
        "tables:",
    ]
    counts = database.table_counts()
    if not counts:
        lines.append("- none")
    else:
        lines.extend(f"- {table}: {count}" for table, count in sorted(counts.items()))
    return "\n".join(lines) + "\n"
