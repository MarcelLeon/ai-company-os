"""Approval policies for risky remote task execution."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from aico.core.models import ApprovalRequest


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
