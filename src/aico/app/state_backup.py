"""Consistent backup and owner-fenced restore for the AICO state database."""

from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aico.app.runtime_owner import (
    RuntimeOwnerLock,
    RuntimeOwnershipError,
    runtime_owner_lock_path,
)
from aico.core.sqlite_state import STATE_SCHEMA_VERSION, STATE_TABLES


class StateBackupError(RuntimeError):
    pass


class StateBackupSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["backup", "verify"]
    artifact_name: str
    schema_version: int = Field(ge=1)
    integrity: Literal["ok"] = "ok"
    table_counts: dict[str, int]
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class StateRestoreSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["restore"] = "restore"
    schema_version: int = Field(ge=1)
    table_counts: dict[str, int]
    restored_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    safety_backup_name: str | None = None


class StateDrillSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["drill"] = "drill"
    artifact_name: str
    schema_version: int = Field(ge=1)
    table_counts: dict[str, int]
    backup_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    materialized_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    materialized_bytes: int = Field(ge=0)
    completed_at: datetime
    report_name: str | None = None


def create_state_backup(source_path: Path, output_path: Path) -> StateBackupSummary:
    source = source_path.expanduser().resolve()
    output = output_path.expanduser().resolve()
    if source == output:
        raise StateBackupError("backup source and output must differ")
    if not source.is_file():
        raise StateBackupError("backup source database is missing")
    if output.exists():
        raise StateBackupError("backup output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_database_path(output)
    published = False
    try:
        _sqlite_backup(source, temporary)
        summary = _inspect_backup(temporary, operation="backup", artifact_name=output.name)
        _sync_file(temporary)
        _publish_new_file(temporary, output)
        published = True
        _sync_directory(output.parent)
        return summary
    except StateBackupError:
        if published:
            _discard_published_file(temporary, output)
        raise
    except Exception:
        if published:
            _discard_published_file(temporary, output)
        raise StateBackupError("state backup failed") from None
    finally:
        temporary.unlink(missing_ok=True)


def verify_state_backup(backup_path: Path) -> StateBackupSummary:
    backup = backup_path.expanduser().resolve()
    if not backup.is_file():
        raise StateBackupError("backup artifact is missing")
    return _inspect_backup(backup, operation="verify", artifact_name=backup.name)


def drill_state_backup(
    backup_path: Path,
    *,
    expected_sha256: str,
    workspace: Path | None = None,
    report_path: Path | None = None,
    clock: Callable[[], datetime] | None = None,
) -> StateDrillSummary:
    backup = backup_path.expanduser().resolve()
    verified = verify_state_backup(backup)
    if not hmac.compare_digest(verified.sha256, expected_sha256.lower()):
        raise StateBackupError("backup SHA-256 does not match expected value")
    drill_workspace = _validated_drill_workspace(workspace)
    report = _validated_drill_report(report_path, backup=backup)
    drill_clock = clock or (lambda: datetime.now(UTC))
    try:
        with tempfile.TemporaryDirectory(
            prefix="aico-state-drill-",
            dir=drill_workspace,
        ) as raw_directory:
            disposable_directory = Path(raw_directory)
            target = disposable_directory / "state.db"
            restore_state_backup(
                target,
                backup,
                expected_sha256=verified.sha256,
                base_dir=disposable_directory,
            )
            materialized = verify_state_backup(target)
            _require_drill_parity(verified, materialized)
            completed_at = drill_clock()
            if completed_at.tzinfo is None:
                raise StateBackupError("drill clock must be timezone-aware")
            summary = StateDrillSummary(
                artifact_name=backup.name,
                schema_version=materialized.schema_version,
                table_counts=materialized.table_counts,
                backup_sha256=verified.sha256,
                materialized_sha256=materialized.sha256,
                materialized_bytes=materialized.bytes,
                completed_at=completed_at,
                report_name=report.name if report is not None else None,
            )
    except StateBackupError:
        raise
    except Exception:
        raise StateBackupError("disposable restore drill failed") from None
    if report is not None:
        _write_new_report(report, summary.model_dump_json() + "\n")
    return summary


def restore_state_backup(
    target_path: Path,
    backup_path: Path,
    *,
    expected_sha256: str,
    base_dir: Path,
    clock: Callable[[], datetime] | None = None,
) -> StateRestoreSummary:
    target = target_path.expanduser().resolve()
    backup = backup_path.expanduser().resolve()
    if target == backup:
        raise StateBackupError("restore target and backup must differ")
    verified = verify_state_backup(backup)
    if not hmac.compare_digest(verified.sha256, expected_sha256.lower()):
        raise StateBackupError("backup SHA-256 does not match expected value")
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = RuntimeOwnerLock(
        runtime_owner_lock_path(target, base_dir=base_dir),
        resource_path=target,
    )
    try:
        lock.acquire()
    except RuntimeOwnershipError:
        raise StateBackupError("runtime owner is active; restore refused") from None
    temporary = _temporary_database_path(target)
    safety: Path | None = None
    try:
        if target.exists():
            safety = _safety_backup_path(target, clock=clock)
            create_state_backup(target, safety)
        _sqlite_backup(backup, temporary)
        restored = _inspect_backup(
            temporary,
            operation="verify",
            artifact_name=target.name,
        )
        _sync_file(temporary)
        os.replace(temporary, target)
        Path(f"{target}-wal").unlink(missing_ok=True)
        Path(f"{target}-shm").unlink(missing_ok=True)
        _sync_directory(target.parent)
        return StateRestoreSummary(
            schema_version=restored.schema_version,
            table_counts=restored.table_counts,
            restored_sha256=verified.sha256,
            safety_backup_name=safety.name if safety is not None else None,
        )
    except StateBackupError:
        raise
    except Exception:
        raise StateBackupError("state restore failed") from None
    finally:
        temporary.unlink(missing_ok=True)
        lock.release()


def _inspect_backup(
    path: Path,
    *,
    operation: Literal["backup", "verify"],
    artifact_name: str,
) -> StateBackupSummary:
    try:
        with sqlite3.connect(_read_only_uri(path), uri=True) as connection:
            integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
            if integrity_rows != [("ok",)]:
                raise StateBackupError("backup integrity check failed")
            schema_row = connection.execute(
                "SELECT value FROM aico_schema WHERE key = 'schema_version'"
            ).fetchone()
            if schema_row is None or int(schema_row[0]) != STATE_SCHEMA_VERSION:
                raise StateBackupError("backup schema version is not supported")
            existing = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            counts = {
                table: _table_count(connection, table)
                for table in STATE_TABLES
                if table in existing
            }
    except StateBackupError:
        raise
    except (OSError, sqlite3.Error, TypeError, ValueError):
        raise StateBackupError("backup integrity or schema verification failed") from None
    return StateBackupSummary(
        operation=operation,
        artifact_name=artifact_name,
        schema_version=STATE_SCHEMA_VERSION,
        table_counts=counts,
        bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _sqlite_backup(source: Path, destination: Path) -> None:
    try:
        source_uri = _read_only_uri(source, immutable=False)
        with sqlite3.connect(source_uri, uri=True) as source_connection:
            with sqlite3.connect(destination) as destination_connection:
                source_connection.backup(destination_connection)
    except sqlite3.Error:
        raise StateBackupError("SQLite online backup failed") from None
    destination.chmod(0o600)


def _temporary_database_path(target: Path) -> Path:
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    os.close(descriptor)
    return Path(raw_path)


def _safety_backup_path(
    target: Path,
    *,
    clock: Callable[[], datetime] | None,
) -> Path:
    now = (clock or (lambda: datetime.now(UTC)))()
    if now.tzinfo is None:
        raise StateBackupError("restore clock must be timezone-aware")
    stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return target.with_name(f"{target.name}.pre-restore-{stamp}.db")


def _read_only_uri(path: Path, *, immutable: bool = True) -> str:
    suffix = "?mode=ro&immutable=1" if immutable else "?mode=ro"
    return f"{path.as_uri()}{suffix}"


def _table_count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(row[0]) if row is not None else 0


def _sync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_new_file(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
    except FileExistsError:
        raise StateBackupError("backup output already exists") from None


def _discard_published_file(source: Path, destination: Path) -> None:
    try:
        if destination.exists() and os.path.samefile(source, destination):
            destination.unlink()
            _sync_directory(destination.parent)
    except OSError:
        pass


def _validated_drill_workspace(workspace: Path | None) -> Path | None:
    if workspace is None:
        return None
    resolved = workspace.expanduser().resolve()
    if not resolved.is_dir():
        raise StateBackupError("drill workspace is missing or not a directory")
    return resolved


def _validated_drill_report(report_path: Path | None, *, backup: Path) -> Path | None:
    if report_path is None:
        return None
    report = report_path.expanduser().resolve()
    if report == backup:
        raise StateBackupError("drill report and backup must differ")
    if report.exists():
        raise StateBackupError("drill report already exists")
    return report


def _require_drill_parity(
    backup: StateBackupSummary,
    materialized: StateBackupSummary,
) -> None:
    if backup.schema_version != materialized.schema_version:
        raise StateBackupError("drill materialized schema does not match backup")
    if backup.table_counts != materialized.table_counts:
        raise StateBackupError("drill materialized table counts do not match backup")


def _write_new_report(report: Path, payload: str) -> None:
    report.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_database_path(report)
    published = False
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.chmod(0o600)
        _sync_file(temporary)
        try:
            os.link(temporary, report)
        except FileExistsError:
            raise StateBackupError("drill report already exists") from None
        published = True
        _sync_directory(report.parent)
    except StateBackupError:
        if published:
            _discard_published_file(temporary, report)
        raise
    except Exception:
        if published:
            _discard_published_file(temporary, report)
        raise StateBackupError("drill report publication failed") from None
    finally:
        temporary.unlink(missing_ok=True)
