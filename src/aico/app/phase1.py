"""Local Phase 1 runtime wiring for Telegram -> Claude Code."""

from __future__ import annotations

import argparse
import asyncio
import json
import shlex
from dataclasses import dataclass
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aico.adapter import AIAdapter
from aico.adapter.claude_code import ClaudeCodeAdapter
from aico.adapter.codex import CodexAdapter
from aico.channel.telegram import TelegramChannel
from aico.core import (
    AdapterRegistry,
    MessageRouter,
    Orchestrator,
    PersonaProfile,
    PersonaRegistry,
    TaskBus,
)


class Phase1Settings(BaseSettings):
    """Environment-backed settings for the Phase 1 local runtime."""

    model_config = SettingsConfigDict(env_prefix="AICO_", env_file=".env", extra="ignore")

    telegram_bot_token: str = Field(min_length=1)
    default_persona: str = Field(default="claude-code", min_length=1)
    telegram_poll_timeout_seconds: int = Field(default=30, gt=0)
    claude_command: str = Field(default="claude -p --output-format text", min_length=1)
    claude_working_directory: Path | None = None
    enable_codex_adapter: bool = False
    codex_command: str = Field(
        default="codex --ask-for-approval never exec --sandbox read-only --color never",
        min_length=1,
    )
    persona_config_path: Path | None = None

    def claude_command_tuple(self) -> tuple[str, ...]:
        return _split_command(self.claude_command)

    def codex_command_tuple(self) -> tuple[str, ...]:
        return _split_command(self.codex_command)


def _split_command(command_text: str) -> tuple[str, ...]:
    command = tuple(shlex.split(command_text))
    if not command:
        raise ValueError("command must not be empty")
    return command


@dataclass
class Phase1Runtime:
    channel: TelegramChannel
    adapter: ClaudeCodeAdapter
    registry: AdapterRegistry
    persona_registry: PersonaRegistry
    orchestrator: Orchestrator

    async def start(self) -> None:
        self.orchestrator.bind()
        await self.channel.start()

    async def stop(self) -> None:
        await self.channel.stop()


def build_phase1_runtime(settings: Phase1Settings) -> Phase1Runtime:
    channel = TelegramChannel(
        settings.telegram_bot_token,
        poll_timeout_seconds=settings.telegram_poll_timeout_seconds,
    )
    adapter = ClaudeCodeAdapter(
        command=settings.claude_command_tuple(),
        cwd=settings.claude_working_directory,
    )
    adapters: list[AIAdapter] = [adapter]
    if settings.enable_codex_adapter:
        adapters.append(
            CodexAdapter(
                command=settings.codex_command_tuple(),
                cwd=settings.claude_working_directory,
            )
        )
    registry = AdapterRegistry(
        adapters,
        default_adapter_name=adapter.name,
        aliases={"claude": adapter.name},
    )
    personas = _load_personas(settings)
    _validate_personas(personas, registry)
    persona_registry = PersonaRegistry(personas)
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona=settings.default_persona),
        task_bus=TaskBus(registry, persona_registry=persona_registry),
    )
    return Phase1Runtime(
        channel=channel,
        adapter=adapter,
        registry=registry,
        persona_registry=persona_registry,
        orchestrator=orchestrator,
    )


async def run_phase1(settings: Phase1Settings) -> None:
    runtime = build_phase1_runtime(settings)
    await runtime.start()
    try:
        await _wait_forever()
    finally:
        await runtime.stop()


def main() -> None:
    _parse_args()
    try:
        asyncio.run(run_phase1(Phase1Settings()))  # type: ignore[call-arg]
    except KeyboardInterrupt:
        return


def _parse_args() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Phase 1 Telegram -> Claude Code local runtime.",
    )
    parser.parse_args()


async def _wait_forever() -> None:
    while True:
        await asyncio.sleep(3600)


def _default_personas(*, enable_codex: bool) -> tuple[PersonaProfile, ...]:
    personas = [
        PersonaProfile(
            name="implementer",
            adapter_name="claude-code",
            aliases=("claude", "claude-code"),
            role_instruction=(
                "Role: implementer. Focus on safe code changes, small steps, tests, "
                "and clear handoff notes."
            ),
        )
    ]
    if enable_codex:
        personas.append(
            PersonaProfile(
                name="reviewer",
                adapter_name="codex",
                aliases=("codex",),
                role_instruction=(
                    "Role: reviewer. Focus on read-only analysis, risks, missing tests, "
                    "and concise findings."
                ),
            )
        )
    return tuple(personas)


def _load_personas(settings: Phase1Settings) -> tuple[PersonaProfile, ...]:
    if settings.persona_config_path is None:
        return _default_personas(enable_codex=settings.enable_codex_adapter)

    raw = json.loads(settings.persona_config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("persona config must be a JSON array")
    return tuple(PersonaProfile.model_validate(item) for item in raw)


def _validate_personas(
    personas: tuple[PersonaProfile, ...],
    registry: AdapterRegistry,
) -> None:
    for persona in personas:
        if registry.get(persona.adapter_name) is None:
            raise ValueError(
                f"persona {persona.name} references unknown adapter {persona.adapter_name}"
            )
