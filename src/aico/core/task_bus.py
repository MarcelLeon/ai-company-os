"""Minimal task bus that delegates work to an AI adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

from aico.adapter import AIAdapter
from aico.core.adapter_registry import AdapterRegistry
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
    utc_now,
)
from aico.core.persona_registry import PersonaRegistry
from aico.core.risk import TextRiskAssessor


class TaskBus:
    """Submit tasks and expose adapter output without leaking adapter lookup."""

    def __init__(
        self,
        adapter: AIAdapter | AdapterRegistry,
        persona_registry: PersonaRegistry | None = None,
        risk_assessor: TextRiskAssessor | None = None,
        audit_log: InMemoryAuditLog | None = None,
    ) -> None:
        self._single_adapter_mode = not isinstance(adapter, AdapterRegistry)
        self._registry = (
            adapter if isinstance(adapter, AdapterRegistry) else AdapterRegistry([adapter])
        )
        self._persona_registry = persona_registry
        self._risk_assessor = risk_assessor or TextRiskAssessor()
        self._audit_log = audit_log or InMemoryAuditLog()
        self._task_adapters: dict[str, str] = {}
        self._tasks: dict[str, TaskSnapshot] = {}
        self._task_records: dict[str, Task] = {}
        self._approvals: dict[str, ApprovalRequest] = {}

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

        self._task_records[task.task_id] = task
        risk = self._risk_assessor.assess(task)
        self._audit_log.record(
            AuditEventType.TASK_SUBMITTED,
            task,
            adapter_name=adapter.name,
            risk_level=risk.risk_level,
        )
        if risk.requires_approval:
            self._approvals[task.task_id] = ApprovalRequest(task=task, risk=risk)
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

    async def approve(self, task_id: str, reviewer_id: str) -> TaskAck:
        approval = self._approvals.get(task_id)
        if approval is None or approval.status is not ApprovalStatus.PENDING:
            return TaskAck(
                task_id=task_id,
                status=AckStatus.REJECTED,
                reason="unknown pending approval",
            )

        task = approval.task
        adapter = self._adapter_for_pending_task(task)
        if adapter is None:
            self._update_task(task_id, TaskStatus.REJECTED, reason="adapter unavailable")
            return TaskAck(
                task_id=task_id,
                status=AckStatus.REJECTED,
                reason="adapter unavailable",
            )

        self._approvals[task_id] = approval.model_copy(
            update={
                "status": ApprovalStatus.APPROVED,
                "reviewer_id": reviewer_id,
                "updated_at": utc_now(),
            }
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
        task_id: str,
        reviewer_id: str,
        *,
        reason: str | None = None,
    ) -> TaskAck:
        approval = self._approvals.get(task_id)
        if approval is None or approval.status is not ApprovalStatus.PENDING:
            return TaskAck(
                task_id=task_id,
                status=AckStatus.REJECTED,
                reason="unknown pending approval",
            )

        task = approval.task
        reject_reason = reason or "approval rejected"
        self._approvals[task_id] = approval.model_copy(
            update={
                "status": ApprovalStatus.REJECTED,
                "reviewer_id": reviewer_id,
                "reason": reject_reason,
                "updated_at": utc_now(),
            }
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
            self._task_adapters[task.task_id] = adapter.name
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

    async def interrupt(self, task_id: str) -> None:
        adapter = self._adapter_for_task(task_id)
        if adapter is not None:
            await adapter.interrupt(task_id)
            if self._task_status(task_id) is TaskStatus.RUNNING:
                self._update_task(task_id, TaskStatus.INTERRUPTED)
                self._record_audit_for_task(task_id, AuditEventType.TASK_INTERRUPTED)

    def snapshots(self) -> tuple[AdapterSnapshot, ...]:
        return self._registry.snapshots()

    def task_snapshots(self, *, limit: int = 5) -> tuple[TaskSnapshot, ...]:
        snapshots = sorted(
            self._tasks.values(),
            key=lambda snapshot: snapshot.updated_at,
            reverse=True,
        )
        return tuple(reversed(snapshots[:limit]))

    def audit_events(self, *, limit: int = 10) -> tuple[AuditEvent, ...]:
        return self._audit_log.events(limit=limit)

    def broadcast_targets(self) -> tuple[str, ...]:
        if self._persona_registry is not None:
            return self._persona_registry.names()
        return tuple(snapshot.name for snapshot in self._registry.snapshots())

    def _adapter_for_task(self, task_id: str) -> AIAdapter | None:
        adapter_name = self._task_adapters.get(task_id)
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
        self._tasks[task.task_id] = TaskSnapshot(
            task_id=task.task_id,
            target_persona=task.target_persona,
            adapter_name=adapter_name,
            status=status,
            reason=reason,
            risk_level=risk_level,
            created_at=task.created_at,
        )

    def _update_from_output(self, task_id: str, output: TaskOutput) -> None:
        if self._task_status(task_id) is TaskStatus.INTERRUPTED:
            return
        if output.type is OutputType.ERROR:
            self._update_task(task_id, TaskStatus.FAILED, reason=output.content)
            self._record_audit_for_task(
                task_id,
                AuditEventType.TASK_FAILED,
                detail=output.content,
            )
        elif output.type is OutputType.DONE:
            self._update_task(task_id, TaskStatus.DONE)
            self._record_audit_for_task(task_id, AuditEventType.TASK_COMPLETED)

    def _task_status(self, task_id: str) -> TaskStatus | None:
        snapshot = self._tasks.get(task_id)
        return None if snapshot is None else snapshot.status

    def _update_task(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        reason: str | None = None,
    ) -> None:
        snapshot = self._tasks.get(task_id)
        if snapshot is None:
            return
        self._tasks[task_id] = snapshot.model_copy(
            update={
                "status": status,
                "reason": reason,
                "updated_at": utc_now(),
            }
        )

    def _record_audit_for_task(
        self,
        task_id: str,
        event_type: AuditEventType,
        *,
        detail: str | None = None,
    ) -> None:
        task = self._task_records.get(task_id)
        snapshot = self._tasks.get(task_id)
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
