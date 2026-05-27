"""Command handling for lightweight verifiable goal briefs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from aico.channel import IMChannel
from aico.core.agent_session import AgentSession
from aico.core.goal_brief import (
    GoalBrief,
    goal_brief_from_text,
    goal_list_message,
    goal_prompt,
    goal_started_message,
    should_suggest_goal_brief,
    task_with_goal_brief,
)
from aico.core.models import IncomingMessage, MessageContent, Task, TaskSnapshot, TaskStatus
from aico.core.outcome_grader import (
    outcome_grader_prompt,
    outcome_grader_skipped_message,
    outcome_grader_started_message,
    task_with_outcome_grader_metadata,
)
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectAssignmentDirectory,
    ProjectProfile,
)
from aico.core.session_commands import session_scope
from aico.core.task_bus import TaskBus

ProjectTaskFactory = Callable[
    [IncomingMessage, str, AssignmentProfile, str],
    tuple[Task, AgentSession | None],
]
GoalTaskRunner = Callable[[IncomingMessage, Task, AgentSession | None], Awaitable[str]]


class GoalBriefCommandHandler:
    """Attach verifiable goal briefs without owning long-running execution loops."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        project_directory: ProjectAssignmentDirectory,
        task_bus: TaskBus,
        task_for_assignment: ProjectTaskFactory,
        run_goal_task: GoalTaskRunner,
    ) -> None:
        self._channel = channel
        self._project_directory = project_directory
        self._task_bus = task_bus
        self._task_for_assignment = task_for_assignment
        self._run_goal_task = run_goal_task

    async def handle_goal(self, message: IncomingMessage, payload: str) -> None:
        if not payload:
            await self._channel.send_message(
                message.source,
                goal_list_message(self._task_bus.task_snapshots(limit=None)),
            )
            return
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="No active project. Use /project <project> first."),
            )
            return
        role_ref, objective = self._goal_role_and_objective(project.id, payload)
        if not objective.strip():
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /goal [role] <objective>"),
            )
            return
        assignment = self._project_directory.appointment_for_role(project.id, role_ref)
        if assignment is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Role not appointed in {project.id}: {role_ref}"),
            )
            return
        await self._start_goal(message, project, assignment, objective, auto_detected=False)

    async def maybe_run_auto_goal(
        self,
        message: IncomingMessage,
        *,
        project: ProjectProfile,
        assignment: AssignmentProfile,
        payload: str,
    ) -> bool:
        if not should_suggest_goal_brief(payload):
            return False
        await self._start_goal(message, project, assignment, payload, auto_detected=True)
        return True

    async def _start_goal(
        self,
        message: IncomingMessage,
        project: ProjectProfile,
        assignment: AssignmentProfile,
        objective: str,
        *,
        auto_detected: bool,
    ) -> None:
        task, session, brief = self._goal_task_for_assignment(
            message,
            project.id,
            assignment,
            objective,
        )
        await self._channel.send_message(
            message.source,
            goal_started_message(brief, project, assignment, auto_detected=auto_detected),
        )
        owner_output = await self._run_goal_task(message, task, session)
        await self._maybe_grade_outcome(
            message,
            project=project,
            owner_assignment=assignment,
            owner_task=task,
            brief=brief,
            owner_output=owner_output,
        )

    async def _maybe_grade_outcome(
        self,
        message: IncomingMessage,
        *,
        project: ProjectProfile,
        owner_assignment: AssignmentProfile,
        owner_task: Task,
        brief: GoalBrief,
        owner_output: str,
    ) -> None:
        snapshot = self._task_bus.task_snapshot(owner_task.task_id)
        if not isinstance(snapshot, TaskSnapshot) or snapshot.status is not TaskStatus.DONE:
            return
        assignment = self._outcome_grader_assignment(project.id, owner_assignment.role)
        if assignment is None:
            await self._channel.send_message(
                message.source,
                outcome_grader_skipped_message(project),
            )
            return
        grader_task, session = self._task_for_assignment(
            message,
            project.id,
            assignment,
            outcome_grader_prompt(
                brief=brief,
                owner_task=owner_task,
                owner_output=owner_output,
            ),
        )
        grader_task = task_with_outcome_grader_metadata(
            grader_task,
            graded_task_id=owner_task.task_id,
            goal_id=brief.goal_id,
        )
        await self._channel.send_message(
            message.source,
            outcome_grader_started_message(
                project=project,
                assignment=assignment,
                grader_task=grader_task,
                graded_task=owner_task,
                brief=brief,
            ),
        )
        await self._run_goal_task(message, grader_task, session)

    def _outcome_grader_assignment(
        self,
        project_id: str,
        owner_role: str,
    ) -> AssignmentProfile | None:
        for role_ref in ("tester", "reviewer"):
            if role_ref == owner_role:
                continue
            assignment = self._project_directory.appointment_for_role(project_id, role_ref)
            if assignment is not None:
                return assignment
        return None

    def _goal_role_and_objective(self, project_id: str, payload: str) -> tuple[str, str]:
        role_ref, separator, objective = payload.partition(" ")
        if separator and self._project_directory.appointment_for_role(project_id, role_ref):
            return role_ref, objective.strip()
        assignment = self._project_directory.default_assignment(project_id)
        return (role_ref, objective.strip()) if assignment is None else (assignment.role, payload)

    def _goal_task_for_assignment(
        self,
        message: IncomingMessage,
        project_id: str,
        assignment: AssignmentProfile,
        objective: str,
    ) -> tuple[Task, AgentSession | None, GoalBrief]:
        pending_brief = goal_brief_from_text("goal-pending", objective)
        task, session = self._task_for_assignment(
            message,
            project_id,
            assignment,
            goal_prompt(pending_brief),
        )
        brief = goal_brief_from_text(f"goal-{task.task_id[:8]}", objective)
        task = task.model_copy(
            update={"payload": task.payload.replace("goal-pending", brief.goal_id)}
        )
        return task_with_goal_brief(task, brief), session, brief
