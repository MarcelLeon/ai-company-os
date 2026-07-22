"""Durable intent and secret-free receipts for scheduled recovery drills."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol, cast

from pydantic import Field, model_validator

from aico.core.models import FrozenModel
from aico.core.sqlite_state import SQLiteStateDatabase

MAX_RECOVERY_DRILL_ATTEMPTS = 5
_RETRY_SECONDS = (60, 300, 900, 900)


class RecoveryDrillStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    VERIFIED = "verified"
    EXHAUSTED = "exhausted"


class RecoveryDrillReceipt(FrozenModel):
    schema_version: Literal[1] = 1
    drill_id: str = Field(pattern=r"^drill-[a-f0-9]{32}$")
    backup_id: str = Field(pattern=r"^recovery-[a-f0-9]{32}$")
    policy_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    backup_receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    state_schema_version: int = Field(ge=1)
    state_table_count: int = Field(ge=0)
    audit_event_count: int = Field(ge=0)
    audit_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    memory_record_count: int = Field(ge=0)
    memory_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    unresolved_asset_count: int = Field(ge=0)
    post_restore_evidence_asset_count: int = Field(ge=0)
    completed_at: datetime
    global_transaction: Literal[False] = False
    business_restore_ready: Literal[False] = False

    @model_validator(mode="after")
    def validate_receipt(self) -> RecoveryDrillReceipt:
        _require_aware(self.completed_at)
        if self.global_transaction or self.business_restore_ready:
            raise ValueError("scheduled recovery drill cannot claim business readiness")
        return self


class RecoveryDrillRecord(FrozenModel):
    drill_id: str = Field(pattern=r"^drill-[a-f0-9]{32}$")
    binding_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    backup_id: str = Field(pattern=r"^recovery-[a-f0-9]{32}$")
    policy_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    scheduled_for: datetime
    status: RecoveryDrillStatus = RecoveryDrillStatus.PENDING
    attempts: int = Field(default=0, ge=0, le=MAX_RECOVERY_DRILL_ATTEMPTS)
    next_attempt_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    verified_at: datetime | None = None
    receipt_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    receipt: RecoveryDrillReceipt | None = None

    @model_validator(mode="after")
    def validate_state(self) -> RecoveryDrillRecord:
        for value in (
            self.scheduled_for,
            self.next_attempt_at,
            self.created_at,
            self.updated_at,
            self.verified_at,
        ):
            if value is not None:
                _require_aware(value)
        verified = self.status is RecoveryDrillStatus.VERIFIED
        evidence = (
            self.verified_at is not None
            and self.receipt_sha256 is not None
            and self.receipt is not None
        )
        if verified != evidence:
            raise ValueError("verified recovery drill requires receipt evidence")
        if self.receipt is not None and (
            self.receipt.drill_id != self.drill_id
            or self.receipt.backup_id != self.backup_id
            or self.receipt.policy_sha256 != self.policy_sha256
        ):
            raise ValueError("scheduled recovery drill receipt binding mismatch")
        return self


class RecoveryDrillStore(Protocol):
    def ensure(self, record: RecoveryDrillRecord) -> RecoveryDrillRecord: ...

    def load(self, drill_id: str) -> RecoveryDrillRecord | None: ...

    def latest(self, binding_sha256: str) -> RecoveryDrillRecord | None: ...

    def latest_verified(self, binding_sha256: str) -> RecoveryDrillRecord | None: ...

    def next_open(self, binding_sha256: str) -> RecoveryDrillRecord | None: ...

    def protected_backup_ids(self, binding_sha256: str) -> frozenset[str]: ...

    def reconcile_interrupted(self, binding_sha256: str, *, now: datetime) -> int: ...

    def begin_attempt(self, drill_id: str, *, now: datetime) -> RecoveryDrillRecord: ...

    def defer(self, drill_id: str, *, now: datetime) -> RecoveryDrillRecord: ...

    def mark_verified(
        self,
        drill_id: str,
        *,
        receipt: RecoveryDrillReceipt,
        receipt_sha256: str,
        now: datetime,
    ) -> RecoveryDrillRecord: ...


class SQLiteRecoveryDrillStore:
    """Persist scheduled drill intent before disposable materialization starts."""

    def __init__(self, path: Path | str) -> None:
        self._database = SQLiteStateDatabase(path)
        self._init_schema()

    def ensure(self, record: RecoveryDrillRecord) -> RecoveryDrillRecord:
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._row(connection, record.drill_id)
            if row is not None:
                existing = _record(row)
                if _identity(existing) != _identity(record):
                    raise ValueError("scheduled recovery drill identity drift")
                return existing
            connection.execute(
                """
                INSERT INTO scheduled_recovery_drills
                (drill_id, binding_sha256, backup_id, scheduled_for, status,
                 next_attempt_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                _values(record),
            )
        return record

    def load(self, drill_id: str) -> RecoveryDrillRecord | None:
        with self._database.connect() as connection:
            row = self._row(connection, drill_id)
        return None if row is None else _record(row)

    def latest(self, binding_sha256: str) -> RecoveryDrillRecord | None:
        return self._select(binding_sha256, status=None, ascending=False)

    def latest_verified(self, binding_sha256: str) -> RecoveryDrillRecord | None:
        return self._select(
            binding_sha256,
            status=RecoveryDrillStatus.VERIFIED,
            ascending=False,
        )

    def next_open(self, binding_sha256: str) -> RecoveryDrillRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_recovery_drills "
                "WHERE binding_sha256 = ? AND status IN (?, ?) "
                "ORDER BY scheduled_for, rowid LIMIT 1",
                (
                    binding_sha256,
                    RecoveryDrillStatus.PENDING.value,
                    RecoveryDrillStatus.RETRYING.value,
                ),
            ).fetchone()
        return None if row is None else _record(cast(tuple[object, ...], row))

    def protected_backup_ids(self, binding_sha256: str) -> frozenset[str]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT backup_id FROM scheduled_recovery_drills "
                "WHERE binding_sha256 = ? AND status IN (?, ?, ?)",
                (
                    binding_sha256,
                    RecoveryDrillStatus.PENDING.value,
                    RecoveryDrillStatus.RUNNING.value,
                    RecoveryDrillStatus.RETRYING.value,
                ),
            ).fetchall()
        protected = {str(row[0]) for row in rows}
        latest = self.latest(binding_sha256)
        if latest is not None and latest.status is RecoveryDrillStatus.EXHAUSTED:
            protected.add(latest.backup_id)
        return frozenset(protected)

    def reconcile_interrupted(self, binding_sha256: str, *, now: datetime) -> int:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_recovery_drills "
                "WHERE binding_sha256 = ? AND status = ?",
                (binding_sha256, RecoveryDrillStatus.RUNNING.value),
            ).fetchall()
            for row in rows:
                record = _record(cast(tuple[object, ...], row))
                updated = record.model_copy(
                    update={
                        "status": RecoveryDrillStatus.RETRYING,
                        "attempts": max(record.attempts - 1, 0),
                        "next_attempt_at": now,
                        "updated_at": now,
                    }
                )
                self._update(connection, updated)
        return len(rows)

    def begin_attempt(self, drill_id: str, *, now: datetime) -> RecoveryDrillRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, drill_id)
            if record.status in {RecoveryDrillStatus.VERIFIED, RecoveryDrillStatus.EXHAUSTED}:
                return record
            if record.next_attempt_at is not None and record.next_attempt_at > now:
                return record
            updated = record.model_copy(
                update={
                    "status": RecoveryDrillStatus.RUNNING,
                    "attempts": record.attempts + 1,
                    "next_attempt_at": None,
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def defer(self, drill_id: str, *, now: datetime) -> RecoveryDrillRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, drill_id)
            if record.status is not RecoveryDrillStatus.RUNNING:
                return record
            exhausted = record.attempts >= MAX_RECOVERY_DRILL_ATTEMPTS
            updated = record.model_copy(
                update={
                    "status": (
                        RecoveryDrillStatus.EXHAUSTED if exhausted else RecoveryDrillStatus.RETRYING
                    ),
                    "next_attempt_at": (None if exhausted else now + _retry_delay(record.attempts)),
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def mark_verified(
        self,
        drill_id: str,
        *,
        receipt: RecoveryDrillReceipt,
        receipt_sha256: str,
        now: datetime,
    ) -> RecoveryDrillRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, drill_id)
            if record.status is RecoveryDrillStatus.VERIFIED:
                if record.receipt != receipt or record.receipt_sha256 != receipt_sha256:
                    raise ValueError("scheduled recovery drill receipt drift")
                return record
            if record.status is not RecoveryDrillStatus.RUNNING:
                raise ValueError("scheduled recovery drill is not running")
            updated = record.model_copy(
                update={
                    "status": RecoveryDrillStatus.VERIFIED,
                    "next_attempt_at": None,
                    "updated_at": now,
                    "verified_at": now,
                    "receipt": receipt,
                    "receipt_sha256": receipt_sha256,
                }
            )
            self._update(connection, updated)
        return updated

    def _select(
        self,
        binding_sha256: str,
        *,
        status: RecoveryDrillStatus | None,
        ascending: bool,
    ) -> RecoveryDrillRecord | None:
        where = "binding_sha256 = ?"
        args: tuple[object, ...] = (binding_sha256,)
        if status is not None:
            where += " AND status = ?"
            args += (status.value,)
        order = "scheduled_for, rowid" if ascending else "scheduled_for DESC, rowid DESC"
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_recovery_drills "
                f"WHERE {where} ORDER BY {order} LIMIT 1",
                args,
            ).fetchone()
        return None if row is None else _record(cast(tuple[object, ...], row))

    def _required(
        self,
        connection: sqlite3.Connection,
        drill_id: str,
    ) -> RecoveryDrillRecord:
        row = self._row(connection, drill_id)
        if row is None:
            raise ValueError(f"unknown scheduled recovery drill: {drill_id}")
        return _record(row)

    def _row(
        self,
        connection: sqlite3.Connection,
        drill_id: str,
    ) -> tuple[object, ...] | None:
        return cast(
            tuple[object, ...] | None,
            connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_recovery_drills WHERE drill_id = ?",
                (drill_id,),
            ).fetchone(),
        )

    def _update(self, connection: sqlite3.Connection, record: RecoveryDrillRecord) -> None:
        connection.execute(
            """
            UPDATE scheduled_recovery_drills
            SET binding_sha256 = ?, backup_id = ?, scheduled_for = ?, status = ?,
                next_attempt_at = ?, payload = ? WHERE drill_id = ?
            """,
            _values(record)[1:] + (record.drill_id,),
        )

    def _init_schema(self) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_recovery_drills (
                    drill_id TEXT PRIMARY KEY,
                    binding_sha256 TEXT NOT NULL,
                    backup_id TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    status TEXT NOT NULL,
                    next_attempt_at TEXT,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_scheduled_recovery_drill_binding "
                "ON scheduled_recovery_drills(binding_sha256, scheduled_for)"
            )


