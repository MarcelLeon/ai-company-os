"""Project status and report command handlers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from aico.channel import IMChannel
from aico.core.models import IncomingMessage, MessageContent
from aico.core.project_assignment import ProjectAssignmentDirectory, ProjectProfile
from aico.core.project_docs import (
    blocker_document_snippets,
    brief_document_snippets,
    risk_document_snippets,
)
from aico.core.project_messages import (
    project_blockers_message,
    project_brief_message,
    project_next_message,
    project_report_message,
    project_risks_message,
    project_summary_message,
)
from aico.core.session_commands import session_scope
from aico.core.task_bus import TaskBus

ProjectSummaryRunner = Callable[
    [IncomingMessage, ProjectProfile, str, str],
    Awaitable[str | None],
]


class ProjectStatusCommandHandler:
    """Handle project status, blockers, next-action, and report commands."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        task_bus: TaskBus,
        project_directory: ProjectAssignmentDirectory,
        summarize_project: ProjectSummaryRunner | None = None,
    ) -> None:
        self._channel = channel
        self._task_bus = task_bus
        self._project_directory = project_directory
        self._summarize_project = summarize_project

    async def handle_brief(self, message: IncomingMessage, project_id: str | None) -> None:
        project = self._project_from_optional_ref(message, project_id)
        if project is None:
            await self._send_no_active_project(message)
            return
        await self._send_with_summary(
            message,
            project,
            "brief",
            project_brief_message(
                project,
                self._project_directory.appointments(project.id),
                self._project_directory.default_assignment(project.id),
                self._task_bus.task_snapshots(),
                self._task_bus.audit_events(),
                brief_document_snippets(project),
            ),
        )

    async def handle_risks(self, message: IncomingMessage, project_id: str | None) -> None:
        project = self._project_from_optional_ref(message, project_id)
        if project is None:
            await self._send_no_active_project(message)
            return
        await self._send_with_summary(
            message,
            project,
            "risks",
            project_risks_message(
                project,
                self._task_bus.task_snapshots(),
                self._task_bus.audit_events(),
                risk_document_snippets(project),
            ),
        )

    async def handle_blockers(self, message: IncomingMessage, project_id: str | None) -> None:
        project = self._project_from_optional_ref(message, project_id)
        if project is None:
            await self._send_no_active_project(message)
            return
        await self._send_with_summary(
            message,
            project,
            "blockers",
            project_blockers_message(
                project,
                self._task_bus.task_snapshots(),
                blocker_document_snippets(project),
            ),
        )

    async def handle_next(self, message: IncomingMessage, project_id: str | None) -> None:
        project = self._project_from_optional_ref(message, project_id)
        if project is None:
            await self._send_no_active_project(message)
            return
        await self._send_with_summary(
            message,
            project,
            "next actions",
            project_next_message(
                project,
                self._project_directory.appointments(project.id),
                self._project_directory.default_assignment(project.id),
                self._task_bus.task_snapshots(),
                blocker_document_snippets(project),
            ),
        )

    async def handle_daily(self, message: IncomingMessage, project_id: str | None) -> None:
        await self._send_project_report(
            message,
            project_id,
            title="Daily report",
            window_label="last 24h in local AICO state",
            window_days=1,
        )

    async def handle_weekly(self, message: IncomingMessage, project_id: str | None) -> None:
        await self._send_project_report(
            message,
            project_id,
            title="Weekly report",
            window_label="last 7d in local AICO state",
            window_days=7,
        )

    async def _send_project_report(
        self,
        message: IncomingMessage,
        project_id: str | None,
        *,
        title: str,
        window_label: str,
        window_days: int,
    ) -> None:
        project = self._project_from_optional_ref(message, project_id)
        if project is None:
            await self._send_no_active_project(message)
            return
        await self._send_with_summary(
            message,
            project,
            title.lower(),
            project_report_message(
                project,
                self._project_directory.appointments(project.id),
                self._project_directory.default_assignment(project.id),
                self._task_bus.task_snapshots(limit=20),
                self._task_bus.audit_events(limit=50),
                brief_document_snippets(project),
                risk_document_snippets(project),
                title=title,
                window_label=window_label,
                window_days=window_days,
            ),
        )

    def _project_from_optional_ref(
        self,
        message: IncomingMessage,
        project_ref: str | None,
    ) -> ProjectProfile | None:
        if project_ref:
            return self._project_directory.project(project_ref)
        return self._project_directory.active_project(session_scope(message))

    async def _send_with_summary(
        self,
        message: IncomingMessage,
        project: ProjectProfile,
        report_name: str,
        facts: MessageContent,
    ) -> None:
        summary = None
        if self._summarize_project is not None:
            summary = await self._summarize_project(message, project, report_name, facts.text)
        await self._channel.send_message(
            message.source,
            project_summary_message(facts, summary),
        )

    async def _send_no_active_project(self, message: IncomingMessage) -> None:
        await self._channel.send_message(
            message.source,
            MessageContent(text="No active project. Use /project <project> first."),
        )
