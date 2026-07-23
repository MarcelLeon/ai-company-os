"""Command registry for Orchestrator slash-command handling."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from uuid import uuid4

from aico.channel import IMChannel
from aico.core.agent_directory import AgentDirectory
from aico.core.agent_session import (
    AgentSession,
    InMemoryAgentSessionStore,
    ProviderSessionRef,
)
from aico.core.command_messages import (
    ack_failure_message,
    audit_message,
    metrics_message,
    short_id_text,
    status_message,
)
from aico.core.commands import Command, CommandName, help_text, reject_parts
from aico.core.dream import DreamCommandHandler
from aico.core.experience_commands import ExperienceCommandHandler
from aico.core.goal_brief_commands import GoalBriefCommandHandler
from aico.core.inbox import inbox_message
from aico.core.language import (
    ResponseLanguageStore,
    language_message,
    language_usage_message,
    parse_response_language,
)
from aico.core.lead_decision import LeadDecisionWorkflow
from aico.core.memory import MemoryAtom, MemoryScope, MemoryStatus, MemoryStore
from aico.core.memory_commands import MemoryCommandHandler
from aico.core.models import (
    AckStatus,
    ChannelTarget,
    IncomingMessage,
    MessageContent,
    SentMessage,
    Task,
    TaskSnapshot,
    TaskStatus,
)
from aico.core.morning import (
    MorningHandoffEnvelope,
    morning_handoff_envelope,
    morning_message,
)
from aico.core.offline_delegation import OfflineDelegationCommandHandler, OfflineDelegationStore
from aico.core.orchestrator_commands import DirectoryCommandHandler
from aico.core.orchestrator_task_factory import OrchestratorTaskFactory
from aico.core.project_assignment import ProjectAssignmentDirectory
from aico.core.project_commands import ProjectCommandHandler
from aico.core.project_summary import ProjectSummaryCoordinator
from aico.core.role_proposal import RoleProposalCoordinator
from aico.core.router import MessageRouter
from aico.core.session_commands import session_scope
from aico.core.standing_autonomy import (
    PreauthorizedTaskRunner,
    StandingAutonomyCoordinator,
    StandingAutonomyGrantSet,
    StandingAutonomyOutcomeEnvelope,
    StandingAutonomyReceipt,
    StandingAutonomyReceiptStatus,
    StandingAutonomyRunDisposition,
    StandingAutonomyRunReceipt,
    standing_autonomy_outcome_envelope,
    standing_autonomy_receipts,
)
from aico.core.standing_evidence_pack import (
    StandingEvidencePack,
    StandingEvidencePackError,
    build_standing_evidence_pack,
)
from aico.core.standing_proposal import (
    StandingProposal,
    StandingProposalCoordinator,
    StandingProposalStore,
)
from aico.core.task_bus import TaskBus, task_usage_for_task
from aico.core.timeline_rollback_commands import RollbackCommandHandler, TimelineCommandHandler
from aico.core.undo_why_commands import UndoCommandHandler, WhyCommandHandler
from aico.core.unified_event import UnifiedEventIndex
from aico.view.commands import ViewSnapshotCommandHandler

ProviderSessionRefFactory = Callable[[AgentSession], ProviderSessionRef | None]
TargetTaskRunner = Callable[[IncomingMessage, Task], Awaitable[None]]
TaskRunner = Callable[..., Awaitable[str]]
ProjectRoleTaskRunner = Callable[[IncomingMessage, str, str, bool], Awaitable[None]]
DelegatedTaskRunner = Callable[[IncomingMessage, Task, AgentSession | None], Awaitable[str]]
EventIndexFactory = Callable[[], UnifiedEventIndex]
StreamTaskOutput = Callable[[IncomingMessage, SentMessage, Task], Awaitable[str]]
StreamTaskIdOutput = Callable[[IncomingMessage, SentMessage, str], Awaitable[None]]


class _MorningDeliveryRegistryMixin:
    _channel: IMChannel
    _event_index_factory: EventIndexFactory
    _memory_store: MemoryStore | None
    _offline_delegations: OfflineDelegationCommandHandler
    _project_directory: ProjectAssignmentDirectory
    _standing_autonomy: StandingAutonomyCoordinator
    _standing_proposals: StandingProposalCoordinator
    _task_bus: TaskBus

    async def deliver_morning_handoff(
        self,
        target: ChannelTarget,
        envelope: MorningHandoffEnvelope,
    ) -> SentMessage:
        return await self._channel.send_message(target, envelope.content)

    async def send_morning_handoff(
        self,
        target: ChannelTarget,
        *,
        project_id: str,
        scope_id: str | None = None,
        delivery_id: str | None = None,
    ) -> SentMessage:
        if delivery_id is None:
            delivery_id = f"morning-{uuid4().hex}"
        envelope = self.prepare_morning_handoff(
            project_id=project_id,
            scope_id=scope_id or target.target_id,
            delivery_id=delivery_id,
        )
        sent = await self.deliver_morning_handoff(target, envelope)
        receipt = await self.run_scheduled_autonomy(
            target,
            project_id=envelope.project_id,
            intent_id=f"autonomy-{uuid4().hex}",
        )
        outcome = self.prepare_scheduled_autonomy_outcome(receipt)
        if outcome is not None:
            await self.deliver_scheduled_autonomy_outcome(target, outcome)
        return sent

    def prepare_morning_handoff(
        self,
        *,
        project_id: str,
        scope_id: str,
        delivery_id: str,
    ) -> MorningHandoffEnvelope:
        project = self._project_directory.project(project_id)
        if project is None:
            raise ValueError(f"unknown morning push project: {project_id}")
        task_snapshots = self._task_bus.task_snapshots(limit=None)
        proposals = self._standing_proposals.refresh(project.id, task_snapshots)
        index = self._event_index_factory()
        return morning_handoff_envelope(
            delivery_id=delivery_id,
            project_id=project.id,
            task_snapshots=task_snapshots,
            overnight_records=self._offline_delegations.records_for_scope(
                scope_id,
                project_id=project.id,
            ),
            audit_events=self._task_bus.audit_events(limit=None),
            recent_events=index.recent(limit=5),
            experience_candidates=self._candidate_experiences(project.id),
            standing_proposals=proposals,
            standing_autonomy_receipts=self._autonomy_receipts(project.id, task_snapshots),
        )

    async def run_scheduled_autonomy(
        self,
        target: ChannelTarget,
        *,
        project_id: str,
        intent_id: str,
    ) -> StandingAutonomyRunReceipt:
        task_snapshots = self._task_bus.task_snapshots(limit=None)
        return await self._standing_autonomy.run_once(
            target,
            project_id=project_id,
            task_snapshots=task_snapshots,
            intent_id=intent_id,
        )

    def scheduled_autonomy_evidence(
        self,
        *,
        project_id: str,
        intent_id: str,
    ) -> StandingAutonomyRunReceipt | None:
        return self._standing_autonomy.evidence_for_intent(
            project_id=project_id,
            intent_id=intent_id,
        )

    def prepare_scheduled_autonomy_outcome(
        self,
        receipt: StandingAutonomyRunReceipt,
    ) -> StandingAutonomyOutcomeEnvelope | None:
        if receipt.disposition is not StandingAutonomyRunDisposition.DISPATCH_RECORDED:
            return None
        task_snapshots = self._task_bus.task_snapshots(limit=None)
        outcome = next(
            (
                item
                for item in self._autonomy_receipts(receipt.project_id, task_snapshots)
                if item.proposal_id == receipt.proposal_id and item.task_id == receipt.task_id
            ),
            None,
        )
        if outcome is None:
            raise ValueError("scheduled autonomy outcome evidence is missing")
        if outcome.status in {
            StandingAutonomyReceiptStatus.RUNNING,
            StandingAutonomyReceiptStatus.WAITING_APPROVAL,
        }:
            return None
        return standing_autonomy_outcome_envelope(receipt, outcome)

    async def deliver_scheduled_autonomy_outcome(
        self,
        target: ChannelTarget,
        envelope: StandingAutonomyOutcomeEnvelope,
    ) -> SentMessage:
        return await self._channel.send_message(target, envelope.content)

    def _candidate_experiences(self, project_id: str) -> tuple[MemoryAtom, ...]:
        if self._memory_store is None:
            return ()
        return self._memory_store.list_experiences(
            MemoryScope.project(project_id),
            statuses=(MemoryStatus.CANDIDATE,),
        )

    def _autonomy_receipts(
        self,
        project_id: str,
        task_snapshots: tuple[TaskSnapshot, ...],
    ) -> tuple[StandingAutonomyReceipt, ...]:
        return standing_autonomy_receipts(
            self._standing_proposals.history(project_id),
            task_snapshots,
            evidence_root=_project_evidence_root(self._project_directory, project_id),
        )


class OrchestratorCommandRegistry(_MorningDeliveryRegistryMixin):
    """Own slash-command handlers and keep Orchestrator focused on task execution."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        router: MessageRouter,
        task_bus: TaskBus,
        session_store: InMemoryAgentSessionStore,
        agent_directory: AgentDirectory,
        project_directory: ProjectAssignmentDirectory,
        memory_store: MemoryStore | None,
        task_factory: OrchestratorTaskFactory,
        task_sessions: dict[str, str],
        response_languages: ResponseLanguageStore,
        provider_session_factory: ProviderSessionRefFactory | None,
        offline_delegation_store: OfflineDelegationStore | None,
        standing_proposal_store: StandingProposalStore | None,
        standing_autonomy_grants: StandingAutonomyGrantSet | None,
        view_snapshot_handler: ViewSnapshotCommandHandler | None,
        run_task: TaskRunner,
        run_target_task: TargetTaskRunner,
        run_project_role_task: ProjectRoleTaskRunner,
        run_delegated_task: DelegatedTaskRunner,
        run_preauthorized_task: PreauthorizedTaskRunner,
        run_goal_task: DelegatedTaskRunner,
        run_decision_task: TaskRunner,
        stream_outputs_for_task: StreamTaskOutput,
        stream_outputs: StreamTaskIdOutput,
        event_index_factory: EventIndexFactory,
    ) -> None:
        self._channel = channel
        self._router = router
        self._task_bus = task_bus
        self._session_store = session_store
        self._project_directory = project_directory
        self._memory_store = memory_store
        self._view_snapshots = view_snapshot_handler
        self._task_factory = task_factory
        self._task_sessions = task_sessions
        self._response_languages = response_languages
        self._run_task = run_task
        self._stream_outputs_for_task = stream_outputs_for_task
        self._stream_outputs = stream_outputs
        self._event_index_factory = event_index_factory
        self._role_proposals: RoleProposalCoordinator
        self._project_summaries: ProjectSummaryCoordinator
        self._directory_commands: DirectoryCommandHandler
        self._project_commands: ProjectCommandHandler
        self._memory_commands: MemoryCommandHandler
        self._dream_commands: DreamCommandHandler
        self._experience_commands: ExperienceCommandHandler
        self._undo_commands: UndoCommandHandler
        self._why_commands: WhyCommandHandler
        self._timeline_commands: TimelineCommandHandler
        self._rollback_commands: RollbackCommandHandler
        self._offline_delegations: OfflineDelegationCommandHandler
        self._goal_briefs: GoalBriefCommandHandler
        self._lead_decisions: LeadDecisionWorkflow
        self._standing_proposals: StandingProposalCoordinator
        self._standing_autonomy: StandingAutonomyCoordinator
        _install_command_handlers(
            self,
            channel=channel,
            router=router,
            task_bus=task_bus,
            session_store=session_store,
            agent_directory=agent_directory,
            project_directory=project_directory,
            memory_store=memory_store,
            task_factory=task_factory,
            task_sessions=task_sessions,
            provider_session_factory=provider_session_factory,
            offline_delegation_store=offline_delegation_store,
            standing_proposal_store=standing_proposal_store,
            standing_autonomy_grants=standing_autonomy_grants,
            run_target_task=run_target_task,
            run_project_role_task=run_project_role_task,
            run_delegated_task=run_delegated_task,
            run_preauthorized_task=run_preauthorized_task,
            run_goal_task=run_goal_task,
            run_decision_task=run_decision_task,
            event_index_factory=event_index_factory,
        )

    @property
    def lead_decisions(self) -> LeadDecisionWorkflow:
        return self._lead_decisions

    @property
    def goal_briefs(self) -> GoalBriefCommandHandler:
        return self._goal_briefs

    async def handle(self, message: IncomingMessage, command: Command) -> None:
        if command.name is CommandName.HELP:
            await self._channel.send_message(message.source, MessageContent(text=help_text()))
        elif command.name is CommandName.STATUS:
            await self._channel.send_message(
                message.source,
                status_message(self._task_bus.snapshots(), self._task_bus.task_snapshots()),
            )
        elif command.name is CommandName.METRICS:
            await self._channel.send_message(
                message.source,
                metrics_message(
                    self._task_bus.task_snapshots(limit=None),
                    self._task_bus.audit_events(limit=None),
                ),
            )
        elif command.name is CommandName.INBOX:
            await self._handle_inbox(message)
        elif command.name is CommandName.MORNING:
            await self._handle_morning(message)
        elif command.name is CommandName.PROPOSALS:
            await self._handle_proposals(message)
        elif command.name is CommandName.PROPOSAL:
            await self._standing_proposals.handle_proposal(message, command.payload)
        elif command.name is CommandName.LANGUAGE:
            await self._handle_language(message, command.payload)
        elif command.name is CommandName.TASKS:
            await self._directory_commands.handle_tasks(message, command.payload)
        elif command.name is CommandName.TASK:
            await self._directory_commands.handle_task(message, command.payload)
        elif command.name is CommandName.AUDIT:
            await self._channel.send_message(
                message.source,
                audit_message(self._task_bus.audit_events()),
            )
        elif command.name in _PROJECT_COMMANDS:
            await self._handle_project(message, command)
        elif command.name is CommandName.OVERNIGHT:
            await self._offline_delegations.handle_overnight(message, command.payload)
        elif command.name is CommandName.DREAM:
            await self._dream_commands.handle_dream(message)
        elif command.name is CommandName.EXPERIENCE:
            await self._experience_commands.handle_experience(message, command.payload)
        elif command.name is CommandName.UNDO:
            await self._undo_commands.handle_undo(message, command.payload)
        elif command.name is CommandName.WHY:
            await self._why_commands.handle_why(message, command.payload)
        elif command.name is CommandName.VIEW:
            await self._handle_view(message, command.payload)
        elif command.name is CommandName.TIMELINE:
            await self._timeline_commands.handle_timeline(message, command.payload)
        elif command.name is CommandName.ROLLBACK:
            await self._rollback_commands.handle_rollback(message, command.payload)
        elif command.name is CommandName.GOAL:
            await self._goal_briefs.handle_goal(message, command.payload)
        elif command.name in _PROJECT_ROLE_COMMANDS:
            await self._handle_project_role(message, command)
        elif command.name in _DIRECTORY_COMMANDS:
            await self._handle_directory(message, command)
        elif command.name in _MEMORY_COMMANDS:
            await self._handle_memory(message, command)
        elif command.name is CommandName.APPROVE:
            await self._handle_approval(message, command.payload or None)
        elif command.name is CommandName.REJECT:
            task_id, reason = reject_parts(command)
            await self._handle_rejection(message, task_id, reason)
        elif command.name is CommandName.INTERRUPT:
            await self._handle_interrupt(message, command.payload)
        elif command.name is CommandName.BROADCAST:
            await self._handle_broadcast(message, command.payload)

    async def _handle_inbox(self, message: IncomingMessage) -> None:
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="No active project. Use /project <project> first."),
            )
            return
        task_snapshots = self._task_bus.task_snapshots(limit=None)
        proposals = self._standing_proposals.refresh(project.id, task_snapshots)
        index = self._event_index_factory()
        await self._channel.send_message(
            message.source,
            inbox_message(
                project_id=project.id,
                task_snapshots=task_snapshots,
                overnight_records=self._offline_delegations.records_for_scope(
                    session_scope(message),
                    project_id=project.id,
                ),
                audit_events=self._task_bus.audit_events(limit=None),
                recent_events=index.recent(limit=5),
                experience_candidates=self._candidate_experiences(project.id),
                standing_proposals=proposals,
                standing_autonomy_receipts=self._autonomy_receipts(project.id, task_snapshots),
            ),
        )

    async def _handle_morning(self, message: IncomingMessage) -> None:
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="No active project. Use /project <project> first."),
            )
            return
        task_snapshots = self._task_bus.task_snapshots(limit=None)
        proposals = self._standing_proposals.refresh(project.id, task_snapshots)
        index = self._event_index_factory()
        await self._channel.send_message(
            message.source,
            morning_message(
                project_id=project.id,
                task_snapshots=task_snapshots,
                overnight_records=self._offline_delegations.records_for_scope(
                    session_scope(message),
                    project_id=project.id,
                ),
                audit_events=self._task_bus.audit_events(limit=None),
                recent_events=index.recent(limit=5),
                experience_candidates=self._candidate_experiences(project.id),
                standing_proposals=proposals,
                standing_autonomy_receipts=self._autonomy_receipts(project.id, task_snapshots),
            ),
        )

    async def _handle_proposals(self, message: IncomingMessage) -> None:
        project = self._project_directory.active_project(session_scope(message))
        if project is not None:
            self._standing_proposals.refresh(
                project.id,
                self._task_bus.task_snapshots(limit=None),
            )
        await self._standing_proposals.handle_list(message)

    async def _handle_view(self, message: IncomingMessage, payload: str) -> None:
        if self._view_snapshots is None:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=(
                        "AICO view snapshots are not configured. Set AICO_VIEW_ENABLED=true "
                        "and restart aico-phase1."
                    )
                ),
            )
            return
        await self._view_snapshots.handle_view(message, payload)

    async def _handle_project(self, message: IncomingMessage, command: Command) -> None:
        if command.name is CommandName.PROJECTS:
            await self._project_commands.handle_projects(message)
        elif command.name is CommandName.PROJECT:
            await self._project_commands.handle_project(message, command.payload)
        elif command.name is CommandName.BRIEF:
            await self._project_commands.handle_brief(message, command.payload or None)
        elif command.name is CommandName.RISKS:
            await self._project_commands.handle_risks(message, command.payload or None)
        elif command.name is CommandName.BLOCKERS:
            await self._project_commands.handle_blockers(message, command.payload or None)
        elif command.name is CommandName.NEXT:
            await self._project_commands.handle_next(message, command.payload or None)
        elif command.name is CommandName.DAILY:
            await self._project_commands.handle_daily(message, command.payload or None)
        elif command.name is CommandName.WEEKLY:
            await self._project_commands.handle_weekly(message, command.payload or None)

    async def _handle_project_role(self, message: IncomingMessage, command: Command) -> None:
        if command.name is CommandName.ROLES:
            await self._project_commands.handle_roles(message, command.payload or None)
        elif command.name is CommandName.ROLE:
            await self._project_commands.handle_role(message, command.payload)
        elif command.name is CommandName.TEAM:
            await self._project_commands.handle_team(message, command.payload or None)
        elif command.name is CommandName.WHO:
            await self._project_commands.handle_who(message, command.payload)
        elif command.name is CommandName.APPOINT:
            await self._project_commands.handle_appoint(message, command.payload)
        elif command.name is CommandName.UNAPPOINT:
            await self._project_commands.handle_unappoint(message, command.payload)
        elif command.name is CommandName.ASK:
            await self._project_commands.handle_ask(message, command.payload)
        elif command.name in {CommandName.LEAD, CommandName.DEFAULT}:
            await self._project_commands.handle_default(message, command.payload)
        elif command.name is CommandName.ASSIGNMENTS:
            await self._project_commands.handle_assignments(message, command.payload or None)
        elif command.name is CommandName.ASSIGNMENT:
            await self._project_commands.handle_assignment(message, command.payload)

    async def _handle_directory(self, message: IncomingMessage, command: Command) -> None:
        if command.name is CommandName.AGENTS:
            await self._directory_commands.handle_agents(message)
        elif command.name is CommandName.AGENT:
            await self._directory_commands.handle_agent(message, command.payload)
        elif command.name is CommandName.SKILLS:
            await self._directory_commands.handle_skills(message, command.payload)
        elif command.name is CommandName.TOOLS:
            await self._directory_commands.handle_tools(message, command.payload)
        elif command.name is CommandName.SESSIONS:
            await self._directory_commands.handle_sessions(message)
        elif command.name is CommandName.NEW:
            await self._directory_commands.handle_new_session(message, command.payload)
        elif command.name is CommandName.USE:
            await self._directory_commands.handle_use_session(message, command.payload)
        elif command.name is CommandName.BIND:
            await self._directory_commands.handle_bind_session(message, command.payload)

    async def _handle_memory(self, message: IncomingMessage, command: Command) -> None:
        if command.name is CommandName.REMEMBER:
            await self._memory_commands.handle_remember(message, command.payload)
        elif command.name is CommandName.RECALL:
            await self._memory_commands.handle_recall(message, command.payload)
        elif command.name is CommandName.FORGET:
            await self._memory_commands.handle_forget(message, command.payload)

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


