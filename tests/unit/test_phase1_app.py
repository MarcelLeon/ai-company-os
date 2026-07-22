import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import aico.app.phase1 as phase1_app
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
from aico.app.runtime_alerts import (
    RuntimeAlertDeliverySnapshot,
    RuntimeAlertDeliveryStatus,
)
from aico.app.runtime_config_source import RuntimeConfigSourceHealth
from aico.app.runtime_liveness import RuntimeLivenessPulse, WebhookRuntimeLivenessSink
from aico.channel.feishu import FeishuChannel
from aico.channel.telegram import TelegramChannel
from aico.core import (
    AuditEventType,
    ChannelTarget,
    HealthStatus,
    IncomingMessage,
    InMemoryAuditLog,
    JsonlAuditSink,
    JsonlMemoryStore,
    MessageContent,
    RiskLevel,
    SQLiteTaskStateStore,
    Task,
    TaskSnapshot,
    TaskStatus,
    read_jsonl_audit_events,
)
from aico.core.audit_ledger import AuditIntegrityError
from aico.core.sqlite_state import SQLiteStateDatabase
from aico.core.standing_autonomy import (
    StandingAutonomyConfigError,
    StandingAutonomyGrant,
    StandingAutonomyGrantSet,
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
        owner_sender_ids="user-1,user-2",
        trusted_target_ids="chat-1",
        approval_reviewer_ids="user-1, user-2,,",
    )

    assert settings.approval_reviewer_id_tuple() == ("user-1", "user-2")


def test_phase1_settings_parse_owner_ingress_bindings() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        owner_sender_ids="owner-1, owner-2,owner-1",
        trusted_target_ids="chat-1, chat-2,chat-1",
    )

    assert settings.owner_sender_id_tuple() == ("owner-1", "owner-2")
    assert settings.trusted_target_id_tuple() == ("chat-1", "chat-2")


def test_phase1_settings_reject_morning_target_outside_trusted_ingress() -> None:
    with pytest.raises(ValidationError, match="trusted IM target"):
        Phase1Settings(
            telegram_bot_token="token",
            owner_sender_ids="owner-1",
            trusted_target_ids="chat-1",
            morning_push_enabled=True,
            morning_push_target_id="public-chat",
            morning_push_project="aico",
        )


def test_phase1_settings_reject_approval_reviewer_outside_owner_senders() -> None:
    with pytest.raises(ValidationError, match="approval reviewers must be configured owner"):
        Phase1Settings(
            telegram_bot_token="token",
            owner_sender_ids="owner-1",
            trusted_target_ids="chat-1",
            approval_reviewer_ids="stranger",
        )


def test_build_phase1_runtime_wires_owner_bound_ingress() -> None:
    runtime = build_phase1_runtime(
        Phase1Settings(
            telegram_bot_token="token",
            claude_command="claude -p",
            owner_sender_ids="owner-1",
            trusted_target_ids="chat-1",
        )
    )
    trusted = IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="owner-1",
        content=MessageContent(text="/inbox"),
        raw_ref="message-1",
    )
    untrusted = trusted.model_copy(update={"sender_id": "stranger"})

    assert runtime.orchestrator._ingress.accepts(trusted)  # noqa: SLF001
    assert not runtime.orchestrator._ingress.accepts(untrusted)  # noqa: SLF001


def test_phase1_settings_bound_approval_lease() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        approval_max_age_seconds=3600,
    )

    assert settings.approval_max_age_seconds == 3600
    with pytest.raises(ValidationError):
        Phase1Settings(telegram_bot_token="token", approval_max_age_seconds=299)
    with pytest.raises(ValidationError):
        Phase1Settings(telegram_bot_token="token", approval_max_age_seconds=604_801)


