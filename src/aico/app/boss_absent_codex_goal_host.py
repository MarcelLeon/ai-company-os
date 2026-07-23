"""Fail-closed evidence contracts for the native Codex Goal host boundary."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from aico.core.models import FrozenModel

Sha256 = str
GoalStatus = Literal[
    "active",
    "paused",
    "blocked",
    "usageLimited",
    "budgetLimited",
    "complete",
]


class CodexGoalHostKind(StrEnum):
    NATIVE_CODEX_HOST = "native_codex_host"
    STANDALONE_APP_SERVER = "standalone_app_server"


class CodexGoalTurnSource(StrEnum):
    INITIAL_TASK = "initial_task"
    NATIVE_HOST_CONTINUATION = "native_host_continuation"
    OWNER_TAKEOVER = "owner_takeover"
    HARNESS_INJECTION = "harness_injection"


class CodexGoalHostCapabilities(FrozenModel):
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    host_build: str = Field(min_length=1, max_length=128)
    host_kind: CodexGoalHostKind
    native_continuation_available: bool
    runner_constructs_continuation_input: bool
    persistent_thread_resume: bool
    isolated_run_state: bool
    provider_usage_observable: bool
    default_capabilities_only: bool


class CodexGoalHostAdmissionReceipt(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    host_build: str = Field(min_length=1, max_length=128)
    host_kind: Literal[CodexGoalHostKind.NATIVE_CODEX_HOST]
    continuation_owner: Literal["native_codex_host"] = "native_codex_host"
    continuation_input_opaque: Literal[True] = True
    formal_run_admitted: Literal[True] = True


class CodexGoalHostTurnReceipt(FrozenModel):
    version: Literal[1] = 1
    sequence: int = Field(ge=1)
    source: CodexGoalTurnSource
    previous_turn_sha256: Sha256 | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    turn_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    opaque_input_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_instance_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    goal_status_after: GoalStatus
    goal_tokens_before: int = Field(ge=0)
    goal_tokens_after: int = Field(ge=0)
    goal_token_budget: int = Field(ge=1)
    provider_total_tokens: int = Field(ge=1)
    human_interventions: int = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def validate_turn_receipt(self) -> CodexGoalHostTurnReceipt:
        if self.goal_tokens_after - self.goal_tokens_before != self.provider_total_tokens:
            raise ValueError("Codex Goal host and provider usage do not match")
        if self.goal_tokens_after > self.goal_token_budget:
            raise ValueError("Codex Goal host turn exceeded the frozen token budget")
        if self.source is CodexGoalTurnSource.INITIAL_TASK:
            if self.sequence != 1 or self.previous_turn_sha256 is not None:
                raise ValueError("initial Codex Goal turn must start the receipt chain")
        elif self.previous_turn_sha256 is None:
            raise ValueError("continued Codex Goal turn must link the previous turn")
        expected_interventions = int(self.source is CodexGoalTurnSource.OWNER_TAKEOVER)
        if self.human_interventions != expected_interventions:
            raise ValueError("Codex Goal host intervention count does not match the turn source")
        return self


class CodexGoalHostRunReceipt(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    host_admission_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    turns: tuple[CodexGoalHostTurnReceipt, ...] = Field(min_length=1, max_length=256)
    total_tokens: int = Field(ge=1)
    human_interventions: int = Field(ge=0)
    terminal_status: GoalStatus

    @model_validator(mode="after")
    def validate_run_receipt(self) -> CodexGoalHostRunReceipt:
        _validate_turn_chain(self.turns)
        if self.total_tokens != sum(turn.provider_total_tokens for turn in self.turns):
            raise ValueError("Codex Goal host run total does not match provider turns")
        if self.human_interventions != sum(turn.human_interventions for turn in self.turns):
            raise ValueError("Codex Goal host run intervention total does not match turns")
        if self.terminal_status != self.turns[-1].goal_status_after:
            raise ValueError("Codex Goal host terminal status does not match the final turn")
        return self


def admit_codex_goal_host(
    capabilities: CodexGoalHostCapabilities,
) -> CodexGoalHostAdmissionReceipt:
    """Admit only the native host; app-server alone is just the Goal control plane."""
    if capabilities.host_kind is not CodexGoalHostKind.NATIVE_CODEX_HOST:
        raise ValueError("standalone app-server cannot represent native Codex Goal continuation")
    required = (
        capabilities.native_continuation_available,
        capabilities.persistent_thread_resume,
        capabilities.isolated_run_state,
        capabilities.provider_usage_observable,
        capabilities.default_capabilities_only,
    )
    if not all(required):
        raise ValueError("Codex Goal host is missing a formal benchmark capability")
    if capabilities.runner_constructs_continuation_input:
        raise ValueError("benchmark runner cannot construct Codex Goal continuation input")
    return CodexGoalHostAdmissionReceipt(
        contract_sha256=capabilities.contract_sha256,
        host_build=capabilities.host_build,
        host_kind=CodexGoalHostKind.NATIVE_CODEX_HOST,
    )


def _validate_turn_chain(turns: tuple[CodexGoalHostTurnReceipt, ...]) -> None:
    if turns[0].source is not CodexGoalTurnSource.INITIAL_TASK:
        raise ValueError("Codex Goal host run must start with the frozen initial task")
    for expected_sequence, turn in enumerate(turns, start=1):
        if turn.sequence != expected_sequence:
            raise ValueError("Codex Goal host turn sequence is not contiguous")
        if expected_sequence == 1:
            continue
        previous = turns[expected_sequence - 2]
        if turn.previous_turn_sha256 != previous.turn_sha256:
            raise ValueError("Codex Goal host turn chain is broken")
        if turn.goal_tokens_before != previous.goal_tokens_after:
            raise ValueError("Codex Goal host usage is not continuous across turns")
        if previous.goal_status_after != "active":
            raise ValueError("Codex Goal host continued after a terminal or paused status")
        if turn.source is CodexGoalTurnSource.INITIAL_TASK:
            raise ValueError("Codex Goal host run contains multiple initial turns")
