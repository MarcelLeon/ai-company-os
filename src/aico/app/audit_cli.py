"""Operator CLI for durable audit integrity, backup, drill, and restore."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from aico.app.audit_backup import (
    AuditBackupError,
    create_audit_backup,
    verify_audit_backup,
)
from aico.app.audit_restore import (
    AuditRestoreError,
    drill_audit_backup,
    restore_audit_backup,
)
from aico.core.audit_ledger import (
    AuditIntegrityError,
    AuditLedgerSummary,
    seal_legacy_audit_ledger,
    verify_audit_ledger,
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
    if args.command == "verify-backup":
        try:
            backup_summary = verify_audit_backup(
                args.backup,
                expected_sha256=args.expected_sha256,
            )
        except AuditBackupError as exc:
            stderr.write(f"Audit backup verification failed: {exc}\n")
            return 2
        stdout.write(backup_summary.model_dump_json() + "\n")
        return 0
    if args.command == "drill-backup":
        try:
            drill = drill_audit_backup(
                args.backup,
                expected_sha256=args.expected_sha256,
                workspace=args.workspace,
                report_path=args.report,
            )
        except AuditRestoreError as exc:
            stderr.write(f"Audit backup drill failed: {exc}\n")
            return 2
        stdout.write(drill.model_dump_json() + "\n")
        return 0
    audit_path = args.audit_log or _audit_path(environment)
    if audit_path is None:
        stderr.write("Audit ledger path is required via --audit-log or AICO_AUDIT_LOG_PATH.\n")
        return 2
    try:
        if args.command == "backup":
            backup = create_audit_backup(audit_path, args.output)
            stdout.write(backup.model_dump_json() + "\n")
            return 0
        if args.command == "restore":
            state_db = args.state_db or _state_path(environment)
            if state_db is None:
                stderr.write(
                    "State database path is required via --state-db or AICO_STATE_DB_PATH.\n"
                )
                return 2
            restored = restore_audit_backup(
                audit_path,
                args.backup,
                expected_sha256=args.expected_sha256,
                state_db_path=state_db,
                preservation_path=args.preservation_output,
                base_dir=Path.cwd(),
                confirmed=args.yes,
            )
            stdout.write(restored.model_dump_json() + "\n")
            return 0
        summary = (
            seal_legacy_audit_ledger(audit_path)
            if args.command == "seal"
            else verify_audit_ledger(audit_path)
        )
    except (AuditBackupError, AuditIntegrityError, AuditRestoreError, ValueError) as exc:
        stderr.write(f"Audit ledger {args.command} failed: {exc}\n")
        return 2
    except OSError:
        stderr.write(f"Audit ledger {args.command} failed: local file operation failed\n")
        return 2
    stdout.write(_summary_json(args.command, summary) + "\n")
    return 0


def main() -> None:
    raise SystemExit(run())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seal, verify, drill, back up, or restore an AICO audit JSONL ledger."
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        help="Audit JSONL path. Defaults to AICO_AUDIT_LOG_PATH.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify", help="Verify the live ledger and checkpoint")
    commands.add_parser("seal", help="Explicitly anchor an owner-reviewed legacy ledger")
    backup = commands.add_parser("backup", help="Create a verified single-file recovery point")
    backup.add_argument("--output", required=True, type=Path, help="New .zip artifact path")
    verify_backup = commands.add_parser(
        "verify-backup",
        help="Materialize and verify a recovery point offline",
    )
    verify_backup.add_argument("--backup", required=True, type=Path, help="Backup artifact path")
    verify_backup.add_argument("--expected-sha256", help="Require a previously recorded SHA-256")
    drill = commands.add_parser(
        "drill-backup",
        help="Materialize a recovery point in a disposable workspace",
    )
    drill.add_argument("--backup", required=True, type=Path, help="Backup artifact path")
    drill.add_argument("--expected-sha256", required=True, help="Recorded artifact SHA-256")
    drill.add_argument("--workspace", type=Path, help="Existing disposable workspace parent")
    drill.add_argument("--report", type=Path, help="New owner-only drill report path")
    restore = commands.add_parser(
        "restore",
        help="Stop-the-world restore with mandatory pre-restore preservation",
    )
    restore.add_argument("--backup", required=True, type=Path, help="Backup artifact path")
    restore.add_argument("--expected-sha256", required=True, help="Recorded artifact SHA-256")
    restore.add_argument("--state-db", type=Path, help="Runtime state DB used for owner fencing")
    restore.add_argument(
        "--preservation-output",
        required=True,
        type=Path,
        help="New safety backup or corrupt-live quarantine artifact",
    )
    restore.add_argument(
        "--yes",
        action="store_true",
        help="Confirm replacement of the live audit ledger/checkpoint pair",
    )
    return parser


def _audit_path(environ: dict[str, str]) -> Path | None:
    value = environ.get("AICO_AUDIT_LOG_PATH", "").strip()
    return Path(value).expanduser() if value else None


def _state_path(environ: dict[str, str]) -> Path | None:
    value = environ.get("AICO_STATE_DB_PATH", "").strip()
    return Path(value).expanduser() if value else None


def _summary_json(operation: str, summary: AuditLedgerSummary) -> str:
    return json.dumps(
        {
            "byte_size": summary.byte_size,
            "checkpoint_lag": summary.checkpoint_lag,
            "event_count": summary.event_count,
            "operation": operation,
            "sealed": summary.sealed,
            "status": "ok",
        },
        sort_keys=True,
    )
