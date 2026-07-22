"""Durable out-of-band alerts for confirmed runtime incidents."""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field

from aico.app.runtime_health import RuntimeComponentHealth, RuntimeHealthSnapshot
from aico.app.runtime_self_healing import (
    OwnedTaskRecoveryHealth,
    RecoveryStatus,
    RuntimeSelfHealingSnapshot,
)
from aico.core.models import HealthStatus
from aico.core.sqlite_state import SQLiteStateDatabase

log = logging.getLogger(__name__)
CONFIRMED_HEALTH_FAILURE_CHECKS = 3
_SAFE_COMPONENT = re.compile(r"^[a-z0-9][a-z0-9:._-]{0,127}$")


class RuntimeAlertEventType(StrEnum):
    INCIDENT_OPENED = "incident_opened"
    INCIDENT_RESOLVED = "incident_resolved"


class RuntimeAlertDeliveryStatus(StrEnum):
    DISABLED = "disabled"
    HEALTHY = "healthy"
    PENDING = "pending"
    FAILED = "failed"


class RuntimeAlertEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(min_length=1)
    incident_id: str = Field(min_length=1)
    event_type: RuntimeAlertEventType
    component: str = Field(pattern=r"^[a-z0-9][a-z0-9:._-]{0,127}$")
    attempts: int = Field(ge=0)
    occurred_at: datetime

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            **self.model_dump(mode="json"),
        }


class RuntimeAlertSink(Protocol):
    async def send(self, event: RuntimeAlertEvent) -> None: ...


