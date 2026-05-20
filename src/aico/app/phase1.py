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
from typing import Literal

import httpx
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from aico.adapter import AIAdapter
from aico.adapter.claude_code import ClaudeCodeAdapter
from aico.adapter.codeflicker import CodeFlickerAdapter
from aico.adapter.codex import CodexAdapter
from aico.adapter.cursor import CursorAdapter
from aico.adapter.gemini import GeminiAdapter
from aico.adapter.trae import TraeAdapter
from aico.channel import IMChannel
from aico.channel.feishu import FeishuChannel
from aico.channel.telegram import TelegramChannel
from aico.core import (
    AdapterRegistry,
    AgentCard,
    AgentDirectory,
    AgentSession,
    AssignmentProfile,
    CompanyAgentProfile,
    InMemoryAgentSessionStore,
    InMemoryAuditLog,
    JsonlAuditSink,
    JsonlMemoryStore,
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
    RoleScope,
    TaskBus,
    agent_cards_from_personas,
    read_jsonl_audit_events,
)


class Phase1Settings(BaseSettings):
    """Environment-backed settings for the Phase 1 local runtime."""

    model_config = SettingsConfigDict(env_prefix="AICO_", env_file=".env", extra="ignore")

    channel: Literal["telegram", "feishu"] = "telegram"
    telegram_bot_token: str | None = Field(default=None, min_length=1)
    default_persona: str = Field(default="claude-code", min_length=1)
    telegram_poll_timeout_seconds: int = Field(default=30, gt=0)
    feishu_app_id: str | None = Field(default=None, min_length=1)
    feishu_app_secret: str | None = Field(default=None, min_length=1)
    feishu_verification_token: str | None = Field(default=None, min_length=1)
    feishu_api_base_url: str = Field(default="https://open.feishu.cn", min_length=1)
    feishu_webhook_host: str = Field(default="0.0.0.0", min_length=1)
    feishu_webhook_port: int = Field(default=8080, gt=0)
    feishu_event_path: str = Field(default="/feishu/events", min_length=1)
    claude_command: str = Field(
        default="claude -p --output-format text --permission-mode bypassPermissions",
        min_length=1,
    )
    claude_working_directory: Path | None = None
    claude_max_concurrent_tasks: int = Field(default=5, gt=0)
    enable_codex_adapter: bool = False
    codex_command: str = Field(
        default="codex --ask-for-approval never exec --sandbox read-only --color never",
        min_length=1,
    )
    codex_output_idle_timeout_seconds: float = Field(default=300.0, gt=0)
    codex_max_concurrent_tasks: int = Field(default=5, gt=0)
    enable_cursor_adapter: bool = False
    cursor_command: str = Field(
        default="cursor-agent -p --force --output-format text",
        min_length=1,
    )
    cursor_output_idle_timeout_seconds: float = Field(default=300.0, gt=0)
    cursor_max_concurrent_tasks: int = Field(default=5, gt=0)
    enable_codeflicker_adapter: bool = False
    codeflicker_command: str = Field(
        default="flickcli -q --approval-mode yolo --output-format text",
        min_length=1,
    )
    codeflicker_output_idle_timeout_seconds: float = Field(default=300.0, gt=0)
    codeflicker_max_concurrent_tasks: int = Field(default=5, gt=0)
    enable_trae_adapter: bool = False
    trae_command: str = Field(default="trae-cli --print --yolo", min_length=1)
    trae_output_idle_timeout_seconds: float = Field(default=300.0, gt=0)
    trae_max_concurrent_tasks: int = Field(default=5, gt=0)
    enable_gemini_adapter: bool = False
    gemini_command: str = Field(
        default="gemini --approval-mode yolo --output-format text",
        min_length=1,
    )
    gemini_output_idle_timeout_seconds: float = Field(default=300.0, gt=0)
    gemini_max_concurrent_tasks: int = Field(default=5, gt=0)
    persona_config_path: Path | None = None
    project_config_path: Path | None = None
    approval_reviewer_ids: str = ""
    audit_log_path: Path | None = None
    memory_path: Path | None = None
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

    def cursor_command_tuple(self) -> tuple[str, ...]:
        return _split_command(self.cursor_command)

    def codeflicker_command_tuple(self) -> tuple[str, ...]:
        return _split_command(self.codeflicker_command)

    def trae_command_tuple(self) -> tuple[str, ...]:
        return _split_command(self.trae_command)

    def gemini_command_tuple(self) -> tuple[str, ...]:
        return _split_command(self.gemini_command)

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
    channel: IMChannel
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


