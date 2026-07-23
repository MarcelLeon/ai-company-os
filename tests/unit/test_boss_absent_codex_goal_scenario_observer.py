from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
from pydantic import BaseModel

from aico.app.boss_absent_aico_im import (
    AicoImDecision,
    AicoImDecisionReceipt,
    AicoImExchangeKind,
)
from aico.app.boss_absent_benchmark_cli import run
from aico.app.boss_absent_codex_goal_evidence import (
    CodexGoalRoleEvidence,
    CodexGoalScenarioEvidenceReceipt,
    finalize_codex_goal_benchmark_result,
)
from aico.app.boss_absent_codex_goal_host import (
    CodexGoalHostAdmissionReceipt,
    CodexGoalHostKind,
    CodexGoalHostRunReceipt,
    CodexGoalHostTurnReceipt,
    CodexGoalTurnSource,
)
from aico.app.boss_absent_codex_goal_live_observer import (
    CodexDesktopHostProcessObservation,
)
from aico.app.boss_absent_codex_goal_role_observer import (
    CodexGoalRoleChainObservationReceipt,
)
from aico.app.boss_absent_codex_goal_run_observer import (
    CodexGoalHostRunObservationReceipt,
    CodexGoalHostRunSessionAnchor,
)
from aico.app.boss_absent_codex_goal_scenario_observer import (
    CodexGoalApprovalActionObservationReceipt,
    CodexGoalExternalCheckReceipt,
    CodexGoalTerminalObservationReceipt,
    IndependentCodexGoalScenarioObserver,
    JsonCodexGoalScenarioObservationStore,
)
from aico.core.boss_absent_benchmark import (
    BenchmarkScenario,
    BenchmarkTerminalStatus,
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    BossAbsentTaskSet,
    canonical_sha256,
)

_NOW = datetime(2026, 7, 23, tzinfo=UTC)


@pytest.mark.parametrize("scenario", tuple(BenchmarkScenario))
def test_observer_derives_complete_receipt_for_each_scenario(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: BenchmarkScenario,
) -> None:
    contract = _contract()
    task = _task(scenario)
    approval_decision = _approval_decision(contract, task)
    approval_payload = approval_decision.model_dump_json().encode()
    admission = _admission(contract)
    host_run = _host_run(
        contract,
        task,
        admission,
        approval_grant_sha=hashlib.sha256(approval_payload).hexdigest(),
    )
    child_paths = _child_files(tmp_path, task)
    role_receipt = _role_receipt(contract, task, host_run, child_paths)
    monkeypatch.setattr(
        "aico.app.boss_absent_codex_goal_scenario_observer.observe_codex_goal_role_chain",
        lambda *_args, **_kwargs: role_receipt,
    )
    observer = IndependentCodexGoalScenarioObserver(
        contract,
        task,
        admission,
        _host_observation(contract, task, admission, host_run),
        JsonCodexGoalScenarioObservationStore((tmp_path / "observations.json").absolute()),
        observer_build="observer-test",
        clock=lambda: _NOW,
    )
    observer.observe_role_sessions(
        codex_home=tmp_path,
        parent_session_path=tmp_path / "unused-parent.jsonl",
        child_session_paths=child_paths,
    )
    fixture = _private_file(tmp_path / "fixture.json", task.fixture.encode())
    observer.observe_fixture(fixture)
    if task.restart_required:
        observer.observe_restart()
    if task.scenario is BenchmarkScenario.EVIDENCE_DRIFT:
        fixture.write_text(f"{task.fixture}-changed")
        observer.observe_drift(fixture)
    if task.budget_pressure:
        irrelevant = _private_file(tmp_path / "irrelevant.log", b"z" * 160)
        observer.observe_source_pressure(irrelevant, child_paths)
    if task.approval_required:
        _observe_approval(
            observer,
            contract,
            task,
            host_run,
            approval_decision,
            tmp_path,
        )
    _observe_checks(observer, contract, task, host_run, role_receipt, tmp_path)
    observer.observe_budget()
    if task.im_takeover_required:
        takeover = _im_decision(
            contract,
            task,
            kind=AicoImExchangeKind.TAKEOVER,
            subject=role_receipt.roles[-1].artifact_sha256,
        )
        path = _model_file(tmp_path / "takeover.json", takeover)
        observer.observe_takeover(path)
    terminal = CodexGoalTerminalObservationReceipt(
        contract_sha256=canonical_sha256(contract),
        task_id=task.task_id,
        host_run_sha256=canonical_sha256(host_run),
        consumed_checkpoint_sha256=role_receipt.roles[-1].artifact_sha256,
        status=BenchmarkTerminalStatus.COMPLETE,
    )
    observer.observe_terminal(_model_file(tmp_path / "terminal.json", terminal))

    receipt = observer.build_receipt()
    result = finalize_codex_goal_benchmark_result(
        contract,
        task,
        admission,
        _host_observation(contract, task, admission, host_run),
        receipt,
    )

    assert result.terminal_status is BenchmarkTerminalStatus.COMPLETE
    assert result.total_tokens == 220
    assert receipt.role_chain_observation_sha256 == canonical_sha256(role_receipt)
    assert receipt.host_run_observation_sha256 == canonical_sha256(
        _host_observation(contract, task, admission, host_run)
    )
    assert receipt.evidence.proofs()[0].sha256 is not None


