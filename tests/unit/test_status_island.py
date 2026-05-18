from datetime import UTC, datetime, timedelta
from typing import cast

from aico.core import (
    RiskLevel,
    TaskSnapshot,
    TaskStatus,
    build_metrics_report,
    build_status_island_snapshot,
    status_island_text,
    status_island_to_dict,
)


def test_status_island_snapshot_exposes_glance_and_actions() -> None:
    base_time = datetime(2026, 5, 7, 9, 0, tzinfo=UTC)
    report = build_metrics_report(
        (
            TaskSnapshot(
                task_id="task-approval",
                target_persona="implementer",
                adapter_name="claude-code",
                status=TaskStatus.WAITING_APPROVAL,
                risk_level=RiskLevel.WRITE_FILES,
                created_at=base_time,
                updated_at=base_time + timedelta(seconds=5),
            ),
            TaskSnapshot(
                task_id="task-running",
                target_persona="reviewer",
                adapter_name="codex",
                status=TaskStatus.RUNNING,
                created_at=base_time,
                updated_at=base_time + timedelta(seconds=10),
            ),
        ),
        (),
        now=base_time + timedelta(seconds=20),
    )

    snapshot = build_status_island_snapshot(report)

    assert snapshot.title == "AICO needs approval"
    assert snapshot.status == "needs_approval"
    assert snapshot.active_agents == 2
    assert snapshot.open_tasks == 2
    assert snapshot.waiting_approval_tasks == 1
    assert snapshot.running_tasks == 1
    assert [task.short_id for task in snapshot.recent_tasks] == ["task-run", "task-app"]
    assert snapshot.recent_tasks[0].commands == ("/task task-run", "/interrupt task-run")
    assert snapshot.recent_tasks[1].commands == (
        "/task task-app",
        "/approve task-app",
        "/reject task-app",
    )


def test_status_island_text_and_json_are_menu_bar_friendly() -> None:
    base_time = datetime(2026, 5, 7, 9, 0, tzinfo=UTC)
    report = build_metrics_report(
        (
            TaskSnapshot(
                task_id="task-failed",
                target_persona="implementer",
                adapter_name="claude-code",
                status=TaskStatus.FAILED,
                created_at=base_time,
                updated_at=base_time,
            ),
        ),
        (),
        now=base_time + timedelta(seconds=30),
    )
    snapshot = build_status_island_snapshot(report)

    assert status_island_text(snapshot).startswith(
        "AICO needs attention: agents=1 open=0 running=0 waiting=0 failed=1"
    )
    payload = status_island_to_dict(snapshot)
    assert payload["title"] == "AICO needs attention"
    recent_tasks = cast(list[dict[str, object]], payload["recent_tasks"])
    assert recent_tasks[0]["commands"] == ["/task task-fai"]
