"""Task construction helpers for Orchestrator."""

from __future__ import annotations

from collections.abc import Callable

from aico.core.agent_directory import AgentDirectory
from aico.core.agent_session import (
    AgentSession,
    InMemoryAgentSessionStore,
    ProviderSessionMode,
    ProviderSessionRef,
    provider_session_from_task,
    task_with_provider_session,
)
from aico.core.memory import MemoryPacket, MemoryRetriever, MemoryScope, MemoryStore
from aico.core.models import IncomingMessage, Task
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectAssignmentDirectory,
    task_with_assignment_context,
)
from aico.core.prompt_stack import render_appointment_prompt
from aico.core.router import MessageRouter
from aico.core.session_commands import has_explicit_task_target, session_scope

ProviderSessionRefFactory = Callable[[AgentSession], ProviderSessionRef | None]


class OrchestratorTaskFactory:
    """Build routed tasks while keeping project/session details out of Orchestrator."""

    def __init__(
        self,
        *,
        router: MessageRouter,
        session_store: InMemoryAgentSessionStore,
        agent_directory: AgentDirectory,
        project_directory: ProjectAssignmentDirectory,
        memory_store: MemoryStore | None,
        provider_session_factory: ProviderSessionRefFactory | None,
    ) -> None:
        self._router = router
        self._session_store = session_store
        self._agent_directory = agent_directory
        self._project_directory = project_directory
        self._memory_store = memory_store
        self._provider_session_factory = provider_session_factory
        self._assignment_sessions: dict[str, str] = {}

    def task_for_message(self, message: IncomingMessage) -> tuple[Task, AgentSession | None]:
        if has_explicit_task_target(message):
            return self._router.to_task(message), None

        project = self._project_directory.active_project(session_scope(message))
        if project is not None:
            assignment = self._project_directory.default_assignment(project.id)
            if assignment is not None:
                return self.task_for_assignment(message, project.id, assignment)

        session = self._session_store.active(session_scope(message))
        if session is None:
            return self._router.to_task(message), None

        task = self._router.to_task_for_target(
            message,
            session.agent_name,
            message.content.text.strip(),
        )
        if session.provider_ref is not None:
            mode = (
                ProviderSessionMode.RESUME
                if session.provider_ref.initialized
                else ProviderSessionMode.NEW
            )
            task = task_with_provider_session(task, session.provider_ref, mode)
        return task, session

    def task_for_assignment(
        self,
        message: IncomingMessage,
        project_id: str,
        assignment: AssignmentProfile,
        payload: str | None = None,
        *,
        memory_packet: MemoryPacket | None = None,
    ) -> tuple[Task, AgentSession | None]:
        project = self._project_directory.project(project_id)
        if project is None:
            return self._router.to_task(message), None
        card = self._agent_directory.resolve(assignment.agent)
        target_agent = assignment.agent if card is None else card.name
        task = self._router.to_task_for_target(
            message,
            target_agent,
            message.content.text.strip() if payload is None else payload,
        )
        task = task.model_copy(
            update={
                "payload": render_appointment_prompt(
                    task=task,
                    agent=self._project_directory.agent(assignment.agent),
                    role=self._project_directory.role(assignment.role),
                    project=project,
                    project_role=self._project_directory.project_role(
                        project.id,
                        assignment.role,
                    ),
                    appointment=assignment,
                    is_project_lead=_is_same_assignment(
                        assignment,
                        self._project_directory.default_assignment(project.id),
                    ),
                    memory_packet=memory_packet
                    if memory_packet is not None
                    else self._memory_packet_for_assignment(
                        boss_id=message.sender_id,
                        project_id=project.id,
                        assignment=assignment,
                        query=task.payload,
                    ),
                )
            }
        )
        task = task_with_assignment_context(task, project=project, assignment=assignment)
        session = self._ensure_assignment_session(assignment, target_agent, project.repo)
        if session.provider_ref is not None:
            mode = (
                ProviderSessionMode.RESUME
                if session.provider_ref.initialized
                else ProviderSessionMode.NEW
            )
            task = task_with_provider_session(task, session.provider_ref, mode)
        return task, session

    def task_for_assignment_with_memory(
        self,
        message: IncomingMessage,
        project_id: str,
        assignment: AssignmentProfile,
        payload: str,
        memory_packet: MemoryPacket | None,
    ) -> tuple[Task, AgentSession | None]:
        return self.task_for_assignment(
            message,
            project_id,
            assignment,
            payload=payload,
            memory_packet=memory_packet,
        )

    def mark_provider_initialized(self, session_id: str, task: Task) -> None:
        provider_session = provider_session_from_task(task)
        if provider_session is None or provider_session.mode is not ProviderSessionMode.NEW:
            return
        self._session_store.mark_provider_initialized(session_id)

    def _memory_packet_for_assignment(
        self,
        *,
        boss_id: str,
        project_id: str,
        assignment: AssignmentProfile,
        query: str,
    ) -> MemoryPacket | None:
        if self._memory_store is None:
            return None
        scopes = (
            MemoryScope.boss(boss_id),
            MemoryScope.project(project_id),
            MemoryScope.team(project_id, "default"),
            MemoryScope.role(project_id, "default", assignment.role),
            MemoryScope.agent(project_id, "default", assignment.agent),
        )
        packet = MemoryRetriever(self._memory_store).retrieve_packet(scopes=scopes, query=query)
        return packet if packet.items else None

    def _ensure_assignment_session(
        self,
        assignment: AssignmentProfile,
        target_agent: str,
        project_workspace: str,
    ) -> AgentSession:
        session_id = self._assignment_sessions.get(assignment.seat)
        session = None if session_id is None else self._session_store.get(session_id)
        card = self._agent_directory.resolve(target_agent)
        adapter_name = assignment.agent if card is None else card.adapter_name
        if (
            session is not None
            and session.agent_name == target_agent
            and session.adapter_name == adapter_name
        ):
            return session

        if session is not None:
            self._session_store.close(session.session_id)
        session = self._session_store.create(
            agent_name=target_agent,
            adapter_name=adapter_name,
            workspace=assignment.workspace or project_workspace,
        )
        provider_ref = (
            self._provider_session_factory(session) if self._provider_session_factory else None
        )
        if provider_ref is not None:
            session = (
                self._session_store.bind_provider_ref(session.session_id, provider_ref) or session
            )
        self._assignment_sessions[assignment.seat] = session.session_id
        return session


def _is_same_assignment(
    left: AssignmentProfile,
    right: AssignmentProfile | None,
) -> bool:
    return right is not None and left.seat == right.seat
