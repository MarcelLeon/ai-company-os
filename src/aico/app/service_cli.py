"""Manage the macOS LaunchAgent that keeps AICO available while the boss is absent."""

from __future__ import annotations

import argparse
import os
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TextIO

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from aico.app.absence_admission import (
    ABSENCE_ADMISSION_MODES,
    runtime_webhook_isolation_error,
    strict_absence_contract_gaps,
)
from aico.app.phase1 import (
    Phase1Settings,
    preflight_recovery_backup,
    preflight_standing_autonomy,
)
from aico.app.runtime_commissioning import (
    RuntimeCommissioningError,
    verify_runtime_commissioning_receipt,
)
from aico.app.runtime_heartbeat import heartbeat_health
from aico.app.runtime_owner import runtime_owner_lock_path, runtime_owner_status
from aico.core.approval import (
    DEFAULT_APPROVAL_MAX_AGE_SECONDS,
    MAX_APPROVAL_MAX_AGE_SECONDS,
    MIN_APPROVAL_MAX_AGE_SECONDS,
)
from aico.core.audit_ledger import AuditIntegrityError, verify_audit_ledger
from aico.core.ingress_authorization import IngressBindingError, parse_ingress_ids
from aico.core.memory_ledger import MemoryIntegrityError, verify_memory_ledger
from aico.core.standing_autonomy import (
    StandingAutonomyConfigError,
    load_standing_autonomy_grants,
)

DEFAULT_LABEL = "com.aico.phase1"
DEFAULT_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
_PLACEHOLDER_FRAGMENTS = (
    "replace-with",
    "replace-me",
    "your-",
    "/absolute/path/to",
    "<",
    ">",
)
CheckStatus = Literal["ok", "warn", "fail"]


