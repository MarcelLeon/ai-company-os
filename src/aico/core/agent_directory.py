"""Agent capability facade built from personas and adapters."""

from __future__ import annotations

from dataclasses import dataclass

from aico.core.adapter_registry import AdapterRegistry
from aico.core.agent_session import AgentCard
from aico.core.persona_registry import PersonaRegistry


@dataclass(frozen=True)
class AgentDirectory:
    """Resolve user-facing agent names without owning provider tools or skills."""

    cards: tuple[AgentCard, ...] = ()

    def list(self) -> tuple[AgentCard, ...]:
        return self.cards

    def resolve(self, agent_ref: str) -> AgentCard | None:
        normalized_ref = _normalize(agent_ref)
        for card in self.cards:
            names = (card.name, card.adapter_name, *card.aliases)
            if any(_normalize(name) == normalized_ref for name in names):
                return card
        return None


def agent_cards_from_personas(
    persona_registry: PersonaRegistry,
    adapter_registry: AdapterRegistry,
) -> tuple[AgentCard, ...]:
    cards: list[AgentCard] = []
    for persona in persona_registry.profiles():
        adapter = adapter_registry.get(persona.adapter_name)
        capabilities = () if adapter is None else tuple(sorted(adapter.capabilities()))
        cards.append(
            AgentCard(
                name=persona.name,
                adapter_name=persona.adapter_name,
                provider_name=_provider_name(persona.adapter_name),
                role_description=_role_description(persona.role_instruction),
                aliases=persona.aliases,
                capabilities=capabilities,
                session_features=_session_features(persona.adapter_name),
            )
        )
    return tuple(cards)


def _provider_name(adapter_name: str) -> str:
    return adapter_name


def _role_description(role_instruction: str) -> str:
    return role_instruction.strip().splitlines()[0]


def _session_features(adapter_name: str) -> tuple[str, ...]:
    if adapter_name == "claude-code":
        return ("new", "resume")
    if adapter_name == "codex":
        return ("resume(bind)",)
    return ()


def _normalize(value: str) -> str:
    return value.strip().lower().replace("_", "-")
