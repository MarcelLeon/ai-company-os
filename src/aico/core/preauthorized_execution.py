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
PREAUTHORIZED_MAX_TOTAL_TOKENS_KEY = "aico.preauthorized_max_total_tokens"
PREAUTHORIZED_MODEL_KEY = "aico.preauthorized_model"
PREAUTHORIZED_REASONING_EFFORT_KEY = "aico.preauthorized_reasoning_effort"
_PREAUTHORIZED_KEYS = {
    PREAUTHORIZED_MODE_KEY,
    PREAUTHORIZED_GRANT_ID_KEY,
    PREAUTHORIZED_EXPIRES_AT_KEY,
    PREAUTHORIZED_MAX_DURATION_KEY,
    PREAUTHORIZED_MAX_TOTAL_TOKENS_KEY,
    PREAUTHORIZED_MODEL_KEY,
    PREAUTHORIZED_REASONING_EFFORT_KEY,
}


class PreauthorizedExecutionMode(StrEnum):
    READ_ONLY = "read_only"


@runtime_checkable
class PreauthorizedExecutionAdapter(Protocol):
    """Optional Adapter contract backed by a tool-owned execution boundary."""

    def supports_preauthorized_execution(self, mode: str) -> bool: ...

    def supports_preauthorized_budget(self, max_total_tokens: int) -> bool: ...


@runtime_checkable
class PreauthorizedModelAdapter(Protocol):
    """Optional exact model/effort boundary used by comparative benchmark tasks."""

    def supports_preauthorized_model(self, model: str, reasoning_effort: str) -> bool: ...


def task_with_preauthorized_execution(
    task: Task,
    *,
    grant_id: str,
    expires_at: object,
    max_duration_seconds: float,
    max_total_tokens: int,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> Task:
    if (model is None) != (reasoning_effort is None):
        raise ValueError("preauthorized exact model and reasoning effort must be provided together")
    if model is not None and (not model.strip() or not _safe_effort(reasoning_effort or "")):
        raise ValueError("preauthorized exact model contract is invalid")
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
                MetadataEntry(
                    key=PREAUTHORIZED_MAX_TOTAL_TOKENS_KEY,
                    value=max_total_tokens,
                ),
                *(
                    ()
                    if model is None
                    else (
                        MetadataEntry(key=PREAUTHORIZED_MODEL_KEY, value=model),
                        MetadataEntry(
                            key=PREAUTHORIZED_REASONING_EFFORT_KEY,
                            value=reasoning_effort,
                        ),
                    )
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


def preauthorized_max_total_tokens(task: Task) -> int | None:
    value = next(
        (entry.value for entry in task.metadata if entry.key == PREAUTHORIZED_MAX_TOTAL_TOKENS_KEY),
        None,
    )
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def preauthorized_model_contract(task: Task) -> tuple[str, str] | None:
    model = next(
        (entry.value for entry in task.metadata if entry.key == PREAUTHORIZED_MODEL_KEY),
        None,
    )
    effort = next(
        (entry.value for entry in task.metadata if entry.key == PREAUTHORIZED_REASONING_EFFORT_KEY),
        None,
    )
    if model is None and effort is None:
        return None
    if (
        not isinstance(model, str)
        or not model.strip()
        or not isinstance(effort, str)
        or not _safe_effort(effort)
    ):
        raise ValueError("preauthorized exact model contract is invalid")
    return model, effort


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
    max_total_tokens = preauthorized_max_total_tokens(task)
    if max_total_tokens is None:
        return "preauthorized execution requires a single-run token budget"
    if not adapter.supports_preauthorized_budget(max_total_tokens):
        return "adapter lacks an enforced single-run token budget"
    try:
        model_contract = preauthorized_model_contract(task)
    except ValueError:
        return "preauthorized exact model contract is invalid"
    if model_contract is not None:
        if not isinstance(adapter, PreauthorizedModelAdapter) or not (
            adapter.supports_preauthorized_model(*model_contract)
        ):
            return "adapter lacks an enforced exact model boundary"
    return None


def _safe_effort(value: str) -> bool:
    return 0 < len(value) <= 32 and all(char.isalnum() or char in {"-", "_"} for char in value)
