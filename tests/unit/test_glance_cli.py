import json
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

from pytest import MonkeyPatch

from aico.app.glance_cli import run
from aico.core import AuditEvent, AuditEventType, RiskLevel


def test_glance_cli_outputs_text_from_audit_log(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    _write_audit_events(audit_path)
    stdout = StringIO()

    exit_code = run(["--audit-log", str(audit_path)], stdout=stdout)

    assert exit_code == 0
    output = stdout.getvalue()
    assert output.startswith("AICO needs approval: agents=1 open=1 running=0 waiting=1 failed=0")
    assert "- task-app [claude-code] waiting_approval" in output
    assert "/approve task-app" in output
    assert "/reject task-app" in output


def test_glance_cli_outputs_json_from_env_audit_log(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    audit_path = tmp_path / "audit.jsonl"
    _write_audit_events(audit_path)
    monkeypatch.setenv("AICO_AUDIT_LOG_PATH", str(audit_path))
    stdout = StringIO()

    exit_code = run(["--format", "json"], stdout=stdout)

    assert exit_code == 0
    payload = json.loads(stdout.getvalue())
    assert payload["title"] == "AICO needs approval"
    assert payload["recent_tasks"][0]["commands"] == [
        "/task task-app",
        "/approve task-app",
        "/reject task-app",
    ]


def _write_audit_events(path: Path) -> None:
    base_time = datetime.now(UTC) - timedelta(minutes=1)
    events = (
        _event(
            "event-1",
            AuditEventType.TASK_SUBMITTED,
            timestamp=base_time,
            adapter_name="claude-code",
            risk_level=RiskLevel.WRITE_FILES,
        ),
        _event(
            "event-2",
            AuditEventType.APPROVAL_REQUESTED,
            timestamp=base_time + timedelta(seconds=30),
            adapter_name="claude-code",
            risk_level=RiskLevel.WRITE_FILES,
            detail="approval required",
        ),
    )
    path.write_text(
        "\n".join(event.model_dump_json() for event in events) + "\n",
        encoding="utf-8",
    )


def _event(
    event_id: str,
    event_type: AuditEventType,
    *,
    timestamp: datetime,
    adapter_name: str | None = None,
    risk_level: RiskLevel = RiskLevel.READ_ONLY,
    detail: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        event_type=event_type,
        task_id="task-approval",
        actor_id="user-1",
        target_persona="implementer",
        adapter_name=adapter_name,
        risk_level=risk_level,
        detail=detail,
        timestamp=timestamp,
    )
