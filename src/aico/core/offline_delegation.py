"""Phase 8 offline delegation command support."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from aico.channel import IMChannel
from aico.core.agent_session import AgentSession
from aico.core.command_messages import short_id_text
from aico.core.models import IncomingMessage, MessageContent, MetadataEntry, Task
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectAssignmentDirectory,
    ProjectProfile,
)
from aico.core.session_commands import session_scope

OFFLINE_DELEGATION_INTENT = "offline_delegation"
OFFLINE_DELEGATION_INTENT_KEY = "aico.intent"
OFFLINE_DELEGATION_ID_KEY = "aico.offline_delegation_id"
OFFLINE_DELEGATION_GOAL_KEY = "aico.offline_goal"

ProjectTaskFactory = Callable[
    [IncomingMessage, str, AssignmentProfile, str],
    tuple[Task, AgentSession | None],
]
DelegatedTaskRunner = Callable[[IncomingMessage, Task, AgentSession | None], Awaitable[None]]


@dataclass(frozen=True)
class OfflineDelegationRecord:
    delegation_id: str
    project_id: str
    project_name: str
    role: str
    agent: str
    task_id: str
    goal: str


class OfflineDelegationCommandHandler:
    """Create and list project-scoped offline delegation work orders."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        project_directory: ProjectAssignmentDirectory,
        task_for_assignment: ProjectTaskFactory,
        run_delegated_task: DelegatedTaskRunner,
        max_records_per_scope: int = 5,
    ) -> None:
        self._channel = channel
        self._project_directory = project_directory
        self._task_for_assignment = task_for_assignment
        self._run_delegated_task = run_delegated_task
        self._max_records_per_scope = max_records_per_scope
        self._records_by_scope: dict[str, list[OfflineDelegationRecord]] = {}

    async def handle_overnight(self, message: IncomingMessage, payload: str) -> None:
        goal = payload.strip()
        if not goal:
            await self._send_current_delegations(message)
            return

        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="No active project. Use /project <project> first."),
            )
            return
        assignment = self._project_directory.default_assignment(project.id)
        if assignment is None:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=(
                        f"No appointed lead for {project.id}. Use /appoint <agent> as <role> first."
                    )
                ),
            )
            return

        task, session = self._task_for_assignment(
            message,
            project.id,
            assignment,
            offline_delegation_prompt(project, assignment, goal),
        )
        delegation_id = f"night-{short_id_text(task.task_id)}"
        task = _task_with_offline_metadata(task, delegation_id, goal)
        record = OfflineDelegationRecord(
            delegation_id=delegation_id,
            project_id=project.id,
            project_name=project.name,
            role=assignment.role,
            agent=assignment.agent,
            task_id=task.task_id,
            goal=goal,
        )
        self._remember_record(session_scope(message), record)
        await self._channel.send_message(
            message.source,
            offline_delegation_started_message(record),
        )
        await self._run_delegated_task(message, task, session)

    async def _send_current_delegations(self, message: IncomingMessage) -> None:
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="No active project. Use /project <project> first."),
            )
            return
        records = [
            record
            for record in self._records_by_scope.get(session_scope(message), [])
            if record.project_id == project.id
        ]
        if not records:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=f"No overnight delegations for {project.id}. Use /overnight <goal>."
                ),
            )
            return
        lines = [f"Overnight delegations for {project.id}:"]
        lines.extend(
            f"• {record.delegation_id}: {record.role} -> {record.agent} "
            f"({short_id_text(record.task_id)})"
            for record in records
        )
        lines.append("")
        lines.append("Morning:")
        lines.append(f"- /daily {project.id}")
        lines.append("- /tasks")
        await self._channel.send_message(message.source, MessageContent(text="\n".join(lines)))

    def _remember_record(self, scope_id: str, record: OfflineDelegationRecord) -> None:
        records = [*self._records_by_scope.get(scope_id, ()), record]
        self._records_by_scope[scope_id] = records[-self._max_records_per_scope :]


def offline_delegation_prompt(
    project: ProjectProfile,
    assignment: AssignmentProfile,
    goal: str,
) -> str:
    return (
        "Offline delegation request for the project lead.\n"
        f"Project: {project.id} [{project.name}]\n"
        f"Lead role: {assignment.role}\n"
        f"Boss goal: {goal}\n\n"
        "Operating rules:\n"
        "- Work in small auditable steps and keep the project north star in mind.\n"
        "- Stay within AICO approval policy. If blocked by approval, missing credentials, "
        "or unclear scope, stop and report the blocker.\n"
        "- Leave a morning handoff with: done, blocked, risks, and next 3 actions.\n"
        "- Prefer project/team context and shared memory already provided above."
    )


def offline_delegation_started_message(record: OfflineDelegationRecord) -> MessageContent:
    text = (
        f"Overnight delegation queued: {record.delegation_id}\n"
        f"project: {record.project_id} [{record.project_name}]\n"
        f"lead: {record.role} -> {record.agent}\n"
        f"goal: {record.goal}\n"
        f"tracking: /task {short_id_text(record.task_id)}\n\n"
        "Morning:\n"
        f"- /daily {record.project_id}\n"
        "- /tasks\n\n"
        "Guardrails:\n"
        "- risky work still pauses for /approve\n"
        "- the lead should report done, blocked, risks, and next actions"
    )
    return MessageContent(text=text)


def _task_with_offline_metadata(task: Task, delegation_id: str, goal: str) -> Task:
    return task.model_copy(
        update={
            "metadata": (
                *task.metadata,
                MetadataEntry(key=OFFLINE_DELEGATION_INTENT_KEY, value=OFFLINE_DELEGATION_INTENT),
                MetadataEntry(key=OFFLINE_DELEGATION_ID_KEY, value=delegation_id),
                MetadataEntry(key=OFFLINE_DELEGATION_GOAL_KEY, value=goal[:200]),
            )
        }
    )
