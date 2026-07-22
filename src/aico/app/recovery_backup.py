"""Durable state and receipts for scheduled core recovery-set backups."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol, cast

from pydantic import Field, model_validator

from aico.core.models import FrozenModel
from aico.core.sqlite_state import SQLiteStateDatabase

MAX_RECOVERY_BACKUP_ATTEMPTS = 5
_RETRY_SECONDS = (60, 300, 900, 900)


class RecoveryBackupStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    VERIFIED = "verified"
    EXHAUSTED = "exhausted"
    PRUNING = "pruning"
    PRUNED = "pruned"


class RecoveryCustodyStatus(StrEnum):
    UNKNOWN = "unknown"
    VERIFIED = "verified"
    FAILED = "failed"


class RecoveryBackupReceipt(FrozenModel):
    schema_version: Literal[2] = 2
    backup_id: str = Field(pattern=r"^recovery-[a-f0-9]{32}$")
    artifact_name: str = Field(pattern=r"^aico-core-recovery-[a-f0-9]{32}\.zip$")
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime
    capture_window_seconds: float = Field(ge=0)
    state_schema_version: int = Field(ge=1)
    state_table_count: int = Field(ge=0)
    audit_event_count: int = Field(ge=0)
    audit_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    memory_record_count: int = Field(ge=0)
    memory_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    destination_fingerprint_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    global_transaction: Literal[False] = False
    business_restore_ready: Literal[False] = False

    @model_validator(mode="after")
    def validate_receipt(self) -> RecoveryBackupReceipt:
        _require_aware(self.created_at)
        if self.global_transaction or self.business_restore_ready:
            raise ValueError("scheduled recovery receipt cannot claim business readiness")
        return self


class RecoveryBackupRecord(FrozenModel):
    backup_id: str = Field(pattern=r"^recovery-[a-f0-9]{32}$")
    binding_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    scheduled_for: datetime
    status: RecoveryBackupStatus = RecoveryBackupStatus.PENDING
    attempts: int = Field(default=0, ge=0, le=MAX_RECOVERY_BACKUP_ATTEMPTS)
    next_attempt_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    verified_at: datetime | None = None
    receipt_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    receipt: RecoveryBackupReceipt | None = None
    custody_status: RecoveryCustodyStatus = RecoveryCustodyStatus.UNKNOWN
    custody_checked_at: datetime | None = None
    custody_failures: int = Field(default=0, ge=0)
    retention_started_at: datetime | None = None
    retention_policy_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    pruned_at: datetime | None = None

    @model_validator(mode="after")
    def validate_state(self) -> RecoveryBackupRecord:
        for value in (
            self.scheduled_for,
            self.next_attempt_at,
            self.created_at,
            self.updated_at,
            self.verified_at,
            self.custody_checked_at,
            self.retention_started_at,
            self.pruned_at,
        ):
            if value is not None:
                _require_aware(value)
        evidenced = self.status in {
            RecoveryBackupStatus.VERIFIED,
            RecoveryBackupStatus.PRUNING,
            RecoveryBackupStatus.PRUNED,
        }
        evidence = (
            self.verified_at is not None
            and self.receipt_sha256 is not None
            and self.receipt is not None
        )
        if evidenced != evidence:
            raise ValueError("verified recovery backup requires receipt evidence")
        if self.receipt is not None and self.receipt.backup_id != self.backup_id:
            raise ValueError("recovery backup receipt binding mismatch")
        custody_checked = self.custody_checked_at is not None
        if (self.custody_status is RecoveryCustodyStatus.UNKNOWN) != (not custody_checked):
            raise ValueError("recovery custody status and checked time mismatch")
        if self.custody_status is RecoveryCustodyStatus.FAILED and self.custody_failures < 1:
            raise ValueError("failed recovery custody requires a failure count")
        if self.custody_status is RecoveryCustodyStatus.VERIFIED and self.custody_failures:
            raise ValueError("verified recovery custody cannot retain failures")
        if evidenced != (self.custody_status is not RecoveryCustodyStatus.UNKNOWN):
            raise ValueError("only verified backups can carry custody evidence")
        pruning = self.status is RecoveryBackupStatus.PRUNING
        pruned = self.status is RecoveryBackupStatus.PRUNED
        retention_evidence = (
            self.retention_started_at is not None and self.retention_policy_sha256 is not None
        )
        if (pruning or pruned) != retention_evidence:
            raise ValueError("recovery pruning requires durable policy evidence")
        if pruned != (self.pruned_at is not None):
            raise ValueError("pruned recovery backup requires completion time")
        return self


class RecoveryBackupStore(Protocol):
    def ensure(self, record: RecoveryBackupRecord) -> RecoveryBackupRecord: ...

    def load(self, backup_id: str) -> RecoveryBackupRecord | None: ...

    def latest(self, binding_sha256: str) -> RecoveryBackupRecord | None: ...

    def latest_verified(self, binding_sha256: str) -> RecoveryBackupRecord | None: ...

    def next_open(self, binding_sha256: str) -> RecoveryBackupRecord | None: ...

    def reconcile_interrupted(self, binding_sha256: str, *, now: datetime) -> int: ...

    def begin_attempt(self, backup_id: str, *, now: datetime) -> RecoveryBackupRecord: ...

    def defer(self, backup_id: str, *, now: datetime) -> RecoveryBackupRecord: ...

    def mark_verified(
        self,
        backup_id: str,
        *,
        receipt: RecoveryBackupReceipt,
        receipt_sha256: str,
        now: datetime,
    ) -> RecoveryBackupRecord: ...

    def mark_custody_verified(self, backup_id: str, *, now: datetime) -> RecoveryBackupRecord: ...

    def mark_custody_failed(self, backup_id: str, *, now: datetime) -> RecoveryBackupRecord: ...

    def retention_candidates(
        self,
        binding_sha256: str,
        *,
        older_than: datetime,
        keep_generations: int,
    ) -> tuple[RecoveryBackupRecord, ...]: ...

    def next_pruning(self, binding_sha256: str) -> RecoveryBackupRecord | None: ...

    def begin_prune(
        self,
        backup_id: str,
        *,
        policy_sha256: str,
        now: datetime,
    ) -> RecoveryBackupRecord: ...

    def mark_pruned(self, backup_id: str, *, now: datetime) -> RecoveryBackupRecord: ...


class SQLiteRecoveryBackupStore:
    """Persist scheduled capture intent before creating any recovery artifact."""

    def __init__(self, path: Path | str) -> None:
        self._database = SQLiteStateDatabase(path)
        self._init_schema()

    def ensure(self, record: RecoveryBackupRecord) -> RecoveryBackupRecord:
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._row(connection, record.backup_id)
            if row is not None:
                existing = _record(row)
                if _identity(existing) != _identity(record):
                    raise ValueError("scheduled recovery backup identity drift")
                return existing
            connection.execute(
                """
                INSERT INTO scheduled_recovery_backups
                (backup_id, binding_sha256, scheduled_for, status, next_attempt_at, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                _values(record),
            )
        return record

    def load(self, backup_id: str) -> RecoveryBackupRecord | None:
        with self._database.connect() as connection:
            row = self._row(connection, backup_id)
        return None if row is None else _record(row)

    def latest(self, binding_sha256: str) -> RecoveryBackupRecord | None:
        return self._select(binding_sha256, status=None)

    def latest_verified(self, binding_sha256: str) -> RecoveryBackupRecord | None:
        return self._select(binding_sha256, status=RecoveryBackupStatus.VERIFIED)

    def next_open(self, binding_sha256: str) -> RecoveryBackupRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_recovery_backups "
                "WHERE binding_sha256 = ? AND status IN (?, ?) "
                "ORDER BY scheduled_for, rowid LIMIT 1",
                (
                    binding_sha256,
                    RecoveryBackupStatus.PENDING.value,
                    RecoveryBackupStatus.RETRYING.value,
                ),
            ).fetchone()
        return None if row is None else _record(cast(tuple[object, ...], row))

    def reconcile_interrupted(self, binding_sha256: str, *, now: datetime) -> int:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_recovery_backups "
                "WHERE binding_sha256 = ? AND status = ?",
                (binding_sha256, RecoveryBackupStatus.RUNNING.value),
            ).fetchall()
            for row in rows:
                record = _record(cast(tuple[object, ...], row))
                updated = record.model_copy(
                    update={
                        "status": RecoveryBackupStatus.RETRYING,
                        "attempts": max(record.attempts - 1, 0),
                        "next_attempt_at": now,
                        "updated_at": now,
                    }
                )
                self._update(connection, updated)
        return len(rows)

    def begin_attempt(self, backup_id: str, *, now: datetime) -> RecoveryBackupRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, backup_id)
            if record.status in {
                RecoveryBackupStatus.VERIFIED,
                RecoveryBackupStatus.EXHAUSTED,
            }:
                return record
            if record.next_attempt_at is not None and record.next_attempt_at > now:
                return record
            updated = record.model_copy(
                update={
                    "status": RecoveryBackupStatus.RUNNING,
                    "attempts": record.attempts + 1,
                    "next_attempt_at": None,
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def defer(self, backup_id: str, *, now: datetime) -> RecoveryBackupRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, backup_id)
            if record.status is not RecoveryBackupStatus.RUNNING:
                return record
            exhausted = record.attempts >= MAX_RECOVERY_BACKUP_ATTEMPTS
            updated = record.model_copy(
                update={
                    "status": (
                        RecoveryBackupStatus.EXHAUSTED
                        if exhausted
                        else RecoveryBackupStatus.RETRYING
                    ),
                    "next_attempt_at": (None if exhausted else now + _retry_delay(record.attempts)),
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def mark_verified(
        self,
        backup_id: str,
        *,
        receipt: RecoveryBackupReceipt,
        receipt_sha256: str,
        now: datetime,
    ) -> RecoveryBackupRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, backup_id)
            if record.status is RecoveryBackupStatus.VERIFIED:
                if record.receipt != receipt or record.receipt_sha256 != receipt_sha256:
                    raise ValueError("scheduled recovery receipt drift")
                return record
            if record.status is not RecoveryBackupStatus.RUNNING:
                raise ValueError("scheduled recovery backup is not running")
            updated = record.model_copy(
                update={
                    "status": RecoveryBackupStatus.VERIFIED,
                    "next_attempt_at": None,
                    "updated_at": now,
                    "verified_at": now,
                    "receipt_sha256": receipt_sha256,
                    "receipt": receipt,
                    "custody_status": RecoveryCustodyStatus.VERIFIED,
                    "custody_checked_at": now,
                    "custody_failures": 0,
                }
            )
            self._update(connection, updated)
        return updated

    def mark_custody_verified(
        self,
        backup_id: str,
        *,
        now: datetime,
    ) -> RecoveryBackupRecord:
        return self._mark_custody(backup_id, status=RecoveryCustodyStatus.VERIFIED, now=now)

    def mark_custody_failed(
        self,
        backup_id: str,
        *,
        now: datetime,
    ) -> RecoveryBackupRecord:
        return self._mark_custody(backup_id, status=RecoveryCustodyStatus.FAILED, now=now)

    def _mark_custody(
        self,
        backup_id: str,
        *,
        status: RecoveryCustodyStatus,
        now: datetime,
    ) -> RecoveryBackupRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, backup_id)
            if record.status is not RecoveryBackupStatus.VERIFIED:
                raise ValueError("recovery custody requires a verified backup")
            failures = (
                0 if status is RecoveryCustodyStatus.VERIFIED else record.custody_failures + 1
            )
            updated = record.model_copy(
                update={
                    "custody_status": status,
                    "custody_checked_at": now,
                    "custody_failures": failures,
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def retention_candidates(
        self,
        binding_sha256: str,
        *,
        older_than: datetime,
        keep_generations: int,
    ) -> tuple[RecoveryBackupRecord, ...]:
        _require_aware(older_than)
        if keep_generations < 2:
            raise ValueError("recovery retention must preserve at least two generations")
        with self._database.connect() as connection:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_recovery_backups "
                "WHERE binding_sha256 = ? AND status = ? "
                "ORDER BY scheduled_for DESC, rowid DESC",
                (binding_sha256, RecoveryBackupStatus.VERIFIED.value),
            ).fetchall()
        records = tuple(_record(cast(tuple[object, ...], row)) for row in rows)
        candidates = records[keep_generations:]
        return tuple(
            record
            for record in reversed(candidates)
            if record.verified_at is not None
            and record.verified_at <= older_than
            and record.custody_status is RecoveryCustodyStatus.VERIFIED
        )

    def next_pruning(self, binding_sha256: str) -> RecoveryBackupRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_recovery_backups "
                "WHERE binding_sha256 = ? AND status = ? "
                "ORDER BY scheduled_for, rowid LIMIT 1",
                (binding_sha256, RecoveryBackupStatus.PRUNING.value),
            ).fetchone()
        return None if row is None else _record(cast(tuple[object, ...], row))

    def begin_prune(
        self,
        backup_id: str,
        *,
        policy_sha256: str,
        now: datetime,
    ) -> RecoveryBackupRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, backup_id)
            if record.status is RecoveryBackupStatus.PRUNING:
                if record.retention_policy_sha256 != policy_sha256:
                    raise ValueError("recovery retention policy drift")
                return record
            if record.status is not RecoveryBackupStatus.VERIFIED:
                return record
            if record.custody_status is not RecoveryCustodyStatus.VERIFIED:
                raise ValueError("recovery retention requires verified custody")
            updated = record.model_copy(
                update={
                    "status": RecoveryBackupStatus.PRUNING,
                    "retention_started_at": now,
                    "retention_policy_sha256": policy_sha256,
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def mark_pruned(self, backup_id: str, *, now: datetime) -> RecoveryBackupRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, backup_id)
            if record.status is RecoveryBackupStatus.PRUNED:
                return record
            if record.status is not RecoveryBackupStatus.PRUNING:
                raise ValueError("recovery backup is not pruning")
            updated = record.model_copy(
                update={
                    "status": RecoveryBackupStatus.PRUNED,
                    "pruned_at": now,
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def _select(
        self,
        binding_sha256: str,
        *,
        status: RecoveryBackupStatus | None,
    ) -> RecoveryBackupRecord | None:
        where = "binding_sha256 = ?"
        args: tuple[object, ...] = (binding_sha256,)
        if status is not None:
            where += " AND status = ?"
            args += (status.value,)
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_recovery_backups "
                f"WHERE {where} ORDER BY scheduled_for DESC, rowid DESC LIMIT 1",
                args,
            ).fetchone()
        return None if row is None else _record(cast(tuple[object, ...], row))

    def _required(
        self,
        connection: sqlite3.Connection,
        backup_id: str,
    ) -> RecoveryBackupRecord:
        row = self._row(connection, backup_id)
        if row is None:
            raise ValueError(f"unknown scheduled recovery backup: {backup_id}")
        return _record(row)

    def _row(
        self,
        connection: sqlite3.Connection,
        backup_id: str,
    ) -> tuple[object, ...] | None:
        return cast(
            tuple[object, ...] | None,
            connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_recovery_backups WHERE backup_id = ?",
                (backup_id,),
            ).fetchone(),
        )

    def _update(self, connection: sqlite3.Connection, record: RecoveryBackupRecord) -> None:
        connection.execute(
            """
            UPDATE scheduled_recovery_backups
            SET binding_sha256 = ?, scheduled_for = ?, status = ?, next_attempt_at = ?,
                payload = ? WHERE backup_id = ?
            """,
            _values(record)[1:] + (record.backup_id,),
        )

    def _init_schema(self) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_recovery_backups (
                    backup_id TEXT PRIMARY KEY,
                    binding_sha256 TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    status TEXT NOT NULL,
                    next_attempt_at TEXT,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_scheduled_recovery_binding "
                "ON scheduled_recovery_backups(binding_sha256, scheduled_for)"
            )


_COLUMNS = "backup_id, binding_sha256, scheduled_for, status, next_attempt_at, payload"


def _record(row: tuple[object, ...]) -> RecoveryBackupRecord:
    record = RecoveryBackupRecord.model_validate_json(str(row[5]))
    indexed = (
        str(row[0]),
        str(row[1]),
        str(row[2]),
        str(row[3]),
        None if row[4] is None else str(row[4]),
    )
    expected = (
        record.backup_id,
        record.binding_sha256,
        record.scheduled_for.isoformat(),
        record.status.value,
        None if record.next_attempt_at is None else record.next_attempt_at.isoformat(),
    )
    if indexed != expected:
        raise ValueError("scheduled recovery backup indexed state mismatch")
    return record


def _values(record: RecoveryBackupRecord) -> tuple[object, ...]:
    return (
        record.backup_id,
        record.binding_sha256,
        record.scheduled_for.isoformat(),
        record.status.value,
        None if record.next_attempt_at is None else record.next_attempt_at.isoformat(),
        record.model_dump_json(),
    )


def _identity(record: RecoveryBackupRecord) -> tuple[str, str, datetime]:
    return record.backup_id, record.binding_sha256, record.scheduled_for


def _retry_delay(attempts: int) -> timedelta:
    index = min(max(attempts - 1, 0), len(_RETRY_SECONDS) - 1)
    return timedelta(seconds=_RETRY_SECONDS[index])


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("scheduled recovery backup time must be timezone-aware")