class WebhookRuntimeAlertSink:
    """Send vendor-neutral alert JSON to an owner-configured endpoint."""

    def __init__(
        self,
        *,
        url: str,
        bearer_token: str | None = None,
        timeout_seconds: float = 5,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        parsed_url = httpx.URL(url)
        if parsed_url.scheme != "https" or parsed_url.host is None:
            raise ValueError("runtime alert webhook URL must use HTTPS")
        if timeout_seconds <= 0:
            raise ValueError("runtime alert webhook timeout must be positive")
        self._url = url
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def send(self, event: RuntimeAlertEvent) -> None:
        headers = {"Idempotency-Key": event.event_id}
        if self._bearer_token is not None:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        if self._client is not None:
            await self._post(self._client, event, headers)
            return
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            await self._post(client, event, headers)

    async def _post(
        self,
        client: httpx.AsyncClient,
        event: RuntimeAlertEvent,
        headers: dict[str, str],
    ) -> None:
        response = await client.post(
            self._url,
            json=event.to_payload(),
            headers=headers,
        )
        response.raise_for_status()


class SQLiteRuntimeAlertStore:
    """Persist active runtime incidents and immutable delivery events."""

    def __init__(
        self,
        path: Path | str,
        *,
        incident_id_factory: Callable[[], str] | None = None,
        event_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._database = SQLiteStateDatabase(path)
        self._incident_id_factory = incident_id_factory or _new_id
        self._event_id_factory = event_id_factory or _new_id
        self._init_schema()

    def observe(
        self,
        snapshot: RuntimeSelfHealingSnapshot,
        health_snapshot: RuntimeHealthSnapshot | None = None,
    ) -> tuple[RuntimeAlertEvent, ...]:
        created: list[RuntimeAlertEvent] = []
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            recovery_statuses = {
                component.name: component.status for component in snapshot.components
            }
            for component in sorted(snapshot.components, key=lambda item: item.name):
                event = self._observe_component(connection, component, snapshot.checked_at)
                if event is not None:
                    created.append(event)
            if health_snapshot is not None:
                for health_component in sorted(
                    health_snapshot.components,
                    key=lambda item: (item.kind, item.name),
                ):
                    event = self._observe_health_component(
                        connection,
                        health_component,
                        health_snapshot.checked_at,
                        recovery_status=recovery_statuses.get(
                            f"{health_component.kind}:{health_component.name}"
                        ),
                    )
                    if event is not None:
                        created.append(event)
        return tuple(created)

    def load_pending(
        self,
        *,
        limit: int,
        now: datetime,
    ) -> tuple[RuntimeAlertEvent, ...]:
        if limit <= 0:
            raise ValueError("runtime alert batch limit must be positive")
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT payload, next_attempt_at
                FROM runtime_alert_outbox
                WHERE delivered = 0
                ORDER BY rowid
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        events: list[RuntimeAlertEvent] = []
        for payload, next_attempt_at in rows:
            if next_attempt_at is not None:
                retry_at = datetime.fromisoformat(str(next_attempt_at))
                if retry_at > now:
                    break
            events.append(RuntimeAlertEvent.model_validate_json(payload))
        return tuple(events)

    def mark_delivered(self, event_id: str) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE runtime_alert_outbox SET delivered = 1 WHERE event_id = ?",
                (event_id,),
            )

    def defer(self, event_id: str, *, failed_at: datetime) -> None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT delivery_attempts FROM runtime_alert_outbox WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"unknown runtime alert event: {event_id}")
            attempts = int(row[0]) + 1
            next_attempt_at = failed_at + _retry_delay(attempts)
            connection.execute(
                """
                UPDATE runtime_alert_outbox
                SET delivery_attempts = ?, next_attempt_at = ?
                WHERE event_id = ? AND delivered = 0
                """,
                (attempts, next_attempt_at.isoformat(), event_id),
            )

    def pending_count(self) -> int:
        return self._count("runtime_alert_outbox", "WHERE delivered = 0")

    def active_incident_count(self) -> int:
        return self._count("runtime_alert_incidents")

    def health_observation_count(self) -> int:
        return self._count("runtime_health_alert_observations")

    def _observe_component(
        self,
        connection: sqlite3.Connection,
        component: OwnedTaskRecoveryHealth,
        checked_at: datetime,
    ) -> RuntimeAlertEvent | None:
        name = component.name
        status = component.status
        attempts = component.attempts
        row = connection.execute(
            "SELECT incident_id, attempts FROM runtime_alert_incidents WHERE component = ?",
            (name,),
        ).fetchone()
        if status is RecoveryStatus.OPEN and row is None:
            health_incident = connection.execute(
                "SELECT 1 FROM runtime_alert_incidents WHERE component = ?",
                (f"health:{name}",),
            ).fetchone()
            if health_incident is not None:
                return None
            return self._open_incident(connection, name, attempts, checked_at)
        if status is RecoveryStatus.HEALTHY and row is not None:
            return self._resolve_incident(
                connection,
                name,
                incident_id=str(row[0]),
                attempts=int(row[1]),
                checked_at=checked_at,
            )
        return None

    def _observe_health_component(
        self,
        connection: sqlite3.Connection,
        component: RuntimeComponentHealth,
        checked_at: datetime,
        *,
        recovery_status: RecoveryStatus | None,
    ) -> RuntimeAlertEvent | None:
        name = _health_component_name(component)
        incident = connection.execute(
            "SELECT incident_id, attempts FROM runtime_alert_incidents WHERE component = ?",
            (name,),
        ).fetchone()
        if recovery_status in {RecoveryStatus.OPEN, RecoveryStatus.RECOVERING}:
            self._clear_health_observation(connection, name)
            return None
        if not component.required:
            self._clear_health_observation(connection, name)
            if incident is not None:
                return self._resolve_incident(
                    connection,
                    name,
                    incident_id=str(incident[0]),
                    attempts=int(incident[1]),
                    checked_at=checked_at,
                )
            return None
        if component.status is HealthStatus.FAILED:
            failures = self._record_health_failure(connection, name, checked_at)
            if failures >= CONFIRMED_HEALTH_FAILURE_CHECKS and incident is None:
                return self._open_incident(connection, name, failures, checked_at)
            return None
        self._clear_health_observation(connection, name)
        if component.status is HealthStatus.OK and incident is not None:
            return self._resolve_incident(
                connection,
                name,
                incident_id=str(incident[0]),
                attempts=int(incident[1]),
                checked_at=checked_at,
            )
        return None

    def _record_health_failure(
        self,
        connection: sqlite3.Connection,
        component: str,
        checked_at: datetime,
    ) -> int:
        row = connection.execute(
            "SELECT consecutive_failures, last_checked_at "
            "FROM runtime_health_alert_observations "
            "WHERE component = ?",
            (component,),
        ).fetchone()
        if row is not None and checked_at <= datetime.fromisoformat(str(row[1])):
            return int(row[0])
        failures = 1 if row is None else int(row[0]) + 1
        connection.execute(
            """
            INSERT INTO runtime_health_alert_observations (
                component, consecutive_failures, last_checked_at
            ) VALUES (?, ?, ?)
            ON CONFLICT(component) DO UPDATE SET
                consecutive_failures = excluded.consecutive_failures,
                last_checked_at = excluded.last_checked_at
            """,
            (component, failures, checked_at.isoformat()),
        )
        return failures

    def _clear_health_observation(
        self,
        connection: sqlite3.Connection,
        component: str,
    ) -> None:
        connection.execute(
            "DELETE FROM runtime_health_alert_observations WHERE component = ?",
            (component,),
        )

    def _open_incident(
        self,
        connection: sqlite3.Connection,
        component: str,
        attempts: int,
        checked_at: datetime,
    ) -> RuntimeAlertEvent:
        incident_id = self._incident_id_factory()
        event = RuntimeAlertEvent(
            event_id=self._event_id_factory(),
            incident_id=incident_id,
            event_type=RuntimeAlertEventType.INCIDENT_OPENED,
            component=component,
            attempts=attempts,
            occurred_at=checked_at,
        )
        connection.execute(
            """
            INSERT INTO runtime_alert_incidents (component, incident_id, attempts, opened_at)
            VALUES (?, ?, ?, ?)
            """,
            (component, incident_id, attempts, checked_at.isoformat()),
        )
        self._insert_outbox(connection, event)
        return event

    def _resolve_incident(
        self,
        connection: sqlite3.Connection,
        component: str,
        *,
        incident_id: str,
        attempts: int,
        checked_at: datetime,
    ) -> RuntimeAlertEvent:
        event = RuntimeAlertEvent(
            event_id=self._event_id_factory(),
            incident_id=incident_id,
            event_type=RuntimeAlertEventType.INCIDENT_RESOLVED,
            component=component,
            attempts=attempts,
            occurred_at=checked_at,
        )
        connection.execute(
            "DELETE FROM runtime_alert_incidents WHERE component = ?",
            (component,),
        )
        self._insert_outbox(connection, event)
        return event

    def _insert_outbox(
        self,
        connection: sqlite3.Connection,
        event: RuntimeAlertEvent,
    ) -> None:
        connection.execute(
            """
            INSERT INTO runtime_alert_outbox (
                event_id, incident_id, event_type, payload, delivered
            ) VALUES (?, ?, ?, ?, 0)
            """,
            (
                event.event_id,
                event.incident_id,
                event.event_type.value,
                event.model_dump_json(),
            ),
        )

    def _count(self, table: str, where: str = "") -> int:
        with self._database.connect() as connection:
            row = connection.execute(f"SELECT COUNT(*) FROM {table} {where}").fetchone()
        return int(row[0]) if row is not None else 0

    def _init_schema(self) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_alert_incidents (
                    component TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL UNIQUE,
                    attempts INTEGER NOT NULL CHECK (attempts >= 0),
                    opened_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_alert_outbox (
                    event_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    delivered INTEGER NOT NULL DEFAULT 0 CHECK (delivered IN (0, 1)),
                    delivery_attempts INTEGER NOT NULL DEFAULT 0 CHECK (delivery_attempts >= 0),
                    next_attempt_at TEXT,
                    UNIQUE (incident_id, event_type)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_health_alert_observations (
                    component TEXT PRIMARY KEY,
                    consecutive_failures INTEGER NOT NULL
                        CHECK (consecutive_failures >= 1),
                    last_checked_at TEXT NOT NULL
                )
                """
            )


class RuntimeAlertCoordinator:
    """Observe confirmed runtime transitions and deliver pending events in order."""

    def __init__(
        self,
        *,
        store: SQLiteRuntimeAlertStore,
        sink: RuntimeAlertSink,
        batch_limit: int = 10,
    ) -> None:
        if batch_limit <= 0:
            raise ValueError("runtime alert batch limit must be positive")
        self._store = store
        self._sink = sink
        self._batch_limit = batch_limit

    async def check(
        self,
        snapshot: RuntimeSelfHealingSnapshot,
        health_snapshot: RuntimeHealthSnapshot | None = None,
    ) -> RuntimeAlertDeliverySnapshot:
        self._store.observe(snapshot, health_snapshot)
        checked_at = snapshot.checked_at
        if health_snapshot is not None and health_snapshot.checked_at > checked_at:
            checked_at = health_snapshot.checked_at
        for event in self._store.load_pending(
            limit=self._batch_limit,
            now=checked_at,
        ):
            try:
                await self._sink.send(event)
            except Exception as exc:
                log.error(
                    "Runtime alert delivery failed: event_id=%s component=%s type=%s",
                    event.event_id,
                    event.component,
                    type(exc).__name__,
                )
                self._store.defer(event.event_id, failed_at=checked_at)
                break
            self._store.mark_delivered(event.event_id)
        pending = self._store.pending_count()
        return RuntimeAlertDeliverySnapshot(
            status=(
                RuntimeAlertDeliveryStatus.PENDING
                if pending > 0
                else RuntimeAlertDeliveryStatus.HEALTHY
            ),
            checked_at=checked_at,
            pending_events=pending,
        )


class RuntimeAlertDeliverySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: RuntimeAlertDeliveryStatus
    checked_at: datetime
    pending_events: int | None = Field(default=None, ge=0)

    def to_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json")


def disabled_runtime_alert_snapshot(checked_at: datetime) -> RuntimeAlertDeliverySnapshot:
    return RuntimeAlertDeliverySnapshot(
        status=RuntimeAlertDeliveryStatus.DISABLED,
        checked_at=checked_at,
        pending_events=0,
    )


def failed_runtime_alert_snapshot(checked_at: datetime) -> RuntimeAlertDeliverySnapshot:
    return RuntimeAlertDeliverySnapshot(
        status=RuntimeAlertDeliveryStatus.FAILED,
        checked_at=checked_at,
        pending_events=None,
    )


def _new_id() -> str:
    return str(uuid4())


def _retry_delay(attempts: int) -> timedelta:
    seconds = (60, 300, 900)[min(attempts, 3) - 1]
    return timedelta(seconds=seconds)


def _health_component_name(component: RuntimeComponentHealth) -> str:
    candidate = f"health:{component.kind}:{component.name}"
    if _SAFE_COMPONENT.fullmatch(candidate):
        return candidate
    digest = hashlib.sha256(f"{component.kind}:{component.name}".encode()).hexdigest()[:16]
    return f"health:{component.kind}:id-{digest}"