def _install_command_handlers(
    registry: OrchestratorCommandRegistry,
    *,
    channel: IMChannel,
    router: MessageRouter,
    task_bus: TaskBus,
    session_store: InMemoryAgentSessionStore,
    agent_directory: AgentDirectory,
    project_directory: ProjectAssignmentDirectory,
    memory_store: MemoryStore | None,
    task_factory: OrchestratorTaskFactory,
    task_sessions: dict[str, str],
    provider_session_factory: ProviderSessionRefFactory | None,
    offline_delegation_store: OfflineDelegationStore | None,
    standing_proposal_store: StandingProposalStore | None,
    standing_autonomy_grants: StandingAutonomyGrantSet | None,
    run_target_task: TargetTaskRunner,
    run_project_role_task: ProjectRoleTaskRunner,
    run_delegated_task: DelegatedTaskRunner,
    run_preauthorized_task: PreauthorizedTaskRunner,
    run_goal_task: DelegatedTaskRunner,
    run_decision_task: TaskRunner,
    event_index_factory: EventIndexFactory,
) -> None:
    registry._role_proposals = _build_role_proposals(
        task_bus,
        session_store,
        project_directory,
        task_sessions,
        task_factory,
    )
    registry._project_summaries = _build_project_summaries(
        task_bus,
        session_store,
        project_directory,
        task_sessions,
        task_factory,
    )
    registry._directory_commands = _build_directory_commands(
        channel=channel,
        router=router,
        task_bus=task_bus,
        session_store=session_store,
        agent_directory=agent_directory,
        project_directory=project_directory,
        provider_session_factory=provider_session_factory,
        run_target_task=run_target_task,
    )
    registry._project_commands = _build_project_commands(
        channel=channel,
        task_bus=task_bus,
        agent_directory=agent_directory,
        project_directory=project_directory,
        run_project_role_task=run_project_role_task,
        role_proposals=registry._role_proposals,
        project_summaries=registry._project_summaries,
    )
    _install_memory_and_audit_handlers(
        registry,
        channel=channel,
        task_bus=task_bus,
        project_directory=project_directory,
        memory_store=memory_store,
        event_index_factory=event_index_factory,
    )
    registry._offline_delegations = _build_offline_delegations(
        channel=channel,
        project_directory=project_directory,
        task_factory=task_factory,
        run_delegated_task=run_delegated_task,
        store=offline_delegation_store,
    )
    _install_standing_handlers(
        registry,
        channel=channel,
        project_directory=project_directory,
        task_factory=task_factory,
        run_delegated_task=run_delegated_task,
        standing_proposal_store=standing_proposal_store,
        standing_autonomy_grants=standing_autonomy_grants,
        task_bus=task_bus,
        run_preauthorized_task=run_preauthorized_task,
    )
    registry._goal_briefs = _build_goal_briefs(
        channel=channel,
        project_directory=project_directory,
        task_bus=task_bus,
        task_factory=task_factory,
        run_goal_task=run_goal_task,
        memory_store=memory_store,
    )
    registry._lead_decisions = _build_lead_decisions(
        channel=channel,
        project_directory=project_directory,
        memory_store=memory_store,
        task_bus=task_bus,
        task_factory=task_factory,
        run_decision_task=run_decision_task,
    )


