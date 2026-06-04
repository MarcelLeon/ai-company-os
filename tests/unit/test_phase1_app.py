import logging
from pathlib import Path

from aico.adapter.claude_code import (
    DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS,
    ClaudeCodeAdapter,
)
from aico.adapter.codeflicker import CodeFlickerAdapter
from aico.adapter.codex import CodexAdapter
from aico.adapter.cursor import CursorAdapter
from aico.adapter.gemini import GeminiAdapter
from aico.adapter.trae import TraeAdapter
from aico.app.phase1 import Phase1Settings, build_phase1_runtime, configure_logging
from aico.channel.feishu import FeishuChannel
from aico.channel.telegram import TelegramChannel
from aico.core import (
    AuditEventType,
    InMemoryAuditLog,
    JsonlAuditSink,
    JsonlMemoryStore,
    RiskLevel,
    Task,
)


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


def test_phase1_settings_parse_cursor_command() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        cursor_command="cursor-agent -p --force --output-format text",
    )

    assert settings.cursor_command_tuple() == (
        "cursor-agent",
        "-p",
        "--force",
        "--output-format",
        "text",
    )


def test_phase1_settings_parse_codeflicker_command() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        codeflicker_command="flickcli -q --approval-mode yolo --output-format text",
    )

    assert settings.codeflicker_command_tuple() == (
        "flickcli",
        "-q",
        "--approval-mode",
        "yolo",
        "--output-format",
        "text",
    )


def test_phase1_settings_parse_trae_and_gemini_commands() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        trae_command="trae-cli --print --yolo",
        gemini_command="gemini --approval-mode yolo --output-format text",
    )

    assert settings.trae_command_tuple() == ("trae-cli", "--print", "--yolo")
    assert settings.gemini_command_tuple() == (
        "gemini",
        "--approval-mode",
        "yolo",
        "--output-format",
        "text",
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


def test_phase1_logging_suppresses_http_client_info_logs(tmp_path: Path) -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        log_level="INFO",
        log_path=tmp_path / "aico.log",
    )

    configure_logging(settings)

    assert logging.getLogger("httpx").getEffectiveLevel() == logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() == logging.WARNING


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


def test_build_phase1_runtime_loads_existing_audit_jsonl(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit" / "events.jsonl"
    seed_log = InMemoryAuditLog(
        event_id_factory=lambda: "event-1",
        sinks=(JsonlAuditSink(audit_path),),
    )
    task = Task(
        task_id="task-1",
        payload="run pytest",
        requester_id="user-1",
        target_persona="claude-code",
    )
    event = seed_log.record(AuditEventType.TASK_SUBMITTED, task)
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
        audit_log_path=audit_path,
    )

    runtime = build_phase1_runtime(settings)

    assert runtime.orchestrator._task_bus.audit_events(limit=None) == (event,)  # noqa: SLF001


def test_build_phase1_runtime_configures_memory_store_when_path_set(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory" / "shared.jsonl"
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
        memory_path=memory_path,
    )

    runtime = build_phase1_runtime(settings)

    assert isinstance(runtime.orchestrator._memory_store, JsonlMemoryStore)  # noqa: SLF001


def test_build_phase1_runtime_configures_sqlite_task_state_store(tmp_path: Path) -> None:
    state_db_path = tmp_path / "state" / "aico.db"
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
        state_db_path=state_db_path,
    )

    runtime = build_phase1_runtime(settings)

    assert runtime.orchestrator._task_bus._task_store is not None  # noqa: SLF001
    assert state_db_path.exists()


def test_phase1_settings_maps_bool_like_state_db_path_to_local_data_dir() -> None:
    enabled = Phase1Settings.model_validate(
        {"telegram_bot_token": "token", "state_db_path": "true"}
    )
    disabled = Phase1Settings.model_validate(
        {"telegram_bot_token": "token", "state_db_path": "false"}
    )

    assert enabled.state_db_path == Path(".aico/state.db")
    assert disabled.state_db_path is None


