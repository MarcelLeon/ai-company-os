"""Shared SQLite state database helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

STATE_SCHEMA_VERSION = 1
STATE_TABLES = (
    "task_records",
    "task_snapshots",
    "approval_requests",
    "offline_delegations",
)


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


def _existing_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {str(row[0]) for row in rows}


def _table_count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(row[0]) if row is not None else 0
