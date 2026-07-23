from __future__ import annotations

import io
import json
import os
import plistlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.app.runtime_owner import RuntimeOwnerLock
from aico.app.service_cli import (
    CommandResult,
    LaunchdService,
    ServiceContext,
    readiness_checks,
    run_service_cli,
)
from aico.core import (
    AuditEventType,
    InMemoryAuditLog,
    JsonlAuditSink,
    JsonlMemoryStore,
    MemoryAtom,
    MemoryEvidence,
    MemoryScope,
    Task,
)
from aico.core.standing_autonomy import StandingAutonomyGrant, StandingAutonomyGrantSet


class RecordingRunner:
    def __init__(self, *, loaded: bool = True, pid: int | None = None) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.loaded = loaded
        self.pid = os.getpid() if pid is None else pid

    def __call__(self, command: tuple[str, ...]) -> CommandResult:
        self.commands.append(command)
        if command[1] == "bootout":
            self.loaded = False
        if command[1] == "bootstrap":
            self.loaded = True
        if command[1] == "print" and not self.loaded:
            return CommandResult(returncode=3, stdout="", stderr="not found")
        return CommandResult(
            returncode=0,
            stdout=f"state = running\npid = {self.pid}\n",
            stderr="",
        )


class BootstrapFailureRunner(RecordingRunner):
    def __call__(self, command: tuple[str, ...]) -> CommandResult:
        self.commands.append(command)
        if command[1] == "bootout":
            self.loaded = False
        if command[1] == "print" and not self.loaded:
            return CommandResult(returncode=3, stdout="", stderr="not found")
        if command[1] == "bootstrap":
            return CommandResult(returncode=5, stdout="", stderr="bootstrap rejected")
        return CommandResult(returncode=0, stdout="", stderr="")


class DelayedBootoutRunner(RecordingRunner):
    def __init__(self) -> None:
        super().__init__()
        self.prints_after_bootout = 0

    def __call__(self, command: tuple[str, ...]) -> CommandResult:
        self.commands.append(command)
        if command[1] == "bootout":
            return CommandResult(returncode=0, stdout="", stderr="")
        if command[1] == "print" and self.loaded:
            self.prints_after_bootout += 1
            if self.prints_after_bootout >= 2:
                self.loaded = False
            else:
                return CommandResult(returncode=0, stdout="state = running\n", stderr="")
        if command[1] == "bootstrap":
            self.loaded = True
        if command[1] == "print" and not self.loaded:
            return CommandResult(returncode=3, stdout="", stderr="not found")
        return CommandResult(returncode=0, stdout="", stderr="")


class TransientBootstrapFailureRunner(RecordingRunner):
    def __init__(self, *, loaded: bool) -> None:
        super().__init__(loaded=loaded)
        self.bootstrap_attempts = 0

    def __call__(self, command: tuple[str, ...]) -> CommandResult:
        self.commands.append(command)
        if command[1] == "bootout":
            self.loaded = False
        if command[1] == "print" and not self.loaded:
            return CommandResult(returncode=3, stdout="", stderr="not found")
        if command[1] == "bootstrap":
            self.bootstrap_attempts += 1
            if self.bootstrap_attempts == 1:
                return CommandResult(returncode=5, stdout="", stderr="Input/output error")
            self.loaded = True
        return CommandResult(returncode=0, stdout="", stderr="")


def test_launchd_plist_is_restartable_and_contains_no_secret_values(tmp_path: Path) -> None:
    context = _context(tmp_path)
    service = LaunchdService(context, runner=RecordingRunner())

    payload = service.render_plist()
    parsed = plistlib.loads(payload)

    assert parsed["ProgramArguments"] == [str(context.executable)]
    assert parsed["WorkingDirectory"] == str(context.repo)
    assert parsed["RunAtLoad"] is True
    assert parsed["KeepAlive"] == {"SuccessfulExit": False}
    assert parsed["StandardOutPath"] == str(context.stdout_log)
    assert parsed["StandardErrorPath"] == str(context.stderr_log)
    assert parsed["EnvironmentVariables"] == {
        "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
        "PYTHONUNBUFFERED": "1",
    }
    text = payload.decode("utf-8")
    assert "super-secret-token" not in text
    assert "AICO_TELEGRAM_BOT_TOKEN" not in text