def _install_standing_handlers(
    registry: OrchestratorCommandRegistry,
    *,
    channel: IMChannel,
    project_directory: ProjectAssignmentDirectory,
    task_factory: OrchestratorTaskFactory,
    run_delegated_task: DelegatedTaskRunner,
    standing_proposal_store: StandingProposalStore | None,
    standing_autonomy_grants: StandingAutonomyGrantSet | None,
    task_bus: TaskBus,
    run_preauthorized_task: PreauthorizedTaskRunner,
) -> None:
    registry._standing_proposals = _build_standing_proposals(
        channel=channel,
        project_directory=project_directory,
        task_factory=task_factory,
        run_delegated_task=run_delegated_task,
        store=standing_proposal_store,
    )
    registry._standing_autonomy = StandingAutonomyCoordinator(
        channel=channel,
        proposals=registry._standing_proposals,
        grants=standing_autonomy_grants,
        preflight=task_bus.preauthorized_refusal,
        run_task=run_preauthorized_task,
        usage_for_task=lambda task_id: task_usage_for_task(task_bus, task_id),
        status_for_task=lambda task_id: _task_status(task_bus, task_id),
        evidence_root_for_project=lambda project_id: _project_evidence_root(
            project_directory, project_id
        ),
        evidence_pack_for_proposal=lambda proposal: _project_evidence_pack(
            project_directory, proposal
        ),
        authorization_time_refusal=task_bus.authorization_time_refusal,
    )