def test_phase1_strict_absence_admission_rejects_runtime_config_drift() -> None:
    base: dict[str, object] = {
        "telegram_bot_token": "token",
        "absence_admission_mode": "strict",
        "state_db_path": Path("state.db"),
        "audit_log_path": Path("audit.jsonl"),
        "memory_path": Path("memory.jsonl"),
        "project_config_path": Path("projects.json"),
        "reviewed_config_revision": "a" * 40,
        "runtime_alert_webhook_url": "https://alerts.example.test/runtime",
        "runtime_liveness_enabled": True,
        "runtime_liveness_webhook_url": "https://receiver.example.test/pulses",
        "runtime_monitor_id": "owner-runtime",
        "recovery_backup_enabled": True,
        "recovery_backup_output_dir": Path("/private/recovery"),
        "recovery_drill_enabled": True,
        "standing_autonomy_grant_path": Path("/private/standing.json"),
        "commissioning_receipt_path": Path("/private/commissioning.json"),
        "commissioning_dead_man_evidence_path": Path("/private/dead-man.json"),
        "commissioning_receiver_public_key_path": Path("/private/receiver-public.pem"),
    }
    settings = Phase1Settings.model_validate(base)

    assert settings.absence_admission_mode == "strict"
    for field_name, contract in (
        ("runtime_alert_webhook_url", "runtime alerts"),
        ("runtime_liveness_enabled", "runtime liveness"),
        ("recovery_backup_enabled", "recovery backup"),
        ("standing_autonomy_grant_path", "standing autonomy"),
        ("commissioning_receipt_path", "runtime commissioning"),
        ("commissioning_receiver_public_key_path", "runtime commissioning"),
        ("recovery_drill_enabled", "recovery drill"),
    ):
        disabled: object = None if "path" in field_name or "url" in field_name else False
        drifted = {**base, field_name: disabled}
        if field_name == "recovery_backup_enabled":
            drifted["recovery_drill_enabled"] = False
        with pytest.raises(ValidationError, match=contract):
            Phase1Settings.model_validate(drifted)


