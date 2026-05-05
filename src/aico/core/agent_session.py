"""Thin agent harness models for session and capability facades."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import Field

from aico.core.models import Capability, FrozenModel, MetadataEntry, Task, utc_now

SessionIdFactory = Callable[[], str]


class AgentSessionStatus(StrEnum):
    IDLE = "idle"
    BUSY = "busy"
    CLOSED = "closed"


class ProviderCapabilitySource(StrEnum):
    PROVIDER_CLI = "provider_cli"


class ProviderSessionMode(StrEnum):
    NEW = "new"
    RESUME = "resume"


class ProviderSessionRef(FrozenModel):
    provider_name: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    resume_hint: str | None = None
    initialized: bool = False


class ProviderTaskSession(FrozenModel):
    provider_name: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    mode: ProviderSessionMode


class AgentCard(FrozenModel):
    name: str = Field(min_length=1)
    adapter_name: str = Field(min_length=1)
    provider_name: str = Field(min_length=1)
    role_description: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    capabilities: tuple[Capability, ...] = ()
    tools_source: ProviderCapabilitySource = ProviderCapabilitySource.PROVIDER_CLI
    skills_source: ProviderCapabilitySource = ProviderCapabilitySource.PROVIDER_CLI
    session_features: tuple[str, ...] = ()


class AgentSession(FrozenModel):
    session_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    adapter_name: str = Field(min_length=1)
    provider_ref: ProviderSessionRef | None = None
    workspace: str | None = None
    status: AgentSessionStatus = AgentSessionStatus.IDLE
    active_task_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class InMemoryAgentSessionStore:
    """Keep AICO session refs without owning provider conversation history."""

    def __init__(self, session_id_factory: SessionIdFactory | None = None) -> None:
        self._session_id_factory = session_id_factory or _new_session_id
        self._sessions: dict[str, AgentSession] = {}
        self._active_sessions: dict[str, str] = {}

    def create(
        self,
        *,
        agent_name: str,
        adapter_name: str,
        provider_ref: ProviderSessionRef | None = None,
        workspace: str | None = None,
    ) -> AgentSession:
        session = AgentSession(
            session_id=self._session_id_factory(),
            agent_name=agent_name,
            adapter_name=adapter_name,
            provider_ref=provider_ref,
            workspace=workspace,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> AgentSession | None:
        return self._sessions.get(session_id)

    def active(self, scope_id: str) -> AgentSession | None:
        session_id = self._active_sessions.get(scope_id)
        if session_id is None:
            return None
        session = self._sessions.get(session_id)
        if session is None or session.status is AgentSessionStatus.CLOSED:
            self._active_sessions.pop(scope_id, None)
            return None
        return session

    def set_active(self, scope_id: str, session_id: str) -> AgentSession | None:
        session = self._sessions.get(session_id)
        if session is None or session.status is AgentSessionStatus.CLOSED:
            return None
        self._active_sessions[scope_id] = session_id
        return session

    def list(self, *, agent_name: str | None = None) -> tuple[AgentSession, ...]:
        sessions = tuple(self._sessions.values())
        if agent_name is None:
            return sessions
        return tuple(session for session in sessions if session.agent_name == agent_name)

    def bind_provider_ref(
        self,
        session_id: str,
        provider_ref: ProviderSessionRef,
    ) -> AgentSession | None:
        return self._update(session_id, provider_ref=provider_ref)

    def mark_provider_initialized(self, session_id: str) -> AgentSession | None:
        session = self._sessions.get(session_id)
        if session is None or session.provider_ref is None:
            return session
        provider_ref = session.provider_ref.model_copy(update={"initialized": True})
        return self._update(session_id, provider_ref=provider_ref)

    def mark_busy(self, session_id: str, task_id: str) -> AgentSession | None:
        return self._update(
            session_id,
            status=AgentSessionStatus.BUSY,
            active_task_id=task_id,
        )

    def mark_idle(self, session_id: str) -> AgentSession | None:
        return self._update(
            session_id,
            status=AgentSessionStatus.IDLE,
            active_task_id=None,
        )

    def close(self, session_id: str) -> AgentSession | None:
        for scope_id, active_session_id in tuple(self._active_sessions.items()):
            if active_session_id == session_id:
                self._active_sessions.pop(scope_id, None)
        return self._update(
            session_id,
            status=AgentSessionStatus.CLOSED,
            active_task_id=None,
        )

    def _update(self, session_id: str, **updates: object) -> AgentSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        updated = session.model_copy(update={**updates, "updated_at": utc_now()})
        self._sessions[session_id] = updated
        return updated


def _new_session_id() -> str:
    return str(uuid4())


_PROVIDER_NAME_KEY = "aico.provider_name"
_PROVIDER_SESSION_ID_KEY = "aico.provider_session_id"
_PROVIDER_SESSION_MODE_KEY = "aico.provider_session_mode"
_PROVIDER_SESSION_KEYS = {
    _PROVIDER_NAME_KEY,
    _PROVIDER_SESSION_ID_KEY,
    _PROVIDER_SESSION_MODE_KEY,
}


def task_with_provider_session(
    task: Task,
    provider_ref: ProviderSessionRef,
    mode: ProviderSessionMode,
) -> Task:
    metadata = tuple(entry for entry in task.metadata if entry.key not in _PROVIDER_SESSION_KEYS)
    return task.model_copy(
        update={
            "metadata": (
                *metadata,
                MetadataEntry(key=_PROVIDER_NAME_KEY, value=provider_ref.provider_name),
                MetadataEntry(key=_PROVIDER_SESSION_ID_KEY, value=provider_ref.session_id),
                MetadataEntry(key=_PROVIDER_SESSION_MODE_KEY, value=mode.value),
            )
        }
    )


def provider_session_from_task(task: Task) -> ProviderTaskSession | None:
    metadata = {entry.key: entry.value for entry in task.metadata}
    provider_name = metadata.get(_PROVIDER_NAME_KEY)
    session_id = metadata.get(_PROVIDER_SESSION_ID_KEY)
    mode = metadata.get(_PROVIDER_SESSION_MODE_KEY)
    if not isinstance(provider_name, str) or not isinstance(session_id, str):
        return None
    if not isinstance(mode, str):
        return None
    try:
        session_mode = ProviderSessionMode(mode)
    except ValueError:
        return None
    return ProviderTaskSession(
        provider_name=provider_name,
        session_id=session_id,
        mode=session_mode,
    )
