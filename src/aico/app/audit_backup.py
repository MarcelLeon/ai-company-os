"""Portable, offline-verifiable recovery points for the durable audit ledger."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from aico.core.audit_ledger import (
    AuditIntegrityError,
    AuditLedgerSummary,
    copy_audit_ledger_snapshot,
    verify_audit_ledger,
)
from aico.core.audit_recovery import replace_audit_ledger_snapshot

AUDIT_BACKUP_SCHEMA_VERSION = 1
AUDIT_LEDGER_MEMBER = "audit.jsonl"
AUDIT_CHECKPOINT_MEMBER = "audit.jsonl.checkpoint.json"
AUDIT_MANIFEST_MEMBER = "manifest.json"
_EXPECTED_MEMBERS = frozenset({AUDIT_LEDGER_MEMBER, AUDIT_CHECKPOINT_MEMBER, AUDIT_MANIFEST_MEMBER})
_MAX_MANIFEST_BYTES = 64 * 1024
_COPY_CHUNK_BYTES = 1024 * 1024


class AuditBackupError(RuntimeError):
    """An audit backup cannot be trusted, created, or verified safely."""


class AuditBackupFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=128)
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class AuditBackupManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    created_at: AwareDatetime
    event_count: int = Field(ge=0)
    byte_size: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    ledger: AuditBackupFile
    checkpoint: AuditBackupFile


class AuditBackupSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["backup", "verify", "materialize"]
    artifact_name: str
    created_at: AwareDatetime
    event_count: int = Field(ge=0)
    ledger_bytes: int = Field(ge=0)
    artifact_bytes: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def create_audit_backup(
    audit_path: Path,
    output_path: Path,
    *,
    clock: Callable[[], datetime] | None = None,
) -> AuditBackupSummary:
    audit = _absolute_path(audit_path)
    output = _absolute_path(output_path)
    if output in {audit, _checkpoint_path(audit)}:
        raise AuditBackupError("backup output must differ from the live audit ledger")
    if output.exists() or output.is_symlink():
        raise AuditBackupError("backup output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_file(output)
    published = False
    try:
        with tempfile.TemporaryDirectory(
            prefix="aico-audit-backup-",
            dir=output.parent,
        ) as raw_directory:
            snapshot_dir = Path(raw_directory)
            snapshot_dir.chmod(0o700)
            ledger = snapshot_dir / AUDIT_LEDGER_MEMBER
            ledger_summary = copy_audit_ledger_snapshot(audit, ledger)
            created_at = (clock or (lambda: datetime.now(UTC)))()
            if created_at.tzinfo is None:
                raise AuditBackupError("backup clock must be timezone-aware")
            manifest = _build_manifest(ledger, ledger_summary, created_at)
            _write_archive(temporary, ledger, manifest)
        summary = _inspect_backup(
            temporary,
            operation="backup",
            artifact_name=output.name,
        )
        _sync_file(temporary)
        _publish_new_file(temporary, output)
        published = True
        _sync_directory(output.parent)
        return summary
    except (AuditBackupError, AuditIntegrityError) as exc:
        if published:
            _discard_published_file(temporary, output)
        raise AuditBackupError(str(exc)) from None
    except Exception:
        if published:
            _discard_published_file(temporary, output)
        raise AuditBackupError("audit backup failed") from None
    finally:
        temporary.unlink(missing_ok=True)


def verify_audit_backup(
    backup_path: Path,
    *,
    expected_sha256: str | None = None,
) -> AuditBackupSummary:
    backup = _absolute_path(backup_path)
    try:
        if not backup.exists():
            raise AuditBackupError("audit backup artifact is missing")
        return _inspect_backup(
            backup,
            operation="verify",
            artifact_name=backup.name,
            expected_sha256=expected_sha256,
        )
    except AuditBackupError:
        raise
    except Exception:
        raise AuditBackupError("audit backup verification failed") from None


def materialize_audit_backup(
    backup_path: Path,
    output_path: Path,
    *,
    expected_sha256: str,
) -> AuditBackupSummary:
    """Materialize one verified artifact as a private ledger/checkpoint pair."""
    backup = _absolute_path(backup_path)
    output = _absolute_path(output_path)
    checkpoint = _checkpoint_path(output)
    if output == backup:
        raise AuditBackupError("audit materialization output and backup must differ")
    if any(candidate.exists() or candidate.is_symlink() for candidate in (output, checkpoint)):
        raise AuditBackupError("audit materialization output already exists")
    try:
        return _inspect_backup(
            backup,
            operation="materialize",
            artifact_name=backup.name,
            expected_sha256=expected_sha256,
            materialize_to=output,
        )
    except AuditBackupError:
        raise
    except Exception:
        raise AuditBackupError("audit backup materialization failed") from None


def _build_manifest(
    ledger: Path,
    summary: AuditLedgerSummary,
    created_at: datetime,
) -> AuditBackupManifest:
    checkpoint = _checkpoint_path(ledger)
    return AuditBackupManifest(
        created_at=created_at,
        event_count=summary.event_count,
        byte_size=summary.byte_size,
        head_sha256=summary.head_sha256,
        ledger=_file_manifest(AUDIT_LEDGER_MEMBER, ledger),
        checkpoint=_file_manifest(AUDIT_CHECKPOINT_MEMBER, checkpoint),
    )


def _write_archive(
    target: Path,
    ledger: Path,
    manifest: AuditBackupManifest,
) -> None:
    payload = (
        json.dumps(
            manifest.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        _write_bytes_member(archive, AUDIT_MANIFEST_MEMBER, payload)
        _write_file_member(archive, AUDIT_LEDGER_MEMBER, ledger)
        _write_file_member(archive, AUDIT_CHECKPOINT_MEMBER, _checkpoint_path(ledger))
    target.chmod(0o600)


def _inspect_backup(
    backup: Path,
    *,
    operation: Literal["backup", "verify", "materialize"],
    artifact_name: str,
    expected_sha256: str | None = None,
    materialize_to: Path | None = None,
) -> AuditBackupSummary:
    _validate_private_file(backup)
    artifact_sha256 = _sha256(backup)
    _require_expected_sha256(artifact_sha256, expected_sha256)
    try:
        with zipfile.ZipFile(backup, "r") as archive:
            members = _validated_members(archive)
            manifest = _read_manifest(archive, members[AUDIT_MANIFEST_MEMBER])
            _validate_manifest(manifest, members)
            with tempfile.TemporaryDirectory(prefix="aico-audit-verify-") as raw_directory:
                directory = Path(raw_directory)
                directory.chmod(0o700)
                ledger = directory / AUDIT_LEDGER_MEMBER
                _extract_member(archive, members[AUDIT_LEDGER_MEMBER], ledger, manifest.ledger)
                _extract_member(
                    archive,
                    members[AUDIT_CHECKPOINT_MEMBER],
                    _checkpoint_path(ledger),
                    manifest.checkpoint,
                )
                ledger_summary = verify_audit_ledger(ledger)
                _require_manifest_parity(ledger_summary, manifest)
                if materialize_to is not None:
                    restored = replace_audit_ledger_snapshot(materialize_to, ledger)
                    if restored != ledger_summary:
                        raise AuditBackupError("materialized audit ledger does not match backup")
    except AuditBackupError:
        raise
    except (
        AuditIntegrityError,
        EOFError,
        OSError,
        RuntimeError,
        ValidationError,
        ValueError,
        zipfile.BadZipFile,
    ):
        raise AuditBackupError("audit backup integrity verification failed") from None
    return AuditBackupSummary(
        operation=operation,
        artifact_name=artifact_name,
        created_at=manifest.created_at,
        event_count=manifest.event_count,
        ledger_bytes=manifest.byte_size,
        artifact_bytes=backup.stat().st_size,
        head_sha256=manifest.head_sha256,
        sha256=artifact_sha256,
    )


def _require_manifest_parity(
    ledger: AuditLedgerSummary,
    manifest: AuditBackupManifest,
) -> None:
    if (
        not ledger.sealed
        or ledger.checkpoint_lag
        or ledger.event_count != manifest.event_count
        or ledger.byte_size != manifest.byte_size
        or ledger.head_sha256 != manifest.head_sha256
    ):
        raise AuditBackupError("audit backup ledger does not match its manifest")


def _validated_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    names = [info.filename for info in infos]
    if len(infos) != len(_EXPECTED_MEMBERS) or set(names) != _EXPECTED_MEMBERS:
        raise AuditBackupError("audit backup members are invalid")
    for info in infos:
        if info.is_dir() or info.flag_bits & 0x1 or info.compress_type != zipfile.ZIP_STORED:
            raise AuditBackupError("audit backup member encoding is invalid")
        if info.file_size != info.compress_size:
            raise AuditBackupError("audit backup member size is invalid")
    manifest = next(info for info in infos if info.filename == AUDIT_MANIFEST_MEMBER)
    if manifest.file_size > _MAX_MANIFEST_BYTES:
        raise AuditBackupError("audit backup manifest is too large")
    return {info.filename: info for info in infos}


def _read_manifest(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
) -> AuditBackupManifest:
    try:
        return AuditBackupManifest.model_validate_json(archive.read(info))
    except ValidationError:
        raise AuditBackupError("audit backup manifest is invalid") from None


def _validate_manifest(
    manifest: AuditBackupManifest,
    members: dict[str, zipfile.ZipInfo],
) -> None:
    if manifest.ledger.name != AUDIT_LEDGER_MEMBER:
        raise AuditBackupError("audit backup ledger manifest is invalid")
    if manifest.checkpoint.name != AUDIT_CHECKPOINT_MEMBER:
        raise AuditBackupError("audit backup checkpoint manifest is invalid")
    if manifest.byte_size != manifest.ledger.bytes:
        raise AuditBackupError("audit backup ledger size does not match its manifest")
    for file_manifest in (manifest.ledger, manifest.checkpoint):
        if members[file_manifest.name].file_size != file_manifest.bytes:
            raise AuditBackupError("audit backup member size does not match its manifest")


def _extract_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    target: Path,
    expected: AuditBackupFile,
) -> None:
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    digest = hashlib.sha256()
    copied = 0
    with archive.open(info, "r") as source, os.fdopen(descriptor, "wb", closefd=True) as output:
        while chunk := source.read(_COPY_CHUNK_BYTES):
            output.write(chunk)
            digest.update(chunk)
            copied += len(chunk)
        output.flush()
        os.fsync(output.fileno())
    if copied != expected.bytes or not hmac.compare_digest(digest.hexdigest(), expected.sha256):
        raise AuditBackupError("audit backup member hash does not match its manifest")


def _write_bytes_member(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    with archive.open(_member_info(name), "w") as output:
        output.write(payload)


def _write_file_member(archive: zipfile.ZipFile, name: str, source: Path) -> None:
    with source.open("rb") as input_file, archive.open(_member_info(name), "w") as output:
        shutil.copyfileobj(input_file, output, length=_COPY_CHUNK_BYTES)


def _member_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info


def _file_manifest(name: str, path: Path) -> AuditBackupFile:
    return AuditBackupFile(name=name, bytes=path.stat().st_size, sha256=_sha256(path))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_COPY_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _require_expected_sha256(actual: str, expected: str | None) -> None:
    if expected is None:
        return
    normalized = expected.lower()
    if re.fullmatch(r"[a-f0-9]{64}", normalized) is None:
        raise AuditBackupError("expected audit backup SHA-256 is invalid")
    if not hmac.compare_digest(actual, normalized):
        raise AuditBackupError("audit backup SHA-256 does not match expected value")


def _validate_private_file(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError:
        raise AuditBackupError("audit backup metadata is unavailable") from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise AuditBackupError("audit backup must be a regular non-symlink file")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise AuditBackupError("audit backup must be owned by the current user")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise AuditBackupError("audit backup must be owner-only")


def _temporary_file(target: Path) -> Path:
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    os.close(descriptor)
    return Path(raw_path)


def _publish_new_file(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
    except FileExistsError:
        raise AuditBackupError("backup output already exists") from None


def _discard_published_file(source: Path, destination: Path) -> None:
    try:
        if destination.exists() and os.path.samefile(source, destination):
            destination.unlink()
            _sync_directory(destination.parent)
    except OSError:
        pass


def _sync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def _checkpoint_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.checkpoint.json")
