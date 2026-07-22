from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from aico.core import (
    AckStatus,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    AuditEventType,
    ChannelTarget,
    IncomingMessage,
    MessageContent,
    MetadataEntry,
    OutputType,
    RiskAssessment,
    RiskLevel,
    Task,
    TaskAck,
    TaskOutput,
    TaskSnapshot,
    TaskStatus,
)


def test_task_is_immutable_and_uses_utc_timestamp() -> None:
    task = Task(
        task_id="task-1",
        payload="Refactor the adapter boundary",
        requester_id="user-1",
        target_persona="lao-zhang",
        metadata=(MetadataEntry(key="trace_id", value="trace-1"),),
    )

    assert task.created_at.tzinfo == UTC
    assert task.metadata[0].key == "trace_id"

    with pytest.raises(ValidationError):
        task.payload = "mutated"


def test_task_rejects_empty_identity_fields() -> None:
    with pytest.raises(ValidationError):
        Task(
            task_id="",
            payload="Do work",
            requester_id="user-1",
            target_persona="lao-zhang",
        )


def test_task_ack_and_output_keep_protocol_state_explicit() -> None:
    ack = TaskAck(task_id="task-1", status=AckStatus.ACCEPTED)
    output = TaskOutput(task_id="task-1", sequence=0, type=OutputType.TEXT, content="hello")

    assert ack.status is AckStatus.ACCEPTED
    assert output.type == "text"


def test_task_snapshot_keeps_lifecycle_state_explicit() -> None:
    snapshot = TaskSnapshot(
        task_id="task-1",
        target_persona="codex",
        adapter_name="codex",
        status=TaskStatus.RUNNING,
    )

    assert snapshot.status is TaskStatus.RUNNING
    assert snapshot.adapter_name == "codex"
    assert snapshot.created_at.tzinfo == UTC


def test_risk_approval_and_audit_models_are_explicit() -> None:
    task = Task(
        task_id="task-1",
        payload="delete generated files",
        requester_id="user-1",
        target_persona="implementer",
    )
    risk = RiskAssessment(
        risk_level=RiskLevel.DESTRUCTIVE,
        requires_approval=True,
        reasons=("mentions destructive operations",),
    )
    event = AuditEvent(
        event_id="event-1",
        event_type=AuditEventType.APPROVAL_REQUESTED,
        task_id=task.task_id,
        actor_id=task.requester_id,
        target_persona=task.target_persona,
        risk_level=risk.risk_level,
    )

    assert risk.requires_approval is True
    assert event.event_type is AuditEventType.APPROVAL_REQUESTED
    assert AuditEventType.APPROVAL_DENIED.value == "approval_denied"
    assert AuditEventType.APPROVAL_EXPIRED.value == "approval_expired"
    assert AuditEventType.COLLABORATION_REQUESTED.value == "collaboration_requested"
    assert ApprovalStatus.PENDING.value == "pending"
    assert ApprovalStatus.EXPIRED.value == "expired"


def test_approval_request_freezes_an_aware_future_expiry() -> None:
    created_at = datetime(2026, 7, 22, 8, tzinfo=UTC)
    task = Task(
        task_id="task-lease",
        payload="modify one file",
        requester_id="user-1",
        target_persona="implementer",
    )
    risk = RiskAssessment(risk_level=RiskLevel.WRITE_FILES, requires_approval=True)

    approval = ApprovalRequest(
        task=task,
        risk=risk,
        created_at=created_at,
        expires_at=created_at + timedelta(minutes=5),
    )

    assert approval.expires_at == created_at + timedelta(minutes=5)
    with pytest.raises(ValidationError):
        ApprovalRequest(
            task=task,
            risk=risk,
            created_at=created_at,
            expires_at=created_at,
        )


def test_incoming_message_captures_channel_context() -> None:
    target = ChannelTarget(channel_name="telegram", target_id="chat-1")
    message = IncomingMessage(
        channel_name="telegram",
        source=target,
        sender_id="user-1",
        mentions=("lao-zhang",),
        content=MessageContent(text="please review"),
        raw_ref="message-1",
    )

    assert message.source == target
    assert message.mentions == ("lao-zhang",)