def test_launchd_plist_uses_webhook_entrypoint_for_feishu_channel(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    webhook = context.repo / ".venv/bin/aico-feishu-webhook"
    webhook.write_text("#!/bin/sh\n", encoding="utf-8")
    webhook.chmod(0o755)
    context.env_file.write_text(
        context.env_file.read_text(encoding="utf-8")
        + "\nAICO_CHANNEL=feishu"
        + "\nAICO_FEISHU_APP_ID=app-id"
        + "\nAICO_FEISHU_APP_SECRET=app-secret"
        + "\nAICO_FEISHU_VERIFICATION_TOKEN=verify-token\n",
        encoding="utf-8",
    )

    payload = plistlib.loads(LaunchdService(context, runner=RecordingRunner()).render_plist())

    assert payload["ProgramArguments"] == [str(webhook)]
    assert not any(check.status == "fail" for check in readiness_checks(context))


def test_service_install_backs_up_changed_plist_and_uses_user_launchd_domain(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    runner = RecordingRunner()
    service = LaunchdService(context, runner=runner)
    context.plist_path.parent.mkdir(parents=True)
    context.plist_path.write_text("old plist", encoding="utf-8")

    backup = service.install()

    assert backup == context.plist_path.with_suffix(".plist.previous")
    assert backup.read_text(encoding="utf-8") == "old plist"
    assert plistlib.loads(context.plist_path.read_bytes())["Label"] == context.label
    assert runner.commands == [
        ("launchctl", "bootout", "gui/501/com.aico.phase1"),
        ("launchctl", "print", "gui/501/com.aico.phase1"),
        ("launchctl", "bootstrap", "gui/501", str(context.plist_path)),
        ("launchctl", "kickstart", "-k", "gui/501/com.aico.phase1"),
    ]


def test_service_install_waits_for_delayed_bootout(tmp_path: Path) -> None:
    context = _context(tmp_path)
    runner = DelayedBootoutRunner()
    sleeps: list[float] = []

    LaunchdService(context, runner=runner, sleeper=sleeps.append).install()

    assert runner.prints_after_bootout == 2
    assert sleeps == [0.05]
    assert runner.loaded is True


def test_service_install_retries_transient_bootstrap_failure(tmp_path: Path) -> None:
    context = _context(tmp_path)
    runner = TransientBootstrapFailureRunner(loaded=True)
    sleeps: list[float] = []

    LaunchdService(context, runner=runner, sleeper=sleeps.append).install()

    assert runner.bootstrap_attempts == 2
    assert sleeps == [0.1]
    assert runner.loaded is True


def test_service_restart_bootstraps_an_unloaded_service(tmp_path: Path) -> None:
    context = _context(tmp_path)
    service = LaunchdService(context, runner=RecordingRunner())
    context.plist_path.parent.mkdir(parents=True)
    context.plist_path.write_bytes(service.render_plist())
    runner = TransientBootstrapFailureRunner(loaded=False)
    sleeps: list[float] = []

    LaunchdService(context, runner=runner, sleeper=sleeps.append).restart()

    assert runner.bootstrap_attempts == 2
    assert runner.commands == [
        ("launchctl", "print", "gui/501/com.aico.phase1"),
        ("launchctl", "bootstrap", "gui/501", str(context.plist_path)),
        ("launchctl", "print", "gui/501/com.aico.phase1"),
        ("launchctl", "bootstrap", "gui/501", str(context.plist_path)),
        ("launchctl", "kickstart", "-k", "gui/501/com.aico.phase1"),
    ]


def test_service_uninstall_moves_plist_to_trash(tmp_path: Path) -> None:
    context = _context(tmp_path)
    runner = RecordingRunner()
    service = LaunchdService(context, runner=runner)
    context.plist_path.parent.mkdir(parents=True)
    context.plist_path.write_bytes(service.render_plist())

    recovered = service.uninstall()

    assert not context.plist_path.exists()
    assert recovered is not None
    assert recovered.parent == context.home / ".Trash"
    assert recovered.exists()
    assert runner.commands == [("launchctl", "bootout", "gui/501/com.aico.phase1")]


def test_service_doctor_is_secret_safe_and_reports_preinstall_readiness(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    output = io.StringIO()
    error = io.StringIO()

    exit_code = run_service_cli(
        ["--repo", str(context.repo), "doctor"],
        stdout=output,
        stderr=error,
        home=context.home,
        platform="darwin",
        uid=501,
        environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
        runner=RecordingRunner(loaded=False),
        now=lambda: datetime(2026, 7, 21, 12, tzinfo=UTC),
    )

    report = output.getvalue()
    assert exit_code == 0
    assert error.getvalue() == ""
    assert "[OK] env required keys" in report
    assert "[WARN] runtime alerts: disabled" in report
    assert "[WARN] runtime liveness: disabled" in report
    assert "[WARN] absence admission: optional" in report
    assert "[OK] IM ingress: 1 owner sender(s), 1 trusted target(s)" in report
    assert "[OK] approval lease: expires after 86400s" in report
    assert "[OK] audit integrity: ready, no events" in report
    assert "[OK] memory integrity: ready, no records" in report
    assert "[WARN] plist installed" in report
    assert "[WARN] runtime owner: missing" in report
    assert "super-secret-token" not in report


def test_service_readiness_reports_sealed_audit_and_rejects_tampering(tmp_path: Path) -> None:
    context = _context(tmp_path)
    audit_path = context.repo / ".aico/audit.jsonl"
    event = InMemoryAuditLog(event_id_factory=lambda: "audit-event").record(
        AuditEventType.TASK_SUBMITTED,
        Task(
            task_id="task-audit",
            payload="private customer operation",
            requester_id="owner",
            target_persona="reviewer",
        ),
    )
    JsonlAuditSink(audit_path).write(event)

    healthy = readiness_checks(context)
    assert next(check for check in healthy if check.name == "audit integrity").detail == (
        "sealed, 1 event(s)"
    )

    audit_path.write_bytes(audit_path.read_bytes().replace(b'"task-audit"', b'"task-other"'))
    corrupted = next(
        check for check in readiness_checks(context) if check.name == "audit integrity"
    )
    assert corrupted.status == "fail"
    assert "hash chain" in corrupted.detail
    assert "private customer operation" not in corrupted.detail


def test_service_readiness_rejects_unsealed_legacy_audit(tmp_path: Path) -> None:
    context = _context(tmp_path)
    audit_path = context.repo / ".aico/audit.jsonl"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text(
        InMemoryAuditLog(event_id_factory=lambda: "legacy-event")
        .record(
            AuditEventType.TASK_SUBMITTED,
            Task(
                task_id="task-legacy",
                payload="inspect",
                requester_id="owner",
                target_persona="reviewer",
            ),
        )
        .model_dump_json()
        + "\n",
        encoding="utf-8",
    )
    audit_path.chmod(0o600)

    check = next(check for check in readiness_checks(context) if check.name == "audit integrity")

    assert check.status == "fail"
    assert check.detail == "audit ledger is unsealed; run aico-audit seal"


def test_service_readiness_reports_memory_integrity_and_rejects_tampering(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    memory_path = context.repo / ".aico/memory.jsonl"
    JsonlMemoryStore(memory_path).append_atom(
        MemoryAtom(
            memory_id="memory-doctor",
            claim="private customer fact",
            evidence=(MemoryEvidence(ref="task:doctor", source="test"),),
            scope=MemoryScope.project("aico"),
            source="test",
            confidence=0.9,
            created_by="test-agent",
        )
    )

    healthy = next(check for check in readiness_checks(context) if check.name == "memory integrity")
    assert healthy.detail == "sealed, 1 record(s)"

    memory_path.write_bytes(
        memory_path.read_bytes().replace(b"private customer fact", b"private customer fake")
    )
    corrupted = next(
        check for check in readiness_checks(context) if check.name == "memory integrity"
    )
    assert corrupted.status == "fail"
    assert "hash chain" in corrupted.detail
    assert "private customer fact" not in corrupted.detail


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("AICO_OWNER_SENDER_IDS", ""),
        ("AICO_OWNER_SENDER_IDS", "replace-with-private-owner"),
        ("AICO_TRUSTED_TARGET_IDS", ""),
        ("AICO_TRUSTED_TARGET_IDS", "replace-with-private-chat"),
    ],
)
def test_service_readiness_rejects_unbound_ingress_without_identity_leak(
    tmp_path: Path,
    key: str,
    value: str,
) -> None:
    context = _context(tmp_path)
    original = context.env_file.read_text(encoding="utf-8")
    lines = [line for line in original.splitlines() if not line.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    context.env_file.write_text("\n".join(lines), encoding="utf-8")

    check = next(item for item in readiness_checks(context) if item.name == "IM ingress")

    assert check.status == "fail"
    assert check.detail == "requires owner sender ids and trusted target ids"
    if value:
        assert value not in str(check)


def test_service_readiness_rejects_ingress_identity_discovery_mode(tmp_path: Path) -> None:
    context = _context(tmp_path)
    context.env_file.write_text(
        context.env_file.read_text(encoding="utf-8")
        + "\nAICO_INGRESS_DISCOVERY_LOG_IDENTITIES=true\n",
        encoding="utf-8",
    )

    check = next(item for item in readiness_checks(context) if item.name == "IM ingress")

    assert check.status == "fail"
    assert check.detail == "identity discovery must be disabled before install"


@pytest.mark.parametrize("value", ["299", "604801", "private-invalid-duration"])
def test_service_readiness_rejects_unbounded_approval_lease_without_leaking_value(
    tmp_path: Path,
    value: str,
) -> None:
    context = _context(tmp_path)
    context.env_file.write_text(
        context.env_file.read_text(encoding="utf-8") + f"\nAICO_APPROVAL_MAX_AGE_SECONDS={value}\n",
        encoding="utf-8",
    )

    check = next(item for item in readiness_checks(context) if item.name == "approval lease")

    assert check.status == "fail"
    assert check.detail == "must be an integer between 300 and 604800 seconds"
    assert value not in str(check)


def test_service_readiness_rejects_unsafe_alert_webhook_without_leaking_value(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    context.env_file.write_text(
        context.env_file.read_text(encoding="utf-8")
        + "\nAICO_RUNTIME_ALERT_WEBHOOK_URL=http://secret-alert-host.test/hook"
        + "\nAICO_RUNTIME_ALERT_WEBHOOK_BEARER_TOKEN=alert-secret\n",
        encoding="utf-8",
    )

    checks = readiness_checks(context)
    alert_check = next(check for check in checks if check.name == "runtime alerts")

    assert alert_check.status == "fail"
    assert alert_check.detail == "AICO_RUNTIME_ALERT_WEBHOOK_URL must use HTTPS"
    assert "secret-alert-host" not in str(checks)
    assert "alert-secret" not in str(checks)


def test_service_readiness_validates_external_dead_man_monitor_without_identity_leak(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    base = context.env_file.read_text(encoding="utf-8")
    context.env_file.write_text(
        base
        + "\nAICO_RUNTIME_LIVENESS_WEBHOOK_URL=https://receiver.example.test/private"
        + "\nAICO_RUNTIME_LIVENESS_ENABLED=true"
        + "\nAICO_RUNTIME_MONITOR_ID=owner-runtime"
        + "\nAICO_RUNTIME_LIVENESS_INTERVAL_SECONDS=60"
        + "\nAICO_RUNTIME_LIVENESS_TTL_SECONDS=120\n",
        encoding="utf-8",
    )

    invalid = next(check for check in readiness_checks(context) if check.name == "runtime liveness")
    context.env_file.write_text(
        context.env_file.read_text(encoding="utf-8").replace(
            "AICO_RUNTIME_LIVENESS_TTL_SECONDS=120",
            "AICO_RUNTIME_LIVENESS_TTL_SECONDS=180",
        ),
        encoding="utf-8",
    )
    ready = next(check for check in readiness_checks(context) if check.name == "runtime liveness")

    assert invalid.status == "fail"
    assert invalid.detail == "runtime liveness TTL must be at least three pulse intervals"
    assert ready.status == "ok"
    assert ready.detail == "external dead-man pulse configured"
    assert "owner-runtime" not in str((invalid, ready))
    assert "receiver.example.test" not in str((invalid, ready))


def test_service_readiness_rejects_liveness_token_without_dedicated_url(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    context.env_file.write_text(
        context.env_file.read_text(encoding="utf-8")
        + "\nAICO_RUNTIME_LIVENESS_WEBHOOK_BEARER_TOKEN=pulse-secret\n",
        encoding="utf-8",
    )

    check = next(item for item in readiness_checks(context) if item.name == "runtime liveness")

    assert check.status == "fail"
    assert check.detail == "liveness bearer token configured without liveness webhook URL"
    assert "pulse-secret" not in str(check)


@pytest.mark.parametrize("reuse", ["url", "token"])
def test_service_readiness_rejects_runtime_webhook_authority_reuse_without_leak(
    tmp_path: Path,
    reuse: str,
) -> None:
    context = _context(tmp_path)
    alert_url = "https://alerts.example.test/runtime"
    liveness_url = alert_url if reuse == "url" else "https://receiver.example.test/pulses"
    alert_token = "shared-private-token" if reuse == "token" else "alert-private-token"
    liveness_token = "shared-private-token" if reuse == "token" else "pulse-private-token"
    _append_env(
        context,
        "\n".join(
            (
                f"AICO_RUNTIME_ALERT_WEBHOOK_URL={alert_url}",
                f"AICO_RUNTIME_ALERT_WEBHOOK_BEARER_TOKEN={alert_token}",
                "AICO_RUNTIME_LIVENESS_ENABLED=true",
                f"AICO_RUNTIME_LIVENESS_WEBHOOK_URL={liveness_url}",
                f"AICO_RUNTIME_LIVENESS_WEBHOOK_BEARER_TOKEN={liveness_token}",
                "AICO_RUNTIME_MONITOR_ID=owner-runtime",
            )
        ),
    )

    check = next(
        item for item in readiness_checks(context) if item.name == "runtime endpoint isolation"
    )

    assert check.status == "fail"
    assert "must be distinct" in check.detail
    rendered = str(check)
    for private_value in (alert_url, liveness_url, alert_token, liveness_token):
        assert private_value not in rendered


def test_service_readiness_verifies_owner_bound_standing_autonomy_without_identity_leak(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    grant_path, _ = _configure_standing_autonomy(context, tmp_path)

    check = next(item for item in readiness_checks(context) if item.name == "standing autonomy")

    assert check.status == "ok"
    assert check.detail == "owner-bound runtime binding verified (1 grants)"
    assert "owner-telegram-private" not in str(check)
    assert "chat-private" not in str(check)
    assert str(grant_path) not in str(check)
    assert not (context.repo / ".aico").exists()

    grant_path.chmod(0o644)
    unsafe = next(item for item in readiness_checks(context) if item.name == "standing autonomy")
    assert unsafe.status == "fail"
    assert unsafe.detail == "standing autonomy grant must be owner-only"


def test_service_readiness_ignores_ambient_dotenv_during_explicit_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ambient = tmp_path / "ambient"
    ambient.mkdir()
    (ambient / ".env").write_text(
        "AICO_PERSONA_CONFIG_PATH=missing-ambient-personas.json\nAICO_ENABLE_CURSOR_ADAPTER=true\n",
        encoding="utf-8",
    )
    context = _context(tmp_path / "service")
    _configure_standing_autonomy(context, tmp_path / "service")
    monkeypatch.chdir(ambient)

    check = next(item for item in readiness_checks(context) if item.name == "standing autonomy")

    assert check.status == "ok"
    assert check.detail == "owner-bound runtime binding verified (1 grants)"


def test_service_readiness_preflights_scheduled_recovery_destination(tmp_path: Path) -> None:
    context = _context(tmp_path)
    output = tmp_path / "private-recovery"
    output.mkdir()
    output.chmod(0o700)
    context.env_file.write_text(
        context.env_file.read_text(encoding="utf-8")
        + "\nAICO_REVIEWED_CONFIG_REVISION="
        + "a" * 40
        + "\nAICO_RECOVERY_BACKUP_ENABLED=true"
        + f"\nAICO_RECOVERY_BACKUP_OUTPUT_DIR={output}\n",
        encoding="utf-8",
    )

    check = next(item for item in readiness_checks(context) if item.name == "recovery backup")

    assert check.status == "ok"
    assert check.detail == "capture, verify, and custody configured; storage class not attested"
    assert str(output) not in str(check)
    assert not (context.repo / ".aico").exists()

    context.env_file.write_text(
        context.env_file.read_text(encoding="utf-8") + "\nAICO_RECOVERY_DRILL_ENABLED=true\n",
        encoding="utf-8",
    )
    drilled = next(item for item in readiness_checks(context) if item.name == "recovery backup")
    assert drilled.status == "ok"
    assert drilled.detail == (
        "capture, verify, custody, and disposable drill configured; storage class not attested"
    )

    output.chmod(0o755)
    unsafe = next(item for item in readiness_checks(context) if item.name == "recovery backup")
    assert unsafe.status == "fail"
    assert unsafe.detail == "scheduled capture destination or binding is invalid"
    assert str(output) not in str(unsafe)


@pytest.mark.parametrize(
    "invalid_binding",
    [
        "target",
        "codex-disabled",
        "wrapper",
        "invalid-setting",
        "malformed-project",
        "unknown-project",
        "missing-charter",
        "missing-seat",
        "missing-persona",
    ],
)
def test_service_readiness_rejects_invalid_standing_runtime_binding_without_leak(
    tmp_path: Path,
    invalid_binding: str,
) -> None:
    context = _context(tmp_path)
    grant_path, project_path = _configure_standing_autonomy(context, tmp_path)
    if invalid_binding == "target":
        _append_env(context, "AICO_MORNING_PUSH_TARGET_ID=another-private-chat")
    elif invalid_binding == "codex-disabled":
        _append_env(context, "AICO_ENABLE_CODEX_ADAPTER=false")
    elif invalid_binding == "wrapper":
        _append_env(context, "AICO_CODEX_COMMAND=private-provider-wrapper exec")
    elif invalid_binding == "invalid-setting":
        _append_env(context, "AICO_CODEX_MAX_CONCURRENT_TASKS=private-invalid-count")
    elif invalid_binding == "malformed-project":
        project_path.write_text("private malformed project", encoding="utf-8")
    elif invalid_binding == "unknown-project":
        grant_payload = json.loads(grant_path.read_text(encoding="utf-8"))
        grant_payload["grants"][0]["project_id"] = "private-unknown-project"
        grant_path.write_text(json.dumps(grant_payload), encoding="utf-8")
        _append_env(context, "AICO_MORNING_PUSH_PROJECT=private-unknown-project")
    elif invalid_binding == "missing-persona":
        persona_path = context.repo / "config/private-personas.json"
        persona_path.write_text(
            json.dumps(
                [
                    {
                        "name": "implementer",
                        "adapter_name": "claude-code",
                        "aliases": ["claude"],
                    }
                ]
            ),
            encoding="utf-8",
        )
        _append_env(context, "AICO_PERSONA_CONFIG_PATH=config/private-personas.json")
    else:
        payload = json.loads(project_path.read_text(encoding="utf-8"))
        if invalid_binding == "missing-charter":
            payload["projects"]["aico"]["standing_charter"] = []
        else:
            payload["assignments"] = []
        project_path.write_text(json.dumps(payload), encoding="utf-8")

    check = next(item for item in readiness_checks(context) if item.name == "standing autonomy")

    assert check.status == "fail"
    assert check.detail == "standing autonomy runtime binding is invalid"
    rendered = str(check)
    for private_value in (
        "owner-telegram-private",
        "chat-private",
        "another-private-chat",
        "private-provider-wrapper",
        "private-invalid-count",
        "private malformed project",
        "private-unknown-project",
        "private-personas",
        str(grant_path),
        str(project_path),
    ):
        assert private_value not in rendered
    assert not (context.repo / ".aico").exists()


def test_service_readiness_rejects_configured_empty_standing_grant_set(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    grant_path, _ = _configure_standing_autonomy(context, tmp_path)
    grant_path.write_text(StandingAutonomyGrantSet().model_dump_json(), encoding="utf-8")

    check = next(item for item in readiness_checks(context) if item.name == "standing autonomy")

    assert check.status == "fail"
    assert check.detail == "standing autonomy grant file contains no grants"


def test_service_doctor_fails_for_stale_loaded_runtime_without_leaking_env(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    service = LaunchdService(context, runner=RecordingRunner())
    context.plist_path.parent.mkdir(parents=True)
    context.plist_path.write_bytes(service.render_plist())
    context.heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    context.heartbeat_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "state": "running",
                "pid": 123,
                "started_at": "2026-07-21T10:00:00+00:00",
                "heartbeat_at": "2026-07-21T10:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    output = io.StringIO()

    exit_code = run_service_cli(
        ["--repo", str(context.repo), "doctor"],
        stdout=output,
        home=context.home,
        platform="darwin",
        uid=501,
        environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
        runner=RecordingRunner(),
        now=lambda: datetime(2026, 7, 21, 12, tzinfo=UTC),
    )

    assert exit_code == 2
    assert "[FAIL] runtime owner: loaded service has no active owner" in output.getvalue()
    assert "[FAIL] heartbeat: stale" in output.getvalue()
    assert "super-secret-token" not in output.getvalue()


def test_service_doctor_fails_for_fresh_required_component_failure(
    tmp_path: Path,
) -> None:
    context = _installed_context(tmp_path)
    _write_component_heartbeat(context, aggregate="failed", component_required=True)
    output = io.StringIO()

    exit_code = run_service_cli(
        ["--repo", str(context.repo), "doctor"],
        stdout=output,
        home=context.home,
        platform="darwin",
        uid=501,
        environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
        runner=RecordingRunner(),
        now=lambda: datetime(2026, 7, 21, 12, tzinfo=UTC),
    )

    assert exit_code == 2
    assert "[FAIL] heartbeat: components failed: channel:telegram" in output.getvalue()


def test_service_doctor_warns_for_fresh_optional_component_degradation(
    tmp_path: Path,
) -> None:
    context = _installed_context(tmp_path)
    _write_component_heartbeat(context, aggregate="degraded", component_required=False)
    owner = _active_owner(context)
    output = io.StringIO()

    try:
        exit_code = run_service_cli(
            ["--repo", str(context.repo), "doctor"],
            stdout=output,
            home=context.home,
            platform="darwin",
            uid=501,
            environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
            runner=RecordingRunner(),
            now=lambda: datetime(2026, 7, 21, 12, tzinfo=UTC),
        )
    finally:
        owner.release()

    assert exit_code == 0
    assert "matches launchd" in output.getvalue()
    assert "[WARN] heartbeat: components degraded: adapter:codex" in output.getvalue()


def test_service_doctor_fails_for_open_owned_task_recovery_circuit(
    tmp_path: Path,
) -> None:
    context = _installed_context(tmp_path)
    _write_recovery_heartbeat(context, recovery_status="open", attempts=3)
    owner = _active_owner(context)
    output = io.StringIO()

    try:
        exit_code = run_service_cli(
            ["--repo", str(context.repo), "doctor"],
            stdout=output,
            home=context.home,
            platform="darwin",
            uid=501,
            environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
            runner=RecordingRunner(),
            now=lambda: datetime(2026, 7, 21, 12, tzinfo=UTC),
        )
    finally:
        owner.release()

    assert exit_code == 2
    assert (
        "[FAIL] heartbeat: owned task recovery open: channel:telegram-polling" in output.getvalue()
    )


def test_service_doctor_warns_for_pending_out_of_band_alert(tmp_path: Path) -> None:
    context = _installed_context(tmp_path)
    _write_alerting_heartbeat(context, alerting_status="pending", pending_events=2)
    owner = _active_owner(context)
    output = io.StringIO()

    try:
        exit_code = run_service_cli(
            ["--repo", str(context.repo), "doctor"],
            stdout=output,
            home=context.home,
            platform="darwin",
            uid=501,
            environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
            runner=RecordingRunner(),
            now=lambda: datetime(2026, 7, 21, 12, tzinfo=UTC),
        )
    finally:
        owner.release()

    assert exit_code == 0
    assert "[WARN] heartbeat: out-of-band alerts pending: 2" in output.getvalue()


def test_service_doctor_fails_when_manual_owner_pid_differs_from_launchd(
    tmp_path: Path,
) -> None:
    context = _installed_context(tmp_path)
    _write_component_heartbeat(context, aggregate="degraded", component_required=False)
    owner = _active_owner(context)
    output = io.StringIO()

    try:
        exit_code = run_service_cli(
            ["--repo", str(context.repo), "doctor"],
            stdout=output,
            home=context.home,
            platform="darwin",
            uid=501,
            environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
            runner=RecordingRunner(pid=os.getpid() + 1000),
            now=lambda: datetime(2026, 7, 21, 12, tzinfo=UTC),
        )
    finally:
        owner.release()

    assert exit_code == 2
    assert "[FAIL] runtime owner: owner pid=" in output.getvalue()
    assert "does not match launchd pid=" in output.getvalue()


def test_service_install_refuses_unsafe_env_permissions(tmp_path: Path) -> None:
    context = _context(tmp_path)
    context.env_file.chmod(0o644)
    output = io.StringIO()
    runner = RecordingRunner()

    exit_code = run_service_cli(
        ["--repo", str(context.repo), "install"],
        stdout=output,
        home=context.home,
        platform="darwin",
        uid=501,
        environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
        runner=runner,
    )

    assert exit_code == 2
    assert "[FAIL] env permissions" in output.getvalue()
    assert runner.commands == []


def test_service_install_strict_absence_admission_refuses_disabled_contracts(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    _append_env(context, "AICO_ABSENCE_ADMISSION_MODE=strict")
    output = io.StringIO()
    runner = RecordingRunner()

    exit_code = run_service_cli(
        ["--repo", str(context.repo), "install"],
        stdout=output,
        home=context.home,
        platform="darwin",
        uid=501,
        environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
        runner=runner,
    )

    report = output.getvalue()
    assert exit_code == 2
    assert "[FAIL] absence admission: strict machine contracts not ready:" in report
    for contract in (
        "runtime alerts",
        "runtime liveness",
        "runtime commissioning",
        "recovery backup",
        "standing autonomy",
        "recovery drill",
    ):
        assert contract in report
    assert "super-secret-token" not in report
    assert runner.commands == []


def test_service_readiness_strict_absence_admission_accepts_machine_contracts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path)
    _configure_standing_autonomy(context, tmp_path)
    output = tmp_path / "private-recovery"
    output.mkdir()
    output.chmod(0o700)
    commissioning = tmp_path / "commissioning.json"
    evidence = tmp_path / "dead-man.json"
    public_key = tmp_path / "receiver-public.pem"
    monkeypatch.setattr(
        "aico.app.service_cli.verify_runtime_commissioning_receipt",
        lambda **_: None,
    )
    _append_env(
        context,
        "\n".join(
            (
                "AICO_ABSENCE_ADMISSION_MODE=strict",
                "AICO_RUNTIME_ALERT_WEBHOOK_URL=https://alerts.example.test/runtime",
                "AICO_RUNTIME_LIVENESS_ENABLED=true",
                "AICO_RUNTIME_LIVENESS_WEBHOOK_URL=https://receiver.example.test/pulses",
                "AICO_RUNTIME_MONITOR_ID=owner-runtime",
                "AICO_RUNTIME_LIVENESS_INTERVAL_SECONDS=60",
                "AICO_RUNTIME_LIVENESS_TTL_SECONDS=300",
                f"AICO_REVIEWED_CONFIG_REVISION={'a' * 40}",
                "AICO_RECOVERY_BACKUP_ENABLED=true",
                f"AICO_RECOVERY_BACKUP_OUTPUT_DIR={output}",
                "AICO_RECOVERY_DRILL_ENABLED=true",
                f"AICO_COMMISSIONING_RECEIPT_PATH={commissioning}",
                f"AICO_COMMISSIONING_DEAD_MAN_EVIDENCE_PATH={evidence}",
                f"AICO_COMMISSIONING_RECEIVER_PUBLIC_KEY_PATH={public_key}",
            )
        ),
    )

    checks = readiness_checks(context)
    admission = next(check for check in checks if check.name == "absence admission")

    assert not any(check.status == "fail" for check in checks)
    assert admission.status == "ok"
    assert admission.detail == (
        "strict machine contracts configured; receiver-signed evidence bound; "
        "receiver host and human read not attested"
    )
    rendered = str(checks)
    assert "alerts.example.test" not in rendered
    assert "receiver.example.test" not in rendered
    assert str(output) not in rendered

    _append_env(context, "AICO_RECOVERY_DRILL_ENABLED=false")
    without_drill = next(
        check for check in readiness_checks(context) if check.name == "absence admission"
    )
    assert without_drill.status == "fail"
    assert without_drill.detail == "strict machine contracts not ready: recovery drill"


@pytest.mark.parametrize("mode", ["production", "private-secret-mode"])
def test_service_readiness_rejects_unknown_absence_admission_mode_without_leak(
    tmp_path: Path,
    mode: str,
) -> None:
    context = _context(tmp_path)
    _append_env(context, f"AICO_ABSENCE_ADMISSION_MODE={mode}")

    check = next(item for item in readiness_checks(context) if item.name == "absence admission")

    assert check.status == "fail"
    assert check.detail == "AICO_ABSENCE_ADMISSION_MODE must be optional or strict"
    assert mode not in str(check)


def test_service_install_refuses_placeholder_env_without_leaking_value(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    context.env_file.write_text(
        context.env_file.read_text(encoding="utf-8").replace(
            "super-secret-token", "replace-with-your-bot-token"
        ),
        encoding="utf-8",
    )
    context.env_file.chmod(0o600)
    output = io.StringIO()
    runner = RecordingRunner()

    exit_code = run_service_cli(
        ["--repo", str(context.repo), "install"],
        stdout=output,
        home=context.home,
        platform="darwin",
        uid=501,
        environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
        runner=runner,
    )

    report = output.getvalue()
    assert exit_code == 2
    assert "missing or placeholder: AICO_TELEGRAM_BOT_TOKEN" in report
    assert "replace-with-your-bot-token" not in report
    assert runner.commands == []


def test_service_install_refuses_unknown_channel_before_launchctl(tmp_path: Path) -> None:
    context = _context(tmp_path)
    context.env_file.write_text(
        context.env_file.read_text(encoding="utf-8") + "\nAICO_CHANNEL=unknown\n",
        encoding="utf-8",
    )
    output = io.StringIO()
    runner = RecordingRunner()

    exit_code = run_service_cli(
        ["--repo", str(context.repo), "install"],
        stdout=output,
        home=context.home,
        platform="darwin",
        uid=501,
        environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
        runner=runner,
    )

    assert exit_code == 2
    assert "[FAIL] channel: unknown" in output.getvalue()
    assert runner.commands == []


def test_service_install_failure_keeps_previous_plist_backup(tmp_path: Path) -> None:
    context = _context(tmp_path)
    context.plist_path.parent.mkdir(parents=True)
    context.plist_path.write_text("previous service", encoding="utf-8")
    error = io.StringIO()

    exit_code = run_service_cli(
        ["--repo", str(context.repo), "install"],
        stderr=error,
        home=context.home,
        platform="darwin",
        uid=501,
        environ={"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
        runner=BootstrapFailureRunner(),
    )

    backup = context.plist_path.with_suffix(".plist.previous")
    assert exit_code == 2
    assert backup.read_text(encoding="utf-8") == "previous service"
    assert "bootstrap rejected" in error.getvalue()
    assert "super-secret-token" not in error.getvalue()


def test_service_status_refuses_non_macos_without_running_command(tmp_path: Path) -> None:
    context = _context(tmp_path)
    runner = RecordingRunner()
    error = io.StringIO()

    exit_code = run_service_cli(
        ["--repo", str(context.repo), "status"],
        stderr=error,
        home=context.home,
        platform="linux",
        uid=501,
        environ={"PATH": "/usr/bin:/bin"},
        runner=runner,
    )

    assert exit_code == 2
    assert "status requires macOS launchd" in error.getvalue()
    assert runner.commands == []


def _context(tmp_path: Path) -> ServiceContext:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    executable = repo / ".venv/bin/aico-phase1"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)
    env_file = repo / ".env"
    env_file.write_text(
        "\n".join(
            (
                "AICO_TELEGRAM_BOT_TOKEN=super-secret-token",
                "AICO_CLAUDE_WORKING_DIRECTORY=/repo",
                "AICO_PROJECT_CONFIG_PATH=config/projects.example.json",
                "AICO_STATE_DB_PATH=.aico/state.db",
                "AICO_AUDIT_LOG_PATH=.aico/audit.jsonl",
                "AICO_MEMORY_PATH=.aico/memory.jsonl",
                "AICO_OWNER_SENDER_IDS=owner-private",
                "AICO_TRUSTED_TARGET_IDS=chat-private",
            )
        ),
        encoding="utf-8",
    )
    env_file.chmod(0o600)
    return ServiceContext(
        repo=repo,
        home=home,
        label="com.aico.phase1",
        uid=501,
        platform="darwin",
        path_env="/opt/homebrew/bin:/usr/bin:/bin",
    )


def _configure_standing_autonomy(
    context: ServiceContext,
    tmp_path: Path,
) -> tuple[Path, Path]:
    managed_project = context.repo / "managed-project"
    managed_project.mkdir()
    (managed_project / "STATUS.md").write_text("# Current status\nEvidence is current.\n")
    project_path = context.repo / "config/standing-projects.json"
    project_path.parent.mkdir()
    project_path.write_text(
        json.dumps(
            {
                "agents": {
                    "codex": {
                        "id": "codex",
                        "provider": "codex",
                        "title": "Independent Reviewer",
                    }
                },
                "roles": {"reviewer": {"id": "reviewer", "title": "Independent Reviewer"}},
                "projects": {
                    "aico": {
                        "id": "aico",
                        "name": "AI Company OS",
                        "repo": str(managed_project),
                        "default_assignment": "aico-reviewer",
                        "standing_charter": [
                            {
                                "id": "absence-loop",
                                "objective": "Inspect current recovery evidence.",
                                "role": "reviewer",
                                "acceptance_evidence": ["one bounded report"],
                                "stop_conditions": ["stop before external communication"],
                                "evidence_sources": [{"path": "STATUS.md"}],
                            }
                        ],
                    }
                },
                "assignments": [
                    {
                        "project": "aico",
                        "agent": "codex",
                        "role": "reviewer",
                        "seat": "aico-reviewer",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    grant_path = tmp_path / "private-standing-autonomy.json"
    grant_path.write_text(
        StandingAutonomyGrantSet(
            grants=(
                StandingAutonomyGrant(
                    grant_id="grant-private-1",
                    owner_id="owner-private",
                    channel_name="telegram",
                    target_id="chat-private",
                    project_id="aico",
                    charter_id="absence-loop",
                    expires_at=datetime(2027, 1, 1, tzinfo=UTC),
                    max_runs=1,
                    max_duration_seconds=300,
                    max_total_tokens=50_000,
                    token_stop_threshold=100_000,
                ),
            )
        ).model_dump_json(),
        encoding="utf-8",
    )
    grant_path.chmod(0o600)
    _append_env(
        context,
        "\n".join(
            (
                f"AICO_STANDING_AUTONOMY_GRANT_PATH={grant_path}",
                "AICO_MORNING_PUSH_ENABLED=true",
                "AICO_MORNING_PUSH_TARGET_ID=chat-private",
                "AICO_MORNING_PUSH_PROJECT=aico",
                "AICO_ENABLE_CODEX_ADAPTER=true",
                "AICO_CODEX_COMMAND=codex exec --sandbox read-only",
                "AICO_PROJECT_CONFIG_PATH=config/standing-projects.json",
            )
        ),
    )
    return grant_path, project_path


def _append_env(context: ServiceContext, content: str) -> None:
    context.env_file.write_text(
        f"{context.env_file.read_text(encoding='utf-8')}\n{content}\n",
        encoding="utf-8",
    )


def _installed_context(tmp_path: Path) -> ServiceContext:
    context = _context(tmp_path)
    service = LaunchdService(context, runner=RecordingRunner())
    context.plist_path.parent.mkdir(parents=True)
    context.plist_path.write_bytes(service.render_plist())
    context.heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    return context


def _write_component_heartbeat(
    context: ServiceContext,
    *,
    aggregate: str,
    component_required: bool,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    component_kind = "channel" if component_required else "adapter"
    component_name = "telegram" if component_required else "codex"
    context.heartbeat_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "state": "running",
                "pid": 123,
                "started_at": now.isoformat(),
                "heartbeat_at": now.isoformat(),
                "health": {
                    "status": aggregate,
                    "checked_at": now.isoformat(),
                    "components": [
                        {
                            "kind": component_kind,
                            "name": component_name,
                            "required": component_required,
                            "status": "failed",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )


def _write_recovery_heartbeat(
    context: ServiceContext,
    *,
    recovery_status: str,
    attempts: int,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    context.heartbeat_path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "state": "running",
                "pid": os.getpid(),
                "started_at": now.isoformat(),
                "heartbeat_at": now.isoformat(),
                "health": {
                    "status": "ok",
                    "checked_at": now.isoformat(),
                    "components": [],
                },
                "self_healing": {
                    "status": recovery_status,
                    "checked_at": now.isoformat(),
                    "components": [
                        {
                            "name": "channel:telegram-polling",
                            "status": recovery_status,
                            "attempts": attempts,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )


def _write_alerting_heartbeat(
    context: ServiceContext,
    *,
    alerting_status: str,
    pending_events: int | None,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    context.heartbeat_path.write_text(
        json.dumps(
            {
                "schema_version": 4,
                "state": "running",
                "pid": os.getpid(),
                "started_at": now.isoformat(),
                "heartbeat_at": now.isoformat(),
                "health": {
                    "status": "ok",
                    "checked_at": now.isoformat(),
                    "components": [],
                },
                "self_healing": {
                    "status": "healthy",
                    "checked_at": now.isoformat(),
                    "components": [],
                },
                "alerting": {
                    "status": alerting_status,
                    "checked_at": now.isoformat(),
                    "pending_events": pending_events,
                },
            }
        ),
        encoding="utf-8",
    )


def _active_owner(context: ServiceContext) -> RuntimeOwnerLock:
    owner = RuntimeOwnerLock(context.owner_lock_path, resource_path=context.repo / ".aico/state.db")
    owner.acquire()
    return owner
