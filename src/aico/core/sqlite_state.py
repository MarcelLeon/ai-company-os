"""Shared SQLite state database helpers."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aico.core.authorization_clock import AuthorizationClockObservation

STATE_SCHEMA_VERSION = 13
STATE_TABLES = (
    "task_records",
    "task_snapshots",
    "approval_requests",
    "task_recovery_audit_outbox",
    "runtime_alert_incidents",
    "runtime_alert_outbox",
    "runtime_health_alert_observations",
    "offline_delegations",
    "standing_proposals",
    "authorization_clock_state",
    "morning_delivery_outbox",
    "scheduled_autonomy_intents",
    "scheduled_autonomy_outcome_outbox",
    "scheduled_recovery_backups",
    "scheduled_recovery_drills",
)


@dataclass(frozen=True)
class MorningDeliverySummary:
    delivery_id: str
    status: str
    attempts: int
    duplicate_possible: bool
    content_sha256: str
    autonomy_receipts: int
    scheduled_for: str
    delivered_at: str | None


@dataclass(frozen=True)
class ScheduledAutonomySummary:
    intent_id: str
    status: str
    attempts: int
    duplicate_notification_possible: bool
    disposition: str | None
    proposal_id_sha256: str | None
    task_id_sha256: str | None


@dataclass(frozen=True)
class AutonomyOutcomeDeliverySummary:
    notification_id: str
    intent_id: str
    status: str
    attempts: int
    duplicate_possible: bool
    content_sha256: str
    source_status: str
    outcome_status: str
    delivered_at: str | None


@dataclass(frozen=True)
class RecoveryBackupSummary:
    backup_id: str
    status: str
    attempts: int
    artifact_sha256: str | None
    receipt_sha256: str | None
    verified_at: str | None
    custody_status: str
    custody_checked_at: str | None
    custody_failures: int
    retention_started_at: str | None
    retention_policy_sha256: str | None
    pruned_at: str | None


@dataclass(frozen=True)
class RecoveryDrillSummary:
    drill_id: str
    status: str
    attempts: int
    backup_id: str
    policy_sha256: str
    artifact_sha256: str | None
    receipt_sha256: str | None
    verified_at: str | None
    state_table_count: int | None
    unresolved_asset_count: int | None
    post_restore_evidence_asset_count: int | None


class SQLiteStateDatabase:
    """Small coordination layer for local-first AICO state tables."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_metadata()

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def table_counts(self) -> dict[str, int]:
        with self.connect() as connection:
            existing = _existing_tables(connection)
            return {
                table: _table_count(connection, table)
                for table in STATE_TABLES
                if table in existing
            }

    def schema_version(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM aico_schema WHERE key = 'schema_version'"
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def pending_recovery_audit_count(self) -> int:
        with self.connect() as connection:
            if "task_recovery_audit_outbox" not in _existing_tables(connection):
                return 0
            row = connection.execute(
                "SELECT COUNT(*) FROM task_recovery_audit_outbox WHERE delivered = 0"
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def pending_runtime_alert_count(self) -> int:
        with self.connect() as connection:
            if "runtime_alert_outbox" not in _existing_tables(connection):
                return 0
            row = connection.execute(
                "SELECT COUNT(*) FROM runtime_alert_outbox WHERE delivered = 0"
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def runtime_health_alert_candidate_count(self) -> int:
        with self.connect() as connection:
            if "runtime_health_alert_observations" not in _existing_tables(connection):
                return 0
            row = connection.execute(
                "SELECT COUNT(*) FROM runtime_health_alert_observations"
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def recent_morning_deliveries(self, *, limit: int = 5) -> tuple[MorningDeliverySummary, ...]:
        if limit <= 0:
            raise ValueError("morning delivery summary limit must be positive")
        with self.connect() as connection:
            if "morning_delivery_outbox" not in _existing_tables(connection):
                return ()
            rows = connection.execute(
                """
                SELECT delivery_id, status, attempts, duplicate_possible, payload,
                       scheduled_for, delivered_at
                FROM morning_delivery_outbox
                ORDER BY scheduled_for DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        summaries: list[MorningDeliverySummary] = []
        for row in rows:
            payload = json.loads(str(row[4]))
            summaries.append(
                MorningDeliverySummary(
                    delivery_id=str(row[0]),
                    status=str(row[1]),
                    attempts=int(row[2]),
                    duplicate_possible=bool(row[3]),
                    content_sha256=str(payload["content_sha256"]),
                    autonomy_receipts=len(payload.get("autonomy_receipt_sha256", [])),
                    scheduled_for=str(row[5]),
                    delivered_at=None if row[6] is None else str(row[6]),
                )
            )
        return tuple(summaries)

    def recent_scheduled_autonomy(
        self,
        *,
        limit: int = 5,
    ) -> tuple[ScheduledAutonomySummary, ...]:
        if limit <= 0:
            raise ValueError("scheduled autonomy summary limit must be positive")
        with self.connect() as connection:
            if "scheduled_autonomy_intents" not in _existing_tables(connection):
                return ()
            rows = connection.execute(
                """
                SELECT intent_id, status, payload
                FROM scheduled_autonomy_intents
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        summaries: list[ScheduledAutonomySummary] = []
        for row in rows:
            payload = json.loads(str(row[2]))
            if payload.get("intent_id") != str(row[0]) or payload.get("status") != str(row[1]):
                raise ValueError("scheduled autonomy summary state mismatch")
            receipt = payload.get("receipt")
            summaries.append(
                ScheduledAutonomySummary(
                    intent_id=str(row[0]),
                    status=str(row[1]),
                    attempts=int(payload["attempts"]),
                    duplicate_notification_possible=bool(
                        payload["duplicate_notification_possible"]
                    ),
                    disposition=None if receipt is None else str(receipt["disposition"]),
                    proposal_id_sha256=_identifier_sha256(receipt, "proposal_id"),
                    task_id_sha256=_identifier_sha256(receipt, "task_id"),
                )
            )
        return tuple(summaries)

    def recent_autonomy_outcome_deliveries(
        self,
        *,
        limit: int = 5,
    ) -> tuple[AutonomyOutcomeDeliverySummary, ...]:
        if limit <= 0:
            raise ValueError("autonomy outcome delivery summary limit must be positive")
        with self.connect() as connection:
            if "scheduled_autonomy_outcome_outbox" not in _existing_tables(connection):
                return ()
            rows = connection.execute(
                """
                SELECT notification_id, intent_id, status, payload
                FROM scheduled_autonomy_outcome_outbox
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        summaries: list[AutonomyOutcomeDeliverySummary] = []
        for row in rows:
            payload = json.loads(str(row[3]))
            if (
                payload.get("notification_id") != str(row[0])
                or payload.get("intent_id") != str(row[1])
                or payload.get("status") != str(row[2])
            ):
                raise ValueError("autonomy outcome delivery summary state mismatch")
            envelope = payload["envelope"]
            summaries.append(
                AutonomyOutcomeDeliverySummary(
                    notification_id=str(row[0]),
                    intent_id=str(row[1]),
                    status=str(row[2]),
                    attempts=int(payload["attempts"]),
                    duplicate_possible=bool(payload["duplicate_possible"]),
                    content_sha256=str(envelope["content_sha256"]),
                    source_status=str(envelope["source_status"]),
                    outcome_status=str(envelope["outcome_status"]),
                    delivered_at=(
                        None
                        if payload.get("delivered_at") is None
                        else str(payload["delivered_at"])
                    ),
                )
            )
        return tuple(summaries)

    def recent_recovery_backups(
        self,
        *,
        limit: int = 5,
    ) -> tuple[RecoveryBackupSummary, ...]:
        if limit <= 0:
            raise ValueError("recovery backup summary limit must be positive")
        with self.connect() as connection:
            if "scheduled_recovery_backups" not in _existing_tables(connection):
                return ()
            rows = connection.execute(
                """
                SELECT backup_id, status, payload
                FROM scheduled_recovery_backups
                ORDER BY scheduled_for DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        summaries: list[RecoveryBackupSummary] = []
        for row in rows:
            payload = json.loads(str(row[2]))
            if payload.get("backup_id") != str(row[0]) or payload.get("status") != str(row[1]):
                raise ValueError("scheduled recovery backup summary state mismatch")
            receipt = payload.get("receipt")
            summaries.append(
                RecoveryBackupSummary(
                    backup_id=str(row[0]),
                    status=str(row[1]),
                    attempts=int(payload["attempts"]),
                    artifact_sha256=(None if receipt is None else str(receipt["artifact_sha256"])),
                    receipt_sha256=(
                        None
                        if payload.get("receipt_sha256") is None
                        else str(payload["receipt_sha256"])
                    ),
                    verified_at=(
                        None if payload.get("verified_at") is None else str(payload["verified_at"])
                    ),
                    custody_status=str(payload["custody_status"]),
                    custody_checked_at=(
                        None
                        if payload.get("custody_checked_at") is None
                        else str(payload["custody_checked_at"])
                    ),
                    custody_failures=int(payload["custody_failures"]),
                    retention_started_at=(
                        None
                        if payload.get("retention_started_at") is None
                        else str(payload["retention_started_at"])
                    ),
                    retention_policy_sha256=(
                        None
                        if payload.get("retention_policy_sha256") is None
                        else str(payload["retention_policy_sha256"])
                    ),
                    pruned_at=(
                        None if payload.get("pruned_at") is None else str(payload["pruned_at"])
                    ),
                )
            )
        return tuple(summaries)

    def recent_recovery_drills(
        self,
        *,
        limit: int = 5,
    ) -> tuple[RecoveryDrillSummary, ...]:
        if limit <= 0:
            raise ValueError("recovery drill summary limit must be positive")
        with self.connect() as connection:
            if "scheduled_recovery_drills" not in _existing_tables(connection):
                return ()
            rows = connection.execute(
                """
                SELECT drill_id, status, payload
                FROM scheduled_recovery_drills
                ORDER BY scheduled_for DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        summaries: list[RecoveryDrillSummary] = []
        for row in rows:
            payload = json.loads(str(row[2]))
            if payload.get("drill_id") != str(row[0]) or payload.get("status") != str(row[1]):
                raise ValueError("scheduled recovery drill summary state mismatch")
            receipt = payload.get("receipt")
            summaries.append(
                RecoveryDrillSummary(
                    drill_id=str(row[0]),
                    status=str(row[1]),
                    attempts=int(payload["attempts"]),
                    backup_id=str(payload["backup_id"]),
                    policy_sha256=str(payload["policy_sha256"]),
                    artifact_sha256=(None if receipt is None else str(receipt["artifact_sha256"])),
                    receipt_sha256=(
                        None
                        if payload.get("receipt_sha256") is None
                        else str(payload["receipt_sha256"])
                    ),
                    verified_at=(
                        None if payload.get("verified_at") is None else str(payload["verified_at"])
                    ),
                    state_table_count=(
                        None if receipt is None else int(receipt["state_table_count"])
                    ),
                    unresolved_asset_count=(
                        None if receipt is None else int(receipt["unresolved_asset_count"])
                    ),
                    post_restore_evidence_asset_count=(
                        None
                        if receipt is None
                        else int(receipt["post_restore_evidence_asset_count"])
                    ),
                )
            )
        return tuple(summaries)

    def observe_authorization_time(
        self,
        now: datetime,
        *,
        minimum_expected_at: datetime,
        rollback_tolerance_seconds: int,
    ) -> AuthorizationClockObservation:
        if now.tzinfo is None or minimum_expected_at.tzinfo is None:
            raise ValueError("authorization clock timestamps must be timezone-aware")
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT high_water_at FROM authorization_clock_state WHERE singleton = 1"
            ).fetchone()
            persisted = _parse_authorization_time(row[0]) if row is not None else now
            high_water = max(persisted, now, minimum_expected_at)
            connection.execute(
                """
                INSERT INTO authorization_clock_state (singleton, high_water_at)
                VALUES (1, ?)
                ON CONFLICT(singleton) DO UPDATE SET high_water_at = excluded.high_water_at
                """,
                (high_water.astimezone(UTC).isoformat(),),
            )
        tolerance = rollback_tolerance_seconds
        return AuthorizationClockObservation(
            observed_at=now,
            high_water_at=high_water,
            rolled_back=now.timestamp() + tolerance < high_water.timestamp(),
        )

    def reset_state_tables(self) -> None:
        with self.connect() as connection:
            existing = _existing_tables(connection)
            for table in STATE_TABLES:
                if table in existing:
                    connection.execute(f"DELETE FROM {table}")

    def _init_metadata(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS aico_schema (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO aico_schema (key, value)
                VALUES ('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(STATE_SCHEMA_VERSION),),
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS authorization_clock_state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    high_water_at TEXT NOT NULL
                )
                """
            )


def _existing_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {str(row[0]) for row in rows}


def _table_count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(row[0]) if row is not None else 0


def _parse_authorization_time(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("persisted authorization clock timestamp must be timezone-aware")
    return parsed


def _identifier_sha256(receipt: object, key: str) -> str | None:
    if not isinstance(receipt, dict):
        return None
    value = receipt.get(key)
    if not isinstance(value, str):
        return None
    return hashlib.sha256(value.encode()).hexdigest()
