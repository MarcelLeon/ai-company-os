"""Local observability summaries for IM-first dashboards."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from aico.core.models import (
    AuditEvent,
    AuditEventType,
    RiskLevel,
    TaskSnapshot,
    TaskStatus,
    utc_now,
)


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


@dataclass(frozen=True)
class TokenCostSummary:
    available: bool
    reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None


@dataclass(frozen=True)
class UsageRecord:
    task_id: str
    adapter_name: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float | None = None


@dataclass(frozen=True)
class MetricsGlance:
    status: str
    open_tasks: int
    running_tasks: int
    waiting_approval_tasks: int
    failed_tasks: int


@dataclass(frozen=True)
class MetricsReport:
    generated_at: datetime
    source_label: str
    summaries: tuple[MetricsSummary, ...]
    glance: MetricsGlance
    token_cost: TokenCostSummary
    recent_tasks: tuple[TaskSnapshot, ...]


DEFAULT_METRICS_WINDOWS = (
    MetricsWindow(label="24h", duration=timedelta(hours=24)),
    MetricsWindow(label="7d", duration=timedelta(days=7)),
)
DEFAULT_METRICS_SOURCE_LABEL = "local state + audit replay"
TOKEN_COST_UNAVAILABLE_REASON = "unavailable from current CLI adapters"
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
    return build_metrics_report(
        task_snapshots,
        audit_events,
        now=now,
        windows=windows,
    ).summaries


def build_metrics_report(
    task_snapshots: tuple[TaskSnapshot, ...],
    audit_events: tuple[AuditEvent, ...],
    *,
    now: datetime | None = None,
    windows: tuple[MetricsWindow, ...] = DEFAULT_METRICS_WINDOWS,
) -> MetricsReport:
    effective_now = now or utc_now()
    merged_snapshots = merge_task_snapshots(
        task_snapshots,
        task_snapshots_from_audit_events(audit_events),
    )
    summaries = tuple(
        _build_window_summary(merged_snapshots, audit_events, window, effective_now)
        for window in windows
    )
    return MetricsReport(
        generated_at=effective_now,
        source_label=DEFAULT_METRICS_SOURCE_LABEL,
        summaries=summaries,
        glance=_build_glance(summaries),
        token_cost=_build_token_cost(usage_records_from_audit_events(audit_events)),
        recent_tasks=_recent_tasks(merged_snapshots),
    )


def metrics_report_to_dict(report: MetricsReport) -> dict[str, object]:
    return {
        "generated_at": report.generated_at.isoformat(),
        "source": report.source_label,
        "glance": {
            "status": report.glance.status,
            "open_tasks": report.glance.open_tasks,
            "running_tasks": report.glance.running_tasks,
            "waiting_approval_tasks": report.glance.waiting_approval_tasks,
            "failed_tasks": report.glance.failed_tasks,
        },
        "summaries": [_summary_to_dict(summary) for summary in report.summaries],
        "token_cost": {
            "available": report.token_cost.available,
            "reason": report.token_cost.reason,
            "input_tokens": report.token_cost.input_tokens,
            "output_tokens": report.token_cost.output_tokens,
            "total_tokens": report.token_cost.total_tokens,
            "cost_usd": report.token_cost.cost_usd,
        },
        "recent_tasks": [_task_snapshot_to_dict(snapshot) for snapshot in report.recent_tasks],
    }


def usage_audit_detail(
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int | None = None,
    cost_usd: float | None = None,
) -> str:
    effective_total = total_tokens if total_tokens is not None else input_tokens + output_tokens
    payload: dict[str, int | float | None] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": effective_total,
    }
    if cost_usd is not None:
        payload["cost_usd"] = cost_usd
    return json.dumps(payload, sort_keys=True)


def usage_records_from_audit_events(
    audit_events: tuple[AuditEvent, ...],
) -> tuple[UsageRecord, ...]:
    records: list[UsageRecord] = []
    for event in audit_events:
        if event.event_type is not AuditEventType.TASK_USAGE_RECORDED:
            continue
        record = _usage_record_from_event(event)
        if record is not None:
            records.append(record)
    return tuple(records)


def merge_task_snapshots(
    primary: tuple[TaskSnapshot, ...],
    fallback: tuple[TaskSnapshot, ...],
) -> tuple[TaskSnapshot, ...]:
    snapshots = {snapshot.task_id: snapshot for snapshot in fallback}
    snapshots.update({snapshot.task_id: snapshot for snapshot in primary})
    return tuple(snapshots.values())


def task_snapshots_from_audit_events(
    audit_events: tuple[AuditEvent, ...],
) -> tuple[TaskSnapshot, ...]:
    builders: dict[str, _SnapshotBuilder] = {}
    for event in audit_events:
        if event.task_id not in builders and not _starts_task_snapshot(event):
            continue
        builder = builders.setdefault(
            event.task_id,
            _SnapshotBuilder(
                task_id=event.task_id,
                target_persona=event.target_persona,
                created_at=event.timestamp,
            ),
        )
        builder.apply(event)
    return tuple(builder.to_snapshot() for builder in builders.values())


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


def _recent_tasks(task_snapshots: tuple[TaskSnapshot, ...]) -> tuple[TaskSnapshot, ...]:
    return tuple(sorted(task_snapshots, key=lambda snapshot: snapshot.updated_at, reverse=True)[:5])


def _build_token_cost(usage_records: tuple[UsageRecord, ...]) -> TokenCostSummary:
    if not usage_records:
        return TokenCostSummary(
            available=False,
            reason=TOKEN_COST_UNAVAILABLE_REASON,
        )
    input_tokens = sum(record.input_tokens for record in usage_records)
    output_tokens = sum(record.output_tokens for record in usage_records)
    total_tokens = sum(record.total_tokens for record in usage_records)
    costs = tuple(record.cost_usd for record in usage_records if record.cost_usd is not None)
    return TokenCostSummary(
        available=True,
        reason="reported by adapter audit events",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost_usd=sum(costs) if costs else None,
    )


def _build_glance(summaries: tuple[MetricsSummary, ...]) -> MetricsGlance:
    if not summaries:
        return MetricsGlance(
            status="quiet",
            open_tasks=0,
            running_tasks=0,
            waiting_approval_tasks=0,
            failed_tasks=0,
        )
    counts = dict(summaries[0].status_counts)
    running = counts[TaskStatus.RUNNING]
    waiting_approval = counts[TaskStatus.WAITING_APPROVAL]
    failed = counts[TaskStatus.FAILED]
    open_tasks = running + waiting_approval
    return MetricsGlance(
        status=_glance_status(running, waiting_approval, failed),
        open_tasks=open_tasks,
        running_tasks=running,
        waiting_approval_tasks=waiting_approval,
        failed_tasks=failed,
    )


def _glance_status(running: int, waiting_approval: int, failed: int) -> str:
    if waiting_approval:
        return "needs_approval"
    if running:
        return "working"
    if failed:
        return "attention"
    return "quiet"


def _summary_to_dict(summary: MetricsSummary) -> dict[str, object]:
    return {
        "window": {
            "label": summary.window.label,
            "seconds": int(summary.window.duration.total_seconds()),
        },
        "total_tasks": summary.total_tasks,
        "status_counts": {status.value: count for status, count in summary.status_counts},
        "adapter_counts": dict(summary.adapter_counts),
        "collaboration_requests": summary.collaboration_requests,
        "avg_terminal_seconds": summary.avg_terminal_seconds,
        "open_tasks": [_task_snapshot_to_dict(snapshot) for snapshot in summary.open_tasks],
    }


def _task_snapshot_to_dict(snapshot: TaskSnapshot) -> dict[str, object]:
    return {
        "task_id": snapshot.task_id,
        "target_persona": snapshot.target_persona,
        "adapter_name": snapshot.adapter_name,
        "status": snapshot.status.value,
        "reason": snapshot.reason,
        "risk_level": snapshot.risk_level.value,
        "created_at": snapshot.created_at.isoformat(),
        "updated_at": snapshot.updated_at.isoformat(),
    }


def _usage_record_from_event(event: AuditEvent) -> UsageRecord | None:
    if not event.detail:
        return None
    try:
        payload = json.loads(event.detail)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    input_tokens = _non_negative_int(payload.get("input_tokens"))
    output_tokens = _non_negative_int(payload.get("output_tokens"))
    total_tokens = _non_negative_int(payload.get("total_tokens"))
    cost_usd = _non_negative_float(payload.get("cost_usd"))
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None
    effective_input = input_tokens or 0
    effective_output = output_tokens or 0
    effective_total = (
        total_tokens if total_tokens is not None else effective_input + effective_output
    )
    return UsageRecord(
        task_id=event.task_id,
        adapter_name=event.adapter_name,
        input_tokens=effective_input,
        output_tokens=effective_output,
        total_tokens=effective_total,
        cost_usd=cost_usd,
    )


def _non_negative_int(value: object) -> int | None:
    if not isinstance(value, int) or value < 0:
        return None
    return value


def _non_negative_float(value: object) -> float | None:
    if isinstance(value, int | float) and value >= 0:
        return float(value)
    return None


@dataclass
class _SnapshotBuilder:
    task_id: str
    target_persona: str
    created_at: datetime
    updated_at: datetime | None = None
    adapter_name: str | None = None
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    status: TaskStatus = TaskStatus.RUNNING
    reason: str | None = None

    def apply(self, event: AuditEvent) -> None:
        self.updated_at = event.timestamp
        self.risk_level = event.risk_level
        if event.adapter_name is not None:
            self.adapter_name = event.adapter_name
        status = _status_from_event(event)
        if status is not None:
            self.status = status
            self.reason = _reason_from_event(event, status)

    def to_snapshot(self) -> TaskSnapshot:
        return TaskSnapshot(
            task_id=self.task_id,
            target_persona=self.target_persona,
            adapter_name=self.adapter_name,
            status=self.status,
            reason=self.reason,
            risk_level=self.risk_level,
            created_at=self.created_at,
            updated_at=self.updated_at or self.created_at,
        )


def _status_from_event(event: AuditEvent) -> TaskStatus | None:
    if event.event_type is AuditEventType.TASK_SUBMITTED:
        return TaskStatus.RUNNING
    if event.event_type is AuditEventType.APPROVAL_REQUESTED:
        return TaskStatus.WAITING_APPROVAL
    if event.event_type is AuditEventType.ADAPTER_DISPATCHED:
        return TaskStatus.RUNNING
    if event.event_type is AuditEventType.TASK_COMPLETED:
        return TaskStatus.DONE
    if event.event_type is AuditEventType.TASK_FAILED:
        return TaskStatus.FAILED
    if event.event_type is AuditEventType.TASK_INTERRUPTED:
        return TaskStatus.INTERRUPTED
    if event.event_type is AuditEventType.TASK_REJECTED:
        return TaskStatus.REJECTED
    return None


def _starts_task_snapshot(event: AuditEvent) -> bool:
    return event.event_type in {
        AuditEventType.TASK_SUBMITTED,
        AuditEventType.APPROVAL_REQUESTED,
        AuditEventType.ADAPTER_DISPATCHED,
        AuditEventType.TASK_COMPLETED,
        AuditEventType.TASK_FAILED,
        AuditEventType.TASK_INTERRUPTED,
        AuditEventType.TASK_REJECTED,
    }


def _reason_from_event(event: AuditEvent, status: TaskStatus) -> str | None:
    if status in {TaskStatus.FAILED, TaskStatus.REJECTED, TaskStatus.WAITING_APPROVAL}:
        return event.detail
    return None
