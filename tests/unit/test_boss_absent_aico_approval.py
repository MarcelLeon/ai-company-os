from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.app.boss_absent_aico_approval import (
    AicoApprovalActionIntent,
    AicoBenchmarkApprovalGrant,
    execute_aico_approval_action,
    write_aico_approval_grant_from_im,
)
from aico.app.boss_absent_aico_im import (
    AicoImDecision,
    AicoImDecisionReceipt,
    AicoImExchangeKind,
)
from aico.app.boss_absent_aico_runner import (
    AicoBenchmarkRunPhase,
    AicoBenchmarkRunState,
    AicoBenchmarkRuntimeAdmission,
    AicoBenchmarkRuntimeCapabilities,
    AicoRoleCheckpoint,
    JsonAicoBenchmarkStateStore,
    admit_aico_benchmark_runtime,
)
from aico.core.boss_absent_benchmark import (
    BenchmarkScenario,
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    canonical_sha256,
)
from aico.core.models import TaskUsage


def _contract() -> BossAbsentBenchmarkContract:
    return BossAbsentBenchmarkContract(
        benchmark_id="boss-absent-approval",
        frozen_at=datetime(2026, 7, 23, tzinfo=UTC),
        model="gpt-5.6-sol",
        reasoning_effort="high",
        repo_revision="a" * 40,
        aico_version="test",
        codex_cli_version="0.144.5",
        wall_window_seconds=600,
        max_total_tokens=1_000,
        task_set_sha256="b" * 64,
        project_id="benchmark-project",
        project_assignment_sha256="c" * 64,
    )


def _task() -> BossAbsentTask:
    return BossAbsentTask(
        task_id="approval-action-test",
        scenario=BenchmarkScenario.APPROVAL,
        objective="apply one exact isolated marker",
        fixture=(
            '{"action_id":"publish-release-marker",'
            '"target":"isolated-fixture/release-status.txt",'
            '"content":"approved release-2026.07.23",'
            '"approval_scope":"write exact content once"}'
        ),
        acceptance=("request exact approval", "write once", "review"),
        required_roles=("implementer", "reviewer"),
        unattended_eligible=False,
        collaboration_required=True,
        im_takeover_required=True,
        approval_required=True,
    )


def _admission(contract: BossAbsentBenchmarkContract) -> AicoBenchmarkRuntimeAdmission:
    return admit_aico_benchmark_runtime(
        contract,
        AicoBenchmarkRuntimeCapabilities(
            runtime_build="aico-approval-test",
            model=contract.model,
            reasoning_effort=contract.reasoning_effort,
            isolated_run_state=True,
            managed_role_orchestration=True,
            hard_remaining_token_cap=True,
            provider_usage_observable=True,
            durable_dispatch_reconciliation=True,
        ),
    )


def _pending_state(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: AicoBenchmarkRuntimeAdmission,
) -> AicoBenchmarkRunState:
    request_sha = _request_sha(contract, task)
    return AicoBenchmarkRunState(
        contract_sha256=canonical_sha256(contract),
        runtime_admission_sha256=canonical_sha256(admission),
        benchmark_id=contract.benchmark_id,
        task_id=task.task_id,
        phase=AicoBenchmarkRunPhase.APPROVAL_PENDING,
        checkpoints=(
            AicoRoleCheckpoint(
                sequence=1,
                dispatch_id="1" * 64,
                role="implementer",
                agent_id="agent-implementer",
                assignment_sha256="2" * 64,
                provider_execution_sha256="3" * 64,
                runtime_instance_sha256="a" * 64,
                input_fixture_sha256=hashlib.sha256(task.fixture.encode()).hexdigest(),
                artifact_sha256="c" * 64,
                usage=TaskUsage(input_tokens=90, output_tokens=10, total_tokens=100),
            ),
        ),
        approval_request_sha256=request_sha,
        total_tokens=100,
    )


