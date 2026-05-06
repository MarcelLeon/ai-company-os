"""Command handlers for project-office operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from aico.channel import IMChannel
from aico.core.agent_directory import AgentDirectory
from aico.core.models import IncomingMessage, MessageContent
from aico.core.project_assignment import ProjectAssignmentDirectory, ProjectProfile
from aico.core.project_messages import (
    appointment_created_message,
    appointment_removed_message,
    assignment_message,
    assignments_message,
    default_role_message,
    project_office_message,
    projects_message,
    roles_message,
    team_message,
    who_message,
)
from aico.core.project_role_commands import ProjectRoleCommandHandler, RoleProposalRunner
from aico.core.project_status_commands import ProjectStatusCommandHandler, ProjectSummaryRunner
from aico.core.session_commands import session_scope
from aico.core.task_bus import TaskBus

RoleTaskRunner = Callable[[IncomingMessage, str, str], Awaitable[None]]


class ProjectCommandHandler:
    """Handle project-office, role, and assignment commands."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        task_bus: TaskBus,
        agent_directory: AgentDirectory,
        project_directory: ProjectAssignmentDirectory,
        run_role_task: RoleTaskRunner,
        propose_role: RoleProposalRunner,
        summarize_project: ProjectSummaryRunner | None = None,
    ) -> None:
        self._channel = channel
        self._agent_directory = agent_directory
        self._project_directory = project_directory
        self._run_role_task = run_role_task
        self._status_commands = ProjectStatusCommandHandler(
            channel=channel,
            task_bus=task_bus,
            project_directory=project_directory,
            summarize_project=summarize_project,
        )
        self._role_commands = ProjectRoleCommandHandler(
            channel=channel,
            project_directory=project_directory,
            propose_role=propose_role,
        )

    async def handle_projects(self, message: IncomingMessage) -> None:
        await self._channel.send_message(
            message.source,
            projects_message(
                self._project_directory.projects(),
                self._project_directory.active_project(session_scope(message)),
            ),
        )

    async def handle_project(self, message: IncomingMessage, project_id: str) -> None:
        if not project_id:
            project = self._project_directory.active_project(session_scope(message))
            if project is None:
                await self._channel.send_message(
                    message.source,
                    MessageContent(text="No active project. Use /project <project> first."),
                )
                return
            await self._send_project_office(message, project)
            return
        project = self._project_directory.set_active_project(session_scope(message), project_id)
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Project not found: {project_id}"),
            )
            return
        await self._send_project_office(message, project)

    async def _send_project_office(
        self,
        message: IncomingMessage,
        project: ProjectProfile,
    ) -> None:
        await self._channel.send_message(
            message.source,
            project_office_message(
                project,
                self._project_directory.appointments(project.id),
                self._project_directory.default_assignment(project.id),
            ),
        )

    async def handle_brief(self, message: IncomingMessage, project_id: str | None) -> None:
        await self._status_commands.handle_brief(message, project_id)

    async def handle_risks(self, message: IncomingMessage, project_id: str | None) -> None:
        await self._status_commands.handle_risks(message, project_id)

    async def handle_blockers(self, message: IncomingMessage, project_id: str | None) -> None:
        await self._status_commands.handle_blockers(message, project_id)

    async def handle_next(self, message: IncomingMessage, project_id: str | None) -> None:
        await self._status_commands.handle_next(message, project_id)

    async def handle_roles(self, message: IncomingMessage, project_id: str | None) -> None:
        project = self._project_from_optional_ref(message, project_id)
        if project is None:
            await self._send_no_active_project(message)
            return
        await self._channel.send_message(
            message.source,
            roles_message(
                project,
                self._project_directory.roles(project.id),
                self._project_directory.appointments(project.id),
            ),
        )

    async def handle_role(self, message: IncomingMessage, payload: str) -> None:
        await self._role_commands.handle_role(message, payload)

    async def handle_daily(self, message: IncomingMessage, project_id: str | None) -> None:
        await self._status_commands.handle_daily(message, project_id)

    async def handle_weekly(self, message: IncomingMessage, project_id: str | None) -> None:
        await self._status_commands.handle_weekly(message, project_id)

    async def handle_team(self, message: IncomingMessage, project_id: str | None) -> None:
        project = self._project_from_optional_ref(message, project_id)
        if project is None:
            await self._send_no_active_project(message)
            return
        await self._channel.send_message(
            message.source,
            team_message(
                project,
                self._project_directory.appointments(project.id),
                self._project_directory.default_assignment(project.id),
            ),
        )

    async def handle_who(self, message: IncomingMessage, role_ref: str) -> None:
        if not role_ref:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /who <role>"),
            )
            return
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._send_no_active_project(message)
            return
        appointment = self._project_directory.appointment_for_role(project.id, role_ref)
        if appointment is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Role not appointed in {project.id}: {role_ref}"),
            )
            return
        await self._channel.send_message(
            message.source,
            who_message(
                project,
                appointment,
                self._project_directory.agent(appointment.agent),
                self._project_directory.role(appointment.role),
            ),
        )

    async def handle_appoint(self, message: IncomingMessage, payload: str) -> None:
        agent_ref, role_ref, permissions = _appoint_parts(payload)
        if agent_ref is None or role_ref is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /appoint <agent> as <role> [permissions]"),
            )
            return
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._send_no_active_project(message)
            return
        if self._agent_directory.resolve(agent_ref) is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Agent not found: {agent_ref}"),
            )
            return
        appointment = self._project_directory.upsert_appointment(
            project_id=project.id,
            agent_id=agent_ref,
            role_id=role_ref,
            permissions=permissions,
        )
        if appointment is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Cannot appoint {agent_ref} as {role_ref}"),
            )
            return
        await self._channel.send_message(
            message.source,
            appointment_created_message(
                project,
                appointment,
                self._project_directory.agent(appointment.agent),
                self._project_directory.role(appointment.role),
            ),
        )

    async def handle_unappoint(self, message: IncomingMessage, role_ref: str) -> None:
        if not role_ref:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /unappoint <role>"),
            )
            return
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._send_no_active_project(message)
            return
        appointment = self._project_directory.remove_appointment_for_role(project.id, role_ref)
        if appointment is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Role not appointed in {project.id}: {role_ref}"),
            )
            return
        await self._channel.send_message(
            message.source,
            appointment_removed_message(project, appointment),
        )

    async def handle_ask(self, message: IncomingMessage, payload: str) -> None:
        role_ref, _, task_text = payload.partition(" ")
        if not role_ref or not task_text.strip():
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /ask <role> <task>"),
            )
            return
        await self._run_role_task(message, role_ref, task_text.strip())

    async def handle_default(self, message: IncomingMessage, role_ref: str) -> None:
        if not role_ref:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /default <role>"),
            )
            return
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._send_no_active_project(message)
            return
        appointment = self._project_directory.set_default_role(project.id, role_ref)
        if appointment is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Role not appointed in {project.id}: {role_ref}"),
            )
            return
        await self._channel.send_message(
            message.source,
            default_role_message(project, appointment),
        )

    async def handle_assignments(
        self,
        message: IncomingMessage,
        project_id: str | None,
    ) -> None:
        project_id = project_id or None
        if project_id is not None and self._project_directory.project(project_id) is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Project not found: {project_id}"),
            )
            return
        await self._channel.send_message(
            message.source,
            assignments_message(
                self._project_directory.assignments(project_id),
                project_id=project_id,
            ),
        )

    async def handle_assignment(self, message: IncomingMessage, seat: str) -> None:
        if not seat:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /assignment <seat>"),
            )
            return
        assignment = self._project_directory.assignment(seat)
        if assignment is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Assignment not found: {seat}"),
            )
            return
        await self._channel.send_message(
            message.source,
            assignment_message(
                assignment,
                self._project_directory.agent(assignment.agent),
                self._project_directory.project(assignment.project),
            ),
        )

    async def _send_no_active_project(self, message: IncomingMessage) -> None:
        await self._channel.send_message(
            message.source,
            MessageContent(text="No active project. Use /project <project> first."),
        )

    def _project_from_optional_ref(
        self,
        message: IncomingMessage,
        project_ref: str | None,
    ) -> ProjectProfile | None:
        if project_ref:
            return self._project_directory.project(project_ref)
        return self._project_directory.active_project(session_scope(message))


def _appoint_parts(payload: str) -> tuple[str | None, str | None, tuple[str, ...]]:
    parts = payload.split()
    if len(parts) < 3 or parts[1].lower() != "as":
        return None, None, ()
    permissions = tuple(_permission_tokens(parts[3:]))
    return parts[0], parts[2], permissions


def _permission_tokens(tokens: list[str]) -> tuple[str, ...]:
    if not tokens:
        return ()
    if len(tokens) == 1 and tokens[0].lower() in {"readonly", "read-only"}:
        return ("read_repo", "read_docs")
    return tuple(token.strip(",") for token in tokens if token.strip(","))