def test_observer_rejects_hidden_irrelevant_source_consumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.BUDGET_PRESSURE)
    admission = _admission(contract)
    host_run = _host_run(contract, task, admission)
    irrelevant = _private_file(tmp_path / "irrelevant.log", b"unique-source-" * 12)
    child_paths = _child_files(tmp_path, task, extra=irrelevant.read_bytes()[:32])
    role_receipt = _role_receipt(contract, task, host_run, child_paths)
    monkeypatch.setattr(
        "aico.app.boss_absent_codex_goal_scenario_observer.observe_codex_goal_role_chain",
        lambda *_args, **_kwargs: role_receipt,
    )
    observer = _observer(contract, task, admission, host_run, tmp_path)
    observer.observe_role_sessions(
        codex_home=tmp_path,
        parent_session_path=tmp_path / "unused.jsonl",
        child_session_paths=child_paths,
    )

    with pytest.raises(ValueError, match="consumed the irrelevant source"):
        observer.observe_source_pressure(irrelevant, child_paths)


def test_observer_rejects_mutation_before_owner_grant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.APPROVAL)
    decision = _approval_decision(contract, task)
    grant_sha = hashlib.sha256(decision.model_dump_json().encode()).hexdigest()
    admission = _admission(contract)
    host_run = _host_run(contract, task, admission, approval_grant_sha=grant_sha)
    child_paths = _child_files(tmp_path, task)
    role_receipt = _role_receipt(contract, task, host_run, child_paths)
    monkeypatch.setattr(
        "aico.app.boss_absent_codex_goal_scenario_observer.observe_codex_goal_role_chain",
        lambda *_args, **_kwargs: role_receipt,
    )
    observer = _observer(contract, task, admission, host_run, tmp_path)
    observer.observe_role_sessions(
        codex_home=tmp_path,
        parent_session_path=tmp_path / "unused.jsonl",
        child_session_paths=child_paths,
    )
    mutation_dir = tmp_path / "mutation"
    mutation_dir.mkdir()
    target = mutation_dir / "release-status.txt"
    observer.observe_approval_request((target,))
    target.write_text("mutated too early")

    with pytest.raises(ValueError, match="pre-mutation fence drifted"):
        observer.observe_approval_grant(
            _model_file(tmp_path / "approval.json", decision),
            (target,),
        )