def _project_evidence_root(
    directory: ProjectAssignmentDirectory,
    project_id: str,
) -> Path | None:
    project = directory.project(project_id)
    if project is None:
        return None
    root = Path(project.repo).expanduser()
    return root if root.is_absolute() else Path.cwd() / root


def _project_evidence_pack(
    directory: ProjectAssignmentDirectory,
    proposal: StandingProposal,
) -> StandingEvidencePack:
    project = directory.project(proposal.project_id)
    root = _project_evidence_root(directory, proposal.project_id)
    if project is None or root is None:
        raise StandingEvidencePackError("standing evidence project is unavailable")
    charter = next(
        (item for item in project.standing_charter if item.id == proposal.charter_id),
        None,
    )
    if charter is None:
        raise StandingEvidencePackError("standing evidence charter is unavailable")
    return build_standing_evidence_pack(
        root,
        project_id=proposal.project_id,
        charter_id=proposal.charter_id,
        source_specs=charter.evidence_sources,
    )


def _task_status(task_bus: TaskBus, task_id: str) -> TaskStatus | None:
    snapshot = task_bus.task_snapshot(task_id)
    return snapshot.status if isinstance(snapshot, TaskSnapshot) else None


def _install_memory_and_audit_handlers(
    registry: OrchestratorCommandRegistry,
    *,
    channel: IMChannel,
    task_bus: TaskBus,
    project_directory: ProjectAssignmentDirectory,
    memory_store: MemoryStore | None,
    event_index_factory: EventIndexFactory,
) -> None:
    registry._memory_commands = MemoryCommandHandler(
        channel=channel,
        project_directory=project_directory,
        memory_store=memory_store,
    )
    registry._dream_commands = DreamCommandHandler(
        channel=channel,
        project_directory=project_directory,
        memory_store=memory_store,
        task_bus=task_bus,
    )
    registry._experience_commands = ExperienceCommandHandler(
        channel=channel,
        project_directory=project_directory,
        memory_store=memory_store,
    )
    registry._undo_commands = UndoCommandHandler(
        channel=channel,
        memory_store=memory_store,
        event_index_factory=event_index_factory,
    )
    registry._why_commands = WhyCommandHandler(
        channel=channel,
        event_index_factory=event_index_factory,
    )
    registry._timeline_commands = TimelineCommandHandler(
        channel=channel,
        event_index_factory=event_index_factory,
    )
    registry._rollback_commands = RollbackCommandHandler(
        channel=channel,
        memory_store=memory_store,
        audit_log=task_bus.audit_log(),
    )


