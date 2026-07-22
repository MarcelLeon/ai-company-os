"""Fail-closed metadata and Adapter boundary for owner-preauthorized execution."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from aico.adapter import AIAdapter
from aico.core.agent_session import provider_session_from_task
from aico.core.collaboration import collaboration_disabled
from aico.core.models import MetadataEntry, RiskAssessment, RiskLevel, Task

PREAUTHORIZED_MODE_KEY = "aico.preauthorized_mode"
PREAUTHORIZED_GRANT_ID_KEY = "aico.preauthorized_grant_id"
PREAUTHORIZED_EXPIRES_AT_KEY = "aico.preauthorized_expires_at"
PREAUTHORIZED_MAX_DURATION_KEY = "aico.preauthorized_max_duration_seconds"
_PREAUTHORIZED_KEYS = {
    PREAUTHORIZED_MODE_KEY,
    PREAUTHORIZED_GRANT_ID_KEY,
    PREAUTHORIZED_EXPIRES_AT_KEY,
    PREAUTHORIZED_MAX_DURATION_KEY,
}


class PreauthorizedExecutionMode(StrEnum):
    READ_ONLY = "read_only"


@runtime_checkable
class PreauthorizedExecutionAdapter(Protocol):
    """Optional Adapter contract backed by a tool-owned execution boundary."""

    def supports_preauthorized_execution(self, mode: str) -> bool: ...


def task_with_preauthorized_execution(
    task: Task,
    *,
    grant_id: str,
    expires_at: object,
    max_duration_seconds: float,
) -> Task:
    metadata = tuple(entry for entry in task.metadata if entry.key not in _PREAUTHORIZED_KEYS)
    expiry = expires_at.isoformat() if hasattr(expires_at, "isoformat") else str(expires_at)
    return task.model_copy(
        update={
            "metadata": (
                *metadata,
                MetadataEntry(
                    key=PREAUTHORIZED_MODE_KEY,
                    value=PreauthorizedExecutionMode.READ_ONLY.value,
                ),
                MetadataEntry(key=PREAUTHORIZED_GRANT_ID_KEY, value=grant_id),
                MetadataEntry(key=PREAUTHORIZED_EXPIRES_AT_KEY, value=expiry),
                MetadataEntry(
                    key=PREAUTHORIZED_MAX_DURATION_KEY,
                    value=max_duration_seconds,
                ),
            )
        }
    )


def preauthorized_execution_mode(task: Task) -> str | None:
    value = next(
        (entry.value for entry in task.metadata if entry.key == PREAUTHORIZED_MODE_KEY),
        None,
    )
    return value if isinstance(value, str) else None


def preauthorized_submission_refusal(
    task: Task,
    adapter: AIAdapter,
    risk: RiskAssessment,
) -> str | None:
    mode = preauthorized_execution_mode(task)
    if mode is None:
        return None
    if mode != PreauthorizedExecutionMode.READ_ONLY.value:
        return "unsupported preauthorized execution mode"
    if risk.risk_level is not RiskLevel.READ_ONLY or risk.requires_approval:
        return "preauthorized execution must remain read-only"
    if not collaboration_disabled(task):
        return "preauthorized execution must disable collaboration"
    if provider_session_from_task(task) is not None:
        return "preauthorized execution must not reuse a provider session"
    if not isinstance(adapter, PreauthorizedExecutionAdapter):
        return "adapter lacks an enforced read-only preauthorization boundary"
    if not adapter.supports_preauthorized_execution(mode):
        return "adapter lacks an enforced read-only preauthorization boundary"
    return None
