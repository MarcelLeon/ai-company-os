"""Durable delivery state for terminal scheduled-autonomy outcomes."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Protocol, cast

from pydantic import Field, model_validator

from aico.core.models import FrozenModel, SentMessage
from aico.core.sqlite_state import SQLiteStateDatabase
from aico.core.standing_autonomy import StandingAutonomyOutcomeEnvelope

MAX_AUTONOMY_OUTCOME_DELIVERY_ATTEMPTS = 5
_RETRY_SECONDS = (60, 300, 900, 900)


class AutonomyOutcomeDeliveryStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    RETRYING = "retrying"
    DELIVERED = "delivered"
    EXHAUSTED = "exhausted"


class AutonomyOutcomeDeliveryRecord(FrozenModel):
    notification_id: str = Field(pattern=r"^autonomy-outcome-[a-f0-9]{32}$")
    intent_id: str = Field(pattern=r"^autonomy-[a-f0-9]{32}$")
    binding_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    envelope: StandingAutonomyOutcomeEnvelope
    status: AutonomyOutcomeDeliveryStatus = AutonomyOutcomeDeliveryStatus.PENDING
    attempts: int = Field(default=0, ge=0, le=MAX_AUTONOMY_OUTCOME_DELIVERY_ATTEMPTS)
    next_attempt_at: datetime | None = None
    duplicate_possible: bool = False
    created_at: datetime
    updated_at: datetime
    delivered_at: datetime | None = None
    message_id_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_state(self) -> AutonomyOutcomeDeliveryRecord:
        timestamps = (
            self.next_attempt_at,
            self.created_at,
            self.updated_at,
            self.delivered_at,
        )
        if any(
            value is not None and (value.tzinfo is None or value.utcoffset() is None)
            for value in timestamps
        ):
            raise ValueError("autonomy outcome delivery timestamps must be timezone-aware")
        if self.envelope.intent_id != self.intent_id:
            raise ValueError("autonomy outcome delivery intent mismatch")
        delivered = self.status is AutonomyOutcomeDeliveryStatus.DELIVERED
        if delivered != (self.delivered_at is not None and self.message_id_sha256 is not None):
            raise ValueError("delivered autonomy outcome requires acknowledgement evidence")
        return self


class AutonomyOutcomeDeliveryStore(Protocol):
    def ensure(self, record: AutonomyOutcomeDeliveryRecord) -> AutonomyOutcomeDeliveryRecord: ...

    def load(self, notification_id: str) -> AutonomyOutcomeDeliveryRecord | None: ...

    def for_intent(self, intent_id: str) -> AutonomyOutcomeDeliveryRecord | None: ...

    def latest(self, binding_sha256: str) -> AutonomyOutcomeDeliveryRecord | None: ...

    def next_open(self, binding_sha256: str) -> AutonomyOutcomeDeliveryRecord | None: ...

    def begin_attempt(
        self, notification_id: str, *, now: datetime
    ) -> AutonomyOutcomeDeliveryRecord: ...

    def defer(self, notification_id: str, *, now: datetime) -> AutonomyOutcomeDeliveryRecord: ...

    def mark_delivered(
        self,
        notification_id: str,
        *,
        sent: SentMessage,
        now: datetime,
    ) -> AutonomyOutcomeDeliveryRecord: ...

    def reconcile_interrupted(self, *, now: datetime) -> int: ...


class SQLiteAutonomyOutcomeDeliveryStore:
    """Persist exact outcome content before an IM delivery attempt."""

    def __init__(self, path: Path | str) -> None:
        self._database = SQLiteStateDatabase(path)
        self._init_schema()

    def ensure(self, record: AutonomyOutcomeDeliveryRecord) -> AutonomyOutcomeDeliveryRecord:
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._row(connection, record.notification_id)
            if existing is not None:
                current = _record(existing)
                if _identity(current) != _identity(record):
                    raise ValueError("autonomy outcome delivery identity drift")
                return current
            if (
                connection.execute(
                    "SELECT 1 FROM scheduled_autonomy_outcome_outbox WHERE intent_id = ?",
                    (record.intent_id,),
                ).fetchone()
                is not None
            ):
                raise ValueError("autonomy outcome intent already has a notification")
            connection.execute(
                """
                INSERT INTO scheduled_autonomy_outcome_outbox
                (notification_id, intent_id, binding_sha256, status, next_attempt_at,
                 created_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                _values(record),
            )
        return record

    def load(self, notification_id: str) -> AutonomyOutcomeDeliveryRecord | None:
        with self._database.connect() as connection:
            row = self._row(connection, notification_id)
        return None if row is None else _record(row)

    def for_intent(self, intent_id: str) -> AutonomyOutcomeDeliveryRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_autonomy_outcome_outbox WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
        return None if row is None else _record(cast(tuple[object, ...], row))

    def latest(self, binding_sha256: str) -> AutonomyOutcomeDeliveryRecord | None:
        return self._select(binding_sha256, open_only=False)

    def next_open(self, binding_sha256: str) -> AutonomyOutcomeDeliveryRecord | None:
        return self._select(binding_sha256, open_only=True)

    def begin_attempt(
        self, notification_id: str, *, now: datetime
    ) -> AutonomyOutcomeDeliveryRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, notification_id)
            if record.status in {
                AutonomyOutcomeDeliveryStatus.DELIVERED,
                AutonomyOutcomeDeliveryStatus.EXHAUSTED,
            }:
                return record
            if record.next_attempt_at is not None and record.next_attempt_at > now:
                return record
            updated = record.model_copy(
                update={
                    "status": AutonomyOutcomeDeliveryStatus.SENDING,
                    "attempts": record.attempts + 1,
                    "next_attempt_at": None,
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def defer(self, notification_id: str, *, now: datetime) -> AutonomyOutcomeDeliveryRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, notification_id)
            if record.status is not AutonomyOutcomeDeliveryStatus.SENDING:
                return record
            exhausted = record.attempts >= MAX_AUTONOMY_OUTCOME_DELIVERY_ATTEMPTS
            updated = record.model_copy(
                update={
                    "status": (
                        AutonomyOutcomeDeliveryStatus.EXHAUSTED
                        if exhausted
                        else AutonomyOutcomeDeliveryStatus.RETRYING
                    ),
                    "next_attempt_at": (None if exhausted else now + _retry_delay(record.attempts)),
                    "duplicate_possible": True,
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def mark_delivered(
        self,
        notification_id: str,
        *,
        sent: SentMessage,
        now: datetime,
    ) -> AutonomyOutcomeDeliveryRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, notification_id)
            if record.status is AutonomyOutcomeDeliveryStatus.DELIVERED:
                return record
            if record.status is not AutonomyOutcomeDeliveryStatus.SENDING:
                raise ValueError("autonomy outcome delivery is not sending")
            updated = record.model_copy(
                update={
                    "status": AutonomyOutcomeDeliveryStatus.DELIVERED,
                    "next_attempt_at": None,
                    "updated_at": now,
                    "delivered_at": now,
                    "message_id_sha256": hashlib.sha256(
                        sent.message_id.encode("utf-8")
                    ).hexdigest(),
                }
            )
            self._update(connection, updated)
        return updated

    def reconcile_interrupted(self, *, now: datetime) -> int:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_autonomy_outcome_outbox WHERE status = ?",
                (AutonomyOutcomeDeliveryStatus.SENDING.value,),
            ).fetchall()
            for row in rows:
                record = _record(cast(tuple[object, ...], row))
                exhausted = record.attempts >= MAX_AUTONOMY_OUTCOME_DELIVERY_ATTEMPTS
                updated = record.model_copy(
                    update={
                        "status": (
                            AutonomyOutcomeDeliveryStatus.EXHAUSTED
                            if exhausted
                            else AutonomyOutcomeDeliveryStatus.RETRYING
                        ),
                        "next_attempt_at": None if exhausted else now,
                        "duplicate_possible": True,
                        "updated_at": now,
                    }
                )
                self._update(connection, updated)
        return len(rows)

    def _select(
        self, binding_sha256: str, *, open_only: bool
    ) -> AutonomyOutcomeDeliveryRecord | None:
        where = "binding_sha256 = ?"
        args: tuple[object, ...] = (binding_sha256,)
        if open_only:
            where += " AND status IN (?, ?, ?)"
            args += (
                AutonomyOutcomeDeliveryStatus.PENDING.value,
                AutonomyOutcomeDeliveryStatus.SENDING.value,
                AutonomyOutcomeDeliveryStatus.RETRYING.value,
            )
        order = "created_at, rowid" if open_only else "created_at DESC, rowid DESC"
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_autonomy_outcome_outbox "
                f"WHERE {where} ORDER BY {order} LIMIT 1",
                args,
            ).fetchone()
        return None if row is None else _record(cast(tuple[object, ...], row))

    def _required(
        self, connection: sqlite3.Connection, notification_id: str
    ) -> AutonomyOutcomeDeliveryRecord:
        row = self._row(connection, notification_id)
        if row is None:
            raise ValueError(f"unknown autonomy outcome delivery: {notification_id}")
        return _record(row)

    def _row(
        self, connection: sqlite3.Connection, notification_id: str
    ) -> tuple[object, ...] | None:
        return cast(
            tuple[object, ...] | None,
            connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_autonomy_outcome_outbox "
                "WHERE notification_id = ?",
                (notification_id,),
            ).fetchone(),
        )

    def _update(
        self, connection: sqlite3.Connection, record: AutonomyOutcomeDeliveryRecord
    ) -> None:
        connection.execute(
            """
            UPDATE scheduled_autonomy_outcome_outbox
            SET intent_id = ?, binding_sha256 = ?, status = ?, next_attempt_at = ?,
                created_at = ?, payload = ?
            WHERE notification_id = ?
            """,
            _values(record)[1:] + (record.notification_id,),
        )

    def _init_schema(self) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_autonomy_outcome_outbox (
                    notification_id TEXT PRIMARY KEY,
                    intent_id TEXT NOT NULL UNIQUE,
                    binding_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    next_attempt_at TEXT,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_autonomy_outcome_binding "
                "ON scheduled_autonomy_outcome_outbox(binding_sha256, created_at)"
            )