def test_phase1_loads_strict_absence_admission_from_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".env").write_text(
        "AICO_TELEGRAM_BOT_TOKEN=private-token\nAICO_ABSENCE_ADMISSION_MODE=strict\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="configuration validation failed") as exc:
        phase1_app.load_phase1_settings()

    assert "private-token" not in str(exc.value)


def test_phase1_settings_constructor_does_not_implicitly_read_checkout_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".env").write_text(
        "AICO_STATE_DB_PATH=.aico/ambient-state.db\nAICO_ENABLE_CURSOR_ADAPTER=true\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = Phase1Settings(telegram_bot_token="token")

    assert settings.state_db_path is None
    assert settings.enable_cursor_adapter is False


def test_phase1_strict_absence_preflight_runs_before_runtime_construction(
    tmp_path: Path,
) -> None:
    output = tmp_path / "recovery"
    output.mkdir()
    output.chmod(0o700)
    settings = Phase1Settings.model_validate(
        {
            "telegram_bot_token": "token",
            "absence_admission_mode": "strict",
            "owner_sender_ids": "owner",
            "trusted_target_ids": "chat",
            "state_db_path": tmp_path / "state.db",
            "audit_log_path": tmp_path / "audit.jsonl",
            "memory_path": tmp_path / "memory.jsonl",
            "project_config_path": Path.cwd() / "config/projects.example.json",
            "reviewed_config_revision": "a" * 40,
            "runtime_alert_webhook_url": "https://alerts.example.test/runtime",
            "runtime_liveness_enabled": True,
            "runtime_liveness_webhook_url": "https://receiver.example.test/pulses",
            "runtime_monitor_id": "owner-runtime",
            "recovery_backup_enabled": True,
            "recovery_backup_output_dir": output,
            "recovery_drill_enabled": True,
            "standing_autonomy_grant_path": tmp_path / "missing-standing.json",
            "commissioning_receipt_path": tmp_path / "commissioning.json",
            "commissioning_dead_man_evidence_path": tmp_path / "dead-man.json",
            "commissioning_receiver_public_key_path": tmp_path / "receiver-public.pem",
            "morning_push_enabled": True,
            "morning_push_target_id": "chat",
            "morning_push_project": "aico",
            "enable_codex_adapter": True,
        }
    )

    with pytest.raises(StandingAutonomyConfigError):
        build_phase1_runtime(settings)

    assert not (tmp_path / "state.db").exists()
    assert not (tmp_path / "audit.jsonl").exists()


def test_phase1_commissioning_preflight_binds_loaded_dotenv_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("AICO_CHANNEL=telegram\n")
    dotenv.chmod(0o600)
    settings = Phase1Settings.model_validate(
        {
            "project_config_path": tmp_path / "projects.json",
            "reviewed_config_revision": "a" * 40,
            "runtime_monitor_id": "owner-runtime",
            "commissioning_receipt_path": tmp_path / "commissioning.json",
            "commissioning_dead_man_evidence_path": tmp_path / "dead-man.json",
            "commissioning_receiver_public_key_path": tmp_path / "receiver-public.pem",
            "recovery_backup_checkout_path": tmp_path,
        }
    )
    settings._config_source_health = RuntimeConfigSourceHealth.capture(dotenv)  # noqa: SLF001
    captured: dict[str, object] = {}

    def verify(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(phase1_app, "verify_runtime_commissioning_receipt", verify)

    health = phase1_app.preflight_runtime_commissioning(settings)

    assert health.dotenv_path == dotenv
    assert health.expected_runtime_id == "owner-runtime"
    assert health.trusted_receiver_public_key_path == tmp_path / "receiver-public.pem"
    assert captured["receipt_path"] == tmp_path / "commissioning.json"


def test_phase1_runtime_configures_file_logging(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "aico.log"
    settings = Phase1Settings(telegram_bot_token="token", log_path=log_path)

    configure_logging(settings)

    assert log_path.read_text(encoding="utf-8")


async def test_strict_phase1_heartbeat_includes_loaded_dotenv_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("AICO_CHANNEL=telegram\n", encoding="utf-8")
    settings = Phase1Settings(
        telegram_bot_token="token",
        runtime_heartbeat_path=tmp_path / "heartbeat.json",
    )
    settings.absence_admission_mode = "strict"
    settings._config_source_health = RuntimeConfigSourceHealth.capture(dotenv)  # noqa: SLF001
    runtime = build_phase1_runtime(
        settings.model_copy(update={"absence_admission_mode": "optional"})
    )

    async def healthy() -> HealthStatus:
        return HealthStatus.OK

    monkeypatch.setattr(runtime.channel, "health_check", healthy)
    for adapter in runtime.registry.adapters():
        monkeypatch.setattr(adapter, "health_check", healthy)
    dotenv.write_text("AICO_CHANNEL=feishu\n", encoding="utf-8")

    heartbeat = phase1_app._runtime_heartbeat(settings, runtime)  # noqa: SLF001
    assert heartbeat is not None
    snapshot = await heartbeat._health_probe()  # type: ignore[misc]  # noqa: SLF001

    assert snapshot.status is HealthStatus.FAILED
    assert snapshot.failed_component_names() == ("configuration:dotenv-generation",)


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
    settings = Phase1Settings.model_validate(
        {
            "telegram_bot_token": "token",
            "log_path": "",
            "runtime_heartbeat_path": "",
        }
    )

    assert settings.log_path is None
    assert settings.runtime_heartbeat_path is None


def test_phase1_settings_require_durable_state_for_alert_webhook() -> None:
    with pytest.raises(ValueError, match="STATE_DB_PATH"):
        Phase1Settings.model_validate(
            {
                "telegram_bot_token": "token",
                "runtime_alert_webhook_url": "https://alerts.example.test/aico",
            }
        )

    with pytest.raises(ValueError, match="HEARTBEAT_PATH"):
        Phase1Settings.model_validate(
            {
                "telegram_bot_token": "token",
                "state_db_path": ".aico/state.db",
                "runtime_heartbeat_path": "",
                "runtime_alert_webhook_url": "https://alerts.example.test/aico",
            }
        )


def test_phase1_settings_require_https_and_redact_alert_secrets(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        Phase1Settings.model_validate(
            {
                "telegram_bot_token": "token",
                "state_db_path": tmp_path / "state.db",
                "runtime_alert_webhook_url": "http://alerts.example.test/aico",
            }
        )

    settings = Phase1Settings.model_validate(
        {
            "telegram_bot_token": "token",
            "state_db_path": tmp_path / "state.db",
            "runtime_alert_webhook_url": "https://alerts.example.test/secret-path",
            "runtime_alert_webhook_bearer_token": "super-secret-token",
        }
    )

    assert "alerts.example.test" not in str(settings)
    assert "super-secret-token" not in str(settings)


def test_phase1_settings_require_explicit_dead_man_identity_and_transport(
    tmp_path: Path,
) -> None:
    base = {
        "telegram_bot_token": "token",
        "state_db_path": tmp_path / "state.db",
        "runtime_liveness_enabled": True,
    }
    with pytest.raises(ValueError, match="RUNTIME_LIVENESS_WEBHOOK_URL"):
        Phase1Settings.model_validate(base)
    with pytest.raises(ValueError, match="RUNTIME_MONITOR_ID"):
        Phase1Settings.model_validate(
            {
                **base,
                "runtime_liveness_webhook_url": "https://alerts.example.test/aico",
            }
        )
    with pytest.raises(ValueError, match="RUNTIME_MONITOR_ID"):
        Phase1Settings.model_validate(
            {
                **base,
                "runtime_liveness_webhook_url": "https://alerts.example.test/aico",
                "runtime_monitor_id": "/Users/private/runtime",
            }
        )


def test_phase1_settings_bound_dead_man_interval_and_ttl(tmp_path: Path) -> None:
    base = {
        "telegram_bot_token": "token",
        "state_db_path": tmp_path / "state.db",
        "runtime_liveness_webhook_url": "https://alerts.example.test/aico",
        "runtime_liveness_enabled": True,
        "runtime_monitor_id": "owner-runtime",
    }
    with pytest.raises(ValueError, match="at least the heartbeat interval"):
        Phase1Settings.model_validate(
            {
                **base,
                "runtime_heartbeat_interval_seconds": 30,
                "runtime_liveness_interval_seconds": 20,
            }
        )
    with pytest.raises(ValueError, match="at least three pulse intervals"):
        Phase1Settings.model_validate(
            {
                **base,
                "runtime_liveness_interval_seconds": 60,
                "runtime_liveness_ttl_seconds": 120,
            }
        )

    settings = Phase1Settings.model_validate(
        {
            **base,
            "runtime_liveness_interval_seconds": 60,
            "runtime_liveness_ttl_seconds": 180,
            "runtime_liveness_webhook_bearer_token": "super-secret-token",
        }
    )

    assert settings.runtime_monitor_id is not None
    assert settings.runtime_monitor_id.get_secret_value() == "owner-runtime"
    assert "owner-runtime" not in str(settings)
    assert "super-secret-token" not in str(settings)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        (
            {"runtime_liveness_webhook_url": "https://alerts.example.test/runtime"},
            "webhook URLs must be distinct",
        ),
        (
            {
                "runtime_alert_webhook_bearer_token": "shared-private-token",
                "runtime_liveness_webhook_bearer_token": "shared-private-token",
            },
            "bearer tokens must be distinct",
        ),
    ],
)
def test_phase1_settings_reject_runtime_webhook_authority_reuse(
    tmp_path: Path,
    override: dict[str, object],
    message: str,
) -> None:
    base: dict[str, object] = {
        "telegram_bot_token": "token",
        "state_db_path": tmp_path / "state.db",
        "runtime_alert_webhook_url": "https://alerts.example.test/runtime",
        "runtime_liveness_enabled": True,
        "runtime_liveness_webhook_url": "https://receiver.example.test/pulses",
        "runtime_monitor_id": "owner-runtime",
    }

    with pytest.raises(ValidationError, match=message):
        Phase1Settings.model_validate({**base, **override})


async def test_phase1_liveness_probe_wires_immediate_secret_free_pulse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pulses: list[RuntimeLivenessPulse] = []

    async def record(
        _sink: WebhookRuntimeLivenessSink,
        pulse: RuntimeLivenessPulse,
    ) -> None:
        pulses.append(pulse)

    monkeypatch.setattr(WebhookRuntimeLivenessSink, "send", record)
    settings = Phase1Settings.model_validate(
        {
            "telegram_bot_token": "token",
            "runtime_liveness_webhook_url": "https://receiver.example.test/private",
            "runtime_liveness_webhook_bearer_token": "super-secret-token",
            "runtime_liveness_enabled": True,
            "runtime_monitor_id": "owner-runtime",
            "runtime_liveness_interval_seconds": 60,
            "runtime_liveness_ttl_seconds": 180,
        }
    )

    alerting = RuntimeAlertDeliverySnapshot(
        status=RuntimeAlertDeliveryStatus.PENDING,
        checked_at=datetime.now(UTC),
        pending_events=1,
    )
    snapshot = await phase1_app._runtime_liveness_probe(settings)(alerting)  # noqa: SLF001

    assert snapshot.status.value == "healthy"
    assert len(pulses) == 1
    assert pulses[0].runtime_id == "owner-runtime"
    assert pulses[0].alert_delivery_status.value == "pending"
    rendered = str(snapshot.to_payload())
    assert "owner-runtime" not in rendered
    assert "receiver.example.test" not in rendered
    assert "super-secret-token" not in rendered


def test_phase1_liveness_transport_does_not_require_incident_alert_state() -> None:
    settings = Phase1Settings.model_validate(
        {
            "telegram_bot_token": "token",
            "runtime_liveness_enabled": True,
            "runtime_liveness_webhook_url": "https://receiver.example.test/pulses",
            "runtime_liveness_webhook_bearer_token": "pulse-token",
            "runtime_monitor_id": "owner-runtime",
        }
    )

    assert settings.state_db_path is None
    assert settings.runtime_alert_webhook_url is None


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


def test_build_phase1_runtime_refuses_tampered_audit_history(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit" / "events.jsonl"
    seed_log = InMemoryAuditLog(
        event_id_factory=lambda: "event-1",
        sinks=(JsonlAuditSink(audit_path),),
    )
    seed_log.record(
        AuditEventType.TASK_SUBMITTED,
        Task(
            task_id="task-1",
            payload="private operation",
            requester_id="owner",
            target_persona="claude-code",
        ),
    )
    audit_path.write_bytes(
        audit_path.read_bytes().replace(b'"task_id": "task-1"', b'"task_id": "task-x"')
    )
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
        audit_log_path=audit_path,
    )

    with pytest.raises(AuditIntegrityError, match="hash chain"):
        build_phase1_runtime(settings)


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
    assert "standing_proposals" in SQLiteStateDatabase(state_db_path).table_counts()


def test_build_phase1_runtime_delivers_recovery_outbox_once(tmp_path: Path) -> None:
    state_db_path = tmp_path / "state" / "aico.db"
    audit_path = tmp_path / "audit" / "events.jsonl"
    store = SQLiteTaskStateStore(state_db_path)
    task = Task(
        task_id="task-runtime-recovery",
        payload="publish result",
        requester_id="boss",
        target_persona="claude-code",
        trace_id="trace-runtime-recovery",
    )
    store.upsert_task_record(task)
    store.upsert_task_snapshot(
        TaskSnapshot(
            task_id=task.task_id,
            target_persona=task.target_persona,
            adapter_name="claude-code",
            status=TaskStatus.RUNNING,
            created_at=task.created_at,
        )
    )
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
        state_db_path=state_db_path,
        audit_log_path=audit_path,
    )

    first_runtime = build_phase1_runtime(settings)
    assert store.load_task_snapshots()[0].status is TaskStatus.RUNNING
    assert first_runtime.task_bus is not None
    first_runtime.task_bus.recover_startup_state()
    second_runtime = build_phase1_runtime(settings)

    snapshots = first_runtime.task_bus.task_snapshots(limit=None)
    assert snapshots[0].status is TaskStatus.INTERRUPTED
    assert second_runtime.task_bus is not None
    assert second_runtime.task_bus.task_snapshots(limit=None) == snapshots
    events = read_jsonl_audit_events(audit_path)
    assert [event.event_type for event in events] == [AuditEventType.TASK_INTERRUPTED]
    assert events[0].task_id == task.task_id
    assert events[0].trace_id == task.trace_id
    assert store.load_pending_recovery_audit_events() == ()


def test_build_phase1_runtime_defaults_to_single_project_after_restart() -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
    )

    runtime = build_phase1_runtime(settings)

    active = runtime.orchestrator._project_directory.active_project(  # noqa: SLF001
        "telegram:chat-after-restart:boss"
    )
    assert active is not None
    assert active.id == "aico"