def test_build_phase1_runtime_configures_view_snapshot_handler_when_enabled(
    tmp_path: Path,
) -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
        view_enabled=True,
        view_output_dir=tmp_path / "view",
    )

    runtime = build_phase1_runtime(settings)

    assert runtime.orchestrator._view_snapshots is not None  # noqa: SLF001


def test_build_phase1_runtime_leaves_view_snapshot_handler_disabled_by_default() -> None:
    settings = Phase1Settings(telegram_bot_token="token", claude_command="claude -p")

    runtime = build_phase1_runtime(settings)

    assert runtime.orchestrator._view_snapshots is None  # noqa: SLF001


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


def test_build_phase1_runtime_wires_feishu_channel() -> None:
    settings = Phase1Settings(
        channel="feishu",
        feishu_app_id="app-id",
        feishu_app_secret="app-secret",
        feishu_verification_token="verify-token",
        claude_command="claude -p",
    )

    runtime = build_phase1_runtime(settings)

    assert isinstance(runtime.channel, FeishuChannel)
    assert runtime.channel.name == "feishu"


def test_build_phase1_runtime_requires_feishu_credentials() -> None:
    settings = Phase1Settings(
        channel="feishu",
        claude_command="claude -p",
    )

    try:
        build_phase1_runtime(settings)
    except ValueError as exc:
        assert "AICO_FEISHU_APP_ID is required" in str(exc)
    else:
        raise AssertionError("expected missing Feishu settings to fail")


def test_build_phase1_runtime_can_enable_codex_adapter_for_status() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_codex_adapter=True,
        enable_cursor_adapter=False,
        enable_codeflicker_adapter=False,
        enable_trae_adapter=False,
        enable_gemini_adapter=False,
        claude_command="claude -p",
        codex_command="codex --ask-for-approval never exec --sandbox read-only",
        codex_output_idle_timeout_seconds=DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS,
    )

    runtime = build_phase1_runtime(settings)

    snapshots = runtime.registry.snapshots()
    assert [snapshot.name for snapshot in snapshots] == ["claude-code", "codex"]
    codex = runtime.registry.get("codex")
    assert isinstance(codex, CodexAdapter)
    assert (  # noqa: SLF001
        codex._output_idle_timeout_seconds == DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS
    )
    assert codex.max_concurrent_tasks() == 5


def test_build_phase1_runtime_can_disable_optional_adapter_idle_timeout() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_codex_adapter=True,
        enable_cursor_adapter=False,
        enable_codeflicker_adapter=False,
        enable_trae_adapter=False,
        enable_gemini_adapter=False,
        claude_command="claude -p",
        codex_command="codex --ask-for-approval never exec --sandbox read-only",
        codex_output_idle_timeout_seconds=0,
    )

    runtime = build_phase1_runtime(settings)

    codex = runtime.registry.get("codex")
    assert isinstance(codex, CodexAdapter)
    assert codex._output_idle_timeout_seconds is None  # noqa: SLF001


def test_build_phase1_runtime_can_enable_cursor_adapter_for_agents() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_codex_adapter=False,
        enable_cursor_adapter=True,
        enable_codeflicker_adapter=False,
        enable_trae_adapter=False,
        enable_gemini_adapter=False,
        claude_command="claude -p",
        cursor_command="cursor-agent -p --force --output-format text",
    )

    runtime = build_phase1_runtime(settings)

    snapshots = runtime.registry.snapshots()
    assert [snapshot.name for snapshot in snapshots] == ["claude-code", "cursor"]
    cursor = runtime.registry.get("cursor")
    assert isinstance(cursor, CursorAdapter)
    assert runtime.persona_registry.resolve("cursor-agent") is not None


