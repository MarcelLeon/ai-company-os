"""Inspect, back up, verify, restore, and reset the local AICO state database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from aico.app.runtime_owner import (
    RuntimeOwnerLock,
    RuntimeOwnershipError,
    runtime_owner_lock_path,
)
from aico.app.state_backup import (
    StateBackupError,
    create_state_backup,
    drill_state_backup,
    restore_state_backup,
    verify_state_backup,
)
from aico.core.sqlite_state import SQLiteStateDatabase


def run_state_cli(argv: list[str] | None = None, *, stdout: TextIO = sys.stdout) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "backup":
        return _run_backup(args.db, args.output, stdout=stdout)
    if args.command == "verify":
        return _run_verify(args.backup, stdout=stdout)
    if args.command == "drill":
        return _run_drill(
            args.backup,
            expected_sha256=args.expected_sha256,
            workspace=args.workspace,
            report=args.report,
            stdout=stdout,
        )
    if args.command == "restore":
        if not args.yes:
            stdout.write("Refusing to restore without --yes.\n")
            return 2
        return _run_restore(
            args.db,
            args.backup,
            expected_sha256=args.expected_sha256,
            stdout=stdout,
        )
    if args.command == "reset":
        if not args.yes:
            stdout.write("Refusing to reset without --yes.\n")
            return 2
        return _run_reset(args.db, stdout=stdout)

    database = SQLiteStateDatabase(args.db)
    stdout.write(_summary_text(database))
    return 0


def main() -> None:
    raise SystemExit(run_state_cli())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aico-state")
    parser.add_argument("--db", required=True, type=Path, help="Path to AICO SQLite state DB")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("summary", help="Print schema version and state table counts")
    backup = subparsers.add_parser("backup", help="Create a verified online SQLite backup")
    backup.add_argument("--output", required=True, type=Path, help="New backup artifact path")
    verify = subparsers.add_parser("verify", help="Verify a backup without mutating it")
    verify.add_argument("--backup", required=True, type=Path, help="Backup artifact path")
    drill = subparsers.add_parser("drill", help="Rehearse restore in a disposable directory")
    drill.add_argument("--backup", required=True, type=Path, help="Backup artifact path")
    drill.add_argument("--expected-sha256", required=True)
    drill.add_argument("--workspace", type=Path, help="Existing directory for disposable files")
    drill.add_argument("--report", type=Path, help="New JSON evidence report path")
    restore = subparsers.add_parser("restore", help="Restore a verified backup while offline")
    restore.add_argument("--from", dest="backup", required=True, type=Path)
    restore.add_argument("--expected-sha256", required=True)
    restore.add_argument("--yes", action="store_true", help="Confirm destructive restore")
    reset = subparsers.add_parser("reset", help="Delete known AICO state rows")
    reset.add_argument("--yes", action="store_true", help="Confirm state table reset")
    parser.set_defaults(command="summary")
    return parser


def _run_backup(source: Path, output: Path, *, stdout: TextIO) -> int:
    try:
        summary = create_state_backup(source, output)
    except StateBackupError as exc:
        stdout.write(f"Backup refused: {exc}\n")
        return 3
    stdout.write(summary.model_dump_json() + "\n")
    return 0


def _run_verify(backup: Path, *, stdout: TextIO) -> int:
    try:
        summary = verify_state_backup(backup)
    except StateBackupError as exc:
        stdout.write(f"Verification failed: {exc}\n")
        return 3
    stdout.write(summary.model_dump_json() + "\n")
    return 0


def _run_drill(
    backup: Path,
    *,
    expected_sha256: str,
    workspace: Path | None,
    report: Path | None,
    stdout: TextIO,
) -> int:
    try:
        summary = drill_state_backup(
            backup,
            expected_sha256=expected_sha256,
            workspace=workspace,
            report_path=report,
        )
    except StateBackupError as exc:
        stdout.write(f"Drill failed: {exc}\n")
        return 3
    stdout.write(summary.model_dump_json() + "\n")
    return 0


def _run_restore(
    target: Path,
    backup: Path,
    *,
    expected_sha256: str,
    stdout: TextIO,
) -> int:
    try:
        summary = restore_state_backup(
            target,
            backup,
            expected_sha256=expected_sha256,
            base_dir=target.parent,
        )
    except StateBackupError as exc:
        stdout.write(f"Restore refused: {exc}\n")
        return 3
    stdout.write(summary.model_dump_json() + "\n")
    return 0


def _run_reset(path: Path, *, stdout: TextIO) -> int:
    canonical = path.expanduser().resolve()
    lock = RuntimeOwnerLock(
        runtime_owner_lock_path(canonical, base_dir=canonical.parent),
        resource_path=canonical,
    )
    try:
        lock.acquire()
    except RuntimeOwnershipError:
        stdout.write("Reset refused: runtime owner is active.\n")
        return 3
    try:
        database = SQLiteStateDatabase(canonical)
        database.reset_state_tables()
    finally:
        lock.release()
    stdout.write(f"Reset AICO state tables in {database.path}\n")
    return 0


def _summary_text(database: SQLiteStateDatabase) -> str:
    lines = [
        f"AICO state DB: {database.path}",
        f"schema_version: {database.schema_version()}",
        f"pending_recovery_audits: {database.pending_recovery_audit_count()}",
        f"pending_runtime_alerts: {database.pending_runtime_alert_count()}",
        f"runtime_health_alert_candidates: {database.runtime_health_alert_candidate_count()}",
        "tables:",
    ]
    counts = database.table_counts()
    if not counts:
        lines.append("- none")
    else:
        lines.extend(f"- {table}: {count}" for table, count in sorted(counts.items()))
    lines.append("recent_morning_deliveries:")
    deliveries = database.recent_morning_deliveries()
    if not deliveries:
        lines.append("- none")
    else:
        lines.extend(
            f"- {item.delivery_id} status={item.status} attempts={item.attempts} "
            f"duplicate_possible={str(item.duplicate_possible).lower()} "
            f"content_sha256={item.content_sha256} receipts={item.autonomy_receipts} "
            f"scheduled_for={item.scheduled_for} delivered_at={item.delivered_at or 'none'}"
            for item in deliveries
        )
    lines.append("recent_scheduled_autonomy:")
    autonomy = database.recent_scheduled_autonomy()
    if not autonomy:
        lines.append("- none")
    else:
        lines.extend(
            f"- {item.intent_id} status={item.status} attempts={item.attempts} "
            f"duplicate_notification_possible="
            f"{str(item.duplicate_notification_possible).lower()} "
            f"disposition={item.disposition or 'none'} "
            f"proposal_id_sha256={item.proposal_id_sha256 or 'none'} "
            f"task_id_sha256={item.task_id_sha256 or 'none'}"
            for item in autonomy
        )
    lines.append("recent_autonomy_outcome_deliveries:")
    outcomes = database.recent_autonomy_outcome_deliveries()
    if not outcomes:
        lines.append("- none")
    else:
        lines.extend(
            f"- {item.notification_id} intent={item.intent_id} status={item.status} "
            f"attempts={item.attempts} "
            f"duplicate_possible={str(item.duplicate_possible).lower()} "
            f"content_sha256={item.content_sha256} "
            f"source_status={item.source_status} outcome={item.outcome_status} "
            f"delivered_at={item.delivered_at or 'none'}"
            for item in outcomes
        )
    lines.append("recent_recovery_backups:")
    backups = database.recent_recovery_backups()
    if not backups:
        lines.append("- none")
    else:
        lines.extend(
            f"- {item.backup_id} status={item.status} attempts={item.attempts} "
            f"artifact_sha256={item.artifact_sha256 or 'none'} "
            f"receipt_sha256={item.receipt_sha256 or 'none'} "
            f"verified_at={item.verified_at or 'none'} "
            f"custody={item.custody_status} "
            f"custody_checked_at={item.custody_checked_at or 'none'} "
            f"custody_failures={item.custody_failures} "
            f"retention_started_at={item.retention_started_at or 'none'} "
            f"retention_policy_sha256={item.retention_policy_sha256 or 'none'} "
            f"pruned_at={item.pruned_at or 'none'}"
            for item in backups
        )
    lines.append("recent_recovery_drills:")
    drills = database.recent_recovery_drills()
    if not drills:
        lines.append("- none")
    else:
        lines.extend(
            f"- {item.drill_id} status={item.status} attempts={item.attempts} "
            f"backup_id={item.backup_id} policy_sha256={item.policy_sha256} "
            f"artifact_sha256={item.artifact_sha256 or 'none'} "
            f"receipt_sha256={item.receipt_sha256 or 'none'} "
            f"verified_at={item.verified_at or 'none'} "
            f"state_tables={_value_or_none(item.state_table_count)} "
            f"unresolved_assets={_value_or_none(item.unresolved_asset_count)} "
            f"post_restore_evidence_assets="
            f"{_value_or_none(item.post_restore_evidence_asset_count)}"
            for item in drills
        )
    return "\n".join(lines) + "\n"


def _value_or_none(value: object | None) -> object:
    return "none" if value is None else value
