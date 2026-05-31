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
    ProviderSessionRef,
)
from aico.core.collaboration import collaboration_payload, split_collaboration_directive
from aico.core.command_messages import (
    ack_failure_message,
    approval_required_message,
    audit_message,
    metrics_message,
    short_id_text,
    status_message,
)
from aico.core.commands import Command, CommandName, help_text, parse_command, reject_parts
from aico.core.dream import DreamCommandHandler
from aico.core.experience_commands import ExperienceCommandHandler
from aico.core.goal_brief_commands import GoalBriefCommandHandler
from aico.core.inbox import inbox_message
from aico.core.language import (
    ResponseLanguageStore,
    language_message,
    language_usage_message,
    parse_response_language,
    task_with_response_language,
)
from aico.core.lead_decision import (
    LeadDecisionWorkflow,
    is_decision_task,
)
from aico.core.memory import MemoryStore
from aico.core.memory_capture import MemoryCaptureService
from aico.core.memory_commands import MemoryCommandHandler
from aico.core.message_rendering import rich_text_message
from aico.core.models import (
    AckStatus,
    IncomingMessage,
    MessageContent,
    OutputType,
    SentMessage,
    Task,
)
from aico.core.morning import morning_message
from aico.core.native_output import native_output_format_from_task, task_with_native_output_format
from aico.core.offline_delegation import OfflineDelegationCommandHandler, OfflineDelegationStore
from aico.core.orchestrator_commands import DirectoryCommandHandler
from aico.core.orchestrator_task_factory import OrchestratorTaskFactory, _is_same_assignment
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectAssignmentDirectory,
)
from aico.core.project_commands import ProjectCommandHandler
from aico.core.project_summary import ProjectSummaryCoordinator
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
        offline_delegation_store: OfflineDelegationStore | None = None,
        prefer_native_channel_format: bool = False,
    ) -> None:
        self._channel = channel
        self._router = router
        self._task_bus = task_bus
        self._session_store = session_store or InMemoryAgentSessionStore()
        self._provider_session_factory = provider_session_factory
        self._agent_directory = agent_directory or AgentDirectory()
        self._project_directory = project_directory or ProjectAssignmentDirectory()
        self._memory_store = memory_store
        self._prefer_native_channel_format = prefer_native_channel_format
        self._task_sessions: dict[str, str] = {}
        self._response_languages = ResponseLanguageStore()
        self._task_factory = OrchestratorTaskFactory(
            router=self._router,
            session_store=self._session_store,
            agent_directory=self._agent_directory,
            project_directory=self._project_directory,
            memory_store=self._memory_store,
            provider_session_factory=self._provider_session_factory,
        )
        self._role_proposals = RoleProposalCoordinator(
            task_bus=self._task_bus,
            session_store=self._session_store,
            project_directory=self._project_directory,
            task_sessions=self._task_sessions,
            task_for_assignment=self._task_factory.task_for_assignment,
        )
        self._project_summaries = ProjectSummaryCoordinator(
            task_bus=self._task_bus,
            session_store=self._session_store,
            project_directory=self._project_directory,
            task_sessions=self._task_sessions,
            task_for_assignment=self._task_factory.task_for_assignment,
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
        self._dream_commands = DreamCommandHandler(
            channel=self._channel,
            project_directory=self._project_directory,
            memory_store=self._memory_store,
            task_bus=self._task_bus,
        )
        self._experience_commands = ExperienceCommandHandler(
            channel=self._channel,
            project_directory=self._project_directory,
            memory_store=self._memory_store,
        )
        self._offline_delegations = OfflineDelegationCommandHandler(
            channel=self._channel,
            project_directory=self._project_directory,
            task_for_assignment=self._task_factory.task_for_assignment,
            run_delegated_task=self._run_delegated_task,
            store=offline_delegation_store,
        )
        self._goal_briefs = GoalBriefCommandHandler(
            channel=self._channel,
            project_directory=self._project_directory,
            task_bus=self._task_bus,
            task_for_assignment=self._task_factory.task_for_assignment,
            run_goal_task=self._run_delegated_task,
            memory_store=self._memory_store,
        )
        self._lead_decisions = LeadDecisionWorkflow(
            channel=self._channel,
            project_directory=self._project_directory,
            memory_store=self._memory_store,
            audit_recorder=self._task_bus,
            task_for_assignment=self._task_factory.task_for_assignment_with_memory,
            run_decision_task=self._run_decision_task,
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
        lead_decision = self._lead_decision_assignment_for_message(message)
        if lead_decision is not None:
            project_id, assignment = lead_decision
            await self._lead_decisions.run(
                message,
                project_id=project_id,
                assignment=assignment,
                boss_task=message.content.text.strip(),
            )
            return
        task, session = self._task_factory.task_for_message(message)
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
                self._task_factory.mark_provider_initialized(session_id, approval_task)
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

    async def _handle_language(self, message: IncomingMessage, payload: str) -> None:
        scope_id = session_scope(message)
        if not payload.strip():
            await self._channel.send_message(
                message.source,
                language_message(current=self._response_languages.current(scope_id)),
            )
            return
        language = parse_response_language(payload)
        if language is None:
            await self._channel.send_message(message.source, language_usage_message())
            return
        self._response_languages.set_language(scope_id, language)
        await self._channel.send_message(
            message.source,
            language_message(
                current=self._response_languages.current(scope_id),
                updated=True,
            ),
        )

    async def _run_task(
        self,
        message: IncomingMessage,
        task: Task,
        *,
        include_target: bool,
        collaboration_depth: int = 0,
        session_id: str | None = None,
    ) -> str:
        task = task_with_response_language(
            task,
            self._response_languages.current(session_scope(message)),
        )
        task = task_with_native_output_format(
            task,
            channel_name=message.source.channel_name,
            enabled=self._prefer_native_channel_format,
        )
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
            return ""
        if ack.status is not AckStatus.ACCEPTED:
            if session_id is not None:
                self._task_sessions.pop(task.task_id, None)
            await self._channel.send_message(
                message.source,
                ack_failure_message(ack.status, ack.reason),
            )
            return ""

        target_text = f" [{task.target_persona}]" if include_target else ""
        if session_id is not None:
            self._session_store.mark_busy(session_id, task.task_id)
        sent_message = await self._channel.send_message(
            message.source,
            MessageContent(text=f"Task accepted: {task.task_id}{target_text}"),
        )
        try:
            output_text = await self._stream_outputs_for_task(
                message,
                sent_message,
                task,
                collaboration_depth=collaboration_depth,
            )
            if session_id is not None:
                self._task_factory.mark_provider_initialized(session_id, task)
            return output_text
        finally:
            if session_id is not None:
                self._session_store.mark_idle(session_id)
                self._task_sessions.pop(task.task_id, None)

    async def _run_target_task(self, message: IncomingMessage, task: Task) -> None:
        await self._run_task(message, task, include_target=True)

    async def _run_delegated_task(
        self,
        message: IncomingMessage,
        task: Task,
        session: AgentSession | None,
    ) -> str:
        return await self._run_task(
            message,
            task,
            include_target=True,
            session_id=None if session is None else session.session_id,
        )

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
        if self._should_run_lead_decision(project.id, assignment, payload):
            await self._lead_decisions.run(
                message,
                project_id=project.id,
                assignment=assignment,
                boss_task=payload,
            )
            return
        if await self._goal_briefs.maybe_run_auto_goal(
            message,
            project=project,
            assignment=assignment,
            payload=payload,
        ):
            return
        task, session = self._task_factory.task_for_assignment(
            message, project.id, assignment, payload=payload
        )
        await self._run_task(
            message,
            task,
            include_target=True,
            session_id=None if session is None else session.session_id,
        )

    def _lead_decision_assignment_for_message(
        self,
        message: IncomingMessage,
    ) -> tuple[str, AssignmentProfile] | None:
        if has_explicit_task_target(message):
            return None
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            return None
        assignment = self._project_directory.default_assignment(project.id)
        if assignment is None:
            return None
        if not self._should_run_lead_decision(project.id, assignment, message.content.text):
            return None
        return project.id, assignment

    def _should_run_lead_decision(
        self,
        project_id: str,
        assignment: AssignmentProfile,
        payload: str,
    ) -> bool:
        return _is_same_assignment(
            assignment,
            self._project_directory.default_assignment(project_id),
        ) and is_decision_task(payload)

    async def _run_decision_task(
        self,
        message: IncomingMessage,
        task: Task,
        session: AgentSession | None,
        collaboration_depth: int,
    ) -> str:
        return await self._run_task(
            message,
            task,
            include_target=True,
            collaboration_depth=collaboration_depth,
            session_id=None if session is None else session.session_id,
        )

    async def _stream_outputs_for_task(
        self,
        message: IncomingMessage,
        sent_message: SentMessage,
        task: Task,
        *,
        collaboration_depth: int = 0,
    ) -> str:
        log.info("Stream start: task_id=%s target=%s", task.task_id, task.target_persona)
        writer = StreamedMessageWriter(
            self._channel,
            message.source,
            sent_message,
            preferred_format=native_output_format_from_task(task),
        )
        captured: list[str] = []
        async for output in self._task_bus.stream_output(task.task_id):
            text = ""
            if output.type is OutputType.TEXT:
                directive, remaining = split_collaboration_directive(output.content)
                if directive is not None and collaboration_depth == 0:
                    parent_context = "".join((*captured, remaining))
                    await self._handle_collaboration_directive(
                        message,
                        task,
                        directive.target_persona,
                        directive.payload,
                        parent_context,
                    )
                text = remaining
            elif output.type is OutputType.STATUS:
                await writer.show_status(output.content)
                continue
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
                captured.append(text)
            await writer.append(text)
        log.info("Stream finished: task_id=%s", task.task_id)
        return "".join(captured)

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
        source_context: str,
    ) -> None:
        source_label = _collaboration_source_label(source_task)
        log.info(
            "Collaboration directive: parent_task=%s source=%s target=%s payload_chars=%s",
            source_task.task_id,
            source_label,
            target_persona,
            len(payload),
        )
        await self._channel.send_message(
            message.source,
            rich_text_message(
                "\n".join(
                    (
                        "# Collaboration requested",
                        f"source: {source_label}",
                        f"target: {target_persona}",
                    )
                )
            ),
        )
        child_task = self._router.to_task_for_target(
            message,
            target_persona,
            collaboration_payload(source_label, payload, source_context=source_context),
        )
        self._task_bus.record_collaboration_requested(
            source_task,
            child_task,
            actor_id=source_label,
        )
        await self._run_task(
            message,
            child_task,
            include_target=True,
            collaboration_depth=1,
        )


_ASSIGNMENT_ROLE_METADATA_KEY = "aico.assignment_role"


def _collaboration_source_label(task: Task) -> str:
    for entry in task.metadata:
        if (
            entry.key == _ASSIGNMENT_ROLE_METADATA_KEY
            and isinstance(entry.value, str)
            and entry.value.strip()
        ):
            return entry.value.strip()
    return task.target_persona


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
    elif command.name is CommandName.INBOX:
        await _handle_inbox_command(orchestrator, message)
    elif command.name is CommandName.MORNING:
        await _handle_morning_command(orchestrator, message)
    elif command.name is CommandName.LANGUAGE:
        await orchestrator._handle_language(message, command.payload)
    elif command.name is CommandName.TASKS:
        await orchestrator._directory_commands.handle_tasks(message, command.payload)
    elif command.name is CommandName.TASK:
        await orchestrator._directory_commands.handle_task(message, command.payload)
    elif command.name is CommandName.AUDIT:
        await orchestrator._channel.send_message(
            message.source,
            audit_message(orchestrator._task_bus.audit_events()),
        )
    elif command.name in _PROJECT_COMMANDS:
        await _handle_project_command(orchestrator, message, command)
    elif command.name is CommandName.OVERNIGHT:
        await orchestrator._offline_delegations.handle_overnight(message, command.payload)
    elif command.name is CommandName.DREAM:
        await orchestrator._dream_commands.handle_dream(message)
    elif command.name is CommandName.EXPERIENCE:
        await orchestrator._experience_commands.handle_experience(message, command.payload)
    elif command.name is CommandName.GOAL:
        await orchestrator._goal_briefs.handle_goal(message, command.payload)
    elif command.name in _PROJECT_ROLE_COMMANDS:
        await _handle_project_role_command(orchestrator, message, command)
    elif command.name in _DIRECTORY_COMMANDS:
        await _handle_directory_command(orchestrator, message, command)
    elif command.name in _MEMORY_COMMANDS:
        await _handle_memory_command(orchestrator, message, command)
    elif command.name is CommandName.APPROVE:
        await orchestrator._handle_approval(message, command.payload or None)
    elif command.name is CommandName.REJECT:
        task_id, reason = reject_parts(command)
        await orchestrator._handle_rejection(message, task_id, reason)
    elif command.name is CommandName.INTERRUPT:
        await orchestrator._handle_interrupt(message, command.payload)
    elif command.name is CommandName.BROADCAST:
        await orchestrator._handle_broadcast(message, command.payload)


_PROJECT_COMMANDS = {
    CommandName.PROJECTS,
    CommandName.PROJECT,
    CommandName.BRIEF,
    CommandName.RISKS,
    CommandName.BLOCKERS,
    CommandName.NEXT,
    CommandName.DAILY,
    CommandName.WEEKLY,
}

_PROJECT_ROLE_COMMANDS = {
    CommandName.ROLES,
    CommandName.ROLE,
    CommandName.TEAM,
    CommandName.WHO,
    CommandName.APPOINT,
    CommandName.UNAPPOINT,
    CommandName.ASK,
    CommandName.LEAD,
    CommandName.DEFAULT,
    CommandName.ASSIGNMENTS,
    CommandName.ASSIGNMENT,
}

_DIRECTORY_COMMANDS = {
    CommandName.AGENTS,
    CommandName.AGENT,
    CommandName.SKILLS,
    CommandName.TOOLS,
    CommandName.SESSIONS,
    CommandName.NEW,
    CommandName.USE,
    CommandName.BIND,
}

_MEMORY_COMMANDS = {CommandName.REMEMBER, CommandName.RECALL, CommandName.FORGET}


async def _handle_inbox_command(orchestrator: Orchestrator, message: IncomingMessage) -> None:
    project = orchestrator._project_directory.active_project(session_scope(message))
    if project is None:
        await orchestrator._channel.send_message(
            message.source,
            MessageContent(text="No active project. Use /project <project> first."),
        )
        return
    await orchestrator._channel.send_message(
        message.source,
        inbox_message(
            project_id=project.id,
            task_snapshots=orchestrator._task_bus.task_snapshots(limit=None),
            overnight_records=orchestrator._offline_delegations.records_for_scope(
                session_scope(message),
                project_id=project.id,
            ),
            audit_events=orchestrator._task_bus.audit_events(limit=None),
        ),
    )


async def _handle_morning_command(orchestrator: Orchestrator, message: IncomingMessage) -> None:
    project = orchestrator._project_directory.active_project(session_scope(message))
    if project is None:
        await orchestrator._channel.send_message(
            message.source,
            MessageContent(text="No active project. Use /project <project> first."),
        )
        return
    await orchestrator._channel.send_message(
        message.source,
        morning_message(
            project_id=project.id,
            task_snapshots=orchestrator._task_bus.task_snapshots(limit=None),
            overnight_records=orchestrator._offline_delegations.records_for_scope(
                session_scope(message),
                project_id=project.id,
            ),
            audit_events=orchestrator._task_bus.audit_events(limit=None),
        ),
    )


async def _handle_project_command(
    orchestrator: Orchestrator,
    message: IncomingMessage,
    command: Command,
) -> None:
    if command.name is CommandName.PROJECTS:
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


async def _handle_project_role_command(
    orchestrator: Orchestrator,
    message: IncomingMessage,
    command: Command,
) -> None:
    if command.name is CommandName.ROLES:
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


async def _handle_directory_command(
    orchestrator: Orchestrator,
    message: IncomingMessage,
    command: Command,
) -> None:
    if command.name is CommandName.AGENTS:
        await orchestrator._directory_commands.handle_agents(message)
    elif command.name is CommandName.AGENT:
        await orchestrator._directory_commands.handle_agent(message, command.payload)
    elif command.name is CommandName.SKILLS:
        await orchestrator._directory_commands.handle_skills(message, command.payload)
    elif command.name is CommandName.TOOLS:
        await orchestrator._directory_commands.handle_tools(message, command.payload)
    elif command.name is CommandName.SESSIONS:
        await orchestrator._directory_commands.handle_sessions(message)
    elif command.name is CommandName.NEW:
        await orchestrator._directory_commands.handle_new_session(message, command.payload)
    elif command.name is CommandName.USE:
        await orchestrator._directory_commands.handle_use_session(message, command.payload)
    elif command.name is CommandName.BIND:
        await orchestrator._directory_commands.handle_bind_session(message, command.payload)


async def _handle_memory_command(
    orchestrator: Orchestrator,
    message: IncomingMessage,
    command: Command,
) -> None:
    if command.name is CommandName.REMEMBER:
        await orchestrator._memory_commands.handle_remember(message, command.payload)
    elif command.name is CommandName.RECALL:
        await orchestrator._memory_commands.handle_recall(message, command.payload)
    elif command.name is CommandName.FORGET:
        await orchestrator._memory_commands.handle_forget(message, command.payload)