def test_build_phase1_runtime_can_enable_codeflicker_adapter_for_agents() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_codex_adapter=False,
        enable_cursor_adapter=False,
        enable_codeflicker_adapter=True,
        enable_trae_adapter=False,
        enable_gemini_adapter=False,
        claude_command="claude -p",
        codeflicker_command="flickcli -q --approval-mode yolo --output-format text",
    )

    runtime = build_phase1_runtime(settings)

    snapshots = runtime.registry.snapshots()
    assert [snapshot.name for snapshot in snapshots] == ["claude-code", "codeflicker"]
    codeflicker = runtime.registry.get("codeflicker")
    assert isinstance(codeflicker, CodeFlickerAdapter)
    assert runtime.persona_registry.resolve("flickcli") is not None


def test_build_phase1_runtime_can_enable_all_optional_adapters() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_codex_adapter=True,
        enable_cursor_adapter=True,
        enable_codeflicker_adapter=True,
        enable_trae_adapter=True,
        enable_gemini_adapter=True,
        claude_command="claude -p",
        codex_command="codex --ask-for-approval never exec --sandbox read-only",
        cursor_command="cursor-agent -p --force --output-format text",
        codeflicker_command="flickcli -q --approval-mode yolo --output-format text",
        trae_command="trae-cli --print --yolo",
        gemini_command="gemini --approval-mode yolo --output-format text",
    )

    runtime = build_phase1_runtime(settings)

    assert [snapshot.name for snapshot in runtime.registry.snapshots()] == [
        "claude-code",
        "codex",
        "cursor",
        "codeflicker",
        "trae",
        "gemini",
    ]
    assert runtime.persona_registry.names() == (
        "implementer",
        "reviewer",
        "cursor",
        "codeflicker",
        "trae",
        "gemini",
    )
    assert [card.name for card in runtime.orchestrator._agent_directory.list()] == [  # noqa: SLF001
        "implementer",
        "reviewer",
        "cursor",
        "codeflicker",
        "trae",
        "gemini",
    ]
    assert runtime.project_directory.agent("codeflicker") is not None
    codeflicker_tester = runtime.project_directory.upsert_appointment(
        project_id="aico",
        agent_id="codeflicker",
        role_id="tester",
    )
    assert codeflicker_tester is not None
    assert codeflicker_tester.agent == "codeflicker"


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
        enable_cursor_adapter=False,
        enable_codeflicker_adapter=False,
        enable_trae_adapter=False,
        enable_gemini_adapter=False,
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
        enable_cursor_adapter=False,
        enable_codeflicker_adapter=False,
        enable_trae_adapter=False,
        enable_gemini_adapter=False,
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
        "aico-challenger",
    ]
    assert assignments[0].permissions == ("code", "tests", "docs")
    assert assignments[1].permissions == ("code", "docs", "audit")
    assert assignments[2].permissions == ("docs", "audit")
    assert runtime.project_directory.default_assignment("aico") == assignments[0]
    assert runtime.project_directory.role("pm") is not None
    assert runtime.project_directory.role("senior-architect") is not None
    assert runtime.project_directory.role("challenger") is not None
    assert runtime.project_directory.role("golden-tester") is not None
    assert runtime.project_directory.role("market-risk") is not None
    assert runtime.project_directory.role("legal-compliance") is not None


def test_build_phase1_runtime_can_enable_trae_and_gemini_adapters() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        enable_trae_adapter=True,
        enable_gemini_adapter=True,
        claude_command="claude -p",
        trae_command="trae-cli --print --yolo",
        gemini_command="gemini --approval-mode yolo --output-format text",
    )

    runtime = build_phase1_runtime(settings)

    assert isinstance(runtime.registry.get("trae"), TraeAdapter)
    assert isinstance(runtime.registry.get("gemini"), GeminiAdapter)
    assert runtime.persona_registry.resolve("trae-cli") is not None
    assert runtime.persona_registry.resolve("gemini-cli") is not None


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
