"""Phase 1 orchestration loop for one channel and one task bus."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from aico.channel import IMChannel
from aico.core.agent_directory import AgentDirectory
from aico.core.agent_session import (
    AgentSession,
    InMemoryAgentSessionStore,
    ProviderSessionMode,
    ProviderSessionRef,
    provider_session_from_task,
    task_with_provider_session,
)
from aico.core.collaboration import collaboration_payload, parse_collaboration_directive
from aico.core.command_messages import (
    ack_failure_message,
    approval_required_message,
    audit_message,
    metrics_message,
    short_id_text,
    status_message,
)
from aico.core.commands import Command, CommandName, help_text, parse_command, reject_parts
from aico.core.memory import MemoryPacket, MemoryRetriever, MemoryScope, MemoryStore
from aico.core.memory_capture import MemoryCaptureService
from aico.core.memory_commands import MemoryCommandHandler
from aico.core.models import (
    AckStatus,
    IncomingMessage,
    MessageContent,
    OutputType,
    SentMessage,
    Task,
)
from aico.core.orchestrator_commands import DirectoryCommandHandler
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectAssignmentDirectory,
    task_with_assignment_context,
)
from aico.core.project_commands import ProjectCommandHandler
from aico.core.project_summary import ProjectSummaryCoordinator
from aico.core.prompt_stack import render_appointment_prompt
from aico.core.role_proposal import RoleProposalCoordinator
from aico.core.router import MessageRouter
from aico.core.session_commands import (
    has_explicit_task_target,
    session_scope,
)
from aico.core.streaming import StreamedMessageWriter
from aico.core.task_bus import TaskBus

log = logging.getLogger(__name__)
ProviderSessionRefFactory = Callable[[AgentSession], ProviderSessionRef | None]


class Orchestrator:
    """Handle an incoming IM message by submitting a task and streaming progress back."""

    def __init__(
        self,
        channel: IMChannel,
        router: MessageRouter,
        task_bus: TaskBus,
        session_store: InMemoryAgentSessionStore | None = None,
        provider_session_factory: ProviderSessionRefFactory | None = None,
        agent_directory: AgentDirectory | None = None,
        project_directory: ProjectAssignmentDirectory | None = None,
        memory_store: MemoryStore | None = None,
    ) -> None:
        self._channel = channel
        self._router = router
        self._task_bus = task_bus
        self._session_store = session_store or InMemoryAgentSessionStore()
        self._provider_session_factory = provider_session_factory
        self._agent_directory = agent_directory or AgentDirectory()
        self._project_directory = project_directory or ProjectAssignmentDirectory()
        self._memory_store = memory_store
        self._task_sessions: dict[str, str] = {}
        self._assignment_sessions: dict[str, str] = {}
        self._role_proposals = RoleProposalCoordinator(
            task_bus=self._task_bus,
            session_store=self._session_store,
            project_directory=self._project_directory,
            task_sessions=self._task_sessions,
            task_for_assignment=self._internal_task_for_assignment,
        )
        self._project_summaries = ProjectSummaryCoordinator(
            task_bus=self._task_bus,
            session_store=self._session_store,
            project_directory=self._project_directory,
            task_sessions=self._task_sessions,
            task_for_assignment=self._internal_task_for_assignment,
        )
        self._directory_commands = DirectoryCommandHandler(
            channel=self._channel,
            router=self._router,
            task_bus=self._task_bus,
            session_store=self._session_store,
            agent_directory=self._agent_directory,
            project_directory=self._project_directory,
            provider_session_factory=self._provider_session_factory,
            run_target_task=self._run_target_task,
        )
        self._project_commands = ProjectCommandHandler(
            channel=self._channel,
            task_bus=self._task_bus,
            agent_directory=self._agent_directory,
            project_directory=self._project_directory,
            run_role_task=self._run_project_role_task,
            propose_role=self._role_proposals.propose,
            summarize_project=self._project_summaries.summarize,
        )
        self._memory_commands = MemoryCommandHandler(
            channel=self._channel,
            project_directory=self._project_directory,
            memory_store=self._memory_store,
        )
        self._memory_capture = (
            MemoryCaptureService(self._memory_store) if self._memory_store is not None else None
        )

    def bind(self) -> None:
        self._channel.on_incoming(self.handle_incoming)

    async def handle_incoming(self, message: IncomingMessage) -> None:
        log.info(
            "Incoming message: raw_ref=%s sender=%s chars=%s",
            message.raw_ref,
            message.sender_id,
            len(message.content.text),
        )
        command = parse_command(message.content.text)
        if command is not None:
            log.info("Command received: raw_ref=%s command=%s", message.raw_ref, command.name.value)
            await self._handle_command(message, command)
            return

        self._capture_boss_feedback(message)
        task, session = self._task_for_message(message)
        log.info(
            "Task routed: task_id=%s target=%s payload_chars=%s",
            task.task_id,
            task.target_persona,
            len(task.payload),
        )
        await self._run_task(
            message,
            task,
            include_target=False,
            session_id=None if session is None else session.session_id,
        )

    async def _handle_command(self, message: IncomingMessage, command: Command) -> None:
        await _handle_command(self, message, command)

    def _capture_boss_feedback(self, message: IncomingMessage) -> None:
        if self._memory_capture is None:
            return
        self._memory_capture.capture_boss_feedback(
            message,
            active_project=self._project_directory.active_project(session_scope(message)),
        )

    async def _handle_broadcast(self, message: IncomingMessage, payload: str) -> None:
        if not payload:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /broadcast <task>"),
            )
            return

        targets = self._task_bus.broadcast_targets()
        if not targets:
            await self._channel.send_message(message.source, MessageContent(text="No targets"))
            return

        await self._channel.send_message(
            message.source,
            MessageContent(text=f"Broadcast accepted: {len(targets)} targets"),
        )
        tasks = [self._router.to_task_for_target(message, target, payload) for target in targets]
        await asyncio.gather(
            *(self._run_task(message, task, include_target=True) for task in tasks)
        )

    async def _handle_approval(self, message: IncomingMessage, task_id: str | None) -> None:
        ack = await self._task_bus.approve(task_id or None, reviewer_id=message.sender_id)
        if ack.status is not AckStatus.ACCEPTED:
            await self._channel.send_message(
                message.source,
                ack_failure_message(ack.status, ack.reason),
            )
            return

        sent_message = await self._channel.send_message(
            message.source,
            MessageContent(text=f"Task approved: {short_id_text(ack.task_id)}"),
        )
        approval_task = self._task_bus.task_record(ack.task_id)
        if approval_task is None:
            await self._stream_outputs(message, sent_message, ack.task_id)
            return
        session_id = self._task_sessions.get(ack.task_id)
        if session_id is not None:
            self._session_store.mark_busy(session_id, ack.task_id)
        try:
            await self._stream_outputs_for_task(message, sent_message, approval_task)
            if session_id is not None:
                self._mark_provider_initialized(session_id, approval_task)
        finally:
            if session_id is not None:
                self._session_store.mark_idle(session_id)
                self._task_sessions.pop(ack.task_id, None)

    async def _handle_rejection(
        self,
        message: IncomingMessage,
        task_id: str | None,
        reason: str | None,
    ) -> None:
        ack = await self._task_bus.reject_approval(
            task_id,
            reviewer_id=message.sender_id,
            reason=reason,
        )
        await self._channel.send_message(
            message.source,
            ack_failure_message(ack.status, ack.reason),
        )

    async def _handle_interrupt(self, message: IncomingMessage, task_ref: str) -> None:
        if not task_ref:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /interrupt <task_id>"),
            )
            return
        ack = await self._task_bus.interrupt(task_ref)
        if ack.status is not AckStatus.ACCEPTED:
            await self._channel.send_message(
                message.source,
                ack_failure_message(ack.status, ack.reason),
            )
            return
        await self._channel.send_message(
            message.source,
            MessageContent(text=f"Task interrupted: {short_id_text(ack.task_id)}"),
        )

    async def _run_task(
        self,
        message: IncomingMessage,
        task: Task,
        *,
        include_target: bool,
        collaboration_depth: int = 0,
        session_id: str | None = None,
    ) -> None:
        if session_id is not None:
            self._task_sessions[task.task_id] = session_id
        ack = await self._task_bus.submit(task)
        log.info(
            "Task ack: task_id=%s target=%s status=%s reason=%s",
            task.task_id,
            task.target_persona,
            ack.status.value,
            ack.reason,
        )
        if ack.status is AckStatus.WAITING_APPROVAL:
            await self._channel.send_message(
                message.source,
                approval_required_message(task.task_id, ack.reason),
            )
            return
        if ack.status is not AckStatus.ACCEPTED:
            if session_id is not None:
                self._task_sessions.pop(task.task_id, None)
            await self._channel.send_message(
                message.source,
                ack_failure_message(ack.status, ack.reason),
            )
            return

        target_text = f" [{task.target_persona}]" if include_target else ""
        if session_id is not None:
            self._session_store.mark_busy(session_id, task.task_id)
        sent_message = await self._channel.send_message(
            message.source,
            MessageContent(text=f"Task accepted: {task.task_id}{target_text}"),
        )
        try:
            await self._stream_outputs_for_task(
                message,
                sent_message,
                task,
                collaboration_depth=collaboration_depth,
            )
            if session_id is not None:
                self._mark_provider_initialized(session_id, task)
        finally:
            if session_id is not None:
                self._session_store.mark_idle(session_id)
                self._task_sessions.pop(task.task_id, None)

    async def _run_target_task(self, message: IncomingMessage, task: Task) -> None:
        await self._run_task(message, task, include_target=True)

    async def _run_project_role_task(
        self,
        message: IncomingMessage,
        role_ref: str,
        payload: str,
    ) -> None:
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="No active project. Use /project <project> first."),
            )
            return
        assignment = self._project_directory.appointment_for_role(project.id, role_ref)
        if assignment is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Role not appointed in {project.id}: {role_ref}"),
            )
            return
        task, session = self._task_for_assignment(message, project.id, assignment, payload=payload)
        await self._run_task(
            message,
            task,
            include_target=True,
            session_id=None if session is None else session.session_id,
        )

    def _task_for_message(
        self,
        message: IncomingMessage,
    ) -> tuple[Task, AgentSession | None]:
        if has_explicit_task_target(message):
            return self._router.to_task(message), None

        project = self._project_directory.active_project(session_scope(message))
        if project is not None:
            assignment = self._project_directory.default_assignment(project.id)
            if assignment is not None:
                return self._task_for_assignment(message, project.id, assignment)

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

    def _internal_task_for_assignment(
        self,
        message: IncomingMessage,
        project_id: str,
        assignment: AssignmentProfile,
        payload: str,
    ) -> tuple[Task, AgentSession | None]:
        return self._task_for_assignment(message, project_id, assignment, payload=payload)

    def _task_for_assignment(
        self,
        message: IncomingMessage,
        project_id: str,
        assignment: AssignmentProfile,
        *,
        payload: str | None = None,
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
                    memory_packet=self._memory_packet_for_assignment(
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
        packet = MemoryRetriever(self._memory_store).retrieve_packet(
            scopes=scopes,
            query=query,
        )
        return packet if packet.items else None

    def _ensure_assignment_session(
        self,
        assignment: AssignmentProfile,
        target_agent: str,
        project_workspace: str,
    ) -> AgentSession:
        session_id = self._assignment_sessions.get(assignment.seat)
        session = None if session_id is None else self._session_store.get(session_id)
        if session is not None:
            return session

        card = self._agent_directory.resolve(target_agent)
        adapter_name = assignment.agent if card is None else card.adapter_name
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

    def _mark_provider_initialized(self, session_id: str, task: Task) -> None:
        provider_session = provider_session_from_task(task)
        if provider_session is None or provider_session.mode is not ProviderSessionMode.NEW:
            return
        self._session_store.mark_provider_initialized(session_id)

    async def _stream_outputs_for_task(
        self,
        message: IncomingMessage,
        sent_message: SentMessage,
        task: Task,
        *,
        collaboration_depth: int = 0,
    ) -> None:
        log.info("Stream start: task_id=%s target=%s", task.task_id, task.target_persona)
        writer = StreamedMessageWriter(self._channel, message.source, sent_message)
        async for output in self._task_bus.stream_output(task.task_id):
            text = ""
            if output.type is OutputType.TEXT:
                directive = parse_collaboration_directive(output.content)
                if directive is not None and collaboration_depth == 0:
                    await self._handle_collaboration_directive(
                        message,
                        task,
                        directive.target_persona,
                        directive.payload,
                    )
                    continue
                text = output.content
            elif output.type is OutputType.ERROR:
                text = f"\nERROR: {output.content}"
            elif output.type is OutputType.DONE and output.content:
                text = output.content

            if text:
                log.info(
                    "Stream output: task_id=%s type=%s chars=%s",
                    task.task_id,
                    output.type.value,
                    len(text),
                )
            await writer.append(text)
        log.info("Stream finished: task_id=%s", task.task_id)

    async def _stream_outputs(
        self,
        message: IncomingMessage,
        sent_message: SentMessage,
        task_id: str,
    ) -> None:
        task = self._task_bus.task_record(task_id)
        if task is None:
            writer = StreamedMessageWriter(self._channel, message.source, sent_message)
            async for output in self._task_bus.stream_output(task_id):
                if output.type is OutputType.ERROR:
                    await writer.append(f"\nERROR: {output.content}")
            return
        await self._stream_outputs_for_task(message, sent_message, task)

    async def _handle_collaboration_directive(
        self,
        message: IncomingMessage,
        source_task: Task,
        target_persona: str,
        payload: str,
    ) -> None:
        log.info(
            "Collaboration directive: parent_task=%s source=%s target=%s payload_chars=%s",
            source_task.task_id,
            source_task.target_persona,
            target_persona,
            len(payload),
        )
        await self._channel.send_message(
            message.source,
            MessageContent(
                text=f"Collaboration requested: {source_task.target_persona} -> {target_persona}"
            ),
        )
        child_task = self._router.to_task_for_target(
            message,
            target_persona,
            collaboration_payload(source_task.target_persona, payload),
        )
        self._task_bus.record_collaboration_requested(source_task, child_task)
        await self._run_task(
            message,
            child_task,
            include_target=True,
            collaboration_depth=1,
        )


async def _handle_command(
    orchestrator: Orchestrator,
    message: IncomingMessage,
    command: Command,
) -> None:
    if command.name is CommandName.HELP:
        await orchestrator._channel.send_message(message.source, MessageContent(text=help_text()))
    elif command.name is CommandName.STATUS:
        await orchestrator._channel.send_message(
            message.source,
            status_message(
                orchestrator._task_bus.snapshots(),
                orchestrator._task_bus.task_snapshots(),
            ),
        )
    elif command.name is CommandName.METRICS:
        await orchestrator._channel.send_message(
            message.source,
            metrics_message(
                orchestrator._task_bus.task_snapshots(limit=None),
                orchestrator._task_bus.audit_events(limit=None),
            ),
        )
    elif command.name is CommandName.TASKS:
        await orchestrator._directory_commands.handle_tasks(message, command.payload)
    elif command.name is CommandName.TASK:
        await orchestrator._directory_commands.handle_task(message, command.payload)
    elif command.name is CommandName.AUDIT:
        await orchestrator._channel.send_message(
            message.source,
            audit_message(orchestrator._task_bus.audit_events()),
        )
    elif command.name is CommandName.PROJECTS:
        await orchestrator._project_commands.handle_projects(message)
    elif command.name is CommandName.PROJECT:
        await orchestrator._project_commands.handle_project(message, command.payload)
    elif command.name is CommandName.BRIEF:
        await orchestrator._project_commands.handle_brief(message, command.payload or None)
    elif command.name is CommandName.RISKS:
        await orchestrator._project_commands.handle_risks(message, command.payload or None)
    elif command.name is CommandName.BLOCKERS:
        await orchestrator._project_commands.handle_blockers(message, command.payload or None)
    elif command.name is CommandName.NEXT:
        await orchestrator._project_commands.handle_next(message, command.payload or None)
    elif command.name is CommandName.DAILY:
        await orchestrator._project_commands.handle_daily(message, command.payload or None)
    elif command.name is CommandName.WEEKLY:
        await orchestrator._project_commands.handle_weekly(message, command.payload or None)
    elif command.name is CommandName.ROLES:
        await orchestrator._project_commands.handle_roles(message, command.payload or None)
    elif command.name is CommandName.ROLE:
        await orchestrator._project_commands.handle_role(message, command.payload)
    elif command.name is CommandName.TEAM:
        await orchestrator._project_commands.handle_team(message, command.payload or None)
    elif command.name is CommandName.WHO:
        await orchestrator._project_commands.handle_who(message, command.payload)
    elif command.name is CommandName.APPOINT:
        await orchestrator._project_commands.handle_appoint(message, command.payload)
    elif command.name is CommandName.UNAPPOINT:
        await orchestrator._project_commands.handle_unappoint(message, command.payload)
    elif command.name is CommandName.ASK:
        await orchestrator._project_commands.handle_ask(message, command.payload)
    elif command.name in {CommandName.LEAD, CommandName.DEFAULT}:
        await orchestrator._project_commands.handle_default(message, command.payload)
    elif command.name is CommandName.ASSIGNMENTS:
        await orchestrator._project_commands.handle_assignments(message, command.payload or None)
    elif command.name is CommandName.ASSIGNMENT:
        await orchestrator._project_commands.handle_assignment(message, command.payload)
    elif command.name is CommandName.AGENTS:
        await orchestrator._directory_commands.handle_agents(message)
    elif command.name is CommandName.AGENT:
        await orchestrator._directory_commands.handle_agent(message, command.payload)
    elif command.name is CommandName.SKILLS:
        await orchestrator._directory_commands.handle_skills(message, command.payload)
    elif command.name is CommandName.TOOLS:
        await orchestrator._directory_commands.handle_tools(message, command.payload)
    elif command.name is CommandName.REMEMBER:
        await orchestrator._memory_commands.handle_remember(message, command.payload)
    elif command.name is CommandName.RECALL:
        await orchestrator._memory_commands.handle_recall(message, command.payload)
    elif command.name is CommandName.FORGET:
        await orchestrator._memory_commands.handle_forget(message, command.payload)
    elif command.name is CommandName.APPROVE:
        await orchestrator._handle_approval(message, command.payload or None)
    elif command.name is CommandName.REJECT:
        task_id, reason = reject_parts(command)
        await orchestrator._handle_rejection(message, task_id, reason)
    elif command.name is CommandName.INTERRUPT:
        await orchestrator._handle_interrupt(message, command.payload)
    elif command.name is CommandName.BROADCAST:
        await orchestrator._handle_broadcast(message, command.payload)
    elif command.name is CommandName.SESSIONS:
        await orchestrator._directory_commands.handle_sessions(message)
    elif command.name is CommandName.NEW:
        await orchestrator._directory_commands.handle_new_session(message, command.payload)
    elif command.name is CommandName.USE:
        await orchestrator._directory_commands.handle_use_session(message, command.payload)
    elif command.name is CommandName.BIND:
        await orchestrator._directory_commands.handle_bind_session(message, command.payload)