def _grant(
    path: Path,
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    *,
    expires_at: datetime = datetime(2027, 1, 1, tzinfo=UTC),
) -> Path:
    decision_path = path.with_name("decision.json")
    decision_path.write_text(
        AicoImDecisionReceipt(
            kind=AicoImExchangeKind.APPROVAL,
            contract_sha256=canonical_sha256(contract),
            task_id=task.task_id,
            subject_sha256=_request_sha(contract, task),
            request_sha256="d" * 64,
            owner_binding_sha256="e" * 64,
            delivery_ack_sha256="f" * 64,
            inbound_ack_sha256="1" * 64,
            decision=AicoImDecision.APPROVED,
            actions=1,
            elapsed_seconds=5,
            decided_at=datetime(2026, 7, 23, tzinfo=UTC),
        ).model_dump_json(indent=2)
        + "\n",
        encoding="utf-8",
    )
    decision_path.chmod(0o600)
    path.write_text(
        AicoBenchmarkApprovalGrant(
            contract_sha256=canonical_sha256(contract),
            task_id=task.task_id,
            request_sha256=_request_sha(contract, task),
            decision_receipt_sha256=hashlib.sha256(decision_path.read_bytes()).hexdigest(),
            granted_at=datetime(2026, 7, 23, tzinfo=UTC),
            expires_at=expires_at,
        ).model_dump_json(indent=2)
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return decision_path


def test_approval_executor_writes_once_and_releases_runner(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    admission = _admission(contract)
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())
    store.save(_pending_state(contract, task, admission))
    grant = tmp_path / "grant.json"
    decision = _grant(grant, contract, task)
    intent = (tmp_path / "approval" / "intent.json").absolute()
    receipt = (tmp_path / "approval" / "receipt.json").absolute()
    mutation_root = (tmp_path / "mutation").absolute()

    resumed = execute_aico_approval_action(
        contract,
        task,
        admission,
        store,
        grant_path=grant,
        decision_receipt_path=decision,
        mutation_root=mutation_root,
        intent_path=intent,
        receipt_path=receipt,
        now=datetime(2026, 7, 23, 1, tzinfo=UTC),
    )
    repeated = execute_aico_approval_action(
        contract,
        task,
        admission,
        store,
        grant_path=grant,
        decision_receipt_path=decision,
        mutation_root=mutation_root,
        intent_path=intent,
        receipt_path=receipt,
        now=datetime(2026, 7, 23, 1, tzinfo=UTC),
    )

    target = mutation_root / "isolated-fixture" / "release-status.txt"
    assert resumed.phase is AicoBenchmarkRunPhase.RUNNING
    assert repeated == resumed
    assert target.read_text(encoding="utf-8") == "approved release-2026.07.23"
    assert target.stat().st_mode & 0o777 == 0o600
    assert intent.stat().st_mode & 0o777 == 0o600
    assert receipt.stat().st_mode & 0o777 == 0o600
    assert resumed.approval_checkpoint is not None


def test_approval_grant_can_only_be_issued_from_exact_im_decision(
    tmp_path: Path,
) -> None:
    contract = _contract()
    task = _task()
    admission = _admission(contract)
    state = _pending_state(contract, task, admission)
    discarded = tmp_path / "discarded-grant.json"
    decision = _grant(discarded, contract, task)
    output = (tmp_path / "issued-grant.json").absolute()

    grant = write_aico_approval_grant_from_im(
        contract,
        task,
        state,
        decision_receipt_path=decision,
        grant_path=output,
        now=datetime(2026, 7, 23, 0, 1, tzinfo=UTC),
        expires_at=datetime(2026, 7, 23, 2, tzinfo=UTC),
    )

    assert grant.decision_receipt_sha256 == hashlib.sha256(decision.read_bytes()).hexdigest()
    assert output.stat().st_mode & 0o777 == 0o600


def test_approval_executor_reconciles_write_after_crash_without_rewriting(
    tmp_path: Path,
) -> None:
    contract = _contract()
    task = _task()
    admission = _admission(contract)
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())
    store.save(_pending_state(contract, task, admission))
    grant = tmp_path / "grant.json"
    decision = _grant(grant, contract, task)
    mutation_root = (tmp_path / "mutation").absolute()
    target = mutation_root / "isolated-fixture" / "release-status.txt"
    target.parent.mkdir(mode=0o700, parents=True)
    mutation_root.chmod(0o700)
    target.parent.chmod(0o700)
    target.write_text("approved release-2026.07.23", encoding="utf-8")
    target.chmod(0o600)
    intent_path = (tmp_path / "approval" / "intent.json").absolute()
    intent_path.parent.mkdir(mode=0o700)
    grant_sha = hashlib.sha256(grant.read_bytes()).hexdigest()
    intent_path.write_text(
        AicoApprovalActionIntent(
            contract_sha256=canonical_sha256(contract),
            task_id=task.task_id,
            request_sha256=_request_sha(contract, task),
            grant_sha256=grant_sha,
            action_id="publish-release-marker",
            target_sha256=hashlib.sha256(b"isolated-fixture/release-status.txt").hexdigest(),
            content_sha256=hashlib.sha256(b"approved release-2026.07.23").hexdigest(),
        ).model_dump_json(indent=2)
        + "\n",
        encoding="utf-8",
    )
    intent_path.chmod(0o600)
    before = target.stat().st_mtime_ns

    resumed = execute_aico_approval_action(
        contract,
        task,
        admission,
        store,
        grant_path=grant,
        decision_receipt_path=decision,
        mutation_root=mutation_root,
        intent_path=intent_path,
        receipt_path=(tmp_path / "approval" / "receipt.json").absolute(),
        now=datetime(2026, 7, 23, 1, tzinfo=UTC),
    )

    assert resumed.approval_checkpoint is not None
    assert target.stat().st_mtime_ns == before


