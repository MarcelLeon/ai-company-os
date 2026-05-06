"""LLM-assisted summaries for local project status facts."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from aico.core.agent_session import (
    AgentSession,
    InMemoryAgentSessionStore,
    ProviderSessionMode,
    provider_session_from_task,
)
from aico.core.models import AckStatus, IncomingMessage, MetadataEntry, OutputType, Task
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectAssignmentDirectory,
    ProjectProfile,
)

if TYPE_CHECKING:
    from aico.core.task_bus import TaskBus

PROJECT_SUMMARY_INTENT = "project_summary"
PROJECT_SUMMARY_INTENT_KEY = "aico.intent"
ProjectTaskFactory = Callable[
    [IncomingMessage, str, AssignmentProfile, str],
    tuple[Task, AgentSession | None],
]


class ProjectSummaryCoordinator:
    """Ask the current project lead to summarize local facts without hiding them."""

    def __init__(
        self,
        *,
        task_bus: TaskBus,
        session_store: InMemoryAgentSessionStore,
        project_directory: ProjectAssignmentDirectory,
        task_sessions: dict[str, str],
        task_for_assignment: ProjectTaskFactory,
    ) -> None:
        self._task_bus = task_bus
        self._session_store = session_store
        self._project_directory = project_directory
        self._task_sessions = task_sessions
        self._task_for_assignment = task_for_assignment

    async def summarize(
        self,
        message: IncomingMessage,
        project: ProjectProfile,
        report_name: str,
        facts: str,
    ) -> str | None:
        assignment = self._project_directory.default_assignment(project.id)
        if assignment is None:
            return None
        task, session = self._task_for_assignment(
            message,
            project.id,
            assignment,
            project_summary_prompt(project, report_name=report_name, facts=facts),
        )
        output = await self._collect_task_output(
            _task_with_project_summary_intent(task),
            None if session is None else session.session_id,
        )
        if output.startswith("Project summary failed:"):
            return None
        return _clean_summary(output)

    async def _collect_task_output(self, task: Task, session_id: str | None) -> str:
        if session_id is not None:
            self._task_sessions[task.task_id] = session_id
        ack = await self._task_bus.submit(task)
        if ack.status is not AckStatus.ACCEPTED:
            if session_id is not None:
                self._task_sessions.pop(task.task_id, None)
            return f"Project summary failed: {ack.reason or ack.status.value}"
        if session_id is not None:
            self._session_store.mark_busy(session_id, task.task_id)
        chunks: list[str] = []
        try:
            async for output in self._task_bus.stream_output(task.task_id):
                if output.type is OutputType.ERROR:
                    return f"Project summary failed: {output.content}"
                if output.type in {OutputType.TEXT, OutputType.DONE} and output.content:
                    chunks.append(output.content)
            if session_id is not None:
                self._mark_provider_initialized(session_id, task)
        finally:
            if session_id is not None:
                self._session_store.mark_idle(session_id)
                self._task_sessions.pop(task.task_id, None)
        return "".join(chunks)

    def _mark_provider_initialized(self, session_id: str, task: Task) -> None:
        provider_session = provider_session_from_task(task)
        if provider_session is None or provider_session.mode is not ProviderSessionMode.NEW:
            return
        self._session_store.mark_provider_initialized(session_id)


def project_summary_prompt(project: ProjectProfile, *, report_name: str, facts: str) -> str:
    clipped_facts = facts[:6000]
    return (
        "Summarize these local AICO project facts for the human boss.\n"
        f"Project: {project.id} [{project.name}]\n"
        f"Report: {report_name}\n\n"
        "Rules:\n"
        "- Return 2-4 concise bullet lines.\n"
        "- Use only the facts below; do not invent progress, risks, owners, or dates.\n"
        "- Call out the next management decision only when the facts support it.\n"
        "- Keep the original facts auditable; this summary is only a top note.\n\n"
        "Facts:\n"
        f"{clipped_facts}"
    )


def _task_with_project_summary_intent(task: Task) -> Task:
    return task.model_copy(
        update={
            "metadata": (
                *task.metadata,
                MetadataEntry(key=PROJECT_SUMMARY_INTENT_KEY, value=PROJECT_SUMMARY_INTENT),
            )
        }
    )


def _clean_summary(output: str) -> str | None:
    summary = output.strip()
    if not summary:
        return None
    return summary