def test_ledger_detects_hash_chain_and_identity_tampering(tmp_path: Path) -> None:
    contract = _contract()
    task = _task(BenchmarkScenario.NORMAL)
    admission = _admission(contract)
    host_run = _host_run(contract, task, admission)
    store = JsonCodexGoalScenarioObservationStore((tmp_path / "ledger.json").absolute())
    _observer(contract, task, admission, host_run, tmp_path, store=store)
    ledger = store.load()
    assert ledger is not None
    drifted = ledger.model_copy(update={"task_id": "different-task"})
    store.save(drifted)

    with pytest.raises(ValueError, match="identity drifted"):
        _observer(contract, task, admission, host_run, tmp_path, store=store)
    chain_store = JsonCodexGoalScenarioObservationStore((tmp_path / "chain-ledger.json").absolute())
    observer = _observer(contract, task, admission, host_run, tmp_path, store=chain_store)
    observer.observe_fixture(_private_file(tmp_path / "fixture.json", task.fixture.encode()))
    chained = chain_store.load()
    assert chained is not None
    event = chained.events[0].model_copy(update={"previous_event_sha256": "0" * 64})
    chain_store.save(chained.model_copy(update={"events": (event,)}))

    with pytest.raises(ValueError, match="ledger is invalid"):
        chain_store.load()


def test_cli_derives_owner_safe_receipt_from_observation_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tasks = BossAbsentTaskSet(
        name="codex-observer-cli",
        tasks=tuple(_task(scenario) for scenario in BenchmarkScenario),
    )
    contract = _contract().model_copy(update={"task_set_sha256": canonical_sha256(tasks)})
    task = _task(BenchmarkScenario.NORMAL)
    admission = _admission(contract)
    host_run = _host_run(contract, task, admission)
    child_paths = _child_files(tmp_path, task)
    role_receipt = _role_receipt(contract, task, host_run, child_paths)
    monkeypatch.setattr(
        "aico.app.boss_absent_codex_goal_scenario_observer.observe_codex_goal_role_chain",
        lambda *_args, **_kwargs: role_receipt,
    )
    ledger_path = (tmp_path / "ledger.json").absolute()
    observer = _observer(
        contract,
        task,
        admission,
        host_run,
        tmp_path,
        store=JsonCodexGoalScenarioObservationStore(ledger_path),
    )
    observer.observe_role_sessions(
        codex_home=tmp_path,
        parent_session_path=tmp_path / "unused.jsonl",
        child_session_paths=child_paths,
    )
    observer.observe_fixture(_private_file(tmp_path / "fixture.json", task.fixture.encode()))
    _observe_checks(observer, contract, task, host_run, role_receipt, tmp_path)
    observer.observe_budget()
    terminal = CodexGoalTerminalObservationReceipt(
        contract_sha256=canonical_sha256(contract),
        task_id=task.task_id,
        host_run_sha256=canonical_sha256(host_run),
        consumed_checkpoint_sha256=role_receipt.roles[-1].artifact_sha256,
        status=BenchmarkTerminalStatus.COMPLETE,
    )
    observer.observe_terminal(_model_file(tmp_path / "terminal.json", terminal))
    paths = {
        "contract": _model_file(tmp_path / "contract.json", contract),
        "tasks": _model_file(tmp_path / "tasks.json", tasks),
        "host-admission": _model_file(tmp_path / "admission.json", admission),
        "host-run-observation": _model_file(
            tmp_path / "host-run-observation.json",
            _host_observation(contract, task, admission, host_run),
        ),
    }
    output = tmp_path / "scenario-receipt.json"
    stdout = StringIO()

    exit_code = run(
        (
            "finalize-codex-goal-observations",
            "--contract",
            str(paths["contract"]),
            "--tasks",
            str(paths["tasks"]),
            "--host-admission",
            str(paths["host-admission"]),
            "--host-run-observation",
            str(paths["host-run-observation"]),
            "--observations",
            str(ledger_path),
            "--output",
            str(output),
        ),
        stdout=stdout,
    )

    receipt = CodexGoalScenarioEvidenceReceipt.model_validate_json(output.read_text())
    assert exit_code == 0
    assert receipt.task_id == task.task_id
    assert "independent observations finalized" in stdout.getvalue()
    assert output.stat().st_mode & 0o777 == 0o600


