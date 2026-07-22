"""Approval policies for risky remote task execution."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from aico.core.audit import InMemoryAuditLog
from aico.core.authorization_clock import (
    AUTHORIZATION_CLOCK_ROLLBACK_REASON,
    AuthorizationClockGuard,
)
from aico.core.models import (
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    AuditEventType,
    RiskAssessment,
    Task,
    TaskStatus,
    utc_now,
)
from aico.core.task_state import APPROVAL_EXPIRED_REASON, TaskStateRepository

DEFAULT_APPROVAL_MAX_AGE_SECONDS = 86_400
MIN_APPROVAL_MAX_AGE_SECONDS = 300
MAX_APPROVAL_MAX_AGE_SECONDS = 604_800


@dataclass(frozen=True)
class ApprovalDecision:
    allowed: bool
    reason: str | None = None


class ApprovalPolicy(Protocol):
    """Decide whether a reviewer may approve or reject a pending task."""

    def can_review(
        self,
        approval: ApprovalRequest,
        reviewer_id: str,
    ) -> ApprovalDecision: ...


class RequesterOrListedApproverPolicy:
    """Allow the requester and configured reviewers to resolve approvals."""

    def __init__(self, reviewer_ids: Iterable[str] = ()) -> None:
        self._reviewer_ids = frozenset(
            reviewer_id.strip() for reviewer_id in reviewer_ids if reviewer_id.strip()
        )

    def can_review(
        self,
        approval: ApprovalRequest,
        reviewer_id: str,
    ) -> ApprovalDecision:
        if reviewer_id == approval.task.requester_id:
            return ApprovalDecision(allowed=True)
        if reviewer_id in self._reviewer_ids:
            return ApprovalDecision(allowed=True)
        return ApprovalDecision(allowed=False, reason="approver not authorized")


class ApprovalLeaseCoordinator:
    """Own bounded approval timestamps, expiry reconciliation, and audit delivery."""

    def __init__(
        self,
        state: TaskStateRepository,
        audit_log: InMemoryAuditLog,
        *,
        max_age_seconds: int = DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        durable: bool = False,
        clock: Callable[[], datetime] = utc_now,
        authorization_clock: AuthorizationClockGuard | None = None,
    ) -> None:
        if not MIN_APPROVAL_MAX_AGE_SECONDS <= max_age_seconds <= MAX_APPROVAL_MAX_AGE_SECONDS:
            raise ValueError("approval max age is outside the supported range")
        self._state = state
        self._audit_log = audit_log
        self._max_age_seconds = max_age_seconds
        self._durable = durable
        self._clock = clock
        self._authorization_clock = authorization_clock or AuthorizationClockGuard(clock=clock)
        self._authorization_time_refusal: str | None = None

    def new_request(self, task: Task, risk: RiskAssessment) -> ApprovalRequest:
        now = self._clock()
        return ApprovalRequest(
            task=task,
            risk=risk,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(seconds=self._max_age_seconds),
        )

    def resolve(
        self,
        approval: ApprovalRequest,
        status: ApprovalStatus,
        *,
        reviewer_id: str | None = None,
        reason: str | None = None,
    ) -> ApprovalRequest:
        resolved = approval.model_copy(
            update={
                "status": status,
                "reviewer_id": reviewer_id,
                "reason": reason,
                "updated_at": self._clock(),
            }
        )
        self._state.save_approval(resolved)
        return resolved

    def sweep(self) -> int:
        observation = self._authorization_clock.observe()
        now = observation.observed_at
        self._authorization_time_refusal = (
            AUTHORIZATION_CLOCK_ROLLBACK_REASON if observation.rolled_back else None
        )
        reason = self._authorization_time_refusal or APPROVAL_EXPIRED_REASON
        if self._durable:
            events = self._state.reconcile_expired_approvals(
                now=now,
                max_age_seconds=self._max_age_seconds,
                reason=reason,
                force=observation.rolled_back,
            )
            self.deliver_reconciliation_events(events)
            return sum(event.event_type is AuditEventType.APPROVAL_EXPIRED for event in events)
        cutoff = now - timedelta(seconds=self._max_age_seconds)
        expired = tuple(
            approval
            for approval in self._state.pending_approvals()
            if observation.rolled_back or _approval_expired(approval, now, cutoff)
        )
        for approval in expired:
            self._expire_in_memory(approval, now, reason)
        return len(expired)

    def authorization_time_refusal(self) -> str | None:
        self.sweep()
        return self._authorization_time_refusal

    def deliver_reconciliation_events(self, events: tuple[AuditEvent, ...]) -> None:
        for event in events:
            self._audit_log.record_existing(event)
            self._state.mark_recovery_audit_delivered(event.event_id)

    def _expire_in_memory(
        self,
        approval: ApprovalRequest,
        now: datetime,
        reason: str,
    ) -> None:
        self._state.save_approval(
            approval.model_copy(
                update={
                    "status": ApprovalStatus.EXPIRED,
                    "reason": reason,
                    "updated_at": now,
                }
            )
        )
        self._state.update_task(
            approval.task.task_id,
            TaskStatus.REJECTED,
            reason=reason,
            now=now,
        )
        self._audit_log.record(
            AuditEventType.APPROVAL_EXPIRED,
            approval.task,
            actor_id="aico-policy",
            adapter_name=self._state.task_adapters.get(approval.task.task_id),
            risk_level=approval.risk.risk_level,
            detail=reason,
        )


def _approval_expired(
    approval: ApprovalRequest,
    now: datetime,
    legacy_cutoff: datetime,
) -> bool:
    if approval.expires_at is not None:
        return approval.expires_at.tzinfo is None or approval.expires_at <= now
    return approval.created_at.tzinfo is None or approval.created_at <= legacy_cutoff
