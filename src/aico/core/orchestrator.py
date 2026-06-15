"""Phase 1 orchestration loop for one channel and one task bus."""

from __future__ import annotations

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
)
from aico.core.commands import Command, parse_command
from aico.core.language import (
    ResponseLanguageStore,
    task_with_response_language,
)
from aico.core.lead_decision import is_decision_task
from aico.core.memory import MemoryAtom, MemoryScope, MemoryStore
from aico.core.memory_capture import MemoryCaptureService
from aico.core.message_rendering import rich_text_message
from aico.core.models import (
    AckStatus,
    ChannelTarget,
    IncomingMessage,
    MessageContent,
    OutputType,
    SentMessage,
    Task,
    TaskSnapshot,
    TaskStatus,
)
from aico.core.native_output import native_output_format_from_task, task_with_native_output_format
from aico.core.offline_delegation import (
    OfflineDelegationStore,
    offline_delegation_completion_issue,
    offline_delegation_incomplete_message,
)
from aico.core.orchestrator_command_registry import OrchestratorCommandRegistry
from aico.core.orchestrator_task_factory import OrchestratorTaskFactory, _is_same_assignment
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectAssignmentDirectory,
)
from aico.core.router import MessageRouter
from aico.core.session_commands import (
    has_explicit_task_target,
    session_scope,
)
from aico.core.streaming import StreamedMessageWriter
from aico.core.task_bus import TaskBus
from aico.core.unified_event import InMemoryUnifiedEventIndex, UnifiedEventIndex
from aico.view.commands import ViewSnapshotCommandHandler

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
        view_snapshot_handler: ViewSnapshotCommandHandler | None = None,
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
        self._view_snapshots = view_snapshot_handler
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
        self._memory_capture = (
            MemoryCaptureService(self._memory_store) if self._memory_store is not None else None
        )
        self._commands = OrchestratorCommandRegistry(
            channel=self._channel,
            router=self._router,
            task_bus=self._task_bus,
            session_store=self._session_store,
            agent_directory=self._agent_directory,
            project_directory=self._project_directory,
            memory_store=self._memory_store,
            task_factory=self._task_factory,
            task_sessions=self._task_sessions,
            response_languages=self._response_languages,
            provider_session_factory=self._provider_session_factory,
            offline_delegation_store=offline_delegation_store,
            view_snapshot_handler=self._view_snapshots,
            run_task=self._run_task,
            run_target_task=self._run_target_task,
            run_project_role_task=self._run_project_role_task,
            run_delegated_task=self._run_delegated_task,
            run_goal_task=self._run_goal_task,
            run_decision_task=self._run_decision_task,
            stream_outputs_for_task=self._stream_outputs_for_task,
            stream_outputs=self._stream_outputs,
            event_index_factory=self._build_event_index,
        )

    def bind(self) -> None:
        self._channel.on_incoming(self.handle_incoming)

    def _build_event_index(self) -> UnifiedEventIndex:
        return _build_orchestrator_event_index(
            task_bus=self._task_bus,
            memory_store=self._memory_store,
            project_directory=self._project_directory,
        )

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
            await self._commands.lead_decisions.run(
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
        await self._commands.handle(message, command)

    async def send_morning_handoff(
        self,
        target: ChannelTarget,
        *,
        project_id: str,
        scope_id: str | None = None,
    ) -> None:
        await self._commands.send_morning_handoff(
            target,
            project_id=project_id,
            scope_id=scope_id,
        )

    def _capture_boss_feedback(self, message: IncomingMessage) -> None:
        if self._memory_capture is None:
            return
        self._memory_capture.capture_boss_feedback(
            message,
            active_project=self._project_directory.active_project(session_scope(message)),
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
        output = await self._run_task(
            message,
            task,
            include_target=True,
            session_id=None if session is None else session.session_id,
        )
        await self._mark_incomplete_overnight_handoff(message, task, output)
        return output

    async def _mark_incomplete_overnight_handoff(
        self,
        message: IncomingMessage,
        task: Task,
        output: str,
    ) -> None:
        snapshot = self._task_bus.task_snapshot(task.task_id)
        if not isinstance(snapshot, TaskSnapshot) or snapshot.status is not TaskStatus.DONE:
            return
        issue = offline_delegation_completion_issue(output)
        if issue is None:
            return
        self._task_bus.mark_failed(task.task_id, reason=issue)
        await self._channel.send_message(
            message.source,
            offline_delegation_incomplete_message(task.task_id, issue),
        )

    async def _run_goal_task(
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
            await self._commands.lead_decisions.run(
                message,
                project_id=project.id,
                assignment=assignment,
                boss_task=payload,
            )
            return
        if await self._commands.goal_briefs.maybe_run_auto_goal(
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


def _build_orchestrator_event_index(
    *,
    task_bus: TaskBus,
    memory_store: MemoryStore | None,
    project_directory: ProjectAssignmentDirectory,
) -> UnifiedEventIndex:
    memory_atoms: list[MemoryAtom] = []
    if memory_store is not None:
        for project in project_directory.projects():
            memory_atoms.extend(
                memory_store.list_atoms(
                    MemoryScope.project(project.id),
                    include_archived=True,
                )
            )
    return InMemoryUnifiedEventIndex(
        audit_events=task_bus.audit_events(limit=None),
        memory_atoms=tuple(memory_atoms),
        task_snapshots=task_bus.task_snapshots(limit=None),
    )


def _collaboration_source_label(task: Task) -> str:
    for entry in task.metadata:
        if (
            entry.key == _ASSIGNMENT_ROLE_METADATA_KEY
            and isinstance(entry.value, str)
            and entry.value.strip()
        ):
            return entry.value.strip()
    return task.target_persona
