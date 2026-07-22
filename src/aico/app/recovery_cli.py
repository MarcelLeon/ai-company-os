"""Operator CLI for core state/audit/memory recovery-set capture and drills."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from aico.app.provider_auth_probe import build_cli_provider_probe
from aico.app.provider_authentication import (
    ProviderAuthenticationError,
    ProviderAuthenticationSummary,
    ProviderProbeFactory,
    create_provider_authentication_receipt,
    verify_provider_authentication_receipt,
)
from aico.app.recovery_reinjection import (
    RecoveryReinjectionError,
    RecoveryReinjectionSummary,
    create_recovery_reinjection_receipt,
    verify_recovery_reinjection_receipt,
)
from aico.app.recovery_set import (
    RecoverySetCheckoutSummary,
    RecoverySetDrillSummary,
    RecoverySetError,
    RecoverySetSummary,
    create_recovery_set,
    drill_recovery_set,
    verify_recovery_checkout,
    verify_recovery_set,
)

RecoverySummary = (
    RecoverySetSummary
    | RecoverySetDrillSummary
    | RecoverySetCheckoutSummary
    | RecoveryReinjectionSummary
    | ProviderAuthenticationSummary
)


def run(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    environ: dict[str, str] | None = None,
    provider_probe_factory: ProviderProbeFactory = build_cli_provider_probe,
) -> int:
    args = _parser().parse_args(argv)
    environment = dict(os.environ) if environ is None else environ
    try:
        summary = _execute(args, environment, provider_probe_factory)
    except (ProviderAuthenticationError, RecoveryReinjectionError, RecoverySetError) as exc:
        stderr.write(f"Core recovery set {args.command} failed: {exc}\n")
        return 2
    except OSError:
        stderr.write(f"Core recovery set {args.command} failed: local file operation failed\n")
        return 2
    stdout.write(summary.model_dump_json() + "\n")
    return 0


def _execute(
    args: argparse.Namespace,
    environment: dict[str, str],
    provider_probe_factory: ProviderProbeFactory,
) -> RecoverySummary:
    if args.command == "capture":
        return _capture(args, environment)
    if args.command == "verify":
        return verify_recovery_set(args.recovery_set, expected_sha256=args.expected_sha256)
    if args.command == "verify-checkout":
        return verify_recovery_checkout(
            args.recovery_set,
            expected_sha256=args.expected_sha256,
            checkout_path=args.checkout,
        )
    if args.command == "reinjection-receipt":
        return create_recovery_reinjection_receipt(
            args.recovery_set,
            expected_recovery_set_sha256=args.expected_sha256,
            checkout_path=args.checkout,
            output_path=args.output,
            owner_decision_ref=args.owner_decision_ref,
        )
    if args.command == "verify-reinjection":
        return verify_recovery_reinjection_receipt(
            args.recovery_set,
            expected_recovery_set_sha256=args.expected_sha256,
            checkout_path=args.checkout,
            receipt_path=args.receipt,
            expected_receipt_sha256=args.expected_receipt_sha256,
        )
    if args.command == "provider-auth-receipt":
        return create_provider_authentication_receipt(
            args.recovery_set,
            expected_recovery_set_sha256=args.expected_sha256,
            checkout_path=args.checkout,
            reinjection_receipt_path=args.reinjection_receipt,
            expected_reinjection_receipt_sha256=args.expected_reinjection_receipt_sha256,
            output_path=args.output,
            probe_factory=provider_probe_factory,
        )
    if args.command == "verify-provider-auth":
        return verify_provider_authentication_receipt(
            args.recovery_set,
            expected_recovery_set_sha256=args.expected_sha256,
            checkout_path=args.checkout,
            reinjection_receipt_path=args.reinjection_receipt,
            expected_reinjection_receipt_sha256=args.expected_reinjection_receipt_sha256,
            receipt_path=args.receipt,
            expected_receipt_sha256=args.expected_receipt_sha256,
        )
    return drill_recovery_set(
        args.recovery_set,
        expected_sha256=args.expected_sha256,
        workspace=args.workspace,
        report_path=args.report,
    )


def _capture(args: argparse.Namespace, environment: dict[str, str]) -> RecoverySetSummary:
    state = args.state_db or _path_from_env(environment, "AICO_STATE_DB_PATH")
    audit = args.audit_log or _path_from_env(environment, "AICO_AUDIT_LOG_PATH")
    memory = args.memory_log or _path_from_env(environment, "AICO_MEMORY_PATH")
    project = args.project_config or _path_from_env(environment, "AICO_PROJECT_CONFIG_PATH")
    persona = args.persona_config or _path_from_env(environment, "AICO_PERSONA_CONFIG_PATH")
    checkout = args.checkout or _path_from_env(environment, "AICO_CHECKOUT_PATH") or Path.cwd()
    revision = (
        args.expected_config_revision
        or environment.get("AICO_REVIEWED_CONFIG_REVISION", "").strip()
    )
    if state is None or audit is None or memory is None or project is None or not revision:
        raise RecoverySetError(
            "state, audit, memory, project config, and reviewed revision are required"
        )
    return create_recovery_set(
        state,
        audit,
        memory,
        args.output,
        checkout_path=checkout,
        project_config_path=project,
        expected_config_revision=revision,
        persona_config_path=persona,
    )


def main() -> None:
    raise SystemExit(run())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Capture and validate an explicitly non-transactional AICO core recovery set.")
    )
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser(
        "capture",
        help="Capture state, audit, and memory artifacts in one bounded-window set",
    )
    capture.add_argument("--state-db", type=Path, help="Live AICO state DB path")
    capture.add_argument("--audit-log", type=Path, help="Live AICO audit JSONL path")
    capture.add_argument("--memory-log", type=Path, help="Live AICO memory JSONL path")
    capture.add_argument("--checkout", type=Path, help="Clean Git worktree root; defaults to cwd")
    capture.add_argument("--project-config", type=Path, help="Tracked active project config")
    capture.add_argument(
        "--expected-config-revision",
        help="Exact full Git commit selected by the review authority",
    )
    capture.add_argument(
        "--persona-config",
        type=Path,
        help="Tracked active persona config; omit when using built-in personas",
    )
    capture.add_argument("--output", required=True, type=Path, help="New recovery-set ZIP path")
    verify = commands.add_parser("verify", help="Verify all embedded component artifacts")
    _add_artifact_arguments(verify)
    checkout = commands.add_parser(
        "verify-checkout",
        help="Verify a clean checkout and active configs against the recovery set revision",
    )
    _add_artifact_arguments(checkout)
    checkout.add_argument("--checkout", required=True, type=Path, help="Restored Git root")
    receipt = commands.add_parser(
        "reinjection-receipt",
        help="Verify reinjected runtime material and create an owner-only receipt",
    )
    _add_artifact_arguments(receipt)
    receipt.add_argument("--checkout", required=True, type=Path, help="Restored Git root")
    receipt.add_argument("--output", required=True, type=Path, help="New receipt JSON path")
    receipt.add_argument(
        "--owner-decision-ref",
        required=True,
        help="Safe incident/change reference for the explicit post-restore owner decision",
    )
    reinjection = commands.add_parser(
        "verify-reinjection",
        help="Re-verify an owner-only reinjection receipt against the current runtime material",
    )
    _add_artifact_arguments(reinjection)
    reinjection.add_argument("--checkout", required=True, type=Path, help="Restored Git root")
    reinjection.add_argument("--receipt", required=True, type=Path, help="Receipt JSON path")
    reinjection.add_argument(
        "--expected-receipt-sha256",
        required=True,
        help="Receipt SHA-256 recorded in an independent authority",
    )
    provider_receipt = commands.add_parser(
        "provider-auth-receipt",
        help="Run constrained live provider probes and create a short-lived owner-only receipt",
    )
    _add_artifact_arguments(provider_receipt)
    _add_provider_binding_arguments(provider_receipt)
    provider_receipt.add_argument("--output", required=True, type=Path, help="New receipt JSON")
    provider_verify = commands.add_parser(
        "verify-provider-auth",
        help="Verify a short-lived provider receipt without replaying the paid live probes",
    )
    _add_artifact_arguments(provider_verify)
    _add_provider_binding_arguments(provider_verify)
    provider_verify.add_argument("--receipt", required=True, type=Path, help="Provider receipt")
    provider_verify.add_argument(
        "--expected-receipt-sha256",
        required=True,
        help="Provider receipt SHA-256 recorded in an independent authority",
    )
    drill = commands.add_parser(
        "drill",
        help="Run all production component materializers in a disposable workspace",
    )
    _add_artifact_arguments(drill)
    drill.add_argument("--workspace", type=Path, help="Existing disposable workspace parent")
    drill.add_argument("--report", type=Path, help="New owner-only drill report path")
    return parser


def _add_artifact_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--recovery-set",
        required=True,
        type=Path,
        help="Core recovery-set artifact path",
    )
    parser.add_argument(
        "--expected-sha256",
        required=True,
        help="Recovery-set SHA-256 recorded in an independent authority",
    )


def _add_provider_binding_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--checkout", required=True, type=Path, help="Restored Git root")
    parser.add_argument(
        "--reinjection-receipt",
        required=True,
        type=Path,
        help="Verified runtime reinjection receipt",
    )
    parser.add_argument(
        "--expected-reinjection-receipt-sha256",
        required=True,
        help="Reinjection receipt SHA-256 recorded in an independent authority",
    )


def _path_from_env(environ: dict[str, str], key: str) -> Path | None:
    value = environ.get(key, "").strip()
    if key == "AICO_STATE_DB_PATH":
        normalized = value.casefold()
        if normalized in {"0", "false", "no", "off"}:
            return None
        if normalized in {"1", "true", "yes", "on"}:
            return Path(".aico/state.db")
    return Path(value).expanduser() if value else None
