"""Durable execution intent for standing autonomy after a morning acknowledgement."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Protocol, cast

from pydantic import Field, model_validator

from aico.core.models import FrozenModel
from aico.core.sqlite_state import SQLiteStateDatabase
from aico.core.standing_autonomy import StandingAutonomyRunReceipt

MAX_SCHEDULED_AUTONOMY_ATTEMPTS = 5
_RETRY_SECONDS = (60, 300, 900, 900)


class ScheduledAutonomyStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    SETTLED = "settled"
    EXHAUSTED = "exhausted"


class ScheduledAutonomyIntent(FrozenModel):
    intent_id: str = Field(pattern=r"^autonomy-[a-f0-9]{32}$")
    delivery_id: str = Field(pattern=r"^morning-[a-f0-9]{32}$")
    binding_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    project_id: str = Field(min_length=1)
    status: ScheduledAutonomyStatus = ScheduledAutonomyStatus.PENDING
    attempts: int = Field(default=0, ge=0, le=MAX_SCHEDULED_AUTONOMY_ATTEMPTS)
    next_attempt_at: datetime | None = None
    duplicate_notification_possible: bool = False
    created_at: datetime
    updated_at: datetime
    settled_at: datetime | None = None
    receipt: StandingAutonomyRunReceipt | None = None

    @model_validator(mode="after")
    def validate_state(self) -> ScheduledAutonomyIntent:
        timestamps = (self.created_at, self.updated_at, self.next_attempt_at, self.settled_at)
        if any(
            value is not None and (value.tzinfo is None or value.utcoffset() is None)
            for value in timestamps
        ):
            raise ValueError("scheduled autonomy timestamps must be timezone-aware")
        settled = self.status is ScheduledAutonomyStatus.SETTLED
        if settled != (self.settled_at is not None and self.receipt is not None):
            raise ValueError("settled autonomy intent requires a run receipt")
        if self.receipt is not None and (
            self.receipt.intent_id != self.intent_id or self.receipt.project_id != self.project_id
        ):
            raise ValueError("scheduled autonomy receipt binding mismatch")
        return self


class ScheduledAutonomyStore(Protocol):
    def ensure(self, intent: ScheduledAutonomyIntent) -> ScheduledAutonomyIntent: ...

    def load(self, intent_id: str) -> ScheduledAutonomyIntent | None: ...

    def latest(self, binding_sha256: str) -> ScheduledAutonomyIntent | None: ...

    def next_open(self, binding_sha256: str) -> ScheduledAutonomyIntent | None: ...

    def interrupted(self, binding_sha256: str) -> tuple[ScheduledAutonomyIntent, ...]: ...

    def begin_attempt(self, intent_id: str, *, now: datetime) -> ScheduledAutonomyIntent: ...

    def defer(
        self,
        intent_id: str,
        *,
        now: datetime,
        immediate: bool = False,
    ) -> ScheduledAutonomyIntent: ...

    def mark_settled(
        self,
        intent_id: str,
        *,
        receipt: StandingAutonomyRunReceipt,
        now: datetime,
    ) -> ScheduledAutonomyIntent: ...


class SQLiteScheduledAutonomyStore:
    """Persist intent before any morning message can trigger autonomous execution."""

    def __init__(self, path: Path | str) -> None:
        self._database = SQLiteStateDatabase(path)
        self._init_schema()

    def ensure(self, intent: ScheduledAutonomyIntent) -> ScheduledAutonomyIntent:
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._row(connection, intent.intent_id)
            if row is not None:
                existing = _intent(row)
                if _identity(existing) != _identity(intent):
                    raise ValueError("scheduled autonomy intent identity drift")
                return existing
            connection.execute(
                """
                INSERT INTO scheduled_autonomy_intents
                (intent_id, delivery_id, binding_sha256, project_id, status,
                 next_attempt_at, created_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _values(intent),
            )
        return intent

    def load(self, intent_id: str) -> ScheduledAutonomyIntent | None:
        with self._database.connect() as connection:
            row = self._row(connection, intent_id)
        return None if row is None else _intent(row)

    def latest(self, binding_sha256: str) -> ScheduledAutonomyIntent | None:
        return self._select(binding_sha256, open_only=False)

    def next_open(self, binding_sha256: str) -> ScheduledAutonomyIntent | None:
        return self._select(binding_sha256, open_only=True)

    def interrupted(self, binding_sha256: str) -> tuple[ScheduledAutonomyIntent, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_autonomy_intents "
                "WHERE binding_sha256 = ? AND status = ? ORDER BY created_at, rowid",
                (binding_sha256, ScheduledAutonomyStatus.RUNNING.value),
            ).fetchall()
        return tuple(_intent(cast(tuple[object, ...], row)) for row in rows)

    def begin_attempt(self, intent_id: str, *, now: datetime) -> ScheduledAutonomyIntent:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            intent = self._required(connection, intent_id)
            if intent.status in {
                ScheduledAutonomyStatus.SETTLED,
                ScheduledAutonomyStatus.EXHAUSTED,
            }:
                return intent
            if intent.next_attempt_at is not None and intent.next_attempt_at > now:
                return intent
            updated = intent.model_copy(
                update={
                    "status": ScheduledAutonomyStatus.RUNNING,
                    "attempts": intent.attempts + 1,
                    "next_attempt_at": None,
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def defer(
        self,
        intent_id: str,
        *,
        now: datetime,
        immediate: bool = False,
    ) -> ScheduledAutonomyIntent:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            intent = self._required(connection, intent_id)
            if intent.status is not ScheduledAutonomyStatus.RUNNING:
                return intent
            exhausted = intent.attempts >= MAX_SCHEDULED_AUTONOMY_ATTEMPTS
            retry_at = None
            if not exhausted:
                retry_at = now if immediate else now + _retry_delay(intent.attempts)
            updated = intent.model_copy(
                update={
                    "status": (
                        ScheduledAutonomyStatus.EXHAUSTED
                        if exhausted
                        else ScheduledAutonomyStatus.RETRYING
                    ),
                    "next_attempt_at": retry_at,
                    "duplicate_notification_possible": True,
                    "updated_at": now,
                }
            )
            self._update(connection, updated)
        return updated

    def mark_settled(
        self,
        intent_id: str,
        *,
        receipt: StandingAutonomyRunReceipt,
        now: datetime,
    ) -> ScheduledAutonomyIntent:
        _require_aware(now)
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            intent = self._required(connection, intent_id)
            if intent.status is ScheduledAutonomyStatus.SETTLED:
                if intent.receipt != receipt:
                    raise ValueError("scheduled autonomy receipt drift")
                return intent
            if intent.status is not ScheduledAutonomyStatus.RUNNING:
                raise ValueError("scheduled autonomy intent is not running")
            updated = intent.model_copy(
                update={
                    "status": ScheduledAutonomyStatus.SETTLED,
                    "next_attempt_at": None,
                    "updated_at": now,
                    "settled_at": now,
                    "receipt": receipt,
                }
            )
            self._update(connection, updated)
        return updated

    def _select(
        self,
        binding_sha256: str,
        *,
        open_only: bool,
    ) -> ScheduledAutonomyIntent | None:
        where = "binding_sha256 = ?"
        args: tuple[object, ...] = (binding_sha256,)
        if open_only:
            where += " AND status IN (?, ?)"
            args += (
                ScheduledAutonomyStatus.PENDING.value,
                ScheduledAutonomyStatus.RETRYING.value,
            )
        order = "created_at, rowid" if open_only else "created_at DESC, rowid DESC"
        with self._database.connect() as connection:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_autonomy_intents "
                f"WHERE {where} ORDER BY {order} LIMIT 1",
                args,
            ).fetchone()
        return None if row is None else _intent(cast(tuple[object, ...], row))

    def _required(
        self,
        connection: sqlite3.Connection,
        intent_id: str,
    ) -> ScheduledAutonomyIntent:
        row = self._row(connection, intent_id)
        if row is None:
            raise ValueError(f"unknown scheduled autonomy intent: {intent_id}")
        return _intent(row)

    def _row(
        self,
        connection: sqlite3.Connection,
        intent_id: str,
    ) -> tuple[object, ...] | None:
        return cast(
            tuple[object, ...] | None,
            connection.execute(
                f"SELECT {_COLUMNS} FROM scheduled_autonomy_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone(),
        )

    def _update(
        self,
        connection: sqlite3.Connection,
        intent: ScheduledAutonomyIntent,
    ) -> None:
        connection.execute(
            """
            UPDATE scheduled_autonomy_intents
            SET delivery_id = ?, binding_sha256 = ?, project_id = ?, status = ?,
                next_attempt_at = ?, created_at = ?, payload = ?
            WHERE intent_id = ?
            """,
            _values(intent)[1:] + (intent.intent_id,),
        )

    def _init_schema(self) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_autonomy_intents (
                    intent_id TEXT PRIMARY KEY,
                    delivery_id TEXT NOT NULL UNIQUE,
                    binding_sha256 TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    next_attempt_at TEXT,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_scheduled_autonomy_binding "
                "ON scheduled_autonomy_intents(binding_sha256, created_at)"
            )


_COLUMNS = (
    "intent_id, delivery_id, binding_sha256, project_id, status, "
    "next_attempt_at, created_at, payload"
)


def _intent(row: tuple[object, ...]) -> ScheduledAutonomyIntent:
    intent = ScheduledAutonomyIntent.model_validate_json(str(row[7]))
    indexed = (
        str(row[0]),
        str(row[1]),
        str(row[2]),
        str(row[3]),
        str(row[4]),
        None if row[5] is None else str(row[5]),
        str(row[6]),
    )
    expected = (
        intent.intent_id,
        intent.delivery_id,
        intent.binding_sha256,
        intent.project_id,
        intent.status.value,
        None if intent.next_attempt_at is None else intent.next_attempt_at.isoformat(),
        intent.created_at.isoformat(),
    )
    if indexed != expected:
        raise ValueError("scheduled autonomy indexed state mismatch")
    return intent


def _values(intent: ScheduledAutonomyIntent) -> tuple[object, ...]:
    return (
        intent.intent_id,
        intent.delivery_id,
        intent.binding_sha256,
        intent.project_id,
        intent.status.value,
        None if intent.next_attempt_at is None else intent.next_attempt_at.isoformat(),
        intent.created_at.isoformat(),
        intent.model_dump_json(),
    )


def _identity(intent: ScheduledAutonomyIntent) -> tuple[str, str, str, str]:
    return (
        intent.intent_id,
        intent.delivery_id,
        intent.binding_sha256,
        intent.project_id,
    )


def _retry_delay(attempts: int) -> timedelta:
    index = min(max(attempts - 1, 0), len(_RETRY_SECONDS) - 1)
    return timedelta(seconds=_RETRY_SECONDS[index])


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("scheduled autonomy time must be timezone-aware")
