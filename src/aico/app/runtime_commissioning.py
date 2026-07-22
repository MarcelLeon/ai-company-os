"""Secret-free, expiring runtime commissioning receipts."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import stat
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from aico.app.config_revision import (
    ConfigRevisionError,
    ConfigRevisionEvidence,
    capture_config_revision,
)
from aico.app.dead_man_evidence_cli import (
    DeadManEvidenceVerificationError,
    verify_evidence_bytes,
)
from aico.app.dead_man_receiver import DeadManEvidenceBundle
from aico.app.runtime_config_source import capture_file_generation
from aico.core.models import HealthStatus

_MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
_MAX_RECEIPT_BYTES = 64 * 1024
_MAX_EVIDENCE_AGE_SECONDS = 3600
_COPY_CHUNK_BYTES = 1024 * 1024


class RuntimeCommissioningError(RuntimeError):
    """Current runtime commissioning evidence is missing, stale, or mismatched."""


class RuntimeCommissioningReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    runtime_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    checked_at: AwareDatetime
    expires_at: AwareDatetime
    config_revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    config_tree_oid: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    config_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    dotenv_generation_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    dead_man_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    dead_man_evidence_generated_at: AwareDatetime
    dead_man_evidence_expires_at: AwareDatetime
    notification_probe_completed_at: AwareDatetime
    notification_probe_expires_at: AwareDatetime
    maximum_evidence_age_seconds: int = Field(ge=1, le=_MAX_EVIDENCE_AGE_SECONDS)
    minimum_complete_outages: Literal[1] = 1
    all_events_delivered: Literal[True] = True
    fresh_notification_probe: Literal[True] = True
    all_routes_healthy: Literal[True] = True
    dotenv_path_recorded: Literal[False] = False
    dotenv_generation_metadata_recorded: Literal[False] = False
    dotenv_content_recorded: Literal[False] = False
    dotenv_content_hash_recorded: Literal[False] = False
    external_provider_ack_attested: Literal[False] = False
    receiver_origin_attested: Literal[False] = False
    human_read_attested: Literal[False] = False
    verification_authority: Literal["operator_invoked_local_commissioning"] = (
        "operator_invoked_local_commissioning"
    )
    business_absence_ready: Literal[False] = False

    @model_validator(mode="after")
    def validate_expiry_contract(self) -> RuntimeCommissioningReceipt:
        evidence_expiry = self.dead_man_evidence_generated_at + timedelta(
            seconds=self.maximum_evidence_age_seconds
        )
        if self.dead_man_evidence_expires_at != evidence_expiry:
            raise ValueError("commissioning evidence expiry is invalid")
        if self.notification_probe_expires_at <= self.notification_probe_completed_at:
            raise ValueError("commissioning probe expiry is invalid")
        if self.expires_at != min(
            self.dead_man_evidence_expires_at,
            self.notification_probe_expires_at,
        ):
            raise ValueError("commissioning receipt expiry is invalid")
        if not self.dead_man_evidence_generated_at <= self.checked_at <= self.expires_at:
            raise ValueError("commissioning receipt time is outside evidence validity")
        return self


class RuntimeCommissioningSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["create", "verify"]
    receipt_name: str
    receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    runtime_id: str
    config_revision: str
    dead_man_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    checked_at: AwareDatetime
    expires_at: AwareDatetime
    current_bindings_verified: Literal[True] = True
    strict_external_evidence_verified: Literal[True] = True
    business_absence_ready: Literal[False] = False


def create_runtime_commissioning_receipt(
    *,
    checkout_path: Path,
    project_config_path: Path,
    expected_config_revision: str,
    dotenv_path: Path,
    dead_man_evidence_path: Path,
    runtime_id: str,
    maximum_evidence_age_seconds: int,
    output_path: Path,
    persona_config_path: Path | None = None,
    clock: Callable[[], datetime] | None = None,
) -> RuntimeCommissioningSummary:
    checkout = _absolute(checkout_path)
    output = _absolute(output_path)
    _require_outside_checkout(output, checkout, "commissioning receipt")
    if (
        isinstance(maximum_evidence_age_seconds, bool)
        or maximum_evidence_age_seconds < 1
        or maximum_evidence_age_seconds > _MAX_EVIDENCE_AGE_SECONDS
    ):
        raise RuntimeCommissioningError("maximum evidence age is outside commissioning bounds")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        checked_at = _aware_now(clock or (lambda: datetime.now(UTC)))
        config, _ = capture_config_revision(
            checkout,
            project_config_path,
            persona_config_path,
            expected_revision=expected_config_revision,
        )
        dotenv_generation_sha = _dotenv_generation_sha256(dotenv_path)
        evidence_raw = _read_private_external_file(
            dead_man_evidence_path,
            checkout,
            "dead-man evidence",
        )
        verify_evidence_bytes(
            evidence_raw,
            expected_runtime_id=runtime_id,
            minimum_complete_outages=1,
            require_all_delivered=True,
            maximum_evidence_age_seconds=maximum_evidence_age_seconds,
            require_fresh_notification_probe=True,
            require_all_routes_healthy=True,
            now=checked_at,
        )
        bundle = DeadManEvidenceBundle.model_validate_json(evidence_raw)
        receipt = _build_receipt(
            runtime_id=runtime_id,
            checked_at=checked_at,
            config=config,
            dotenv_generation_sha256=dotenv_generation_sha,
            evidence_raw=evidence_raw,
            evidence=bundle,
            maximum_evidence_age_seconds=maximum_evidence_age_seconds,
        )
        _write_new_receipt(output, receipt)
        return _summary("create", output, _sha256(output), receipt)
    except RuntimeCommissioningError:
        raise
    except (ConfigRevisionError, DeadManEvidenceVerificationError, ValidationError, ValueError):
        raise RuntimeCommissioningError("runtime commissioning receipt creation failed") from None
    except Exception:
        raise RuntimeCommissioningError("runtime commissioning receipt creation failed") from None


def verify_runtime_commissioning_receipt(
    *,
    checkout_path: Path,
    project_config_path: Path,
    expected_config_revision: str,
    expected_runtime_id: str,
    dotenv_path: Path,
    dead_man_evidence_path: Path,
    receipt_path: Path,
    persona_config_path: Path | None = None,
    expected_receipt_sha256: str | None = None,
    clock: Callable[[], datetime] | None = None,
) -> RuntimeCommissioningSummary:
    checkout = _absolute(checkout_path)
    receipt_file = _absolute(receipt_path)
    _require_outside_checkout(receipt_file, checkout, "commissioning receipt")
    receipt_raw = _read_private_file(
        receipt_file,
        "commissioning receipt",
        maximum_bytes=_MAX_RECEIPT_BYTES,
    )
    receipt_sha = hashlib.sha256(receipt_raw).hexdigest()
    if expected_receipt_sha256 is not None:
        _require_sha(receipt_sha, expected_receipt_sha256)
    try:
        receipt = RuntimeCommissioningReceipt.model_validate_json(receipt_raw)
        current = _aware_now(clock or (lambda: datetime.now(UTC)))
        if expected_runtime_id != receipt.runtime_id:
            raise RuntimeCommissioningError("commissioning runtime identity does not match")
        if expected_config_revision.strip().lower() != receipt.config_revision:
            raise RuntimeCommissioningError("commissioning config revision does not match")
        config, _ = capture_config_revision(
            checkout,
            project_config_path,
            persona_config_path,
            expected_revision=receipt.config_revision,
        )
        evidence_raw = _read_private_external_file(
            dead_man_evidence_path,
            checkout,
            "dead-man evidence",
        )
        verify_evidence_bytes(
            evidence_raw,
            expected_runtime_id=receipt.runtime_id,
            minimum_complete_outages=receipt.minimum_complete_outages,
            require_all_delivered=receipt.all_events_delivered,
            maximum_evidence_age_seconds=receipt.maximum_evidence_age_seconds,
            require_fresh_notification_probe=receipt.fresh_notification_probe,
            require_all_routes_healthy=receipt.all_routes_healthy,
            now=current,
        )
        evidence = DeadManEvidenceBundle.model_validate_json(evidence_raw)
        if not _current_bindings_match(
            receipt,
            config=config,
            dotenv_generation_sha256=_dotenv_generation_sha256(dotenv_path),
            evidence_raw=evidence_raw,
            evidence=evidence,
            current=current,
        ):
            raise RuntimeCommissioningError("commissioning receipt is stale or mismatched")
        return _summary("verify", receipt_file, receipt_sha, receipt)
    except RuntimeCommissioningError:
        raise
    except (ConfigRevisionError, DeadManEvidenceVerificationError, ValidationError, ValueError):
        raise RuntimeCommissioningError("runtime commissioning receipt is invalid") from None


@dataclass(frozen=True)
class RuntimeCommissioningHealth:
    checkout_path: Path
    project_config_path: Path
    expected_config_revision: str
    expected_runtime_id: str
    dotenv_path: Path
    dead_man_evidence_path: Path
    receipt_path: Path
    persona_config_path: Path | None = None
    clock: Callable[[], datetime] | None = None

    async def health_check(self) -> HealthStatus:
        try:
            await asyncio.to_thread(
                verify_runtime_commissioning_receipt,
                checkout_path=self.checkout_path,
                project_config_path=self.project_config_path,
                expected_config_revision=self.expected_config_revision,
                expected_runtime_id=self.expected_runtime_id,
                dotenv_path=self.dotenv_path,
                dead_man_evidence_path=self.dead_man_evidence_path,
                receipt_path=self.receipt_path,
                persona_config_path=self.persona_config_path,
                clock=self.clock,
            )
        except Exception:
            return HealthStatus.FAILED
        return HealthStatus.OK


def _build_receipt(
    *,
    runtime_id: str,
    checked_at: datetime,
    config: ConfigRevisionEvidence,
    dotenv_generation_sha256: str,
    evidence_raw: bytes,
    evidence: DeadManEvidenceBundle,
    maximum_evidence_age_seconds: int,
) -> RuntimeCommissioningReceipt:
    probe_completed = evidence.notification_probe.last_completed_at
    if probe_completed is None:
        raise RuntimeCommissioningError("completed notification probe is required")
    evidence_expires = evidence.generated_at + timedelta(seconds=maximum_evidence_age_seconds)
    probe_expires = probe_completed + timedelta(seconds=evidence.notification_probe.max_age_seconds)
    return RuntimeCommissioningReceipt(
        runtime_id=runtime_id,
        checked_at=checked_at,
        expires_at=min(evidence_expires, probe_expires),
        config_revision=config.revision,
        config_tree_oid=config.tree_oid,
        config_evidence_sha256=_config_evidence_sha256(config),
        dotenv_generation_sha256=dotenv_generation_sha256,
        dead_man_evidence_sha256=hashlib.sha256(evidence_raw).hexdigest(),
        dead_man_evidence_generated_at=evidence.generated_at,
        dead_man_evidence_expires_at=evidence_expires,
        notification_probe_completed_at=probe_completed,
        notification_probe_expires_at=probe_expires,
        maximum_evidence_age_seconds=maximum_evidence_age_seconds,
    )


def _current_bindings_match(
    receipt: RuntimeCommissioningReceipt,
    *,
    config: ConfigRevisionEvidence,
    dotenv_generation_sha256: str,
    evidence_raw: bytes,
    evidence: DeadManEvidenceBundle,
    current: datetime,
) -> bool:
    probe_completed = evidence.notification_probe.last_completed_at
    if probe_completed is None:
        return False
    evidence_expires = evidence.generated_at + timedelta(
        seconds=receipt.maximum_evidence_age_seconds
    )
    probe_expires = probe_completed + timedelta(seconds=evidence.notification_probe.max_age_seconds)
    return (
        receipt.checked_at <= current <= receipt.expires_at
        and receipt.config_revision == config.revision
        and receipt.config_tree_oid == config.tree_oid
        and hmac.compare_digest(
            receipt.config_evidence_sha256,
            _config_evidence_sha256(config),
        )
        and hmac.compare_digest(
            receipt.dotenv_generation_sha256,
            dotenv_generation_sha256,
        )
        and hmac.compare_digest(
            receipt.dead_man_evidence_sha256,
            hashlib.sha256(evidence_raw).hexdigest(),
        )
        and receipt.dead_man_evidence_generated_at == evidence.generated_at
        and receipt.dead_man_evidence_expires_at == evidence_expires
        and receipt.notification_probe_completed_at == probe_completed
        and receipt.notification_probe_expires_at == probe_expires
        and receipt.expires_at == min(evidence_expires, probe_expires)
    )


def _config_evidence_sha256(evidence: ConfigRevisionEvidence) -> str:
    payload = json.dumps(
        evidence.model_dump(mode="json"),
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _dotenv_generation_sha256(path: Path) -> str:
    candidate = _absolute(path)
    try:
        metadata = candidate.lstat()
    except OSError:
        raise RuntimeCommissioningError("dotenv generation is unavailable") from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeCommissioningError("dotenv must be a regular non-symlink file")
    if stat.S_IMODE(metadata.st_mode) & 0o077 or metadata.st_uid != os.getuid():
        raise RuntimeCommissioningError("dotenv must be owner-only")
    generation = capture_file_generation(candidate)
    if generation is None:
        raise RuntimeCommissioningError("dotenv generation is unavailable")
    payload = ":".join(str(value) for value in generation).encode()
    return hashlib.sha256(payload).hexdigest()


def _read_private_external_file(path: Path, checkout: Path, label: str) -> bytes:
    candidate = _absolute(path)
    _require_outside_checkout(candidate, checkout, label)
    return _read_private_file(candidate, label, maximum_bytes=_MAX_ARTIFACT_BYTES)


def _read_private_file(path: Path, label: str, *, maximum_bytes: int) -> bytes:
    try:
        metadata = path.lstat()
    except OSError:
        raise RuntimeCommissioningError(f"{label} is missing") from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeCommissioningError(f"{label} must be a regular non-symlink file")
    if stat.S_IMODE(metadata.st_mode) & 0o077 or metadata.st_uid != os.getuid():
        raise RuntimeCommissioningError(f"{label} must be owner-only")
    if metadata.st_size <= 0 or metadata.st_size > maximum_bytes:
        raise RuntimeCommissioningError(f"{label} size is invalid")
    try:
        return path.read_bytes()
    except OSError:
        raise RuntimeCommissioningError(f"{label} is unreadable") from None


def _write_new_receipt(path: Path, receipt: RuntimeCommissioningReceipt) -> None:
    if path.exists() or path.is_symlink():
        raise RuntimeCommissioningError("commissioning receipt output already exists")
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
        raise RuntimeCommissioningError("commissioning receipt output already exists") from None
    except Exception:
        if published:
            path.unlink(missing_ok=True)
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _require_outside_checkout(path: Path, checkout: Path, label: str) -> None:
    try:
        _canonical_uncreated_path(path).relative_to(checkout.resolve(strict=True))
    except ValueError:
        return
    except OSError:
        raise RuntimeCommissioningError(f"{label} location is invalid") from None
    raise RuntimeCommissioningError(f"{label} must be outside the checkout")


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
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise RuntimeCommissioningError("expected commissioning receipt SHA-256 is invalid")
    if not hmac.compare_digest(actual, normalized):
        raise RuntimeCommissioningError("commissioning receipt SHA-256 does not match")


def _summary(
    operation: Literal["create", "verify"],
    path: Path,
    receipt_sha256: str,
    receipt: RuntimeCommissioningReceipt,
) -> RuntimeCommissioningSummary:
    return RuntimeCommissioningSummary(
        operation=operation,
        receipt_name=path.name,
        receipt_sha256=receipt_sha256,
        runtime_id=receipt.runtime_id,
        config_revision=receipt.config_revision,
        dead_man_evidence_sha256=receipt.dead_man_evidence_sha256,
        checked_at=receipt.checked_at,
        expires_at=receipt.expires_at,
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
        raise RuntimeCommissioningError("commissioning time must be timezone-aware")
    return value


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))
