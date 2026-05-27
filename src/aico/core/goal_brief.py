"""Lightweight goal contracts for verifiable project delegation."""

from __future__ import annotations

from dataclasses import dataclass

from aico.core.message_rendering import rich_text_message
from aico.core.models import MessageContent, MetadataEntry, Task, TaskSnapshot
from aico.core.project_assignment import AssignmentProfile, ProjectProfile

GOAL_BRIEF_INTENT = "goal_brief"
GOAL_BRIEF_INTENT_KEY = "aico.intent"
GOAL_BRIEF_ID_KEY = "aico.goal_id"
GOAL_BRIEF_OBJECTIVE_KEY = "aico.goal_objective"
GOAL_BRIEF_ACCEPTANCE_KEY = "aico.goal_acceptance"


@dataclass(frozen=True)
class GoalBrief:
    goal_id: str
    objective: str
    acceptance_criteria: tuple[str, ...]
    verification: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()


def should_suggest_goal_brief(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "验收:",
            "验收：",
            "停止:",
            "停止：",
            "通过/失败",
            "必须给出",
            "acceptance:",
            "done when",
            "stop if",
            "pass/fail",
            "evidence",
        )
    )


def goal_brief_from_text(goal_id: str, text: str) -> GoalBrief:
    sections = _sections(text)
    objective = sections.get("objective", text).strip()
    acceptance = _lines(sections.get("acceptance", ""))
    if not acceptance:
        acceptance = ("The agent reports concrete verification evidence before claiming done.",)
    return GoalBrief(
        goal_id=goal_id,
        objective=objective,
        acceptance_criteria=acceptance,
        verification=_lines(sections.get("verification", "")),
        stop_conditions=_lines(sections.get("stop", "")),
    )


def goal_prompt(brief: GoalBrief) -> str:
    blocks = [
        "AICO Goal Brief",
        f"goal_id: {brief.goal_id}",
        f"objective: {brief.objective}",
        "",
        "Acceptance criteria:",
        *_bullet_lines(brief.acceptance_criteria),
    ]
    if brief.verification:
        blocks.extend(("", "Verification hints:", *_bullet_lines(brief.verification)))
    if brief.stop_conditions:
        blocks.extend(("", "Stop conditions:", *_bullet_lines(brief.stop_conditions)))
    blocks.extend(
        (
            "",
            "Operating rules:",
            "- Treat this as a verifiable delegation, not a casual chat.",
            "- Do not claim done until every acceptance criterion has evidence.",
            "- If a risky action is required, stop at AICO approval and report what is needed.",
            "- Keep scope limited to the objective and stop conditions.",
        )
    )
    return "\n".join(blocks)


def task_with_goal_brief(task: Task, brief: GoalBrief) -> Task:
    metadata = tuple(entry for entry in task.metadata if entry.key not in _GOAL_KEYS)
    return task.model_copy(
        update={
            "metadata": (
                *metadata,
                MetadataEntry(key=GOAL_BRIEF_INTENT_KEY, value=GOAL_BRIEF_INTENT),
                MetadataEntry(key=GOAL_BRIEF_ID_KEY, value=brief.goal_id),
                MetadataEntry(key=GOAL_BRIEF_OBJECTIVE_KEY, value=brief.objective[:200]),
                MetadataEntry(
                    key=GOAL_BRIEF_ACCEPTANCE_KEY,
                    value="; ".join(brief.acceptance_criteria)[:300],
                ),
            )
        }
    )


def goal_started_message(
    brief: GoalBrief,
    project: ProjectProfile,
    assignment: AssignmentProfile,
    *,
    auto_detected: bool = False,
) -> MessageContent:
    prefix = "Verifiable task detected. Goal brief attached." if auto_detected else "Goal queued."
    lines = [
        f"# {prefix} {brief.goal_id}",
        f"project: {project.id} [{project.name}]",
        f"owner: {assignment.role} -> {assignment.agent}",
        f"objective: {brief.objective}",
        "acceptance:",
        *_bullet_lines(brief.acceptance_criteria),
        "",
        f"tracking: /task {brief.goal_id.removeprefix('goal-')}",
    ]
    return rich_text_message("\n".join(lines))


def goal_list_message(snapshots: tuple[TaskSnapshot, ...]) -> MessageContent:
    goal_snapshots = [snapshot for snapshot in snapshots if goal_metadata(snapshot)]
    if not goal_snapshots:
        return MessageContent(text="No recent goal briefs. Use /goal <role> <objective>.")
    lines = ["# Recent goal briefs"]
    for snapshot in goal_snapshots:
        metadata = goal_metadata(snapshot)
        objective = metadata.get(GOAL_BRIEF_OBJECTIVE_KEY) or "-"
        lines.append(
            f"- {metadata.get(GOAL_BRIEF_ID_KEY, short_id_text(snapshot.task_id))}: "
            f"{snapshot.target_persona} [{snapshot.status.value}] {objective}"
        )
    return rich_text_message("\n".join(lines))


def goal_metadata(snapshot: TaskSnapshot) -> dict[str, object]:
    values: dict[str, object] = {entry.key: entry.value for entry in snapshot.metadata}
    if values.get(GOAL_BRIEF_INTENT_KEY) != GOAL_BRIEF_INTENT:
        return {}
    return values


_GOAL_KEYS = {
    GOAL_BRIEF_INTENT_KEY,
    GOAL_BRIEF_ID_KEY,
    GOAL_BRIEF_OBJECTIVE_KEY,
    GOAL_BRIEF_ACCEPTANCE_KEY,
}


def _sections(text: str) -> dict[str, str]:
    normalized = (
        text.replace("验收：", "验收:")
        .replace("验证：", "验证:")
        .replace("停止：", "停止:")
        .strip()
    )
    labels = (
        ("acceptance", ("验收:", "acceptance:", "done when:")),
        ("verification", ("验证:", "verify:", "verification:")),
        ("stop", ("停止:", "stop:", "stop if:")),
    )
    positions: list[tuple[int, str, str]] = []
    lowered = normalized.lower()
    for name, markers in labels:
        for marker in markers:
            index = lowered.find(marker)
            if index >= 0:
                positions.append((index, name, marker))
                break
    if not positions:
        return {"objective": normalized}
    positions.sort(key=lambda item: item[0])
    sections: dict[str, str] = {"objective": normalized[: positions[0][0]].strip(" ,;。")}
    for offset, (start, name, marker) in enumerate(positions):
        content_start = start + len(marker)
        content_end = positions[offset + 1][0] if offset + 1 < len(positions) else len(normalized)
        sections[name] = normalized[content_start:content_end].strip(" ,;。")
    return sections


def _lines(text: str) -> tuple[str, ...]:
    return tuple(
        part.strip(" -•,;。")
        for part in text.replace("；", ";").replace("。", ";").split(";")
        if part.strip(" -•,;。")
    )


def _bullet_lines(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"- {value}" for value in values)


def short_id_text(value: str) -> str:
    return value[:8]