def _observe_approval(
    observer: IndependentCodexGoalScenarioObserver,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    host_run: CodexGoalHostRunReceipt,
    decision: AicoImDecisionReceipt,
    root: Path,
) -> None:
    mutation_dir = root / "mutation"
    mutation_dir.mkdir()
    target = mutation_dir / "release-status.txt"
    observer.observe_approval_request((target,))
    observer.observe_approval_grant(
        _model_file(root / "approval-decision.json", decision),
        (target,),
    )
    target.write_text("approved release marker")
    snapshot = _mutation_snapshot((target,))
    owner_turn = next(
        turn for turn in host_run.turns if turn.source is CodexGoalTurnSource.OWNER_TAKEOVER
    )
    action = CodexGoalApprovalActionObservationReceipt(
        contract_sha256=canonical_sha256(contract),
        task_id=task.task_id,
        host_run_sha256=canonical_sha256(host_run),
        request_sha256=decision.subject_sha256,
        grant_sha256=hashlib.sha256(decision.model_dump_json().encode()).hexdigest(),
        owner_turn_sha256=owner_turn.turn_sha256,
        mutation_set_sha256=snapshot,
    )
    observer.observe_approval_action(
        _model_file(root / "approval-action.json", action),
        (target,),
    )


def _observe_checks(
    observer: IndependentCodexGoalScenarioObserver,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    host_run: CodexGoalHostRunReceipt,
    roles: CodexGoalRoleChainObservationReceipt,
    root: Path,
) -> None:
    for kind in ("acceptance", "test_gate"):
        receipt = CodexGoalExternalCheckReceipt(
            check_kind=kind,
            contract_sha256=canonical_sha256(contract),
            task_id=task.task_id,
            host_run_sha256=canonical_sha256(host_run),
            checked_artifact_sha256=roles.roles[-1].artifact_sha256,
            passed=True,
        )
        observer.observe_external_check(_model_file(root / f"{kind}.json", receipt))


def _observer(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
    host_run: CodexGoalHostRunReceipt,
    root: Path,
    *,
    store: JsonCodexGoalScenarioObservationStore | None = None,
) -> IndependentCodexGoalScenarioObserver:
    return IndependentCodexGoalScenarioObserver(
        contract,
        task,
        admission,
        _host_observation(contract, task, admission, host_run),
        store or JsonCodexGoalScenarioObservationStore((root / "ledger.json").absolute()),
        observer_build="observer-test",
        clock=lambda: _NOW,
    )


def _contract() -> BossAbsentBenchmarkContract:
    return BossAbsentBenchmarkContract(
        benchmark_id="codex-scenario-observer",
        frozen_at=_NOW,
        model="gpt-5.6-sol",
        reasoning_effort="high",
        repo_revision="a" * 40,
        aico_version="test",
        codex_cli_version="0.145.0-alpha.30",
        wall_window_seconds=600,
        max_total_tokens=1_000,
        task_set_sha256="b" * 64,
        project_id="benchmark-project",
        project_assignment_sha256="c" * 64,
    )


def _task(scenario: BenchmarkScenario) -> BossAbsentTask:
    approval = scenario is BenchmarkScenario.APPROVAL
    restart = scenario is BenchmarkScenario.RESTART
    budget = scenario is BenchmarkScenario.BUDGET_PRESSURE
    return BossAbsentTask(
        task_id=f"task-{scenario.value.replace('_', '-')}",
        scenario=scenario,
        objective="produce a verified terminal handoff",
        fixture='{"release":"candidate-17","tests":"green"}',
        acceptance=("lead plans", "reviewer verifies"),
        required_roles=("lead", "reviewer"),
        unattended_eligible=not approval,
        collaboration_required=True,
        restart_required=restart,
        im_takeover_required=restart or approval,
        approval_required=approval,
        budget_pressure=budget,
    )


