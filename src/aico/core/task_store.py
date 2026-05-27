"""Task state persistence backends."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

from aico.core.models import ApprovalRequest, Task, TaskSnapshot
from aico.core.sqlite_state import SQLiteStateDatabase


class TaskStateStore(Protocol):
    """Persistence boundary for restart-recoverable task state."""

    def load_task_records(self) -> tuple[Task, ...]: ...

    def load_task_snapshots(self) -> tuple[TaskSnapshot, ...]: ...

    def load_approvals(self) -> tuple[ApprovalRequest, ...]: ...

    def upsert_task_record(self, task: Task) -> None: ...

    def upsert_task_snapshot(self, snapshot: TaskSnapshot) -> None: ...

    def upsert_approval(self, approval: ApprovalRequest) -> None: ...


class SQLiteTaskStateStore:
    """SQLite-backed task state store for local-first production use."""

    def __init__(self, path: Path | str) -> None:
        self._database = SQLiteStateDatabase(path)
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
