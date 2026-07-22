"""Durable, bounded delivery state for scheduled morning handoffs."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Protocol, cast

from pydantic import Field, model_validator

from aico.core.models import FrozenModel, SentMessage
from aico.core.morning import MorningHandoffEnvelope
from aico.core.sqlite_state import SQLiteStateDatabase

MAX_MORNING_DELIVERY_ATTEMPTS = 5
_RETRY_SECONDS = (60, 300, 900, 900)


class MorningDeliveryStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    RETRYING = "retrying"
    DELIVERED = "delivered"
    EXHAUSTED = "exhausted"


class MorningDeliveryRecord(FrozenModel):
    delivery_id: str = Field(pattern=r"^morning-[a-f0-9]{32}$")
    binding_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    scheduled_for: datetime
    envelope: MorningHandoffEnvelope
    status: MorningDeliveryStatus = MorningDeliveryStatus.PENDING
    attempts: int = Field(default=0, ge=0, le=MAX_MORNING_DELIVERY_ATTEMPTS)
    next_attempt_at: datetime | None = None
    duplicate_possible: bool = False
    created_at: datetime
    updated_at: datetime
    delivered_at: datetime | None = None
    message_id_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_state(self) -> MorningDeliveryRecord:
        timestamps = (
            self.scheduled_for,
            self.created_at,
            self.updated_at,
            self.next_attempt_at,
            self.delivered_at,
        )
        if any(
            value is not None and (value.tzinfo is None or value.utcoffset() is None)
            for value in timestamps
        ):
            raise ValueError("morning delivery timestamps must be timezone-aware")
        if self.envelope.delivery_id != self.delivery_id:
            raise ValueError("morning delivery envelope identity mismatch")
        delivered = self.status is MorningDeliveryStatus.DELIVERED
        if delivered != (self.delivered_at is not None and self.message_id_sha256 is not None):
            raise ValueError("delivered morning state requires acknowledgement evidence")
        return self


class MorningDeliveryStore(Protocol):
    def enqueue(self, record: MorningDeliveryRecord) -> MorningDeliveryRecord: ...

    def load(self, delivery_id: str) -> MorningDeliveryRecord | None: ...

    def latest(self, binding_sha256: str) -> MorningDeliveryRecord | None: ...

    def next_open(self, binding_sha256: str) -> MorningDeliveryRecord | None: ...

    def begin_attempt(self, delivery_id: str, *, now: datetime) -> MorningDeliveryRecord: ...

    def defer(self, delivery_id: str, *, now: datetime) -> MorningDeliveryRecord: ...

    def mark_delivered(
        self, delivery_id: str, *, sent: SentMessage, now: datetime
    ) -> MorningDeliveryRecord: ...

    def reconcile_interrupted(self, *, now: datetime) -> int: ...


class SQLiteMorningDeliveryStore:
    """Persist exact content before delivery and retain secret-free acknowledgements."""

    def __init__(self, path: Path | str) -> None:
        self._database = SQLiteStateDatabase(path)
        self._init_schema()

    def enqueue(self, record: MorningDeliveryRecord) -> MorningDeliveryRecord:
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._row(connection, record.delivery_id)
            if row is not None:
                existing = _record(row)
                if (
                    existing.binding_sha256 != record.binding_sha256
                    or existing.envelope != record.envelope
                ):
                    raise ValueError("morning delivery identity drift")
                return existing
            connection.execute(
                """
                INSERT INTO morning_delivery_outbox
                (delivery_id, binding_sha256, scheduled_for, payload, status, attempts,
                 next_attempt_at, duplicate_possible, created_at, updated_at,
                 delivered_at, message_id_sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _values(record),
            )
        return record

    def load(self, delivery_id: str) -> MorningDeliveryRecord | None:
        with self._database.connect() as connection:
            row = self._row(connection, delivery_id)
        return None if row is None else _record(row)

    def latest(self, binding_sha256: str) -> MorningDeliveryRecord | None:
        return self._select_open_or_latest(binding_sha256, open_only=False)

    def next_open(self, binding_sha256: str) -> MorningDeliveryRecord | None:
        return self._select_open_or_latest(binding_sha256, open_only=True)

    def begin_attempt(self, delivery_id: str, *, now: datetime) -> MorningDeliveryRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, delivery_id)
            if record.status in {MorningDeliveryStatus.DELIVERED, MorningDeliveryStatus.EXHAUSTED}:
                return record
            if record.next_attempt_at is not None and record.next_attempt_at > now:
                return record
            updated = record.model_copy(
                update={
                    "status": MorningDeliveryStatus.SENDING,
                    "attempts": record.attempts + 1,
                    "next_attempt_at": None,
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def defer(self, delivery_id: str, *, now: datetime) -> MorningDeliveryRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, delivery_id)
            if record.status is not MorningDeliveryStatus.SENDING:
                return record
            exhausted = record.attempts >= MAX_MORNING_DELIVERY_ATTEMPTS
            retry_at = None if exhausted else now + _retry_delay(record.attempts)
            updated = record.model_copy(
                update={
                    "status": (
                        MorningDeliveryStatus.EXHAUSTED
                        if exhausted
                        else MorningDeliveryStatus.RETRYING
                    ),
                    "next_attempt_at": retry_at,
                    "duplicate_possible": True,
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def mark_delivered(
        self,
        delivery_id: str,
        *,
        sent: SentMessage,
        now: datetime,
    ) -> MorningDeliveryRecord:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = self._required(connection, delivery_id)
            if record.status is MorningDeliveryStatus.DELIVERED:
                return record
            if record.status is not MorningDeliveryStatus.SENDING:
                raise ValueError("morning delivery is not sending")
            updated = record.model_copy(
                update={
                    "status": MorningDeliveryStatus.DELIVERED,
                    "next_attempt_at": None,
                    "updated_at": now,
                    "delivered_at": now,
                    "message_id_sha256": hashlib.sha256(sent.message_id.encode()).hexdigest(),
                }
            )
            self._update(connection, updated)
        return updated

    def reconcile_interrupted(self, *, now: datetime) -> int:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT " + _COLUMNS + " FROM morning_delivery_outbox WHERE status = ?",
                (MorningDeliveryStatus.SENDING.value,),
            ).fetchall()
            for row in rows:
                record = _record(row)
                exhausted = record.attempts >= MAX_MORNING_DELIVERY_ATTEMPTS
                updated = record.model_copy(
                    update={
                        "status": (
                            MorningDeliveryStatus.EXHAUSTED
                            if exhausted
                            else MorningDeliveryStatus.RETRYING
                        ),
                        "next_attempt_at": None if exhausted else now,
                        "duplicate_possible": True,
                        "updated_at": now,
                    }
                )
                self._update(connection, updated)
        return len(rows)

    def _select_open_or_latest(
        self, binding_sha256: str, *, open_only: bool
    ) -> MorningDeliveryRecord | None:
        where = "binding_sha256 = ?"
        args: tuple[object, ...] = (binding_sha256,)
        if open_only:
            where += " AND status IN (?, ?, ?)"
            args += (
                MorningDeliveryStatus.PENDING.value,
                MorningDeliveryStatus.SENDING.value,
                MorningDeliveryStatus.RETRYING.value,
            )
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM morning_delivery_outbox "
                f"WHERE {where} ORDER BY scheduled_for, rowid LIMIT 1"
                if open_only
                else f"SELECT {_COLUMNS} FROM morning_delivery_outbox "
                f"WHERE {where} ORDER BY scheduled_for DESC, rowid DESC LIMIT 1",
                args,
            ).fetchone()
        return None if row is None else _record(row)

    def _required(self, connection: sqlite3.Connection, delivery_id: str) -> MorningDeliveryRecord:
        row = self._row(connection, delivery_id)
        if row is None:
            raise ValueError(f"unknown morning delivery: {delivery_id}")
        return _record(row)

    def _row(self, connection: sqlite3.Connection, delivery_id: str) -> tuple[object, ...] | None:
        return cast(
            tuple[object, ...] | None,
            connection.execute(
                f"SELECT {_COLUMNS} FROM morning_delivery_outbox WHERE delivery_id = ?",
                (delivery_id,),
            ).fetchone(),
        )

    def _update(self, connection: sqlite3.Connection, record: MorningDeliveryRecord) -> None:
        connection.execute(
            """
            UPDATE morning_delivery_outbox
            SET binding_sha256 = ?, scheduled_for = ?, payload = ?, status = ?, attempts = ?,
                next_attempt_at = ?, duplicate_possible = ?, created_at = ?, updated_at = ?,
                delivered_at = ?, message_id_sha256 = ?
            WHERE delivery_id = ?
            """,
            _values(record)[1:] + (record.delivery_id,),
        )

    def _init_schema(self) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS morning_delivery_outbox (
                    delivery_id TEXT PRIMARY KEY,
                    binding_sha256 TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    next_attempt_at TEXT,
                    duplicate_possible INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    delivered_at TEXT,
                    message_id_sha256 TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_morning_delivery_binding "
                "ON morning_delivery_outbox(binding_sha256, scheduled_for)"
            )


_COLUMNS = (
    "delivery_id, binding_sha256, scheduled_for, payload, status, attempts, "
    "next_attempt_at, duplicate_possible, created_at, updated_at, delivered_at, "
    "message_id_sha256"
)


def _record(row: tuple[object, ...]) -> MorningDeliveryRecord:
    envelope = MorningHandoffEnvelope.model_validate_json(str(row[3]))
    return MorningDeliveryRecord(
        delivery_id=str(row[0]),
        binding_sha256=str(row[1]),
        scheduled_for=datetime.fromisoformat(str(row[2])),
        envelope=envelope,
        status=MorningDeliveryStatus(str(row[4])),
        attempts=int(str(row[5])),
        next_attempt_at=None if row[6] is None else datetime.fromisoformat(str(row[6])),
        duplicate_possible=bool(row[7]),
        created_at=datetime.fromisoformat(str(row[8])),
        updated_at=datetime.fromisoformat(str(row[9])),
        delivered_at=None if row[10] is None else datetime.fromisoformat(str(row[10])),
        message_id_sha256=None if row[11] is None else str(row[11]),
    )


def _values(record: MorningDeliveryRecord) -> tuple[object, ...]:
    return (
        record.delivery_id,
        record.binding_sha256,
        record.scheduled_for.isoformat(),
        record.envelope.model_dump_json(),
        record.status.value,
        record.attempts,
        None if record.next_attempt_at is None else record.next_attempt_at.isoformat(),
        int(record.duplicate_possible),
        record.created_at.isoformat(),
        record.updated_at.isoformat(),
        None if record.delivered_at is None else record.delivered_at.isoformat(),
        record.message_id_sha256,
    )


def _retry_delay(attempts: int) -> timedelta:
    index = min(max(attempts - 1, 0), len(_RETRY_SECONDS) - 1)
    return timedelta(seconds=_RETRY_SECONDS[index])


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("morning delivery time must be timezone-aware")
