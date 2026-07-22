"""Create and verify runtime commissioning receipts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aico.app.runtime_commissioning import (
    RuntimeCommissioningError,
    create_runtime_commissioning_receipt,
    verify_runtime_commissioning_receipt,
)


def main() -> None:
    args = _parser().parse_args()
    common = {
        "checkout_path": args.checkout,
        "project_config_path": args.project_config,
        "persona_config_path": args.persona_config,
        "expected_config_revision": args.expected_config_revision,
        "dotenv_path": args.dotenv,
        "dead_man_evidence_path": args.dead_man_evidence,
        "trusted_receiver_public_key_path": args.trusted_receiver_public_key,
    }
    try:
        if args.command == "create":
            summary = create_runtime_commissioning_receipt(
                **common,
                runtime_id=args.runtime_id,
                maximum_evidence_age_seconds=args.maximum_evidence_age_seconds,
                output_path=args.output,
            )
        else:
            summary = verify_runtime_commissioning_receipt(
                **common,
                expected_runtime_id=args.runtime_id,
                receipt_path=args.receipt,
                expected_receipt_sha256=args.expected_receipt_sha256,
            )
    except RuntimeCommissioningError as exc:
        print(f"runtime commissioning failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    print(summary.model_dump_json())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aico-commission",
        description="Bind reviewed runtime configuration to current external evidence.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    verify = subparsers.add_parser("verify")
    for command in (create, verify):
        command.add_argument("--checkout", type=Path, required=True)
        command.add_argument("--project-config", type=Path, required=True)
        command.add_argument("--persona-config", type=Path)
        command.add_argument("--expected-config-revision", required=True)
        command.add_argument("--runtime-id", required=True)
        command.add_argument("--dotenv", type=Path, required=True)
        command.add_argument("--dead-man-evidence", type=Path, required=True)
        command.add_argument("--trusted-receiver-public-key", type=Path, required=True)
    create.add_argument(
        "--maximum-evidence-age-seconds",
        type=int,
        required=True,
    )
    create.add_argument("--output", type=Path, required=True)
    verify.add_argument("--receipt", type=Path, required=True)
    verify.add_argument("--expected-receipt-sha256")
    return parser
