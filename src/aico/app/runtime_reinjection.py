"""Secret-free runtime and standing-grant recovery materialization evidence."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aico.app.service_cli import ServiceContext, readiness_checks
from aico.core.standing_autonomy import (
    StandingAutonomyConfigError,
    load_standing_autonomy_grants,
)

_MAX_ENV_BYTES = 128 * 1024
_SECRET_SLOT_ORDER = (
    "AICO_TELEGRAM_BOT_TOKEN",
    "AICO_FEISHU_APP_SECRET",
    "AICO_FEISHU_VERIFICATION_TOKEN",
    "AICO_RUNTIME_ALERT_WEBHOOK_BEARER_TOKEN",
    "AICO_RUNTIME_LIVENESS_WEBHOOK_BEARER_TOKEN",
)
_REINJECTION_CHECKS = (
    "channel",
    "env file",
    "env permissions",
    "env required keys",
    "runtime alerts",
    "runtime liveness",
    "IM ingress",
    "approval lease",
    "standing autonomy",
)
_PROVIDER_ORDER = ("claude-code", "codex", "cursor", "codeflicker", "trae", "gemini")
_OPTIONAL_PROVIDER_FLAGS = {
    "codex": "AICO_ENABLE_CODEX_ADAPTER",
    "cursor": "AICO_ENABLE_CURSOR_ADAPTER",
    "codeflicker": "AICO_ENABLE_CODEFLICKER_ADAPTER",
    "trae": "AICO_ENABLE_TRAE_ADAPTER",
    "gemini": "AICO_ENABLE_GEMINI_ADAPTER",
}
_PROVIDER_COMMANDS = {
    "claude-code": (
        "AICO_CLAUDE_COMMAND",
        "claude -p --output-format text --permission-mode bypassPermissions",
    ),
    "codex": (
        "AICO_CODEX_COMMAND",
        "codex --ask-for-approval never exec --sandbox read-only --color never",
    ),
    "cursor": ("AICO_CURSOR_COMMAND", "cursor-agent -p --force --output-format text"),
    "codeflicker": (
        "AICO_CODEFLICKER_COMMAND",
        "flickcli -q --approval-mode yolo --output-format text",
    ),
    "trae": ("AICO_TRAE_COMMAND", "trae-cli --print --yolo"),
    "gemini": (
        "AICO_GEMINI_COMMAND",
        "gemini --approval-mode yolo --output-format text",
    ),
}

RuntimeSecretSlot = Literal[
    "AICO_TELEGRAM_BOT_TOKEN",
    "AICO_FEISHU_APP_SECRET",
    "AICO_FEISHU_VERIFICATION_TOKEN",
    "AICO_RUNTIME_ALERT_WEBHOOK_BEARER_TOKEN",
    "AICO_RUNTIME_LIVENESS_WEBHOOK_BEARER_TOKEN",
]
RuntimeReinjectionCheck = Literal[
    "channel",
    "env file",
    "env permissions",
    "env required keys",
    "runtime alerts",
    "runtime liveness",
    "IM ingress",
    "approval lease",
    "standing autonomy",
]
ProviderName = Literal["claude-code", "codex", "cursor", "codeflicker", "trae", "gemini"]


class RuntimeReinjectionError(RuntimeError):
    """Runtime recovery material cannot satisfy the captured reinjection contract."""


class RuntimeReinjectionContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[2] = 2
    channel: Literal["telegram", "feishu"]
    secret_slots: tuple[RuntimeSecretSlot, ...] = Field(min_length=1, max_length=5)
    standing_grant_required: bool
    provider_names: tuple[ProviderName, ...] = Field(min_length=1, max_length=6)
    provider_count: int = Field(ge=1, le=6)
    secret_values_recorded: Literal[False] = False
    secret_hashes_recorded: Literal[False] = False
    post_restore_receipt_required: Literal[True] = True
    ai_provider_live_probe_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_contract(self) -> RuntimeReinjectionContract:
        ordered = tuple(slot for slot in _SECRET_SLOT_ORDER if slot in self.secret_slots)
        if self.secret_slots != ordered or len(set(self.secret_slots)) != len(self.secret_slots):
            raise ValueError("runtime secret slots must be unique and canonical")
        telegram = "AICO_TELEGRAM_BOT_TOKEN"
        feishu = {"AICO_FEISHU_APP_SECRET", "AICO_FEISHU_VERIFICATION_TOKEN"}
        if self.channel == "telegram" and (
            telegram not in self.secret_slots or feishu.intersection(self.secret_slots)
        ):
            raise ValueError("runtime secret slots do not match the Telegram channel")
        if self.channel == "feishu" and (
            telegram in self.secret_slots or not feishu.issubset(self.secret_slots)
        ):
            raise ValueError("runtime secret slots do not match the Feishu channel")
        ordered_providers = tuple(
            provider for provider in _PROVIDER_ORDER if provider in self.provider_names
        )
        if (
            self.provider_names != ordered_providers
            or len(set(self.provider_names)) != len(self.provider_names)
            or self.provider_names[0] != "claude-code"
            or self.provider_count != len(self.provider_names)
        ):
            raise ValueError("runtime providers must be unique, canonical, and count-matched")
        return self


class RuntimeReinjectionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["capture", "verify-reinjection"]
    channel: Literal["telegram", "feishu"]
    secret_slots: tuple[RuntimeSecretSlot, ...]
    secret_slot_count: int = Field(ge=1, le=5)
    secrets_present: Literal[True] = True
    secret_values_recorded: Literal[False] = False
    secret_hashes_recorded: Literal[False] = False
    standing_grant_required: bool
    standing_grant_count: int = Field(ge=0, le=1000)
    standing_grant_binding_verified: Literal[True] = True
    provider_names: tuple[ProviderName, ...] = Field(min_length=1, max_length=6)
    provider_count: int = Field(ge=1, le=6)
    verified_checks: tuple[RuntimeReinjectionCheck, ...]
    external_authentication_live_verified: Literal[False] = False

    @model_validator(mode="after")
    def validate_evidence(self) -> RuntimeReinjectionEvidence:
        if self.secret_slot_count != len(self.secret_slots):
            raise ValueError("runtime secret slot count does not match evidence")
        if self.verified_checks != _REINJECTION_CHECKS:
            raise ValueError("runtime reinjection checks are incomplete")
        if self.standing_grant_required != (self.standing_grant_count > 0):
            raise ValueError("standing grant evidence does not match required mode")
        if self.provider_count != len(self.provider_names):
            raise ValueError("runtime provider count does not match evidence")
        return self


def capture_runtime_reinjection_contract(
    checkout_path: Path,
    *,
    expected_owner_uid: int | None = None,
) -> tuple[RuntimeReinjectionContract, RuntimeReinjectionEvidence]:
    checkout = _absolute(checkout_path)
    state = _materialization_state(checkout, expected_owner_uid=expected_owner_uid)
    contract = RuntimeReinjectionContract(
        channel=state.channel,
        secret_slots=state.secret_slots,
        standing_grant_required=state.standing_grant_required,
        provider_names=state.provider_names,
        provider_count=state.provider_count,
    )
    return contract, state.model_copy(update={"operation": "capture"})


def verify_runtime_reinjection(
    contract: RuntimeReinjectionContract,
    checkout_path: Path,
    *,
    expected_owner_uid: int | None = None,
) -> RuntimeReinjectionEvidence:
    checkout = _absolute(checkout_path)
    current = _materialization_state(checkout, expected_owner_uid=expected_owner_uid)
    comparable = RuntimeReinjectionContract(
        channel=current.channel,
        secret_slots=current.secret_slots,
        standing_grant_required=current.standing_grant_required,
        provider_names=current.provider_names,
        provider_count=current.provider_count,
    )
    if comparable != contract:
        raise RuntimeReinjectionError("runtime reinjection does not match recovery set")
    return current


def _materialization_state(
    checkout: Path,
    *,
    expected_owner_uid: int | None,
) -> RuntimeReinjectionEvidence:
    env_path = checkout / ".env"
    _require_env_not_tracked(checkout)
    env = _read_private_env(env_path, expected_owner_uid=expected_owner_uid)
    context = ServiceContext(
        repo=checkout,
        home=checkout,
        label="com.aico.recovery-verification",
        uid=os.getuid() if expected_owner_uid is None else expected_owner_uid,
        platform="darwin",
        path_env="/usr/bin:/bin",
    )
    try:
        checks = {check.name: check for check in readiness_checks(context)}
    except (OSError, UnicodeError, ValueError):
        raise RuntimeReinjectionError("runtime reinjection material is invalid") from None
    if any(name not in checks or checks[name].status == "fail" for name in _REINJECTION_CHECKS):
        raise RuntimeReinjectionError("runtime reinjection material is invalid")
    channel = env.get("AICO_CHANNEL", "telegram").casefold()
    if channel not in {"telegram", "feishu"}:
        raise RuntimeReinjectionError("runtime reinjection material is invalid")
    typed_channel = cast(Literal["telegram", "feishu"], channel)
    secret_slots = cast(
        tuple[RuntimeSecretSlot, ...],
        tuple(slot for slot in _SECRET_SLOT_ORDER if env.get(slot, "").strip()),
    )
    grant_required = bool(env.get("AICO_STANDING_AUTONOMY_GRANT_PATH", "").strip())
    grant_count = _standing_grant_count(env, checkout) if grant_required else 0
    provider_names = _provider_names(env)
    return RuntimeReinjectionEvidence(
        operation="verify-reinjection",
        channel=typed_channel,
        secret_slots=secret_slots,
        secret_slot_count=len(secret_slots),
        standing_grant_required=grant_required,
        standing_grant_count=grant_count,
        provider_names=provider_names,
        provider_count=len(provider_names),
        verified_checks=cast(tuple[RuntimeReinjectionCheck, ...], _REINJECTION_CHECKS),
    )


def runtime_provider_commands(
    checkout_path: Path,
    *,
    expected_owner_uid: int | None = None,
) -> dict[ProviderName, str]:
    """Return only configured provider command strings after private-env validation."""

    checkout = _absolute(checkout_path)
    _require_env_not_tracked(checkout)
    env = _read_private_env(checkout / ".env", expected_owner_uid=expected_owner_uid)
    providers = _provider_names(env)
    return {
        provider: env.get(_PROVIDER_COMMANDS[provider][0], _PROVIDER_COMMANDS[provider][1])
        for provider in providers
    }


def _provider_names(env: dict[str, str]) -> tuple[ProviderName, ...]:
    enabled = {"claude-code"}
    for provider, flag in _OPTIONAL_PROVIDER_FLAGS.items():
        if _strict_boolean(env.get(flag, "false"), flag):
            enabled.add(provider)
    return cast(
        tuple[ProviderName, ...],
        tuple(provider for provider in _PROVIDER_ORDER if provider in enabled),
    )


def _strict_boolean(raw: str, name: str) -> bool:
    value = raw.strip().casefold()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off", ""}:
        return False
    raise RuntimeReinjectionError(f"runtime provider flag {name} is invalid")


def _read_private_env(path: Path, *, expected_owner_uid: int | None) -> dict[str, str]:
    try:
        metadata = path.lstat()
        owner_uid = os.getuid() if expected_owner_uid is None else expected_owner_uid
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise RuntimeReinjectionError("runtime environment must be a regular file")
        if stat.S_IMODE(metadata.st_mode) & 0o077 or metadata.st_uid != owner_uid:
            raise RuntimeReinjectionError("runtime environment must be owner-only")
        if metadata.st_size <= 0 or metadata.st_size > _MAX_ENV_BYTES:
            raise RuntimeReinjectionError("runtime environment size is invalid")
        values: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line.removeprefix("export ").lstrip()
            key, value = line.split("=", maxsplit=1)
            key = key.strip()
            if not key or key in values:
                raise RuntimeReinjectionError("runtime environment contains duplicate keys")
            values[key] = value.strip().strip("\"'")
        return values
    except RuntimeReinjectionError:
        raise
    except (OSError, UnicodeError):
        raise RuntimeReinjectionError("runtime environment is missing or invalid") from None


def _standing_grant_count(env: dict[str, str], checkout: Path) -> int:
    try:
        grants = load_standing_autonomy_grants(
            Path(env["AICO_STANDING_AUTONOMY_GRANT_PATH"]),
            forbidden_roots=(checkout,),
        )
        if not grants.grants:
            raise RuntimeReinjectionError("standing grant reinjection is empty")
        return len(grants.grants)
    except RuntimeReinjectionError:
        raise
    except (KeyError, StandingAutonomyConfigError):
        raise RuntimeReinjectionError("standing grant reinjection is invalid") from None


def _require_env_not_tracked(checkout: Path) -> None:
    try:
        result = subprocess.run(
            ("git", "-c", "core.hooksPath=/dev/null", "ls-files", "--error-unmatch", "--", ".env"),
            cwd=checkout,
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C"},
            check=False,
            capture_output=True,
        )
    except OSError:
        raise RuntimeReinjectionError("runtime environment Git inspection failed") from None
    if result.returncode == 0:
        raise RuntimeReinjectionError("runtime environment must not be tracked by Git")
    if result.returncode != 1:
        raise RuntimeReinjectionError("runtime environment Git inspection failed")


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))
