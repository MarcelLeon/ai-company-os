import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aico.core import (
    ApprovalRequest,
    ApprovalStatus,
    AuditEventType,
    RiskAssessment,
    RiskLevel,
    Task,
    TaskSnapshot,
    TaskStatus,
)
from aico.core.task_store import SQLiteTaskStateStore


def _seed_running_task(store: SQLiteTaskStateStore) -> Task:
    task = Task(
        task_id="task-running",
        payload="publish result",
        requester_id="boss",
        target_persona="operator",
        trace_id="trace-running",
    )
    store.upsert_task_record(task)
    store.upsert_task_snapshot(
        TaskSnapshot(
            task_id=task.task_id,
            target_persona=task.target_persona,
            adapter_name="claude-code",
            status=TaskStatus.RUNNING,
            risk_level=RiskLevel.WRITE_FILES,
            created_at=task.created_at,
        )
    )
    return task


def test_reconcile_running_tasks_commits_snapshot_and_complete_audit_event(
    tmp_path: Path,
) -> None:
    store = SQLiteTaskStateStore(tmp_path / "state.db")
    task = _seed_running_task(store)

    updated = store.reconcile_running_tasks(reason="runtime recovery")
    pending = store.load_pending_recovery_audit_events()

    assert len(updated) == 1
    assert updated[0].status is TaskStatus.INTERRUPTED
    assert updated[0].reason == "runtime recovery"
    assert len(pending) == 1
    event = pending[0]
    assert event.event_id
    assert event.event_type is AuditEventType.TASK_INTERRUPTED
    assert event.task_id == task.task_id
    assert event.actor_id == task.requester_id
    assert event.target_persona == task.target_persona
    assert event.adapter_name == "claude-code"
    assert event.risk_level is RiskLevel.WRITE_FILES
    assert event.detail == "runtime recovery"
    assert event.trace_id == task.trace_id

    store.mark_recovery_audit_delivered(event.event_id)
    assert store.load_pending_recovery_audit_events() == ()


def test_reconcile_running_tasks_rolls_back_snapshot_when_outbox_insert_fails(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "state.db"
    store = SQLiteTaskStateStore(db_path)
    _seed_running_task(store)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_recovery_outbox_insert
            BEFORE INSERT ON task_recovery_audit_outbox
            BEGIN
                SELECT RAISE(ABORT, 'forced outbox failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="forced outbox failure"):
        store.reconcile_running_tasks(reason="runtime recovery")

    assert store.load_task_snapshots()[0].status is TaskStatus.RUNNING
    assert store.load_pending_recovery_audit_events() == ()


def test_reconcile_expired_approvals_is_atomic_with_audit_outbox(tmp_path: Path) -> None:
    created_at = datetime(2026, 7, 22, 8, tzinfo=UTC)
    store = SQLiteTaskStateStore(tmp_path / "state.db", event_id_factory=lambda: "event-expired")
    task = _seed_waiting_approval(store, created_at)

    updated = store.reconcile_expired_approvals(
        expires_before=created_at,
        now=created_at + timedelta(seconds=300),
        reason="approval lease expired; submit a new task for fresh review",
    )
    pending = store.load_pending_recovery_audit_events()

    assert len(updated) == 1
    assert updated[0].approval.status is ApprovalStatus.EXPIRED
    assert updated[0].snapshot is not None
    assert updated[0].snapshot.status is TaskStatus.REJECTED
    assert store.load_approvals()[0].status is ApprovalStatus.EXPIRED
    assert store.load_task_snapshots()[0].status is TaskStatus.REJECTED
    assert len(pending) == 1
    assert pending[0].event_type is AuditEventType.APPROVAL_EXPIRED
    assert pending[0].task_id == task.task_id
    assert pending[0].actor_id == "aico-policy"


def test_reconcile_expired_approvals_rolls_back_all_state_when_outbox_fails(
    tmp_path: Path,
) -> None:
    created_at = datetime(2026, 7, 22, 8, tzinfo=UTC)
    db_path = tmp_path / "state.db"
    store = SQLiteTaskStateStore(db_path)
    _seed_waiting_approval(store, created_at)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_expiry_outbox_insert
            BEFORE INSERT ON task_recovery_audit_outbox
            BEGIN
                SELECT RAISE(ABORT, 'forced expiry outbox failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="forced expiry outbox failure"):
        store.reconcile_expired_approvals(
            expires_before=created_at,
            now=created_at + timedelta(seconds=300),
            reason="approval expired",
        )

    assert store.load_approvals()[0].status is ApprovalStatus.PENDING
    assert store.load_task_snapshots()[0].status is TaskStatus.WAITING_APPROVAL
    assert store.load_pending_recovery_audit_events() == ()


def _seed_waiting_approval(store: SQLiteTaskStateStore, created_at: datetime) -> Task:
    task = Task(
        task_id="task-approval-expiry",
        payload="publish result",
        requester_id="boss",
        target_persona="operator",
        trace_id="trace-approval-expiry",
        created_at=created_at,
    )
    risk = RiskAssessment(risk_level=RiskLevel.WRITE_FILES, requires_approval=True)
    store.upsert_task_record(task)
    store.upsert_task_snapshot(
        TaskSnapshot(
            task_id=task.task_id,
            target_persona=task.target_persona,
            adapter_name="claude-code",
            status=TaskStatus.WAITING_APPROVAL,
            risk_level=risk.risk_level,
            created_at=created_at,
            updated_at=created_at,
        )
    )
    store.upsert_approval(
        ApprovalRequest(
            task=task,
            risk=risk,
            created_at=created_at,
            updated_at=created_at,
        )
    )
    return task
