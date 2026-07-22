"""Operator CLI for independent dead-man receiver state recovery."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from pydantic import BaseModel

from aico.app.dead_man_receiver_recovery import (
    DeadManReceiverRecoveryError,
    create_dead_man_receiver_backup,
    drill_dead_man_receiver_backup,
    restore_dead_man_receiver_backup,
    verify_dead_man_receiver_backup,
)


def run(argv: list[str] | None = None, *, stdout: TextIO = sys.stdout) -> int:
    args = _parser().parse_args(argv)
    summary: BaseModel
    try:
        if args.command == "backup":
            summary = create_dead_man_receiver_backup(args.db, args.output)
        elif args.command == "verify":
            summary = verify_dead_man_receiver_backup(args.backup)
        elif args.command == "drill":
            summary = drill_dead_man_receiver_backup(
                args.backup,
                expected_sha256=args.expected_sha256,
                workspace=args.workspace,
                report_path=args.report,
            )
        else:
            if not args.yes:
                stdout.write("Refusing to restore receiver state without --yes.\n")
                return 2
            summary = restore_dead_man_receiver_backup(
                args.db,
                args.backup,
                expected_sha256=args.expected_sha256,
            )
    except DeadManReceiverRecoveryError as exc:
        stdout.write(f"Receiver recovery failed: {exc}\n")
        return 3
    stdout.write(summary.model_dump_json() + "\n")
    return 0


def main() -> None:
    raise SystemExit(run())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aico-dead-man-recovery")
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup = subparsers.add_parser("backup", help="Create a verified online receiver backup")
    backup.add_argument("--db", required=True, type=Path)
    backup.add_argument("--output", required=True, type=Path)
    verify = subparsers.add_parser("verify", help="Deep-verify a receiver backup offline")
    verify.add_argument("--backup", required=True, type=Path)
    drill = subparsers.add_parser("drill", help="Restore into a disposable workspace")
    drill.add_argument("--backup", required=True, type=Path)
    drill.add_argument("--expected-sha256", required=True)
    drill.add_argument("--workspace", type=Path)
    drill.add_argument("--report", type=Path)
    restore = subparsers.add_parser("restore", help="Restore only while receiver is stopped")
    restore.add_argument("--db", required=True, type=Path)
    restore.add_argument("--from", dest="backup", required=True, type=Path)
    restore.add_argument("--expected-sha256", required=True)
    restore.add_argument("--yes", action="store_true")
    return parser