def test_build_phase1_runtime_configures_morning_push_scheduler(tmp_path: Path) -> None:
    state_db_path = tmp_path / "state.db"
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
        morning_push_enabled=True,
        morning_push_target_id="chat-1",
        trusted_target_ids="chat-1",
        morning_push_project="aico",
        morning_push_time="08:30",
        state_db_path=state_db_path,
    )

    runtime = build_phase1_runtime(settings)

    assert runtime.morning_scheduler is not None
    assert "scheduled_autonomy_outcome_outbox" in SQLiteStateDatabase(state_db_path).table_counts()


def test_build_phase1_runtime_requires_morning_push_target(tmp_path: Path) -> None:
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
        morning_push_enabled=True,
        morning_push_project="aico",
        state_db_path=tmp_path / "state.db",
    )

    try:
        build_phase1_runtime(settings)
    except ValueError as exc:
        assert "AICO_MORNING_PUSH_TARGET_ID" in str(exc)
    else:
        raise AssertionError("expected missing morning push target to fail")


def test_morning_push_requires_durable_state_database() -> None:
    with pytest.raises(ValueError, match="durable morning push"):
        Phase1Settings(
            telegram_bot_token="token",
            claude_command="claude -p",
            morning_push_enabled=True,
            morning_push_target_id="chat-1",
            trusted_target_ids="chat-1",
            morning_push_project="aico",
        )


