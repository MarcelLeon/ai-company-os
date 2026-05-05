"""Local Phase 1 runtime wiring for Telegram -> Claude Code."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shlex
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from aico.adapter import AIAdapter
from aico.adapter.claude_code import ClaudeCodeAdapter
from aico.adapter.codex import CodexAdapter
from aico.channel.telegram import TelegramChannel
from aico.core import (
    AdapterRegistry,
    AgentDirectory,
    AgentSession,
    AssignmentProfile,
    CompanyAgentProfile,
    InMemoryAgentSessionStore,
    InMemoryAuditLog,
    JsonlAuditSink,
    MessageRouter,
    Orchestrator,
    PersonaProfile,
    PersonaRegistry,
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
    ProjectProfile,
    ProjectRoleProfile,
    ProviderSessionRef,
    RequesterOrListedApproverPolicy,
    RoleProfile,
    TaskBus,
    agent_cards_from_personas,
)


class Phase1Settings(BaseSettings):
    """Environment-backed settings for the Phase 1 local runtime."""

    model_config = SettingsConfigDict(env_prefix="AICO_", env_file=".env", extra="ignore")

    telegram_bot_token: str = Field(min_length=1)
    default_persona: str = Field(default="claude-code", min_length=1)
    telegram_poll_timeout_seconds: int = Field(default=30, gt=0)
    claude_command: str = Field(
        default="claude -p --output-format text --permission-mode bypassPermissions",
        min_length=1,
    )
    claude_working_directory: Path | None = None
    enable_codex_adapter: bool = False
    codex_command: str = Field(
        default="codex --ask-for-approval never exec --sandbox read-only --color never",
        min_length=1,
    )
    persona_config_path: Path | None = None
    project_config_path: Path | None = None
    approval_reviewer_ids: str = ""
    audit_log_path: Path | None = None
    log_level: str = "INFO"
    log_path: Path | None = Path("logs/aico.log")

    @field_validator("log_path", mode="before")
    @classmethod
    def empty_log_path_disables_file_logging(cls, value: object) -> object:
        return None if value == "" else value

    def claude_command_tuple(self) -> tuple[str, ...]:
        return _split_command(self.claude_command)

    def codex_command_tuple(self) -> tuple[str, ...]:
        return _split_command(self.codex_command)

    def approval_reviewer_id_tuple(self) -> tuple[str, ...]:
        return tuple(
            reviewer_id.strip()
            for reviewer_id in self.approval_reviewer_ids.split(",")
            if reviewer_id.strip()
        )


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
    session_store: InMemoryAgentSessionStore
    project_directory: ProjectAssignmentDirectory
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
    agent_directory = AgentDirectory(agent_cards_from_personas(persona_registry, registry))
    project_directory = _load_project_directory(settings, agent_directory, registry)
    session_store = InMemoryAgentSessionStore()
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona=settings.default_persona),
        task_bus=TaskBus(
            registry,
            persona_registry=persona_registry,
            audit_log=_build_audit_log(settings),
            approval_policy=RequesterOrListedApproverPolicy(settings.approval_reviewer_id_tuple()),
        ),
        session_store=session_store,
        provider_session_factory=_provider_session_factory(persona_registry),
        agent_directory=agent_directory,
        project_directory=project_directory,
    )
    return Phase1Runtime(
        channel=channel,
        adapter=adapter,
        registry=registry,
        persona_registry=persona_registry,
        session_store=session_store,
        project_directory=project_directory,
        orchestrator=orchestrator,
    )


async def run_phase1(settings: Phase1Settings) -> None:
    configure_logging(settings)
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


def configure_logging(settings: Phase1Settings) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if settings.log_path is not None:
        settings.log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(settings.log_path, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
        force=True,
    )
    logging.getLogger(__name__).info(
        "AICO runtime logging configured: level=%s path=%s",
        settings.log_level.upper(),
        settings.log_path,
    )


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
                "and clear handoff notes. When you need reviewer help, emit a line "
                "like '@reviewer: inspect this implementation'."
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


def _load_project_directory(
    settings: Phase1Settings,
    agent_directory: AgentDirectory,
    registry: AdapterRegistry,
) -> ProjectAssignmentDirectory:
    if settings.project_config_path is None:
        config = _default_project_assignment_config(
            agent_directory=agent_directory,
            repo=settings.claude_working_directory or Path.cwd(),
        )
    else:
        raw = json.loads(settings.project_config_path.read_text(encoding="utf-8"))
        config = ProjectAssignmentConfig.model_validate(raw)
    _validate_project_assignments(config, agent_directory, registry)
    return ProjectAssignmentDirectory(config)


def _default_project_assignment_config(
    *,
    agent_directory: AgentDirectory,
    repo: Path,
) -> ProjectAssignmentConfig:
    agents: dict[str, CompanyAgentProfile] = {}
    assignments: list[AssignmentProfile] = []
    roles = _default_roles()
    for card in agent_directory.list():
        agent_id = card.aliases[0] if card.aliases else card.name
        agents[agent_id] = CompanyAgentProfile(
            id=agent_id,
            provider=card.adapter_name,
            title=card.role_description,
            capabilities=card.capabilities,
        )
        assignments.append(
            AssignmentProfile(
                project="aico",
                agent=agent_id,
                role=card.name,
                seat=f"aico-{card.name}",
                session_policy=_default_assignment_session_policy(card.adapter_name),
                risk_policy=_default_assignment_risk_policy(card.adapter_name),
            )
        )
    default_assignment = assignments[0].seat if assignments else None
    return ProjectAssignmentConfig(
        agents=agents,
        roles=roles,
        projects={
            "aico": ProjectProfile(
                id="aico",
                name="AI Company OS",
                repo=str(repo),
                north_star="NORTH_STAR.md",
                status_doc="STATUS.md",
                journal="docs/journal/ROUNDS.md",
                blockers_doc="docs/journal/BLOCKERS.md",
                pitfalls_doc="docs/journal/PITFALLS.md",
                current_phase="Phase 5 - AI 间协作",
                default_role="implementer",
                default_assignment=default_assignment,
                roles={
                    "implementer": ProjectRoleProfile(role="implementer"),
                    "reviewer": ProjectRoleProfile(role="reviewer"),
                },
            )
        },
        assignments=tuple(assignments),
    )


def _default_roles() -> dict[str, RoleProfile]:
    return {
        "implementer": RoleProfile(
            id="implementer",
            title="Implementation Lead",
            summary="Implement features, fix bugs, update tests, and keep project status current.",
            inline_prompt=(
                "Work in small, reviewable steps. Keep tests and project handoff docs current."
            ),
            default_permissions=("read_repo", "write_code", "run_tests", "write_docs"),
            approval_required=("shell_exec", "destructive"),
        ),
        "reviewer": RoleProfile(
            id="reviewer",
            title="Review Lead",
            summary="Review design risk, code quality, test gaps, and maintainability.",
            inline_prompt=(
                "Prioritize concrete bugs, design risks, missing tests, and maintainability."
            ),
            default_permissions=("read_repo", "read_docs", "read_audit"),
        ),
        "tester": RoleProfile(
            id="tester",
            title="Test Lead",
            summary="Design test strategy, add test cases, run verification, and explain failures.",
            default_permissions=("read_repo", "run_tests", "write_tests"),
        ),
        "pm": RoleProfile(
            id="pm",
            title="Project Manager",
            summary="Break down work, summarize progress, maintain reports, and surface blockers.",
            default_permissions=("read_docs", "write_docs"),
        ),
        "architect": RoleProfile(
            id="architect",
            title="Architect",
            summary="Evaluate module boundaries, ADRs, abstractions, and evolution plans.",
            default_permissions=("read_repo", "read_docs", "write_docs"),
        ),
        "security": RoleProfile(
            id="security",
            title="Security Reviewer",
            summary="Review permissions, secrets, dangerous operations, and supply-chain risk.",
            default_permissions=("read_repo", "read_docs"),
        ),
        "docs": RoleProfile(
            id="docs",
            title="Documentation Lead",
            summary="Maintain README, playbooks, handoff notes, and changelog entries.",
            default_permissions=("read_docs", "write_docs"),
        ),
        "ops": RoleProfile(
            id="ops",
            title="Operations Lead",
            summary="Handle startup, deployment, logs, alerts, and incident troubleshooting.",
            default_permissions=("read_repo", "read_docs", "run_tests"),
            approval_required=("shell_exec", "destructive"),
        ),
        "analyst": RoleProfile(
            id="analyst",
            title="Analyst",
            summary=(
                "Analyze markets, competitors, requirements, and data into structured findings."
            ),
            default_permissions=("read_docs",),
        ),
        "designer": RoleProfile(
            id="designer",
            title="Product Designer",
            summary="Design user flows, command semantics, and information architecture.",
            default_permissions=("read_docs", "write_docs"),
        ),
    }


def _default_assignment_session_policy(adapter_name: str) -> str:
    if adapter_name == "codex":
        return "bind_or_resume"
    return "project_scoped"


def _default_assignment_risk_policy(adapter_name: str) -> str:
    if adapter_name == "codex":
        return "read_only"
    return "approval_required"


def _validate_project_assignments(
    config: ProjectAssignmentConfig,
    agent_directory: AgentDirectory,
    registry: AdapterRegistry,
) -> None:
    for agent_id, agent in config.agents.items():
        if registry.get(agent.provider) is None:
            raise ValueError(f"agent {agent_id} references unknown provider {agent.provider}")
    for assignment in (*config.assignments, *config.appointments):
        if agent_directory.resolve(assignment.agent) is None:
            raise ValueError(
                f"assignment {assignment.seat} references unknown routed agent {assignment.agent}"
            )


def _validate_personas(
    personas: tuple[PersonaProfile, ...],
    registry: AdapterRegistry,
) -> None:
    for persona in personas:
        if registry.get(persona.adapter_name) is None:
            raise ValueError(
                f"persona {persona.name} references unknown adapter {persona.adapter_name}"
            )


def _build_audit_log(settings: Phase1Settings) -> InMemoryAuditLog:
    if settings.audit_log_path is None:
        return InMemoryAuditLog()
    return InMemoryAuditLog(sinks=(JsonlAuditSink(settings.audit_log_path),))


def _provider_session_factory(
    persona_registry: PersonaRegistry,
) -> Callable[[AgentSession], ProviderSessionRef | None]:
    def factory(session: AgentSession) -> ProviderSessionRef | None:
        persona = persona_registry.resolve(session.agent_name)
        adapter_name = session.agent_name if persona is None else persona.adapter_name
        if adapter_name != "claude-code":
            return None
        return ProviderSessionRef(
            provider_name="claude-code",
            session_id=session.session_id,
            resume_hint=f"claude --resume {session.session_id}",
        )

    return factory
