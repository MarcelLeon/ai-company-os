import io
import json
from pathlib import Path

from aico.app.audit_cli import run
from aico.core import AuditEventType, InMemoryAuditLog, JsonlAuditSink, Task
from aico.core.audit_ledger import verify_audit_ledger
from aico.core.task_store import SQLiteTaskStateStore


def test_audit_cli_verifies_sealed_ledger_from_environment(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    _write_event(path)
    stdout = io.StringIO()

    exit_code = run(
        ["verify"],
        stdout=stdout,
        environ={"AICO_AUDIT_LOG_PATH": str(path)},
    )

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload == {
        "byte_size": path.stat().st_size,
        "checkpoint_lag": False,
        "event_count": 1,
        "operation": "verify",
        "sealed": True,
        "status": "ok",
    }


def test_audit_cli_seals_legacy_without_rewriting_events(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    event = InMemoryAuditLog(event_id_factory=lambda: "legacy-event").record(
        AuditEventType.TASK_SUBMITTED,
        _task(),
    )
    original = event.model_dump_json().encode("utf-8") + b"\n"
    path.write_bytes(original)
    stdout = io.StringIO()

    exit_code = run(["--audit-log", str(path), "seal"], stdout=stdout)

    assert exit_code == 0
    assert path.read_bytes() == original
    assert json.loads(stdout.getvalue())["sealed"] is True
    assert path.with_name("audit.jsonl.checkpoint.json").is_file()


def test_audit_cli_refuses_unsealed_or_tampered_history_without_leaking_content(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private-customer-audit.jsonl"
    secret = "private-customer-order"
    path.write_text(
        InMemoryAuditLog(event_id_factory=lambda: "legacy-event")
        .record(AuditEventType.TASK_SUBMITTED, _task(payload=secret))
        .model_dump_json()
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    error = io.StringIO()

    exit_code = run(["--audit-log", str(path), "verify"], stderr=error)

    assert exit_code == 2
    assert "unsealed" in error.getvalue()
    assert secret not in error.getvalue()
    assert str(path) not in error.getvalue()


def test_audit_cli_requires_explicit_path() -> None:
    error = io.StringIO()

    exit_code = run(["verify"], stderr=error, environ={})

    assert exit_code == 2
    assert "AICO_AUDIT_LOG_PATH" in error.getvalue()


def test_audit_cli_refuses_to_seal_a_missing_ledger(tmp_path: Path) -> None:
    error = io.StringIO()

    exit_code = run(["--audit-log", str(tmp_path / "typo.jsonl"), "seal"], stderr=error)

    assert exit_code == 2
    assert "does not exist" in error.getvalue()
    assert str(tmp_path) not in error.getvalue()


def test_audit_cli_creates_and_verifies_backup_without_live_path(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    backup = tmp_path / "audit-recovery.zip"
    _write_event(path)
    stdout = io.StringIO()

    assert (
        run(
            ["--audit-log", str(path), "backup", "--output", str(backup)],
            stdout=stdout,
        )
        == 0
    )
    created = json.loads(stdout.getvalue())
    path.unlink()
    path.with_name("audit.jsonl.checkpoint.json").unlink()

    stdout = io.StringIO()
    assert (
        run(
            [
                "verify-backup",
                "--backup",
                str(backup),
                "--expected-sha256",
                created["sha256"],
            ],
            stdout=stdout,
            environ={},
        )
        == 0
    )
    assert json.loads(stdout.getvalue())["event_count"] == 1


def test_audit_cli_backup_error_does_not_leak_path_or_payload(tmp_path: Path) -> None:
    path = tmp_path / "private-customer-audit.jsonl"
    backup = tmp_path / "private-customer-recovery.zip"
    secret = "merchant private payload"
    _write_event(path, payload=secret)
    assert run(["--audit-log", str(path), "backup", "--output", str(backup)]) == 0
    error = io.StringIO()

    exit_code = run(
        [
            "verify-backup",
            "--backup",
            str(backup),
            "--expected-sha256",
            "0" * 64,
        ],
        stderr=error,
        environ={},
    )

    assert exit_code == 2
    assert "does not match" in error.getvalue()
    assert secret not in error.getvalue()
    assert str(path) not in error.getvalue()
    assert str(backup) not in error.getvalue()


def test_audit_cli_drills_and_explicitly_restores_with_environment_fence(
    tmp_path: Path,
) -> None:
    live = tmp_path / "audit.jsonl"
    backup = tmp_path / "recovery.zip"
    report = tmp_path / "drill.json"
    preserve = tmp_path / "pre-restore.zip"
    state_db = tmp_path / "state.db"
    SQLiteTaskStateStore(state_db)
    _write_event(live)
    create_output = io.StringIO()
    assert (
        run(
            ["--audit-log", str(live), "backup", "--output", str(backup)],
            stdout=create_output,
        )
        == 0
    )
    artifact_sha = json.loads(create_output.getvalue())["sha256"]

    drill_output = io.StringIO()
    assert (
        run(
            [
                "drill-backup",
                "--backup",
                str(backup),
                "--expected-sha256",
                artifact_sha,
                "--report",
                str(report),
            ],
            stdout=drill_output,
            environ={},
        )
        == 0
    )
    assert json.loads(drill_output.getvalue())["operation"] == "drill"
    _write_second_event(live)

    error = io.StringIO()
    assert (
        run(
            [
                "--audit-log",
                str(live),
                "restore",
                "--backup",
                str(backup),
                "--expected-sha256",
                artifact_sha,
                "--preservation-output",
                str(preserve),
            ],
            stderr=error,
            environ={"AICO_STATE_DB_PATH": str(state_db)},
        )
        == 2
    )
    assert "confirmation" in error.getvalue()
    assert verify_audit_ledger(live).event_count == 2
    assert not preserve.exists()

    restored_output = io.StringIO()
    assert (
        run(
            [
                "--audit-log",
                str(live),
                "restore",
                "--backup",
                str(backup),
                "--expected-sha256",
                artifact_sha,
                "--preservation-output",
                str(preserve),
                "--yes",
            ],
            stdout=restored_output,
            environ={"AICO_STATE_DB_PATH": str(state_db)},
        )
        == 0
    )
    assert json.loads(restored_output.getvalue())["operation"] == "restore"
    assert verify_audit_ledger(live).event_count == 1


def _write_event(path: Path, *, payload: str = "inspect") -> None:
    JsonlAuditSink(path).write(
        InMemoryAuditLog(event_id_factory=lambda: "event-1").record(
            AuditEventType.TASK_SUBMITTED,
            _task(payload=payload),
        )
    )


def _write_second_event(path: Path) -> None:
    JsonlAuditSink(path).write(
        InMemoryAuditLog(event_id_factory=lambda: "event-2").record(
            AuditEventType.TASK_SUBMITTED,
            Task(
                task_id="task-2",
                payload="inspect later",
                requester_id="owner",
                target_persona="reviewer",
            ),
        )
    )


def _task(*, payload: str = "inspect") -> Task:
    return Task(
        task_id="task-1",
        payload=payload,
        requester_id="owner",
        target_persona="reviewer",
    )
