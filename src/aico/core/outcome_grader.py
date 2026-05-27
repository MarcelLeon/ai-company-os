"""Outcome grading for verifiable goal briefs."""

from __future__ import annotations

from aico.core.command_messages import short_id_text
from aico.core.goal_brief import GoalBrief
from aico.core.message_rendering import rich_text_message
from aico.core.models import MessageContent, MetadataEntry, Task
from aico.core.project_assignment import AssignmentProfile, ProjectProfile

OUTCOME_GRADER_INTENT = "outcome_grader"
OUTCOME_GRADER_INTENT_KEY = "aico.intent"
OUTCOME_GRADED_TASK_KEY = "aico.graded_task_id"
OUTCOME_GOAL_ID_KEY = "aico.outcome_goal_id"


def outcome_grader_prompt(
    *,
    brief: GoalBrief,
    owner_task: Task,
    owner_output: str,
) -> str:
    output = _trim(owner_output.strip(), limit=5000) or "(no captured output)"
    acceptance = "\n".join(f"- {item}" for item in brief.acceptance_criteria)
    return (
        "AICO Outcome Grader\n"
        f"goal_id: {brief.goal_id}\n"
        f"graded_task_id: {owner_task.task_id}\n"
        f"owner: {owner_task.target_persona}\n"
        f"objective: {brief.objective}\n\n"
        "Acceptance criteria:\n"
        f"{acceptance}\n\n"
        "Owner output:\n"
        f"{output}\n\n"
        "Grade the outcome for the absent boss.\n"
        "Return exactly these sections:\n"
        "1. verdict: pass | partial | fail\n"
        "2. evidence: bullets mapped to acceptance criteria\n"
        "3. gaps: bullets or none\n"
        "4. boss_next_action: one concrete IM command or none\n"
    )


def task_with_outcome_grader_metadata(
    task: Task,
    *,
    graded_task_id: str,
    goal_id: str,
) -> Task:
    metadata = tuple(entry for entry in task.metadata if entry.key not in _OUTCOME_KEYS)
    return task.model_copy(
        update={
            "metadata": (
                *metadata,
                MetadataEntry(key=OUTCOME_GRADER_INTENT_KEY, value=OUTCOME_GRADER_INTENT),
                MetadataEntry(key=OUTCOME_GRADED_TASK_KEY, value=graded_task_id),
                MetadataEntry(key=OUTCOME_GOAL_ID_KEY, value=goal_id),
            )
        }
    )


def outcome_grader_started_message(
    *,
    project: ProjectProfile,
    assignment: AssignmentProfile,
    grader_task: Task,
    graded_task: Task,
    brief: GoalBrief,
) -> MessageContent:
    return rich_text_message(
        "\n".join(
            (
                f"# Outcome grading queued: {short_id_text(grader_task.task_id)}",
                f"project: {project.id} [{project.name}]",
                f"grader: {assignment.role} -> {assignment.agent}",
                f"goal: {brief.goal_id}",
                f"graded_task: {short_id_text(graded_task.task_id)}",
                f"tracking: /task {short_id_text(grader_task.task_id)}",
            )
        )
    )


def outcome_grader_skipped_message(project: ProjectProfile) -> MessageContent:
    return rich_text_message(
        "\n".join(
            (
                f"# Outcome grading skipped for {project.id}",
                "reason: no tester or reviewer is appointed",
                "",
                "Next:",
                "- /appoint <agent> as tester",
            )
        )
    )


def _trim(text: str, *, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: limit - 24]}\n...[trimmed for grader]"


_OUTCOME_KEYS = {
    OUTCOME_GRADER_INTENT_KEY,
    OUTCOME_GRADED_TASK_KEY,
    OUTCOME_GOAL_ID_KEY,
}
