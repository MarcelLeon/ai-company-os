"""Local observability summaries for IM-first dashboards."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from aico.core.models import AuditEvent, AuditEventType, TaskSnapshot, TaskStatus, utc_now


@dataclass(frozen=True)
class MetricsWindow:
    label: str
    duration: timedelta


@dataclass(frozen=True)
class MetricsSummary:
    window: MetricsWindow
    total_tasks: int
    status_counts: tuple[tuple[TaskStatus, int], ...]
    adapter_counts: tuple[tuple[str, int], ...]
    collaboration_requests: int
    avg_terminal_seconds: float | None
    open_tasks: tuple[TaskSnapshot, ...]


DEFAULT_METRICS_WINDOWS = (
    MetricsWindow(label="24h", duration=timedelta(hours=24)),
    MetricsWindow(label="7d", duration=timedelta(days=7)),
)
OPEN_STATUSES = (TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL)
TERMINAL_STATUSES = (
    TaskStatus.DONE,
    TaskStatus.FAILED,
    TaskStatus.INTERRUPTED,
    TaskStatus.REJECTED,
)


def build_metrics_summaries(
    task_snapshots: tuple[TaskSnapshot, ...],
    audit_events: tuple[AuditEvent, ...],
    *,
    now: datetime | None = None,
    windows: tuple[MetricsWindow, ...] = DEFAULT_METRICS_WINDOWS,
) -> tuple[MetricsSummary, ...]:
    effective_now = now or utc_now()
    return tuple(
        _build_window_summary(task_snapshots, audit_events, window, effective_now)
        for window in windows
    )


def _build_window_summary(
    task_snapshots: tuple[TaskSnapshot, ...],
    audit_events: tuple[AuditEvent, ...],
    window: MetricsWindow,
    now: datetime,
) -> MetricsSummary:
    cutoff = now - window.duration
    tasks = tuple(snapshot for snapshot in task_snapshots if snapshot.updated_at >= cutoff)
    collaborations = tuple(
        event
        for event in audit_events
        if event.event_type is AuditEventType.COLLABORATION_REQUESTED and event.timestamp >= cutoff
    )
    return MetricsSummary(
        window=window,
        total_tasks=len(tasks),
        status_counts=_status_counts(tasks),
        adapter_counts=_adapter_counts(tasks),
        collaboration_requests=len(collaborations),
        avg_terminal_seconds=_avg_terminal_seconds(tasks),
        open_tasks=_open_tasks(tasks),
    )


def _status_counts(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[tuple[TaskStatus, int], ...]:
    counts = Counter(snapshot.status for snapshot in task_snapshots)
    return tuple((status, counts[status]) for status in TaskStatus)


def _adapter_counts(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[tuple[str, int], ...]:
    counts = Counter(
        snapshot.adapter_name or snapshot.target_persona for snapshot in task_snapshots
    )
    return tuple(sorted(counts.items()))


def _avg_terminal_seconds(task_snapshots: tuple[TaskSnapshot, ...]) -> float | None:
    durations = tuple(
        (snapshot.updated_at - snapshot.created_at).total_seconds()
        for snapshot in task_snapshots
        if snapshot.status in TERMINAL_STATUSES
    )
    if not durations:
        return None
    return sum(durations) / len(durations)


def _open_tasks(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[TaskSnapshot, ...]:
    tasks = tuple(snapshot for snapshot in task_snapshots if snapshot.status in OPEN_STATUSES)
    return tuple(sorted(tasks, key=lambda snapshot: snapshot.updated_at, reverse=True)[:5])