class _ExplicitPhase1Settings(Phase1Settings):
    """Validate one already-selected service config without ambient settings sources."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        del cls, settings_cls, env_settings, dotenv_settings, file_secret_settings
        return (init_settings,)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


CommandRunner = Callable[[tuple[str, ...]], CommandResult]


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: CheckStatus
    detail: str


@dataclass(frozen=True)
class ServiceContext:
    repo: Path
    home: Path
    label: str
    uid: int
    platform: str
    path_env: str

    @property
    def executable(self) -> Path:
        entrypoint = "aico-feishu-webhook" if self.configured_channel == "feishu" else "aico-phase1"
        return self.repo / ".venv/bin" / entrypoint

    @property
    def configured_channel(self) -> str:
        if not self.env_file.is_file():
            return "telegram"
        return _read_env(self.env_file).get("AICO_CHANNEL", "telegram").casefold()

    @property
    def env_file(self) -> Path:
        return self.repo / ".env"

    @property
    def plist_path(self) -> Path:
        return self.home / "Library/LaunchAgents" / f"{self.label}.plist"

    @property
    def service_dir(self) -> Path:
        return self.repo / ".aico/service"

    @property
    def stdout_log(self) -> Path:
        return self.service_dir / "stdout.log"

    @property
    def stderr_log(self) -> Path:
        return self.service_dir / "stderr.log"

    @property
    def heartbeat_path(self) -> Path:
        return self.repo / ".aico/runtime-heartbeat.json"

    @property
    def owner_lock_path(self) -> Path:
        return runtime_owner_lock_path(_configured_state_db_path(self), base_dir=self.repo)

    @property
    def service_target(self) -> str:
        return f"gui/{self.uid}/{self.label}"

    @property
    def user_domain(self) -> str:
        return f"gui/{self.uid}"


class LaunchdService:
    """One recoverable user LaunchAgent; no cross-platform abstraction until needed."""

    def __init__(self, context: ServiceContext, *, runner: CommandRunner) -> None:
        self.context = context
        self._runner = runner

    def render_plist(self) -> bytes:
        payload = {
            "Label": self.context.label,
            "ProgramArguments": [str(self.context.executable)],
            "WorkingDirectory": str(self.context.repo),
            "RunAtLoad": True,
            "KeepAlive": {"SuccessfulExit": False},
            "ThrottleInterval": 10,
            "ProcessType": "Background",
            "StandardOutPath": str(self.context.stdout_log),
            "StandardErrorPath": str(self.context.stderr_log),
            "EnvironmentVariables": {
                "PATH": self.context.path_env,
                "PYTHONUNBUFFERED": "1",
            },
        }
        return plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True)

    def install(self) -> Path | None:
        context = self.context
        context.plist_path.parent.mkdir(parents=True, exist_ok=True)
        context.service_dir.mkdir(parents=True, exist_ok=True)
        rendered = self.render_plist()
        backup: Path | None = None
        if context.plist_path.exists() and context.plist_path.read_bytes() != rendered:
            backup = context.plist_path.with_suffix(".plist.previous")
            shutil.copy2(context.plist_path, backup)
        _atomic_write(context.plist_path, rendered)
        self._runner(("launchctl", "bootout", context.service_target))
        self._require_success(
            ("launchctl", "bootstrap", context.user_domain, str(context.plist_path))
        )
        self._require_success(("launchctl", "kickstart", "-k", context.service_target))
        return backup

    def restart(self) -> None:
        if not self.context.plist_path.exists():
            raise RuntimeError("service plist is not installed")
        self._require_success(("launchctl", "kickstart", "-k", self.context.service_target))

    def status(self) -> CommandResult:
        return self._runner(("launchctl", "print", self.context.service_target))

    def uninstall(self) -> Path | None:
        self._runner(("launchctl", "bootout", self.context.service_target))
        if not self.context.plist_path.exists():
            return None
        trash = self.context.home / ".Trash"
        trash.mkdir(parents=True, exist_ok=True)
        destination = _unique_trash_path(trash, self.context.plist_path.name)
        shutil.move(str(self.context.plist_path), destination)
        return destination

    def _require_success(self, command: tuple[str, ...]) -> None:
        result = self._runner(command)
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown launchctl error"
            raise RuntimeError(f"{' '.join(command[:2])} failed: {detail}")


def run_service_cli(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    home: Path | None = None,
    platform: str | None = None,
    uid: int | None = None,
    environ: Mapping[str, str] | None = None,
    runner: CommandRunner | None = None,
    now: Callable[[], datetime] | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    args = _build_parser().parse_args(argv)
    environment = os.environ if environ is None else environ
    context = ServiceContext(
        repo=args.repo.expanduser().resolve(),
        home=(home or Path.home()).expanduser().resolve(),
        label=args.label,
        uid=os.getuid() if uid is None else uid,
        platform=platform or sys.platform,
        path_env=environment.get("PATH", DEFAULT_PATH),
    )
    service = LaunchdService(context, runner=runner or _system_runner)
    try:
        return _dispatch(
            args.command,
            service=service,
            stdout=output,
            now=now or (lambda: datetime.now(UTC)),
        )
    except RuntimeError as exc:
        error_output.write(f"aico-service: {exc}\n")
        return 2


def main() -> None:
    raise SystemExit(run_service_cli())


def _dispatch(
    command: str,
    *,
    service: LaunchdService,
    stdout: TextIO,
    now: Callable[[], datetime],
) -> int:
    if command == "render":
        stdout.write(service.render_plist().decode("utf-8"))
        return 0
    if command == "doctor":
        checks = doctor_checks(service, now=now())
        stdout.write(_checks_text(checks))
        return 2 if any(check.status == "fail" for check in checks) else 0
    if command == "install":
        checks = readiness_checks(service.context)
        stdout.write(_checks_text(checks))
        if any(check.status == "fail" for check in checks):
            return 2
        backup = service.install()
        stdout.write(f"Installed and started: {service.context.plist_path}\n")
        if backup is not None:
            stdout.write(f"Previous plist backup: {backup}\n")
        return 0
    if service.context.platform != "darwin":
        raise RuntimeError(f"{command} requires macOS launchd")
    if command == "restart":
        service.restart()
        stdout.write(f"Restarted: {service.context.label}\n")
        return 0
    if command == "status":
        result = service.status()
        if result.returncode == 0:
            stdout.write(result.stdout)
            return 0
        stdout.write(f"Service not loaded: {service.context.label}\n")
        return 1
    recovered = service.uninstall()
    if recovered is None:
        stdout.write(f"Service already absent: {service.context.label}\n")
    else:
        stdout.write(f"Uninstalled; recoverable plist: {recovered}\n")
    return 0


def readiness_checks(
    context: ServiceContext,
    *,
    now: datetime | None = None,
) -> tuple[DoctorCheck, ...]:
    checks = [
        _check(
            "platform",
            context.platform == "darwin",
            "macOS launchd available" if context.platform == "darwin" else context.platform,
        ),
        _check("repository", context.repo.is_dir(), str(context.repo)),
        _check(
            "channel",
            context.configured_channel in {"telegram", "feishu"},
            context.configured_channel,
        ),
        _check(
            "runtime executable",
            context.executable.is_file() and os.access(context.executable, os.X_OK),
            str(context.executable),
        ),
        _check("env file", context.env_file.is_file(), str(context.env_file)),
    ]
    if not context.env_file.is_file():
        return tuple(checks)
    safe_permissions = stat.S_IMODE(context.env_file.stat().st_mode) & 0o077 == 0
    checks.append(
        _check(
            "env permissions",
            safe_permissions,
            "owner-only" if safe_permissions else "run chmod 600 .env",
        )
    )
    env = _read_env(context.env_file)
    unusable = tuple(key for key in _required_env_keys(env) if not _usable_env_value(env.get(key)))
    checks.append(
        _check(
            "env required keys",
            not unusable,
            "present" if not unusable else f"missing or placeholder: {', '.join(unusable)}",
        )
    )
    checks.append(_runtime_alert_readiness(env))
    checks.append(_runtime_liveness_readiness(env))
    checks.append(_runtime_webhook_isolation_readiness(env))
    checks.append(_im_ingress_readiness(env))
    checks.append(_approval_lease_readiness(env))
    checks.append(_audit_integrity_readiness(env, context.repo))
    checks.append(_memory_integrity_readiness(env, context.repo))
    checks.append(_recovery_backup_readiness(env, context.repo))
    checks.append(
        _runtime_commissioning_readiness(
            env,
            context.repo,
            context.env_file,
            now=now or datetime.now(UTC),
        )
    )
    checks.append(_standing_autonomy_readiness(env, context.repo))
    checks.append(_absence_admission_readiness(env, checks))
    return tuple(checks)


def doctor_checks(service: LaunchdService, *, now: datetime) -> tuple[DoctorCheck, ...]:
    context = service.context
    checks = list(readiness_checks(context, now=now))
    installed = context.plist_path.is_file()
    checks.append(
        DoctorCheck(
            name="plist installed",
            status="ok" if installed else "warn",
            detail=str(context.plist_path) if installed else "run aico-service install",
        )
    )
    if not installed:
        checks.append(DoctorCheck(name="launchctl", status="warn", detail="not checked"))
        ownership = runtime_owner_status(context.owner_lock_path)
        checks.append(
            DoctorCheck(
                name="runtime owner",
                status="warn",
                detail=(
                    f"active outside installed service; {ownership.detail}"
                    if ownership.active
                    else ownership.detail
                ),
            )
        )
        checks.append(DoctorCheck(name="heartbeat", status="warn", detail="not installed"))
        return tuple(checks)
    matches = context.plist_path.read_bytes() == service.render_plist()
    checks.append(
        _check("plist current", matches, "matches checkout" if matches else "run install")
    )
    launch_status = service.status()
    loaded = launch_status.returncode == 0
    checks.append(
        DoctorCheck(
            name="launchctl",
            status="ok" if loaded else "warn",
            detail="loaded" if loaded else "not loaded",
        )
    )
    ownership = runtime_owner_status(context.owner_lock_path)
    if loaded:
        launch_pid = _launchctl_pid(launch_status.stdout)
        owner_matches_launchd = (
            ownership.active
            and ownership.owner_pid is not None
            and launch_pid == ownership.owner_pid
        )
        owner_status: CheckStatus = "ok" if owner_matches_launchd else "fail"
        if owner_matches_launchd:
            owner_detail = f"active pid={ownership.owner_pid} matches launchd"
        elif not ownership.active:
            owner_detail = "loaded service has no active owner"
        else:
            owner_detail = (
                f"owner pid={ownership.owner_pid or 'unknown'} does not match "
                f"launchd pid={launch_pid or 'unavailable'}"
            )
    else:
        owner_status = "warn"
        owner_detail = (
            f"active outside launchd; {ownership.detail}" if ownership.active else ownership.detail
        )
    checks.append(DoctorCheck(name="runtime owner", status=owner_status, detail=owner_detail))
    health = heartbeat_health(_configured_heartbeat_path(context), now=now)
    heartbeat_status: CheckStatus = health.status
    heartbeat_never_started = health.detail == "missing" or health.detail.startswith("state=")
    if loaded and heartbeat_status == "warn" and heartbeat_never_started:
        heartbeat_status = "fail"
    checks.append(DoctorCheck(name="heartbeat", status=heartbeat_status, detail=health.detail))
    return tuple(checks)


def _configured_heartbeat_path(context: ServiceContext) -> Path:
    if not context.env_file.is_file():
        return context.heartbeat_path
    value = _read_env(context.env_file).get("AICO_RUNTIME_HEARTBEAT_PATH")
    if not value:
        return context.heartbeat_path
    path = Path(value).expanduser()
    return path if path.is_absolute() else context.repo / path


def _configured_state_db_path(context: ServiceContext) -> Path | None:
    if not context.env_file.is_file():
        return None
    value = _read_env(context.env_file).get("AICO_STATE_DB_PATH", "").strip()
    normalized = value.casefold()
    if not value or normalized in {"0", "false", "no", "off"}:
        return None
    if normalized in {"1", "true", "yes", "on"}:
        return context.repo / ".aico/state.db"
    path = Path(value).expanduser()
    return path if path.is_absolute() else context.repo / path


def _launchctl_pid(output: str) -> int | None:
    match = re.search(r"(?m)^\s*pid\s*=\s*(\d+)\s*$", output)
    return int(match.group(1)) if match is not None else None


def _required_env_keys(env: Mapping[str, str]) -> tuple[str, ...]:
    common = (
        "AICO_CLAUDE_WORKING_DIRECTORY",
        "AICO_PROJECT_CONFIG_PATH",
        "AICO_STATE_DB_PATH",
        "AICO_AUDIT_LOG_PATH",
        "AICO_MEMORY_PATH",
        "AICO_OWNER_SENDER_IDS",
        "AICO_TRUSTED_TARGET_IDS",
    )
    if env.get("AICO_CHANNEL", "telegram").casefold() == "feishu":
        return (
            *common,
            "AICO_FEISHU_APP_ID",
            "AICO_FEISHU_APP_SECRET",
            "AICO_FEISHU_VERIFICATION_TOKEN",
        )
    return (*common, "AICO_TELEGRAM_BOT_TOKEN")


def _runtime_alert_readiness(env: Mapping[str, str]) -> DoctorCheck:
    url = env.get("AICO_RUNTIME_ALERT_WEBHOOK_URL", "").strip()
    token = env.get("AICO_RUNTIME_ALERT_WEBHOOK_BEARER_TOKEN", "").strip()
    if not url:
        if token:
            return DoctorCheck(
                name="runtime alerts",
                status="fail",
                detail="bearer token configured without AICO_RUNTIME_ALERT_WEBHOOK_URL",
            )
        return DoctorCheck(name="runtime alerts", status="warn", detail="disabled")
    if not _usable_env_value(url):
        return DoctorCheck(
            name="runtime alerts",
            status="fail",
            detail="AICO_RUNTIME_ALERT_WEBHOOK_URL is a placeholder",
        )
    if not url.startswith("https://"):
        return DoctorCheck(
            name="runtime alerts",
            status="fail",
            detail="AICO_RUNTIME_ALERT_WEBHOOK_URL must use HTTPS",
        )
    if not _usable_env_value(env.get("AICO_STATE_DB_PATH")):
        return DoctorCheck(
            name="runtime alerts",
            status="fail",
            detail="AICO_STATE_DB_PATH is required for durable alerts",
        )
    if token and not _usable_env_value(token):
        return DoctorCheck(
            name="runtime alerts",
            status="fail",
            detail="AICO_RUNTIME_ALERT_WEBHOOK_BEARER_TOKEN is a placeholder",
        )
    return DoctorCheck(
        name="runtime alerts",
        status="ok",
        detail="durable HTTPS webhook configured",
    )


def _approval_lease_readiness(env: Mapping[str, str]) -> DoctorCheck:
    raw_value = env.get(
        "AICO_APPROVAL_MAX_AGE_SECONDS",
        str(DEFAULT_APPROVAL_MAX_AGE_SECONDS),
    ).strip()
    try:
        max_age_seconds = int(raw_value)
    except ValueError:
        max_age_seconds = 0
    valid = MIN_APPROVAL_MAX_AGE_SECONDS <= max_age_seconds <= MAX_APPROVAL_MAX_AGE_SECONDS
    return DoctorCheck(
        name="approval lease",
        status="ok" if valid else "fail",
        detail=(
            f"expires after {max_age_seconds}s"
            if valid
            else "must be an integer between 300 and 604800 seconds"
        ),
    )


def _audit_integrity_readiness(env: Mapping[str, str], repo: Path) -> DoctorCheck:
    raw_path = env.get("AICO_AUDIT_LOG_PATH", "").strip()
    if not _usable_env_value(raw_path):
        return DoctorCheck(
            name="audit integrity",
            status="fail",
            detail="AICO_AUDIT_LOG_PATH must be configured",
        )
    path = Path(raw_path).expanduser()
    path = path if path.is_absolute() else repo / path
    try:
        summary = verify_audit_ledger(path)
    except (AuditIntegrityError, OSError, ValueError) as exc:
        return DoctorCheck(name="audit integrity", status="fail", detail=str(exc))
    if not summary.sealed:
        return DoctorCheck(name="audit integrity", status="ok", detail="ready, no events")
    detail = f"sealed, {summary.event_count} event(s)"
    if summary.checkpoint_lag:
        detail += ", checkpoint lag recoverable"
    return DoctorCheck(name="audit integrity", status="ok", detail=detail)


def _memory_integrity_readiness(env: Mapping[str, str], repo: Path) -> DoctorCheck:
    raw_path = env.get("AICO_MEMORY_PATH", "").strip()
    if not _usable_env_value(raw_path):
        return DoctorCheck(
            name="memory integrity",
            status="fail",
            detail="AICO_MEMORY_PATH must be configured",
        )
    path = Path(raw_path).expanduser()
    path = path if path.is_absolute() else repo / path
    try:
        summary = verify_memory_ledger(path)
    except (MemoryIntegrityError, OSError, ValueError) as exc:
        return DoctorCheck(name="memory integrity", status="fail", detail=str(exc))
    if not summary.sealed:
        return DoctorCheck(name="memory integrity", status="ok", detail="ready, no records")
    detail = f"sealed, {summary.record_count} record(s)"
    if summary.checkpoint_lag:
        detail += ", checkpoint lag recoverable"
    return DoctorCheck(name="memory integrity", status="ok", detail=detail)


def _im_ingress_readiness(env: Mapping[str, str]) -> DoctorCheck:
    discovery = env.get("AICO_INGRESS_DISCOVERY_LOG_IDENTITIES", "false").strip().casefold()
    if discovery in {"1", "true", "yes", "on"}:
        return DoctorCheck(
            name="IM ingress",
            status="fail",
            detail="identity discovery must be disabled before install",
        )
    try:
        owners = parse_ingress_ids(env.get("AICO_OWNER_SENDER_IDS", ""))
        targets = parse_ingress_ids(env.get("AICO_TRUSTED_TARGET_IDS", ""))
        reviewers = parse_ingress_ids(env.get("AICO_APPROVAL_REVIEWER_IDS", ""))
    except IngressBindingError:
        owners, targets, reviewers = (), (), ()
    if not owners or not targets:
        return DoctorCheck(
            name="IM ingress",
            status="fail",
            detail="requires owner sender ids and trusted target ids",
        )
    if reviewers and not set(reviewers).issubset(owners):
        return DoctorCheck(
            name="IM ingress",
            status="fail",
            detail="approval reviewers must be owner senders",
        )
    morning_enabled = env.get("AICO_MORNING_PUSH_ENABLED", "false").strip().casefold()
    morning_target = env.get("AICO_MORNING_PUSH_TARGET_ID", "").strip()
    if morning_enabled in {"1", "true", "yes", "on"} and morning_target not in targets:
        return DoctorCheck(
            name="IM ingress",
            status="fail",
            detail="morning push target must be trusted",
        )
    return DoctorCheck(
        name="IM ingress",
        status="ok",
        detail=f"{len(owners)} owner sender(s), {len(targets)} trusted target(s)",
    )


def _runtime_liveness_readiness(env: Mapping[str, str]) -> DoctorCheck:
    raw_enabled = env.get("AICO_RUNTIME_LIVENESS_ENABLED", "false").strip().casefold()
    url = env.get("AICO_RUNTIME_LIVENESS_WEBHOOK_URL", "").strip()
    token = env.get("AICO_RUNTIME_LIVENESS_WEBHOOK_BEARER_TOKEN", "").strip()
    if token and not url:
        return DoctorCheck(
            name="runtime liveness",
            status="fail",
            detail="liveness bearer token configured without liveness webhook URL",
        )
    if url and not _usable_env_value(url):
        return DoctorCheck(
            name="runtime liveness",
            status="fail",
            detail="AICO_RUNTIME_LIVENESS_WEBHOOK_URL is a placeholder",
        )
    if url and not url.startswith("https://"):
        return DoctorCheck(
            name="runtime liveness",
            status="fail",
            detail="AICO_RUNTIME_LIVENESS_WEBHOOK_URL must use HTTPS",
        )
    if token and not _usable_env_value(token):
        return DoctorCheck(
            name="runtime liveness",
            status="fail",
            detail="AICO_RUNTIME_LIVENESS_WEBHOOK_BEARER_TOKEN is a placeholder",
        )
    if raw_enabled in {"false", "0", "no", "off"}:
        return DoctorCheck(name="runtime liveness", status="warn", detail="disabled")
    if raw_enabled not in {"true", "1", "yes", "on"}:
        return DoctorCheck(
            name="runtime liveness",
            status="fail",
            detail="AICO_RUNTIME_LIVENESS_ENABLED must be true or false",
        )
    if not _usable_env_value(url):
        return DoctorCheck(
            name="runtime liveness",
            status="fail",
            detail="AICO_RUNTIME_LIVENESS_WEBHOOK_URL is required",
        )
    heartbeat_path = env.get("AICO_RUNTIME_HEARTBEAT_PATH")
    if heartbeat_path is not None and not heartbeat_path.strip():
        return DoctorCheck(
            name="runtime liveness",
            status="fail",
            detail="AICO_RUNTIME_HEARTBEAT_PATH cannot be disabled",
        )
    runtime_id = env.get("AICO_RUNTIME_MONITOR_ID", "").strip()
    if (
        not _usable_env_value(runtime_id)
        or re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", runtime_id) is None
    ):
        return DoctorCheck(
            name="runtime liveness",
            status="fail",
            detail="AICO_RUNTIME_MONITOR_ID must be a safe runtime identity",
        )
    heartbeat_interval = _positive_number(env.get("AICO_RUNTIME_HEARTBEAT_INTERVAL_SECONDS", "30"))
    pulse_interval = _positive_number(env.get("AICO_RUNTIME_LIVENESS_INTERVAL_SECONDS", "60"))
    ttl = _positive_number(env.get("AICO_RUNTIME_LIVENESS_TTL_SECONDS", "300"))
    if heartbeat_interval is None or pulse_interval is None or ttl is None:
        return DoctorCheck(
            name="runtime liveness",
            status="fail",
            detail="runtime liveness intervals must be positive numbers",
        )
    if pulse_interval < heartbeat_interval:
        return DoctorCheck(
            name="runtime liveness",
            status="fail",
            detail="runtime liveness interval must be at least the heartbeat interval",
        )
    if ttl < pulse_interval * 3:
        return DoctorCheck(
            name="runtime liveness",
            status="fail",
            detail="runtime liveness TTL must be at least three pulse intervals",
        )
    return DoctorCheck(
        name="runtime liveness",
        status="ok",
        detail="external dead-man pulse configured",
    )


def _runtime_webhook_isolation_readiness(env: Mapping[str, str]) -> DoctorCheck:
    alert_url = env.get("AICO_RUNTIME_ALERT_WEBHOOK_URL")
    liveness_url = env.get("AICO_RUNTIME_LIVENESS_WEBHOOK_URL")
    error = runtime_webhook_isolation_error(
        alert_url=alert_url,
        liveness_url=liveness_url,
        alert_token=env.get("AICO_RUNTIME_ALERT_WEBHOOK_BEARER_TOKEN"),
        liveness_token=env.get("AICO_RUNTIME_LIVENESS_WEBHOOK_BEARER_TOKEN"),
    )
    if error is not None:
        return DoctorCheck(name="runtime endpoint isolation", status="fail", detail=error)
    detail = (
        "dedicated webhook authorities" if alert_url and liveness_url else "not jointly configured"
    )
    return DoctorCheck(name="runtime endpoint isolation", status="ok", detail=detail)


def _standing_autonomy_readiness(env: Mapping[str, str], repo: Path) -> DoctorCheck:
    raw_path = env.get("AICO_STANDING_AUTONOMY_GRANT_PATH", "").strip()
    if not raw_path:
        return DoctorCheck(name="standing autonomy", status="warn", detail="disabled")
    if not _usable_env_value(raw_path):
        return DoctorCheck(
            name="standing autonomy",
            status="fail",
            detail="AICO_STANDING_AUTONOMY_GRANT_PATH is a placeholder",
        )
    enabled = env.get("AICO_MORNING_PUSH_ENABLED", "false").strip().casefold()
    if enabled not in {"true", "1", "yes", "on"}:
        return DoctorCheck(
            name="standing autonomy",
            status="fail",
            detail="standing autonomy requires scheduled morning push",
        )
    try:
        grants = load_standing_autonomy_grants(Path(raw_path), forbidden_roots=(repo,))
    except StandingAutonomyConfigError as exc:
        return DoctorCheck(name="standing autonomy", status="fail", detail=str(exc))
    if not grants.grants:
        return DoctorCheck(
            name="standing autonomy",
            status="fail",
            detail="standing autonomy grant file contains no grants",
        )
    try:
        settings = _standing_autonomy_settings(env, repo)
        validated = preflight_standing_autonomy(settings)
    except StandingAutonomyConfigError as exc:
        return DoctorCheck(name="standing autonomy", status="fail", detail=str(exc))
    except (OSError, UnicodeError, ValueError):
        return DoctorCheck(
            name="standing autonomy",
            status="fail",
            detail="standing autonomy runtime binding is invalid",
        )
    if validated != grants:
        return DoctorCheck(
            name="standing autonomy",
            status="fail",
            detail="standing autonomy runtime binding is invalid",
        )
    return DoctorCheck(
        name="standing autonomy",
        status="ok",
        detail=f"owner-bound runtime binding verified ({len(grants.grants)} grants)",
    )


def _recovery_backup_readiness(env: Mapping[str, str], repo: Path) -> DoctorCheck:
    enabled = env.get("AICO_RECOVERY_BACKUP_ENABLED", "false").strip().casefold()
    if enabled not in {"true", "1", "yes", "on"}:
        return DoctorCheck(name="recovery backup", status="warn", detail="disabled")
    try:
        settings = _recovery_backup_settings(env, repo)
        if preflight_recovery_backup(settings) is None:
            raise ValueError("recovery backup unexpectedly disabled")
    except (OSError, UnicodeError, ValueError):
        return DoctorCheck(
            name="recovery backup",
            status="fail",
            detail="scheduled capture destination or binding is invalid",
        )
    capabilities = (
        "capture, verify, custody, and disposable drill"
        if settings.recovery_drill_enabled
        else "capture, verify, and custody"
    )
    return DoctorCheck(
        name="recovery backup",
        status="ok",
        detail=f"{capabilities} configured; storage class not attested",
    )


def _runtime_commissioning_readiness(
    env: Mapping[str, str],
    repo: Path,
    dotenv_path: Path,
    *,
    now: datetime,
) -> DoctorCheck:
    receipt_value = env.get("AICO_COMMISSIONING_RECEIPT_PATH", "").strip()
    evidence_value = env.get("AICO_COMMISSIONING_DEAD_MAN_EVIDENCE_PATH", "").strip()
    if not receipt_value and not evidence_value:
        return DoctorCheck(
            name="runtime commissioning",
            status="warn",
            detail="disabled; current external evidence is not bound",
        )
    required = {
        "receipt": receipt_value,
        "evidence": evidence_value,
        "project": env.get("AICO_PROJECT_CONFIG_PATH", "").strip(),
        "revision": env.get("AICO_REVIEWED_CONFIG_REVISION", "").strip(),
        "runtime": env.get("AICO_RUNTIME_MONITOR_ID", "").strip(),
    }
    if not all(required.values()):
        return DoctorCheck(
            name="runtime commissioning",
            status="fail",
            detail="commissioning binding is incomplete",
        )
    project_path = _path_from_repo(Path(required["project"]), repo)
    evidence_path = _path_from_repo(Path(evidence_value), repo)
    receipt_path = _path_from_repo(Path(receipt_value), repo)
    assert project_path is not None
    assert evidence_path is not None
    assert receipt_path is not None
    try:
        verify_runtime_commissioning_receipt(
            checkout_path=repo,
            project_config_path=project_path,
            persona_config_path=_path_from_repo(
                Path(env["AICO_PERSONA_CONFIG_PATH"]),
                repo,
            )
            if env.get("AICO_PERSONA_CONFIG_PATH")
            else None,
            expected_config_revision=required["revision"],
            expected_runtime_id=required["runtime"],
            dotenv_path=dotenv_path,
            dead_man_evidence_path=evidence_path,
            receipt_path=receipt_path,
            clock=lambda: now,
        )
    except (RuntimeCommissioningError, OSError, ValueError):
        return DoctorCheck(
            name="runtime commissioning",
            status="fail",
            detail="receipt is missing, stale, or mismatched",
        )
    return DoctorCheck(
        name="runtime commissioning",
        status="ok",
        detail="current config and external evidence bound; source and human read not attested",
    )


def _absence_admission_readiness(
    env: Mapping[str, str],
    checks: Sequence[DoctorCheck],
) -> DoctorCheck:
    mode = env.get("AICO_ABSENCE_ADMISSION_MODE", "optional").strip().casefold()
    if mode == "optional":
        return DoctorCheck(
            name="absence admission",
            status="warn",
            detail="optional; critical absence contracts are not an install gate",
        )
    if mode not in ABSENCE_ADMISSION_MODES:
        return DoctorCheck(
            name="absence admission",
            status="fail",
            detail="AICO_ABSENCE_ADMISSION_MODE must be optional or strict",
        )
    statuses = {check.name: check.status == "ok" for check in checks}
    drill_enabled = env.get("AICO_RECOVERY_DRILL_ENABLED", "false").strip().casefold()
    missing = strict_absence_contract_gaps(
        statuses,
        recovery_drill_enabled=drill_enabled in {"true", "1", "yes", "on"},
    )
    if missing:
        return DoctorCheck(
            name="absence admission",
            status="fail",
            detail=f"strict machine contracts not ready: {', '.join(missing)}",
        )
    return DoctorCheck(
        name="absence admission",
        status="ok",
        detail=(
            "strict machine contracts configured; current external evidence bound; "
            "source and human read not attested"
        ),
    )


def _standing_autonomy_settings(
    env: Mapping[str, str],
    repo: Path,
) -> Phase1Settings:
    field_names = (
        "channel",
        "claude_command",
        "claude_working_directory",
        "claude_max_concurrent_tasks",
        "enable_codex_adapter",
        "codex_command",
        "codex_output_idle_timeout_seconds",
        "codex_max_concurrent_tasks",
        "persona_config_path",
        "project_config_path",
        "owner_sender_ids",
        "trusted_target_ids",
        "approval_reviewer_ids",
        "morning_push_enabled",
        "morning_push_target_id",
        "morning_push_thread_id",
        "morning_push_project",
        "morning_push_scope_id",
        "morning_push_time",
        "morning_push_on_start",
        "state_db_path",
        "standing_autonomy_grant_path",
    )
    payload = {
        field_name: value
        for field_name in field_names
        if (value := env.get(f"AICO_{field_name.upper()}")) is not None
    }
    settings = _ExplicitPhase1Settings.model_validate(payload)
    path_updates = {
        field_name: _path_from_repo(getattr(settings, field_name), repo)
        for field_name in (
            "claude_working_directory",
            "persona_config_path",
            "project_config_path",
            "state_db_path",
        )
    }
    return settings.model_copy(update=path_updates)


def _recovery_backup_settings(
    env: Mapping[str, str],
    repo: Path,
) -> Phase1Settings:
    field_names = (
        "state_db_path",
        "audit_log_path",
        "memory_path",
        "persona_config_path",
        "project_config_path",
        "reviewed_config_revision",
        "recovery_backup_enabled",
        "recovery_backup_checkout_path",
        "recovery_backup_output_dir",
        "recovery_backup_interval_seconds",
        "recovery_backup_max_age_seconds",
        "recovery_custody_check_interval_seconds",
        "recovery_custody_max_age_seconds",
        "recovery_retention_enabled",
        "recovery_retention_after_seconds",
        "recovery_retention_min_generations",
        "recovery_retention_check_interval_seconds",
        "recovery_retention_max_prunes_per_run",
        "recovery_drill_enabled",
        "recovery_drill_interval_seconds",
        "recovery_drill_max_age_seconds",
        "recovery_drill_workspace",
    )
    payload = {
        field_name: value
        for field_name in field_names
        if (value := env.get(f"AICO_{field_name.upper()}")) is not None
    }
    payload.setdefault("recovery_backup_checkout_path", str(repo))
    settings = _ExplicitPhase1Settings.model_validate(payload)
    path_fields = (
        "state_db_path",
        "audit_log_path",
        "memory_path",
        "persona_config_path",
        "project_config_path",
        "recovery_backup_checkout_path",
        "recovery_backup_output_dir",
        "recovery_drill_workspace",
    )
    updates = {
        field_name: _path_from_repo(getattr(settings, field_name), repo)
        for field_name in path_fields
    }
    return settings.model_copy(update=updates)


def _path_from_repo(path: Path | None, repo: Path) -> Path | None:
    if path is None or path.is_absolute():
        return path
    return repo / path


def _positive_number(value: str) -> float | None:
    try:
        number = float(value)
    except ValueError:
        return None
    return number if number > 0 else None


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()
        key, value = line.split("=", maxsplit=1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _usable_env_value(value: str | None) -> bool:
    if value is None or not value.strip():
        return False
    normalized = value.casefold()
    return not any(fragment in normalized for fragment in _PLACEHOLDER_FRAGMENTS)


def _check(name: str, condition: bool, detail: str) -> DoctorCheck:
    return DoctorCheck(name=name, status="ok" if condition else "fail", detail=detail)


def _checks_text(checks: tuple[DoctorCheck, ...]) -> str:
    return "".join(f"[{check.status.upper()}] {check.name}: {check.detail}\n" for check in checks)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aico-service",
        description="Manage the user-level macOS service for aico-phase1.",
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="AICO checkout root")
    parser.add_argument(
        "--label",
        type=_service_label,
        default=DEFAULT_LABEL,
        help="LaunchAgent label",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("render", "install", "restart", "status", "doctor", "uninstall"):
        subparsers.add_parser(name)
    return parser


def _system_runner(command: tuple[str, ...]) -> CommandResult:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        return CommandResult(returncode=127, stdout="", stderr=str(exc))
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _service_label(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", value):
        raise argparse.ArgumentTypeError(
            "label must contain only letters, numbers, dots, or dashes"
        )
    return value


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _unique_trash_path(trash: Path, filename: str) -> Path:
    candidate = trash / filename
    suffix = 1
    while candidate.exists():
        candidate = trash / f"{filename}.{suffix}"
        suffix += 1
    return candidate
