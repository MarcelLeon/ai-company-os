import json
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

from pytest import MonkeyPatch

from aico.app.metrics_cli import run
from aico.core import AuditEvent, AuditEventType, RiskLevel


def test_metrics_cli_outputs_text_from_audit_log(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    _write_audit_events(audit_path)
    stdout = StringIO()

    exit_code = run(["--audit-log", str(audit_path)], stdout=stdout)

    assert exit_code == 0
    output = stdout.getvalue()
    assert output.startswith("Metrics (local state + audit replay)\n\n")
    assert "glance\nstatus: quiet\nopen: 0 (running=0, waiting_approval=0)\nfailed: 0" in output
    assert "tasks: 1\n" in output
    assert "done=1" in output
    assert "agents: claude-code=1" in output
    assert "token/cost: unavailable from current CLI adapters" in output


def test_metrics_cli_outputs_json_from_env_audit_log(
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
    assert payload["source"] == "local state + audit replay"
    assert payload["glance"]["status"] == "quiet"
    assert payload["summaries"][0]["status_counts"]["done"] == 1
    assert payload["token_cost"]["available"] is False


def _write_audit_events(path: Path) -> None:
    base_time = datetime.now(UTC) - timedelta(minutes=1)
    events = (
        _event(
            "event-1",
            AuditEventType.TASK_SUBMITTED,
            timestamp=base_time,
            adapter_name="claude-code",
        ),
        _event(
            "event-2",
            AuditEventType.TASK_COMPLETED,
            timestamp=base_time + timedelta(seconds=30),
            adapter_name="claude-code",
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
) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        event_type=event_type,
        task_id="task-1",
        actor_id="user-1",
        target_persona="implementer",
        adapter_name=adapter_name,
        risk_level=RiskLevel.READ_ONLY,
        timestamp=timestamp,
    )
