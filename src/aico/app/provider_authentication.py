"""Short-lived, secret-free receipts for real AI-provider authentication probes."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from aico.app.provider_auth_probe import (
    ProviderAuthenticationProbe,
    ProviderAuthenticationProbeError,
    build_cli_provider_probe,
    validated_provider_executable,
)
from aico.app.recovery_reinjection import (
    RecoveryReinjectionError,
    RecoveryReinjectionSummary,
    verify_recovery_reinjection_receipt,
)
from aico.app.runtime_reinjection import ProviderName, runtime_provider_commands

_RECEIPT_TTL = timedelta(minutes=30)
_MAX_RECEIPT_BYTES = 64 * 1024
_COPY_CHUNK_BYTES = 1024 * 1024
_CHALLENGE_PATTERN = re.compile(r"^aico-auth-v1-[a-f0-9]{48}$")

ProviderProbeFactory = Callable[[ProviderName, str], ProviderAuthenticationProbe]


class ProviderAuthenticationError(RuntimeError):
    """Live provider authentication evidence is missing, stale, or untrustworthy."""


class ProviderAuthenticationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: ProviderName
    challenge_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    probe_executable_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    terminal_success: Literal[True] = True
    exact_challenge_response: Literal[True] = True
    usage_observed: Literal[True] = True


class ProviderAuthenticationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    recovery_set_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reinjection_receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    checked_at: AwareDatetime
    expires_at: AwareDatetime
    providers: tuple[ProviderAuthenticationEvidence, ...] = Field(min_length=1, max_length=6)
    provider_count: int = Field(ge=1, le=6)
    owner_decision_ref: str = Field(min_length=1, max_length=128)
    challenge_values_recorded: Literal[False] = False
    prompts_recorded: Literal[False] = False
    provider_outputs_recorded: Literal[False] = False
    provider_errors_recorded: Literal[False] = False
    credential_values_recorded: Literal[False] = False
    credential_hashes_recorded: Literal[False] = False
    credential_identities_recorded: Literal[False] = False
    verification_authority: Literal["operator_invoked_live_provider"] = (
        "operator_invoked_live_provider"
    )
    business_restore_ready: Literal[False] = False

    @model_validator(mode="after")
    def validate_receipt(self) -> ProviderAuthenticationReceipt:
        names = tuple(item.provider for item in self.providers)
        if self.provider_count != len(self.providers) or len(set(names)) != len(names):
            raise ValueError("provider authentication evidence count is invalid")
        if self.expires_at - self.checked_at != _RECEIPT_TTL:
            raise ValueError("provider authentication evidence expiry is invalid")
        return self


class ProviderAuthenticationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["provider-auth-receipt", "verify-provider-auth"]
    receipt_name: str
    receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    recovery_set_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reinjection_receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    checked_at: AwareDatetime
    expires_at: AwareDatetime
    provider_names: tuple[ProviderName, ...] = Field(min_length=1, max_length=6)
    provider_count: int = Field(ge=1, le=6)
    owner_decision_ref: str = Field(min_length=1, max_length=128)
    live_probe_executed: bool
    live_probe_replayed: Literal[False] = False
    business_restore_ready: Literal[False] = False


def create_provider_authentication_receipt(
    recovery_set_path: Path,
    *,
    expected_recovery_set_sha256: str,
    checkout_path: Path,
    reinjection_receipt_path: Path,
    expected_reinjection_receipt_sha256: str,
    output_path: Path,
    probe_factory: ProviderProbeFactory = build_cli_provider_probe,
    clock: Callable[[], datetime] | None = None,
    challenge_factory: Callable[[], str] | None = None,
) -> ProviderAuthenticationSummary:
    checkout = _absolute(checkout_path)
    output = _absolute(output_path)
    _require_outside_checkout(output, checkout)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        reinjection = verify_recovery_reinjection_receipt(
            recovery_set_path,
            expected_recovery_set_sha256=expected_recovery_set_sha256,
            checkout_path=checkout,
            receipt_path=reinjection_receipt_path,
            expected_receipt_sha256=expected_reinjection_receipt_sha256,
        )
        commands = runtime_provider_commands(checkout)
        if tuple(commands) != reinjection.provider_names:
            raise ProviderAuthenticationError("provider authentication scope changed")
        evidence = tuple(
            _probe_provider(provider, command, probe_factory, challenge_factory)
            for provider, command in commands.items()
        )
        checked_at = _aware_now(clock or (lambda: datetime.now(UTC)))
        receipt = ProviderAuthenticationReceipt(
            recovery_set_sha256=reinjection.recovery_set_sha256,
            reinjection_receipt_sha256=reinjection.receipt_sha256,
            config_revision=reinjection.config_revision,
            checked_at=checked_at,
            expires_at=checked_at + _RECEIPT_TTL,
            providers=evidence,
            provider_count=len(evidence),
            owner_decision_ref=reinjection.owner_decision_ref,
        )
        _write_new_receipt(output, receipt)
        return _summary("provider-auth-receipt", output, _sha256(output), receipt, True)
    except ProviderAuthenticationError:
        raise
    except (ProviderAuthenticationProbeError, RecoveryReinjectionError):
        raise ProviderAuthenticationError(
            "provider authentication receipt creation failed"
        ) from None
    except Exception:
        raise ProviderAuthenticationError(
            "provider authentication receipt creation failed"
        ) from None


def verify_provider_authentication_receipt(
    recovery_set_path: Path,
    *,
    expected_recovery_set_sha256: str,
    checkout_path: Path,
    reinjection_receipt_path: Path,
    expected_reinjection_receipt_sha256: str,
    receipt_path: Path,
    expected_receipt_sha256: str,
    clock: Callable[[], datetime] | None = None,
) -> ProviderAuthenticationSummary:
    checkout = _absolute(checkout_path)
    receipt_file = _absolute(receipt_path)
    _require_outside_checkout(receipt_file, checkout)
    _validate_private_file(receipt_file)
    receipt_sha = _sha256(receipt_file)
    _require_sha(receipt_sha, expected_receipt_sha256)
    try:
        receipt = ProviderAuthenticationReceipt.model_validate_json(receipt_file.read_bytes())
        reinjection = verify_recovery_reinjection_receipt(
            recovery_set_path,
            expected_recovery_set_sha256=expected_recovery_set_sha256,
            checkout_path=checkout,
            receipt_path=reinjection_receipt_path,
            expected_receipt_sha256=expected_reinjection_receipt_sha256,
        )
        commands = runtime_provider_commands(checkout)
        current = _aware_now(clock or (lambda: datetime.now(UTC)))
        if not _receipt_matches(receipt, reinjection, commands, current):
            raise ProviderAuthenticationError(
                "provider authentication receipt is stale or mismatched"
            )
        return _summary("verify-provider-auth", receipt_file, receipt_sha, receipt, False)
    except ProviderAuthenticationError:
        raise
    except (
        OSError,
        ProviderAuthenticationProbeError,
        RecoveryReinjectionError,
        ValidationError,
        ValueError,
    ):
        raise ProviderAuthenticationError("provider authentication receipt is invalid") from None


def _probe_provider(
    provider: ProviderName,
    command: str,
    probe_factory: ProviderProbeFactory,
    challenge_factory: Callable[[], str] | None,
) -> ProviderAuthenticationEvidence:
    challenge = (challenge_factory or _new_challenge)()
    if _CHALLENGE_PATTERN.fullmatch(challenge) is None:
        raise ProviderAuthenticationError("provider authentication challenge is invalid")
    result = probe_factory(provider, command).execute(challenge)
    return ProviderAuthenticationEvidence(
        provider=provider,
        challenge_sha256=_text_sha256(challenge),
        probe_executable_sha256=_text_sha256(validated_provider_executable(provider, command)),
        terminal_success=result.terminal_success,
        exact_challenge_response=result.exact_challenge_response,
        usage_observed=result.usage_observed,
    )


def _receipt_matches(
    receipt: ProviderAuthenticationReceipt,
    reinjection: RecoveryReinjectionSummary,
    commands: dict[ProviderName, str],
    current: datetime,
) -> bool:
    expected = tuple(commands)
    evidence_names = tuple(item.provider for item in receipt.providers)
    executable_hashes_match = all(
        hmac.compare_digest(
            item.probe_executable_sha256,
            _text_sha256(validated_provider_executable(item.provider, commands[item.provider])),
        )
        for item in receipt.providers
        if item.provider in commands
    )
    return (
        hmac.compare_digest(receipt.recovery_set_sha256, reinjection.recovery_set_sha256)
        and hmac.compare_digest(receipt.reinjection_receipt_sha256, reinjection.receipt_sha256)
        and receipt.config_revision == reinjection.config_revision
        and receipt.owner_decision_ref == reinjection.owner_decision_ref
        and expected == reinjection.provider_names == evidence_names
        and receipt.provider_count == len(expected)
        and executable_hashes_match
        and receipt.checked_at <= current <= receipt.expires_at
    )


def _write_new_receipt(path: Path, receipt: ProviderAuthenticationReceipt) -> None:
    if path.exists() or path.is_symlink():
        raise ProviderAuthenticationError("provider authentication receipt output already exists")
    payload = (
        json.dumps(receipt.model_dump(mode="json"), separators=(",", ":"), sort_keys=True).encode()
        + b"\n"
    )
    temporary: Path | None = None
    published = False
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            os.fchmod(output.fileno(), 0o600)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, path)
        published = True
        _sync_directory(path.parent)
    except FileExistsError:
        raise ProviderAuthenticationError(
            "provider authentication receipt output already exists"
        ) from None
    except Exception:
        if published:
            path.unlink(missing_ok=True)
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _validate_private_file(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError:
        raise ProviderAuthenticationError("provider authentication receipt is missing") from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ProviderAuthenticationError("provider authentication receipt must be a regular file")
    if stat.S_IMODE(metadata.st_mode) & 0o077 or metadata.st_uid != os.getuid():
        raise ProviderAuthenticationError("provider authentication receipt must be owner-only")
    if metadata.st_size <= 0 or metadata.st_size > _MAX_RECEIPT_BYTES:
        raise ProviderAuthenticationError("provider authentication receipt size is invalid")


def _require_outside_checkout(path: Path, checkout: Path) -> None:
    try:
        _canonical_uncreated_path(path).relative_to(checkout.resolve(strict=True))
    except ValueError:
        return
    except OSError:
        raise ProviderAuthenticationError(
            "provider authentication receipt location is invalid"
        ) from None
    raise ProviderAuthenticationError(
        "provider authentication receipt must be outside the checkout"
    )


def _canonical_uncreated_path(path: Path) -> Path:
    missing: list[str] = []
    ancestor = path.parent
    while not ancestor.exists() and not ancestor.is_symlink():
        missing.append(ancestor.name)
        parent = ancestor.parent
        if parent == ancestor:
            raise OSError("no existing output ancestor")
        ancestor = parent
    resolved = ancestor.resolve(strict=True)
    for name in reversed(missing):
        resolved /= name
    return resolved / path.name


def _require_sha(actual: str, expected: str) -> None:
    normalized = expected.strip().lower()
    if re.fullmatch(r"[a-f0-9]{64}", normalized) is None:
        raise ProviderAuthenticationError(
            "expected provider authentication receipt SHA-256 is invalid"
        )
    if not hmac.compare_digest(actual, normalized):
        raise ProviderAuthenticationError("provider authentication receipt SHA-256 does not match")


def _summary(
    operation: Literal["provider-auth-receipt", "verify-provider-auth"],
    path: Path,
    receipt_sha256: str,
    receipt: ProviderAuthenticationReceipt,
    replayed: bool,
) -> ProviderAuthenticationSummary:
    return ProviderAuthenticationSummary(
        operation=operation,
        receipt_name=path.name,
        receipt_sha256=receipt_sha256,
        recovery_set_sha256=receipt.recovery_set_sha256,
        reinjection_receipt_sha256=receipt.reinjection_receipt_sha256,
        config_revision=receipt.config_revision,
        checked_at=receipt.checked_at,
        expires_at=receipt.expires_at,
        provider_names=tuple(item.provider for item in receipt.providers),
        provider_count=receipt.provider_count,
        owner_decision_ref=receipt.owner_decision_ref,
        live_probe_executed=replayed,
    )


def _new_challenge() -> str:
    return f"aico-auth-v1-{secrets.token_hex(24)}"


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(_COPY_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _aware_now(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProviderAuthenticationError("provider authentication time must be timezone-aware")
    return value


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))
