"""Immutable protocol models shared by adapters, channels, and core services."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Capability(StrEnum):
    CODE_EDIT = "code_edit"
    CODE_REVIEW = "code_review"
    SHELL_EXEC = "shell_exec"
    WEB_BROWSE = "web_browse"
    LONG_RUNNING = "long_running"
    STREAM_OUTPUT = "stream_output"
    INTERRUPTIBLE = "interruptible"


class AdapterStatus(StrEnum):
    IDLE = "idle"
    BUSY = "busy"
    BLOCKED = "blocked"
    WAITING_APPROVAL = "waiting_approval"
    OFFLINE = "offline"


class HealthStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"


class AckStatus(StrEnum):
    ACCEPTED = "accepted"
    BUSY = "busy"
    REJECTED = "rejected"
    WAITING_APPROVAL = "waiting_approval"


class OutputType(StrEnum):
    TEXT = "text"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    DONE = "done"


class TaskStatus(StrEnum):
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    REJECTED = "rejected"


class RiskLevel(StrEnum):
    READ_ONLY = "read_only"
    WRITE_FILES = "write_files"
    SHELL_EXEC = "shell_exec"
    DESTRUCTIVE = "destructive"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AuditEventType(StrEnum):
    TASK_SUBMITTED = "task_submitted"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    ADAPTER_DISPATCHED = "adapter_dispatched"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_INTERRUPTED = "task_interrupted"
    TASK_REJECTED = "task_rejected"


class MessageKind(StrEnum):
    TEXT = "text"


class MetadataEntry(FrozenModel):
    key: str = Field(min_length=1)
    value: str | int | float | bool | None


class Task(FrozenModel):
    task_id: str = Field(min_length=1)
    payload: str = Field(min_length=1)
    requester_id: str = Field(min_length=1)
    target_persona: str = Field(min_length=1)
    context_ref: str | None = None
    metadata: tuple[MetadataEntry, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)


class TaskAck(FrozenModel):
    task_id: str = Field(min_length=1)
    status: AckStatus
    reason: str | None = None


class TaskOutput(FrozenModel):
    task_id: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    type: OutputType
    content: str
    timestamp: datetime = Field(default_factory=utc_now)


class AdapterSnapshot(FrozenModel):
    name: str = Field(min_length=1)
    status: AdapterStatus
    capabilities: tuple[Capability, ...] = ()


class TaskSnapshot(FrozenModel):
    task_id: str = Field(min_length=1)
    target_persona: str = Field(min_length=1)
    adapter_name: str | None = None
    status: TaskStatus
    reason: str | None = None
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RiskAssessment(FrozenModel):
    risk_level: RiskLevel
    requires_approval: bool = False
    reasons: tuple[str, ...] = ()


class ApprovalRequest(FrozenModel):
    task: Task
    risk: RiskAssessment
    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer_id: str | None = None
    reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AuditEvent(FrozenModel):
    event_id: str = Field(min_length=1)
    event_type: AuditEventType
    task_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    target_persona: str = Field(min_length=1)
    adapter_name: str | None = None
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    detail: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class PersonaProfile(FrozenModel):
    name: str = Field(min_length=1)
    adapter_name: str = Field(min_length=1)
    role_instruction: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()


class MessageContent(FrozenModel):
    kind: MessageKind = MessageKind.TEXT
    text: str = Field(min_length=1)


class ChannelTarget(FrozenModel):
    channel_name: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    thread_id: str | None = None


class SentMessage(FrozenModel):
    message_id: str = Field(min_length=1)
    target: ChannelTarget
    timestamp: datetime = Field(default_factory=utc_now)


class IncomingMessage(FrozenModel):
    channel_name: str = Field(min_length=1)
    source: ChannelTarget
    sender_id: str = Field(min_length=1)
    mentions: tuple[str, ...] = ()
    content: MessageContent
    timestamp: datetime = Field(default_factory=utc_now)
    raw_ref: str = Field(min_length=1)