def test_recovery_backup_requires_complete_durable_configuration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="AICO_AUDIT_LOG_PATH"):
        Phase1Settings(
            telegram_bot_token="token",
            recovery_backup_enabled=True,
            state_db_path=tmp_path / "state.db",
        )


def test_phase1_builds_default_disabled_recovery_backup_scheduler(tmp_path: Path) -> None:
    output = tmp_path / "recovery-output"
    output.mkdir()
    output.chmod(0o700)
    settings = Phase1Settings(
        telegram_bot_token="token",
        recovery_backup_enabled=True,
        state_db_path=tmp_path / "state.db",
        audit_log_path=tmp_path / "audit.jsonl",
        memory_path=tmp_path / "memory.jsonl",
        project_config_path=Path.cwd() / "config/projects.example.json",
        reviewed_config_revision="a" * 40,
        recovery_backup_checkout_path=Path.cwd(),
        recovery_backup_output_dir=output,
    )

    scheduler = phase1_app._recovery_backup_scheduler(settings)  # noqa: SLF001

    assert scheduler is not None
    assert scheduler._drill_store is None  # noqa: SLF001
    assert Phase1Settings(telegram_bot_token="token").recovery_backup_enabled is False


def test_recovery_custody_max_age_must_cover_check_interval(tmp_path: Path) -> None:
    output = tmp_path / "recovery-output"
    output.mkdir()
    output.chmod(0o700)

    with pytest.raises(ValueError, match="custody max age"):
        Phase1Settings(
            telegram_bot_token="token",
            recovery_backup_enabled=True,
            state_db_path=tmp_path / "state.db",
            audit_log_path=tmp_path / "audit.jsonl",
            memory_path=tmp_path / "memory.jsonl",
            project_config_path=Path.cwd() / "config/projects.example.json",
            reviewed_config_revision="a" * 40,
            recovery_backup_output_dir=output,
            recovery_custody_check_interval_seconds=600,
            recovery_custody_max_age_seconds=300,
        )


