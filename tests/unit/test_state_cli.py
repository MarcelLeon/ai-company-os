from io import StringIO
from pathlib import Path

from aico.app.state_cli import run_state_cli
from aico.core import Task
from aico.core.task_store import SQLiteTaskStateStore


def test_state_cli_summarizes_sqlite_state_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteTaskStateStore(db_path)
    store.upsert_task_record(
        Task(task_id="task-1", payload="hello", requester_id="user-1", target_persona="claude")
    )
    stdout = StringIO()

    assert run_state_cli(["--db", str(db_path)], stdout=stdout) == 0

    output = stdout.getvalue()
    assert f"AICO state DB: {db_path}" in output
    assert "schema_version: 1" in output
    assert "- task_records: 1" in output


def test_state_cli_reset_requires_confirmation_and_clears_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteTaskStateStore(db_path)
    store.upsert_task_record(
        Task(task_id="task-1", payload="hello", requester_id="user-1", target_persona="claude")
    )
    stdout = StringIO()

    assert run_state_cli(["--db", str(db_path), "reset"], stdout=stdout) == 2
    assert store.load_task_records()

    stdout = StringIO()
    assert run_state_cli(["--db", str(db_path), "reset", "--yes"], stdout=stdout) == 0
    assert store.load_task_records() == ()