def _build_role_proposals(
    task_bus: TaskBus,
    session_store: InMemoryAgentSessionStore,
    project_directory: ProjectAssignmentDirectory,
    task_sessions: dict[str, str],
    task_factory: OrchestratorTaskFactory,
) -> RoleProposalCoordinator:
    return RoleProposalCoordinator(
        task_bus=task_bus,
        session_store=session_store,
        project_directory=project_directory,
        task_sessions=task_sessions,
        task_for_assignment=task_factory.task_for_assignment,
    )


def _build_project_summaries(
    task_bus: TaskBus,
    session_store: InMemoryAgentSessionStore,
    project_directory: ProjectAssignmentDirectory,
    task_sessions: dict[str, str],
    task_factory: OrchestratorTaskFactory,
) -> ProjectSummaryCoordinator:
    return ProjectSummaryCoordinator(
        task_bus=task_bus,
        session_store=session_store,
        project_directory=project_directory,
        task_sessions=task_sessions,
        task_for_assignment=task_factory.task_for_assignment,
    )


def _build_directory_commands(
    *,
    channel: IMChannel,
    router: MessageRouter,
    task_bus: TaskBus,
    session_store: InMemoryAgentSessionStore,
    agent_directory: AgentDirectory,
    project_directory: ProjectAssignmentDirectory,
    provider_session_factory: ProviderSessionRefFactory | None,
    run_target_task: TargetTaskRunner,
) -> DirectoryCommandHandler:
    return DirectoryCommandHandler(
        channel=channel,
        router=router,
        task_bus=task_bus,
        session_store=session_store,
        agent_directory=agent_directory,
        project_directory=project_directory,
        provider_session_factory=provider_session_factory,
        run_target_task=run_target_task,
    )