def test_recovery_retention_age_must_cover_preserved_generations(tmp_path: Path) -> None:
    output = tmp_path / "recovery-output"
    output.mkdir()
    output.chmod(0o700)

    with pytest.raises(ValueError, match="retention age"):
        Phase1Settings(
            telegram_bot_token="token",
            recovery_backup_enabled=True,
            state_db_path=tmp_path / "state.db",
            audit_log_path=tmp_path / "audit.jsonl",
            memory_path=tmp_path / "memory.jsonl",
            project_config_path=Path.cwd() / "config/projects.example.json",
            reviewed_config_revision="a" * 40,
            recovery_backup_output_dir=output,
            recovery_backup_interval_seconds=86_400,
            recovery_retention_enabled=True,
            recovery_retention_after_seconds=172_800,
            recovery_retention_min_generations=7,
        )


def test_recovery_retention_cannot_be_enabled_without_backup() -> None:
    with pytest.raises(ValueError, match="requires scheduled recovery backup"):
        Phase1Settings(
            telegram_bot_token="token",
            recovery_retention_enabled=True,
        )


def test_recovery_drill_requires_backup_and_valid_freshness_window() -> None:
    with pytest.raises(ValueError, match="drill requires scheduled recovery backup"):
        Phase1Settings(
            telegram_bot_token="token",
            recovery_drill_enabled=True,
        )
    with pytest.raises(ValueError, match="drill max age"):
        Phase1Settings(
            telegram_bot_token="token",
            recovery_backup_enabled=True,
            state_db_path=Path("state.db"),
            audit_log_path=Path("audit.jsonl"),
            memory_path=Path("memory.jsonl"),
            project_config_path=Path("projects.json"),
            reviewed_config_revision="a" * 40,
            recovery_backup_output_dir=Path("/private/recovery"),
            recovery_drill_enabled=True,
            recovery_drill_interval_seconds=7_200,
            recovery_drill_max_age_seconds=3_600,
        )


