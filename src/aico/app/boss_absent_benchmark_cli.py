"""Freeze and score evidence-safe AICO vs Codex Goal benchmark artifacts."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TextIO, TypeVar

from pydantic import BaseModel

from aico.adapter.codex import CodexAdapter
from aico.app.boss_absent_aico_approval import (
    execute_aico_approval_action,
    write_aico_approval_grant_from_im,
)
from aico.app.boss_absent_aico_evidence import (
    AicoScenarioEvidenceReceipt,
    finalize_aico_benchmark_result,
)
from aico.app.boss_absent_aico_im import (
    AicoImDecision,
    AicoImDecisionReceipt,
    AicoImExchangeKind,
    AicoImExchangeRequest,
    AicoImExchangeStore,
    AicoImOwnerBinding,
    collect_aico_im_decision,
)
from aico.app.boss_absent_aico_observer import (
    IndependentAicoScenarioObserver,
    JsonAicoScenarioObservationStore,
    build_aico_takeover_ack_from_im,
)
from aico.app.boss_absent_aico_runner import (
    AicoBenchmarkRunPhase,
    AicoBenchmarkRunState,
    AicoBenchmarkRuntimeCapabilities,
    JsonAicoBenchmarkStateStore,
    admit_aico_benchmark_runtime,
    advance_aico_benchmark_task,
)
from aico.app.boss_absent_aico_taskbus_runtime import (
    AicoBenchmarkRoleTarget,
    TaskBusAicoBenchmarkRuntime,
)
from aico.app.boss_absent_benchmark_restart_probe import run_restart_probe
from aico.app.boss_absent_codex_goal_capability import (
    CodexGoalHostSurfaceReceipt,
    CodexGoalNativeHostCandidateReceipt,
    probe_codex_goal_host_surface,
    probe_codex_goal_native_host_candidate,
)
from aico.app.boss_absent_codex_goal_evidence import (
    CodexGoalScenarioEvidenceReceipt,
    finalize_codex_goal_benchmark_result,
)
from aico.app.boss_absent_codex_goal_host import (
    CodexGoalHostAdmissionReceipt,
)
from aico.app.boss_absent_codex_goal_probe import (
    CodexGoalProtocolReceipt,
    probe_codex_goal_protocol,
)
from aico.app.boss_absent_codex_goal_run_observer import (
    CodexGoalHostRunObservationReceipt,
)
from aico.app.boss_absent_codex_goal_scenario_observer import (
    IndependentCodexGoalScenarioObserver,
    JsonCodexGoalScenarioObservationStore,
)
from aico.channel.telegram import TelegramChannel
from aico.core.boss_absent_benchmark import (
    BenchmarkRate,
    BenchmarkSystem,
    BossAbsentBenchmarkContract,
    BossAbsentBenchmarkSummary,
    BossAbsentBenchmarkVerdict,
    BossAbsentTask,
    BossAbsentTaskResult,
    BossAbsentTaskSet,
    canonical_sha256,
    compare_boss_absent_summaries,
    score_boss_absent_system,
)
from aico.core.boss_absent_benchmark_harness import run_synthetic_benchmark_harness
from aico.core.models import utc_now
from aico.core.project_assignment import (
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
)
from aico.core.task_bus import TaskBus

_MAX_JSON_BYTES = 1_048_576
_MAX_RESULTS_BYTES = 4_194_304
_MAX_RESULT_LINE_BYTES = 65_536
ModelT = TypeVar("ModelT", bound=BaseModel)


def run(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error = stderr or sys.stderr
    args = _parser().parse_args(argv)
    try:
        if args.command == "freeze":
            contract = _freeze_contract(args)
            _write_new_model(args.output, contract)
            output.write(
                f"frozen benchmark contract: id={contract.benchmark_id} "
                f"sha256={canonical_sha256(contract)}\n"
            )
            return 0
        if args.command == "score":
            verdict = _score(args)
            output.write(
                f"benchmark verdict: aico_wins={str(verdict.aico_wins).lower()} "
                f"strict_better={verdict.strict_better_metrics}/5\n"
            )
            return 0 if verdict.aico_wins else 1
        if args.command == "dry-run":
            verdict = _dry_run(args)
            output.write(
                "synthetic harness complete: "
                f"aico_wins={str(verdict.aico_wins).lower()} "
                "(equal fake observations; not a benchmark result)\n"
            )
            return 0
        if args.command == "probe-codex-goal":
            receipt = _probe_codex_goal(args)
            output.write(
                "Codex Goal protocol admitted without model calls: "
                f"version={receipt.codex_cli_version} tokens_used={receipt.tokens_used}\n"
            )
            return 0
        if args.command in {"probe-codex-goal-host", "probe-codex-app-host"}:
            return _run_codex_host_probe(args, output)
        if args.command.startswith("finalize-"):
            return _run_finalizer(args, output)
        if args.command == "advance-aico":
            state = asyncio.run(_advance_aico(args))
            output.write(
                f"AICO role advanced: task={state.task_id} phase={state.phase.value} "
                f"checkpoints={len(state.checkpoints)} tokens={state.total_tokens}\n"
            )
            return 0
        if args.command == "apply-aico-approval":
            state = _apply_aico_approval(args)
            output.write(f"AICO approval applied: task={state.task_id} phase={state.phase.value}\n")
            return 0
        if args.command == "collect-aico-approval-im":
            decision = asyncio.run(_collect_aico_approval_im(args))
            output.write(
                "AICO owner approval collected through IM: "
                f"task={decision.task_id} decision={decision.decision.value} "
                f"actions={decision.actions}\n"
            )
            return 0
        if args.command == "collect-aico-takeover-im":
            decision = asyncio.run(_collect_aico_takeover_im(args))
            output.write(
                "AICO owner takeover acknowledged through IM: "
                f"task={decision.task_id} actions={decision.actions} "
                f"seconds={decision.elapsed_seconds:.3f}\n"
            )
            return 0
    except (OSError, UnicodeError, ValueError) as exc:
        error.write(f"benchmark failed: {exc}\n")
        return 2
    raise AssertionError("unknown benchmark command")


def main() -> None:
    raise SystemExit(run())


def _run_finalizer(args: argparse.Namespace, output: TextIO) -> int:
    if args.command == "finalize-aico":
        result = _finalize_aico(args)
        output.write(
            "AICO scenario evidence finalized: "
            f"task={result.task_id} status={result.terminal_status.value} "
            f"tokens={result.total_tokens}\n"
        )
        return 0
    if args.command == "finalize-codex-goal":
        result = _finalize_codex_goal(args)
        output.write(
            "Codex Goal scenario evidence finalized: "
            f"task={result.task_id} status={result.terminal_status.value} "
            f"tokens={result.total_tokens}\n"
        )
        return 0
    if args.command == "finalize-codex-goal-observations":
        codex_receipt = _finalize_codex_goal_observations(args)
        output.write(
            "Codex Goal independent observations finalized: "
            f"task={codex_receipt.task_id} events={codex_receipt.events_sha256}\n"
        )
        return 0
    if args.command == "finalize-aico-observations":
        aico_receipt = _finalize_aico_observations(args)
        output.write(
            f"AICO independent observations finalized: task={aico_receipt.task_id} "
            f"events={aico_receipt.events_sha256}\n"
        )
        return 0
    raise AssertionError("unknown benchmark finalizer command")


def _freeze_contract(args: argparse.Namespace) -> BossAbsentBenchmarkContract:
    task_set = _read_model(args.tasks, BossAbsentTaskSet)
    project_config = _read_model(args.project_config, ProjectAssignmentConfig)
    project_directory = ProjectAssignmentDirectory(project_config)
    if project_directory.project(args.project_id) is None:
        raise ValueError("benchmark project is unknown")
    return BossAbsentBenchmarkContract(
        benchmark_id=args.benchmark_id,
        frozen_at=utc_now(),
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        repo_revision=args.repo_revision,
        aico_version=args.aico_version,
        codex_cli_version=args.codex_cli_version,
        wall_window_seconds=args.wall_window_seconds,
        max_total_tokens=args.max_total_tokens,
        takeover_action_cap=args.takeover_action_cap,
        takeover_seconds_cap=args.takeover_seconds_cap,
        task_set_sha256=canonical_sha256(task_set),
        project_id=args.project_id,
        project_assignment_sha256=canonical_sha256(project_config),
    )


def _score(args: argparse.Namespace) -> BossAbsentBenchmarkVerdict:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    task_set = _read_model(args.tasks, BossAbsentTaskSet)
    results = _read_results(args.results)
    aico = score_boss_absent_system(contract, task_set, results, BenchmarkSystem.AICO)
    codex_goal = score_boss_absent_system(
        contract,
        task_set,
        results,
        BenchmarkSystem.CODEX_GOAL,
    )
    verdict = compare_boss_absent_summaries(contract, aico, codex_goal)
    _write_report_dir(args.output_dir, aico, codex_goal, verdict)
    return verdict


def _dry_run(args: argparse.Namespace) -> BossAbsentBenchmarkVerdict:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    task_set = _read_model(args.tasks, BossAbsentTaskSet)
    run_result = run_synthetic_benchmark_harness(contract, task_set)
    args.output_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    restart_receipts = {
        system: run_restart_probe(args.output_dir, system) for system in BenchmarkSystem
    }
    for system, receipt in restart_receipts.items():
        _write_new_model(
            args.output_dir / f"restart-probe-{system.value}.json",
            receipt,
        )
    results = tuple(
        BossAbsentTaskResult.model_validate(
            result.model_dump()
            | {"restart_evidence_sha256": canonical_sha256(restart_receipts[result.system])}
        )
        if result.task_id == "restart-mid-handoff"
        else result
        for result in run_result.results
    )
    _write_jsonl(args.output_dir / "scenario-events.jsonl", run_result.events)
    results_path = args.output_dir / "task-results.jsonl"
    _write_jsonl(results_path, results)
    aico = score_boss_absent_system(contract, task_set, results, BenchmarkSystem.AICO)
    codex_goal = score_boss_absent_system(contract, task_set, results, BenchmarkSystem.CODEX_GOAL)
    verdict = compare_boss_absent_summaries(contract, aico, codex_goal)
    _write_report_dir(args.output_dir / "scored", aico, codex_goal, verdict)
    return verdict


def _probe_codex_goal(args: argparse.Namespace) -> CodexGoalProtocolReceipt:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    receipt = probe_codex_goal_protocol(
        executable=args.codex,
        expected_cli_version=contract.codex_cli_version,
        model=contract.model,
        token_budget=contract.max_total_tokens,
        cwd=args.cwd,
        cleanup_intent_path=args.output.with_name(f"{args.output.name}.cleanup-intent.json"),
        isolated_home_path=args.output.with_name(f"{args.output.name}.codex-home"),
    )
    _write_new_model(args.output, receipt)
    return receipt


def _probe_codex_goal_host(args: argparse.Namespace) -> CodexGoalHostSurfaceReceipt:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    receipt = probe_codex_goal_host_surface(
        executable=args.codex,
        expected_cli_version=contract.codex_cli_version,
        contract_sha256=canonical_sha256(contract),
    )
    _write_new_model(args.output, receipt)
    return receipt


def _run_codex_host_probe(args: argparse.Namespace, output: TextIO) -> int:
    if args.command == "probe-codex-goal-host":
        receipt = _probe_codex_goal_host(args)
        output.write(
            "Codex Goal host surface attested: "
            f"version={receipt.codex_cli_version} "
            f"formal_run_admitted={str(receipt.formal_run_admitted).lower()} "
            f"blocking={','.join(receipt.blocking_reasons)}\n"
        )
        return 0
    candidate = _probe_codex_app_host(args)
    output.write(
        "Codex signed app host candidate attested: "
        f"app={candidate.app_version}+{candidate.app_build} "
        f"version={candidate.codex_cli_version} "
        f"formal_run_admitted={str(candidate.formal_run_admitted).lower()} "
        f"blocking={','.join(candidate.blocking_reasons)}\n"
    )
    return 0


def _probe_codex_app_host(
    args: argparse.Namespace,
) -> CodexGoalNativeHostCandidateReceipt:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    receipt = probe_codex_goal_native_host_candidate(
        app_bundle=args.app_bundle.expanduser().resolve(),
        embedded_codex=args.embedded_codex.expanduser().resolve(),
        expected_cli_version=contract.codex_cli_version,
        contract_sha256=canonical_sha256(contract),
        expected_team_identifier=args.team_identifier,
    )
    _write_new_model(args.output, receipt)
    return receipt


def _finalize_aico(args: argparse.Namespace) -> BossAbsentTaskResult:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    task_set = _read_model(args.tasks, BossAbsentTaskSet)
    state = _read_model(args.state, AicoBenchmarkRunState)
    receipt = _read_model(args.scenario_evidence, AicoScenarioEvidenceReceipt)
    task = next((item for item in task_set.tasks if item.task_id == state.task_id), None)
    if task is None:
        raise ValueError("AICO role state references an unknown frozen task")
    if canonical_sha256(task_set) != contract.task_set_sha256:
        raise ValueError("benchmark task set fingerprint mismatch")
    result = finalize_aico_benchmark_result(contract, task, state, receipt)
    _write_new_model(args.output, result)
    return result


def _finalize_codex_goal(args: argparse.Namespace) -> BossAbsentTaskResult:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    task_set = _read_model(args.tasks, BossAbsentTaskSet)
    admission = _read_model(args.host_admission, CodexGoalHostAdmissionReceipt)
    host_run_observation = _read_model(
        args.host_run_observation,
        CodexGoalHostRunObservationReceipt,
    )
    receipt = _read_model(args.scenario_evidence, CodexGoalScenarioEvidenceReceipt)
    if canonical_sha256(task_set) != contract.task_set_sha256:
        raise ValueError("benchmark task set fingerprint mismatch")
    task = next((item for item in task_set.tasks if item.task_id == receipt.task_id), None)
    if task is None:
        raise ValueError("Codex Goal scenario evidence references an unknown frozen task")
    result = finalize_codex_goal_benchmark_result(
        contract,
        task,
        admission,
        host_run_observation,
        receipt,
    )
    _write_new_model(args.output, result)
    return result


def _finalize_codex_goal_observations(
    args: argparse.Namespace,
) -> CodexGoalScenarioEvidenceReceipt:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    task_set = _read_model(args.tasks, BossAbsentTaskSet)
    admission = _read_model(args.host_admission, CodexGoalHostAdmissionReceipt)
    host_run_observation = _read_model(
        args.host_run_observation,
        CodexGoalHostRunObservationReceipt,
    )
    if canonical_sha256(task_set) != contract.task_set_sha256:
        raise ValueError("benchmark task set fingerprint mismatch")
    store = JsonCodexGoalScenarioObservationStore(args.observations)
    ledger = store.load()
    if ledger is None:
        raise ValueError("Codex Goal scenario observation ledger is missing")
    task = next((item for item in task_set.tasks if item.task_id == ledger.task_id), None)
    if task is None:
        raise ValueError("Codex Goal observation ledger references an unknown frozen task")
    observer = IndependentCodexGoalScenarioObserver(
        contract,
        task,
        admission,
        host_run_observation,
        store,
        observer_build=ledger.observer_build,
    )
    receipt = observer.build_receipt()
    _write_new_model(args.output, receipt)
    return receipt


def _finalize_aico_observations(
    args: argparse.Namespace,
) -> AicoScenarioEvidenceReceipt:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    task_set = _read_model(args.tasks, BossAbsentTaskSet)
    project_config = _read_model(args.project_config, ProjectAssignmentConfig)
    if canonical_sha256(task_set) != contract.task_set_sha256:
        raise ValueError("benchmark task set fingerprint mismatch")
    store = JsonAicoScenarioObservationStore(args.observations)
    ledger = store.load()
    if ledger is None:
        raise ValueError("AICO scenario observation ledger is missing")
    task = next((item for item in task_set.tasks if item.task_id == ledger.task_id), None)
    if task is None:
        raise ValueError("AICO observation ledger references an unknown frozen task")
    observer = IndependentAicoScenarioObserver(
        contract,
        task,
        store,
        project_config=project_config,
        observer_build=ledger.observer_build,
    )
    receipt = observer.build_receipt()
    _write_new_model(args.output, receipt)
    return receipt


async def _advance_aico(args: argparse.Namespace) -> AicoBenchmarkRunState:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    task_set = _read_model(args.tasks, BossAbsentTaskSet)
    project_config = _read_model(args.project_config, ProjectAssignmentConfig)
    if canonical_sha256(task_set) != contract.task_set_sha256:
        raise ValueError("benchmark task set fingerprint mismatch")
    if canonical_sha256(project_config) != contract.project_assignment_sha256:
        raise ValueError("benchmark project assignment fingerprint mismatch")
    if args.project_id != contract.project_id:
        raise ValueError("benchmark project identity mismatch")
    project_directory = ProjectAssignmentDirectory(project_config)
    task = next((item for item in task_set.tasks if item.task_id == args.task_id), None)
    if task is None:
        raise ValueError("AICO runtime references an unknown frozen task")
    _verify_clean_checkout(args.cwd, contract.repo_revision)
    expires_at = _aware_datetime(args.expires_at)
    role_targets = _role_targets(
        args.role_target,
        project_directory=project_directory,
        project_id=args.project_id,
    )
    if {target.role for target in role_targets} != set(task.required_roles):
        raise ValueError("AICO runtime role targets do not match the frozen task")
    adapter = CodexAdapter(
        command=(args.codex, "exec"),
        cwd=args.cwd,
        output_idle_timeout_seconds=args.max_duration_seconds,
        max_concurrent_tasks=1,
    )
    runtime = TaskBusAicoBenchmarkRuntime(
        task_bus=TaskBus(adapter),
        project_directory=project_directory,
        project_id=args.project_id,
        role_targets=role_targets,
        runtime_build=args.runtime_build,
        runtime_instance_sha256=args.runtime_instance_sha256,
        artifact_dir=args.artifact_dir,
        receipt_dir=args.receipt_dir,
        expires_at=expires_at,
        max_duration_seconds=args.max_duration_seconds,
    )
    admission = admit_aico_benchmark_runtime(
        contract,
        runtime.capabilities(
            model=contract.model,
            reasoning_effort=contract.reasoning_effort,
        ),
    )
    return await advance_aico_benchmark_task(
        contract,
        task,
        admission,
        runtime,
        JsonAicoBenchmarkStateStore(args.state),
    )


def _apply_aico_approval(args: argparse.Namespace) -> AicoBenchmarkRunState:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    task_set = _read_model(args.tasks, BossAbsentTaskSet)
    if canonical_sha256(task_set) != contract.task_set_sha256:
        raise ValueError("benchmark task set fingerprint mismatch")
    task = next((item for item in task_set.tasks if item.task_id == args.task_id), None)
    if task is None:
        raise ValueError("AICO approval references an unknown frozen task")
    admission = admit_aico_benchmark_runtime(
        contract,
        AicoBenchmarkRuntimeCapabilities(
            runtime_build=args.runtime_build,
            model=contract.model,
            reasoning_effort=contract.reasoning_effort,
            isolated_run_state=True,
            managed_role_orchestration=True,
            hard_remaining_token_cap=True,
            provider_usage_observable=True,
            durable_dispatch_reconciliation=True,
        ),
    )
    return execute_aico_approval_action(
        contract,
        task,
        admission,
        JsonAicoBenchmarkStateStore(args.state),
        grant_path=args.grant,
        decision_receipt_path=args.decision_receipt,
        mutation_root=args.mutation_root,
        intent_path=args.intent,
        receipt_path=args.receipt,
    )


async def _collect_aico_approval_im(
    args: argparse.Namespace,
) -> AicoImDecisionReceipt:
    contract, task, state = _im_task_state(args)
    if (
        not task.approval_required
        or state.phase is not AicoBenchmarkRunPhase.APPROVAL_PENDING
        or state.approval_request_sha256 is None
    ):
        raise ValueError("AICO approval IM collection requires a pending approval boundary")
    owner, store, request, channel = _im_exchange(
        args,
        contract=contract,
        task_id=task.task_id,
        kind=AicoImExchangeKind.APPROVAL,
        subject_sha256=state.approval_request_sha256,
    )
    decision = await collect_aico_im_decision(
        channel,
        owner,
        request,
        store,
        max_wait_seconds=args.max_wait_seconds,
    )
    if decision.decision is not AicoImDecision.APPROVED:
        raise ValueError("AICO owner rejected the frozen approval action")
    write_aico_approval_grant_from_im(
        contract,
        task,
        state,
        decision_receipt_path=args.exchange_dir / "decision.json",
        grant_path=args.output,
        expires_at=_aware_datetime(args.grant_expires_at),
    )
    return decision


async def _collect_aico_takeover_im(
    args: argparse.Namespace,
) -> AicoImDecisionReceipt:
    contract, task, state = _im_task_state(args)
    if (
        not task.im_takeover_required
        or state.phase is not AicoBenchmarkRunPhase.ROLE_CHAIN_COMPLETE
        or not state.checkpoints
    ):
        raise ValueError("AICO takeover IM collection requires a complete takeover task")
    checkpoint_sha = state.checkpoints[-1].artifact_sha256
    owner, store, request, channel = _im_exchange(
        args,
        contract=contract,
        task_id=task.task_id,
        kind=AicoImExchangeKind.TAKEOVER,
        subject_sha256=checkpoint_sha,
    )
    decision = await collect_aico_im_decision(
        channel,
        owner,
        request,
        store,
        max_wait_seconds=args.max_wait_seconds,
    )
    receipt = build_aico_takeover_ack_from_im(
        contract,
        task,
        checkpoint_sha,
        args.exchange_dir / "decision.json",
    )
    _write_new_model(args.output, receipt)
    return decision


def _im_task_state(
    args: argparse.Namespace,
) -> tuple[BossAbsentBenchmarkContract, BossAbsentTask, AicoBenchmarkRunState]:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    task_set = _read_model(args.tasks, BossAbsentTaskSet)
    if canonical_sha256(task_set) != contract.task_set_sha256:
        raise ValueError("benchmark task set fingerprint mismatch")
    task = next((item for item in task_set.tasks if item.task_id == args.task_id), None)
    if task is None:
        raise ValueError("AICO IM exchange references an unknown frozen task")
    state = _read_model(args.state, AicoBenchmarkRunState)
    if (
        state.contract_sha256 != canonical_sha256(contract)
        or state.benchmark_id != contract.benchmark_id
        or state.task_id != task.task_id
    ):
        raise ValueError("AICO IM exchange state identity drifted")
    return contract, task, state


def _im_exchange(
    args: argparse.Namespace,
    *,
    contract: BossAbsentBenchmarkContract,
    task_id: str,
    kind: AicoImExchangeKind,
    subject_sha256: str,
) -> tuple[AicoImOwnerBinding, AicoImExchangeStore, AicoImExchangeRequest, TelegramChannel]:
    token = os.environ.get(args.telegram_token_env, "").strip()
    if not token:
        raise ValueError(f"AICO IM collector requires {args.telegram_token_env}")
    owner = AicoImOwnerBinding(
        channel_name="telegram",
        target_id=args.target_id,
        sender_id=args.owner_id,
        thread_id=args.thread_id,
    )
    store = AicoImExchangeStore(args.exchange_dir)
    expires_at = _aware_datetime(args.request_expires_at)
    existing = store.load_intent()
    if existing is None:
        request = AicoImExchangeRequest(
            kind=kind,
            contract_sha256=canonical_sha256(contract),
            task_id=task_id,
            subject_sha256=subject_sha256,
            created_at=utc_now(),
            expires_at=expires_at,
        )
    else:
        request = existing.request
    identity = (
        request.kind is kind
        and request.contract_sha256 == canonical_sha256(contract)
        and request.task_id == task_id
        and request.subject_sha256 == subject_sha256
        and request.expires_at == expires_at
    )
    if not identity:
        raise ValueError("AICO IM persisted request identity drifted")
    channel = TelegramChannel(
        token,
        poll_timeout_seconds=max(1, min(30, int(args.max_wait_seconds))),
    )
    return owner, store, request, channel


def _role_targets(
    values: Sequence[str],
    *,
    project_directory: ProjectAssignmentDirectory,
    project_id: str,
) -> tuple[AicoBenchmarkRoleTarget, ...]:
    result: list[AicoBenchmarkRoleTarget] = []
    for value in values:
        role, separator, remainder = value.partition("=")
        agent_id, persona_separator, persona = remainder.partition(":")
        if not separator or not persona_separator or not role or not agent_id or not persona:
            raise ValueError("AICO role target must use role=agent_id:target_persona syntax")
        assignment = project_directory.appointment_for_role(project_id, role)
        if assignment is None or assignment.agent != agent_id:
            raise ValueError("AICO role target does not match the project appointment")
        result.append(
            AicoBenchmarkRoleTarget(
                role=role,
                agent_id=agent_id,
                assignment_seat=assignment.seat,
                target_persona=persona,
            )
        )
    if not result:
        raise ValueError("AICO runtime requires at least one role target")
    return tuple(result)


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("AICO runtime expiry is not ISO-8601") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("AICO runtime expiry must be timezone-aware")
    return parsed


def _verify_clean_checkout(cwd: Path, expected_revision: str) -> None:
    if not cwd.is_absolute() or not cwd.is_dir() or cwd.is_symlink():
        raise ValueError("AICO benchmark checkout must be an absolute non-symlink directory")
    try:
        head = subprocess.run(
            ("git", "-C", str(cwd), "rev-parse", "HEAD"),
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        status = subprocess.run(
            ("git", "-C", str(cwd), "status", "--porcelain=v1"),
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        raise ValueError("AICO benchmark checkout could not be verified") from None
    if head != expected_revision:
        raise ValueError("AICO benchmark checkout revision drifted")
    if status:
        raise ValueError("AICO benchmark checkout is not clean")


def _read_model(path: Path, model_type: type[ModelT]) -> ModelT:
    payload = _read_bounded(path, _MAX_JSON_BYTES)
    return model_type.model_validate(_loads_unique(payload))


def _read_results(path: Path) -> tuple[BossAbsentTaskResult, ...]:
    payload = _read_bounded(path, _MAX_RESULTS_BYTES)
    results: list[BossAbsentTaskResult] = []
    for line in payload.splitlines():
        if not line.strip():
            continue
        if len(line.encode("utf-8")) > _MAX_RESULT_LINE_BYTES:
            raise ValueError("benchmark result line exceeds bounded size")
        results.append(BossAbsentTaskResult.model_validate(_loads_unique(line)))
    if not results:
        raise ValueError("benchmark results are empty")
    return tuple(results)


def _read_bounded(path: Path, limit: int) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError("benchmark input must be a regular non-symlink file")
    with path.open("rb") as source:
        content = source.read(limit + 1)
    if len(content) > limit:
        raise ValueError("benchmark input exceeds bounded size")
    return content.decode("utf-8")


def _loads_unique(payload: str) -> object:
    def unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("benchmark JSON contains a duplicate key")
            result[key] = value
        return result

    def reject_non_finite(value: str) -> object:
        raise ValueError(f"benchmark JSON contains non-finite number: {value}")

    try:
        return json.loads(
            payload,
            object_pairs_hook=unique_pairs,
            parse_constant=reject_non_finite,
        )
    except json.JSONDecodeError:
        raise ValueError("benchmark JSON is invalid") from None


def _write_new_model(path: Path, model: BaseModel) -> None:
    _write_new_text(path, model.model_dump_json(indent=2) + "\n")


def _write_jsonl(path: Path, models: Sequence[BaseModel]) -> None:
    _write_new_text(path, "".join(f"{model.model_dump_json()}\n" for model in models))


def _write_report_dir(
    output_dir: Path,
    aico: BossAbsentBenchmarkSummary,
    codex_goal: BossAbsentBenchmarkSummary,
    verdict: BossAbsentBenchmarkVerdict,
) -> None:
    output_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    _write_new_model(output_dir / "aico-summary.json", aico)
    _write_new_model(output_dir / "codex-goal-summary.json", codex_goal)
    _write_new_model(output_dir / "verdict.json", verdict)
    _write_new_text(output_dir / "verdict.md", _verdict_markdown(aico, codex_goal, verdict))


def _write_new_text(path: Path, content: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        if path.exists():
            path.unlink()
        raise


def _verdict_markdown(
    aico: BossAbsentBenchmarkSummary,
    codex_goal: BossAbsentBenchmarkSummary,
    verdict: BossAbsentBenchmarkVerdict,
) -> str:
    rows = (
        (
            "Unattended completion",
            _rate_text(aico.unattended_completion),
            _rate_text(codex_goal.unattended_completion),
        ),
        (
            "Collaboration completion",
            _rate_text(aico.collaboration_completion),
            _rate_text(codex_goal.collaboration_completion),
        ),
        ("Takeover effective actions", _actions_text(aico), _actions_text(codex_goal)),
        ("Budget loss", _rate_text(aico.budget_loss), _rate_text(codex_goal.budget_loss)),
        (
            "Evidence completeness",
            _rate_text(aico.evidence_completeness),
            _rate_text(codex_goal.evidence_completeness),
        ),
    )
    lines = [
        "# Boss-Absent Benchmark Verdict",
        "",
        f"- benchmark: `{verdict.benchmark_id}`",
        f"- contract: `{verdict.contract_sha256}`",
        f"- AICO wins: `{str(verdict.aico_wins).lower()}`",
        f"- strictly better metrics: `{verdict.strict_better_metrics}/5`",
        "",
        "| Metric | AICO | Codex Goal | Comparison |",
        "|---|---:|---:|---|",
    ]
    for metric, aico_value, codex_value in rows:
        comparison_key = {
            "Unattended completion": "unattended_completion",
            "Collaboration completion": "collaboration_completion",
            "Takeover effective actions": "takeover_cost",
            "Budget loss": "budget_loss",
            "Evidence completeness": "evidence_completeness",
        }[metric]
        lines.append(
            f"| {metric} | {aico_value} | {codex_value} | "
            f"{verdict.comparisons[comparison_key].value} |"
        )
    lines.extend(("", "## Gates", ""))
    lines.extend(f"- [{'x' if passed else ' '}] {name}" for name, passed in verdict.gates.items())
    lines.extend(("", "## Verdict reasons", ""))
    lines.extend(f"- {reason}" for reason in verdict.reasons)
    lines.append("")
    return "\n".join(lines)


def _rate_text(rate: BenchmarkRate) -> str:
    return "n/a" if rate.denominator == 0 else f"{rate.numerator}/{rate.denominator}"


def _actions_text(summary: BossAbsentBenchmarkSummary) -> str:
    value = summary.takeover_cost.median_effective_actions
    return "n/a" if value is None else f"{value:g}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aico-benchmark",
        description="Freeze and score the evidence-first boss-absent benchmark.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_freeze_arguments(subparsers)
    score = subparsers.add_parser("score", help="Score frozen AICO and Codex Goal results.")
    score.add_argument("--contract", type=Path, required=True)
    score.add_argument("--tasks", type=Path, required=True)
    score.add_argument("--results", type=Path, required=True)
    score.add_argument("--output-dir", type=Path, required=True)
    dry_run = subparsers.add_parser(
        "dry-run",
        help="Exercise scenario artifacts with equal fake observations and no model calls.",
    )
    dry_run.add_argument("--contract", type=Path, required=True)
    dry_run.add_argument("--tasks", type=Path, required=True)
    dry_run.add_argument("--output-dir", type=Path, required=True)
    probe = subparsers.add_parser(
        "probe-codex-goal",
        help="Create, verify, clear, and delete a no-model persistent Goal thread.",
    )
    probe.add_argument("--contract", type=Path, required=True)
    probe.add_argument("--cwd", type=Path, required=True)
    probe.add_argument("--output", type=Path, required=True)
    probe.add_argument("--codex", default="codex")
    _add_codex_host_probe_arguments(subparsers)
    _add_codex_finalize_arguments(subparsers)
    finalize = subparsers.add_parser(
        "finalize-aico",
        help="Bind an AICO role state to independent scenario evidence.",
    )
    finalize.add_argument("--contract", type=Path, required=True)
    finalize.add_argument("--tasks", type=Path, required=True)
    finalize.add_argument("--state", type=Path, required=True)
    finalize.add_argument("--scenario-evidence", type=Path, required=True)
    finalize.add_argument("--output", type=Path, required=True)
    observations = subparsers.add_parser(
        "finalize-aico-observations",
        help="Derive a scenario receipt from an independent owner-only observation ledger.",
    )
    observations.add_argument("--contract", type=Path, required=True)
    observations.add_argument("--tasks", type=Path, required=True)
    observations.add_argument("--project-config", type=Path, required=True)
    observations.add_argument("--observations", type=Path, required=True)
    observations.add_argument("--output", type=Path, required=True)
    advance = subparsers.add_parser(
        "advance-aico",
        help="Advance exactly one frozen AICO role through TaskBus and Codex.",
    )
    advance.add_argument("--contract", type=Path, required=True)
    advance.add_argument("--tasks", type=Path, required=True)
    advance.add_argument("--project-config", type=Path, required=True)
    advance.add_argument("--project-id", required=True)
    advance.add_argument("--task-id", required=True)
    advance.add_argument("--state", type=Path, required=True)
    advance.add_argument("--artifact-dir", type=Path, required=True)
    advance.add_argument("--receipt-dir", type=Path, required=True)
    advance.add_argument("--cwd", type=Path, required=True)
    advance.add_argument("--runtime-build", required=True)
    advance.add_argument("--runtime-instance-sha256", required=True)
    advance.add_argument("--expires-at", required=True)
    advance.add_argument("--max-duration-seconds", type=float, required=True)
    advance.add_argument("--role-target", action="append", required=True)
    advance.add_argument("--codex", default="codex")
    approval = subparsers.add_parser(
        "apply-aico-approval",
        help="Apply one exact owner grant to the isolated approval fixture at most once.",
    )
    approval.add_argument("--contract", type=Path, required=True)
    approval.add_argument("--tasks", type=Path, required=True)
    approval.add_argument("--task-id", required=True)
    approval.add_argument("--state", type=Path, required=True)
    approval.add_argument("--runtime-build", required=True)
    approval.add_argument("--grant", type=Path, required=True)
    approval.add_argument("--decision-receipt", type=Path, required=True)
    approval.add_argument("--mutation-root", type=Path, required=True)
    approval.add_argument("--intent", type=Path, required=True)
    approval.add_argument("--receipt", type=Path, required=True)
    approval_im = subparsers.add_parser(
        "collect-aico-approval-im",
        help="Collect one owner-bound Telegram approval and issue its exact grant.",
    )
    _add_im_arguments(approval_im)
    approval_im.add_argument("--grant-expires-at", required=True)
    takeover_im = subparsers.add_parser(
        "collect-aico-takeover-im",
        help="Collect one owner-bound Telegram terminal takeover acknowledgement.",
    )
    _add_im_arguments(takeover_im)
    return parser


def _add_freeze_arguments(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    freeze = subparsers.add_parser("freeze", help="Freeze a contract before model calls.")
    freeze.add_argument("--tasks", type=Path, required=True)
    freeze.add_argument("--project-config", type=Path, required=True)
    freeze.add_argument("--project-id", required=True)
    freeze.add_argument("--output", type=Path, required=True)
    freeze.add_argument("--benchmark-id", required=True)
    freeze.add_argument("--model", required=True)
    freeze.add_argument("--reasoning-effort", required=True)
    freeze.add_argument("--repo-revision", required=True)
    freeze.add_argument("--aico-version", required=True)
    freeze.add_argument("--codex-cli-version", required=True)
    freeze.add_argument("--wall-window-seconds", type=int, required=True)
    freeze.add_argument("--max-total-tokens", type=int, required=True)
    freeze.add_argument("--takeover-action-cap", type=int, default=20)
    freeze.add_argument("--takeover-seconds-cap", type=int, default=900)


def _add_codex_host_probe_arguments(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    host_probe = subparsers.add_parser(
        "probe-codex-goal-host",
        help="Attest why the installed app-server is not a native Goal continuation host.",
    )
    host_probe.add_argument("--contract", type=Path, required=True)
    host_probe.add_argument("--output", type=Path, required=True)
    host_probe.add_argument("--codex", default="codex")
    app_host_probe = subparsers.add_parser(
        "probe-codex-app-host",
        help="Bind a signed first-party Codex App build to native Goal continuation semantics.",
    )
    app_host_probe.add_argument("--contract", type=Path, required=True)
    app_host_probe.add_argument("--output", type=Path, required=True)
    app_host_probe.add_argument(
        "--app-bundle",
        type=Path,
        default=Path("/Applications/ChatGPT.app"),
    )
    app_host_probe.add_argument(
        "--embedded-codex",
        type=Path,
        default=Path("/Applications/ChatGPT.app/Contents/Resources/codex"),
    )
    app_host_probe.add_argument("--team-identifier", default="2DC432GLL2")


def _add_codex_finalize_arguments(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    finalize = subparsers.add_parser(
        "finalize-codex-goal",
        help="Bind a native Codex Goal host run to independent scenario evidence.",
    )
    finalize.add_argument("--contract", type=Path, required=True)
    finalize.add_argument("--tasks", type=Path, required=True)
    finalize.add_argument("--host-admission", type=Path, required=True)
    finalize.add_argument("--host-run-observation", type=Path, required=True)
    finalize.add_argument("--scenario-evidence", type=Path, required=True)
    finalize.add_argument("--output", type=Path, required=True)
    observations = subparsers.add_parser(
        "finalize-codex-goal-observations",
        help="Derive Codex Goal scenario evidence from an independent hash-chain ledger.",
    )
    observations.add_argument("--contract", type=Path, required=True)
    observations.add_argument("--tasks", type=Path, required=True)
    observations.add_argument("--host-admission", type=Path, required=True)
    observations.add_argument("--host-run-observation", type=Path, required=True)
    observations.add_argument("--observations", type=Path, required=True)
    observations.add_argument("--output", type=Path, required=True)


def _add_im_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--exchange-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--owner-id", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--thread-id")
    parser.add_argument("--request-expires-at", required=True)
    parser.add_argument("--max-wait-seconds", type=float, required=True)
    parser.add_argument("--telegram-token-env", default="AICO_TELEGRAM_BOT_TOKEN")
    parser.add_argument(
        "--exclusive-channel",
        action="store_true",
        required=True,
        help="Confirm this one-shot collector exclusively owns Telegram polling.",
    )


if __name__ == "__main__":
    main()
