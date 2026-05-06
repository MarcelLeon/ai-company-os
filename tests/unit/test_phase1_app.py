from pathlib import Path

from aico.adapter.claude_code import ClaudeCodeAdapter
from aico.adapter.codex import CodexAdapter
from aico.app.phase1 import Phase1Settings, build_phase1_runtime, configure_logging
from aico.channel.telegram import TelegramChannel
from aico.core import AuditEventType, RiskLevel, Task


def test_phase1_settings_parse_claude_command() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p --output-format text",
    )

    assert settings.claude_command_tuple() == ("claude", "-p", "--output-format", "text")


def test_phase1_settings_default_claude_command_bypasses_local_prompts() -> None:
    settings = Phase1Settings(telegram_bot_token="token")

    assert settings.claude_command_tuple() == (
        "claude",
        "-p",
        "--output-format",
        "text",
        "--permission-mode",
        "bypassPermissions",
    )


def test_phase1_settings_parse_codex_command() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        codex_command="codex --ask-for-approval never exec --sandbox read-only",
    )

    assert settings.codex_command_tuple() == (
        "codex",
        "--ask-for-approval",
        "never",
        "exec",
        "--sandbox",
        "read-only",
    )


def test_phase1_settings_parse_approval_reviewer_ids() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        approval_reviewer_ids="user-1, user-2,,",
    )

    assert settings.approval_reviewer_id_tuple() == ("user-1", "user-2")


def test_phase1_runtime_configures_file_logging(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "aico.log"
    settings = Phase1Settings(telegram_bot_token="token", log_path=log_path)

    configure_logging(settings)

    assert log_path.read_text(encoding="utf-8")


def test_phase1_empty_log_path_disables_file_logging() -> None:
    settings = Phase1Settings.model_validate({"telegram_bot_token": "token", "log_path": ""})

    assert settings.log_path is None


def test_build_phase1_runtime_writes_audit_jsonl_when_configured(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit" / "events.jsonl"
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
        audit_log_path=audit_path,
    )
    runtime = build_phase1_runtime(settings)
    task = Task(
        task_id="task-1",
        payload="run pytest",
        requester_id="user-1",
        target_persona="claude-code",
    )

    runtime.orchestrator._task_bus._audit_log.record(  # noqa: SLF001
        AuditEventType.TASK_SUBMITTED,
        task,
        risk_level=RiskLevel.SHELL_EXEC,
    )

    assert '"event_type": "task_submitted"' in audit_path.read_text(encoding="utf-8")


def test_build_phase1_runtime_wires_telegram_channel_and_claude_adapter() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        default_persona="lao-zhang",
        telegram_poll_timeout_seconds=1,
        claude_command="claude -p",
        claude_working_directory=Path("/tmp/work"),
    )

    runtime = build_phase1_runtime(settings)

    assert isinstance(runtime.channel, TelegramChannel)
    assert isinstance(runtime.adapter, ClaudeCodeAdapter)
    assert runtime.channel.name == "telegram"
    assert runtime.adapter.name == "claude-code"
    assert runtime.session_store.list() == ()


def test_build_phase1_runtime_can_enable_codex_adapter_for_status() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_codex_adapter=True,
        claude_command="claude -p",
        codex_command="codex --ask-for-approval never exec --sandbox read-only",
    )

    runtime = build_phase1_runtime(settings)

    snapshots = runtime.registry.snapshots()
    assert [snapshot.name for snapshot in snapshots] == ["claude-code", "codex"]
    codex = runtime.registry.get("codex")
    assert isinstance(codex, CodexAdapter)
    assert codex._output_idle_timeout_seconds == 90.0  # noqa: SLF001


def test_build_phase1_runtime_registers_claude_alias() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
    )

    runtime = build_phase1_runtime(settings)

    assert runtime.registry.resolve("claude") is runtime.adapter


def test_build_phase1_runtime_registers_default_personas() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_codex_adapter=True,
        claude_command="claude -p",
        codex_command="codex --ask-for-approval never exec --sandbox read-only",
    )

    runtime = build_phase1_runtime(settings)
    claude_persona = runtime.persona_registry.resolve("claude")
    codex_persona = runtime.persona_registry.resolve("codex")

    assert runtime.persona_registry.names() == ("implementer", "reviewer")
    assert claude_persona is not None
    assert claude_persona.adapter_name == "claude-code"
    assert codex_persona is not None
    assert codex_persona.adapter_name == "codex"


