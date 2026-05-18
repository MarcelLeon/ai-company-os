"""Compact local glance model for macOS-style status surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from aico.core.command_messages import short_id_text
from aico.core.metrics import MetricsReport
from aico.core.models import TaskSnapshot, TaskStatus


@dataclass(frozen=True)
class StatusIslandTask:
    task_id: str
    short_id: str
    target_persona: str
    adapter_name: str | None
    status: str
    risk_level: str
    age_seconds: int
    commands: tuple[str, ...]


@dataclass(frozen=True)
class StatusIslandSnapshot:
    title: str
    status: str
    active_agents: int
    open_tasks: int
    running_tasks: int
    waiting_approval_tasks: int
    failed_tasks: int
    recent_tasks: tuple[StatusIslandTask, ...]


def build_status_island_snapshot(
    report: MetricsReport,
    *,
    max_tasks: int = 5,
) -> StatusIslandSnapshot:
    return StatusIslandSnapshot(
        title=_title_for_status(report.glance.status),
        status=report.glance.status,
        active_agents=_active_agents(report),
        open_tasks=report.glance.open_tasks,
        running_tasks=report.glance.running_tasks,
        waiting_approval_tasks=report.glance.waiting_approval_tasks,
        failed_tasks=report.glance.failed_tasks,
        recent_tasks=tuple(
            _status_island_task(report, task) for task in report.recent_tasks[:max_tasks]
        ),
    )


def status_island_to_dict(snapshot: StatusIslandSnapshot) -> dict[str, object]:
    return {
        "title": snapshot.title,
        "status": snapshot.status,
        "active_agents": snapshot.active_agents,
        "open_tasks": snapshot.open_tasks,
        "running_tasks": snapshot.running_tasks,
        "waiting_approval_tasks": snapshot.waiting_approval_tasks,
        "failed_tasks": snapshot.failed_tasks,
        "recent_tasks": [
            {
                "task_id": task.task_id,
                "short_id": task.short_id,
                "target_persona": task.target_persona,
                "adapter_name": task.adapter_name,
                "status": task.status,
                "risk_level": task.risk_level,
                "age_seconds": task.age_seconds,
                "commands": list(task.commands),
            }
            for task in snapshot.recent_tasks
        ],
    }


def status_island_text(snapshot: StatusIslandSnapshot) -> str:
    lines = [
        (
            f"{snapshot.title}: agents={snapshot.active_agents} "
            f"open={snapshot.open_tasks} running={snapshot.running_tasks} "
            f"waiting={snapshot.waiting_approval_tasks} failed={snapshot.failed_tasks}"
        )
    ]
    if not snapshot.recent_tasks:
        lines.append("tasks: none")
        return "\n".join(lines)
    lines.append("tasks:")
    lines.extend(_task_line(task) for task in snapshot.recent_tasks)
    return "\n".join(lines)


def _active_agents(report: MetricsReport) -> int:
    if not report.summaries:
        return 0
    return len(report.summaries[0].adapter_counts)


def _status_island_task(report: MetricsReport, task: TaskSnapshot) -> StatusIslandTask:
    return StatusIslandTask(
        task_id=task.task_id,
        short_id=short_id_text(task.task_id),
        target_persona=task.target_persona,
        adapter_name=task.adapter_name,
        status=task.status.value,
        risk_level=task.risk_level.value,
        age_seconds=max(0, int((report.generated_at - task.updated_at).total_seconds())),
        commands=_commands_for_task(task),
    )


def _commands_for_task(task: TaskSnapshot) -> tuple[str, ...]:
    short_id = short_id_text(task.task_id)
    commands = [f"/task {short_id}"]
    if task.status is TaskStatus.WAITING_APPROVAL:
        commands.extend((f"/approve {short_id}", f"/reject {short_id}"))
    elif task.status is TaskStatus.RUNNING:
        commands.append(f"/interrupt {short_id}")
    return tuple(commands)


def _task_line(task: StatusIslandTask) -> str:
    owner = task.adapter_name or task.target_persona
    commands = ", ".join(task.commands)
    return f"- {task.short_id} [{owner}] {task.status} {task.age_seconds}s ago -> {commands}"


def _title_for_status(status: str) -> str:
    if status == "needs_approval":
        return "AICO needs approval"
    if status == "working":
        return "AICO working"
    if status == "attention":
        return "AICO needs attention"
    return "AICO quiet"
