from pathlib import Path

from aico.adapter.claude_code import ClaudeCodeAdapter
from aico.app.phase1 import Phase1Settings, build_phase1_runtime
from aico.channel.telegram import TelegramChannel


def test_phase1_settings_parse_claude_command() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p --output-format text",
    )

    assert settings.claude_command_tuple() == ("claude", "-p", "--output-format", "text")


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
