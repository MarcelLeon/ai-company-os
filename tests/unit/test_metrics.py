from datetime import UTC, datetime, timedelta
from typing import cast

from aico.core import (
    AuditEvent,
    AuditEventType,
    RiskLevel,
    TaskSnapshot,
    TaskStatus,
    build_metrics_report,
    build_metrics_summaries,
    metrics_report_to_dict,
    task_snapshots_from_audit_events,
    usage_audit_detail,
    usage_records_from_audit_events,
)


def test_task_snapshots_from_audit_events_reconstructs_latest_status() -> None:
    base_time = datetime(2026, 5, 7, 9, 0, tzinfo=UTC)
    events = (
        _event(
            "event-1",
            AuditEventType.TASK_SUBMITTED,
            timestamp=base_time,
            adapter_name="claude-code",
            risk_level=RiskLevel.WRITE_FILES,
            detail=None,
        ),
        _event(
            "event-2",
            AuditEventType.APPROVAL_REQUESTED,
            timestamp=base_time + timedelta(seconds=5),
            adapter_name="claude-code",
            risk_level=RiskLevel.WRITE_FILES,
            detail="approval required",
        ),
        _event(
            "event-3",
            AuditEventType.ADAPTER_DISPATCHED,
            timestamp=base_time + timedelta(seconds=10),
            adapter_name="claude-code",
            risk_level=RiskLevel.WRITE_FILES,
            detail=None,
        ),
        _event(
            "event-4",
            AuditEventType.TASK_COMPLETED,
            timestamp=base_time + timedelta(seconds=20),
            adapter_name="claude-code",
            risk_level=RiskLevel.WRITE_FILES,
            detail=None,
        ),
    )

    snapshots = task_snapshots_from_audit_events(events)

    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.task_id == "task-1"
    assert snapshot.adapter_name == "claude-code"
    assert snapshot.status is TaskStatus.DONE
    assert snapshot.risk_level is RiskLevel.WRITE_FILES
    assert snapshot.created_at == base_time
    assert snapshot.updated_at == base_time + timedelta(seconds=20)


def test_metrics_summaries_include_audit_reconstructed_tasks_after_restart() -> None:
    base_time = datetime(2026, 5, 7, 9, 0, tzinfo=UTC)
    restored_events = (
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
    live_snapshot = TaskSnapshot(
        task_id="task-2",
        target_persona="reviewer",
        adapter_name="codex",
        status=TaskStatus.WAITING_APPROVAL,
        created_at=base_time + timedelta(minutes=1),
        updated_at=base_time + timedelta(minutes=1),
    )

    summaries = build_metrics_summaries(
        (live_snapshot,),
        restored_events,
        now=base_time + timedelta(minutes=2),
    )

    day = summaries[0]
    assert day.total_tasks == 2
    assert dict(day.adapter_counts) == {"claude-code": 1, "codex": 1}
    assert dict(day.status_counts)[TaskStatus.DONE] == 1
    assert dict(day.status_counts)[TaskStatus.WAITING_APPROVAL] == 1
    assert day.avg_terminal_seconds == 30
    assert [snapshot.task_id for snapshot in day.open_tasks] == ["task-2"]


def test_metrics_report_exposes_glance_for_status_island_consumers() -> None:
    base_time = datetime(2026, 5, 7, 9, 0, tzinfo=UTC)
    snapshots = (
        TaskSnapshot(
            task_id="task-running",
            target_persona="implementer",
            adapter_name="claude-code",
            status=TaskStatus.RUNNING,
            created_at=base_time,
            updated_at=base_time,
        ),
        TaskSnapshot(
            task_id="task-approval",
            target_persona="reviewer",
            adapter_name="codex",
            status=TaskStatus.WAITING_APPROVAL,
            created_at=base_time,
            updated_at=base_time + timedelta(seconds=1),
        ),
        TaskSnapshot(
            task_id="task-failed",
            target_persona="implementer",
            adapter_name="claude-code",
            status=TaskStatus.FAILED,
            created_at=base_time,
            updated_at=base_time + timedelta(seconds=2),
        ),
    )

    report = build_metrics_report(snapshots, (), now=base_time + timedelta(minutes=1))

    assert report.source_label == "local state + audit replay"
    assert report.glance.status == "needs_approval"
    assert report.glance.open_tasks == 2
    assert report.glance.running_tasks == 1
    assert report.glance.waiting_approval_tasks == 1
    assert report.glance.failed_tasks == 1
    assert report.token_cost.available is False
    assert report.token_cost.reason == "unavailable from current CLI adapters"
    assert [task.task_id for task in report.recent_tasks] == [
        "task-failed",
        "task-approval",
        "task-running",
    ]


def test_metrics_report_to_dict_serializes_enums_and_datetimes() -> None:
    base_time = datetime(2026, 5, 7, 9, 0, tzinfo=UTC)
    snapshot = TaskSnapshot(
        task_id="task-approval",
        target_persona="reviewer",
        adapter_name="codex",
        status=TaskStatus.WAITING_APPROVAL,
        risk_level=RiskLevel.WRITE_FILES,
        created_at=base_time,
        updated_at=base_time + timedelta(seconds=5),
    )
    report = build_metrics_report((snapshot,), (), now=base_time + timedelta(minutes=1))

    payload = metrics_report_to_dict(report)

    assert payload["generated_at"] == "2026-05-07T09:01:00+00:00"
    assert payload["glance"] == {
        "status": "needs_approval",
        "open_tasks": 1,
        "running_tasks": 0,
        "waiting_approval_tasks": 1,
        "failed_tasks": 0,
    }
    summaries = payload["summaries"]
    assert isinstance(summaries, list)
    first_summary = cast(dict[str, object], summaries[0])
    status_counts = cast(dict[str, int], first_summary["status_counts"])
    open_tasks = cast(list[dict[str, object]], first_summary["open_tasks"])
    assert status_counts["waiting_approval"] == 1
    assert open_tasks[0]["risk_level"] == "write_files"
    recent_tasks = cast(list[dict[str, object]], payload["recent_tasks"])
    assert recent_tasks[0]["task_id"] == "task-approval"


def test_usage_records_from_audit_events_feed_token_cost_summary() -> None:
    base_time = datetime(2026, 5, 7, 9, 0, tzinfo=UTC)
    events = (
        _event(
            "event-usage-1",
            AuditEventType.TASK_USAGE_RECORDED,
            timestamp=base_time,
            adapter_name="claude-code",
            detail=usage_audit_detail(input_tokens=10, output_tokens=20, cost_usd=0.03),
        ),
        _event(
            "event-usage-2",
            AuditEventType.TASK_USAGE_RECORDED,
            timestamp=base_time,
            adapter_name="codex",
            detail=usage_audit_detail(input_tokens=5, output_tokens=7),
        ),
    )

    records = usage_records_from_audit_events(events)
    report = build_metrics_report((), events, now=base_time + timedelta(minutes=1))

    assert [record.total_tokens for record in records] == [30, 12]
    assert report.token_cost.available is True
    assert report.token_cost.input_tokens == 15
    assert report.token_cost.output_tokens == 27
    assert report.token_cost.total_tokens == 42
    assert report.token_cost.cost_usd == 0.03


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
        task_id="task-1",
        actor_id="user-1",
        target_persona="implementer",
        adapter_name=adapter_name,
        risk_level=risk_level,
        detail=detail,
        timestamp=timestamp,
    )
