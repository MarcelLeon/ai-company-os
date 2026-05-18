"""Build and parse LLM-assisted project role proposals."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

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
    RoleProfile,
)

if TYPE_CHECKING:
    from aico.core.task_bus import TaskBus

ROLE_PROPOSAL_INTENT = "role_proposal"
ROLE_PROPOSAL_INTENT_KEY = "aico.intent"
RoleTaskFactory = Callable[
    [IncomingMessage, str, AssignmentProfile, str],
    tuple[Task, AgentSession | None],
]


class RoleProposalCoordinator:
    """Run the internal read-only task that drafts a project role."""

    def __init__(
        self,
        *,
        task_bus: TaskBus,
        session_store: InMemoryAgentSessionStore,
        project_directory: ProjectAssignmentDirectory,
        task_sessions: dict[str, str],
        task_for_assignment: RoleTaskFactory,
    ) -> None:
        self._task_bus = task_bus
        self._session_store = session_store
        self._project_directory = project_directory
        self._task_sessions = task_sessions
        self._task_for_assignment = task_for_assignment

    async def propose(
        self,
        message: IncomingMessage,
        project: ProjectProfile,
        request: str,
    ) -> RoleProfile | str:
        assignment = self._project_directory.default_assignment(project.id)
        if assignment is None:
            return f"No lead role appointed in {project.id}. Appoint a lead first."
        task, session = self._task_for_assignment(
            message,
            project.id,
            assignment,
            role_proposal_prompt(project, request),
        )
        output = await self._collect_task_output(
            _task_with_role_proposal_intent(task),
            None if session is None else session.session_id,
        )
        if output.startswith("Role proposal failed:"):
            return output
        try:
            return role_from_llm_output(output, request)
        except ValueError as exc:
            return f"Role proposal failed: {exc}"

    async def _collect_task_output(self, task: Task, session_id: str | None) -> str:
        if session_id is not None:
            self._task_sessions[task.task_id] = session_id
        ack = await self._task_bus.submit(task)
        if ack.status is not AckStatus.ACCEPTED:
            if session_id is not None:
                self._task_sessions.pop(task.task_id, None)
            return f"Role proposal failed: {ack.reason or ack.status.value}"
        if session_id is not None:
            self._session_store.mark_busy(session_id, task.task_id)
        chunks: list[str] = []
        try:
            async for output in self._task_bus.stream_output(task.task_id):
                if output.type is OutputType.ERROR:
                    return f"Role proposal failed: {output.content}"
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


def role_proposal_prompt(project: ProjectProfile, request: str) -> str:
    """Ask a provider to draft one role as machine-readable JSON."""
    return (
        "Draft one project role for the boss to review.\n"
        f"Project: {project.id} [{project.name}]\n"
        f"Need: {request.strip()}\n\n"
        "Return only one JSON object with these keys:\n"
        '- "id": lowercase kebab-case role id\n'
        '- "title": short human title\n'
        '- "summary": one sentence responsibility summary\n'
        '- "default_permissions": array of permission tokens\n'
        '- "approval_required": array of risky permission tokens\n'
        '- "inline_prompt": concise instruction for the appointed agent\n'
        "Keep permissions to role scopes: docs, code, tests, ops, audit."
    )


def role_from_llm_output(output: str, request: str) -> RoleProfile:
    data = _json_object(output)
    title = _required_text(data, "title")
    summary = _required_text(data, "summary")
    role_id = _role_id(str(data.get("id") or title or request))
    inline_prompt = _optional_text(data.get("inline_prompt"))
    return RoleProfile(
        id=role_id,
        title=title,
        summary=summary,
        default_permissions=_string_tuple(data.get("default_permissions")),
        approval_required=_string_tuple(data.get("approval_required")),
        inline_prompt=inline_prompt,
    )


def _json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("role draft did not include a JSON object")
    value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("role draft JSON must be an object")
    return value


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"role draft missing {key}")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    tokens: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            tokens.append(item.strip())
    return tuple(tokens)


def _role_id(value: str) -> str:
    lowered = value.strip().lower().replace("_", "-")
    normalized = re.sub(r"[^a-z0-9-]+", "-", lowered)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "custom-role"


def _task_with_role_proposal_intent(task: Task) -> Task:
    return task.model_copy(
        update={
            "metadata": (
                *task.metadata,
                MetadataEntry(key=ROLE_PROPOSAL_INTENT_KEY, value=ROLE_PROPOSAL_INTENT),
            )
        }
    )