def _admission(contract: BossAbsentBenchmarkContract) -> CodexGoalHostAdmissionReceipt:
    return CodexGoalHostAdmissionReceipt(
        contract_sha256=canonical_sha256(contract),
        host_build="signed-codex-app",
        host_kind=CodexGoalHostKind.NATIVE_CODEX_HOST,
    )


def _host_run(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
    *,
    approval_grant_sha: str = "9" * 64,
) -> CodexGoalHostRunReceipt:
    first = _host_turn(contract, task, 1, before=0, after=100)
    second = _host_turn(
        contract,
        task,
        2,
        before=100,
        after=220,
        previous=first.turn_sha256,
        approval_grant_sha=approval_grant_sha,
    )
    return CodexGoalHostRunReceipt(
        contract_sha256=canonical_sha256(contract),
        host_admission_sha256=canonical_sha256(admission),
        turns=(first, second),
        total_tokens=220,
        human_interventions=int(task.approval_required),
        terminal_status="complete",
    )


def _host_observation(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: CodexGoalHostAdmissionReceipt,
    host_run: CodexGoalHostRunReceipt,
) -> CodexGoalHostRunObservationReceipt:
    runtime = CodexDesktopHostProcessObservation(
        pid=101,
        parent_pid=100,
        started_at=_NOW,
        observed_at=_NOW,
        command_sha256="6" * 64,
        parent_command_sha256="7" * 64,
    )
    anchor = CodexGoalHostRunSessionAnchor(
        device=1,
        inode=1,
        size_bytes=100,
        content_sha256="8" * 64,
        provider_total_tokens=0,
        observed_at=_NOW,
    )
    return CodexGoalHostRunObservationReceipt(
        contract_sha256=canonical_sha256(contract),
        task_sha256=canonical_sha256(task),
        host_admission_sha256=canonical_sha256(admission),
        intent_sha256="9" * 64,
        thread_id_sha256="a" * 64,
        session_before=anchor,
        session_after_sha256="b" * 64,
        session_after_size_bytes=200,
        runtime_observations=(runtime,),
        provider_tokens_before=0,
        provider_tokens_after=host_run.total_tokens,
        goal_tokens_after=host_run.total_tokens,
        host_run=host_run,
    )


def _host_turn(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    sequence: int,
    *,
    before: int,
    after: int,
    previous: str | None = None,
    approval_grant_sha: str = "9" * 64,
) -> CodexGoalHostTurnReceipt:
    owner = task.approval_required and sequence == 2
    return CodexGoalHostTurnReceipt(
        sequence=sequence,
        source=(
            CodexGoalTurnSource.INITIAL_TASK
            if sequence == 1
            else (
                CodexGoalTurnSource.OWNER_TAKEOVER
                if owner
                else CodexGoalTurnSource.NATIVE_HOST_CONTINUATION
            )
        ),
        previous_turn_sha256=previous,
        turn_sha256=str(sequence) * 64,
        opaque_input_sha256=(
            canonical_sha256(task) if sequence == 1 else (approval_grant_sha if owner else "8" * 64)
        ),
        runtime_instance_sha256=("b" * 64 if task.restart_required and sequence == 2 else "a" * 64),
        goal_status_after=("active" if sequence == 1 else "complete"),
        goal_tokens_before=before,
        goal_tokens_after=after,
        goal_token_budget=contract.max_total_tokens,
        provider_total_tokens=after - before,
        human_interventions=int(owner),
    )