_COLUMNS = "drill_id, binding_sha256, backup_id, scheduled_for, status, next_attempt_at, payload"


def _record(row: tuple[object, ...]) -> RecoveryDrillRecord:
    record = RecoveryDrillRecord.model_validate_json(str(row[6]))
    indexed = (
        str(row[0]),
        str(row[1]),
        str(row[2]),
        str(row[3]),
        str(row[4]),
        None if row[5] is None else str(row[5]),
    )
    expected = (
        record.drill_id,
        record.binding_sha256,
        record.backup_id,
        record.scheduled_for.isoformat(),
        record.status.value,
        None if record.next_attempt_at is None else record.next_attempt_at.isoformat(),
    )
    if indexed != expected:
        raise ValueError("scheduled recovery drill indexed state mismatch")
    return record


def _values(record: RecoveryDrillRecord) -> tuple[object, ...]:
    return (
        record.drill_id,
        record.binding_sha256,
        record.backup_id,
        record.scheduled_for.isoformat(),
        record.status.value,
        None if record.next_attempt_at is None else record.next_attempt_at.isoformat(),
        record.model_dump_json(),
    )


def _identity(record: RecoveryDrillRecord) -> tuple[str, str, str, str, datetime]:
    return (
        record.drill_id,
        record.binding_sha256,
        record.backup_id,
        record.policy_sha256,
        record.scheduled_for,
    )


def _retry_delay(attempts: int) -> timedelta:
    index = min(max(attempts - 1, 0), len(_RETRY_SECONDS) - 1)
    return timedelta(seconds=_RETRY_SECONDS[index])


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("scheduled recovery drill time must be timezone-aware")
