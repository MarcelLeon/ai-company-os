"""Operator CLI for durable memory integrity and recovery."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from aico.app.memory_recovery import (
    MemoryBackupSummary,
    MemoryDrillSummary,
    MemoryRecoveryError,
    MemoryRestoreSummary,
    create_memory_backup,
    drill_memory_backup,
    restore_memory_backup,
    verify_memory_backup,
)
from aico.core.memory_ledger import (
    MemoryIntegrityError,
    MemoryLedgerSummary,
    seal_legacy_memory_ledger,
    verify_memory_ledger,
)


def run(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    environ: dict[str, str] | None = None,
) -> int:
    args = _parser().parse_args(argv)
    environment = dict(os.environ) if environ is None else environ
    result: MemoryBackupSummary | MemoryDrillSummary | MemoryRestoreSummary
    try:
        if args.command == "verify-backup":
            result = verify_memory_backup(args.backup, expected_sha256=args.expected_sha256)
        elif args.command == "drill-backup":
            result = drill_memory_backup(
                args.backup,
                expected_sha256=args.expected_sha256,
                workspace=args.workspace,
                report_path=args.report,
            )
        else:
            memory_path = args.memory_log or _path(environment, "AICO_MEMORY_PATH")
            if memory_path is None:
                stderr.write("Memory path is required via --memory-log or AICO_MEMORY_PATH.\n")
                return 2
            if args.command == "backup":
                result = create_memory_backup(memory_path, args.output)
            elif args.command == "restore":
                state_db = args.state_db or _path(environment, "AICO_STATE_DB_PATH")
                if state_db is None:
                    stderr.write(
                        "State database path is required via --state-db or AICO_STATE_DB_PATH.\n"
                    )
                    return 2
                result = restore_memory_backup(
                    memory_path,
                    args.backup,
                    expected_sha256=args.expected_sha256,
                    state_db_path=state_db,
                    preservation_path=args.preservation_output,
                    base_dir=Path.cwd(),
                    confirmed=args.yes,
                )
            else:
                summary = (
                    seal_legacy_memory_ledger(memory_path)
                    if args.command == "seal"
                    else verify_memory_ledger(memory_path)
                )
                stdout.write(_summary_json(args.command, summary) + "\n")
                return 0
    except (MemoryIntegrityError, MemoryRecoveryError, OSError, ValueError) as exc:
        stderr.write(f"Memory {args.command} failed: {exc}\n")
        return 2
    stdout.write(result.model_dump_json() + "\n")
    return 0


def main() -> None:
    raise SystemExit(run())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seal, verify, drill, back up, or restore an AICO memory JSONL ledger."
    )
    parser.add_argument(
        "--memory-log", type=Path, help="Memory JSONL path. Defaults to AICO_MEMORY_PATH."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify", help="Verify the live ledger and checkpoint")
    commands.add_parser("seal", help="Explicitly anchor an owner-reviewed legacy ledger")
    backup = commands.add_parser("backup", help="Create a verified portable recovery point")
    backup.add_argument("--output", required=True, type=Path)
    verify = commands.add_parser("verify-backup", help="Verify a recovery point offline")
    verify.add_argument("--backup", required=True, type=Path)
    verify.add_argument("--expected-sha256")
    drill = commands.add_parser("drill-backup", help="Run a disposable restore drill")
    drill.add_argument("--backup", required=True, type=Path)
    drill.add_argument("--expected-sha256", required=True)
    drill.add_argument("--workspace", type=Path)
    drill.add_argument("--report", type=Path)
    restore = commands.add_parser("restore", help="Owner-fenced stop-the-world restore")
    restore.add_argument("--backup", required=True, type=Path)
    restore.add_argument("--expected-sha256", required=True)
    restore.add_argument("--state-db", type=Path)
    restore.add_argument("--preservation-output", required=True, type=Path)
    restore.add_argument("--yes", action="store_true")
    return parser


def _path(environ: dict[str, str], key: str) -> Path | None:
    value = environ.get(key, "").strip()
    return Path(value).expanduser() if value else None


def _summary_json(operation: str, summary: MemoryLedgerSummary) -> str:
    return json.dumps(
        {
            "byte_size": summary.byte_size,
            "checkpoint_lag": summary.checkpoint_lag,
            "operation": operation,
            "record_count": summary.record_count,
            "sealed": summary.sealed,
            "status": "ok",
        },
        sort_keys=True,
    )
