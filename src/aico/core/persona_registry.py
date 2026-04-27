"""Persona profiles that map human-friendly roles to adapters."""

from __future__ import annotations

from collections.abc import Iterable

from aico.core.models import PersonaProfile


class PersonaRegistry:
    """Resolve role/persona names without leaking role prompts into adapters."""

    def __init__(self, personas: Iterable[PersonaProfile]) -> None:
        self._personas = {persona.name: persona for persona in personas}
        if not self._personas:
            raise ValueError("at least one persona is required")

        self._aliases: dict[str, str] = {}
        for persona in self._personas.values():
            self._register_alias(persona.name, persona.name)
            for alias in persona.aliases:
                self._register_alias(alias, persona.name)

    def resolve(self, name: str) -> PersonaProfile | None:
        persona_name = self._aliases.get(_normalize(name))
        if persona_name is None:
            return None
        return self._personas[persona_name]

    def profiles(self) -> tuple[PersonaProfile, ...]:
        return tuple(self._personas.values())

    def names(self) -> tuple[str, ...]:
        return tuple(self._personas)

    def _register_alias(self, alias: str, persona_name: str) -> None:
        normalized = _normalize(alias)
        if not normalized:
            raise ValueError("persona aliases must not be empty")
        existing = self._aliases.get(normalized)
        if existing is not None and existing != persona_name:
            raise ValueError("persona aliases must be unique")
        self._aliases[normalized] = persona_name


def _normalize(value: str) -> str:
    return value.strip().lower().replace("_", "-")