def test_approval_executor_rejects_expired_or_wrong_target_state(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    admission = _admission(contract)
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())
    store.save(_pending_state(contract, task, admission))
    grant = tmp_path / "grant.json"
    decision = _grant(
        grant,
        contract,
        task,
        expires_at=datetime(2026, 7, 23, 0, 30, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="does not match"):
        execute_aico_approval_action(
            contract,
            task,
            admission,
            store,
            grant_path=grant,
            decision_receipt_path=decision,
            mutation_root=(tmp_path / "mutation").absolute(),
            intent_path=(tmp_path / "approval" / "intent.json").absolute(),
            receipt_path=(tmp_path / "approval" / "receipt.json").absolute(),
            now=datetime(2026, 7, 23, 1, tzinfo=UTC),
        )


def test_approval_executor_rejects_preexisting_target_without_intent(tmp_path: Path) -> None:
    contract = _contract()
    task = _task()
    admission = _admission(contract)
    store = JsonAicoBenchmarkStateStore((tmp_path / "state.json").absolute())
    store.save(_pending_state(contract, task, admission))
    grant = tmp_path / "grant.json"
    decision = _grant(grant, contract, task)
    mutation_root = (tmp_path / "mutation").absolute()
    target = mutation_root / "isolated-fixture" / "release-status.txt"
    target.parent.mkdir(mode=0o700, parents=True)
    mutation_root.chmod(0o700)
    target.parent.chmod(0o700)
    target.write_text("approved release-2026.07.23", encoding="utf-8")
    target.chmod(0o600)

    with pytest.raises(ValueError, match="predates the durable intent"):
        execute_aico_approval_action(
            contract,
            task,
            admission,
            store,
            grant_path=grant,
            decision_receipt_path=decision,
            mutation_root=mutation_root,
            intent_path=(tmp_path / "approval" / "intent.json").absolute(),
            receipt_path=(tmp_path / "approval" / "receipt.json").absolute(),
            now=datetime(2026, 7, 23, 1, tzinfo=UTC),
        )


def _request_sha(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
) -> str:
    return hashlib.sha256(
        (
            f"aico-benchmark-approval-v1\0{canonical_sha256(contract)}\0"
            f"{task.task_id}\0{task.fixture}"
        ).encode()
    ).hexdigest()