def _role_receipt(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    host_run: CodexGoalHostRunReceipt,
    child_paths: tuple[Path, Path],
) -> CodexGoalRoleChainObservationReceipt:
    first = CodexGoalRoleEvidence(
        sequence=1,
        role="lead",
        agent_identity_sha256="a" * 64,
        provider_execution_sha256="c" * 64,
        runtime_instance_sha256=host_run.turns[0].runtime_instance_sha256,
        source_turn_sha256=host_run.turns[0].turn_sha256,
        input_fixture_sha256=hashlib.sha256(task.fixture.encode()).hexdigest(),
        artifact_sha256="e" * 64,
    )
    second = CodexGoalRoleEvidence(
        sequence=2,
        role="reviewer",
        agent_identity_sha256="b" * 64,
        provider_execution_sha256="d" * 64,
        runtime_instance_sha256=host_run.turns[1].runtime_instance_sha256,
        source_turn_sha256=host_run.turns[1].turn_sha256,
        input_fixture_sha256=hashlib.sha256(task.fixture.encode()).hexdigest(),
        artifact_sha256="f" * 64,
        consumed_checkpoint_sha256=first.artifact_sha256,
    )
    return CodexGoalRoleChainObservationReceipt(
        contract_sha256=canonical_sha256(contract),
        task_id=task.task_id,
        host_run_sha256=canonical_sha256(host_run),
        parent_session_sha256="1" * 64,
        child_session_sha256s=tuple(
            hashlib.sha256(path.read_bytes()).hexdigest() for path in child_paths
        ),
        roles=(first, second),
    )


def _approval_decision(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
) -> AicoImDecisionReceipt:
    return _im_decision(
        contract,
        task,
        kind=AicoImExchangeKind.APPROVAL,
        subject=_approval_request_sha(contract, task),
    )


def _im_decision(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    *,
    kind: AicoImExchangeKind,
    subject: str,
) -> AicoImDecisionReceipt:
    return AicoImDecisionReceipt(
        kind=kind,
        contract_sha256=canonical_sha256(contract),
        task_id=task.task_id,
        subject_sha256=subject,
        request_sha256="1" * 64,
        owner_binding_sha256="2" * 64,
        delivery_ack_sha256="3" * 64,
        inbound_ack_sha256="4" * 64,
        decision=(
            AicoImDecision.APPROVED
            if kind is AicoImExchangeKind.APPROVAL
            else AicoImDecision.ACKNOWLEDGED
        ),
        actions=1,
        elapsed_seconds=2,
        decided_at=_NOW,
    )


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


def _mutation_snapshot(paths: tuple[Path, ...]) -> str:
    observations: list[str] = []
    for index, path in enumerate(paths):
        parent = path.parent.stat()
        generation = f"{parent.st_dev}:{parent.st_ino}:{parent.st_mtime_ns}:{parent.st_ctime_ns}"
        if path.exists():
            payload = path.read_bytes()
            target = path.stat()
            generation += (
                f":{target.st_dev}:{target.st_ino}:{target.st_size}:"
                f"{target.st_mtime_ns}:{target.st_ctime_ns}"
            )
        else:
            payload = b"<missing>"
            generation += ":missing"
        observations.append(f"{index}:{hashlib.sha256(payload).hexdigest()}:{generation}")
    return _sha_join(tuple(observations))


def _child_files(
    root: Path,
    task: BossAbsentTask,
    *,
    extra: bytes = b"",
) -> tuple[Path, Path]:
    result: list[Path] = []
    for role in task.required_roles:
        result.append(_private_file(root / f"{role}.jsonl", f"{role}-session".encode() + extra))
    return result[0], result[1]


def _model_file(path: Path, model: BaseModel) -> Path:
    payload = model.model_dump_json().encode()
    return _private_file(path, payload)


def _private_file(path: Path, payload: bytes) -> Path:
    path.write_bytes(payload)
    os.chmod(path, 0o600)
    return path


def _sha_join(values: tuple[str, ...]) -> str:
    return hashlib.sha256("\0".join(values).encode()).hexdigest()
