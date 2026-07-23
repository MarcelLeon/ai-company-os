"""Minimal task bus that delegates work to an AI adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import datetime
from time import monotonic

from aico.adapter import (
    AIAdapter,
    ProviderExecutionReportingAdapter,
    TaskUsageReportingAdapter,
)
from aico.core.adapter_registry import AdapterRegistry
from aico.core.approval import (
    DEFAULT_APPROVAL_MAX_AGE_SECONDS,
    ApprovalLeaseCoordinator,
    ApprovalPolicy,
    RequesterOrListedApproverPolicy,
)
from aico.core.audit import InMemoryAuditLog
from aico.core.authorization_clock import AuthorizationClockGuard
from aico.core.metrics import usage_audit_detail
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
    TaskUsage,
    utc_now,
)
from aico.core.persona_registry import PersonaRegistry
from aico.core.preauthorized_execution import (
    preauthorized_execution_mode,
    preauthorized_submission_refusal,
)
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
        approval_max_age_seconds: int = DEFAULT_APPROVAL_MAX_AGE_SECONDS,
        task_store: TaskStateStore | None = None,
        clock: Callable[[], datetime] = utc_now,
        monotonic_clock: Callable[[], float] = monotonic,
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
        authorization_clock = AuthorizationClockGuard(
            task_store,
            clock=clock,
            monotonic_clock=monotonic_clock,
        )
        self._approval_leases = ApprovalLeaseCoordinator(
            self._state,
            self._audit_log,
            max_age_seconds=approval_max_age_seconds,
            durable=task_store is not None,
            clock=clock,
            authorization_clock=authorization_clock,
        )

    def recover_startup_state(self) -> None:
        """Reconcile persisted execution state after runtime ownership is acquired."""
        self._approval_leases.deliver_reconciliation_events(self._state.reconcile_startup())
        self.expire_stale_approvals()

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
        preauthorized_refusal = self.preauthorized_refusal(task)
        if preauthorized_refusal is not None:
            return self._reject_submission(task, adapter.name, risk, preauthorized_refusal)
        unsupported_reason = unsupported_risk_reason(adapter, risk)
        if unsupported_reason is not None:
            return self._reject_submission(task, adapter.name, risk, unsupported_reason)
        if risk.requires_approval:
            clock_refusal = self.authorization_time_refusal()
            if clock_refusal is not None:
                return self._reject_submission(task, adapter.name, risk, clock_refusal)
            self._state.save_approval(self._approval_leases.new_request(task, risk))
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

    def preauthorized_refusal(self, task: Task) -> str | None:
        refusal = _preauthorized_refusal(
            task, self._adapter_for_pending_task(task), self._risk_assessor
        )
        if refusal is not None or preauthorized_execution_mode(task) is None:
            return refusal
        return self.authorization_time_refusal()

    def authorization_time_refusal(self) -> str | None:
        """Reconcile time-based authority and return a stable fail-closed reason."""
        return self._approval_leases.authorization_time_refusal()

    async def approve(self, task_id: str | None, reviewer_id: str) -> TaskAck:
        self.expire_stale_approvals()
        approval = self._state.resolve_pending_approval(task_id)
        if isinstance(approval, TaskAck):
            return approval

        task_id = approval.task.task_id
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

        self._approval_leases.resolve(
            approval,
            ApprovalStatus.APPROVED,
            reviewer_id=reviewer_id,
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
        self.expire_stale_approvals()
        approval = self._state.resolve_pending_approval(task_id)
        if isinstance(approval, TaskAck):
            return approval

        task_id = approval.task.task_id
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
        self._approval_leases.resolve(
            approval,
            ApprovalStatus.REJECTED,
            reviewer_id=reviewer_id,
            reason=reject_reason,
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
        self.expire_stale_approvals()
        return self._state.task_snapshots(limit=limit)

    def task_snapshot(self, task_ref: str) -> TaskSnapshot | TaskAck:
        self.expire_stale_approvals()
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
        self.expire_stale_approvals()
        return self._state.pending_approvals()

    def expire_stale_approvals(self) -> int:
        """Fail closed when a risky task outlives its bounded approval lease."""
        return self._approval_leases.sweep()

    def _cancel_waiting_approval(self, task_id: str) -> None:
        approval = self._state.approvals.get(task_id)
        if approval is not None and approval.status is ApprovalStatus.PENDING:
            self._approval_leases.resolve(
                approval,
                ApprovalStatus.REJECTED,
                reason="interrupted before approval",
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

    def _reject_submission(
        self,
        task: Task,
        adapter_name: str,
        risk: RiskAssessment,
        reason: str,
    ) -> TaskAck:
        self._record_task(
            task,
            adapter_name=adapter_name,
            status=TaskStatus.REJECTED,
            reason=reason,
            risk_level=risk.risk_level,
        )
        self._audit_log.record(
            AuditEventType.TASK_REJECTED,
            task,
            adapter_name=adapter_name,
            risk_level=risk.risk_level,
            detail=reason,
        )
        return TaskAck(task_id=task.task_id, status=AckStatus.REJECTED, reason=reason)

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
            _record_task_usage(self, task_id)
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


def _record_task_usage(task_bus: TaskBus, task_id: str) -> None:
    usage = task_usage_for_task(task_bus, task_id)
    if usage is None:
        return
    task_bus._record_audit_for_task(  # noqa: SLF001
        task_id,
        AuditEventType.TASK_USAGE_RECORDED,
        detail=usage_audit_detail(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            cache_write_input_tokens=usage.cache_write_input_tokens,
            reasoning_output_tokens=usage.reasoning_output_tokens,
        ),
    )


def task_usage_for_task(task_bus: TaskBus, task_id: str) -> TaskUsage | None:
    adapter = task_bus._adapter_for_task(task_id)  # noqa: SLF001
    if not isinstance(adapter, TaskUsageReportingAdapter):
        return None
    return adapter.task_usage(task_id)


def provider_execution_id_for_task(task_bus: TaskBus, task_id: str) -> str | None:
    adapter = task_bus._adapter_for_task(task_id)  # noqa: SLF001
    if not isinstance(adapter, ProviderExecutionReportingAdapter):
        return None
    return adapter.provider_execution_id(task_id)


def _preauthorized_refusal(
    task: Task,
    adapter: AIAdapter | None,
    risk_assessor: TextRiskAssessor,
) -> str | None:
    if adapter is None:
        return "preauthorized execution target is unavailable"
    return preauthorized_submission_refusal(task, adapter, risk_assessor.assess(task))


def _approval_reason(risk: RiskAssessment) -> str:
    reasons = ", ".join(risk.reasons) if risk.reasons else "risk requires approval"
    return f"approval required: {risk.risk_level.value} - {reasons}"