def test_build_phase1_runtime_registers_default_project_assignments() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_codex_adapter=True,
        claude_command="claude -p",
        codex_command="codex --ask-for-approval never exec --sandbox read-only",
    )

    runtime = build_phase1_runtime(settings)
    project = runtime.project_directory.project("aico")
    assignments = runtime.project_directory.assignments("aico")

    assert project is not None
    assert project.name == "AI Company OS"
    assert [assignment.seat for assignment in assignments] == [
        "aico-implementer",
        "aico-reviewer",
    ]
    assert runtime.project_directory.default_assignment("aico") == assignments[0]


def test_build_phase1_runtime_loads_project_assignments_from_config(tmp_path: Path) -> None:
    project_config = tmp_path / "projects.json"
    project_config.write_text(
        """
        {
          "agents": {
            "claude": {
              "id": "claude",
              "provider": "claude-code",
              "title": "Senior Implementer"
            }
          },
          "projects": {
            "demo": {
              "id": "demo",
              "name": "Demo Project",
              "repo": "/repo/demo",
              "default_assignment": "demo-implementer"
            }
          },
          "assignments": [
            {
              "project": "demo",
              "agent": "claude",
              "role": "implementer",
              "seat": "demo-implementer"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
        project_config_path=project_config,
    )

    runtime = build_phase1_runtime(settings)
    project = runtime.project_directory.project("demo")
    assignment = runtime.project_directory.assignment("demo-implementer")

    assert project is not None
    assert project.name == "Demo Project"
    assert assignment is not None
    assert assignment.agent == "claude"


def test_build_phase1_runtime_rejects_project_agent_for_disabled_adapter(
    tmp_path: Path,
) -> None:
    project_config = tmp_path / "projects.json"
    project_config.write_text(
        """
        {
          "agents": {
            "codex": {
              "id": "codex",
              "provider": "codex",
              "title": "Code Reviewer"
            }
          },
          "projects": {
            "aico": {
              "id": "aico",
              "name": "AI Company OS",
              "repo": "/repo/aico"
            }
          },
          "assignments": [
            {
              "project": "aico",
              "agent": "codex",
              "role": "reviewer",
              "seat": "aico-reviewer"
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_codex_adapter=False,
        claude_command="claude -p",
        project_config_path=project_config,
    )

    try:
        build_phase1_runtime(settings)
    except ValueError as exc:
        assert "agent codex references unknown provider codex" in str(exc)
    else:
        raise AssertionError("expected project validation to fail")


def test_build_phase1_runtime_loads_personas_from_config(tmp_path: Path) -> None:
    persona_config = tmp_path / "personas.json"
    persona_config.write_text(
        """
        [
          {
            "name": "architect",
            "adapter_name": "claude-code",
            "role_instruction": "Role: architect.",
            "aliases": ["design"]
          },
          {
            "name": "reviewer",
            "adapter_name": "codex",
            "role_instruction": "Role: reviewer.",
            "aliases": ["codex"]
          }
        ]
        """,
        encoding="utf-8",
    )
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_codex_adapter=True,
        claude_command="claude -p",
        codex_command="codex --ask-for-approval never exec --sandbox read-only",
        persona_config_path=persona_config,
    )

    runtime = build_phase1_runtime(settings)
    design_persona = runtime.persona_registry.resolve("design")
    codex_persona = runtime.persona_registry.resolve("codex")

    assert runtime.persona_registry.names() == ("architect", "reviewer")
    assert design_persona is not None
    assert design_persona.adapter_name == "claude-code"
    assert codex_persona is not None
    assert codex_persona.adapter_name == "codex"


def test_build_phase1_runtime_rejects_persona_for_disabled_adapter(tmp_path: Path) -> None:
    persona_config = tmp_path / "personas.json"
    persona_config.write_text(
        """
        [
          {
            "name": "reviewer",
            "adapter_name": "codex",
            "role_instruction": "Role: reviewer.",
            "aliases": ["codex"]
          }
        ]
        """,
        encoding="utf-8",
    )
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_codex_adapter=False,
        claude_command="claude -p",
        persona_config_path=persona_config,
    )

    try:
        build_phase1_runtime(settings)
    except ValueError as exc:
        assert "unknown adapter codex" in str(exc)
    else:
        raise AssertionError("expected persona validation to fail")
