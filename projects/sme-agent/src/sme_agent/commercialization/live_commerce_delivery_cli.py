"""Operator CLI for a governed live-commerce customer workspace run."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from sme_agent.commercialization.live_commerce_delivery import (
    LiveCommerceDeliveryInput,
    LiveCommerceDeliveryRunner,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = LiveCommerceDeliveryRunner().run(
            LiveCommerceDeliveryInput(
                output_dir=args.output_dir,
                customer_id=args.customer_id,
                display_name=args.display_name,
                run_id=args.run_id,
                primary_question=args.question,
                authorization_reference=args.authorization_reference,
                live_sessions_csv=args.live_sessions_csv,
                orders_csv=args.orders_csv,
                service_tier=args.service_tier,
                persist_source_files=args.persist_source_files,
            )
        )
    except (OSError, ValueError) as exc:
        print(
            json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            {
                "status": result.status.value,
                "workspace": str(result.workspace.root),
                "delivery_status": str(result.delivery_status_path),
                "evidence_manifest": str(result.evidence_manifest_path),
                "diagnosis_draft": str(result.report_path) if result.report_path else None,
                "raw_sources_retained": bool(result.persisted_source_paths),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create one governed SME Agent live-commerce delivery run."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--customer-id", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--authorization-reference", required=True)
    parser.add_argument("--live-sessions-csv", type=Path, required=True)
    parser.add_argument("--orders-csv", type=Path, required=True)
    parser.add_argument("--service-tier", default="intro_diagnosis")
    parser.add_argument("--persist-source-files", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
