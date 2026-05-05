from collections.abc import AsyncIterator

from aico.core import (
    AckStatus,
    AdapterRegistry,
    AdapterStatus,
    AgentCard,
    AgentDirectory,
    AgentSessionStatus,
    Capability,
    HealthStatus,
    InMemoryAgentSessionStore,
    OutputType,
    PersonaProfile,
    PersonaRegistry,
    ProviderCapabilitySource,
    ProviderSessionMode,
    ProviderSessionRef,
    Task,
    TaskAck,
    TaskOutput,
    agent_cards_from_personas,
    provider_session_from_task,
    task_with_provider_session,
)


def test_agent_card_declares_provider_owned_tools_and_skills() -> None:
    card = AgentCard(
        name="claude",
        adapter_name="claude-code",
        provider_name="claude-code",
        role_description="Implementation agent",
        capabilities=(Capability.CODE_EDIT, Capability.SHELL_EXEC),
        session_features=("resume", "fork"),
    )

    assert card.tools_source is ProviderCapabilitySource.PROVIDER_CLI
    assert card.skills_source is ProviderCapabilitySource.PROVIDER_CLI
    assert card.session_features == ("resume", "fork")


def test_agent_session_store_tracks_provider_session_refs() -> None:
    ids = iter(("aico-session-1",))
    store = InMemoryAgentSessionStore(session_id_factory=lambda: next(ids))
    provider_ref = ProviderSessionRef(
        provider_name="claude-code",
        session_id="provider-session-1",
        resume_hint="claude --resume provider-session-1",
    )

    session = store.create(
        agent_name="claude",
        adapter_name="claude-code",
        provider_ref=provider_ref,
        workspace="/repo",
    )

    assert session.session_id == "aico-session-1"
    assert session.provider_ref == provider_ref
    assert store.get("aico-session-1") == session
    assert store.list(agent_name="claude") == (session,)


def test_agent_session_store_updates_runtime_state_without_losing_provider_ref() -> None:
    store = InMemoryAgentSessionStore(session_id_factory=lambda: "aico-session-1")
    provider_ref = ProviderSessionRef(provider_name="codex", session_id="provider-session-1")
    session = store.create(
        agent_name="reviewer",
        adapter_name="codex",
        provider_ref=provider_ref,
    )

    busy = store.mark_busy(session.session_id, "task-1")
    idle = store.mark_idle(session.session_id)
    closed = store.close(session.session_id)

    assert busy is not None
    assert busy.status is AgentSessionStatus.BUSY
    assert busy.active_task_id == "task-1"
    assert idle is not None
    assert idle.status is AgentSessionStatus.IDLE
    assert idle.active_task_id is None
    assert closed is not None
    assert closed.status is AgentSessionStatus.CLOSED
    assert closed.provider_ref == provider_ref


def test_agent_session_store_tracks_active_session_by_scope() -> None:
    store = InMemoryAgentSessionStore(session_id_factory=lambda: "aico-session-1")
    session = store.create(agent_name="claude", adapter_name="claude-code")

    active = store.set_active("telegram:chat-1:user-1", session.session_id)

    assert active == session
    assert store.active("telegram:chat-1:user-1") == session

    store.close(session.session_id)

    assert store.active("telegram:chat-1:user-1") is None


def test_agent_session_store_marks_provider_ref_initialized() -> None:
    store = InMemoryAgentSessionStore(session_id_factory=lambda: "aico-session-1")
    session = store.create(
        agent_name="claude",
        adapter_name="claude-code",
        provider_ref=ProviderSessionRef(provider_name="claude-code", session_id="provider-1"),
    )

    updated = store.mark_provider_initialized(session.session_id)

    assert updated is not None
    assert updated.provider_ref is not None
    assert updated.provider_ref.initialized


def test_task_provider_session_metadata_roundtrips() -> None:
    task = Task(
        task_id="task-1",
        payload="continue",
        requester_id="user-1",
        target_persona="claude",
    )
    provider_ref = ProviderSessionRef(
        provider_name="claude-code",
        session_id="provider-session-1",
    )

    updated = task_with_provider_session(task, provider_ref, ProviderSessionMode.RESUME)

    provider_session = provider_session_from_task(updated)
    assert provider_session is not None
    assert provider_session.provider_name == "claude-code"
    assert provider_session.session_id == "provider-session-1"
    assert provider_session.mode is ProviderSessionMode.RESUME


def test_agent_directory_builds_cards_from_personas_and_adapters() -> None:
    adapter = _DirectoryAdapter()
    registry = AdapterRegistry([adapter])
    personas = PersonaRegistry(
        [
            PersonaProfile(
                name="implementer",
                adapter_name="claude-code",
                role_instruction="Role: implementer.\nMore detail",
                aliases=("claude",),
            )
        ]
    )

    directory = AgentDirectory(agent_cards_from_personas(personas, registry))
    card = directory.resolve("claude")

    assert card is not None
    assert card.name == "implementer"
    assert card.adapter_name == "claude-code"
    assert card.aliases == ("claude",)
    assert card.role_description == "Role: implementer."
    assert card.capabilities == (Capability.CODE_EDIT, Capability.STREAM_OUTPUT)
    assert card.session_features == ("new", "resume")


class _DirectoryAdapter:
    @property
    def name(self) -> str:
        return "claude-code"

    def capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.CODE_EDIT, Capability.STREAM_OUTPUT})

    async def receive_task(self, task: Task) -> TaskAck:
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        _ = task_id
        return _empty_outputs()

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        _ = task_id

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


async def _empty_outputs() -> AsyncIterator[TaskOutput]:
    if False:
        yield TaskOutput(task_id="unused", sequence=0, type=OutputType.DONE, content="")
