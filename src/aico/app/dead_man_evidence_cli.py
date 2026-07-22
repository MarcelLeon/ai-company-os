"""Offline verification for exported dead-man outage evidence."""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from aico.app.dead_man_receiver import DeadManEvidenceBundle, DeadManEvidenceEvent


class DeadManEvidenceVerificationError(ValueError):
    pass


class DeadManEvidenceVerificationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["valid"] = "valid"
    schema_version: Literal[5] = 5
    runtime_id: str
    complete_outages: int = Field(ge=0)
    event_count: int = Field(ge=0)
    delivered_events: int = Field(ge=0)
    route_health_alerts: int = Field(ge=0)
    delivered_route_health_alerts: int = Field(ge=0)
    degraded_routes: int = Field(ge=0, le=2)
    notification_probe_enabled: bool
    notification_probe_pending: bool
    notification_probe_fresh: bool
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def verify_evidence_bytes(
    raw: bytes,
    *,
    expected_runtime_id: str | None = None,
    minimum_complete_outages: int = 0,
    require_all_delivered: bool = False,
    maximum_evidence_age_seconds: float | None = None,
    require_fresh_notification_probe: bool = False,
    require_all_routes_healthy: bool = False,
    now: datetime | None = None,
) -> DeadManEvidenceVerificationSummary:
    if minimum_complete_outages < 0:
        raise DeadManEvidenceVerificationError("minimum completed outages cannot be negative")
    try:
        bundle = DeadManEvidenceBundle.model_validate_json(raw)
    except ValidationError as exc:
        raise DeadManEvidenceVerificationError("evidence schema or invariants are invalid") from exc
    if expected_runtime_id is not None and bundle.runtime_id != expected_runtime_id:
        raise DeadManEvidenceVerificationError("runtime identity does not match")
    verification_time = now or datetime.now(UTC)
    _verify_freshness(
        bundle,
        maximum_age_seconds=maximum_evidence_age_seconds,
        now=verification_time,
    )
    if bundle.complete_outage_count < minimum_complete_outages:
        raise DeadManEvidenceVerificationError("completed outage requirement is not met")
    events = _all_events(bundle)
    delivered = sum(event.delivered for event in events)
    delivered_route_alerts = sum(alert.delivered for alert in bundle.route_health_alerts)
    if require_all_delivered and (
        delivered != len(events) or delivered_route_alerts != len(bundle.route_health_alerts)
    ):
        raise DeadManEvidenceVerificationError("evidence contains pending delivery")
    if require_fresh_notification_probe:
        _verify_current_notification_probe(bundle, now=verification_time)
    if require_all_routes_healthy and any(
        route.status.value != "healthy" for route in bundle.notification_routes
    ):
        raise DeadManEvidenceVerificationError("notification route health requirement is not met")
    return DeadManEvidenceVerificationSummary(
        runtime_id=bundle.runtime_id,
        complete_outages=bundle.complete_outage_count,
        event_count=len(events),
        delivered_events=delivered,
        route_health_alerts=len(bundle.route_health_alerts),
        delivered_route_health_alerts=delivered_route_alerts,
        degraded_routes=sum(
            route.status.value == "degraded" for route in bundle.notification_routes
        ),
        notification_probe_enabled=bundle.notification_probe.contract.value != "disabled",
        notification_probe_pending=bundle.notification_probe.pending_probe is not None,
        notification_probe_fresh=bundle.notification_probe_fresh,
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def _verify_freshness(
    bundle: DeadManEvidenceBundle,
    *,
    maximum_age_seconds: float | None,
    now: datetime,
) -> None:
    if maximum_age_seconds is None:
        return
    if not math.isfinite(maximum_age_seconds) or maximum_age_seconds <= 0:
        raise DeadManEvidenceVerificationError("maximum evidence age must be positive")
    if now.tzinfo is None:
        raise DeadManEvidenceVerificationError("verification time must be timezone-aware")
    if bundle.generated_at > now:
        raise DeadManEvidenceVerificationError("evidence generation time is in the future")
    age_seconds = (now - bundle.generated_at).total_seconds()
    if age_seconds > maximum_age_seconds:
        raise DeadManEvidenceVerificationError("evidence freshness requirement is not met")


def _verify_current_notification_probe(
    bundle: DeadManEvidenceBundle,
    *,
    now: datetime,
) -> None:
    if now.tzinfo is None:
        raise DeadManEvidenceVerificationError("verification time must be timezone-aware")
    probe = bundle.notification_probe
    if (
        bundle.generated_at > now
        or probe.contract.value == "disabled"
        or probe.pending_probe is not None
        or probe.last_completed_at is None
        or not probe.is_fresh(at=now)
    ):
        raise DeadManEvidenceVerificationError(
            "notification probe freshness requirement is not met"
        )


def _all_events(bundle: DeadManEvidenceBundle) -> tuple[DeadManEvidenceEvent, ...]:
    events: list[DeadManEvidenceEvent] = []
    for outage in bundle.outages:
        events.append(outage.opened)
        if outage.resolved is not None:
            events.append(outage.resolved)
    return tuple(events)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify an exported AICO dead-man evidence bundle offline.",
    )
    parser.add_argument("bundle", type=Path, help="Path to the exported JSON bundle")
    parser.add_argument("--runtime-id", help="Require this safe runtime identity")
    parser.add_argument(
        "--minimum-complete-outages",
        type=int,
        default=1,
        help="Require at least this many opened/resolved outage pairs (default: 1)",
    )
    parser.add_argument(
        "--require-all-delivered",
        action="store_true",
        help="Fail unless every exported event was locally acknowledged by the downstream sink",
    )
    parser.add_argument(
        "--maximum-evidence-age-seconds",
        type=float,
        help="Fail when bundle generated_at is older than this positive limit",
    )
    parser.add_argument(
        "--require-fresh-notification-probe",
        action="store_true",
        help="Require an enabled, settled, currently fresh silent notification probe",
    )
    parser.add_argument(
        "--require-all-routes-healthy",
        action="store_true",
        help="Fail unless every configured notification route is currently healthy",
    )
    args = parser.parse_args()
    try:
        raw = args.bundle.read_bytes()
        summary = verify_evidence_bytes(
            raw,
            expected_runtime_id=args.runtime_id,
            minimum_complete_outages=args.minimum_complete_outages,
            require_all_delivered=args.require_all_delivered,
            maximum_evidence_age_seconds=args.maximum_evidence_age_seconds,
            require_fresh_notification_probe=args.require_fresh_notification_probe,
            require_all_routes_healthy=args.require_all_routes_healthy,
        )
    except (OSError, DeadManEvidenceVerificationError) as exc:
        message = (
            str(exc) if isinstance(exc, DeadManEvidenceVerificationError) else "cannot read bundle"
        )
        print(f"evidence verification failed: {message}", file=sys.stderr)
        raise SystemExit(2) from None
    print(summary.model_dump_json())
