"""Task state persistence backends."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from aico.core.authorization_clock import AuthorizationClockObservation
from aico.core.models import (
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    AuditEventType,
    Task,
    TaskSnapshot,
    TaskStatus,
    utc_now,
)
from aico.core.sqlite_state import SQLiteStateDatabase


@dataclass(frozen=True)
class ApprovalExpiryReconciliation:
    approval: ApprovalRequest
    snapshot: TaskSnapshot | None


class TaskStateStore(Protocol):
    """Persistence boundary for restart-recoverable task state."""

    def load_task_records(self) -> tuple[Task, ...]: ...

    def load_task_snapshots(self) -> tuple[TaskSnapshot, ...]: ...

    def load_approvals(self) -> tuple[ApprovalRequest, ...]: ...

    def upsert_task_record(self, task: Task) -> None: ...

    def upsert_task_snapshot(self, snapshot: TaskSnapshot) -> None: ...

    def upsert_approval(self, approval: ApprovalRequest) -> None: ...

    def reconcile_running_tasks(self, *, reason: str) -> tuple[TaskSnapshot, ...]: ...

    def reconcile_expired_approvals(
        self,
        *,
        expires_before: datetime,
        now: datetime,
        reason: str,
        force: bool = False,
    ) -> tuple[ApprovalExpiryReconciliation, ...]: ...

    def load_pending_recovery_audit_events(self) -> tuple[AuditEvent, ...]: ...

    def mark_recovery_audit_delivered(self, event_id: str) -> None: ...

    def observe_authorization_time(
        self,
        now: datetime,
        *,
        minimum_expected_at: datetime,
        rollback_tolerance_seconds: int,
    ) -> AuthorizationClockObservation: ...


class SQLiteTaskStateStore:
    """SQLite-backed task state store for local-first production use."""

    def __init__(
        self,
        path: Path | str,
        *,
        event_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._database = SQLiteStateDatabase(path)
        self._event_id_factory = event_id_factory or (lambda: str(uuid4()))
        self._init_schema()

    def load_task_records(self) -> tuple[Task, ...]:
        rows = self._fetch_payloads("task_records")
        return tuple(Task.model_validate_json(payload) for payload in rows)

    def load_task_snapshots(self) -> tuple[TaskSnapshot, ...]:
        rows = self._fetch_payloads("task_snapshots")
        return tuple(TaskSnapshot.model_validate_json(payload) for payload in rows)

    def load_approvals(self) -> tuple[ApprovalRequest, ...]:
        rows = self._fetch_payloads("approval_requests")
        return tuple(ApprovalRequest.model_validate_json(payload) for payload in rows)

    def upsert_task_record(self, task: Task) -> None:
        self._upsert("task_records", task.task_id, task.model_dump_json())

    def upsert_task_snapshot(self, snapshot: TaskSnapshot) -> None:
        self._upsert("task_snapshots", snapshot.task_id, snapshot.model_dump_json())

    def upsert_approval(self, approval: ApprovalRequest) -> None:
        self._upsert("approval_requests", approval.task.task_id, approval.model_dump_json())

    def reconcile_running_tasks(self, *, reason: str) -> tuple[TaskSnapshot, ...]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            task_records = {
                str(row[0]): Task.model_validate_json(row[1])
                for row in connection.execute(
                    "SELECT task_id, payload FROM task_records"
                ).fetchall()
            }
            snapshots = tuple(
                TaskSnapshot.model_validate_json(row[0])
                for row in connection.execute("SELECT payload FROM task_snapshots").fetchall()
            )
            running = sorted(
                (snapshot for snapshot in snapshots if snapshot.status is TaskStatus.RUNNING),
                key=lambda snapshot: (snapshot.created_at, snapshot.task_id),
            )
            updated = tuple(
                self._persist_recovery(
                    connection, snapshot, task_records.get(snapshot.task_id), reason
                )
                for snapshot in running
            )
        return updated

    def reconcile_expired_approvals(
        self,
        *,
        expires_before: datetime,
        now: datetime,
        reason: str,
        force: bool = False,
    ) -> tuple[ApprovalExpiryReconciliation, ...]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            approvals = tuple(
                ApprovalRequest.model_validate_json(row[0])
                for row in connection.execute("SELECT payload FROM approval_requests").fetchall()
            )
            snapshots = {
                snapshot.task_id: snapshot
                for snapshot in (
                    TaskSnapshot.model_validate_json(row[0])
                    for row in connection.execute("SELECT payload FROM task_snapshots").fetchall()
                )
            }
            expired = sorted(
                (
                    approval
                    for approval in approvals
                    if approval.status is ApprovalStatus.PENDING
                    and (force or _approval_expired(approval, expires_before, now))
                ),
                key=lambda approval: (approval.created_at, approval.task.task_id),
            )
            reconciled = tuple(
                self._persist_approval_expiry(
                    connection,
                    approval,
                    snapshots.get(approval.task.task_id),
                    now,
                    reason,
                )
                for approval in expired
            )
        return reconciled

    def load_pending_recovery_audit_events(self) -> tuple[AuditEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload
                FROM task_recovery_audit_outbox
                WHERE delivered = 0
                ORDER BY rowid
                """
            ).fetchall()
        return tuple(AuditEvent.model_validate_json(row[0]) for row in rows)

    def mark_recovery_audit_delivered(self, event_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE task_recovery_audit_outbox
                SET delivered = 1
                WHERE event_id = ?
                """,
                (event_id,),
            )

    def observe_authorization_time(
        self,
        now: datetime,
        *,
        minimum_expected_at: datetime,
        rollback_tolerance_seconds: int,
    ) -> AuthorizationClockObservation:
        return self._database.observe_authorization_time(
            now,
            minimum_expected_at=minimum_expected_at,
            rollback_tolerance_seconds=rollback_tolerance_seconds,
        )

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS task_records (
                    task_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS task_snapshots (
                    task_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_requests (
                    task_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS task_recovery_audit_outbox (
                    event_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    delivered INTEGER NOT NULL DEFAULT 0 CHECK (delivered IN (0, 1))
                )
                """
            )

    def _persist_recovery(
        self,
        connection: sqlite3.Connection,
        snapshot: TaskSnapshot,
        task: Task | None,
        reason: str,
    ) -> TaskSnapshot:
        updated = snapshot.model_copy(
            update={"status": TaskStatus.INTERRUPTED, "reason": reason, "updated_at": utc_now()}
        )
        event = AuditEvent(
            event_id=self._event_id_factory(),
            event_type=AuditEventType.TASK_INTERRUPTED,
            task_id=snapshot.task_id,
            actor_id=task.requester_id if task is not None else "aico-runtime",
            target_persona=snapshot.target_persona,
            adapter_name=snapshot.adapter_name,
            risk_level=snapshot.risk_level,
            detail=reason,
            trace_id=(task.trace_id or task.task_id) if task is not None else snapshot.task_id,
        )
        connection.execute(
            "UPDATE task_snapshots SET payload = ? WHERE task_id = ?",
            (updated.model_dump_json(), updated.task_id),
        )
        connection.execute(
            """
            INSERT INTO task_recovery_audit_outbox (event_id, task_id, payload, delivered)
            VALUES (?, ?, ?, 0)
            """,
            (event.event_id, event.task_id, event.model_dump_json()),
        )
        return updated

    def _persist_approval_expiry(
        self,
        connection: sqlite3.Connection,
        approval: ApprovalRequest,
        snapshot: TaskSnapshot | None,
        now: datetime,
        reason: str,
    ) -> ApprovalExpiryReconciliation:
        expired = approval.model_copy(
            update={"status": ApprovalStatus.EXPIRED, "reason": reason, "updated_at": now}
        )
        updated_snapshot = snapshot
        if snapshot is not None and snapshot.status is TaskStatus.WAITING_APPROVAL:
            updated_snapshot = snapshot.model_copy(
                update={"status": TaskStatus.REJECTED, "reason": reason, "updated_at": now}
            )
            connection.execute(
                "UPDATE task_snapshots SET payload = ? WHERE task_id = ?",
                (updated_snapshot.model_dump_json(), updated_snapshot.task_id),
            )
        event = AuditEvent(
            event_id=self._event_id_factory(),
            event_type=AuditEventType.APPROVAL_EXPIRED,
            task_id=approval.task.task_id,
            actor_id="aico-policy",
            target_persona=approval.task.target_persona,
            adapter_name=None if snapshot is None else snapshot.adapter_name,
            risk_level=approval.risk.risk_level,
            detail=reason,
            timestamp=now,
            trace_id=approval.task.trace_id or approval.task.task_id,
        )
        connection.execute(
            "UPDATE approval_requests SET payload = ? WHERE task_id = ?",
            (expired.model_dump_json(), approval.task.task_id),
        )
        connection.execute(
            """
            INSERT INTO task_recovery_audit_outbox (event_id, task_id, payload, delivered)
            VALUES (?, ?, ?, 0)
            """,
            (event.event_id, event.task_id, event.model_dump_json()),
        )
        return ApprovalExpiryReconciliation(expired, updated_snapshot)

    def _fetch_payloads(self, table: str) -> tuple[str, ...]:
        with self._connect() as connection:
            rows = connection.execute(f"SELECT payload FROM {table}").fetchall()
        return tuple(str(row[0]) for row in rows)

    def _upsert(self, table: str, task_id: str, payload: str) -> None:
        with self._connect() as connection:
            connection.execute(
                f"""
                INSERT INTO {table} (task_id, payload)
                VALUES (?, ?)
                ON CONFLICT(task_id) DO UPDATE SET payload = excluded.payload
                """,
                (task_id, payload),
            )

    def _connect(self) -> sqlite3.Connection:
        return self._database.connect()


def _approval_expired(
    approval: ApprovalRequest,
    expires_before: datetime,
    now: datetime,
) -> bool:
    if approval.expires_at is not None:
        return approval.expires_at.tzinfo is None or approval.expires_at <= now
    if approval.created_at.tzinfo is None:
        return True
    return approval.created_at <= expires_before