def _build_project_commands(
    *,
    channel: IMChannel,
    task_bus: TaskBus,
    agent_directory: AgentDirectory,
    project_directory: ProjectAssignmentDirectory,
    run_project_role_task: ProjectRoleTaskRunner,
    role_proposals: RoleProposalCoordinator,
    project_summaries: ProjectSummaryCoordinator,
) -> ProjectCommandHandler:
    return ProjectCommandHandler(
        channel=channel,
        task_bus=task_bus,
        agent_directory=agent_directory,
        project_directory=project_directory,
        run_role_task=run_project_role_task,
        propose_role=role_proposals.propose,
        summarize_project=project_summaries.summarize,
    )


def _build_offline_delegations(
    *,
    channel: IMChannel,
    project_directory: ProjectAssignmentDirectory,
    task_factory: OrchestratorTaskFactory,
    run_delegated_task: DelegatedTaskRunner,
    store: OfflineDelegationStore | None,
) -> OfflineDelegationCommandHandler:
    return OfflineDelegationCommandHandler(
        channel=channel,
        project_directory=project_directory,
        task_for_assignment=task_factory.task_for_assignment,
        run_delegated_task=run_delegated_task,
        store=store,
    )


def _build_standing_proposals(
    *,
    channel: IMChannel,
    project_directory: ProjectAssignmentDirectory,
    task_factory: OrchestratorTaskFactory,
    run_delegated_task: DelegatedTaskRunner,
    store: StandingProposalStore | None,
) -> StandingProposalCoordinator:
    return StandingProposalCoordinator(
        channel=channel,
        project_directory=project_directory,
        task_for_assignment=task_factory.task_for_assignment,
        run_delegated_task=run_delegated_task,
        store=store,
    )


def _build_goal_briefs(
    *,
    channel: IMChannel,
    project_directory: ProjectAssignmentDirectory,
    task_bus: TaskBus,
    task_factory: OrchestratorTaskFactory,
    run_goal_task: DelegatedTaskRunner,
    memory_store: MemoryStore | None,
) -> GoalBriefCommandHandler:
    return GoalBriefCommandHandler(
        channel=channel,
        project_directory=project_directory,
        task_bus=task_bus,
        task_for_assignment=task_factory.task_for_assignment,
        run_goal_task=run_goal_task,
        memory_store=memory_store,
    )


def _build_lead_decisions(
    *,
    channel: IMChannel,
    project_directory: ProjectAssignmentDirectory,
    memory_store: MemoryStore | None,
    task_bus: TaskBus,
    task_factory: OrchestratorTaskFactory,
    run_decision_task: TaskRunner,
) -> LeadDecisionWorkflow:
    return LeadDecisionWorkflow(
        channel=channel,
        project_directory=project_directory,
        memory_store=memory_store,
        audit_recorder=task_bus,
        task_for_assignment=task_factory.task_for_assignment_with_memory,
        run_decision_task=run_decision_task,
    )
