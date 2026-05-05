"""Helpers for IM-facing agent session commands."""

from __future__ import annotations

from aico.core.agent_directory import AgentDirectory
from aico.core.agent_session import (
    AgentCard,
    AgentSession,
    AgentSessionStatus,
    InMemoryAgentSessionStore,
    ProviderSessionRef,
)
from aico.core.models import IncomingMessage, MessageContent


def session_scope(message: IncomingMessage) -> str:
    return f"{message.channel_name}:{message.source.target_id}:{message.sender_id}"


def has_explicit_task_target(message: IncomingMessage) -> bool:
    if message.mentions:
        return True
    text = message.content.text.strip()
    first, _, _ = text.partition(" ")
    if first.startswith(("/", "@")):
        return True
    prefix, separator, _ = text.partition(":")
    return bool(separator and _is_route_prefix(prefix))


def sessions_message(sessions: tuple[AgentSession, ...]) -> str:
    if not sessions:
        return "No sessions"
    lines = ["Sessions:"]
    lines.extend(
        f"- {short_session_id(session.session_id)} [{session.agent_name}] {session.status.value}"
        for session in sessions
    )
    return "\n".join(lines)


def create_agent_session(
    store: InMemoryAgentSessionStore,
    directory: AgentDirectory,
    agent_name: str,
) -> AgentSession:
    card = directory.resolve(agent_name)
    return store.create(
        agent_name=agent_name,
        adapter_name=agent_name if card is None else card.adapter_name,
    )


def bind_provider_session(
    store: InMemoryAgentSessionStore,
    directory: AgentDirectory,
    message: IncomingMessage,
    payload: str,
) -> tuple[AgentSession | None, MessageContent]:
    target_ref, provider_session_id = bind_provider_ref_parts(payload)
    if provider_session_id is None:
        return None, MessageContent(
            text=(
                "Usage: /bind <session_id|agent> <provider_session_id>\n"
                "Or use /bind <provider_session_id> for the active session."
            )
        )

    session = _session_for_bind_target(store, directory, message, target_ref)
    if session is None:
        return None, MessageContent(text=f"Session or agent not found: {target_ref}")

    card = directory.resolve(session.agent_name)
    provider_name = provider_name_for_session(session, card)
    provider_ref = ProviderSessionRef(
        provider_name=provider_name,
        session_id=provider_session_id,
        resume_hint=f"{provider_name} resume {provider_session_id}",
        initialized=True,
    )
    bound = store.bind_provider_ref(session.session_id, provider_ref) or session
    store.set_active(session_scope(message), bound.session_id)
    return bound, MessageContent(
        text=(
            f"Provider session bound: {short_session_id(bound.session_id)} "
            f"[{bound.agent_name}]\n"
            f"provider: {provider_ref.provider_name}\n"
            "mode: resume"
        )
    )


def resolve_session_ref(
    sessions: tuple[AgentSession, ...],
    session_ref: str,
) -> tuple[AgentSession | None, str | None]:
    matches = [
        session
        for session in sessions
        if session.session_id.startswith(session_ref)
        and session.status is not AgentSessionStatus.CLOSED
    ]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        refs = ", ".join(short_session_id(session.session_id) for session in matches)
        return None, f"Multiple sessions match: {refs}"
    return None, f"Session not found: {session_ref}"


def bind_provider_ref_parts(payload: str) -> tuple[str | None, str | None]:
    parts = payload.split()
    if len(parts) == 1:
        return None, parts[0]
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, None


def provider_name_for_session(session: AgentSession, card: AgentCard | None) -> str:
    if session.provider_ref is not None:
        return session.provider_ref.provider_name
    if card is not None:
        return card.provider_name
    return session.adapter_name


def short_session_id(session_id: str) -> str:
    return session_id[:8]


def _session_for_bind_target(
    store: InMemoryAgentSessionStore,
    directory: AgentDirectory,
    message: IncomingMessage,
    target_ref: str | None,
) -> AgentSession | None:
    if target_ref is None:
        return store.active(session_scope(message))

    session, _ = resolve_session_ref(store.list(), target_ref)
    if session is not None:
        return session

    card = directory.resolve(target_ref)
    if card is None:
        return None
    session = store.create(agent_name=card.name, adapter_name=card.adapter_name)
    store.set_active(session_scope(message), session.session_id)
    return session


def _is_route_prefix(prefix: str) -> bool:
    return bool(prefix) and all(char.isalnum() or char in {"-", "_"} for char in prefix)
