"""Dedicated SQLite state for the independent dead-man receiver."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from aico.app.dead_man_receiver_models import (
    DeadManEvent,
    DeadManEventType,
    DeadManEvidenceBundle,
    DeadManEvidenceEvent,
    DeadManMonitorSnapshot,
    DeadManNotificationPolicySnapshot,
    DeadManNotificationProbeContract,
    DeadManNotificationProbeEvent,
    DeadManNotificationProbeSnapshot,
    DeadManNotificationRouteSnapshot,
    DeadManNotificationRouteStatus,
    DeadManOutageEvidence,
    DeadManOutageReason,
    DeadManPulseReason,
    DeadManPulseReceipt,
    DeadManRouteHealthEvent,
    DeadManRouteHealthEventType,
    DeadManRouteHealthEvidence,
    DeadManRouteObservationSource,
)
from aico.app.runtime_liveness import (
    RuntimeAlertDeliverySignal,
    RuntimeLivenessPulse,
    RuntimeLivenessReceiverStatus,
)

DEAD_MAN_RECEIVER_SCHEMA_VERSION: Literal[5] = 5
DEAD_MAN_RECEIVER_TABLES = (
    "dead_man_monitors",
    "dead_man_notification_outbox",
    "dead_man_notification_policy",
    "dead_man_notification_probe",
    "dead_man_notification_routes",
    "dead_man_route_health_outbox",
)


class DeadManMonitorNotArmedError(RuntimeError):
    pass


class DeadManMonitorConflictError(RuntimeError):
    pass


class DeadManReceiverSchemaError(RuntimeError):
    pass


class DeadManNotificationPolicyConflictError(RuntimeError):
    pass


class SQLiteDeadManReceiverStore:
    """Persist monitor, outage and notification intent in one receiver database."""

    def __init__(
        self,
        path: Path | str,
        *,
        outage_id_factory: Callable[[], str] | None = None,
        event_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._outage_id_factory = outage_id_factory or _new_id
        self._event_id_factory = event_id_factory or _new_id
        _init_schema(self._path)

    def configure_notification_policy(
        self,
        *,
        configured_routes: int,
        minimum_acknowledgements: int,
        configured_at: datetime,
    ) -> DeadManNotificationPolicySnapshot:
        return _configure_notification_policy(
            self._path,
            configured_routes=configured_routes,
            minimum_acknowledgements=minimum_acknowledgements,
            configured_at=configured_at,
        )

    def get_notification_policy(self) -> DeadManNotificationPolicySnapshot:
        with self._connect() as connection:
            return _notification_policy_snapshot(_notification_policy_row(connection))

    def configure_notification_probe(
        self,
        *,
        contract: DeadManNotificationProbeContract,
        interval_seconds: int,
        failure_threshold: int,
        max_age_seconds: int,
        configured_at: datetime,
    ) -> DeadManNotificationProbeSnapshot:
        return _configure_notification_probe(
            self._path,
            contract=contract,
            interval_seconds=interval_seconds,
            failure_threshold=failure_threshold,
            max_age_seconds=max_age_seconds,
            configured_at=configured_at,
        )

    def get_notification_probe(self) -> DeadManNotificationProbeSnapshot:
        with self._connect() as connection:
            return _notification_probe_snapshot(_notification_probe_row(connection))

    def arm(
        self,
        runtime_id: str,
        *,
        expires_after_seconds: int,
        armed_at: datetime,
    ) -> DeadManMonitorSnapshot:
        _require_aware(armed_at)
        if expires_after_seconds <= 0:
            raise ValueError("dead-man monitor TTL must be positive")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._monitor_row(connection, runtime_id)
            if row is None:
                connection.execute(
                    """
                    INSERT INTO dead_man_monitors (
                        runtime_id, expires_after_seconds, armed_at, updated_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        runtime_id,
                        expires_after_seconds,
                        armed_at.isoformat(),
                        armed_at.isoformat(),
                    ),
                )
                row = self._required_monitor_row(connection, runtime_id)
            elif int(row["expires_after_seconds"]) != expires_after_seconds:
                raise DeadManMonitorConflictError(
                    "monitor TTL change requires explicit disarm then arm"
                )
            return _monitor_snapshot(row)

    def disarm(self, runtime_id: str) -> bool:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            result = connection.execute(
                "DELETE FROM dead_man_monitors WHERE runtime_id = ?",
                (runtime_id,),
            )
            return result.rowcount > 0

    def get_monitor(self, runtime_id: str) -> DeadManMonitorSnapshot:
        with self._connect() as connection:
            row = self._monitor_row(connection, runtime_id)
        if row is None:
            raise DeadManMonitorNotArmedError("runtime monitor is not armed")
        return _monitor_snapshot(row)

    def accept(
        self,
        pulse: RuntimeLivenessPulse,
        *,
        received_at: datetime,
    ) -> DeadManPulseReceipt:
        _require_aware(received_at)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._monitor_row(connection, pulse.runtime_id)
            if row is None:
                raise DeadManMonitorNotArmedError("runtime monitor is not armed")
            self._require_matching_ttl(row, pulse)
            if not _is_newer_pulse(row, pulse):
                self._open_if_expired(connection, row, now=received_at)
                row = self._required_monitor_row(connection, pulse.runtime_id)
                return DeadManPulseReceipt(
                    accepted=False,
                    reason=DeadManPulseReason.DUPLICATE_OR_OLDER,
                    status=_monitor_status(row),
                )
            if not pulse.renews_monitor:
                return self._accept_without_renewal(
                    connection,
                    row,
                    pulse,
                    received_at=received_at,
                )
            return self._accept_with_renewal(
                connection,
                row,
                pulse,
                received_at=received_at,
            )

    def _accept_with_renewal(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        pulse: RuntimeLivenessPulse,
        *,
        received_at: datetime,
    ) -> DeadManPulseReceipt:
        self._open_if_expired(connection, row, now=received_at)
        row = self._required_monitor_row(connection, pulse.runtime_id)
        resolved = self._resolve_if_open(connection, row, received_at=received_at)
        connection.execute(
            """
            UPDATE dead_man_monitors
            SET boot_id = ?, sequence = ?, sent_at = ?, last_received_at = ?,
                last_pulse_received_at = ?, alert_delivery_status = ?,
                outage_id = NULL, outage_opened_at = NULL, outage_reason = NULL,
                updated_at = ?
            WHERE runtime_id = ?
            """,
            (
                pulse.boot_id,
                pulse.sequence,
                pulse.sent_at.isoformat(),
                received_at.isoformat(),
                received_at.isoformat(),
                pulse.alert_delivery_status.value,
                received_at.isoformat(),
                pulse.runtime_id,
            ),
        )
        return DeadManPulseReceipt(
            accepted=True,
            reason=DeadManPulseReason.ACCEPTED,
            status=RuntimeLivenessReceiverStatus.HEALTHY,
            renewed=True,
            outage_resolved=resolved,
        )

    def _accept_without_renewal(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        pulse: RuntimeLivenessPulse,
        *,
        received_at: datetime,
    ) -> DeadManPulseReceipt:
        del row
        connection.execute(
            """
            UPDATE dead_man_monitors
            SET boot_id = ?, sequence = ?, sent_at = ?, last_pulse_received_at = ?,
                alert_delivery_status = ?, updated_at = ?
            WHERE runtime_id = ?
            """,
            (
                pulse.boot_id,
                pulse.sequence,
                pulse.sent_at.isoformat(),
                received_at.isoformat(),
                pulse.alert_delivery_status.value,
                received_at.isoformat(),
                pulse.runtime_id,
            ),
        )
        current = self._required_monitor_row(connection, pulse.runtime_id)
        self._open_if_expired(connection, current, now=received_at)
        current = self._required_monitor_row(connection, pulse.runtime_id)
        return DeadManPulseReceipt(
            accepted=True,
            reason=DeadManPulseReason.ACCEPTED_WITHOUT_RENEWAL,
            status=_monitor_status(current),
            renewed=False,
        )

    def evaluate(self, *, now: datetime) -> tuple[DeadManEvent, ...]:
        _require_aware(now)
        created: list[DeadManEvent] = []
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT * FROM dead_man_monitors ORDER BY runtime_id"
            ).fetchall()
            for row in rows:
                event = self._open_if_expired(connection, row, now=now)
                if event is not None:
                    created.append(event)
        return tuple(created)

    def load_pending(self, *, limit: int, now: datetime) -> tuple[DeadManEvent, ...]:
        if limit <= 0:
            raise ValueError("dead-man notification batch limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload, next_attempt_at
                FROM dead_man_notification_outbox
                WHERE delivered = 0
                ORDER BY row_id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        events: list[DeadManEvent] = []
        for row in rows:
            next_attempt_at = row["next_attempt_at"]
            if next_attempt_at is not None and _parse_time(next_attempt_at) > now:
                break
            events.append(DeadManEvent.model_validate_json(row["payload"]))
        return tuple(events)

    def record_notification_attempt(
        self,
        event_id: str,
        *,
        acknowledged_routes: tuple[bool, ...] | None,
        transport_succeeded: bool,
        attempted_at: datetime,
    ) -> bool:
        return _record_notification_attempt(
            self._path,
            event_id,
            acknowledged_routes=acknowledged_routes,
            transport_succeeded=transport_succeeded,
            attempted_at=attempted_at,
        )

    def ensure_notification_probe_due(
        self,
        *,
        now: datetime,
    ) -> DeadManNotificationProbeEvent | None:
        return _ensure_notification_probe_due(self._path, now=now)

    def record_notification_probe_attempt(
        self,
        event_id: str,
        *,
        acknowledged_routes: tuple[bool, ...] | None,
        transport_succeeded: bool,
        attempted_at: datetime,
    ) -> None:
        _record_notification_probe_attempt(
            self._path,
            event_id,
            acknowledged_routes=acknowledged_routes,
            transport_succeeded=transport_succeeded,
            attempted_at=attempted_at,
        )

    def list_notification_routes(self) -> tuple[DeadManNotificationRouteSnapshot, ...]:
        return _list_notification_routes(self._path)

    def list_route_health_events(self) -> tuple[DeadManRouteHealthEvent, ...]:
        return _list_route_health_events(self._path)

    def load_pending_route_health_alerts(
        self,
        *,
        limit: int,
        now: datetime,
    ) -> tuple[DeadManRouteHealthEvent, ...]:
        return _load_pending_route_health_alerts(self._path, limit=limit, now=now)

    def record_route_health_alert_attempt(
        self,
        event_id: str,
        *,
        acknowledged: bool,
        attempted_at: datetime,
    ) -> bool:
        return _record_route_health_alert_attempt(
            self._path,
            event_id,
            acknowledged=acknowledged,
            attempted_at=attempted_at,
        )

    def pending_route_health_alert_count(self) -> int:
        return _route_health_alert_count(self._path, pending_only=True)

    def degraded_notification_route_count(self) -> int:
        return _degraded_notification_route_count(self._path)

    def suspect_notification_route_count(self) -> int:
        return _suspect_notification_route_count(self._path)

    def list_events(self, runtime_id: str | None = None) -> tuple[DeadManEvent, ...]:
        query = "SELECT payload FROM dead_man_notification_outbox"
        parameters: tuple[object, ...] = ()
        if runtime_id is not None:
            query += " WHERE runtime_id = ?"
            parameters = (runtime_id,)
        query += " ORDER BY row_id"
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return tuple(DeadManEvent.model_validate_json(row["payload"]) for row in rows)

    def export_evidence(
        self,
        runtime_id: str,
        *,
        generated_at: datetime,
        max_outages: int,
    ) -> DeadManEvidenceBundle:
        return _export_evidence(
            self._path,
            runtime_id,
            generated_at=generated_at,
            max_outages=max_outages,
        )

    def pending_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM dead_man_notification_outbox WHERE delivered = 0"
            ).fetchone()
        return int(row["count"])

    def active_monitor_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM dead_man_monitors").fetchone()
        return int(row["count"])

    def ping(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1").fetchone()

    def _open_if_expired(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        *,
        now: datetime,
    ) -> DeadManEvent | None:
        if row["outage_id"] is not None:
            return None
        expires_at = _monitor_expiry(row)
        if now < expires_at:
            return None
        outage_id = self._outage_id_factory()
        event = DeadManEvent(
            event_id=self._event_id_factory(),
            outage_id=outage_id,
            event_type=DeadManEventType.OUTAGE_OPENED,
            runtime_id=str(row["runtime_id"]),
            reason=_outage_reason(row),
            occurred_at=expires_at,
            detected_at=now,
        )
        connection.execute(
            """
            UPDATE dead_man_monitors
            SET outage_id = ?, outage_opened_at = ?, outage_reason = ?, updated_at = ?
            WHERE runtime_id = ? AND outage_id IS NULL
            """,
            (
                outage_id,
                expires_at.isoformat(),
                event.reason.value,
                now.isoformat(),
                row["runtime_id"],
            ),
        )
        self._insert_event(connection, event)
        return event

    def _resolve_if_open(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
        *,
        received_at: datetime,
    ) -> bool:
        outage_id = row["outage_id"]
        if outage_id is None:
            return False
        event = DeadManEvent(
            event_id=self._event_id_factory(),
            outage_id=str(outage_id),
            event_type=DeadManEventType.OUTAGE_RESOLVED,
            runtime_id=str(row["runtime_id"]),
            reason=DeadManOutageReason(str(row["outage_reason"])),
            occurred_at=received_at,
            detected_at=received_at,
        )
        self._insert_event(connection, event)
        return True

    def _insert_event(self, connection: sqlite3.Connection, event: DeadManEvent) -> None:
        policy = _notification_policy_row(connection)
        connection.execute(
            """
            INSERT INTO dead_man_notification_outbox (
                event_id, outage_id, event_type, runtime_id, payload,
                configured_routes, minimum_acknowledgements
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.outage_id,
                event.event_type.value,
                event.runtime_id,
                event.model_dump_json(),
                int(policy["configured_routes"]),
                int(policy["minimum_acknowledgements"]),
            ),
        )

    @staticmethod
    def _require_matching_ttl(row: sqlite3.Row, pulse: RuntimeLivenessPulse) -> None:
        if int(row["expires_after_seconds"]) != pulse.expires_after_seconds:
            raise DeadManMonitorConflictError("pulse TTL does not match armed monitor")

    @staticmethod
    def _monitor_row(
        connection: sqlite3.Connection,
        runtime_id: str,
    ) -> sqlite3.Row | None:
        return cast(
            sqlite3.Row | None,
            connection.execute(
                "SELECT * FROM dead_man_monitors WHERE runtime_id = ?",
                (runtime_id,),
            ).fetchone(),
        )

    def _required_monitor_row(
        self,
        connection: sqlite3.Connection,
        runtime_id: str,
    ) -> sqlite3.Row:
        row = self._monitor_row(connection, runtime_id)
        if row is None:
            raise DeadManMonitorNotArmedError("runtime monitor is not armed")
        return row

    def _connect(self) -> sqlite3.Connection:
        return _connect_path(self._path)


def _init_schema(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if schema_version not in {0, 1, 2, 3, 4, DEAD_MAN_RECEIVER_SCHEMA_VERSION}:
            raise DeadManReceiverSchemaError("dead-man receiver schema version is not supported")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dead_man_monitors (
                runtime_id TEXT PRIMARY KEY,
                expires_after_seconds INTEGER NOT NULL CHECK (expires_after_seconds > 0),
                armed_at TEXT NOT NULL,
                boot_id TEXT,
                sequence INTEGER CHECK (sequence IS NULL OR sequence > 0),
                sent_at TEXT,
                last_received_at TEXT,
                outage_id TEXT UNIQUE,
                outage_opened_at TEXT,
                updated_at TEXT NOT NULL,
                last_pulse_received_at TEXT,
                alert_delivery_status TEXT NOT NULL DEFAULT 'disabled',
                outage_reason TEXT
            )
            """
        )
        if schema_version == 1:
            _migrate_schema_v1(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dead_man_notification_outbox (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                outage_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                runtime_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                delivered INTEGER NOT NULL DEFAULT 0 CHECK (delivered IN (0, 1)),
                delivery_attempts INTEGER NOT NULL DEFAULT 0 CHECK (delivery_attempts >= 0),
                next_attempt_at TEXT,
                configured_routes INTEGER NOT NULL DEFAULT 1
                    CHECK (configured_routes BETWEEN 1 AND 2),
                minimum_acknowledgements INTEGER NOT NULL DEFAULT 1
                    CHECK (minimum_acknowledgements BETWEEN 1 AND configured_routes),
                acknowledged_route_mask INTEGER
                    CHECK (acknowledged_route_mask BETWEEN 0 AND 3),
                last_attempt_at TEXT,
                UNIQUE (outage_id, event_type)
            )
            """
        )
        if schema_version in {1, 2, 3}:
            _migrate_notification_schema(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dead_man_notification_policy (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                configured_routes INTEGER NOT NULL
                    CHECK (configured_routes BETWEEN 1 AND 2),
                minimum_acknowledgements INTEGER NOT NULL
                    CHECK (minimum_acknowledgements BETWEEN 1 AND configured_routes),
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO dead_man_notification_policy (
                singleton, configured_routes, minimum_acknowledgements, updated_at
            ) VALUES (1, 1, 1, '1970-01-01T00:00:00+00:00')
            """
        )
        _init_route_health_schema(connection)
        if schema_version in {1, 2, 3, 4}:
            _migrate_notification_probe_schema(connection)
        _init_notification_probe_schema(connection)
        connection.execute(f"PRAGMA user_version = {DEAD_MAN_RECEIVER_SCHEMA_VERSION}")
    path.chmod(0o600)


def _init_route_health_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dead_man_notification_routes (
            route_slot INTEGER PRIMARY KEY CHECK (route_slot BETWEEN 1 AND 2),
            status TEXT NOT NULL CHECK (status IN ('unknown', 'healthy', 'degraded')),
            consecutive_failures INTEGER NOT NULL DEFAULT 0 CHECK (consecutive_failures >= 0),
            last_attempt_at TEXT,
            last_acknowledged_at TEXT,
            updated_at TEXT NOT NULL,
            consecutive_probe_failures INTEGER NOT NULL DEFAULT 0
                CHECK (consecutive_probe_failures >= 0),
            last_probe_at TEXT,
            last_probe_acknowledged_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dead_man_route_health_outbox (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            route_slot INTEGER NOT NULL CHECK (route_slot BETWEEN 1 AND 2),
            event_type TEXT NOT NULL CHECK (
                event_type IN ('notification_route_degraded', 'notification_route_recovered')
            ),
            triggering_event_id TEXT NOT NULL,
            runtime_id TEXT NOT NULL,
            payload TEXT NOT NULL,
            delivered INTEGER NOT NULL DEFAULT 0 CHECK (delivered IN (0, 1)),
            delivery_attempts INTEGER NOT NULL DEFAULT 0 CHECK (delivery_attempts >= 0),
            next_attempt_at TEXT,
            observation_source TEXT NOT NULL DEFAULT 'outage_delivery' CHECK (
                observation_source IN ('outage_delivery', 'silent_probe')
            ),
            UNIQUE (route_slot, event_type, triggering_event_id)
        )
        """
    )
    configured_routes = int(
        connection.execute(
            "SELECT configured_routes FROM dead_man_notification_policy WHERE singleton = 1"
        ).fetchone()[0]
    )
    for route_slot in range(1, configured_routes + 1):
        connection.execute(
            """
            INSERT OR IGNORE INTO dead_man_notification_routes (
                route_slot, status, updated_at
            ) VALUES (?, 'unknown', '1970-01-01T00:00:00+00:00')
            """,
            (route_slot,),
        )


def _init_notification_probe_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dead_man_notification_probe (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            contract TEXT NOT NULL CHECK (contract IN ('disabled', 'silent-route-probe-v1')),
            interval_seconds INTEGER NOT NULL CHECK (interval_seconds >= 60),
            failure_threshold INTEGER NOT NULL CHECK (failure_threshold BETWEEN 2 AND 10),
            max_age_seconds INTEGER NOT NULL CHECK (max_age_seconds >= interval_seconds * 2),
            probe_id TEXT,
            payload TEXT,
            scheduled_at TEXT,
            next_probe_at TEXT,
            last_completed_at TEXT,
            last_acknowledged_route_mask INTEGER
                CHECK (last_acknowledged_route_mask BETWEEN 0 AND 3),
            updated_at TEXT NOT NULL,
            CHECK ((probe_id IS NULL) = (payload IS NULL)),
            CHECK ((probe_id IS NULL) = (scheduled_at IS NULL)),
            CHECK ((last_completed_at IS NULL) = (last_acknowledged_route_mask IS NULL))
        )
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO dead_man_notification_probe (
            singleton, contract, interval_seconds, failure_threshold,
            max_age_seconds, updated_at
        ) VALUES (1, 'disabled', 900, 2, 1800, '1970-01-01T00:00:00+00:00')
        """
    )


def _configure_notification_policy(
    path: Path,
    *,
    configured_routes: int,
    minimum_acknowledgements: int,
    configured_at: datetime,
) -> DeadManNotificationPolicySnapshot:
    _require_aware(configured_at)
    _validate_notification_policy(configured_routes, minimum_acknowledgements)
    with _connect_path(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = _notification_policy_row(connection)
        unchanged = (
            int(row["configured_routes"]) == configured_routes
            and int(row["minimum_acknowledgements"]) == minimum_acknowledgements
        )
        if unchanged:
            return _notification_policy_snapshot(row)
        pending = sum(
            int(connection.execute(query).fetchone()[0])
            for query in (
                "SELECT COUNT(*) FROM dead_man_notification_outbox WHERE delivered = 0",
                "SELECT COUNT(*) FROM dead_man_route_health_outbox WHERE delivered = 0",
                "SELECT COUNT(*) FROM dead_man_notification_probe WHERE probe_id IS NOT NULL",
            )
        )
        if pending > 0:
            raise DeadManNotificationPolicyConflictError(
                "notification policy change refused while delivery is pending"
            )
        connection.execute(
            """
            UPDATE dead_man_notification_policy
            SET configured_routes = ?, minimum_acknowledgements = ?, updated_at = ?
            WHERE singleton = 1
            """,
            (
                configured_routes,
                minimum_acknowledgements,
                configured_at.isoformat(),
            ),
        )
        connection.execute(
            "DELETE FROM dead_man_notification_routes WHERE route_slot > ?",
            (configured_routes,),
        )
        for route_slot in range(1, configured_routes + 1):
            connection.execute(
                """
                INSERT OR IGNORE INTO dead_man_notification_routes (
                    route_slot, status, updated_at
                ) VALUES (?, 'unknown', ?)
                """,
                (route_slot, configured_at.isoformat()),
            )
        return _notification_policy_snapshot(_notification_policy_row(connection))


def _configure_notification_probe(
    path: Path,
    *,
    contract: DeadManNotificationProbeContract,
    interval_seconds: int,
    failure_threshold: int,
    max_age_seconds: int,
    configured_at: datetime,
) -> DeadManNotificationProbeSnapshot:
    _require_aware(configured_at)
    if interval_seconds < 60:
        raise ValueError("notification probe interval must be at least 60 seconds")
    if not 2 <= failure_threshold <= 10:
        raise ValueError("notification probe failure threshold must be between 2 and 10")
    if max_age_seconds < interval_seconds * 2:
        raise ValueError("notification probe max age must cover two intervals")
    with _connect_path(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = _notification_probe_row(connection)
        unchanged = (
            str(row["contract"]) == contract.value
            and int(row["interval_seconds"]) == interval_seconds
            and int(row["failure_threshold"]) == failure_threshold
            and int(row["max_age_seconds"]) == max_age_seconds
        )
        if unchanged:
            return _notification_probe_snapshot(row)
        if row["probe_id"] is not None:
            raise DeadManNotificationPolicyConflictError(
                "notification probe configuration change refused while probe is pending"
            )
        pending_delivery = sum(
            int(connection.execute(query).fetchone()[0])
            for query in (
                "SELECT COUNT(*) FROM dead_man_notification_outbox WHERE delivered = 0",
                "SELECT COUNT(*) FROM dead_man_route_health_outbox WHERE delivered = 0",
            )
        )
        if pending_delivery > 0:
            raise DeadManNotificationPolicyConflictError(
                "notification probe configuration change refused while delivery is pending"
            )
        if contract is DeadManNotificationProbeContract.SILENT_ROUTE_PROBE_V1:
            policy = _notification_policy_row(connection)
            if int(policy["configured_routes"]) != 2:
                raise ValueError("silent notification probe requires two configured routes")
        next_probe_at = (
            configured_at.isoformat()
            if contract is DeadManNotificationProbeContract.SILENT_ROUTE_PROBE_V1
            else None
        )
        connection.execute(
            """
            UPDATE dead_man_notification_probe
            SET contract = ?, interval_seconds = ?, failure_threshold = ?,
                max_age_seconds = ?, probe_id = NULL, payload = NULL,
                scheduled_at = NULL, next_probe_at = ?, updated_at = ?
            WHERE singleton = 1
            """,
            (
                contract.value,
                interval_seconds,
                failure_threshold,
                max_age_seconds,
                next_probe_at,
                configured_at.isoformat(),
            ),
        )
        return _notification_probe_snapshot(_notification_probe_row(connection))


def _ensure_notification_probe_due(
    path: Path,
    *,
    now: datetime,
) -> DeadManNotificationProbeEvent | None:
    _require_aware(now)
    with _connect_path(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = _notification_probe_row(connection)
        if str(row["contract"]) == DeadManNotificationProbeContract.DISABLED.value:
            return None
        if row["probe_id"] is not None:
            return DeadManNotificationProbeEvent.model_validate_json(row["payload"])
        next_probe_at = _parse_time(str(row["next_probe_at"]))
        if now < next_probe_at:
            return None
        identity = f"{next_probe_at.isoformat()}:silent-route-probe-v1".encode()
        event = DeadManNotificationProbeEvent(
            event_id=f"rp-{hashlib.sha256(identity).hexdigest()[:32]}",
            scheduled_at=next_probe_at,
        )
        connection.execute(
            """
            UPDATE dead_man_notification_probe
            SET probe_id = ?, payload = ?, scheduled_at = ?, updated_at = ?
            WHERE singleton = 1 AND probe_id IS NULL
            """,
            (
                event.event_id,
                event.model_dump_json(),
                event.scheduled_at.isoformat(),
                now.isoformat(),
            ),
        )
        return event


def _record_notification_probe_attempt(
    path: Path,
    event_id: str,
    *,
    acknowledged_routes: tuple[bool, ...] | None,
    transport_succeeded: bool,
    attempted_at: datetime,
) -> None:
    _require_aware(attempted_at)
    with _connect_path(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = _notification_probe_row(connection)
        if row["probe_id"] != event_id:
            raise ValueError(f"unknown pending notification probe: {event_id}")
        policy = _notification_policy_row(connection)
        configured_routes = int(policy["configured_routes"])
        outcomes = _normalized_route_outcomes(
            configured_routes,
            acknowledged_routes=acknowledged_routes,
            transport_succeeded=transport_succeeded,
        )
        threshold = int(row["failure_threshold"])
        for route_slot, acknowledged in enumerate(outcomes, start=1):
            _record_probe_route_outcome(
                connection,
                route_slot=route_slot,
                acknowledged=acknowledged,
                failure_threshold=threshold,
                event_id=event_id,
                acknowledged_routes=outcomes,
                attempted_at=attempted_at,
            )
        mask = sum(1 << index for index, acknowledged in enumerate(outcomes) if acknowledged)
        next_probe_at = attempted_at + timedelta(seconds=int(row["interval_seconds"]))
        connection.execute(
            """
            UPDATE dead_man_notification_probe
            SET probe_id = NULL, payload = NULL, scheduled_at = NULL,
                next_probe_at = ?, last_completed_at = ?,
                last_acknowledged_route_mask = ?, updated_at = ?
            WHERE singleton = 1 AND probe_id = ?
            """,
            (
                next_probe_at.isoformat(),
                attempted_at.isoformat(),
                mask,
                attempted_at.isoformat(),
                event_id,
            ),
        )


def _record_notification_attempt(
    path: Path,
    event_id: str,
    *,
    acknowledged_routes: tuple[bool, ...] | None,
    transport_succeeded: bool,
    attempted_at: datetime,
) -> bool:
    _require_aware(attempted_at)
    with _connect_path(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT event_id, runtime_id, configured_routes, minimum_acknowledgements,
                delivery_attempts
            FROM dead_man_notification_outbox
            WHERE event_id = ? AND delivered = 0
            """,
            (event_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"unknown pending dead-man event: {event_id}")
        configured_routes = int(row["configured_routes"])
        outcomes = _normalized_route_outcomes(
            configured_routes,
            acknowledged_routes=acknowledged_routes,
            transport_succeeded=transport_succeeded,
        )
        for route_slot, acknowledged in enumerate(outcomes, start=1):
            _record_route_outcome(
                connection,
                route_slot=route_slot,
                acknowledged=acknowledged,
                emit_transition=configured_routes > 1,
                event_id=event_id,
                runtime_id=str(row["runtime_id"]),
                attempted_at=attempted_at,
            )
        mask = sum(1 << index for index, acknowledged in enumerate(outcomes) if acknowledged)
        if sum(outcomes) >= int(row["minimum_acknowledgements"]):
            connection.execute(
                """
                UPDATE dead_man_notification_outbox
                SET delivered = 1, next_attempt_at = NULL,
                    acknowledged_route_mask = ?, last_attempt_at = ?
                WHERE event_id = ? AND delivered = 0
                """,
                (mask, attempted_at.isoformat(), event_id),
            )
            return True
        attempts = int(row["delivery_attempts"]) + 1
        retry_at = attempted_at + _retry_delay(attempts)
        connection.execute(
            """
            UPDATE dead_man_notification_outbox
            SET delivery_attempts = ?, next_attempt_at = ?,
                acknowledged_route_mask = ?, last_attempt_at = ?
            WHERE event_id = ? AND delivered = 0
            """,
            (attempts, retry_at.isoformat(), mask, attempted_at.isoformat(), event_id),
        )
        return False


def _normalized_route_outcomes(
    configured_routes: int,
    *,
    acknowledged_routes: tuple[bool, ...] | None,
    transport_succeeded: bool,
) -> tuple[bool, ...]:
    if acknowledged_routes is not None:
        if len(acknowledged_routes) != configured_routes:
            raise ValueError("notification route outcomes do not match frozen policy")
        return acknowledged_routes
    if transport_succeeded:
        if configured_routes != 1:
            raise ValueError("multi-route sink must report per-route acknowledgements")
        return (True,)
    return (False,) * configured_routes


def _record_route_outcome(
    connection: sqlite3.Connection,
    *,
    route_slot: int,
    acknowledged: bool,
    emit_transition: bool,
    event_id: str,
    runtime_id: str,
    attempted_at: datetime,
) -> None:
    row = connection.execute(
        "SELECT * FROM dead_man_notification_routes WHERE route_slot = ?",
        (route_slot,),
    ).fetchone()
    if row is None:
        raise DeadManReceiverSchemaError("notification route state is missing")
    previous = DeadManNotificationRouteStatus(str(row["status"]))
    current = (
        DeadManNotificationRouteStatus.HEALTHY
        if acknowledged
        else DeadManNotificationRouteStatus.DEGRADED
    )
    failures = 0 if acknowledged else int(row["consecutive_failures"]) + 1
    acknowledged_at = attempted_at.isoformat() if acknowledged else row["last_acknowledged_at"]
    connection.execute(
        """
        UPDATE dead_man_notification_routes
        SET status = ?, consecutive_failures = ?, consecutive_probe_failures = 0,
            last_attempt_at = ?,
            last_acknowledged_at = ?, updated_at = ?
        WHERE route_slot = ?
        """,
        (
            current.value,
            failures,
            attempted_at.isoformat(),
            acknowledged_at,
            attempted_at.isoformat(),
            route_slot,
        ),
    )
    event_type = _route_transition(previous, current) if emit_transition else None
    if event_type is not None:
        _insert_route_health_alert(
            connection,
            route_slot=route_slot,
            event_type=event_type,
            triggering_event_id=event_id,
            runtime_id=runtime_id,
            observation_source=DeadManRouteObservationSource.OUTAGE_DELIVERY,
            acknowledged_routes=None,
            occurred_at=attempted_at,
        )


def _record_probe_route_outcome(
    connection: sqlite3.Connection,
    *,
    route_slot: int,
    acknowledged: bool,
    failure_threshold: int,
    event_id: str,
    acknowledged_routes: tuple[bool, ...],
    attempted_at: datetime,
) -> None:
    row = connection.execute(
        "SELECT * FROM dead_man_notification_routes WHERE route_slot = ?",
        (route_slot,),
    ).fetchone()
    if row is None:
        raise DeadManReceiverSchemaError("notification route state is missing")
    previous = DeadManNotificationRouteStatus(str(row["status"]))
    probe_failures = 0 if acknowledged else int(row["consecutive_probe_failures"]) + 1
    confirmed_failure = not acknowledged and probe_failures >= failure_threshold
    current = (
        DeadManNotificationRouteStatus.HEALTHY
        if acknowledged
        else (
            DeadManNotificationRouteStatus.DEGRADED
            if confirmed_failure or previous is DeadManNotificationRouteStatus.DEGRADED
            else previous
        )
    )
    failures = (
        0
        if acknowledged
        else (
            int(row["consecutive_failures"]) + 1
            if current is DeadManNotificationRouteStatus.DEGRADED
            else 0
        )
    )
    acknowledged_at = attempted_at.isoformat() if acknowledged else row["last_acknowledged_at"]
    probe_acknowledged_at = (
        attempted_at.isoformat() if acknowledged else row["last_probe_acknowledged_at"]
    )
    connection.execute(
        """
        UPDATE dead_man_notification_routes
        SET status = ?, consecutive_failures = ?, consecutive_probe_failures = ?,
            last_attempt_at = ?, last_acknowledged_at = ?, last_probe_at = ?,
            last_probe_acknowledged_at = ?, updated_at = ?
        WHERE route_slot = ?
        """,
        (
            current.value,
            failures,
            probe_failures,
            attempted_at.isoformat(),
            acknowledged_at,
            attempted_at.isoformat(),
            probe_acknowledged_at,
            attempted_at.isoformat(),
            route_slot,
        ),
    )
    event_type = _route_transition(previous, current)
    if event_type is not None:
        _insert_route_health_alert(
            connection,
            route_slot=route_slot,
            event_type=event_type,
            triggering_event_id=event_id,
            runtime_id="receiver-notification-routes",
            observation_source=DeadManRouteObservationSource.SILENT_PROBE,
            acknowledged_routes=acknowledged_routes,
            occurred_at=attempted_at,
        )


def _route_transition(
    previous: DeadManNotificationRouteStatus,
    current: DeadManNotificationRouteStatus,
) -> DeadManRouteHealthEventType | None:
    if current is DeadManNotificationRouteStatus.DEGRADED and previous is not current:
        return DeadManRouteHealthEventType.ROUTE_DEGRADED
    if (
        current is DeadManNotificationRouteStatus.HEALTHY
        and previous is DeadManNotificationRouteStatus.DEGRADED
    ):
        return DeadManRouteHealthEventType.ROUTE_RECOVERED
    return None


def _insert_route_health_alert(
    connection: sqlite3.Connection,
    *,
    route_slot: int,
    event_type: DeadManRouteHealthEventType,
    triggering_event_id: str,
    runtime_id: str,
    observation_source: DeadManRouteObservationSource,
    acknowledged_routes: tuple[bool, ...] | None,
    occurred_at: datetime,
) -> None:
    identity = f"{route_slot}:{event_type.value}:{triggering_event_id}".encode()
    event = DeadManRouteHealthEvent(
        event_id=f"rh-{hashlib.sha256(identity).hexdigest()[:32]}",
        event_type=event_type,
        route_slot=route_slot,
        triggering_event_id=triggering_event_id,
        runtime_id=runtime_id,
        observation_source=observation_source,
        acknowledged_routes=acknowledged_routes,
        occurred_at=occurred_at,
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO dead_man_route_health_outbox (
            event_id, route_slot, event_type, triggering_event_id, runtime_id,
            observation_source, payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event.event_id,
            event.route_slot,
            event.event_type.value,
            event.triggering_event_id,
            event.runtime_id,
            event.observation_source.value,
            event.model_dump_json(),
        ),
    )


def _list_notification_routes(path: Path) -> tuple[DeadManNotificationRouteSnapshot, ...]:
    with _connect_path(path) as connection:
        rows = connection.execute(
            "SELECT * FROM dead_man_notification_routes ORDER BY route_slot"
        ).fetchall()
    return tuple(_notification_route_snapshot(row) for row in rows)


def _notification_route_snapshot(row: sqlite3.Row) -> DeadManNotificationRouteSnapshot:
    return DeadManNotificationRouteSnapshot(
        route_slot=int(row["route_slot"]),
        status=DeadManNotificationRouteStatus(str(row["status"])),
        consecutive_failures=int(row["consecutive_failures"]),
        consecutive_probe_failures=int(row["consecutive_probe_failures"]),
        last_attempt_at=_optional_time(row["last_attempt_at"]),
        last_acknowledged_at=_optional_time(row["last_acknowledged_at"]),
        last_probe_at=_optional_time(row["last_probe_at"]),
        last_probe_acknowledged_at=_optional_time(row["last_probe_acknowledged_at"]),
        updated_at=_parse_time(row["updated_at"]),
    )


def _list_route_health_events(path: Path) -> tuple[DeadManRouteHealthEvent, ...]:
    with _connect_path(path) as connection:
        rows = connection.execute(
            "SELECT payload FROM dead_man_route_health_outbox ORDER BY row_id"
        ).fetchall()
    return tuple(DeadManRouteHealthEvent.model_validate_json(row["payload"]) for row in rows)


def _load_pending_route_health_alerts(
    path: Path,
    *,
    limit: int,
    now: datetime,
) -> tuple[DeadManRouteHealthEvent, ...]:
    if limit <= 0:
        raise ValueError("route health notification batch limit must be positive")
    _require_aware(now)
    with _connect_path(path) as connection:
        rows = connection.execute(
            """
            SELECT payload, next_attempt_at
            FROM dead_man_route_health_outbox
            WHERE delivered = 0
            ORDER BY row_id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    events: list[DeadManRouteHealthEvent] = []
    for row in rows:
        if row["next_attempt_at"] is not None and _parse_time(row["next_attempt_at"]) > now:
            break
        events.append(DeadManRouteHealthEvent.model_validate_json(row["payload"]))
    return tuple(events)


def _record_route_health_alert_attempt(
    path: Path,
    event_id: str,
    *,
    acknowledged: bool,
    attempted_at: datetime,
) -> bool:
    _require_aware(attempted_at)
    with _connect_path(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT delivery_attempts FROM dead_man_route_health_outbox
            WHERE event_id = ? AND delivered = 0
            """,
            (event_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"unknown pending route health event: {event_id}")
        if acknowledged:
            connection.execute(
                """
                UPDATE dead_man_route_health_outbox
                SET delivered = 1, next_attempt_at = NULL
                WHERE event_id = ? AND delivered = 0
                """,
                (event_id,),
            )
            return True
        attempts = int(row["delivery_attempts"]) + 1
        retry_at = attempted_at + _retry_delay(attempts)
        connection.execute(
            """
            UPDATE dead_man_route_health_outbox
            SET delivery_attempts = ?, next_attempt_at = ?
            WHERE event_id = ? AND delivered = 0
            """,
            (attempts, retry_at.isoformat(), event_id),
        )
        return False


def _route_health_alert_count(path: Path, *, pending_only: bool) -> int:
    query = "SELECT COUNT(*) FROM dead_man_route_health_outbox"
    if pending_only:
        query += " WHERE delivered = 0"
    with _connect_path(path) as connection:
        return int(connection.execute(query).fetchone()[0])


def _degraded_notification_route_count(path: Path) -> int:
    with _connect_path(path) as connection:
        return int(
            connection.execute(
                "SELECT COUNT(*) FROM dead_man_notification_routes WHERE status = 'degraded'"
            ).fetchone()[0]
        )


def _suspect_notification_route_count(path: Path) -> int:
    with _connect_path(path) as connection:
        return int(
            connection.execute(
                """
                SELECT COUNT(*) FROM dead_man_notification_routes
                WHERE status != 'degraded' AND consecutive_probe_failures > 0
                """
            ).fetchone()[0]
        )


def _export_evidence(
    path: Path,
    runtime_id: str,
    *,
    generated_at: datetime,
    max_outages: int,
) -> DeadManEvidenceBundle:
    _require_aware(generated_at)
    if not 1 <= max_outages <= 100:
        raise ValueError("dead-man evidence outage limit must be between 1 and 100")
    with _connect_path(path) as connection:
        monitor_row = connection.execute(
            "SELECT * FROM dead_man_monitors WHERE runtime_id = ?",
            (runtime_id,),
        ).fetchone()
        notification_policy = _notification_policy_snapshot(_notification_policy_row(connection))
        notification_probe = _notification_probe_snapshot(_notification_probe_row(connection))
        route_rows = connection.execute(
            "SELECT * FROM dead_man_notification_routes ORDER BY route_slot"
        ).fetchall()
        rows = connection.execute(
            """
            WITH recent_outages AS (
                SELECT outage_id, MIN(row_id) AS first_row
                FROM dead_man_notification_outbox
                WHERE runtime_id = ?
                GROUP BY outage_id
                ORDER BY first_row DESC
                LIMIT ?
            )
            SELECT payload, delivered, delivery_attempts, next_attempt_at,
                configured_routes, minimum_acknowledgements,
                acknowledged_route_mask, last_attempt_at
            FROM dead_man_notification_outbox AS event
            JOIN recent_outages USING (outage_id)
            WHERE event.runtime_id = ?
            ORDER BY event.row_id
            """,
            (runtime_id, max_outages, runtime_id),
        ).fetchall()
        alert_rows = connection.execute(
            """
            SELECT payload, delivered, delivery_attempts, next_attempt_at
            FROM dead_man_route_health_outbox
            WHERE runtime_id = ? OR observation_source = 'silent_probe'
            ORDER BY row_id
            """,
            (runtime_id,),
        ).fetchall()
    if monitor_row is None and not rows:
        raise DeadManMonitorNotArmedError("runtime has no monitor or outage evidence")
    grouped: dict[str, list[DeadManEvidenceEvent]] = {}
    selected_event_ids: set[str] = set()
    for row in rows:
        event = DeadManEvent.model_validate_json(row["payload"])
        selected_event_ids.add(event.event_id)
        evidence = _evidence_event(event, row)
        grouped.setdefault(event.outage_id, []).append(evidence)
    outages = tuple(_outage_evidence(outage_id, events) for outage_id, events in grouped.items())
    route_alerts = tuple(
        route_evidence
        for row in alert_rows
        if (
            (route_evidence := _route_health_evidence(row)).observation_source
            is DeadManRouteObservationSource.SILENT_PROBE
            or route_evidence.triggering_event_id in selected_event_ids
        )
    )
    return DeadManEvidenceBundle(
        runtime_id=runtime_id,
        generated_at=generated_at,
        notification_policy=notification_policy,
        notification_probe=notification_probe,
        notification_probe_fresh=notification_probe.is_fresh(at=generated_at),
        notification_routes=tuple(_notification_route_snapshot(row) for row in route_rows),
        monitor=_monitor_snapshot(monitor_row) if monitor_row is not None else None,
        outages=outages,
        route_health_alerts=route_alerts,
    )


def _evidence_event(event: DeadManEvent, row: sqlite3.Row) -> DeadManEvidenceEvent:
    delivered = bool(row["delivered"])
    configured_routes = int(row["configured_routes"])
    mask = row["acknowledged_route_mask"]
    return DeadManEvidenceEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        reason=event.reason,
        occurred_at=event.occurred_at,
        detected_at=event.detected_at,
        delivered=delivered,
        delivery_attempts=int(row["delivery_attempts"]),
        configured_routes=configured_routes,
        minimum_acknowledgements=int(row["minimum_acknowledgements"]),
        acknowledged_routes=(
            None if mask is None else _route_outcomes_from_mask(int(mask), configured_routes)
        ),
        last_attempt_at=_optional_time(row["last_attempt_at"]),
        next_attempt_at=(
            None
            if delivered or row["next_attempt_at"] is None
            else _parse_time(row["next_attempt_at"])
        ),
    )


def _route_health_evidence(row: sqlite3.Row) -> DeadManRouteHealthEvidence:
    event = DeadManRouteHealthEvent.model_validate_json(row["payload"])
    delivered = bool(row["delivered"])
    return DeadManRouteHealthEvidence(
        **event.model_dump(),
        delivered=delivered,
        delivery_attempts=int(row["delivery_attempts"]),
        next_attempt_at=(
            None
            if delivered or row["next_attempt_at"] is None
            else _parse_time(row["next_attempt_at"])
        ),
    )


def _route_outcomes_from_mask(mask: int, configured_routes: int) -> tuple[bool, ...]:
    if not 0 <= mask < 1 << configured_routes:
        raise ValueError("notification route acknowledgement mask is invalid")
    return tuple(bool(mask & (1 << index)) for index in range(configured_routes))


def _connect_path(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _migrate_schema_v1(connection: sqlite3.Connection) -> None:
    connection.execute("ALTER TABLE dead_man_monitors ADD COLUMN last_pulse_received_at TEXT")
    connection.execute(
        "ALTER TABLE dead_man_monitors ADD COLUMN alert_delivery_status TEXT "
        "NOT NULL DEFAULT 'disabled'"
    )
    connection.execute("ALTER TABLE dead_man_monitors ADD COLUMN outage_reason TEXT")
    connection.execute("UPDATE dead_man_monitors SET last_pulse_received_at = last_received_at")
    connection.execute(
        "UPDATE dead_man_monitors SET outage_reason = 'pulse_expired' WHERE outage_id IS NOT NULL"
    )


def _migrate_notification_schema(connection: sqlite3.Connection) -> None:
    columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(dead_man_notification_outbox)")
    }
    if "configured_routes" not in columns:
        connection.execute(
            "ALTER TABLE dead_man_notification_outbox ADD COLUMN configured_routes "
            "INTEGER NOT NULL DEFAULT 1 CHECK (configured_routes BETWEEN 1 AND 2)"
        )
    if "minimum_acknowledgements" not in columns:
        connection.execute(
            "ALTER TABLE dead_man_notification_outbox ADD COLUMN minimum_acknowledgements "
            "INTEGER NOT NULL DEFAULT 1 "
            "CHECK (minimum_acknowledgements BETWEEN 1 AND configured_routes)"
        )
    if "acknowledged_route_mask" not in columns:
        connection.execute(
            "ALTER TABLE dead_man_notification_outbox ADD COLUMN acknowledged_route_mask "
            "INTEGER CHECK (acknowledged_route_mask BETWEEN 0 AND 3)"
        )
    if "last_attempt_at" not in columns:
        connection.execute(
            "ALTER TABLE dead_man_notification_outbox ADD COLUMN last_attempt_at TEXT"
        )


def _migrate_notification_probe_schema(connection: sqlite3.Connection) -> None:
    route_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(dead_man_notification_routes)")
    }
    required_route_columns = {
        "consecutive_probe_failures",
        "last_probe_at",
        "last_probe_acknowledged_at",
    }
    if not required_route_columns <= route_columns:
        connection.execute(
            "ALTER TABLE dead_man_notification_routes RENAME TO dead_man_notification_routes_v4"
        )
        connection.execute(
            """
            CREATE TABLE dead_man_notification_routes (
                route_slot INTEGER PRIMARY KEY CHECK (route_slot BETWEEN 1 AND 2),
                status TEXT NOT NULL CHECK (status IN ('unknown', 'healthy', 'degraded')),
                consecutive_failures INTEGER NOT NULL DEFAULT 0
                    CHECK (consecutive_failures >= 0),
                last_attempt_at TEXT,
                last_acknowledged_at TEXT,
                updated_at TEXT NOT NULL,
                consecutive_probe_failures INTEGER NOT NULL DEFAULT 0
                    CHECK (consecutive_probe_failures >= 0),
                last_probe_at TEXT,
                last_probe_acknowledged_at TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO dead_man_notification_routes (
                route_slot, status, consecutive_failures, last_attempt_at,
                last_acknowledged_at, updated_at
            )
            SELECT route_slot, status, consecutive_failures, last_attempt_at,
                last_acknowledged_at, updated_at
            FROM dead_man_notification_routes_v4
            """
        )
        connection.execute("DROP TABLE dead_man_notification_routes_v4")
    alert_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(dead_man_route_health_outbox)")
    }
    if "observation_source" not in alert_columns:
        connection.execute(
            "ALTER TABLE dead_man_route_health_outbox RENAME TO dead_man_route_health_outbox_v4"
        )
        connection.execute(
            """
            CREATE TABLE dead_man_route_health_outbox (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                route_slot INTEGER NOT NULL CHECK (route_slot BETWEEN 1 AND 2),
                event_type TEXT NOT NULL CHECK (
                    event_type IN ('notification_route_degraded', 'notification_route_recovered')
                ),
                triggering_event_id TEXT NOT NULL,
                runtime_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                delivered INTEGER NOT NULL DEFAULT 0 CHECK (delivered IN (0, 1)),
                delivery_attempts INTEGER NOT NULL DEFAULT 0 CHECK (delivery_attempts >= 0),
                next_attempt_at TEXT,
                observation_source TEXT NOT NULL DEFAULT 'outage_delivery' CHECK (
                    observation_source IN ('outage_delivery', 'silent_probe')
                ),
                UNIQUE (route_slot, event_type, triggering_event_id)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO dead_man_route_health_outbox (
                row_id, event_id, route_slot, event_type, triggering_event_id,
                runtime_id, payload, delivered, delivery_attempts, next_attempt_at,
                observation_source
            )
            SELECT row_id, event_id, route_slot, event_type, triggering_event_id,
                runtime_id, payload, delivered, delivery_attempts, next_attempt_at,
                'outage_delivery'
            FROM dead_man_route_health_outbox_v4
            """
        )
        connection.execute("DROP TABLE dead_man_route_health_outbox_v4")


def _notification_policy_row(connection: sqlite3.Connection) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM dead_man_notification_policy WHERE singleton = 1"
    ).fetchone()
    if row is None:
        raise DeadManReceiverSchemaError("dead-man notification policy is missing")
    return cast(sqlite3.Row, row)


def _notification_policy_snapshot(row: sqlite3.Row) -> DeadManNotificationPolicySnapshot:
    return DeadManNotificationPolicySnapshot(
        configured_routes=int(row["configured_routes"]),
        minimum_acknowledgements=int(row["minimum_acknowledgements"]),
        updated_at=_parse_time(row["updated_at"]),
    )


def _notification_probe_row(connection: sqlite3.Connection) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM dead_man_notification_probe WHERE singleton = 1"
    ).fetchone()
    if row is None:
        raise DeadManReceiverSchemaError("dead-man notification probe policy is missing")
    return cast(sqlite3.Row, row)


def _notification_probe_snapshot(row: sqlite3.Row) -> DeadManNotificationProbeSnapshot:
    pending = (
        DeadManNotificationProbeEvent.model_validate_json(row["payload"])
        if row["payload"] is not None
        else None
    )
    mask = row["last_acknowledged_route_mask"]
    return DeadManNotificationProbeSnapshot(
        contract=DeadManNotificationProbeContract(str(row["contract"])),
        interval_seconds=int(row["interval_seconds"]),
        failure_threshold=int(row["failure_threshold"]),
        max_age_seconds=int(row["max_age_seconds"]),
        pending_probe=pending,
        next_probe_at=_optional_time(row["next_probe_at"]),
        last_completed_at=_optional_time(row["last_completed_at"]),
        last_acknowledged_routes=(
            None if mask is None else _route_outcomes_from_mask(int(mask), 2)
        ),
        updated_at=_parse_time(row["updated_at"]),
    )


def _validate_notification_policy(
    configured_routes: int,
    minimum_acknowledgements: int,
) -> None:
    if not 1 <= configured_routes <= 2:
        raise ValueError("notification route count must be between one and two")
    if not 1 <= minimum_acknowledgements <= configured_routes:
        raise ValueError("notification quorum cannot exceed configured routes")


def _monitor_snapshot(row: sqlite3.Row) -> DeadManMonitorSnapshot:
    last_received = _optional_time(row["last_received_at"])
    return DeadManMonitorSnapshot(
        runtime_id=str(row["runtime_id"]),
        status=_monitor_status(row),
        expires_after_seconds=int(row["expires_after_seconds"]),
        armed_at=_parse_time(row["armed_at"]),
        last_received_at=last_received,
        last_pulse_received_at=_optional_time(row["last_pulse_received_at"]),
        alert_delivery_status=RuntimeAlertDeliverySignal(str(row["alert_delivery_status"])),
        expires_at=_monitor_expiry(row),
        last_sequence=int(row["sequence"]) if row["sequence"] is not None else None,
        outage_id=str(row["outage_id"]) if row["outage_id"] is not None else None,
        outage_reason=(
            DeadManOutageReason(str(row["outage_reason"]))
            if row["outage_reason"] is not None
            else None
        ),
    )


def _outage_evidence(
    outage_id: str,
    events: list[DeadManEvidenceEvent],
) -> DeadManOutageEvidence:
    if not 1 <= len(events) <= 2:
        raise ValueError("dead-man outage must contain one opened and optional resolved event")
    return DeadManOutageEvidence(
        outage_id=outage_id,
        opened=events[0],
        resolved=events[1] if len(events) == 2 else None,
    )


def _monitor_status(row: sqlite3.Row) -> RuntimeLivenessReceiverStatus:
    if row["outage_id"] is not None:
        return RuntimeLivenessReceiverStatus.STALE
    return RuntimeLivenessReceiverStatus.HEALTHY


def _monitor_expiry(row: sqlite3.Row) -> datetime:
    anchor = row["last_received_at"] or row["armed_at"]
    return _parse_time(anchor) + timedelta(seconds=int(row["expires_after_seconds"]))


def _outage_reason(row: sqlite3.Row) -> DeadManOutageReason:
    status = RuntimeAlertDeliverySignal(str(row["alert_delivery_status"]))
    if not status.renews_monitor and row["last_pulse_received_at"] is not None:
        return DeadManOutageReason.ALERT_DELIVERY_UNHEALTHY
    return DeadManOutageReason.PULSE_EXPIRED


def _is_newer_pulse(row: sqlite3.Row, pulse: RuntimeLivenessPulse) -> bool:
    current_boot = row["boot_id"]
    if current_boot is None:
        return True
    if str(current_boot) == pulse.boot_id:
        return pulse.sequence > int(row["sequence"])
    current_sent_at = _parse_time(row["sent_at"])
    return pulse.sent_at >= current_sent_at


def _parse_time(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError("dead-man receiver timestamp must be timezone-aware")
    return parsed


def _optional_time(value: object) -> datetime | None:
    return None if value is None else _parse_time(value)


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None:
        raise ValueError("dead-man receiver timestamp must be timezone-aware")


def _retry_delay(attempts: int) -> timedelta:
    return timedelta(seconds=(60, 300, 900)[min(attempts, 3) - 1])


def _new_id() -> str:
    return str(uuid4())
