"""Portable backup, drill, and owner-fenced restore for durable memory."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from aico.app.runtime_owner import RuntimeOwnerLock, RuntimeOwnershipError, runtime_owner_lock_path
from aico.core.memory import JsonlMemoryStore
from aico.core.memory_ledger import (
    MemoryIntegrityError,
    MemoryLedgerSummary,
    copy_memory_ledger_snapshot,
    copy_raw_memory_ledger_snapshot,
    memory_checkpoint_path,
    replace_memory_ledger_snapshot,
    verify_memory_ledger,
)
from aico.core.sqlite_state import STATE_SCHEMA_VERSION

MEMORY_LEDGER_MEMBER = "memory.jsonl"
MEMORY_CHECKPOINT_MEMBER = "memory.jsonl.checkpoint.json"
MEMORY_MANIFEST_MEMBER = "manifest.json"
MEMORY_QUARANTINE_MANIFEST_MEMBER = "quarantine.json"
_EXPECTED_MEMBERS = frozenset(
    {MEMORY_LEDGER_MEMBER, MEMORY_CHECKPOINT_MEMBER, MEMORY_MANIFEST_MEMBER}
)
_COPY_CHUNK_BYTES = 1024 * 1024
_MAX_MANIFEST_BYTES = 64 * 1024


class MemoryRecoveryError(RuntimeError):
    """A memory recovery operation could not complete safely."""


class MemoryRecoveryFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=128)
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class MemoryBackupManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    created_at: AwareDatetime
    record_count: int = Field(ge=0)
    byte_size: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    ledger: MemoryRecoveryFile
    checkpoint: MemoryRecoveryFile


class MemoryBackupSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["backup", "verify", "materialize"]
    artifact_name: str
    created_at: AwareDatetime
    record_count: int = Field(ge=0)
    ledger_bytes: int = Field(ge=0)
    artifact_bytes: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class MemoryPreservationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["verified_safety", "unverified_quarantine"]
    artifact_name: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class MemoryDrillSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["drill"] = "drill"
    artifact_name: str
    record_count: int = Field(ge=0)
    ledger_bytes: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    backup_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    completed_at: AwareDatetime
    report_name: str | None = None


class MemoryRestoreSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["restore"] = "restore"
    record_count: int = Field(ge=0)
    ledger_bytes: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    backup_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    preservation: MemoryPreservationSummary | None = None


def create_memory_backup(
    memory_path: Path,
    output_path: Path,
    *,
    clock: Callable[[], datetime] | None = None,
) -> MemoryBackupSummary:
    memory = _absolute(memory_path)
    output = _absolute(output_path)
    if output in {memory, memory_checkpoint_path(memory)}:
        raise MemoryRecoveryError("backup output must differ from the live memory ledger")
    if output.exists() or output.is_symlink():
        raise MemoryRecoveryError("backup output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary(output)
    published = False
    try:
        with tempfile.TemporaryDirectory(prefix="aico-memory-backup-", dir=output.parent) as raw:
            directory = Path(raw)
            directory.chmod(0o700)
            ledger = directory / MEMORY_LEDGER_MEMBER
            summary = copy_memory_ledger_snapshot(memory, ledger)
            created_at = (clock or (lambda: datetime.now(UTC)))()
            if created_at.tzinfo is None:
                raise MemoryRecoveryError("backup clock must be timezone-aware")
            manifest = _manifest(ledger, summary, created_at)
            _write_backup(temporary, ledger, manifest)
        inspected = _inspect_backup(temporary, operation="backup", artifact_name=output.name)
        _sync_file(temporary)
        _publish_new(temporary, output, "backup output already exists")
        published = True
        _sync_directory(output.parent)
        return inspected
    except (MemoryRecoveryError, MemoryIntegrityError) as exc:
        if published:
            _discard_published(temporary, output)
        raise MemoryRecoveryError(str(exc)) from None
    except Exception:
        if published:
            _discard_published(temporary, output)
        raise MemoryRecoveryError("memory backup failed") from None
    finally:
        temporary.unlink(missing_ok=True)


def verify_memory_backup(
    backup_path: Path,
    *,
    expected_sha256: str | None = None,
) -> MemoryBackupSummary:
    return _inspect_backup(
        _absolute(backup_path),
        operation="verify",
        artifact_name=backup_path.name,
        expected_sha256=expected_sha256,
    )


def materialize_memory_backup(
    backup_path: Path,
    output_path: Path,
    *,
    expected_sha256: str,
) -> MemoryBackupSummary:
    output = _absolute(output_path)
    if any(item.exists() or item.is_symlink() for item in (output, memory_checkpoint_path(output))):
        raise MemoryRecoveryError("memory materialization output already exists")
    return _inspect_backup(
        _absolute(backup_path),
        operation="materialize",
        artifact_name=backup_path.name,
        expected_sha256=expected_sha256,
        materialize_to=output,
    )


def drill_memory_backup(
    backup_path: Path,
    *,
    expected_sha256: str,
    workspace: Path | None = None,
    report_path: Path | None = None,
    clock: Callable[[], datetime] | None = None,
) -> MemoryDrillSummary:
    backup = _absolute(backup_path)
    parent = _workspace(workspace)
    report = _new_output(report_path, forbidden={backup})
    try:
        with tempfile.TemporaryDirectory(prefix="aico-memory-drill-", dir=parent) as raw:
            target = Path(raw) / MEMORY_LEDGER_MEMBER
            materialized = materialize_memory_backup(
                backup, target, expected_sha256=expected_sha256
            )
            verified = verify_memory_ledger(target)
            JsonlMemoryStore(target)
            _require_parity(verified, materialized)
            completed_at = (clock or (lambda: datetime.now(UTC)))()
            if completed_at.tzinfo is None:
                raise MemoryRecoveryError("drill clock must be timezone-aware")
            result = MemoryDrillSummary(
                artifact_name=backup.name,
                record_count=verified.record_count,
                ledger_bytes=verified.byte_size,
                head_sha256=verified.head_sha256,
                backup_sha256=materialized.sha256,
                completed_at=completed_at,
                report_name=report.name if report else None,
            )
        if report:
            _write_new_private(report, result.model_dump_json() + "\n")
        return result
    except MemoryRecoveryError:
        raise
    except (MemoryIntegrityError, OSError, ValueError):
        raise MemoryRecoveryError("disposable memory restore drill failed") from None


def restore_memory_backup(
    target_path: Path,
    backup_path: Path,
    *,
    expected_sha256: str,
    state_db_path: Path,
    preservation_path: Path,
    base_dir: Path,
    confirmed: bool,
    clock: Callable[[], datetime] | None = None,
) -> MemoryRestoreSummary:
    if not confirmed:
        raise MemoryRecoveryError("explicit restore confirmation is required")
    target, backup = _absolute(target_path), _absolute(backup_path)
    state_db, preservation = _absolute(state_db_path), _absolute(preservation_path)
    _validate_restore_paths(target, backup, state_db, preservation)
    verified = verify_memory_backup(backup, expected_sha256=expected_sha256)
    owner = RuntimeOwnerLock(
        runtime_owner_lock_path(state_db, base_dir=base_dir), resource_path=state_db
    )
    try:
        owner.acquire()
    except RuntimeOwnershipError:
        raise MemoryRecoveryError("runtime owner is active; memory restore refused") from None
    try:
        preserved = _preserve_live(target, preservation, clock=clock)
        with tempfile.TemporaryDirectory(prefix="aico-memory-restore-", dir=target.parent) as raw:
            source = Path(raw) / MEMORY_LEDGER_MEMBER
            materialize_memory_backup(backup, source, expected_sha256=verified.sha256)
            restored = replace_memory_ledger_snapshot(target, source)
        return MemoryRestoreSummary(
            record_count=restored.record_count,
            ledger_bytes=restored.byte_size,
            head_sha256=restored.head_sha256,
            backup_sha256=verified.sha256,
            preservation=preserved,
        )
    except MemoryRecoveryError:
        raise
    except (MemoryIntegrityError, OSError, ValueError) as exc:
        raise MemoryRecoveryError(str(exc)) from None
    finally:
        owner.release()


def _inspect_backup(
    backup: Path,
    *,
    operation: Literal["backup", "verify", "materialize"],
    artifact_name: str,
    expected_sha256: str | None = None,
    materialize_to: Path | None = None,
) -> MemoryBackupSummary:
    try:
        _validate_private_file(backup, "memory backup")
        artifact_sha = _sha256(backup)
        _expected_hash(artifact_sha, expected_sha256)
        with zipfile.ZipFile(backup) as archive:
            members = _validated_members(archive)
            manifest = MemoryBackupManifest.model_validate_json(
                archive.read(members[MEMORY_MANIFEST_MEMBER])
            )
            _validate_manifest(manifest, members)
            with tempfile.TemporaryDirectory(prefix="aico-memory-verify-") as raw:
                ledger = Path(raw) / MEMORY_LEDGER_MEMBER
                _extract(archive, members[MEMORY_LEDGER_MEMBER], ledger, manifest.ledger)
                _extract(
                    archive,
                    members[MEMORY_CHECKPOINT_MEMBER],
                    memory_checkpoint_path(ledger),
                    manifest.checkpoint,
                )
                verified = verify_memory_ledger(ledger)
                JsonlMemoryStore(ledger)
                _require_manifest_parity(verified, manifest)
                if materialize_to:
                    restored = replace_memory_ledger_snapshot(materialize_to, ledger)
                    if restored != verified:
                        raise MemoryRecoveryError("materialized memory does not match backup")
        return MemoryBackupSummary(
            operation=operation,
            artifact_name=artifact_name,
            created_at=manifest.created_at,
            record_count=manifest.record_count,
            ledger_bytes=manifest.byte_size,
            artifact_bytes=backup.stat().st_size,
            head_sha256=manifest.head_sha256,
            sha256=artifact_sha,
        )
    except MemoryRecoveryError:
        raise
    except (
        MemoryIntegrityError,
        OSError,
        ValidationError,
        ValueError,
        zipfile.BadZipFile,
    ):
        raise MemoryRecoveryError("memory backup integrity verification failed") from None


def _manifest(
    ledger: Path, summary: MemoryLedgerSummary, created_at: datetime
) -> MemoryBackupManifest:
    checkpoint = memory_checkpoint_path(ledger)
    return MemoryBackupManifest(
        created_at=created_at,
        record_count=summary.record_count,
        byte_size=summary.byte_size,
        head_sha256=summary.head_sha256,
        ledger=_file_record(MEMORY_LEDGER_MEMBER, ledger),
        checkpoint=_file_record(MEMORY_CHECKPOINT_MEMBER, checkpoint),
    )


def _write_backup(target: Path, ledger: Path, manifest: MemoryBackupManifest) -> None:
    payload = (
        json.dumps(manifest.model_dump(mode="json"), separators=(",", ":"), sort_keys=True).encode()
        + b"\n"
    )
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(_member_info(MEMORY_MANIFEST_MEMBER), payload)
        _write_member(archive, MEMORY_LEDGER_MEMBER, ledger)
        _write_member(archive, MEMORY_CHECKPOINT_MEMBER, memory_checkpoint_path(ledger))
    target.chmod(0o600)


def _validated_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    if len(infos) != 3 or {item.filename for item in infos} != _EXPECTED_MEMBERS:
        raise MemoryRecoveryError("memory backup members are invalid")
    for item in infos:
        if item.is_dir() or item.flag_bits & 1 or item.compress_type != zipfile.ZIP_STORED:
            raise MemoryRecoveryError("memory backup member encoding is invalid")
        if item.file_size != item.compress_size:
            raise MemoryRecoveryError("memory backup member size is invalid")
    manifest = next(item for item in infos if item.filename == MEMORY_MANIFEST_MEMBER)
    if manifest.file_size > _MAX_MANIFEST_BYTES:
        raise MemoryRecoveryError("memory backup manifest is too large")
    return {item.filename: item for item in infos}


def _validate_manifest(manifest: MemoryBackupManifest, members: dict[str, zipfile.ZipInfo]) -> None:
    if manifest.ledger.name != MEMORY_LEDGER_MEMBER:
        raise MemoryRecoveryError("memory backup ledger manifest is invalid")
    if manifest.checkpoint.name != MEMORY_CHECKPOINT_MEMBER:
        raise MemoryRecoveryError("memory backup checkpoint manifest is invalid")
    if manifest.byte_size != manifest.ledger.bytes:
        raise MemoryRecoveryError("memory backup ledger size does not match manifest")
    for item in (manifest.ledger, manifest.checkpoint):
        if members[item.name].file_size != item.bytes:
            raise MemoryRecoveryError("memory backup member size does not match manifest")


def _extract(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    target: Path,
    expected: MemoryRecoveryFile,
) -> None:
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    digest = hashlib.sha256()
    copied = 0
    with archive.open(info) as source, os.fdopen(descriptor, "wb") as output:
        while chunk := source.read(_COPY_CHUNK_BYTES):
            output.write(chunk)
            digest.update(chunk)
            copied += len(chunk)
        output.flush()
        os.fsync(output.fileno())
    if copied != expected.bytes or not hmac.compare_digest(digest.hexdigest(), expected.sha256):
        raise MemoryRecoveryError("memory backup member hash mismatch")


def _preserve_live(
    target: Path,
    output: Path,
    *,
    clock: Callable[[], datetime] | None,
) -> MemoryPreservationSummary | None:
    if not target.exists() and not memory_checkpoint_path(target).exists():
        return None
    try:
        live = verify_memory_ledger(target)
        JsonlMemoryStore(target)
    except (MemoryIntegrityError, ValueError):
        live = None
    if live and live.sealed:
        backup = create_memory_backup(target, output, clock=clock)
        return MemoryPreservationSummary(
            kind="verified_safety", artifact_name=output.name, sha256=backup.sha256
        )
    return _quarantine(target, output, clock=clock)


def _quarantine(
    target: Path,
    output: Path,
    *,
    clock: Callable[[], datetime] | None,
) -> MemoryPreservationSummary:
    temporary = _temporary(output)
    published = False
    try:
        with tempfile.TemporaryDirectory(
            prefix="aico-memory-quarantine-", dir=output.parent
        ) as raw:
            ledger = Path(raw) / MEMORY_LEDGER_MEMBER
            ledger_present, checkpoint_present = copy_raw_memory_ledger_snapshot(target, ledger)
            files = []
            for name, path, present in (
                (MEMORY_LEDGER_MEMBER, ledger, ledger_present),
                (MEMORY_CHECKPOINT_MEMBER, memory_checkpoint_path(ledger), checkpoint_present),
            ):
                if present:
                    files.append(_file_record(name, path).model_dump(mode="json"))
            created_at = (clock or (lambda: datetime.now(UTC)))()
            if created_at.tzinfo is None:
                raise MemoryRecoveryError("quarantine clock must be timezone-aware")
            manifest = (
                json.dumps(
                    {
                        "created_at": created_at.isoformat(),
                        "files": files,
                        "kind": "unverified_quarantine",
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode()
                + b"\n"
            )
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(_member_info(MEMORY_QUARANTINE_MANIFEST_MEMBER), manifest)
                if ledger_present:
                    _write_member(archive, MEMORY_LEDGER_MEMBER, ledger)
                if checkpoint_present:
                    _write_member(archive, MEMORY_CHECKPOINT_MEMBER, memory_checkpoint_path(ledger))
            temporary.chmod(0o600)
        _sync_file(temporary)
        _publish_new(temporary, output, "preservation output already exists")
        published = True
        _sync_directory(output.parent)
        return MemoryPreservationSummary(
            kind="unverified_quarantine", artifact_name=output.name, sha256=_sha256(output)
        )
    finally:
        if published is False and output.exists():
            _discard_published(temporary, output)
        temporary.unlink(missing_ok=True)


def _validate_restore_paths(target: Path, backup: Path, state_db: Path, output: Path) -> None:
    if len({target, memory_checkpoint_path(target), backup, state_db, output}) != 5:
        raise MemoryRecoveryError("memory restore inputs and outputs must differ")
    _validate_state_database(state_db)
    if output.exists() or output.is_symlink():
        raise MemoryRecoveryError("preservation output already exists")
    if not target.parent.is_dir():
        raise MemoryRecoveryError("memory restore target directory is missing")


def _validate_state_database(path: Path) -> None:
    _validate_private_file(path, "state database", require_private=False)
    try:
        with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT value FROM aico_schema WHERE key = 'schema_version'"
            ).fetchone()
            healthy = connection.execute("PRAGMA quick_check").fetchall() == [("ok",)]
        if row is None or int(row[0]) != STATE_SCHEMA_VERSION or not healthy:
            raise MemoryRecoveryError("state database is not a healthy supported AICO database")
    except MemoryRecoveryError:
        raise
    except (sqlite3.Error, TypeError, ValueError):
        raise MemoryRecoveryError("state database identity verification failed") from None


def _require_manifest_parity(ledger: MemoryLedgerSummary, manifest: MemoryBackupManifest) -> None:
    if (
        not ledger.sealed
        or ledger.checkpoint_lag
        or ledger.record_count != manifest.record_count
        or ledger.byte_size != manifest.byte_size
        or ledger.head_sha256 != manifest.head_sha256
    ):
        raise MemoryRecoveryError("memory backup ledger does not match manifest")


def _require_parity(ledger: MemoryLedgerSummary, backup: MemoryBackupSummary) -> None:
    if (
        ledger.record_count != backup.record_count
        or ledger.byte_size != backup.ledger_bytes
        or ledger.head_sha256 != backup.head_sha256
        or not ledger.sealed
        or ledger.checkpoint_lag
    ):
        raise MemoryRecoveryError("drill materialized memory does not match backup")


def _workspace(path: Path | None) -> Path | None:
    if path is None:
        return None
    result = _absolute(path)
    if not result.is_dir():
        raise MemoryRecoveryError("drill workspace is missing or not a directory")
    return result


def _new_output(path: Path | None, *, forbidden: set[Path]) -> Path | None:
    if path is None:
        return None
    result = _absolute(path)
    if result in forbidden or result.exists() or result.is_symlink():
        raise MemoryRecoveryError("drill report output is invalid or already exists")
    return result


def _write_new_private(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary(path)
    published = False
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.chmod(0o600)
        _sync_file(temporary)
        _publish_new(temporary, path, "drill report already exists")
        published = True
        _sync_directory(path.parent)
    finally:
        if not published:
            _discard_published(temporary, path)
        temporary.unlink(missing_ok=True)


def _expected_hash(actual: str, expected: str | None) -> None:
    if expected is None:
        return
    normalized = expected.lower()
    if re.fullmatch(r"[a-f0-9]{64}", normalized) is None:
        raise MemoryRecoveryError("expected memory backup SHA-256 is invalid")
    if not hmac.compare_digest(actual, normalized):
        raise MemoryRecoveryError("memory backup SHA-256 does not match expected value")


def _validate_private_file(path: Path, label: str, *, require_private: bool = True) -> None:
    try:
        metadata = path.lstat()
    except OSError:
        raise MemoryRecoveryError(f"{label} is missing") from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise MemoryRecoveryError(f"{label} must be a regular non-symlink file")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise MemoryRecoveryError(f"{label} must be owned by the runtime user")
    if require_private and stat.S_IMODE(metadata.st_mode) & 0o077:
        raise MemoryRecoveryError(f"{label} must be owner-only")


def _file_record(name: str, path: Path) -> MemoryRecoveryFile:
    return MemoryRecoveryFile(name=name, bytes=path.stat().st_size, sha256=_sha256(path))


def _write_member(archive: zipfile.ZipFile, name: str, source: Path) -> None:
    with source.open("rb") as input_file, archive.open(_member_info(name), "w") as output:
        shutil.copyfileobj(input_file, output, length=_COPY_CHUNK_BYTES)


def _member_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_COPY_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _temporary(target: Path) -> Path:
    descriptor, raw = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(descriptor)
    return Path(raw)


def _publish_new(source: Path, destination: Path, error: str) -> None:
    try:
        os.link(source, destination)
    except FileExistsError:
        raise MemoryRecoveryError(error) from None


def _discard_published(source: Path, destination: Path) -> None:
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


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))