_COLUMNS = (
    "notification_id, intent_id, binding_sha256, status, next_attempt_at, created_at, payload"
)


def autonomy_outcome_notification_id(intent_id: str) -> str:
    digest = hashlib.sha256(intent_id.encode("utf-8")).hexdigest()[:32]
    return f"autonomy-outcome-{digest}"


def _record(row: tuple[object, ...]) -> AutonomyOutcomeDeliveryRecord:
    record = AutonomyOutcomeDeliveryRecord.model_validate_json(str(row[6]))
    if (
        record.notification_id != str(row[0])
        or record.intent_id != str(row[1])
        or record.binding_sha256 != str(row[2])
        or record.status.value != str(row[3])
        or _optional_time(record.next_attempt_at) != row[4]
        or record.created_at.isoformat() != str(row[5])
    ):
        raise ValueError("autonomy outcome delivery indexed state mismatch")
    return record


def _values(record: AutonomyOutcomeDeliveryRecord) -> tuple[object, ...]:
    return (
        record.notification_id,
        record.intent_id,
        record.binding_sha256,
        record.status.value,
        _optional_time(record.next_attempt_at),
        record.created_at.isoformat(),
        record.model_dump_json(),
    )


def _identity(record: AutonomyOutcomeDeliveryRecord) -> tuple[str, str, str, str]:
    return (
        record.notification_id,
        record.intent_id,
        record.binding_sha256,
        record.envelope.model_dump_json(),
    )


def _optional_time(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _retry_delay(attempts: int) -> timedelta:
    index = min(max(attempts - 1, 0), len(_RETRY_SECONDS) - 1)
    return timedelta(seconds=_RETRY_SECONDS[index])


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("autonomy outcome delivery time must be timezone-aware")
