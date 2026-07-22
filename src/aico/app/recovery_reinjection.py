"""Owner-only post-restore receipts for secret and standing-grant reinjection."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import stat
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from aico.app.recovery_set import (
    RecoverySetError,
    verify_recovery_runtime_reinjection,
)
from aico.app.runtime_reinjection import ProviderName, RuntimeReinjectionEvidence, RuntimeSecretSlot

_MAX_RECEIPT_BYTES = 64 * 1024
_COPY_CHUNK_BYTES = 1024 * 1024


class RecoveryReinjectionError(RuntimeError):
    """A post-restore runtime reinjection receipt is missing or untrustworthy."""


class RecoveryReinjectionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[2] = 2
    recovery_set_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    checked_at: AwareDatetime
    channel: Literal["telegram", "feishu"]
    secret_slots: tuple[RuntimeSecretSlot, ...] = Field(min_length=1, max_length=5)
    secret_slot_count: int = Field(ge=1, le=5)
    secrets_present: Literal[True] = True
    secret_values_recorded: Literal[False] = False
    secret_hashes_recorded: Literal[False] = False
    standing_grant_required: bool
    standing_grant_count: int = Field(ge=0, le=1000)
    standing_grant_binding_verified: Literal[True] = True
    provider_names: tuple[ProviderName, ...] = Field(min_length=1, max_length=6)
    provider_count: int = Field(ge=1, le=6)
    external_authentication_live_verified: Literal[False] = False
    owner_decision_ref: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    verification_authority: Literal["operator_invoked_post_restore"] = (
        "operator_invoked_post_restore"
    )
    business_restore_ready: Literal[False] = False

    @model_validator(mode="after")
    def validate_receipt(self) -> RecoveryReinjectionReceipt:
        if self.secret_slot_count != len(self.secret_slots):
            raise ValueError("reinjection receipt secret slot count does not match")
        if self.standing_grant_required != (self.standing_grant_count > 0):
            raise ValueError("reinjection receipt standing grant mode does not match")
        if self.provider_count != len(self.provider_names):
            raise ValueError("reinjection receipt provider count does not match")
        if any(
            fragment in self.owner_decision_ref.casefold()
            for fragment in ("replace-with", "replace-me", "example")
        ):
            raise ValueError("reinjection receipt owner decision reference is a placeholder")
        return self


class RecoveryReinjectionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["reinjection-receipt", "verify-reinjection"]
    receipt_name: str
    receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    recovery_set_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    checked_at: AwareDatetime
    channel: Literal["telegram", "feishu"]
    secret_slot_count: int = Field(ge=1, le=5)
    standing_grant_required: bool
    standing_grant_count: int = Field(ge=0, le=1000)
    provider_names: tuple[ProviderName, ...] = Field(min_length=1, max_length=6)
    provider_count: int = Field(ge=1, le=6)
    owner_decision_ref: str = Field(min_length=1, max_length=128)
    business_restore_ready: Literal[False] = False


def create_recovery_reinjection_receipt(
    recovery_set_path: Path,
    *,
    expected_recovery_set_sha256: str,
    checkout_path: Path,
    output_path: Path,
    owner_decision_ref: str,
    clock: Callable[[], datetime] | None = None,
) -> RecoveryReinjectionSummary:
    checkout = _absolute(checkout_path)
    output = _absolute(output_path)
    _require_outside_checkout(output, checkout)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        recovery, evidence = verify_recovery_runtime_reinjection(
            recovery_set_path,
            expected_sha256=expected_recovery_set_sha256,
            checkout_path=checkout,
        )
        checked_at = _aware_now(clock or (lambda: datetime.now(UTC)))
        receipt = RecoveryReinjectionReceipt(
            recovery_set_sha256=recovery.sha256,
            config_revision=recovery.config_revision,
            checked_at=checked_at,
            channel=evidence.channel,
            secret_slots=evidence.secret_slots,
            secret_slot_count=evidence.secret_slot_count,
            standing_grant_required=evidence.standing_grant_required,
            standing_grant_count=evidence.standing_grant_count,
            provider_names=evidence.provider_names,
            provider_count=evidence.provider_count,
            owner_decision_ref=owner_decision_ref,
        )
        _write_new_receipt(output, receipt)
        receipt_sha = _sha256(output)
        return _summary("reinjection-receipt", output, receipt_sha, receipt)
    except RecoveryReinjectionError:
        raise
    except RecoverySetError as exc:
        raise RecoveryReinjectionError(str(exc)) from None
    except Exception:
        raise RecoveryReinjectionError("runtime reinjection receipt creation failed") from None


def verify_recovery_reinjection_receipt(
    recovery_set_path: Path,
    *,
    expected_recovery_set_sha256: str,
    checkout_path: Path,
    receipt_path: Path,
    expected_receipt_sha256: str,
) -> RecoveryReinjectionSummary:
    checkout = _absolute(checkout_path)
    receipt_file = _absolute(receipt_path)
    _require_outside_checkout(receipt_file, checkout)
    _validate_private_file(receipt_file)
    receipt_sha = _sha256(receipt_file)
    _require_sha(receipt_sha, expected_receipt_sha256, "reinjection receipt")
    try:
        receipt = RecoveryReinjectionReceipt.model_validate_json(receipt_file.read_bytes())
        recovery, evidence = verify_recovery_runtime_reinjection(
            recovery_set_path,
            expected_sha256=expected_recovery_set_sha256,
            checkout_path=checkout,
        )
        if not _receipt_matches(receipt, recovery.sha256, recovery.config_revision, evidence):
            raise RecoveryReinjectionError("reinjection receipt does not match current runtime")
        return _summary("verify-reinjection", receipt_file, receipt_sha, receipt)
    except RecoveryReinjectionError:
        raise
    except RecoverySetError as exc:
        raise RecoveryReinjectionError(str(exc)) from None
    except (OSError, ValidationError, ValueError):
        raise RecoveryReinjectionError("reinjection receipt is invalid") from None


def _receipt_matches(
    receipt: RecoveryReinjectionReceipt,
    recovery_set_sha256: str,
    config_revision: str,
    evidence: RuntimeReinjectionEvidence,
) -> bool:
    return (
        hmac.compare_digest(receipt.recovery_set_sha256, recovery_set_sha256)
        and receipt.config_revision == config_revision
        and receipt.channel == evidence.channel
        and receipt.secret_slots == evidence.secret_slots
        and receipt.secret_slot_count == evidence.secret_slot_count
        and receipt.standing_grant_required == evidence.standing_grant_required
        and receipt.standing_grant_count == evidence.standing_grant_count
        and receipt.provider_names == evidence.provider_names
        and receipt.provider_count == evidence.provider_count
    )


def _write_new_receipt(path: Path, receipt: RecoveryReinjectionReceipt) -> None:
    if path.exists() or path.is_symlink():
        raise RecoveryReinjectionError("reinjection receipt output already exists")
    payload = (
        json.dumps(
            receipt.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
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
        raise RecoveryReinjectionError("reinjection receipt output already exists") from None
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
        raise RecoveryReinjectionError("reinjection receipt is missing or unreadable") from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RecoveryReinjectionError("reinjection receipt must be a regular non-symlink file")
    if stat.S_IMODE(metadata.st_mode) & 0o077 or metadata.st_uid != os.getuid():
        raise RecoveryReinjectionError("reinjection receipt must be owner-only")
    if metadata.st_size <= 0 or metadata.st_size > _MAX_RECEIPT_BYTES:
        raise RecoveryReinjectionError("reinjection receipt size is invalid")


def _require_outside_checkout(path: Path, checkout: Path) -> None:
    try:
        candidate = _canonical_uncreated_path(path)
        candidate.relative_to(checkout.resolve(strict=True))
    except ValueError:
        return
    except OSError:
        raise RecoveryReinjectionError("reinjection receipt location is invalid") from None
    raise RecoveryReinjectionError("reinjection receipt must be outside the checkout")


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


def _require_sha(actual: str, expected: str, label: str) -> None:
    normalized = expected.strip().lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise RecoveryReinjectionError(f"expected {label} SHA-256 is invalid")
    if not hmac.compare_digest(actual, normalized):
        raise RecoveryReinjectionError(f"{label} SHA-256 does not match")


def _summary(
    operation: Literal["reinjection-receipt", "verify-reinjection"],
    path: Path,
    receipt_sha256: str,
    receipt: RecoveryReinjectionReceipt,
) -> RecoveryReinjectionSummary:
    return RecoveryReinjectionSummary(
        operation=operation,
        receipt_name=path.name,
        receipt_sha256=receipt_sha256,
        recovery_set_sha256=receipt.recovery_set_sha256,
        config_revision=receipt.config_revision,
        checked_at=receipt.checked_at,
        channel=receipt.channel,
        secret_slot_count=receipt.secret_slot_count,
        standing_grant_required=receipt.standing_grant_required,
        standing_grant_count=receipt.standing_grant_count,
        provider_names=receipt.provider_names,
        provider_count=receipt.provider_count,
        owner_decision_ref=receipt.owner_decision_ref,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(_COPY_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _aware_now(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise RecoveryReinjectionError("reinjection receipt time must be timezone-aware")
    return value


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))
