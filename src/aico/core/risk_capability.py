"""Map task risk levels to adapter capabilities."""

from __future__ import annotations

from aico.adapter import AIAdapter
from aico.core.models import Capability, RiskAssessment, RiskLevel


def unsupported_risk_reason(adapter: AIAdapter, risk: RiskAssessment) -> str | None:
    capabilities = adapter.capabilities()
    if risk.risk_level is RiskLevel.READ_ONLY:
        return None
    if risk.risk_level is RiskLevel.WRITE_FILES and Capability.CODE_EDIT in capabilities:
        return None
    if risk.risk_level is RiskLevel.SHELL_EXEC and Capability.SHELL_EXEC in capabilities:
        return None
    if risk.risk_level is RiskLevel.DESTRUCTIVE and capabilities.intersection(
        {Capability.CODE_EDIT, Capability.SHELL_EXEC}
    ):
        return None
    return f"adapter {adapter.name} cannot handle {risk.risk_level.value} tasks; use /claude"
