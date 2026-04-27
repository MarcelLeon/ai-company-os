import pytest

from aico.core import PersonaProfile, PersonaRegistry


def test_persona_registry_resolves_name_and_aliases() -> None:
    profile = PersonaProfile(
        name="reviewer",
        adapter_name="codex",
        role_instruction="Review only.",
        aliases=("codex", "code_reviewer"),
    )
    registry = PersonaRegistry([profile])

    assert registry.resolve("reviewer") == profile
    assert registry.resolve("codex") == profile
    assert registry.resolve("code-reviewer") == profile
    assert registry.resolve("missing") is None
    assert registry.names() == ("reviewer",)


def test_persona_registry_rejects_empty_and_duplicate_aliases() -> None:
    with pytest.raises(ValueError, match="at least one persona"):
        PersonaRegistry([])

    with pytest.raises(ValueError, match="unique"):
        PersonaRegistry(
            [
                PersonaProfile(
                    name="reviewer",
                    adapter_name="codex",
                    role_instruction="Review.",
                    aliases=("team",),
                ),
                PersonaProfile(
                    name="implementer",
                    adapter_name="claude-code",
                    role_instruction="Implement.",
                    aliases=("team",),
                ),
            ]
        )
