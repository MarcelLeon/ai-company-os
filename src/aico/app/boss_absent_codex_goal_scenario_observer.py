"""Independent hash-chain observations for formal Codex Goal benchmark tasks."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from collections.abc import Callable, Sequence
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from aico.app.boss_absent_aico_im import (
    AicoImDecision,
    AicoImDecisionReceipt,
    AicoImExchangeKind,
)
from aico.app.boss_absent_codex_goal_evidence import (
    CodexGoalRoleEvidence,
    CodexGoalScenarioEvidenceReceipt,
)
from aico.app.boss_absent_codex_goal_host import (
    CodexGoalHostAdmissionReceipt,
    CodexGoalHostRunReceipt,
    CodexGoalTurnSource,
)
from aico.app.boss_absent_codex_goal_role_observer import (
    observe_codex_goal_role_chain,
)
from aico.core.boss_absent_benchmark import (
    BenchmarkEvidenceProof,
    BenchmarkEvidenceSet,
    BenchmarkEvidenceStatus,
    BenchmarkScenario,
    BenchmarkTerminalStatus,
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    canonical_sha256,
)
from aico.core.models import FrozenModel, utc_now

_MAX_LEDGER_BYTES = 2_097_152
_MAX_PROOF_BYTES = 65_536
_MAX_SOURCE_BYTES = 1_048_576
_MAX_SESSION_BYTES = 268_435_456


class CodexGoalScenarioObservationKind(StrEnum):
    ROLE_CHAIN = "native_role_chain_verified"
    FIXTURE = "fixture_fingerprinted"
    RESTART = "host_restart_verified"
    DRIFT = "fixture_drift_verified"
    APPROVAL_REQUEST = "approval_request_verified"
    APPROVAL_GRANT = "approval_grant_verified"
    APPROVAL_ACTION = "approval_action_verified"
    SOURCE_PRESSURE = "source_pressure_verified"
    ACCEPTANCE = "acceptance_verified"
    TEST_GATE = "test_gate_verified"
    BUDGET = "budget_verified"
    TAKEOVER = "takeover_verified"
    TERMINAL = "terminal_verified"


class CodexGoalScenarioObservation(FrozenModel):
    version: Literal[1] = 1
    sequence: int = Field(ge=1, le=64)
    previous_event_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    kind: CodexGoalScenarioObservationKind
    observed_at: datetime
    proof_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    role_chain_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    roles: tuple[CodexGoalRoleEvidence, ...] = Field(default=(), max_length=32)
    checkpoint_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    child_session_sha256s: tuple[str, ...] = Field(default=(), max_length=32)
    runtime_before_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    runtime_after_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_before_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_after_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    mutation_set_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    request_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    grant_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    action_receipt_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    owner_turn_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    total_tokens: int | None = Field(default=None, ge=0)
    terminal_status: BenchmarkTerminalStatus | None = None
    passed: bool | None = None
    actions: int | None = Field(default=None, ge=0)
    elapsed_seconds: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_time(self) -> CodexGoalScenarioObservation:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("Codex Goal scenario observation time must be timezone-aware")
        return self


class CodexGoalScenarioObservationLedger(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    host_admission_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    host_run_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observer_build: str = Field(min_length=1, max_length=128)
    started_at: datetime
    events: tuple[CodexGoalScenarioObservation, ...] = Field(default=(), max_length=64)

    @model_validator(mode="after")
    def validate_chain(self) -> CodexGoalScenarioObservationLedger:
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise ValueError("Codex Goal scenario ledger start time must be timezone-aware")
        previous: str | None = None
        for sequence, event in enumerate(self.events, start=1):
            if event.sequence != sequence or event.previous_event_sha256 != previous:
                raise ValueError("Codex Goal scenario observation hash chain is invalid")
            if event.observed_at < self.started_at:
                raise ValueError("Codex Goal scenario observation predates the ledger")
            previous = canonical_sha256(event)
        return self


class CodexGoalExternalCheckReceipt(FrozenModel):
    version: Literal[1] = 1
    check_kind: Literal["acceptance", "test_gate"]
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    host_run_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checked_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    passed: bool


class CodexGoalTerminalObservationReceipt(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    host_run_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumed_checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal[BenchmarkTerminalStatus.COMPLETE]


class CodexGoalApprovalActionObservationReceipt(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    host_run_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    grant_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_turn_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mutation_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_count: Literal[1] = 1


class JsonCodexGoalScenarioObservationStore:
    """Atomic owner-only scenario ledger controlled outside the native host."""

    def __init__(self, path: Path) -> None:
        if not path.is_absolute():
            raise ValueError("Codex Goal scenario observation path must be absolute")
        self._path = path

    def load(self) -> CodexGoalScenarioObservationLedger | None:
        if self._path.is_symlink():
            raise ValueError("Codex Goal scenario observation ledger is unsafe")
        if not self._path.exists():
            return None
        payload = _read_owner_file(self._path, _MAX_LEDGER_BYTES)
        try:
            return CodexGoalScenarioObservationLedger.model_validate_json(payload)
        except ValueError:
            raise ValueError("Codex Goal scenario observation ledger is invalid") from None

    def save(self, ledger: CodexGoalScenarioObservationLedger) -> None:
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self._path.is_symlink():
            raise ValueError("Codex Goal scenario observation ledger is unsafe")
        if self._path.exists():
            _read_owner_file(self._path, _MAX_LEDGER_BYTES)
        payload = ledger.model_dump_json(indent=2).encode() + b"\n"
        if len(payload) > _MAX_LEDGER_BYTES:
            raise ValueError("Codex Goal scenario observation ledger exceeds bounded size")
        _atomic_replace(self._path, payload)


class _CodexGoalObserverSupport:
    _task: BossAbsentTask
    _store: JsonCodexGoalScenarioObservationStore
    _clock: Callable[[], datetime]

    def _record(
        self,
        kind: CodexGoalScenarioObservationKind,
        *,
        proof_sha256: str,
        **fields: object,
    ) -> CodexGoalScenarioObservation:
        ledger = self._ledger()
        if any(event.kind is kind for event in ledger.events):
            raise ValueError(f"Codex Goal scenario observation already recorded: {kind.value}")
        event = CodexGoalScenarioObservation.model_validate(
            {
                "sequence": len(ledger.events) + 1,
                "previous_event_sha256": (
                    None if not ledger.events else canonical_sha256(ledger.events[-1])
                ),
                "kind": kind,
                "observed_at": self._clock(),
                "proof_sha256": proof_sha256,
                **fields,
            }
        )
        self._store.save(ledger.model_copy(update={"events": (*ledger.events, event)}))
        return event

    def _one(self, kind: CodexGoalScenarioObservationKind) -> CodexGoalScenarioObservation:
        matches = tuple(event for event in self._ledger().events if event.kind is kind)
        if len(matches) != 1:
            raise ValueError(f"Codex Goal scenario observation missing: {kind.value}")
        return matches[0]

    def _optional(
        self,
        kind: CodexGoalScenarioObservationKind,
    ) -> CodexGoalScenarioObservation | None:
        matches = tuple(event for event in self._ledger().events if event.kind is kind)
        if len(matches) > 1:
            raise ValueError(f"Codex Goal scenario observation duplicated: {kind.value}")
        return matches[0] if matches else None

    def _ledger(self) -> CodexGoalScenarioObservationLedger:
        ledger = self._store.load()
        if ledger is None:
            raise ValueError("Codex Goal scenario observation ledger disappeared")
        return ledger


class IndependentCodexGoalScenarioObserver(_CodexGoalObserverSupport):
    """Derive a formal receipt from raw native sessions and harness-owned proofs."""

    def __init__(
        self,
        contract: BossAbsentBenchmarkContract,
        task: BossAbsentTask,
        admission: CodexGoalHostAdmissionReceipt,
        host_run: CodexGoalHostRunReceipt,
        store: JsonCodexGoalScenarioObservationStore,
        *,
        observer_build: str,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._contract = contract
        self._task = task
        self._admission = admission
        self._host_run = host_run
        self._store = store
        self._clock = clock
        contract_sha = canonical_sha256(contract)
        admission_sha = canonical_sha256(admission)
        identity = (
            admission.contract_sha256 == contract_sha
            and host_run.contract_sha256 == contract_sha
            and host_run.host_admission_sha256 == admission_sha
        )
        if not identity:
            raise ValueError("Codex Goal scenario observer host identity drifted")
        existing = store.load()
        if existing is None:
            existing = CodexGoalScenarioObservationLedger(
                contract_sha256=contract_sha,
                task_id=task.task_id,
                host_admission_sha256=admission_sha,
                host_run_sha256=canonical_sha256(host_run),
                observer_build=observer_build,
                started_at=clock(),
            )
            store.save(existing)
        expected = (
            contract_sha,
            task.task_id,
            admission_sha,
            canonical_sha256(host_run),
            observer_build,
        )
        actual = (
            existing.contract_sha256,
            existing.task_id,
            existing.host_admission_sha256,
            existing.host_run_sha256,
            existing.observer_build,
        )
        if actual != expected:
            raise ValueError("Codex Goal scenario observation ledger identity drifted")

    def observe_role_sessions(
        self,
        *,
        codex_home: Path,
        parent_session_path: Path,
        child_session_paths: Sequence[Path],
    ) -> CodexGoalScenarioObservation:
        receipt = observe_codex_goal_role_chain(
            self._contract,
            self._task,
            self._host_run,
            codex_home=codex_home,
            parent_session_path=parent_session_path,
            child_session_paths=child_session_paths,
        )
        identity = (
            receipt.contract_sha256 == canonical_sha256(self._contract)
            and receipt.task_id == self._task.task_id
            and receipt.host_run_sha256 == canonical_sha256(self._host_run)
            and tuple(role.role for role in receipt.roles) == self._task.required_roles
        )
        if not identity:
            raise ValueError("Codex Goal observed role-chain receipt identity drifted")
        return self._record(
            CodexGoalScenarioObservationKind.ROLE_CHAIN,
            proof_sha256=canonical_sha256(receipt),
            role_chain_sha256=canonical_sha256(receipt),
            roles=receipt.roles,
            checkpoint_sha256=receipt.roles[-1].artifact_sha256,
            child_session_sha256s=receipt.child_session_sha256s,
        )

    def observe_fixture(self, path: Path) -> CodexGoalScenarioObservation:
        payload = _read_regular_file(path, _MAX_SOURCE_BYTES)
        expected = self._task.fixture.encode()
        if payload != expected:
            raise ValueError("Codex Goal frozen fixture bytes do not match the task")
        digest = _sha(payload)
        return self._record(
            CodexGoalScenarioObservationKind.FIXTURE,
            proof_sha256=digest,
            source_before_sha256=digest,
        )

    def observe_restart(self) -> CodexGoalScenarioObservation:
        role_chain = self._one(CodexGoalScenarioObservationKind.ROLE_CHAIN)
        roles = role_chain.roles
        if (
            not self._task.restart_required
            or len(roles) < 2
            or roles[0].runtime_instance_sha256 == roles[1].runtime_instance_sha256
        ):
            raise ValueError("Codex Goal observer did not see the required host restart")
        return self._record(
            CodexGoalScenarioObservationKind.RESTART,
            proof_sha256=_sha_join(
                (
                    canonical_sha256(self._host_run),
                    roles[0].runtime_instance_sha256,
                    roles[1].runtime_instance_sha256,
                )
            ),
            runtime_before_sha256=roles[0].runtime_instance_sha256,
            runtime_after_sha256=roles[1].runtime_instance_sha256,
        )

    def observe_drift(self, path: Path) -> CodexGoalScenarioObservation:
        fixture = self._one(CodexGoalScenarioObservationKind.FIXTURE)
        after = _sha(_read_regular_file(path, _MAX_SOURCE_BYTES))
        if after == fixture.source_before_sha256:
            raise ValueError("Codex Goal drift observer did not see changed fixture bytes")
        return self._record(
            CodexGoalScenarioObservationKind.DRIFT,
            proof_sha256=_sha_join((fixture.proof_sha256, after)),
            source_before_sha256=fixture.source_before_sha256,
            source_after_sha256=after,
        )

    def observe_source_pressure(
        self,
        irrelevant_path: Path,
        child_session_paths: Sequence[Path],
    ) -> CodexGoalScenarioObservation:
        role_chain = self._one(CodexGoalScenarioObservationKind.ROLE_CHAIN)
        payload = _read_regular_file(irrelevant_path, _MAX_SOURCE_BYTES)
        fixture_sha = _sha(self._task.fixture.encode())
        if _sha(payload) == fixture_sha:
            raise ValueError("Codex Goal irrelevant source matches the frozen fixture")
        sessions = tuple(_read_owner_file(path, _MAX_SESSION_BYTES) for path in child_session_paths)
        if tuple(_sha(item) for item in sessions) != role_chain.child_session_sha256s:
            raise ValueError("Codex Goal source-pressure child session drifted")
        probes = _source_probes(payload)
        if any(probe in session for probe in probes for session in sessions):
            raise ValueError("Codex Goal role session consumed the irrelevant source")
        return self._record(
            CodexGoalScenarioObservationKind.SOURCE_PRESSURE,
            proof_sha256=_sha_join((fixture_sha, _sha(payload), *role_chain.child_session_sha256s)),
            source_before_sha256=fixture_sha,
            source_after_sha256=_sha(payload),
            passed=True,
        )

    def observe_external_check(self, path: Path) -> CodexGoalScenarioObservation:
        payload = _read_owner_file(path, _MAX_PROOF_BYTES)
        try:
            receipt = CodexGoalExternalCheckReceipt.model_validate_json(payload)
        except ValueError:
            raise ValueError("Codex Goal external check receipt is invalid") from None
        role_chain = self._one(CodexGoalScenarioObservationKind.ROLE_CHAIN)
        kind = (
            CodexGoalScenarioObservationKind.ACCEPTANCE
            if receipt.check_kind == "acceptance"
            else CodexGoalScenarioObservationKind.TEST_GATE
        )
        identity = (
            receipt.contract_sha256 == canonical_sha256(self._contract)
            and receipt.task_id == self._task.task_id
            and receipt.host_run_sha256 == canonical_sha256(self._host_run)
            and receipt.checked_artifact_sha256 == role_chain.checkpoint_sha256
            and receipt.passed
        )
        if not identity:
            raise ValueError("Codex Goal external check did not pass for the observed artifact")
        return self._record(
            kind,
            proof_sha256=_sha(payload),
            checkpoint_sha256=receipt.checked_artifact_sha256,
            passed=True,
        )

    def observe_budget(self) -> CodexGoalScenarioObservation:
        self._one(CodexGoalScenarioObservationKind.ROLE_CHAIN)
        if self._host_run.total_tokens > self._contract.max_total_tokens:
            raise ValueError("Codex Goal observed provider usage exceeded the budget")
        return self._record(
            CodexGoalScenarioObservationKind.BUDGET,
            proof_sha256=_sha_join(
                (
                    canonical_sha256(self._host_run),
                    str(self._host_run.total_tokens),
                    str(self._contract.max_total_tokens),
                )
            ),
            total_tokens=self._host_run.total_tokens,
            passed=True,
        )

    def observe_approval_request(
        self,
        mutation_targets: Sequence[Path],
    ) -> CodexGoalScenarioObservation:
        request_sha = _approval_request_sha(self._contract, self._task)
        snapshot = _mutation_snapshot(mutation_targets)
        return self._record(
            CodexGoalScenarioObservationKind.APPROVAL_REQUEST,
            proof_sha256=_sha_join((request_sha, snapshot)),
            mutation_set_sha256=snapshot,
            request_sha256=request_sha,
        )

    def observe_approval_grant(
        self,
        decision_receipt_path: Path,
        mutation_targets: Sequence[Path],
    ) -> CodexGoalScenarioObservation:
        request = self._one(CodexGoalScenarioObservationKind.APPROVAL_REQUEST)
        payload = _read_owner_file(decision_receipt_path, _MAX_PROOF_BYTES)
        try:
            decision = AicoImDecisionReceipt.model_validate_json(payload)
        except ValueError:
            raise ValueError("Codex Goal approval IM decision is invalid") from None
        grant_sha = _sha(payload)
        snapshot = _mutation_snapshot(mutation_targets)
        identity = (
            decision.kind is AicoImExchangeKind.APPROVAL
            and decision.decision is AicoImDecision.APPROVED
            and decision.contract_sha256 == canonical_sha256(self._contract)
            and decision.task_id == self._task.task_id
            and decision.subject_sha256 == request.request_sha256
            and decision.actions <= self._contract.takeover_action_cap
            and decision.elapsed_seconds <= self._contract.takeover_seconds_cap
            and snapshot == request.mutation_set_sha256
        )
        if not identity:
            raise ValueError("Codex Goal approval grant or pre-mutation fence drifted")
        return self._record(
            CodexGoalScenarioObservationKind.APPROVAL_GRANT,
            proof_sha256=_sha_join((request.proof_sha256, grant_sha, snapshot)),
            mutation_set_sha256=snapshot,
            request_sha256=request.request_sha256,
            grant_sha256=grant_sha,
            actions=decision.actions,
            elapsed_seconds=decision.elapsed_seconds,
        )

    def observe_approval_action(
        self,
        path: Path,
        mutation_targets: Sequence[Path],
    ) -> CodexGoalScenarioObservation:
        grant = self._one(CodexGoalScenarioObservationKind.APPROVAL_GRANT)
        payload = _read_owner_file(path, _MAX_PROOF_BYTES)
        try:
            receipt = CodexGoalApprovalActionObservationReceipt.model_validate_json(payload)
        except ValueError:
            raise ValueError("Codex Goal approval action receipt is invalid") from None
        owner_turns = tuple(
            turn
            for turn in self._host_run.turns
            if turn.source is CodexGoalTurnSource.OWNER_TAKEOVER
        )
        snapshot = _mutation_snapshot(mutation_targets)
        identity = (
            len(owner_turns) == 1
            and receipt.contract_sha256 == canonical_sha256(self._contract)
            and receipt.task_id == self._task.task_id
            and receipt.host_run_sha256 == canonical_sha256(self._host_run)
            and receipt.request_sha256 == grant.request_sha256
            and receipt.grant_sha256 == grant.grant_sha256
            and receipt.owner_turn_sha256 == owner_turns[0].turn_sha256
            and owner_turns[0].opaque_input_sha256 == grant.grant_sha256
            and receipt.mutation_set_sha256 == snapshot
            and snapshot != grant.mutation_set_sha256
        )
        if not identity:
            raise ValueError("Codex Goal approval action did not match the exact owner grant")
        return self._record(
            CodexGoalScenarioObservationKind.APPROVAL_ACTION,
            proof_sha256=_sha(payload),
            mutation_set_sha256=snapshot,
            request_sha256=receipt.request_sha256,
            grant_sha256=receipt.grant_sha256,
            action_receipt_sha256=_sha(payload),
            owner_turn_sha256=receipt.owner_turn_sha256,
        )

    def observe_takeover(self, decision_receipt_path: Path) -> CodexGoalScenarioObservation:
        role_chain = self._one(CodexGoalScenarioObservationKind.ROLE_CHAIN)
        payload = _read_owner_file(decision_receipt_path, _MAX_PROOF_BYTES)
        try:
            decision = AicoImDecisionReceipt.model_validate_json(payload)
        except ValueError:
            raise ValueError("Codex Goal takeover IM decision is invalid") from None
        identity = (
            decision.kind is AicoImExchangeKind.TAKEOVER
            and decision.decision is AicoImDecision.ACKNOWLEDGED
            and decision.contract_sha256 == canonical_sha256(self._contract)
            and decision.task_id == self._task.task_id
            and decision.subject_sha256 == role_chain.checkpoint_sha256
            and decision.actions <= self._contract.takeover_action_cap
            and decision.elapsed_seconds <= self._contract.takeover_seconds_cap
        )
        if not identity:
            raise ValueError("Codex Goal takeover decision references another task or exceeds caps")
        return self._record(
            CodexGoalScenarioObservationKind.TAKEOVER,
            proof_sha256=_sha(payload),
            checkpoint_sha256=role_chain.checkpoint_sha256,
            actions=decision.actions,
            elapsed_seconds=decision.elapsed_seconds,
        )

    def observe_terminal(self, path: Path) -> CodexGoalScenarioObservation:
        role_chain = self._one(CodexGoalScenarioObservationKind.ROLE_CHAIN)
        payload = _read_owner_file(path, _MAX_PROOF_BYTES)
        try:
            receipt = CodexGoalTerminalObservationReceipt.model_validate_json(payload)
        except ValueError:
            raise ValueError("Codex Goal terminal observation receipt is invalid") from None
        identity = (
            receipt.contract_sha256 == canonical_sha256(self._contract)
            and receipt.task_id == self._task.task_id
            and receipt.host_run_sha256 == canonical_sha256(self._host_run)
            and receipt.consumed_checkpoint_sha256 == role_chain.checkpoint_sha256
            and self._host_run.terminal_status == "complete"
        )
        if not identity:
            raise ValueError("Codex Goal terminal did not consume the final role artifact")
        return self._record(
            CodexGoalScenarioObservationKind.TERMINAL,
            proof_sha256=_sha(payload),
            checkpoint_sha256=receipt.consumed_checkpoint_sha256,
            terminal_status=receipt.status,
        )

    def build_receipt(self) -> CodexGoalScenarioEvidenceReceipt:
        events = _RequiredEvents(self)
        events.validate_scenario(self._task)
        ledger = self._ledger()
        source = events.drift or events.pressure or events.fixture
        return CodexGoalScenarioEvidenceReceipt(
            contract_sha256=ledger.contract_sha256,
            task_id=ledger.task_id,
            host_admission_sha256=ledger.host_admission_sha256,
            host_run_sha256=ledger.host_run_sha256,
            role_chain_observation_sha256=events.roles.role_chain_sha256 or "",
            observer_build=ledger.observer_build,
            events_sha256=canonical_sha256(ledger),
            terminal_status=events.terminal.terminal_status or BenchmarkTerminalStatus.INCOMPLETE,
            terminal_consumed_checkpoint_sha256=events.terminal.checkpoint_sha256 or "",
            wall_seconds=(events.terminal.observed_at - ledger.started_at).total_seconds(),
            human_interventions=int(self._task.approval_required),
            evidence=BenchmarkEvidenceSet(
                terminal=_proof(events.terminal),
                acceptance=_proof(events.acceptance),
                source_integrity=_proof(source),
                test_gate=_proof(events.test_gate),
                budget_receipt=_proof(events.budget),
            ),
            roles=events.roles.roles,
            restart_observed=events.restart is not None,
            replayed_turns=0,
            restart_evidence_sha256=_optional_sha(events.restart),
            takeover_actions=None if events.takeover is None else events.takeover.actions,
            takeover_seconds=(None if events.takeover is None else events.takeover.elapsed_seconds),
            takeover_evidence_sha256=_optional_sha(events.takeover),
            approval_requests=int(events.approval_request is not None),
            approval_grants=int(events.approval_grant is not None),
            approval_evidence_sha256=_optional_sha(events.approval_action),
            approval_request_sha256=_field(events.approval_action, "request_sha256"),
            approval_grant_sha256=_field(events.approval_action, "grant_sha256"),
            approval_action_receipt_sha256=_field(
                events.approval_action,
                "action_receipt_sha256",
            ),
            approval_turn_sha256=_field(events.approval_action, "owner_turn_sha256"),
            evidence_drift_injected=events.drift is not None,
            evidence_drift_detected=events.drift is not None,
            irrelevant_source_exposed=events.pressure is not None,
        )


class _RequiredEvents:
    def __init__(self, observer: _CodexGoalObserverSupport) -> None:
        one = observer._one
        optional = observer._optional
        self.roles = one(CodexGoalScenarioObservationKind.ROLE_CHAIN)
        self.fixture = one(CodexGoalScenarioObservationKind.FIXTURE)
        self.acceptance = one(CodexGoalScenarioObservationKind.ACCEPTANCE)
        self.test_gate = one(CodexGoalScenarioObservationKind.TEST_GATE)
        self.budget = one(CodexGoalScenarioObservationKind.BUDGET)
        self.terminal = one(CodexGoalScenarioObservationKind.TERMINAL)
        self.restart = optional(CodexGoalScenarioObservationKind.RESTART)
        self.drift = optional(CodexGoalScenarioObservationKind.DRIFT)
        self.approval_request = optional(CodexGoalScenarioObservationKind.APPROVAL_REQUEST)
        self.approval_grant = optional(CodexGoalScenarioObservationKind.APPROVAL_GRANT)
        self.approval_action = optional(CodexGoalScenarioObservationKind.APPROVAL_ACTION)
        self.pressure = optional(CodexGoalScenarioObservationKind.SOURCE_PRESSURE)
        self.takeover = optional(CodexGoalScenarioObservationKind.TAKEOVER)

    def validate_scenario(self, task: BossAbsentTask) -> None:
        observed = (
            self.restart is not None,
            self.drift is not None,
            self.approval_request is not None
            and self.approval_grant is not None
            and self.approval_action is not None,
            self.pressure is not None,
            self.takeover is not None,
        )
        expected = (
            task.restart_required,
            task.scenario is BenchmarkScenario.EVIDENCE_DRIFT,
            task.approval_required,
            task.budget_pressure,
            task.im_takeover_required,
        )
        if observed != expected:
            raise ValueError("Codex Goal scenario events do not match the frozen task")


def _proof(event: CodexGoalScenarioObservation) -> BenchmarkEvidenceProof:
    return BenchmarkEvidenceProof(
        status=BenchmarkEvidenceStatus.PRESENT,
        sha256=canonical_sha256(event),
    )


def _optional_sha(event: CodexGoalScenarioObservation | None) -> str | None:
    return None if event is None else canonical_sha256(event)


def _field(
    event: CodexGoalScenarioObservation | None,
    name: str,
) -> str | None:
    return None if event is None else getattr(event, name)


def _approval_request_sha(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
) -> str:
    return _sha_join(
        (
            "codex-goal-approval-v1",
            canonical_sha256(contract),
            task.task_id,
            canonical_sha256(task),
        )
    )


def _source_probes(payload: bytes) -> tuple[bytes, ...]:
    if len(payload) < 96:
        raise ValueError("Codex Goal irrelevant source lacks three independent probes")
    middle = len(payload) // 2
    return payload[:32], payload[middle : middle + 32], payload[-32:]


def _mutation_snapshot(paths: Sequence[Path]) -> str:
    if not paths:
        raise ValueError("Codex Goal approval mutation target set is empty")
    observations: list[str] = []
    for index, path in enumerate(paths):
        if path.is_symlink() or path.parent.is_symlink() or not path.parent.is_dir():
            raise ValueError("Codex Goal approval mutation target is unsafe")
        parent = path.parent.stat()
        generation = f"{parent.st_dev}:{parent.st_ino}:{parent.st_mtime_ns}:{parent.st_ctime_ns}"
        if path.exists():
            payload = _read_regular_file(path, _MAX_PROOF_BYTES)
            target = path.stat()
            generation += (
                f":{target.st_dev}:{target.st_ino}:{target.st_size}:"
                f"{target.st_mtime_ns}:{target.st_ctime_ns}"
            )
        else:
            payload = b"<missing>"
            generation += ":missing"
        observations.append(f"{index}:{_sha(payload)}:{generation}")
    return _sha_join(observations)


def _read_regular_file(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Codex Goal scenario proof file is unsafe")
    with path.open("rb") as source:
        payload = source.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("Codex Goal scenario proof file is oversized")
    return payload


def _read_owner_file(path: Path, limit: int) -> bytes:
    payload = _read_regular_file(path, limit)
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o022:
        raise ValueError("Codex Goal scenario proof ownership or permissions are unsafe")
    return payload


def _atomic_replace(path: Path, payload: bytes) -> None:
    descriptor, raw = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(raw)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha_join(values: Sequence[str]) -> str:
    return hashlib.sha256("\0".join(values).encode()).hexdigest()
