"""Independent backup, verification, drill, and restore for receiver SQLite state."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import shutil
import sqlite3
import stat
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from aico.app.dead_man_receiver_models import (
    DeadManEvent,
    DeadManEventType,
    DeadManNotificationPolicySnapshot,
    DeadManNotificationProbeContract,
    DeadManNotificationProbeEvent,
    DeadManNotificationProbeSnapshot,
    DeadManNotificationRouteSnapshot,
    DeadManNotificationRouteStatus,
    DeadManOutageReason,
    DeadManRouteHealthEvent,
    DeadManRouteObservationSource,
)
from aico.app.dead_man_receiver_store import (
    DEAD_MAN_RECEIVER_SCHEMA_VERSION,
    DEAD_MAN_RECEIVER_TABLES,
)
from aico.app.runtime_liveness import RuntimeAlertDeliverySignal
from aico.app.runtime_owner import (
    RuntimeOwnerLock,
    RuntimeOwnershipError,
    runtime_owner_lock_path,
)

_IDENTITY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_EXPECTED_SCHEMA_SQL = {
    "dead_man_monitors": """
        CREATE TABLE dead_man_monitors (
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
    """,
    "dead_man_notification_outbox": """
        CREATE TABLE dead_man_notification_outbox (
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
    """,
    "dead_man_notification_policy": """
        CREATE TABLE dead_man_notification_policy (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            configured_routes INTEGER NOT NULL
                CHECK (configured_routes BETWEEN 1 AND 2),
            minimum_acknowledgements INTEGER NOT NULL
                CHECK (minimum_acknowledgements BETWEEN 1 AND configured_routes),
            updated_at TEXT NOT NULL
        )
    """,
    "dead_man_notification_routes": """
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
    """,
    "dead_man_route_health_outbox": """
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
    """,
    "dead_man_notification_probe": """
        CREATE TABLE dead_man_notification_probe (
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
    """,
}


class DeadManReceiverRecoveryError(RuntimeError):
    """Receiver state could not be backed up, trusted, drilled, or restored safely."""


class DeadManReceiverBackupSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["backup", "verify"]
    artifact_name: str
    schema_version: Literal[5] = 5
    integrity: Literal["ok"] = "ok"
    monitor_count: int = Field(ge=0)
    open_monitor_count: int = Field(ge=0)
    outage_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    pending_event_count: int = Field(ge=0)
    degraded_route_count: int = Field(ge=0, le=2)
    route_health_alert_count: int = Field(ge=0)
    pending_route_health_alert_count: int = Field(ge=0)
    notification_probe_enabled: bool
    notification_probe_pending: bool
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class DeadManReceiverRestoreSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["restore"] = "restore"
    schema_version: Literal[5] = 5
    monitor_count: int = Field(ge=0)
    outage_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    pending_event_count: int = Field(ge=0)
    degraded_route_count: int = Field(ge=0, le=2)
    route_health_alert_count: int = Field(ge=0)
    pending_route_health_alert_count: int = Field(ge=0)
    notification_probe_enabled: bool
    notification_probe_pending: bool
    restored_artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    preservation: Literal["none", "verified_safety_backup", "unverified_quarantine"] = "none"
    preservation_name: str | None = None


class DeadManReceiverDrillSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["drill"] = "drill"
    artifact_name: str
    schema_version: Literal[5] = 5
    monitor_count: int = Field(ge=0)
    outage_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    pending_event_count: int = Field(ge=0)
    degraded_route_count: int = Field(ge=0, le=2)
    route_health_alert_count: int = Field(ge=0)
    pending_route_health_alert_count: int = Field(ge=0)
    notification_probe_enabled: bool
    notification_probe_pending: bool
    backup_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    materialized_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    completed_at: datetime
    report_name: str | None = None


def create_dead_man_receiver_backup(
    source_path: Path,
    output_path: Path,
) -> DeadManReceiverBackupSummary:
    source = _canonical_private_file(source_path, label="receiver source database")
    output = _canonical_output(output_path, label="receiver backup output")
    if source == output:
        raise DeadManReceiverRecoveryError("backup source and output must differ")
    if output.exists():
        raise DeadManReceiverRecoveryError("backup output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(output)
    try:
        _sqlite_backup(source, temporary)
        summary = _inspect(temporary, operation="backup", artifact_name=output.name)
        _sync_file(temporary)
        _publish_new_file(temporary, output)
        _sync_directory(output.parent)
        return summary
    except DeadManReceiverRecoveryError:
        _remove_same_inode_if_published(temporary, output)
        raise
    except Exception:
        _remove_same_inode_if_published(temporary, output)
        raise DeadManReceiverRecoveryError("receiver backup failed") from None
    finally:
        temporary.unlink(missing_ok=True)


def verify_dead_man_receiver_backup(path: Path) -> DeadManReceiverBackupSummary:
    backup = _canonical_private_file(path, label="receiver backup artifact")
    try:
        with tempfile.TemporaryDirectory(prefix="aico-dead-man-verify-") as raw_directory:
            snapshot = Path(raw_directory) / "receiver-backup.db"
            shutil.copyfile(backup, snapshot)
            snapshot.chmod(0o600)
            return _inspect(snapshot, operation="verify", artifact_name=backup.name)
    except DeadManReceiverRecoveryError:
        raise
    except OSError:
        raise DeadManReceiverRecoveryError("receiver backup snapshot failed") from None


def drill_dead_man_receiver_backup(
    backup_path: Path,
    *,
    expected_sha256: str,
    workspace: Path | None = None,
    report_path: Path | None = None,
    clock: Callable[[], datetime] | None = None,
) -> DeadManReceiverDrillSummary:
    backup = _canonical_private_file(backup_path, label="receiver backup artifact")
    verified = _verify_expected_hash(backup, expected_sha256)
    drill_workspace = _validated_workspace(workspace)
    report = _validated_report(report_path, backup)
    try:
        with tempfile.TemporaryDirectory(
            prefix="aico-dead-man-drill-", dir=drill_workspace
        ) as raw_directory:
            directory = Path(raw_directory)
            target = directory / "dead-man.db"
            restore_dead_man_receiver_backup(
                target,
                backup,
                expected_sha256=verified.sha256,
            )
            materialized = verify_dead_man_receiver_backup(target)
            _require_parity(verified, materialized)
            completed_at = (clock or (lambda: datetime.now(UTC)))()
            if completed_at.tzinfo is None:
                raise DeadManReceiverRecoveryError("drill clock must be timezone-aware")
            summary = DeadManReceiverDrillSummary(
                artifact_name=backup.name,
                monitor_count=materialized.monitor_count,
                outage_count=materialized.outage_count,
                event_count=materialized.event_count,
                pending_event_count=materialized.pending_event_count,
                degraded_route_count=materialized.degraded_route_count,
                route_health_alert_count=materialized.route_health_alert_count,
                pending_route_health_alert_count=(materialized.pending_route_health_alert_count),
                notification_probe_enabled=materialized.notification_probe_enabled,
                notification_probe_pending=materialized.notification_probe_pending,
                backup_sha256=verified.sha256,
                materialized_sha256=materialized.sha256,
                completed_at=completed_at,
                report_name=report.name if report is not None else None,
            )
    except DeadManReceiverRecoveryError:
        raise
    except Exception:
        raise DeadManReceiverRecoveryError("receiver disposable restore drill failed") from None
    if report is not None:
        _write_new_report(report, summary.model_dump_json() + "\n")
    return summary


def restore_dead_man_receiver_backup(
    target_path: Path,
    backup_path: Path,
    *,
    expected_sha256: str,
    clock: Callable[[], datetime] | None = None,
) -> DeadManReceiverRestoreSummary:
    target = _canonical_output(target_path, label="receiver restore target")
    backup = _canonical_private_file(backup_path, label="receiver backup artifact")
    if target == backup:
        raise DeadManReceiverRecoveryError("restore target and backup must differ")
    target.parent.mkdir(parents=True, exist_ok=True)
    owner = RuntimeOwnerLock(
        runtime_owner_lock_path(target, base_dir=target.parent),
        resource_path=target,
    )
    try:
        owner.acquire()
    except RuntimeOwnershipError:
        raise DeadManReceiverRecoveryError("receiver worker is active; restore refused") from None
    try:
        return _restore_while_owned(
            target,
            backup,
            expected_sha256=expected_sha256,
            clock=clock,
        )
    finally:
        owner.release()


def _restore_while_owned(
    target: Path,
    backup: Path,
    *,
    expected_sha256: str,
    clock: Callable[[], datetime] | None,
) -> DeadManReceiverRestoreSummary:
    temporary = _temporary_path(target)
    preservation: Literal["none", "verified_safety_backup", "unverified_quarantine"] = "none"
    preservation_name: str | None = None
    try:
        shutil.copyfile(backup, temporary)
        temporary.chmod(0o600)
        staged_sha256 = _sha256_file(temporary)
        if not hmac.compare_digest(staged_sha256, expected_sha256.lower()):
            raise DeadManReceiverRecoveryError(
                "receiver backup SHA-256 does not match expected value"
            )
        restored = _inspect(temporary, operation="verify", artifact_name=target.name)
        _sync_file(temporary)
        if target.exists():
            preservation, preservation_name = _preserve_live(target, clock=clock)
        os.replace(temporary, target)
        Path(f"{target}-wal").unlink(missing_ok=True)
        Path(f"{target}-shm").unlink(missing_ok=True)
        _sync_directory(target.parent)
    except DeadManReceiverRecoveryError:
        raise
    except Exception:
        raise DeadManReceiverRecoveryError("receiver restore failed") from None
    finally:
        temporary.unlink(missing_ok=True)
    return DeadManReceiverRestoreSummary(
        monitor_count=restored.monitor_count,
        outage_count=restored.outage_count,
        event_count=restored.event_count,
        pending_event_count=restored.pending_event_count,
        degraded_route_count=restored.degraded_route_count,
        route_health_alert_count=restored.route_health_alert_count,
        pending_route_health_alert_count=restored.pending_route_health_alert_count,
        notification_probe_enabled=restored.notification_probe_enabled,
        notification_probe_pending=restored.notification_probe_pending,
        restored_artifact_sha256=staged_sha256,
        preservation=preservation,
        preservation_name=preservation_name,
    )


def _inspect(
    path: Path,
    *,
    operation: Literal["backup", "verify"],
    artifact_name: str,
) -> DeadManReceiverBackupSummary:
    try:
        with sqlite3.connect(_read_only_uri(path), uri=True) as connection:
            connection.row_factory = sqlite3.Row
            integrity = [tuple(row) for row in connection.execute("PRAGMA integrity_check")]
            if integrity != [("ok",)]:
                raise DeadManReceiverRecoveryError("receiver backup integrity check failed")
            _require_schema(connection)
            metrics = _semantic_metrics(connection)
    except DeadManReceiverRecoveryError:
        raise
    except (OSError, sqlite3.Error, TypeError, ValueError, ValidationError):
        raise DeadManReceiverRecoveryError(
            "receiver backup integrity, schema, or semantic verification failed"
        ) from None
    return DeadManReceiverBackupSummary(
        operation=operation,
        artifact_name=artifact_name,
        schema_version=DEAD_MAN_RECEIVER_SCHEMA_VERSION,
        monitor_count=metrics["monitor_count"],
        open_monitor_count=metrics["open_monitor_count"],
        outage_count=metrics["outage_count"],
        event_count=metrics["event_count"],
        pending_event_count=metrics["pending_event_count"],
        degraded_route_count=metrics["degraded_route_count"],
        route_health_alert_count=metrics["route_health_alert_count"],
        pending_route_health_alert_count=metrics["pending_route_health_alert_count"],
        notification_probe_enabled=bool(metrics["notification_probe_enabled"]),
        notification_probe_pending=bool(metrics["notification_probe_pending"]),
        bytes=path.stat().st_size,
        sha256=_sha256_file(path),
    )


def _require_schema(connection: sqlite3.Connection) -> None:
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version != DEAD_MAN_RECEIVER_SCHEMA_VERSION:
        raise DeadManReceiverRecoveryError("receiver backup schema version is not supported")
    objects = connection.execute(
        "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
    ).fetchall()
    tables = {str(row["name"]) for row in objects if row["type"] == "table"}
    expected_tables = {*DEAD_MAN_RECEIVER_TABLES, "sqlite_sequence"}
    if tables != expected_tables:
        raise DeadManReceiverRecoveryError("receiver backup schema tables are invalid")
    if any(row["type"] in {"trigger", "view"} for row in objects):
        raise DeadManReceiverRecoveryError("receiver backup executable schema objects are refused")
    if any(row["type"] == "index" and row["sql"] is not None for row in objects):
        raise DeadManReceiverRecoveryError("receiver backup user-defined indexes are refused")
    object_by_name = {str(row["name"]): row for row in objects}
    for table, expected_sql in _EXPECTED_SCHEMA_SQL.items():
        if _normalized_sql(object_by_name[table]["sql"]) != _normalized_sql(expected_sql):
            raise DeadManReceiverRecoveryError("receiver backup table constraints are invalid")
    if connection.execute("PRAGMA foreign_key_check").fetchall():
        raise DeadManReceiverRecoveryError("receiver backup foreign-key check failed")
    _require_schema_columns(connection)


def _require_schema_columns(connection: sqlite3.Connection) -> None:
    expected_columns = {
        "dead_man_monitors": (
            "runtime_id",
            "expires_after_seconds",
            "armed_at",
            "boot_id",
            "sequence",
            "sent_at",
            "last_received_at",
            "outage_id",
            "outage_opened_at",
            "updated_at",
            "last_pulse_received_at",
            "alert_delivery_status",
            "outage_reason",
        ),
        "dead_man_notification_outbox": (
            "row_id",
            "event_id",
            "outage_id",
            "event_type",
            "runtime_id",
            "payload",
            "delivered",
            "delivery_attempts",
            "next_attempt_at",
            "configured_routes",
            "minimum_acknowledgements",
            "acknowledged_route_mask",
            "last_attempt_at",
        ),
        "dead_man_notification_policy": (
            "singleton",
            "configured_routes",
            "minimum_acknowledgements",
            "updated_at",
        ),
        "dead_man_notification_probe": (
            "singleton",
            "contract",
            "interval_seconds",
            "failure_threshold",
            "max_age_seconds",
            "probe_id",
            "payload",
            "scheduled_at",
            "next_probe_at",
            "last_completed_at",
            "last_acknowledged_route_mask",
            "updated_at",
        ),
        "dead_man_notification_routes": (
            "route_slot",
            "status",
            "consecutive_failures",
            "last_attempt_at",
            "last_acknowledged_at",
            "updated_at",
            "consecutive_probe_failures",
            "last_probe_at",
            "last_probe_acknowledged_at",
        ),
        "dead_man_route_health_outbox": (
            "row_id",
            "event_id",
            "route_slot",
            "event_type",
            "triggering_event_id",
            "runtime_id",
            "payload",
            "delivered",
            "delivery_attempts",
            "next_attempt_at",
            "observation_source",
        ),
    }
    for table, expected in expected_columns.items():
        column_rows = connection.execute(f"PRAGMA table_info({table})")
        actual = tuple(str(row["name"]) for row in column_rows)
        if actual != expected:
            raise DeadManReceiverRecoveryError("receiver backup schema columns are invalid")


def _semantic_metrics(connection: sqlite3.Connection) -> dict[str, int]:
    policy_rows = connection.execute(
        "SELECT * FROM dead_man_notification_policy ORDER BY singleton"
    ).fetchall()
    if len(policy_rows) != 1 or int(policy_rows[0]["singleton"]) != 1:
        raise DeadManReceiverRecoveryError("receiver notification policy is invalid")
    policy = DeadManNotificationPolicySnapshot(
        configured_routes=int(policy_rows[0]["configured_routes"]),
        minimum_acknowledgements=int(policy_rows[0]["minimum_acknowledgements"]),
        updated_at=_aware_time(policy_rows[0]["updated_at"]),
    )
    probe_rows = connection.execute(
        "SELECT * FROM dead_man_notification_probe ORDER BY singleton"
    ).fetchall()
    probe = _validated_probe(probe_rows, policy)
    route_rows = connection.execute(
        "SELECT * FROM dead_man_notification_routes ORDER BY route_slot"
    ).fetchall()
    monitor_rows = connection.execute(
        "SELECT * FROM dead_man_monitors ORDER BY runtime_id"
    ).fetchall()
    event_rows = connection.execute(
        "SELECT * FROM dead_man_notification_outbox ORDER BY row_id"
    ).fetchall()
    events_by_outage = _validated_events(event_rows, policy)
    routes = _validated_routes(route_rows, policy)
    route_alert_rows = connection.execute(
        "SELECT * FROM dead_man_route_health_outbox ORDER BY row_id"
    ).fetchall()
    _validated_route_health_alerts(route_alert_rows, event_rows, policy)
    open_monitors = 0
    for row in monitor_rows:
        _validate_monitor(row, events_by_outage)
        open_monitors += row["outage_id"] is not None
    return {
        "monitor_count": len(monitor_rows),
        "open_monitor_count": open_monitors,
        "outage_count": len(events_by_outage),
        "event_count": len(event_rows),
        "pending_event_count": sum(not bool(row["delivered"]) for row in event_rows),
        "degraded_route_count": sum(
            route.status is DeadManNotificationRouteStatus.DEGRADED for route in routes
        ),
        "route_health_alert_count": len(route_alert_rows),
        "pending_route_health_alert_count": sum(
            not bool(row["delivered"]) for row in route_alert_rows
        ),
        "notification_probe_enabled": int(
            probe.contract is DeadManNotificationProbeContract.SILENT_ROUTE_PROBE_V1
        ),
        "notification_probe_pending": int(probe.pending_probe is not None),
    }


def _validated_probe(
    rows: list[sqlite3.Row],
    policy: DeadManNotificationPolicySnapshot,
) -> DeadManNotificationProbeSnapshot:
    if len(rows) != 1 or int(rows[0]["singleton"]) != 1:
        raise DeadManReceiverRecoveryError("receiver notification probe policy is invalid")
    row = rows[0]
    try:
        pending = (
            DeadManNotificationProbeEvent.model_validate_json(row["payload"])
            if row["payload"] is not None
            else None
        )
        if pending is not None and (
            pending.event_id != row["probe_id"]
            or pending.scheduled_at != _aware_time(row["scheduled_at"])
        ):
            raise ValueError("probe payload metadata mismatch")
        mask = row["last_acknowledged_route_mask"]
        snapshot = DeadManNotificationProbeSnapshot(
            contract=DeadManNotificationProbeContract(str(row["contract"])),
            interval_seconds=int(row["interval_seconds"]),
            failure_threshold=int(row["failure_threshold"]),
            max_age_seconds=int(row["max_age_seconds"]),
            pending_probe=pending,
            next_probe_at=(
                None if row["next_probe_at"] is None else _aware_time(row["next_probe_at"])
            ),
            last_completed_at=(
                None if row["last_completed_at"] is None else _aware_time(row["last_completed_at"])
            ),
            last_acknowledged_routes=(
                None
                if mask is None
                else tuple(bool(int(mask) & (1 << index)) for index in range(2))
            ),
            updated_at=_aware_time(row["updated_at"]),
        )
    except (ValueError, ValidationError):
        raise DeadManReceiverRecoveryError(
            "receiver notification probe checkpoint is invalid"
        ) from None
    if (
        snapshot.contract is DeadManNotificationProbeContract.SILENT_ROUTE_PROBE_V1
        and policy.configured_routes != 2
    ):
        raise DeadManReceiverRecoveryError("receiver notification probe policy drifted")
    return snapshot


def _validated_routes(
    rows: list[sqlite3.Row],
    policy: DeadManNotificationPolicySnapshot,
) -> tuple[DeadManNotificationRouteSnapshot, ...]:
    expected_slots = tuple(range(1, policy.configured_routes + 1))
    if tuple(int(row["route_slot"]) for row in rows) != expected_slots:
        raise DeadManReceiverRecoveryError("receiver notification route set is invalid")
    try:
        return tuple(
            DeadManNotificationRouteSnapshot(
                route_slot=int(row["route_slot"]),
                status=DeadManNotificationRouteStatus(str(row["status"])),
                consecutive_failures=int(row["consecutive_failures"]),
                consecutive_probe_failures=int(row["consecutive_probe_failures"]),
                last_attempt_at=(
                    None if row["last_attempt_at"] is None else _aware_time(row["last_attempt_at"])
                ),
                last_acknowledged_at=(
                    None
                    if row["last_acknowledged_at"] is None
                    else _aware_time(row["last_acknowledged_at"])
                ),
                last_probe_at=(
                    None if row["last_probe_at"] is None else _aware_time(row["last_probe_at"])
                ),
                last_probe_acknowledged_at=(
                    None
                    if row["last_probe_acknowledged_at"] is None
                    else _aware_time(row["last_probe_acknowledged_at"])
                ),
                updated_at=_aware_time(row["updated_at"]),
            )
            for row in rows
        )
    except (ValueError, ValidationError):
        raise DeadManReceiverRecoveryError(
            "receiver notification route checkpoint is invalid"
        ) from None


def _validated_route_health_alerts(
    rows: list[sqlite3.Row],
    event_rows: list[sqlite3.Row],
    policy: DeadManNotificationPolicySnapshot,
) -> None:
    events = {str(row["event_id"]): row for row in event_rows}
    seen: set[str] = set()
    for row in rows:
        delivered = bool(row["delivered"])
        attempts = int(row["delivery_attempts"])
        if int(row["delivered"]) not in {0, 1} or attempts < 0:
            raise DeadManReceiverRecoveryError("receiver route alert delivery is invalid")
        _validate_retry_checkpoint(delivered, attempts, row["next_attempt_at"])
        event = DeadManRouteHealthEvent.model_validate_json(row["payload"])
        if (
            event.event_id != row["event_id"]
            or event.route_slot != int(row["route_slot"])
            or event.event_type.value != row["event_type"]
            or event.triggering_event_id != row["triggering_event_id"]
            or event.runtime_id != row["runtime_id"]
            or event.observation_source.value != row["observation_source"]
        ):
            raise DeadManReceiverRecoveryError("receiver route alert payload metadata mismatch")
        if event.observation_source is DeadManRouteObservationSource.OUTAGE_DELIVERY:
            trigger = events.get(event.triggering_event_id)
            if trigger is None:
                raise DeadManReceiverRecoveryError("receiver route alert trigger is missing")
            if event.runtime_id != trigger["runtime_id"] or event.route_slot > int(
                trigger["configured_routes"]
            ):
                raise DeadManReceiverRecoveryError("receiver route alert payload metadata mismatch")
        elif not event.triggering_event_id.startswith("rp-"):
            raise DeadManReceiverRecoveryError("receiver route probe alert trigger is invalid")
        if not delivered and event.route_slot > policy.configured_routes:
            raise DeadManReceiverRecoveryError("receiver pending route alert policy drifted")
        if event.event_id in seen:
            raise DeadManReceiverRecoveryError("receiver route alert identity is duplicated")
        seen.add(event.event_id)


def _validated_events(
    rows: list[sqlite3.Row],
    policy: DeadManNotificationPolicySnapshot,
) -> dict[str, list[DeadManEvent]]:
    grouped: dict[str, list[DeadManEvent]] = {}
    for row in rows:
        delivered = int(row["delivered"])
        attempts = int(row["delivery_attempts"])
        if delivered not in {0, 1} or attempts < 0:
            raise DeadManReceiverRecoveryError("receiver outbox delivery checkpoint is invalid")
        configured_routes = int(row["configured_routes"])
        minimum_acknowledgements = int(row["minimum_acknowledgements"])
        if not 1 <= minimum_acknowledgements <= configured_routes <= 2:
            raise DeadManReceiverRecoveryError("receiver event notification policy is invalid")
        if not delivered and (
            configured_routes != policy.configured_routes
            or minimum_acknowledgements != policy.minimum_acknowledgements
        ):
            raise DeadManReceiverRecoveryError("receiver pending event notification policy drifted")
        _validate_retry_checkpoint(bool(delivered), attempts, row["next_attempt_at"])
        mask = row["acknowledged_route_mask"]
        last_attempt_at = row["last_attempt_at"]
        if (mask is None) != (last_attempt_at is None):
            raise DeadManReceiverRecoveryError("receiver route attempt checkpoint is partial")
        if mask is not None:
            mask_value = int(mask)
            if not 0 <= mask_value < 1 << configured_routes:
                raise DeadManReceiverRecoveryError("receiver route acknowledgement mask is invalid")
            acknowledgements = mask_value.bit_count()
            if delivered and acknowledgements < minimum_acknowledgements:
                raise DeadManReceiverRecoveryError("receiver delivered event missed frozen quorum")
            _aware_time(last_attempt_at)
        event = DeadManEvent.model_validate_json(row["payload"])
        if (
            event.event_id != row["event_id"]
            or event.outage_id != row["outage_id"]
            or event.event_type.value != row["event_type"]
            or event.runtime_id != row["runtime_id"]
        ):
            raise DeadManReceiverRecoveryError("receiver outbox payload metadata mismatch")
        if row["next_attempt_at"] is not None:
            _aware_time(row["next_attempt_at"])
        grouped.setdefault(event.outage_id, []).append(event)
    for events in grouped.values():
        if not 1 <= len(events) <= 2:
            raise DeadManReceiverRecoveryError("receiver outage event cardinality is invalid")
        if events[0].event_type is not DeadManEventType.OUTAGE_OPENED:
            raise DeadManReceiverRecoveryError("receiver outage does not begin with opened")
        if len(events) == 2:
            if events[1].event_type is not DeadManEventType.OUTAGE_RESOLVED:
                raise DeadManReceiverRecoveryError("receiver outage does not end with resolved")
            if events[1].runtime_id != events[0].runtime_id:
                raise DeadManReceiverRecoveryError("receiver outage runtime identity changed")
            if events[1].occurred_at < events[0].occurred_at:
                raise DeadManReceiverRecoveryError("receiver outage resolution precedes opening")
            if events[1].reason is not events[0].reason:
                raise DeadManReceiverRecoveryError("receiver outage reason changed")
    overtaken = _delivery_overtake(rows)
    if overtaken:
        raise DeadManReceiverRecoveryError("receiver resolved delivery overtook opened delivery")
    return grouped


def _validate_retry_checkpoint(
    delivered: bool,
    attempts: int,
    next_attempt_at: object,
) -> None:
    if delivered:
        if next_attempt_at is not None:
            raise DeadManReceiverRecoveryError("receiver delivered item retained retry time")
        return
    if (next_attempt_at is None) != (attempts == 0):
        raise DeadManReceiverRecoveryError("receiver outbox retry checkpoint is partial")
    if next_attempt_at is not None:
        _aware_time(next_attempt_at)


def _validate_monitor(
    row: sqlite3.Row,
    events_by_outage: dict[str, list[DeadManEvent]],
) -> None:
    runtime_id = str(row["runtime_id"])
    if _IDENTITY_PATTERN.fullmatch(runtime_id) is None:
        raise DeadManReceiverRecoveryError("receiver monitor runtime identity is invalid")
    if int(row["expires_after_seconds"]) <= 0:
        raise DeadManReceiverRecoveryError("receiver monitor TTL is invalid")
    for column in ("armed_at", "updated_at"):
        _aware_time(row[column])
    ordered_values = tuple(row[key] for key in ("boot_id", "sequence", "sent_at"))
    if any(value is None for value in ordered_values) and any(
        value is not None for value in ordered_values
    ):
        raise DeadManReceiverRecoveryError("receiver monitor pulse checkpoint is partial")
    if row["sent_at"] is not None:
        if _IDENTITY_PATTERN.fullmatch(str(row["boot_id"])) is None:
            raise DeadManReceiverRecoveryError("receiver monitor boot identity is invalid")
        if int(row["sequence"]) <= 0:
            raise DeadManReceiverRecoveryError("receiver monitor sequence is invalid")
        _aware_time(row["sent_at"])
    if row["last_received_at"] is not None:
        _aware_time(row["last_received_at"])
    if row["last_pulse_received_at"] is not None:
        _aware_time(row["last_pulse_received_at"])
    if (row["last_pulse_received_at"] is None) != all(value is None for value in ordered_values):
        raise DeadManReceiverRecoveryError(
            "receiver monitor ordered pulse receipt checkpoint is partial"
        )
    if row["last_received_at"] is not None and row["last_pulse_received_at"] is None:
        raise DeadManReceiverRecoveryError(
            "receiver monitor renewal lacks an ordered pulse receipt"
        )
    try:
        RuntimeAlertDeliverySignal(str(row["alert_delivery_status"]))
    except ValueError:
        raise DeadManReceiverRecoveryError(
            "receiver monitor alert delivery status is invalid"
        ) from None
    outage_values = (row["outage_id"], row["outage_opened_at"], row["outage_reason"])
    if any(value is None for value in outage_values) != all(
        value is None for value in outage_values
    ):
        raise DeadManReceiverRecoveryError("receiver monitor outage checkpoint is partial")
    if row["outage_id"] is None:
        return
    opened_at = _aware_time(row["outage_opened_at"])
    try:
        outage_reason = DeadManOutageReason(str(row["outage_reason"]))
    except ValueError:
        raise DeadManReceiverRecoveryError("receiver monitor outage reason is invalid") from None
    events = events_by_outage.get(str(row["outage_id"]), [])
    if len(events) != 1 or events[0].event_type is not DeadManEventType.OUTAGE_OPENED:
        raise DeadManReceiverRecoveryError("receiver open monitor lacks one open event")
    if (
        events[0].runtime_id != row["runtime_id"]
        or events[0].occurred_at != opened_at
        or events[0].reason is not outage_reason
    ):
        raise DeadManReceiverRecoveryError("receiver open monitor and outage event disagree")


def _preserve_live(
    target: Path,
    *,
    clock: Callable[[], datetime] | None,
) -> tuple[Literal["verified_safety_backup", "unverified_quarantine"], str]:
    stamp = _utc_stamp(clock)
    safety = target.with_name(f"{target.name}.pre-restore-{stamp}.db")
    if safety.exists():
        raise DeadManReceiverRecoveryError("receiver preservation output already exists")
    try:
        create_dead_man_receiver_backup(target, safety)
    except DeadManReceiverRecoveryError:
        if safety.exists():
            raise DeadManReceiverRecoveryError(
                "receiver preservation output already exists"
            ) from None
        quarantine = _quarantine_raw_live(target, stamp=stamp)
        return "unverified_quarantine", quarantine.name
    return "verified_safety_backup", safety.name


def _quarantine_raw_live(target: Path, *, stamp: str) -> Path:
    raw_directory = tempfile.mkdtemp(
        prefix=f"{target.name}.unverified-pre-restore-{stamp}-",
        dir=target.parent,
    )
    quarantine = Path(raw_directory)
    quarantine.chmod(0o700)
    try:
        for source in (target, Path(f"{target}-wal"), Path(f"{target}-shm")):
            if not source.exists():
                continue
            destination = quarantine / source.name
            shutil.copyfile(source, destination)
            destination.chmod(0o600)
            _sync_file(destination)
        _sync_directory(quarantine)
        _sync_directory(target.parent)
    except Exception:
        shutil.rmtree(quarantine, ignore_errors=True)
        raise DeadManReceiverRecoveryError("receiver live-state quarantine failed") from None
    return quarantine


def _sqlite_backup(source: Path, destination: Path) -> None:
    try:
        with sqlite3.connect(_read_only_uri(source, immutable=False), uri=True) as source_db:
            with sqlite3.connect(destination) as destination_db:
                source_db.backup(destination_db)
    except sqlite3.Error:
        raise DeadManReceiverRecoveryError("receiver SQLite online backup failed") from None
    destination.chmod(0o600)


def _verify_expected_hash(path: Path, expected: str) -> DeadManReceiverBackupSummary:
    verified = verify_dead_man_receiver_backup(path)
    if not hmac.compare_digest(verified.sha256, expected.lower()):
        raise DeadManReceiverRecoveryError("receiver backup SHA-256 does not match expected value")
    return verified


def _require_parity(
    backup: DeadManReceiverBackupSummary,
    materialized: DeadManReceiverBackupSummary,
) -> None:
    fields = (
        "schema_version",
        "monitor_count",
        "open_monitor_count",
        "outage_count",
        "event_count",
        "pending_event_count",
        "degraded_route_count",
        "route_health_alert_count",
        "pending_route_health_alert_count",
        "notification_probe_enabled",
        "notification_probe_pending",
    )
    if any(getattr(backup, field) != getattr(materialized, field) for field in fields):
        raise DeadManReceiverRecoveryError(
            "receiver drill materialized semantics do not match backup"
        )


def _validated_workspace(workspace: Path | None) -> Path | None:
    if workspace is None:
        return None
    expanded = workspace.expanduser()
    if expanded.is_symlink():
        raise DeadManReceiverRecoveryError("receiver drill workspace cannot be a symlink")
    resolved = expanded.resolve()
    if not resolved.is_dir():
        raise DeadManReceiverRecoveryError("receiver drill workspace is missing")
    return resolved


def _validated_report(report: Path | None, backup: Path) -> Path | None:
    if report is None:
        return None
    resolved = _canonical_output(report, label="receiver drill report")
    if resolved == backup:
        raise DeadManReceiverRecoveryError("receiver drill report and backup must differ")
    if resolved.exists():
        raise DeadManReceiverRecoveryError("receiver drill report already exists")
    return resolved


def _write_new_report(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(path)
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.chmod(0o600)
        _sync_file(temporary)
        _publish_new_file(temporary, path)
        _sync_directory(path.parent)
    except DeadManReceiverRecoveryError:
        _remove_same_inode_if_published(temporary, path)
        raise
    except Exception:
        _remove_same_inode_if_published(temporary, path)
        raise DeadManReceiverRecoveryError("receiver drill report publication failed") from None
    finally:
        temporary.unlink(missing_ok=True)


def _temporary_path(target: Path) -> Path:
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    os.close(descriptor)
    return Path(raw_path)


def _publish_new_file(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
    except FileExistsError:
        raise DeadManReceiverRecoveryError("receiver recovery output already exists") from None


def _remove_same_inode_if_published(source: Path, destination: Path) -> None:
    try:
        if destination.exists() and os.path.samefile(source, destination):
            destination.unlink()
            _sync_directory(destination.parent)
    except OSError:
        pass


def _read_only_uri(path: Path, *, immutable: bool = True) -> str:
    query = "?mode=ro&immutable=1" if immutable else "?mode=ro"
    return f"{path.as_uri()}{query}"


def _canonical_private_file(path: Path, *, label: str) -> Path:
    expanded = path.expanduser()
    if expanded.is_symlink():
        raise DeadManReceiverRecoveryError(f"{label} cannot be a symlink")
    canonical = expanded.resolve()
    if not canonical.is_file():
        raise DeadManReceiverRecoveryError(f"{label} is missing or not a regular file")
    if stat.S_IMODE(canonical.stat().st_mode) & 0o077:
        raise DeadManReceiverRecoveryError(f"{label} must be owner-only")
    return canonical


def _canonical_output(path: Path, *, label: str) -> Path:
    expanded = path.expanduser()
    if expanded.is_symlink():
        raise DeadManReceiverRecoveryError(f"{label} cannot be a symlink")
    return expanded.resolve()


def _aware_time(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise DeadManReceiverRecoveryError("receiver recovery timestamp is timezone-naive")
    return parsed


def _delivery_overtake(rows: list[sqlite3.Row]) -> bool:
    delivery_by_outage: dict[str, dict[str, bool]] = {}
    for row in rows:
        delivery_by_outage.setdefault(str(row["outage_id"]), {})[str(row["event_type"])] = bool(
            row["delivered"]
        )
    return any(
        states.get(DeadManEventType.OUTAGE_RESOLVED.value, False)
        and not states.get(DeadManEventType.OUTAGE_OPENED.value, False)
        for states in delivery_by_outage.values()
    )


def _normalized_sql(value: object) -> str:
    return " ".join(str(value).split()).lower()


def _utc_stamp(clock: Callable[[], datetime] | None) -> str:
    now = (clock or (lambda: datetime.now(UTC)))()
    if now.tzinfo is None:
        raise DeadManReceiverRecoveryError("receiver restore clock must be timezone-aware")
    return now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _sync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
