"""Freeze and score evidence-safe AICO vs Codex Goal benchmark artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO, TypeVar

from pydantic import BaseModel

from aico.app.boss_absent_aico_evidence import (
    AicoScenarioEvidenceReceipt,
    finalize_aico_benchmark_result,
)
from aico.app.boss_absent_aico_runner import AicoBenchmarkRunState
from aico.app.boss_absent_benchmark_restart_probe import run_restart_probe
from aico.app.boss_absent_codex_goal_probe import (
    CodexGoalProtocolReceipt,
    probe_codex_goal_protocol,
)
from aico.core.boss_absent_benchmark import (
    BenchmarkRate,
    BenchmarkSystem,
    BossAbsentBenchmarkContract,
    BossAbsentBenchmarkSummary,
    BossAbsentBenchmarkVerdict,
    BossAbsentTaskResult,
    BossAbsentTaskSet,
    canonical_sha256,
    compare_boss_absent_summaries,
    score_boss_absent_system,
)
from aico.core.boss_absent_benchmark_harness import run_synthetic_benchmark_harness
from aico.core.models import utc_now

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
        if args.command == "finalize-aico":
            result = _finalize_aico(args)
            output.write(
                "AICO scenario evidence finalized: "
                f"task={result.task_id} status={result.terminal_status.value} "
                f"tokens={result.total_tokens}\n"
            )
            return 0
    except (OSError, UnicodeError, ValueError) as exc:
        error.write(f"benchmark failed: {exc}\n")
        return 2
    raise AssertionError("unknown benchmark command")


def main() -> None:
    raise SystemExit(run())


def _freeze_contract(args: argparse.Namespace) -> BossAbsentBenchmarkContract:
    task_set = _read_model(args.tasks, BossAbsentTaskSet)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        output.write(model.model_dump_json(indent=2))
        output.write("\n")


def _write_jsonl(path: Path, models: Sequence[BaseModel]) -> None:
    with path.open("x", encoding="utf-8") as output:
        for model in models:
            output.write(model.model_dump_json())
            output.write("\n")


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
    with (output_dir / "verdict.md").open("x", encoding="utf-8") as output:
        output.write(_verdict_markdown(aico, codex_goal, verdict))


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
    freeze = subparsers.add_parser("freeze", help="Freeze a contract before model calls.")
    freeze.add_argument("--tasks", type=Path, required=True)
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
    finalize = subparsers.add_parser(
        "finalize-aico",
        help="Bind an AICO role state to independent scenario evidence.",
    )
    finalize.add_argument("--contract", type=Path, required=True)
    finalize.add_argument("--tasks", type=Path, required=True)
    finalize.add_argument("--state", type=Path, required=True)
    finalize.add_argument("--scenario-evidence", type=Path, required=True)
    finalize.add_argument("--output", type=Path, required=True)
    return parser


if __name__ == "__main__":
    main()
