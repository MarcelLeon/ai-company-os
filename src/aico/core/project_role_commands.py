"""Role proposal command handlers for project-office operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from aico.channel import IMChannel
from aico.core.models import IncomingMessage, MessageContent
from aico.core.project_assignment import ProjectAssignmentDirectory, ProjectProfile, RoleProfile
from aico.core.project_messages import role_added_message, role_proposal_message
from aico.core.session_commands import session_scope

RoleProposalRunner = Callable[[IncomingMessage, ProjectProfile, str], Awaitable[RoleProfile | str]]


class ProjectRoleCommandHandler:
    """Handle project role proposal and confirmation commands."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        project_directory: ProjectAssignmentDirectory,
        propose_role: RoleProposalRunner,
    ) -> None:
        self._channel = channel
        self._project_directory = project_directory
        self._propose_role = propose_role
        self._role_drafts: dict[str, tuple[str, RoleProfile]] = {}

    async def handle_role(self, message: IncomingMessage, payload: str) -> None:
        action, _, rest = payload.partition(" ")
        if action == "propose":
            await self._handle_role_propose(message, rest.strip())
        elif action == "confirm":
            await self._handle_role_confirm(message)
        elif action in {"discard", "cancel"}:
            await self._handle_role_discard(message)
        else:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /role propose <need>, /role confirm, or /role discard"),
            )

    async def _handle_role_propose(self, message: IncomingMessage, request: str) -> None:
        if not request:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /role propose <need>"),
            )
            return
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._send_no_active_project(message)
            return
        await self._channel.send_message(
            message.source,
            MessageContent(text=f"Drafting role proposal for {project.id}..."),
        )
        proposal = await self._propose_role(message, project, request)
        if isinstance(proposal, str):
            await self._channel.send_message(message.source, MessageContent(text=proposal))
            return
        self._role_drafts[session_scope(message)] = (project.id, proposal)
        await self._channel.send_message(
            message.source,
            role_proposal_message(project, proposal),
        )

    async def _handle_role_confirm(self, message: IncomingMessage) -> None:
        scope = session_scope(message)
        draft = self._role_drafts.get(scope)
        if draft is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="No pending role proposal. Use /role propose <need> first."),
            )
            return
        project_id, role = draft
        project = self._project_directory.project(project_id)
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Project not found: {project_id}"),
            )
            return
        added = self._project_directory.add_project_role(project.id, role)
        if added is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Role already exists in {project.id}: {role.id}"),
            )
            return
        self._role_drafts.pop(scope, None)
        await self._channel.send_message(message.source, role_added_message(project, added))

    async def _handle_role_discard(self, message: IncomingMessage) -> None:
        self._role_drafts.pop(session_scope(message), None)
        await self._channel.send_message(
            message.source,
            MessageContent(text="Role proposal discarded"),
        )

    async def _send_no_active_project(self, message: IncomingMessage) -> None:
        await self._channel.send_message(
            message.source,
            MessageContent(text="No active project. Use /project <project> first."),
        )
