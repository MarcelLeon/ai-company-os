"""Shared machine-contract names for explicit boss-absent admission."""

from __future__ import annotations

from collections.abc import Mapping

ABSENCE_ADMISSION_MODES = frozenset({"optional", "strict"})
STRICT_ABSENCE_CONTRACTS = (
    "runtime alerts",
    "runtime liveness",
    "runtime endpoint isolation",
    "runtime commissioning",
    "recovery backup",
    "standing autonomy",
)


def strict_absence_contract_gaps(
    readiness: Mapping[str, bool],
    *,
    recovery_drill_enabled: bool,
) -> tuple[str, ...]:
    """Return fixed, secret-free names for strict machine-contract gaps."""
    gaps = [name for name in STRICT_ABSENCE_CONTRACTS if not readiness.get(name, False)]
    if not recovery_drill_enabled:
        gaps.append("recovery drill")
    return tuple(gaps)


def runtime_webhook_isolation_error(
    *,
    alert_url: str | None,
    liveness_url: str | None,
    alert_token: str | None,
    liveness_token: str | None,
) -> str | None:
    """Reject endpoint or credential reuse without returning sensitive values."""
    normalized_alert_url = (alert_url or "").strip()
    normalized_liveness_url = (liveness_url or "").strip()
    if normalized_alert_url and normalized_alert_url == normalized_liveness_url:
        return "runtime alert and liveness webhook URLs must be distinct"
    normalized_alert_token = (alert_token or "").strip()
    normalized_liveness_token = (liveness_token or "").strip()
    if normalized_alert_token and normalized_alert_token == normalized_liveness_token:
        return "runtime alert and liveness bearer tokens must be distinct"
    return None
