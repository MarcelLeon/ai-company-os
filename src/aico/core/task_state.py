"""TaskBus state repository and persistence bridge."""

from __future__ import annotations

from aico.core.models import (
    AckStatus,
    ApprovalRequest,
    ApprovalStatus,
    RiskLevel,
    Task,
    TaskAck,
    TaskSnapshot,
    TaskStatus,
    utc_now,
)
from aico.core.task_store import TaskStateStore


class TaskStateRepository:
    """Own restart-recoverable task, snapshot, approval, and adapter state."""

    def __init__(self, store: TaskStateStore | None = None) -> None:
        self._store = store
        self.task_records: dict[str, Task] = {
            task.task_id: task for task in self._load_task_records()
        }
        self.tasks: dict[str, TaskSnapshot] = {
            snapshot.task_id: snapshot for snapshot in self._load_task_snapshots()
        }
        self.approvals: dict[str, ApprovalRequest] = {
            approval.task.task_id: approval for approval in self._load_approvals()
        }
        self.task_adapters: dict[str, str] = {
            snapshot.task_id: snapshot.adapter_name
            for snapshot in self.tasks.values()
            if snapshot.adapter_name is not None
        }

    def record_task(self, task: Task) -> None:
        self.task_records[task.task_id] = task
        if self._store is not None:
            self._store.upsert_task_record(task)

    def record_snapshot(
        self,
        task: Task,
        *,
        status: TaskStatus,
        adapter_name: str | None = None,
        reason: str | None = None,
        risk_level: RiskLevel = RiskLevel.READ_ONLY,
    ) -> None:
        snapshot = TaskSnapshot(
            task_id=task.task_id,
            target_persona=task.target_persona,
            adapter_name=adapter_name,
            status=status,
            reason=reason,
            risk_level=risk_level,
            metadata=task.metadata,
            created_at=task.created_at,
        )
        self.tasks[task.task_id] = snapshot
        self._save_snapshot(snapshot)

    def update_task(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        reason: str | None = None,
    ) -> TaskSnapshot | None:
        snapshot = self.tasks.get(task_id)
        if snapshot is None:
            return None
        updated = snapshot.model_copy(
            update={
                "status": status,
                "reason": reason,
                "updated_at": utc_now(),
            }
        )
        self.tasks[task_id] = updated
        self._save_snapshot(updated)
        return updated

    def save_approval(self, approval: ApprovalRequest) -> None:
        self.approvals[approval.task.task_id] = approval
        if self._store is not None:
            self._store.upsert_approval(approval)

    def task_status(self, task_id: str) -> TaskStatus | None:
        snapshot = self.tasks.get(task_id)
        return None if snapshot is None else snapshot.status

    def task_snapshots(self, *, limit: int | None = 5) -> tuple[TaskSnapshot, ...]:
        snapshots = sorted(
            self.tasks.values(),
            key=lambda snapshot: snapshot.updated_at,
            reverse=True,
        )
        if limit is None:
            return tuple(reversed(snapshots))
        return tuple(reversed(snapshots[:limit]))

    def resolve_known_task(self, task_ref: str) -> TaskSnapshot | TaskAck:
        if task_ref in self.tasks:
            return self.tasks[task_ref]
        matches = tuple(
            snapshot for task_id, snapshot in self.tasks.items() if task_id.startswith(task_ref)
        )
        if len(matches) == 1:
            return matches[0]
        if matches:
            return TaskAck(
                task_id=task_ref,
                status=AckStatus.REJECTED,
                reason=f"multiple matching tasks: {_task_refs(matches)}",
            )
        return TaskAck(
            task_id=task_ref,
            status=AckStatus.REJECTED,
            reason=f"unknown task: {task_ref}",
        )

    def pending_approvals(self) -> tuple[ApprovalRequest, ...]:
        return tuple(
            approval
            for approval in self.approvals.values()
            if approval.status is ApprovalStatus.PENDING
        )

    def resolve_pending_approval(self, task_ref: str | None) -> ApprovalRequest | TaskAck:
        pending = self.pending_approvals()
        if not task_ref:
            if len(pending) == 1:
                return pending[0]
            if not pending:
                return TaskAck(
                    task_id="approval",
                    status=AckStatus.REJECTED,
                    reason="no pending approvals",
                )
            return TaskAck(
                task_id="approval",
                status=AckStatus.REJECTED,
                reason=f"multiple pending approvals: {_pending_task_refs(pending)}",
            )

        matches = [approval for approval in pending if approval.task.task_id.startswith(task_ref)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return TaskAck(
                task_id=task_ref,
                status=AckStatus.REJECTED,
                reason=f"multiple pending approvals match: {_pending_task_refs(matches)}",
            )
        return TaskAck(
            task_id=task_ref,
            status=AckStatus.REJECTED,
            reason="unknown pending approval",
        )

    def _load_task_records(self) -> tuple[Task, ...]:
        return () if self._store is None else self._store.load_task_records()

    def _load_task_snapshots(self) -> tuple[TaskSnapshot, ...]:
        return () if self._store is None else self._store.load_task_snapshots()

    def _load_approvals(self) -> tuple[ApprovalRequest, ...]:
        return () if self._store is None else self._store.load_approvals()

    def _save_snapshot(self, snapshot: TaskSnapshot) -> None:
        if self._store is not None:
            self._store.upsert_task_snapshot(snapshot)


def _pending_task_refs(approvals: tuple[ApprovalRequest, ...] | list[ApprovalRequest]) -> str:
    return ", ".join(_short_task_id(approval.task.task_id) for approval in approvals)


def _task_refs(tasks: tuple[TaskSnapshot, ...]) -> str:
    return ", ".join(_short_task_id(task.task_id) for task in tasks)


def _short_task_id(task_id: str) -> str:
    return task_id[:8]