def test_phase1_builds_default_disabled_scheduled_recovery_drill(tmp_path: Path) -> None:
    output = tmp_path / "recovery-output"
    output.mkdir()
    output.chmod(0o700)
    workspace = tmp_path / "drill-workspace"
    workspace.mkdir()
    workspace.chmod(0o700)
    settings = Phase1Settings(
        telegram_bot_token="token",
        recovery_backup_enabled=True,
        state_db_path=tmp_path / "state.db",
        audit_log_path=tmp_path / "audit.jsonl",
        memory_path=tmp_path / "memory.jsonl",
        project_config_path=Path.cwd() / "config/projects.example.json",
        reviewed_config_revision="a" * 40,
        recovery_backup_checkout_path=Path.cwd(),
        recovery_backup_output_dir=output,
        recovery_drill_enabled=True,
        recovery_drill_workspace=workspace,
    )

    scheduler = phase1_app._recovery_backup_scheduler(settings)  # noqa: SLF001

    assert scheduler is not None
    assert scheduler._drill_store is not None  # noqa: SLF001
    assert scheduler._config.drill_workspace == workspace  # noqa: SLF001


def test_build_phase1_runtime_loads_external_owner_bound_standing_grant(
    tmp_path: Path,
) -> None:
    managed_repo = tmp_path / "managed-repo"
    managed_repo.mkdir()
    project_config = tmp_path / "projects.json"
    project_config.write_text(
        f"""
        {{
          "agents": {{
            "codex": {{
              "id": "codex",
              "provider": "codex",
              "title": "Independent Reviewer"
            }}
          }},
          "roles": {{
            "reviewer": {{
              "id": "reviewer",
              "title": "Independent Reviewer"
            }}
          }},
          "projects": {{
            "aico": {{
              "id": "aico",
              "name": "AI Company OS",
              "repo": "{managed_repo}",
              "default_assignment": "aico-reviewer",
              "standing_charter": [
                {{
                  "id": "absence-loop",
                  "objective": "Inspect current recovery evidence.",
                  "role": "reviewer",
                  "acceptance_evidence": ["one bounded report"],
                  "stop_conditions": ["stop before external communication"]
                }}
              ]
            }}
          }},
          "assignments": [
            {{
              "project": "aico",
              "agent": "codex",
              "role": "reviewer",
              "seat": "aico-reviewer"
            }}
          ]
        }}
        """,
        encoding="utf-8",
    )
    grant_path = tmp_path / "standing-grant.json"
    grant_path.write_text(
        StandingAutonomyGrantSet(
            grants=(
                StandingAutonomyGrant(
                    grant_id="grant-1",
                    owner_id="owner-1",
                    channel_name="telegram",
                    target_id="chat-1",
                    project_id="aico",
                    charter_id="absence-loop",
                    expires_at=datetime(2027, 1, 1, tzinfo=UTC),
                    max_runs=1,
                    max_duration_seconds=300,
                    token_stop_threshold=100_000,
                ),
            )
        ).model_dump_json(),
        encoding="utf-8",
    )
    grant_path.chmod(0o600)
    settings = Phase1Settings(
        telegram_bot_token="token",
        claude_command="claude -p",
        enable_codex_adapter=True,
        codex_command="codex exec --sandbox read-only",
        project_config_path=project_config,
        standing_autonomy_grant_path=grant_path,
        morning_push_enabled=True,
        morning_push_target_id="chat-1",
        trusted_target_ids="chat-1",
        morning_push_project="aico",
        state_db_path=tmp_path / "state.db",
    )

    validated = phase1_app.preflight_standing_autonomy(settings)
    runtime = build_phase1_runtime(settings)
    loaded = runtime.orchestrator._commands._standing_autonomy._grants  # noqa: SLF001

    assert validated == loaded
    assert loaded.grants[0].grant_id == "grant-1"
    assert loaded.grants[0].owner_id == "owner-1"


