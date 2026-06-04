"""Minimal task bus that delegates work to an AI adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

from aico.adapter import AIAdapter
from aico.core.adapter_registry import AdapterRegistry
from aico.core.approval import ApprovalPolicy, RequesterOrListedApproverPolicy
from aico.core.audit import InMemoryAuditLog
from aico.core.models import (
    AckStatus,
    AdapterSnapshot,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    AuditEventType,
    OutputType,
    PersonaProfile,
    RiskAssessment,
    RiskLevel,
    Task,
    TaskAck,
    TaskOutput,
    TaskSnapshot,
    TaskStatus,
)
from aico.core.persona_registry import PersonaRegistry
from aico.core.risk import TextRiskAssessor
from aico.core.risk_capability import unsupported_risk_reason
from aico.core.task_state import TaskStateRepository
from aico.core.task_store import TaskStateStore


class TaskBus:
    """Submit tasks and expose adapter output without leaking adapter lookup."""

    def __init__(
        self,
        adapter: AIAdapter | AdapterRegistry,
        persona_registry: PersonaRegistry | None = None,
        risk_assessor: TextRiskAssessor | None = None,
        audit_log: InMemoryAuditLog | None = None,
        approval_policy: ApprovalPolicy | None = None,
        task_store: TaskStateStore | None = None,
    ) -> None:
        self._single_adapter_mode = not isinstance(adapter, AdapterRegistry)
        self._registry = (
            adapter if isinstance(adapter, AdapterRegistry) else AdapterRegistry([adapter])
        )
        self._persona_registry = persona_registry
        self._risk_assessor = risk_assessor or TextRiskAssessor()
        self._audit_log = audit_log or InMemoryAuditLog()
        self._approval_policy = approval_policy or RequesterOrListedApproverPolicy()
        self._task_store = task_store
        self._state = TaskStateRepository(task_store)

    async def submit(self, task: Task) -> TaskAck:
        adapter_name = self._adapter_name_for_task(task)
        adapter = self._registry.resolve(adapter_name)
        if adapter is None and self._single_adapter_mode:
            adapter = self._registry.default()
        if adapter is None:
            self._record_task(
                task,
                status=TaskStatus.REJECTED,
                reason=f"unknown adapter or persona: {adapter_name}",
            )
            self._audit_log.record(
                AuditEventType.TASK_REJECTED,
                task,
                detail=f"unknown adapter or persona: {adapter_name}",
            )
            return TaskAck(
                task_id=task.task_id,
                status=AckStatus.REJECTED,
                reason=f"unknown adapter or persona: {adapter_name}",
            )

        self._state.record_task(task)
        risk = self._risk_assessor.assess(task)
        self._audit_log.record(
            AuditEventType.TASK_SUBMITTED,
            task,
            adapter_name=adapter.name,
            risk_level=risk.risk_level,
        )
        unsupported_reason = unsupported_risk_reason(adapter, risk)
        if unsupported_reason is not None:
            self._record_task(
                task,
                adapter_name=adapter.name,
                status=TaskStatus.REJECTED,
                reason=unsupported_reason,
                risk_level=risk.risk_level,
            )
            self._audit_log.record(
                AuditEventType.TASK_REJECTED,
                task,
                adapter_name=adapter.name,
                risk_level=risk.risk_level,
                detail=unsupported_reason,
            )
            return TaskAck(
                task_id=task.task_id,
                status=AckStatus.REJECTED,
                reason=unsupported_reason,
            )
        if risk.requires_approval:
            self._state.save_approval(ApprovalRequest(task=task, risk=risk))
            self._record_task(
                task,
                adapter_name=adapter.name,
                status=TaskStatus.WAITING_APPROVAL,
                reason=_approval_reason(risk),
                risk_level=risk.risk_level,
            )
            self._audit_log.record(
                AuditEventType.APPROVAL_REQUESTED,
                task,
                adapter_name=adapter.name,
                risk_level=risk.risk_level,
                detail=_approval_reason(risk),
            )
            return TaskAck(
                task_id=task.task_id,
                status=AckStatus.WAITING_APPROVAL,
                reason=_approval_reason(risk),
            )

        return await self._dispatch(task, adapter, risk)

    async def approve(self, task_id: str | None, reviewer_id: str) -> TaskAck:
        approval = self._state.resolve_pending_approval(task_id)
        if isinstance(approval, TaskAck):
            return approval

        task_id = approval.task.task_id
        if approval.status is not ApprovalStatus.PENDING:
            return TaskAck(
                task_id=task_id,
                status=AckStatus.REJECTED,
                reason="unknown pending approval",
            )

        task = approval.task
        decision = self._approval_policy.can_review(approval, reviewer_id)
        if not decision.allowed:
            self._audit_log.record(
                AuditEventType.APPROVAL_DENIED,
                task,
                actor_id=reviewer_id,
                risk_level=approval.risk.risk_level,
                detail=decision.reason,
            )
            return TaskAck(
                task_id=task_id,
                status=AckStatus.REJECTED,
                reason=decision.reason or "approver not authorized",
            )

        adapter = self._adapter_for_pending_task(task)
        if adapter is None:
            self._update_task(task_id, TaskStatus.REJECTED, reason="adapter unavailable")
            return TaskAck(
                task_id=task_id,
                status=AckStatus.REJECTED,
                reason="adapter unavailable",
            )

        self._state.save_approval(
            approval.model_copy(
                update={
                    "status": ApprovalStatus.APPROVED,
                    "reviewer_id": reviewer_id,
                }
            )
        )
        self._audit_log.record(
            AuditEventType.APPROVAL_APPROVED,
            task,
            actor_id=reviewer_id,
            adapter_name=adapter.name,
            risk_level=approval.risk.risk_level,
        )
        return await self._dispatch(task, adapter, approval.risk)

    async def reject_approval(
        self,
        task_id: str | None,
        reviewer_id: str,
        *,
        reason: str | None = None,
    ) -> TaskAck:
        approval = self._state.resolve_pending_approval(task_id)
        if isinstance(approval, TaskAck):
            return approval

        task_id = approval.task.task_id
        if approval.status is not ApprovalStatus.PENDING:
            return TaskAck(
                task_id=task_id,
                status=AckStatus.REJECTED,
                reason="unknown pending approval",
            )

        task = approval.task
        decision = self._approval_policy.can_review(approval, reviewer_id)
        if not decision.allowed:
            self._audit_log.record(
                AuditEventType.APPROVAL_DENIED,
                task,
                actor_id=reviewer_id,
                risk_level=approval.risk.risk_level,
                detail=decision.reason,
            )
            return TaskAck(
                task_id=task_id,
                status=AckStatus.REJECTED,
                reason=decision.reason or "approver not authorized",
            )

        reject_reason = reason or "approval rejected"
        self._state.save_approval(
            approval.model_copy(
                update={
                    "status": ApprovalStatus.REJECTED,
                    "reviewer_id": reviewer_id,
                    "reason": reject_reason,
                }
            )
        )
        self._update_task(task_id, TaskStatus.REJECTED, reason=reject_reason)
        self._audit_log.record(
            AuditEventType.APPROVAL_REJECTED,
            task,
            actor_id=reviewer_id,
            risk_level=approval.risk.risk_level,
            detail=reject_reason,
        )
        self._audit_log.record(
            AuditEventType.TASK_REJECTED,
            task,
            actor_id=reviewer_id,
            risk_level=approval.risk.risk_level,
            detail=reject_reason,
        )
        return TaskAck(task_id=task_id, status=AckStatus.REJECTED, reason=reject_reason)

    async def _dispatch(
        self,
        task: Task,
        adapter: AIAdapter,
        risk: RiskAssessment,
    ) -> TaskAck:
        effective_task = self._effective_task(task)
        ack = await adapter.receive_task(effective_task)
        if ack.status is AckStatus.ACCEPTED:
            self._state.task_adapters[task.task_id] = adapter.name
            self._record_task(
                task,
                adapter_name=adapter.name,
                status=TaskStatus.RUNNING,
                risk_level=risk.risk_level,
            )
            self._audit_log.record(
                AuditEventType.ADAPTER_DISPATCHED,
                task,
                adapter_name=adapter.name,
                risk_level=risk.risk_level,
            )
        else:
            self._record_task(
                task,
                adapter_name=adapter.name,
                status=TaskStatus.REJECTED,
                reason=ack.reason,
                risk_level=risk.risk_level,
            )
            self._audit_log.record(
                AuditEventType.TASK_REJECTED,
                task,
                adapter_name=adapter.name,
                risk_level=risk.risk_level,
                detail=ack.reason,
            )
        return ack

    async def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        adapter = self._adapter_for_task(task_id)
        if adapter is None:
            async for output in _unknown_task_output(task_id):
                yield output
            return

        async for output in adapter.stream_output(task_id):
            self._update_from_output(task_id, output)
            yield output

    async def interrupt(self, task_ref: str) -> TaskAck:
        task = self._state.resolve_known_task(task_ref)
        if isinstance(task, TaskAck):
            return task

        task_id = task.task_id
        if task.status is TaskStatus.WAITING_APPROVAL:
            self._cancel_waiting_approval(task_id)
            return TaskAck(
                task_id=task_id,
                status=AckStatus.ACCEPTED,
                reason="pending approval canceled",
            )
        if task.status is not TaskStatus.RUNNING:
            return TaskAck(
                task_id=task_id,
                status=AckStatus.REJECTED,
                reason=f"task is {task.status.value}, not running",
            )

        adapter = self._adapter_for_task(task_id)
        if adapter is not None:
            await adapter.interrupt(task_id)
            if self._state.task_status(task_id) is TaskStatus.RUNNING:
                self._update_task(task_id, TaskStatus.INTERRUPTED)
                self._record_audit_for_task(task_id, AuditEventType.TASK_INTERRUPTED)
            return TaskAck(task_id=task_id, status=AckStatus.ACCEPTED)
        return TaskAck(task_id=task_id, status=AckStatus.REJECTED, reason="adapter unavailable")

    def snapshots(self) -> tuple[AdapterSnapshot, ...]:
        return self._registry.snapshots()

    def task_snapshots(self, *, limit: int | None = 5) -> tuple[TaskSnapshot, ...]:
        return self._state.task_snapshots(limit=limit)

    def task_snapshot(self, task_ref: str) -> TaskSnapshot | TaskAck:
        return self._state.resolve_known_task(task_ref)

    def audit_events(self, *, limit: int | None = 10) -> tuple[AuditEvent, ...]:
        return self._audit_log.events(limit=limit)

    def audit_log(self) -> InMemoryAuditLog:
        return self._audit_log

    def record_collaboration_requested(
        self,
        source_task: Task,
        child_task: Task,
        *,
        actor_id: str | None = None,
    ) -> None:
        self._audit_log.record(
            AuditEventType.COLLABORATION_REQUESTED,
            child_task,
            actor_id=actor_id or source_task.target_persona,
            detail=f"parent_task={source_task.task_id}",
        )

    def mark_failed(self, task_id: str, *, reason: str) -> None:
        self._update_task(task_id, TaskStatus.FAILED, reason=reason)
        self._record_audit_for_task(task_id, AuditEventType.TASK_FAILED, detail=reason)

    def record_lead_decision(self, task: Task, *, detail: str) -> AuditEvent:
        snapshot = self._state.tasks.get(task.task_id)
        return self._audit_log.record(
            AuditEventType.LEAD_DECISION_RECORDED,
            task,
            adapter_name=None if snapshot is None else snapshot.adapter_name,
            risk_level=RiskLevel.READ_ONLY if snapshot is None else snapshot.risk_level,
            detail=detail,
        )

    def task_record(self, task_id: str) -> Task | None:
        return self._state.task_records.get(task_id)

    def pending_approvals(self) -> tuple[ApprovalRequest, ...]:
        return self._state.pending_approvals()

    def _cancel_waiting_approval(self, task_id: str) -> None:
        approval = self._state.approvals.get(task_id)
        if approval is not None and approval.status is ApprovalStatus.PENDING:
            self._state.save_approval(
                approval.model_copy(
                    update={
                        "status": ApprovalStatus.REJECTED,
                        "reason": "interrupted before approval",
                    }
                )
            )
            self._audit_log.record(
                AuditEventType.APPROVAL_REJECTED,
                approval.task,
                risk_level=approval.risk.risk_level,
                detail="interrupted before approval",
            )
        self._update_task(task_id, TaskStatus.INTERRUPTED, reason="interrupted before approval")
        self._record_audit_for_task(
            task_id,
            AuditEventType.TASK_INTERRUPTED,
            detail="interrupted before approval",
        )

    def broadcast_targets(self) -> tuple[str, ...]:
        if self._persona_registry is not None:
            return self._persona_registry.names()
        return tuple(snapshot.name for snapshot in self._registry.snapshots())

    def _adapter_for_task(self, task_id: str) -> AIAdapter | None:
        adapter_name = self._state.task_adapters.get(task_id)
        if adapter_name is None:
            return None
        return self._registry.get(adapter_name)

    def _adapter_name_for_task(self, task: Task) -> str:
        persona = self._resolve_persona(task.target_persona)
        return task.target_persona if persona is None else persona.adapter_name

    def _adapter_for_pending_task(self, task: Task) -> AIAdapter | None:
        adapter = self._registry.resolve(self._adapter_name_for_task(task))
        if adapter is None and self._single_adapter_mode:
            return self._registry.default()
        return adapter

    def _effective_task(self, task: Task) -> Task:
        persona = self._resolve_persona(task.target_persona)
        if persona is None:
            return task
        return task.model_copy(
            update={
                "payload": f"{persona.role_instruction.strip()}\n\n{task.payload}",
            }
        )

    def _resolve_persona(self, target_persona: str) -> PersonaProfile | None:
        if self._persona_registry is None:
            return None
        return self._persona_registry.resolve(target_persona)

    def _record_task(
        self,
        task: Task,
        *,
        status: TaskStatus,
        adapter_name: str | None = None,
        reason: str | None = None,
        risk_level: RiskLevel = RiskLevel.READ_ONLY,
    ) -> None:
        self._state.record_snapshot(
            task,
            adapter_name=adapter_name,
            status=status,
            reason=reason,
            risk_level=risk_level,
        )

    def _update_from_output(self, task_id: str, output: TaskOutput) -> None:
        if self._state.task_status(task_id) is TaskStatus.INTERRUPTED:
            return
        if output.type is OutputType.ERROR:
            self._update_task(task_id, TaskStatus.FAILED, reason=output.content)
            self._record_audit_for_task(
                task_id,
                AuditEventType.TASK_FAILED,
                detail=output.content,
            )
        elif output.type is OutputType.STATUS:
            self._update_task(task_id, TaskStatus.RUNNING, reason=output.content)
        elif output.type is OutputType.TEXT:
            self._update_task(task_id, TaskStatus.RUNNING)
        elif output.type is OutputType.DONE:
            self._update_task(task_id, TaskStatus.DONE)
            self._record_audit_for_task(task_id, AuditEventType.TASK_COMPLETED)

    def _update_task(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        reason: str | None = None,
    ) -> None:
        self._state.update_task(task_id, status, reason=reason)

    def _record_audit_for_task(
        self,
        task_id: str,
        event_type: AuditEventType,
        *,
        detail: str | None = None,
    ) -> None:
        task = self._state.task_records.get(task_id)
        snapshot = self._state.tasks.get(task_id)
        if task is None or snapshot is None:
            return
        self._audit_log.record(
            event_type,
            task,
            adapter_name=snapshot.adapter_name,
            risk_level=snapshot.risk_level,
            detail=detail,
        )


async def _unknown_task_output(task_id: str) -> AsyncIterator[TaskOutput]:
    yield TaskOutput(
        task_id=task_id,
        sequence=0,
        type=OutputType.ERROR,
        content="unknown task id",
    )


def _approval_reason(risk: RiskAssessment) -> str:
    reasons = ", ".join(risk.reasons) if risk.reasons else "risk requires approval"
    return f"approval required: {risk.risk_level.value} - {reasons}"
