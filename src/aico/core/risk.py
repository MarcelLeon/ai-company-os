"""Text risk assessment for remote task approval gates."""

from __future__ import annotations

from aico.core.models import RiskAssessment, RiskLevel, Task


class TextRiskAssessor:
    """Classify task text into the smallest useful Phase 4 risk levels."""

    def assess(self, task: Task) -> RiskAssessment:
        text = task.payload.lower()
        reasons: list[str] = []
        level = RiskLevel.READ_ONLY

        if _contains_any(text, _WRITE_MARKERS):
            level = RiskLevel.WRITE_FILES
            reasons.append("mentions file or code changes")
        if _contains_any(text, _SHELL_MARKERS):
            level = RiskLevel.SHELL_EXEC
            reasons.append("mentions shell or command execution")
        if _contains_any(text, _DESTRUCTIVE_MARKERS):
            level = RiskLevel.DESTRUCTIVE
            reasons.append("mentions destructive operations")

        return RiskAssessment(
            risk_level=level,
            requires_approval=level is not RiskLevel.READ_ONLY,
            reasons=tuple(reasons),
        )


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


_WRITE_MARKERS = (
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
)

_SHELL_MARKERS = (
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
)

_DESTRUCTIVE_MARKERS = (
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
)
