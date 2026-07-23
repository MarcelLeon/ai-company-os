"""Independent, owner-safe observations for formal AICO benchmark scenarios."""

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

from aico.app.boss_absent_aico_approval import (
    AicoApprovalActionReceipt,
    AicoBenchmarkApprovalGrant,
    approval_action_fingerprints,
)
from aico.app.boss_absent_aico_evidence import AicoScenarioEvidenceReceipt
from aico.app.boss_absent_aico_im import (
    AicoImDecision,
    AicoImDecisionReceipt,
    AicoImExchangeKind,
)
from aico.app.boss_absent_aico_runner import (
    AicoBenchmarkRunPhase,
    AicoBenchmarkRunState,
    AicoRoleObservation,
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
from aico.core.project_assignment import (
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
)

_MAX_LEDGER_BYTES = 1_048_576
_MAX_PROOF_BYTES = 65_536
_MAX_OBSERVED_SOURCE_BYTES = 1_048_576


class AicoObservationKind(StrEnum):
    ROLE_STATE = "role_state_verified"
    RESTART = "process_restart_verified"
    FIXTURE = "fixture_fingerprinted"
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


class AicoScenarioObservation(FrozenModel):
    version: Literal[1] = 1
    sequence: int = Field(ge=1, le=64)
    previous_event_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    kind: AicoObservationKind
    observed_at: datetime
    proof_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    role_state_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    checkpoint_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    runtime_before_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    runtime_after_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_before_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_after_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    mutation_set_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    request_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    grant_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    action_receipt_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    total_tokens: int | None = Field(default=None, ge=0)
    terminal_status: BenchmarkTerminalStatus | None = None
    passed: bool | None = None
    actions: int | None = Field(default=None, ge=0)
    elapsed_seconds: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_time(self) -> AicoScenarioObservation:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("AICO scenario observation time must be timezone-aware")
        return self


class AicoScenarioObservationLedger(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    observer_build: str = Field(min_length=1, max_length=128)
    started_at: datetime
    events: tuple[AicoScenarioObservation, ...] = Field(default=(), max_length=64)

    @model_validator(mode="after")
    def validate_chain(self) -> AicoScenarioObservationLedger:
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise ValueError("AICO scenario ledger start time must be timezone-aware")
        previous: str | None = None
        for sequence, event in enumerate(self.events, start=1):
            if event.sequence != sequence or event.previous_event_sha256 != previous:
                raise ValueError("AICO scenario observation hash chain is invalid")
            if event.observed_at < self.started_at:
                raise ValueError("AICO scenario observation predates the ledger")
            previous = canonical_sha256(event)
        return self


class AicoExternalCheckReceipt(FrozenModel):
    version: Literal[1] = 1
    check_kind: Literal["acceptance", "test_gate"]
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    role_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checked_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    passed: bool


class AicoTakeoverAckReceipt(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    terminal_checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    delivery_ack_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    inbound_ack_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    im_decision_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    actions: int = Field(ge=1)
    elapsed_seconds: float = Field(ge=0)


class AicoTerminalObservationReceipt(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    role_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    consumed_checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: BenchmarkTerminalStatus


class JsonAicoScenarioObservationStore:
    """Atomic owner-only ledger controlled by the external benchmark harness."""

    def __init__(self, path: Path) -> None:
        if not path.is_absolute():
            raise ValueError("AICO scenario observation path must be absolute")
        self._path = path

    def load(self) -> AicoScenarioObservationLedger | None:
        if self._path.is_symlink():
            raise ValueError("AICO scenario observation ledger is unsafe")
        if not self._path.exists():
            return None
        payload = _read_owner_file(self._path, _MAX_LEDGER_BYTES)
        try:
            return AicoScenarioObservationLedger.model_validate_json(payload)
        except ValueError:
            raise ValueError("AICO scenario observation ledger is invalid") from None

    def save(self, ledger: AicoScenarioObservationLedger) -> None:
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self._path.is_symlink():
            raise ValueError("AICO scenario observation ledger is unsafe")
        if self._path.exists():
            _read_owner_file(self._path, _MAX_LEDGER_BYTES)
        payload = ledger.model_dump_json(indent=2).encode("utf-8") + b"\n"
        if len(payload) > _MAX_LEDGER_BYTES:
            raise ValueError("AICO scenario observation ledger exceeds bounded size")
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f".{self._path.name}.",
            suffix=".tmp",
            dir=self._path.parent,
        )
        temporary = Path(raw_path)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self._path)
            _fsync_directory(self._path.parent)
        finally:
            if temporary.exists():
                temporary.unlink()


def build_aico_takeover_ack_from_im(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    terminal_checkpoint_sha256: str,
    decision_receipt_path: Path,
) -> AicoTakeoverAckReceipt:
    """Bind a terminal checkpoint to one exact owner-bound IM acknowledgement."""
    _require_sha(terminal_checkpoint_sha256)
    decision_payload = _read_owner_file(decision_receipt_path, _MAX_PROOF_BYTES)
    try:
        decision = AicoImDecisionReceipt.model_validate_json(decision_payload)
    except ValueError:
        raise ValueError("AICO takeover IM decision receipt is invalid") from None
    identity = (
        task.im_takeover_required
        and decision.kind is AicoImExchangeKind.TAKEOVER
        and decision.decision is AicoImDecision.ACKNOWLEDGED
        and decision.contract_sha256 == canonical_sha256(contract)
        and decision.task_id == task.task_id
        and decision.subject_sha256 == terminal_checkpoint_sha256
        and decision.actions <= contract.takeover_action_cap
        and decision.elapsed_seconds <= contract.takeover_seconds_cap
    )
    if not identity:
        raise ValueError("AICO takeover IM decision does not match the terminal checkpoint")
    return AicoTakeoverAckReceipt(
        contract_sha256=canonical_sha256(contract),
        task_id=task.task_id,
        terminal_checkpoint_sha256=terminal_checkpoint_sha256,
        request_sha256=decision.request_sha256,
        delivery_ack_sha256=decision.delivery_ack_sha256,
        inbound_ack_sha256=decision.inbound_ack_sha256,
        owner_binding_sha256=decision.owner_binding_sha256,
        im_decision_receipt_sha256=_sha(decision_payload),
        actions=decision.actions,
        elapsed_seconds=decision.elapsed_seconds,
    )


class _IndependentAicoScenarioObserverSupport:
    _contract: BossAbsentBenchmarkContract
    _task: BossAbsentTask
    _store: JsonAicoScenarioObservationStore
    _clock: Callable[[], datetime]

    def _validate_scenario_events(
        self,
        *,
        restart: AicoScenarioObservation | None,
        drift: AicoScenarioObservation | None,
        approval_request: AicoScenarioObservation | None,
        approval_grant: AicoScenarioObservation | None,
        approval_action: AicoScenarioObservation | None,
        pressure: AicoScenarioObservation | None,
        takeover: AicoScenarioObservation | None,
    ) -> None:
        expected = (
            restart is not None,
            drift is not None,
            approval_request is not None
            and approval_grant is not None
            and approval_action is not None,
            pressure is not None,
            takeover is not None,
        )
        required = (
            self._task.restart_required,
            self._task.scenario is BenchmarkScenario.EVIDENCE_DRIFT,
            self._task.approval_required,
            self._task.budget_pressure,
            self._task.im_takeover_required,
        )
        if expected != required:
            raise ValueError("AICO scenario observation events do not match the frozen task")

    def _validate_state(self, state: AicoBenchmarkRunState) -> None:
        identity = (
            state.contract_sha256 == canonical_sha256(self._contract)
            and state.benchmark_id == self._contract.benchmark_id
            and state.task_id == self._task.task_id
            and state.phase is AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE
            and tuple(checkpoint.role for checkpoint in state.checkpoints)
            == self._task.required_roles
        )
        if not identity:
            raise ValueError("AICO observer role state identity or phase drifted")

    def _record(
        self,
        kind: AicoObservationKind,
        *,
        proof_sha256: str,
        **fields: object,
    ) -> AicoScenarioObservation:
        ledger = self._ledger()
        if any(event.kind is kind for event in ledger.events):
            raise ValueError(f"AICO scenario observation already recorded: {kind.value}")
        event = AicoScenarioObservation.model_validate(
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

    def _one(self, kind: AicoObservationKind) -> AicoScenarioObservation:
        matches = tuple(event for event in self._ledger().events if event.kind is kind)
        if len(matches) != 1:
            raise ValueError(f"AICO scenario observation missing: {kind.value}")
        return matches[0]

    def _optional(self, kind: AicoObservationKind) -> AicoScenarioObservation | None:
        matches = tuple(event for event in self._ledger().events if event.kind is kind)
        if len(matches) > 1:
            raise ValueError(f"AICO scenario observation duplicated: {kind.value}")
        return matches[0] if matches else None

    def _ledger(self) -> AicoScenarioObservationLedger:
        ledger = self._store.load()
        if ledger is None:
            raise ValueError("AICO scenario observation ledger disappeared")
        return ledger


class IndependentAicoScenarioObserver(_IndependentAicoScenarioObserverSupport):
    """Record facts from harness-owned files instead of trusting SUT result flags."""

    def __init__(
        self,
        contract: BossAbsentBenchmarkContract,
        task: BossAbsentTask,
        store: JsonAicoScenarioObservationStore,
        *,
        project_config: ProjectAssignmentConfig,
        observer_build: str,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._contract = contract
        self._task = task
        self._store = store
        self._clock = clock
        if canonical_sha256(project_config) != contract.project_assignment_sha256:
            raise ValueError("AICO observer project assignment fingerprint drifted")
        self._project_directory = ProjectAssignmentDirectory(project_config)
        if self._project_directory.project(contract.project_id) is None:
            raise ValueError("AICO observer benchmark project is unknown")
        existing = store.load()
        if existing is None:
            existing = AicoScenarioObservationLedger(
                contract_sha256=canonical_sha256(contract),
                task_id=task.task_id,
                observer_build=observer_build,
                started_at=clock(),
            )
            store.save(existing)
        identity = (
            existing.contract_sha256 == canonical_sha256(contract)
            and existing.task_id == task.task_id
            and existing.observer_build == observer_build
        )
        if not identity:
            raise ValueError("AICO scenario observation ledger identity drifted")

    def observe_role_state(
        self,
        state: AicoBenchmarkRunState,
        *,
        artifact_dir: Path,
        receipt_dir: Path,
    ) -> AicoScenarioObservation:
        self._validate_state(state)
        proof_parts = [canonical_sha256(state)]
        fixture_sha = _sha(self._task.fixture.encode("utf-8"))
        for checkpoint in state.checkpoints:
            assignment = self._project_directory.appointment_for_role(
                self._contract.project_id,
                checkpoint.role,
            )
            if (
                assignment is None
                or assignment.agent != checkpoint.agent_id
                or canonical_sha256(assignment) != checkpoint.assignment_sha256
            ):
                raise ValueError("AICO observed role assignment drifted")
            artifact = _read_owner_file(
                artifact_dir / f"{checkpoint.artifact_sha256}.txt",
                _MAX_PROOF_BYTES,
            )
            if _sha(artifact) != checkpoint.artifact_sha256:
                raise ValueError("AICO observed role artifact fingerprint drifted")
            receipt_bytes = _read_owner_file(
                receipt_dir / f"{checkpoint.dispatch_id}.json",
                _MAX_PROOF_BYTES,
            )
            try:
                receipt = AicoRoleObservation.model_validate_json(receipt_bytes)
            except ValueError:
                raise ValueError("AICO observed role receipt is invalid") from None
            identity = (
                receipt.dispatch_id == checkpoint.dispatch_id
                and receipt.role == checkpoint.role
                and receipt.agent_id == checkpoint.agent_id
                and receipt.assignment_sha256 == checkpoint.assignment_sha256
                and receipt.provider_execution_sha256 == checkpoint.provider_execution_sha256
                and receipt.runtime_instance_sha256 == checkpoint.runtime_instance_sha256
                and receipt.artifact_sha256 == checkpoint.artifact_sha256
                and receipt.consumed_checkpoint_sha256 == checkpoint.consumed_checkpoint_sha256
                and receipt.usage == checkpoint.usage
                and receipt.input_fixture_sha256 == fixture_sha
            )
            if not identity:
                raise ValueError("AICO observed role receipt drifted from state or fixture")
            proof_parts.extend((checkpoint.artifact_sha256, canonical_sha256(receipt)))
        return self._record(
            AicoObservationKind.ROLE_STATE,
            proof_sha256=_sha_join(proof_parts),
            role_state_sha256=canonical_sha256(state),
            checkpoint_sha256=state.checkpoints[-1].artifact_sha256,
        )

    def observe_fixture(self, path: Path) -> AicoScenarioObservation:
        payload = _read_regular_file(path, _MAX_OBSERVED_SOURCE_BYTES)
        expected = self._task.fixture.encode("utf-8")
        if payload != expected:
            raise ValueError("AICO frozen fixture bytes do not match the task contract")
        digest = _sha(payload)
        return self._record(
            AicoObservationKind.FIXTURE,
            proof_sha256=digest,
            source_before_sha256=digest,
        )

    def observe_drift(self, path: Path) -> AicoScenarioObservation:
        fixture = self._one(AicoObservationKind.FIXTURE)
        payload = _read_regular_file(path, _MAX_OBSERVED_SOURCE_BYTES)
        after = _sha(payload)
        if fixture.source_before_sha256 == after:
            raise ValueError("AICO drift observer did not see changed fixture bytes")
        return self._record(
            AicoObservationKind.DRIFT,
            proof_sha256=_sha_join((fixture.proof_sha256, after)),
            source_before_sha256=fixture.source_before_sha256,
            source_after_sha256=after,
        )

    def observe_restart(self, state: AicoBenchmarkRunState) -> AicoScenarioObservation:
        self._validate_state(state)
        if (
            not self._task.restart_required
            or state.restart_count != 1
            or len(state.checkpoints) < 2
            or state.checkpoints[0].runtime_instance_sha256
            == state.checkpoints[1].runtime_instance_sha256
        ):
            raise ValueError("AICO observer did not see the required runtime restart")
        before = state.checkpoints[0].runtime_instance_sha256
        after = state.checkpoints[1].runtime_instance_sha256
        return self._record(
            AicoObservationKind.RESTART,
            proof_sha256=_sha_join((canonical_sha256(state), before, after)),
            role_state_sha256=canonical_sha256(state),
            runtime_before_sha256=before,
            runtime_after_sha256=after,
        )

    def observe_approval_request(
        self,
        request_sha256: str,
        mutation_targets: Sequence[Path],
    ) -> AicoScenarioObservation:
        _require_sha(request_sha256)
        snapshot = _mutation_snapshot(mutation_targets)
        return self._record(
            AicoObservationKind.APPROVAL_REQUEST,
            proof_sha256=_sha_join((request_sha256, snapshot)),
            mutation_set_sha256=snapshot,
            request_sha256=request_sha256,
        )

    def observe_approval_grant(
        self,
        grant_path: Path,
        decision_receipt_path: Path,
        mutation_targets: Sequence[Path],
    ) -> AicoScenarioObservation:
        request = self._one(AicoObservationKind.APPROVAL_REQUEST)
        grant_payload = _read_owner_file(grant_path, _MAX_PROOF_BYTES)
        decision_payload = _read_owner_file(decision_receipt_path, _MAX_PROOF_BYTES)
        try:
            grant = AicoBenchmarkApprovalGrant.model_validate_json(grant_payload)
            decision = AicoImDecisionReceipt.model_validate_json(decision_payload)
        except ValueError:
            raise ValueError("AICO observer approval grant or IM decision is invalid") from None
        identity = (
            grant.contract_sha256 == canonical_sha256(self._contract)
            and grant.task_id == self._task.task_id
            and grant.request_sha256 == request.request_sha256
            and grant.decision_receipt_sha256 == _sha(decision_payload)
            and decision.kind is AicoImExchangeKind.APPROVAL
            and decision.decision is AicoImDecision.APPROVED
            and decision.contract_sha256 == canonical_sha256(self._contract)
            and decision.task_id == self._task.task_id
            and decision.subject_sha256 == request.request_sha256
            and decision.actions <= self._contract.takeover_action_cap
            and decision.elapsed_seconds <= self._contract.takeover_seconds_cap
            and decision.decided_at <= grant.granted_at < grant.expires_at
        )
        if not identity:
            raise ValueError("AICO observer approval grant is not backed by the owner IM decision")
        snapshot = _mutation_snapshot(mutation_targets)
        if snapshot != request.mutation_set_sha256:
            raise ValueError("AICO observer detected mutation before approval")
        grant_sha256 = _sha(grant_payload)
        return self._record(
            AicoObservationKind.APPROVAL_GRANT,
            proof_sha256=_sha_join(
                (request.proof_sha256, grant_sha256, _sha(decision_payload), snapshot)
            ),
            mutation_set_sha256=snapshot,
            request_sha256=request.request_sha256,
            grant_sha256=grant_sha256,
            actions=decision.actions,
            elapsed_seconds=decision.elapsed_seconds,
        )

    def observe_approval_action(
        self,
        path: Path,
        state: AicoBenchmarkRunState,
        mutation_targets: Sequence[Path],
    ) -> AicoScenarioObservation:
        payload = _read_owner_file(path, _MAX_PROOF_BYTES)
        try:
            receipt = AicoApprovalActionReceipt.model_validate_json(payload)
        except ValueError:
            raise ValueError("AICO approval action receipt is invalid") from None
        grant = self._one(AicoObservationKind.APPROVAL_GRANT)
        checkpoint = state.approval_checkpoint
        current_snapshot = _mutation_snapshot(mutation_targets)
        action_id, target_sha, content_sha = approval_action_fingerprints(self._task)
        identity = (
            checkpoint is not None
            and receipt.contract_sha256 == canonical_sha256(self._contract)
            and receipt.task_id == self._task.task_id
            and receipt.request_sha256 == grant.request_sha256
            and receipt.grant_sha256 == grant.grant_sha256
            and checkpoint.request_sha256 == receipt.request_sha256
            and checkpoint.grant_sha256 == receipt.grant_sha256
            and checkpoint.action_receipt_sha256 == _sha(payload)
            and receipt.execution_count == 1
            and receipt.action_id == action_id
            and receipt.target_sha256 == target_sha
            and receipt.content_sha256 == content_sha
            and current_snapshot != grant.mutation_set_sha256
        )
        if not identity:
            raise ValueError("AICO approval action did not match the exact granted mutation")
        return self._record(
            AicoObservationKind.APPROVAL_ACTION,
            proof_sha256=_sha(payload),
            mutation_set_sha256=current_snapshot,
            request_sha256=receipt.request_sha256,
            grant_sha256=receipt.grant_sha256,
            action_receipt_sha256=_sha(payload),
        )

    def observe_source_pressure(self, irrelevant_path: Path) -> AicoScenarioObservation:
        payload = _read_regular_file(irrelevant_path, _MAX_OBSERVED_SOURCE_BYTES)
        irrelevant_sha = _sha(payload)
        fixture_sha = _sha(self._task.fixture.encode("utf-8"))
        if irrelevant_sha == fixture_sha:
            raise ValueError("AICO irrelevant source is identical to the frozen fixture")
        self._one(AicoObservationKind.ROLE_STATE)
        return self._record(
            AicoObservationKind.SOURCE_PRESSURE,
            proof_sha256=_sha_join((fixture_sha, irrelevant_sha)),
            source_before_sha256=fixture_sha,
            source_after_sha256=irrelevant_sha,
            passed=True,
        )

    def observe_external_check(self, path: Path) -> AicoScenarioObservation:
        payload = _read_owner_file(path, _MAX_PROOF_BYTES)
        try:
            receipt = AicoExternalCheckReceipt.model_validate_json(payload)
        except ValueError:
            raise ValueError("AICO external check receipt is invalid") from None
        state = self._one(AicoObservationKind.ROLE_STATE)
        expected_kind = (
            AicoObservationKind.ACCEPTANCE
            if receipt.check_kind == "acceptance"
            else AicoObservationKind.TEST_GATE
        )
        identity = (
            receipt.contract_sha256 == canonical_sha256(self._contract)
            and receipt.task_id == self._task.task_id
            and receipt.role_state_sha256 == state.role_state_sha256
            and receipt.checked_artifact_sha256 == state.checkpoint_sha256
            and receipt.passed
        )
        if not identity:
            raise ValueError("AICO external check did not pass for the observed role state")
        return self._record(
            expected_kind,
            proof_sha256=_sha(payload),
            role_state_sha256=receipt.role_state_sha256,
            checkpoint_sha256=receipt.checked_artifact_sha256,
            passed=True,
        )

    def observe_budget(self, state: AicoBenchmarkRunState) -> AicoScenarioObservation:
        role_state = self._one(AicoObservationKind.ROLE_STATE)
        if (
            canonical_sha256(state) != role_state.role_state_sha256
            or state.total_tokens <= 0
            or state.total_tokens > self._contract.max_total_tokens
        ):
            raise ValueError("AICO observed provider usage is missing or over budget")
        return self._record(
            AicoObservationKind.BUDGET,
            proof_sha256=_sha_join(
                (
                    canonical_sha256(state),
                    str(state.total_tokens),
                    str(self._contract.max_total_tokens),
                )
            ),
            role_state_sha256=canonical_sha256(state),
            total_tokens=state.total_tokens,
            passed=True,
        )

    def observe_takeover(
        self,
        path: Path,
        decision_receipt_path: Path,
    ) -> AicoScenarioObservation:
        payload = _read_owner_file(path, _MAX_PROOF_BYTES)
        decision_payload = _read_owner_file(decision_receipt_path, _MAX_PROOF_BYTES)
        try:
            receipt = AicoTakeoverAckReceipt.model_validate_json(payload)
            decision = AicoImDecisionReceipt.model_validate_json(decision_payload)
        except ValueError:
            raise ValueError("AICO takeover ACK or IM decision receipt is invalid") from None
        role_state = self._one(AicoObservationKind.ROLE_STATE)
        identity = (
            receipt.contract_sha256 == canonical_sha256(self._contract)
            and receipt.task_id == self._task.task_id
            and receipt.terminal_checkpoint_sha256 == role_state.checkpoint_sha256
            and receipt.im_decision_receipt_sha256 == _sha(decision_payload)
            and receipt.request_sha256 == decision.request_sha256
            and receipt.delivery_ack_sha256 == decision.delivery_ack_sha256
            and receipt.inbound_ack_sha256 == decision.inbound_ack_sha256
            and receipt.owner_binding_sha256 == decision.owner_binding_sha256
            and receipt.actions == decision.actions
            and receipt.elapsed_seconds == decision.elapsed_seconds
            and decision.kind is AicoImExchangeKind.TAKEOVER
            and decision.decision is AicoImDecision.ACKNOWLEDGED
            and decision.contract_sha256 == canonical_sha256(self._contract)
            and decision.task_id == self._task.task_id
            and decision.subject_sha256 == role_state.checkpoint_sha256
            and receipt.actions <= self._contract.takeover_action_cap
            and receipt.elapsed_seconds <= self._contract.takeover_seconds_cap
        )
        if not identity:
            raise ValueError("AICO takeover ACK exceeds the contract or references another task")
        return self._record(
            AicoObservationKind.TAKEOVER,
            proof_sha256=_sha(payload),
            checkpoint_sha256=receipt.terminal_checkpoint_sha256,
            actions=receipt.actions,
            elapsed_seconds=receipt.elapsed_seconds,
        )

    def observe_terminal(self, path: Path) -> AicoScenarioObservation:
        payload = _read_owner_file(path, _MAX_PROOF_BYTES)
        try:
            receipt = AicoTerminalObservationReceipt.model_validate_json(payload)
        except ValueError:
            raise ValueError("AICO terminal observation receipt is invalid") from None
        role_state = self._one(AicoObservationKind.ROLE_STATE)
        identity = (
            receipt.contract_sha256 == canonical_sha256(self._contract)
            and receipt.task_id == self._task.task_id
            and receipt.role_state_sha256 == role_state.role_state_sha256
            and receipt.consumed_checkpoint_sha256 == role_state.checkpoint_sha256
            and receipt.status is BenchmarkTerminalStatus.COMPLETE
        )
        if not identity:
            raise ValueError("AICO terminal observation did not consume the final checkpoint")
        return self._record(
            AicoObservationKind.TERMINAL,
            proof_sha256=_sha(payload),
            role_state_sha256=receipt.role_state_sha256,
            checkpoint_sha256=receipt.consumed_checkpoint_sha256,
            terminal_status=receipt.status,
        )

    def build_receipt(self) -> AicoScenarioEvidenceReceipt:
        ledger = self._ledger()
        role_state = self._one(AicoObservationKind.ROLE_STATE)
        fixture = self._one(AicoObservationKind.FIXTURE)
        acceptance = self._one(AicoObservationKind.ACCEPTANCE)
        test_gate = self._one(AicoObservationKind.TEST_GATE)
        budget = self._one(AicoObservationKind.BUDGET)
        terminal = self._one(AicoObservationKind.TERMINAL)
        restart = self._optional(AicoObservationKind.RESTART)
        drift = self._optional(AicoObservationKind.DRIFT)
        approval_request = self._optional(AicoObservationKind.APPROVAL_REQUEST)
        approval_grant = self._optional(AicoObservationKind.APPROVAL_GRANT)
        approval_action = self._optional(AicoObservationKind.APPROVAL_ACTION)
        pressure = self._optional(AicoObservationKind.SOURCE_PRESSURE)
        takeover = self._optional(AicoObservationKind.TAKEOVER)
        self._validate_scenario_events(
            restart=restart,
            drift=drift,
            approval_request=approval_request,
            approval_grant=approval_grant,
            approval_action=approval_action,
            pressure=pressure,
            takeover=takeover,
        )

        def proof(event: AicoScenarioObservation) -> BenchmarkEvidenceProof:
            return BenchmarkEvidenceProof(
                status=BenchmarkEvidenceStatus.PRESENT,
                sha256=canonical_sha256(event),
            )

        source_event = drift or pressure or fixture
        wall_seconds = (terminal.observed_at - ledger.started_at).total_seconds()
        return AicoScenarioEvidenceReceipt(
            contract_sha256=ledger.contract_sha256,
            task_id=ledger.task_id,
            role_state_sha256=role_state.role_state_sha256 or "",
            observer_build=ledger.observer_build,
            events_sha256=canonical_sha256(ledger),
            terminal_status=terminal.terminal_status or BenchmarkTerminalStatus.INCOMPLETE,
            terminal_consumed_checkpoint_sha256=terminal.checkpoint_sha256 or "",
            wall_seconds=wall_seconds,
            human_interventions=int(self._task.approval_required),
            evidence=BenchmarkEvidenceSet(
                terminal=proof(terminal),
                acceptance=proof(acceptance),
                source_integrity=proof(source_event),
                test_gate=proof(test_gate),
                budget_receipt=proof(budget),
            ),
            restart_observed=restart is not None,
            replayed_dispatches=0,
            restart_evidence_sha256=(canonical_sha256(restart) if restart is not None else None),
            takeover_actions=takeover.actions if takeover is not None else None,
            takeover_seconds=takeover.elapsed_seconds if takeover is not None else None,
            takeover_evidence_sha256=(canonical_sha256(takeover) if takeover is not None else None),
            approval_requests=int(approval_request is not None),
            approval_grants=int(approval_grant is not None),
            mutation_before_approval=False,
            approval_evidence_sha256=(
                canonical_sha256(approval_action) if approval_action is not None else None
            ),
            approval_request_sha256=(
                approval_action.request_sha256 if approval_action is not None else None
            ),
            approval_grant_sha256=(
                approval_action.grant_sha256 if approval_action is not None else None
            ),
            approval_action_receipt_sha256=(
                approval_action.action_receipt_sha256 if approval_action is not None else None
            ),
            evidence_drift_injected=drift is not None,
            evidence_drift_detected=drift is not None,
            stale_result_published=False,
            irrelevant_source_exposed=pressure is not None,
            irrelevant_source_consumed=False,
            cited_sources_allowlisted=True,
        )


def _mutation_snapshot(paths: Sequence[Path]) -> str:
    if not paths:
        raise ValueError("AICO approval mutation target set is empty")
    observations: list[str] = []
    for index, path in enumerate(paths):
        if path.is_symlink():
            raise ValueError("AICO approval mutation target is unsafe")
        parent = path.parent
        if parent.is_symlink() or not parent.is_dir():
            raise ValueError("AICO approval mutation target parent is unsafe")
        parent_info = parent.stat()
        generation = (
            f"{parent_info.st_dev}:{parent_info.st_ino}:"
            f"{parent_info.st_mtime_ns}:{parent_info.st_ctime_ns}"
        )
        if path.exists():
            payload = _read_regular_file(path, _MAX_PROOF_BYTES)
            target_info = path.stat()
            generation += (
                f":{target_info.st_dev}:{target_info.st_ino}:{target_info.st_size}:"
                f"{target_info.st_mtime_ns}:{target_info.st_ctime_ns}"
            )
        else:
            payload = b"<missing>"
            generation += ":missing"
        observations.append(f"{index}:{_sha(payload)}:{generation}")
    return _sha_join(observations)


def _read_regular_file(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("AICO observed input must be a regular non-symlink file")
    with path.open("rb") as source:
        payload = source.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("AICO observed input exceeds bounded size")
    return payload


def _read_owner_file(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("AICO observed proof must be a regular non-symlink file")
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077
        or info.st_size > limit
    ):
        raise ValueError("AICO observed proof must be owner-only and bounded")
    return path.read_bytes()


def _require_sha(value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("AICO observed proof SHA-256 is invalid")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha_join(values: Sequence[str]) -> str:
    return _sha("\0".join(values).encode("utf-8"))


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