def test_build_phase1_runtime_rejects_grant_for_another_morning_target(
    tmp_path: Path,
) -> None:
    grant_path = tmp_path / "standing-grant.json"
    grant_path.write_text(
        StandingAutonomyGrantSet(
            grants=(
                StandingAutonomyGrant(
                    grant_id="grant-1",
                    owner_id="owner-1",
                    channel_name="telegram",
                    target_id="another-chat",
                    project_id="aico",
                    charter_id="missing-charter",
                    expires_at=datetime(2027, 1, 1, tzinfo=UTC),
                    max_runs=1,
                    max_duration_seconds=300,
                    token_stop_threshold=100_000,
                ),
            )
        ).model_dump_json(),
        encoding="utf-8",
    )
    grant_path.chmod(0o600)

    with pytest.raises(ValueError, match="does not match scheduled morning target"):
        build_phase1_runtime(
            Phase1Settings(
                telegram_bot_token="token",
                claude_command="claude -p",
                standing_autonomy_grant_path=grant_path,
                morning_push_enabled=True,
                morning_push_target_id="chat-1",
                trusted_target_ids="chat-1",
                morning_push_project="aico",
                state_db_path=tmp_path / "state.db",
            )
        )


def test_build_phase1_runtime_rejects_standing_grant_inside_managed_repo(
    tmp_path: Path,
) -> None:
    runtime = build_phase1_runtime(
        Phase1Settings(telegram_bot_token="token", claude_command="claude -p")
    )
    config = runtime.project_directory._config  # noqa: SLF001
    project = config.projects["aico"]
    grant_path = Path(project.repo) / ".aico-test-standing-grant.json"
    grant_path.write_text(
        StandingAutonomyGrantSet().model_dump_json(),
        encoding="utf-8",
    )
    grant_path.chmod(0o600)
    try:
        with pytest.raises(StandingAutonomyConfigError, match="outside managed repositories"):
            phase1_app._standing_autonomy_grants(  # noqa: SLF001
                Phase1Settings(
                    telegram_bot_token="token",
                    claude_command="claude -p",
                    standing_autonomy_grant_path=grant_path,
                ),
                runtime.project_directory,
                runtime.orchestrator._agent_directory,  # noqa: SLF001
                runtime.registry,
            )
    finally:
        grant_path.unlink()


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
    assert project.current_phase == "Phase 8 - 离线托管 + 老板缺席操作模型"
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