def build_phase1_runtime(
    settings: Phase1Settings,
    *,
    feishu_client: httpx.AsyncClient | None = None,
) -> Phase1Runtime:
    channel = _build_channel(settings, feishu_client=feishu_client)
    adapter = ClaudeCodeAdapter(
        command=settings.claude_command_tuple(),
        cwd=settings.claude_working_directory,
        max_concurrent_tasks=settings.claude_max_concurrent_tasks,
    )
    adapters: list[AIAdapter] = [adapter]
    if settings.enable_codex_adapter:
        adapters.append(
            CodexAdapter(
                command=settings.codex_command_tuple(),
                cwd=settings.claude_working_directory,
                output_idle_timeout_seconds=settings.codex_output_idle_timeout_seconds,
                max_concurrent_tasks=settings.codex_max_concurrent_tasks,
            )
        )
    if settings.enable_cursor_adapter:
        adapters.append(
            CursorAdapter(
                command=settings.cursor_command_tuple(),
                cwd=settings.claude_working_directory,
                output_idle_timeout_seconds=settings.cursor_output_idle_timeout_seconds,
                max_concurrent_tasks=settings.cursor_max_concurrent_tasks,
            )
        )
    if settings.enable_codeflicker_adapter:
        adapters.append(
            CodeFlickerAdapter(
                command=settings.codeflicker_command_tuple(),
                cwd=settings.claude_working_directory,
                output_idle_timeout_seconds=settings.codeflicker_output_idle_timeout_seconds,
                max_concurrent_tasks=settings.codeflicker_max_concurrent_tasks,
            )
        )
    if settings.enable_trae_adapter:
        adapters.append(
            TraeAdapter(
                command=settings.trae_command_tuple(),
                cwd=settings.claude_working_directory,
                output_idle_timeout_seconds=settings.trae_output_idle_timeout_seconds,
                max_concurrent_tasks=settings.trae_max_concurrent_tasks,
            )
        )
    if settings.enable_gemini_adapter:
        adapters.append(
            GeminiAdapter(
                command=settings.gemini_command_tuple(),
                cwd=settings.claude_working_directory,
                output_idle_timeout_seconds=settings.gemini_output_idle_timeout_seconds,
                max_concurrent_tasks=settings.gemini_max_concurrent_tasks,
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
        memory_store=JsonlMemoryStore(settings.memory_path) if settings.memory_path else None,
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


def _build_channel(
    settings: Phase1Settings,
    *,
    feishu_client: httpx.AsyncClient | None = None,
) -> IMChannel:
    match settings.channel:
        case "telegram":
            if settings.telegram_bot_token is None:
                raise ValueError("AICO_TELEGRAM_BOT_TOKEN is required when AICO_CHANNEL=telegram")
            return TelegramChannel(
                settings.telegram_bot_token,
                poll_timeout_seconds=settings.telegram_poll_timeout_seconds,
            )
        case "feishu":
            if settings.feishu_app_id is None:
                raise ValueError("AICO_FEISHU_APP_ID is required when AICO_CHANNEL=feishu")
            if settings.feishu_app_secret is None:
                raise ValueError("AICO_FEISHU_APP_SECRET is required when AICO_CHANNEL=feishu")
            return FeishuChannel(
                app_id=settings.feishu_app_id,
                app_secret=settings.feishu_app_secret,
                verification_token=settings.feishu_verification_token,
                api_base_url=settings.feishu_api_base_url,
                client=feishu_client,
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
        asyncio.run(run_phase1(Phase1Settings()))
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
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger(__name__).info(
        "AICO runtime logging configured: level=%s path=%s",
        settings.log_level.upper(),
        settings.log_path,
    )


async def _wait_forever() -> None:
    while True:
        await asyncio.sleep(3600)


def _default_personas(settings: Phase1Settings) -> tuple[PersonaProfile, ...]:
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
    if settings.enable_codex_adapter:
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
    if settings.enable_cursor_adapter:
        personas.append(
            PersonaProfile(
                name="cursor",
                adapter_name="cursor",
                aliases=("cursor-agent",),
                role_instruction=(
                    "Role: cursor. Use Cursor Agent CLI for codebase analysis, "
                    "implementation, review, and safe command execution after AICO approval."
                ),
            )
        )
    if settings.enable_codeflicker_adapter:
        personas.append(
            PersonaProfile(
                name="codeflicker",
                adapter_name="codeflicker",
                aliases=("flicker", "flickcli"),
                role_instruction=(
                    "Role: codeflicker. Use CodeFlicker CLI for codebase analysis, "
                    "implementation, review, and safe command execution after AICO approval."
                ),
            )
        )
    if settings.enable_trae_adapter:
        personas.append(
            PersonaProfile(
                name="trae",
                adapter_name="trae",
                aliases=("trae-cli", "trae-agent"),
                role_instruction=(
                    "Role: trae. Use Trae CLI for implementation, debugging, refactoring, "
                    "tests, and transparent engineering task execution after AICO approval."
                ),
            )
        )
    if settings.enable_gemini_adapter:
        personas.append(
            PersonaProfile(
                name="gemini",
                adapter_name="gemini",
                aliases=("gemini-cli",),
                role_instruction=(
                    "Role: gemini. Use Gemini CLI for broad codebase reasoning, "
                    "implementation, review, and verification after AICO approval."
                ),
            )
        )
    return tuple(personas)


def _load_personas(settings: Phase1Settings) -> tuple[PersonaProfile, ...]:
    if settings.persona_config_path is None:
        return _default_personas(settings)

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
        agent_id = _default_agent_id(card)
        agents[agent_id] = CompanyAgentProfile(
            id=agent_id,
            provider=card.adapter_name,
            title=card.role_description,
            capabilities=card.capabilities,
            max_concurrent_tasks=card.max_concurrent_tasks,
            recommended_max_appointments=card.max_concurrent_tasks,
        )
        assignments.append(
            AssignmentProfile(
                project="aico",
                agent=agent_id,
                role=card.name,
                seat=f"aico-{card.name}",
                permissions=roles.get(
                    card.name,
                    RoleProfile(id=card.name, title=card.name),
                ).default_permissions,
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
                current_phase="Phase 6 - 可观测看板",
                default_role="implementer",
                default_assignment=default_assignment,
                roles={role_id: ProjectRoleProfile(role=role_id) for role_id in roles},
            )
        },
        assignments=tuple(assignments),
    )


def _default_roles() -> dict[str, RoleProfile]:
    return {
        **_delivery_roles(),
        **_governance_roles(),
        **_support_roles(),
    }


def _default_agent_id(card: AgentCard) -> str:
    if card.name in {"implementer", "reviewer"} and card.aliases:
        return card.aliases[0]
    return card.name


def _delivery_roles() -> dict[str, RoleProfile]:
    return {
        "pm": RoleProfile(
            id="pm",
            title="Project Manager",
            summary=(
                "Own scope, milestones, priorities, handoffs, status reports, and blocker "
                "escalation."
            ),
            inline_prompt=(
                "Turn broad goals into ordered work, define acceptance criteria, surface "
                "tradeoffs, and keep STATUS/ROUNDS-style handoffs crisp."
            ),
            default_permissions=(RoleScope.DOCS, RoleScope.AUDIT),
        ),
        "implementer": RoleProfile(
            id="implementer",
            title="Implementation Lead",
            summary="Implement features, fix bugs, update tests, and keep project status current.",
            inline_prompt=(
                "Work in small, reviewable steps. Keep tests and project handoff docs current."
            ),
            default_permissions=(RoleScope.CODE, RoleScope.TESTS, RoleScope.DOCS),
            approval_required=("shell_exec", "destructive"),
        ),
        "reviewer": RoleProfile(
            id="reviewer",
            title="Review Lead",
            summary="Review design risk, code quality, test gaps, and maintainability.",
            inline_prompt=(
                "Prioritize concrete bugs, design risks, missing tests, and maintainability."
            ),
            default_permissions=(RoleScope.CODE, RoleScope.DOCS, RoleScope.AUDIT),
        ),
        "tester": RoleProfile(
            id="tester",
            title="Test Lead",
            summary=(
                "Design normal-path and regression tests, add focused cases, run verification, "
                "and explain failures."
            ),
            default_permissions=(RoleScope.CODE, RoleScope.TESTS),
        ),
        "golden-tester": RoleProfile(
            id="golden-tester",
            title="Golden Path Tester",
            summary=(
                "Validate end-to-end dogfooding flows and user-visible acceptance paths, "
                "separate from ordinary unit/regression testing."
            ),
            inline_prompt=(
                "Act like the final acceptance gate. Reproduce the user's real workflow, "
                "check command UX, state transitions, observability, and rollback notes."
            ),
            default_permissions=(RoleScope.CODE, RoleScope.TESTS, RoleScope.AUDIT),
        ),
    }


def _governance_roles() -> dict[str, RoleProfile]:
    return {
        "senior-architect": RoleProfile(
            id="senior-architect",
            title="Senior Architect",
            summary=(
                "Review architecture, module boundaries, protocol fit, extension paths, and "
                "long-term maintainability."
            ),
            inline_prompt=(
                "Challenge architecture with concrete alternatives. Prefer protocol-first, "
                "adapterized, observable, pluggable designs and explain why rejected options "
                "were not chosen."
            ),
            default_permissions=(RoleScope.CODE, RoleScope.DOCS, RoleScope.AUDIT),
        ),
        "security": RoleProfile(
            id="security",
            title="Security Reviewer",
            summary="Review permissions, secrets, dangerous operations, and supply-chain risk.",
            default_permissions=(RoleScope.CODE, RoleScope.AUDIT),
        ),
        "market-risk": RoleProfile(
            id="market-risk",
            title="Market Risk Analyst",
            summary=(
                "Evaluate user value, adoption friction, competitive risk, and whether a "
                "feature strengthens the virtual-company product wedge."
            ),
            inline_prompt=(
                "Be commercially skeptical. Focus on dogfooding value, differentiation, "
                "setup friction, and opportunity cost."
            ),
            default_permissions=(RoleScope.DOCS,),
        ),
        "legal-compliance": RoleProfile(
            id="legal-compliance",
            title="Legal and Compliance Reviewer",
            summary=(
                "Review platform terms, privacy, data retention, approval/audit posture, and "
                "safe integration boundaries."
            ),
            inline_prompt=(
                "Flag legal, compliance, privacy, and platform policy risks. Suggest a "
                "minimal compliant path instead of blocking by default."
            ),
            default_permissions=(RoleScope.DOCS, RoleScope.AUDIT),
        ),
    }


def _support_roles() -> dict[str, RoleProfile]:
    return {
        "docs": RoleProfile(
            id="docs",
            title="Documentation Lead",
            summary="Maintain README, playbooks, handoff notes, and changelog entries.",
            default_permissions=(RoleScope.DOCS,),
        ),
        "ops": RoleProfile(
            id="ops",
            title="Operations Lead",
            summary="Handle startup, deployment, logs, alerts, and incident troubleshooting.",
            default_permissions=(RoleScope.CODE, RoleScope.TESTS, RoleScope.OPS, RoleScope.AUDIT),
            approval_required=("shell_exec", "destructive"),
        ),
        "analyst": RoleProfile(
            id="analyst",
            title="Analyst",
            summary=(
                "Analyze markets, competitors, requirements, and data into structured findings."
            ),
            default_permissions=(RoleScope.DOCS,),
        ),
        "designer": RoleProfile(
            id="designer",
            title="Product Designer",
            summary="Design user flows, command semantics, and information architecture.",
            default_permissions=(RoleScope.DOCS,),
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
    return InMemoryAuditLog(
        sinks=(JsonlAuditSink(settings.audit_log_path),),
        initial_events=read_jsonl_audit_events(settings.audit_log_path),
    )


def _provider_session_factory(
    persona_registry: PersonaRegistry,
) -> Callable[[AgentSession], ProviderSessionRef | None]:
    def factory(session: AgentSession) -> ProviderSessionRef | None:
        persona = persona_registry.resolve(session.agent_name)
        adapter_name = session.agent_name if persona is None else persona.adapter_name
        if adapter_name not in {"claude-code", "codeflicker", "trae"}:
            return None
        resume_hints = {
            "claude-code": f"claude --resume {session.session_id}",
            "codeflicker": f"flickcli --resume {session.session_id}",
            "trae": f"trae-cli --resume {session.session_id}",
        }
        return ProviderSessionRef(
            provider_name=adapter_name,
            session_id=session.session_id,
            resume_hint=resume_hints[adapter_name],
        )

    return factory
