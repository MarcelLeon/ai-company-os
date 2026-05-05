"""Command handlers that need directory/session/project context."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from aico.channel import IMChannel
from aico.core.agent_directory import AgentDirectory
from aico.core.agent_session import (
    AgentSession,
    InMemoryAgentSessionStore,
    ProviderSessionRef,
)
from aico.core.command_messages import (
    SKILLS_PROMPT,
    TOOLS_PROMPT,
    agent_card_message,
    agent_list_message,
    short_id_text,
)
from aico.core.models import IncomingMessage, MessageContent, Task
from aico.core.project_assignment import ProjectAssignmentDirectory
from aico.core.router import MessageRouter
from aico.core.session_commands import (
    bind_provider_session,
    create_agent_session,
    resolve_session_ref,
    session_scope,
    sessions_message,
    short_session_id,
)
from aico.core.task_bus import TaskBus

ProviderSessionRefFactory = Callable[[AgentSession], ProviderSessionRef | None]
TargetTaskRunner = Callable[[IncomingMessage, Task], Awaitable[None]]


class DirectoryCommandHandler:
    """Handle commands that inspect agents, projects, assignments, or sessions."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        router: MessageRouter,
        task_bus: TaskBus,
        session_store: InMemoryAgentSessionStore,
        agent_directory: AgentDirectory,
        project_directory: ProjectAssignmentDirectory,
        provider_session_factory: ProviderSessionRefFactory | None,
        run_target_task: TargetTaskRunner,
    ) -> None:
        self._channel = channel
        self._router = router
        self._task_bus = task_bus
        self._session_store = session_store
        self._agent_directory = agent_directory
        self._project_directory = project_directory
        self._provider_session_factory = provider_session_factory
        self._run_target_task = run_target_task

    async def handle_agents(self, message: IncomingMessage) -> None:
        await self._channel.send_message(
            message.source,
            agent_list_message(self._agent_directory.list(), self._task_bus.snapshots()),
        )

    async def handle_agent(self, message: IncomingMessage, agent_ref: str) -> None:
        if not agent_ref:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /agent <agent>"),
            )
            return

        card = self._agent_directory.resolve(agent_ref)
        if card is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Agent not found: {agent_ref}"),
            )
            return

        await self._channel.send_message(
            message.source,
            agent_card_message(card, self._task_bus.snapshots()),
        )

    async def handle_sessions(self, message: IncomingMessage) -> None:
        await self._channel.send_message(
            message.source,
            MessageContent(text=sessions_message(self._session_store.list())),
        )

    async def handle_new_session(self, message: IncomingMessage, agent_name: str) -> None:
        agent_parts = agent_name.split()
        if len(agent_parts) != 1:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /new <agent>"),
            )
            return
        agent_name = agent_parts[0]

        session = create_agent_session(self._session_store, self._agent_directory, agent_name)
        provider_ref = (
            self._provider_session_factory(session) if self._provider_session_factory else None
        )
        if provider_ref is not None:
            session = (
                self._session_store.bind_provider_ref(session.session_id, provider_ref) or session
            )
        await self._channel.send_message(
            message.source,
            MessageContent(
                text=(
                    f"Session created: {short_id_text(session.session_id)}\n"
                    f"agent: {session.agent_name}\n"
                    f"Use /use {short_session_id(session.session_id)} to continue with it."
                )
            ),
        )

    async def handle_bind_session(self, message: IncomingMessage, payload: str) -> None:
        _, content = bind_provider_session(
            self._session_store,
            self._agent_directory,
            message,
            payload,
        )
        await self._channel.send_message(message.source, content)

    async def handle_use_session(self, message: IncomingMessage, session_ref: str) -> None:
        project_ref = _project_ref_from_use_payload(session_ref)
        if project_ref is not None:
            await self._handle_use_project(message, project_ref)
            return

        if not session_ref:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /use <session_id>"),
            )
            return

        session, error = resolve_session_ref(self._session_store.list(), session_ref)
        if session is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=error or f"Session not found: {session_ref}"),
            )
            return

        self._session_store.set_active(session_scope(message), session.session_id)
        await self._channel.send_message(
            message.source,
            MessageContent(
                text=(
                    f"Session active: {short_session_id(session.session_id)} [{session.agent_name}]"
                )
            ),
        )

    async def handle_provider_introspection(
        self,
        message: IncomingMessage,
        agent_ref: str,
        *,
        prompt: str,
    ) -> None:
        if not agent_ref:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /skills <agent> or /tools <agent>"),
            )
            return
        card = self._agent_directory.resolve(agent_ref)
        target_persona = agent_ref if card is None else card.name
        task = self._router.to_task_for_target(message, target_persona, prompt)
        await self._run_target_task(message, task)

    async def handle_skills(self, message: IncomingMessage, agent_ref: str) -> None:
        await self.handle_provider_introspection(message, agent_ref, prompt=SKILLS_PROMPT)

    async def handle_tools(self, message: IncomingMessage, agent_ref: str) -> None:
        await self.handle_provider_introspection(message, agent_ref, prompt=TOOLS_PROMPT)

    async def _handle_use_project(self, message: IncomingMessage, project_ref: str) -> None:
        project = self._project_directory.set_active_project(
            session_scope(message),
            project_ref,
        )
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Project not found: {project_ref}"),
            )
            return
        assignment = self._project_directory.default_assignment(project.id)
        assignment_text = "-" if assignment is None else assignment.seat
        await self._channel.send_message(
            message.source,
            MessageContent(
                text=(
                    f"Project active: {project.id} [{project.name}]\n"
                    f"default assignment: {assignment_text}"
                )
            ),
        )


def _project_ref_from_use_payload(payload: str) -> str | None:
    parts = payload.split()
    if len(parts) == 2 and parts[0].lower() == "project":
        return parts[1]
    return None
