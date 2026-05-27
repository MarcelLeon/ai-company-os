"""Text risk assessment for remote task approval gates."""

from __future__ import annotations

from dataclasses import dataclass

from aico.core.lead_decision import LEAD_DECISION_INTENT, LEAD_DECISION_INTENT_KEY
from aico.core.models import RiskAssessment, RiskLevel, Task
from aico.core.outcome_grader import OUTCOME_GRADER_INTENT, OUTCOME_GRADER_INTENT_KEY
from aico.core.project_summary import PROJECT_SUMMARY_INTENT, PROJECT_SUMMARY_INTENT_KEY
from aico.core.role_proposal import ROLE_PROPOSAL_INTENT, ROLE_PROPOSAL_INTENT_KEY


class TextRiskAssessor:
    """Classify task text into the smallest useful Phase 4 risk levels."""

    def assess(self, task: Task) -> RiskAssessment:
        if _is_internal_read_only_task(task):
            return RiskAssessment(risk_level=RiskLevel.READ_ONLY)

        text = _risk_text(task.payload).lower()
        reasons: list[str] = []
        level = RiskLevel.READ_ONLY

        for rule in RISK_RULES:
            if _contains_any(text, rule.markers):
                level = rule.risk_level
                reasons.append(rule.reason)

        return RiskAssessment(
            risk_level=level,
            requires_approval=level is not RiskLevel.READ_ONLY,
            reasons=tuple(reasons),
        )


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _risk_text(payload: str) -> str:
    _, separator, current_task = payload.rpartition("Current task:")
    if separator:
        return current_task
    return payload


def _is_internal_read_only_task(task: Task) -> bool:
    return any(
        _is_intent(entry.key, entry.value, ROLE_PROPOSAL_INTENT)
        or _is_intent(entry.key, entry.value, PROJECT_SUMMARY_INTENT)
        or _is_intent(entry.key, entry.value, LEAD_DECISION_INTENT)
        or _is_intent(entry.key, entry.value, OUTCOME_GRADER_INTENT)
        for entry in task.metadata
    )


def _is_intent(key: str, value: object, intent: str) -> bool:
    return (
        key
        in {
            ROLE_PROPOSAL_INTENT_KEY,
            PROJECT_SUMMARY_INTENT_KEY,
            LEAD_DECISION_INTENT_KEY,
            OUTCOME_GRADER_INTENT_KEY,
        }
        and value == intent
    )


@dataclass(frozen=True)
class RiskRule:
    risk_level: RiskLevel
    reason: str
    markers: tuple[str, ...]


RISK_RULES = (
    RiskRule(
        RiskLevel.WRITE_FILES,
        "mentions file or code changes",
        (
            "edit ",
            "modify ",
            "change ",
            "write ",
            "create ",
            "update ",
            "patch ",
            "refactor ",
            "修改",
            "写入",
            "创建",
            "更新",
            "重构",
        ),
    ),
    RiskRule(
        RiskLevel.SHELL_EXEC,
        "mentions shell or command execution",
        (
            "run ",
            "execute ",
            "shell",
            "command",
            "pytest",
            "mypy",
            "ruff",
            "npm ",
            "uv ",
            "git ",
            "执行",
            "命令",
        ),
    ),
    RiskRule(
        RiskLevel.DESTRUCTIVE,
        "mentions destructive operations",
        (
            "rm -rf",
            "delete ",
            "remove ",
            "drop ",
            "overwrite",
            "reset --hard",
            "git push",
            "删除",
            "移除",
            "覆盖",
        ),
    ),
)
