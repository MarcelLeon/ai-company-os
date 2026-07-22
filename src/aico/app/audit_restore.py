"""Disposable drills and owner-fenced restore for audit recovery artifacts."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from aico.app.audit_backup import (
    AUDIT_CHECKPOINT_MEMBER,
    AUDIT_LEDGER_MEMBER,
    AuditBackupError,
    AuditBackupSummary,
    create_audit_backup,
    materialize_audit_backup,
    verify_audit_backup,
)
from aico.app.runtime_owner import (
    RuntimeOwnerLock,
    RuntimeOwnershipError,
    runtime_owner_lock_path,
)
from aico.core.audit_ledger import (
    AuditIntegrityError,
    AuditLedgerSummary,
    verify_audit_ledger,
)
from aico.core.audit_recovery import (
    copy_raw_audit_ledger_snapshot,
    replace_audit_ledger_snapshot,
)
from aico.core.sqlite_state import STATE_SCHEMA_VERSION

AUDIT_QUARANTINE_MANIFEST_MEMBER = "quarantine-manifest.json"
_COPY_CHUNK_BYTES = 1024 * 1024


class AuditRestoreError(RuntimeError):
    """An audit drill, preservation, or live restore could not complete safely."""


class AuditQuarantineFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=128)
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class AuditQuarantineManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    created_at: AwareDatetime
    kind: Literal["unverified_quarantine"] = "unverified_quarantine"
    files: tuple[AuditQuarantineFile, ...] = Field(min_length=1, max_length=2)


class AuditPreservationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["verified_safety", "unverified_quarantine"]
    artifact_name: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class AuditRestoreSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["restore"] = "restore"
    event_count: int = Field(ge=0)
    ledger_bytes: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    backup_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    preservation: AuditPreservationSummary | None = None


class AuditDrillSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["drill"] = "drill"
    artifact_name: str
    event_count: int = Field(ge=0)
    ledger_bytes: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    backup_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    completed_at: AwareDatetime
    report_name: str | None = None


def drill_audit_backup(
    backup_path: Path,
    *,
    expected_sha256: str,
    workspace: Path | None = None,
    report_path: Path | None = None,
    clock: Callable[[], datetime] | None = None,
) -> AuditDrillSummary:
    backup = _absolute_path(backup_path)
    drill_workspace = _validated_workspace(workspace)
    report = _validated_new_output(report_path, forbidden={backup})
    now = clock or (lambda: datetime.now(UTC))
    try:
        with tempfile.TemporaryDirectory(prefix="aico-audit-drill-", dir=drill_workspace) as raw:
            directory = Path(raw)
            directory.chmod(0o700)
            target = directory / AUDIT_LEDGER_MEMBER
            materialized = materialize_audit_backup(
                backup,
                target,
                expected_sha256=expected_sha256,
            )
            verified = verify_audit_ledger(target)
            _require_materialized_parity(
                materialized.event_count,
                materialized.head_sha256,
                verified,
            )
            completed_at = now()
            if completed_at.tzinfo is None:
                raise AuditRestoreError("drill clock must be timezone-aware")
            summary = AuditDrillSummary(
                artifact_name=backup.name,
                event_count=verified.event_count,
                ledger_bytes=verified.byte_size,
                head_sha256=verified.head_sha256,
                backup_sha256=materialized.sha256,
                completed_at=completed_at,
                report_name=report.name if report is not None else None,
            )
    except AuditRestoreError:
        raise
    except (AuditBackupError, AuditIntegrityError) as exc:
        raise AuditRestoreError(str(exc)) from None
    except Exception:
        raise AuditRestoreError("disposable audit restore drill failed") from None
    if report is not None:
        _write_new_private_file(report, summary.model_dump_json() + "\n")
    return summary


def restore_audit_backup(
    target_path: Path,
    backup_path: Path,
    *,
    expected_sha256: str,
    state_db_path: Path,
    preservation_path: Path,
    base_dir: Path,
    confirmed: bool,
    clock: Callable[[], datetime] | None = None,
) -> AuditRestoreSummary:
    target = _absolute_path(target_path)
    backup = _absolute_path(backup_path)
    state_db = _absolute_path(state_db_path)
    preservation = _absolute_path(preservation_path)
    if not confirmed:
        raise AuditRestoreError("explicit restore confirmation is required")
    _validate_restore_paths(target, backup, state_db, preservation)
    verified_backup = _verify_expected_backup(backup, expected_sha256)
    lock = RuntimeOwnerLock(
        runtime_owner_lock_path(state_db, base_dir=base_dir),
        resource_path=state_db,
    )
    try:
        lock.acquire()
    except RuntimeOwnershipError:
        raise AuditRestoreError("runtime owner is active; audit restore refused") from None
    try:
        preserved = _preserve_live_audit(target, preservation, clock=clock)
        with tempfile.TemporaryDirectory(prefix="aico-audit-restore-", dir=target.parent) as raw:
            source = Path(raw) / AUDIT_LEDGER_MEMBER
            materialize_audit_backup(
                backup,
                source,
                expected_sha256=verified_backup.sha256,
            )
            restored = replace_audit_ledger_snapshot(target, source)
        return AuditRestoreSummary(
            event_count=restored.event_count,
            ledger_bytes=restored.byte_size,
            head_sha256=restored.head_sha256,
            backup_sha256=verified_backup.sha256,
            preservation=preserved,
        )
    except AuditRestoreError:
        raise
    except (AuditBackupError, AuditIntegrityError) as exc:
        raise AuditRestoreError(str(exc)) from None
    except Exception:
        raise AuditRestoreError(
            "audit restore failed; verify the live ledger before retrying"
        ) from None
    finally:
        lock.release()


def _preserve_live_audit(
    target: Path,
    output: Path,
    *,
    clock: Callable[[], datetime] | None,
) -> AuditPreservationSummary | None:
    if not target.exists() and not _checkpoint_path(target).exists():
        return None
    try:
        live = verify_audit_ledger(target)
    except AuditIntegrityError:
        live = None
    if live is not None and live.sealed:
        backup = create_audit_backup(target, output, clock=clock)
        return AuditPreservationSummary(
            kind="verified_safety",
            artifact_name=output.name,
            sha256=backup.sha256,
        )
    return _create_quarantine(target, output, clock=clock)


def _create_quarantine(
    target: Path,
    output: Path,
    *,
    clock: Callable[[], datetime] | None,
) -> AuditPreservationSummary:
    created_at = (clock or (lambda: datetime.now(UTC)))()
    if created_at.tzinfo is None:
        raise AuditRestoreError("restore clock must be timezone-aware")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_file(output)
    published = False
    try:
        with tempfile.TemporaryDirectory(prefix="aico-audit-quarantine-", dir=output.parent) as raw:
            directory = Path(raw)
            directory.chmod(0o700)
            ledger = directory / AUDIT_LEDGER_MEMBER
            copied = copy_raw_audit_ledger_snapshot(target, ledger)
            files = _quarantine_files(ledger, copied.ledger_present, copied.checkpoint_present)
            manifest = AuditQuarantineManifest(created_at=created_at, files=files)
            _write_quarantine_archive(temporary, ledger, manifest)
            _verify_quarantine_archive(temporary, manifest)
        _sync_file(temporary)
        _publish_new_file(temporary, output)
        published = True
        _sync_directory(output.parent)
        return AuditPreservationSummary(
            kind="unverified_quarantine",
            artifact_name=output.name,
            sha256=_sha256(output),
        )
    except (AuditRestoreError, AuditIntegrityError):
        if published:
            _discard_published_file(temporary, output)
        raise
    except Exception:
        if published:
            _discard_published_file(temporary, output)
        raise AuditRestoreError("corrupt audit quarantine failed") from None
    finally:
        temporary.unlink(missing_ok=True)


def _quarantine_files(
    ledger: Path,
    ledger_present: bool,
    checkpoint_present: bool,
) -> tuple[AuditQuarantineFile, ...]:
    candidates = (
        (AUDIT_LEDGER_MEMBER, ledger, ledger_present),
        (AUDIT_CHECKPOINT_MEMBER, _checkpoint_path(ledger), checkpoint_present),
    )
    return tuple(
        AuditQuarantineFile(name=name, bytes=path.stat().st_size, sha256=_sha256(path))
        for name, path, present in candidates
        if present
    )


def _write_quarantine_archive(
    output: Path,
    ledger: Path,
    manifest: AuditQuarantineManifest,
) -> None:
    payload = manifest.model_dump_json().encode("utf-8") + b"\n"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(_member_info(AUDIT_QUARANTINE_MANIFEST_MEMBER), payload)
        for file in manifest.files:
            source = ledger if file.name == AUDIT_LEDGER_MEMBER else _checkpoint_path(ledger)
            with source.open("rb") as input_file, archive.open(_member_info(file.name), "w") as out:
                shutil.copyfileobj(input_file, out, length=_COPY_CHUNK_BYTES)
    output.chmod(0o600)


def _verify_quarantine_archive(path: Path, manifest: AuditQuarantineManifest) -> None:
    expected = {AUDIT_QUARANTINE_MANIFEST_MEMBER, *(file.name for file in manifest.files)}
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(expected) or set(names) != expected:
                raise AuditRestoreError("audit quarantine members are invalid")
            for file in manifest.files:
                copied, digest = _archive_member_digest(archive, file.name)
                if copied != file.bytes or digest != file.sha256:
                    raise AuditRestoreError("audit quarantine member hash mismatch")
    except zipfile.BadZipFile:
        raise AuditRestoreError("audit quarantine archive is invalid") from None


def _validate_restore_paths(target: Path, backup: Path, state_db: Path, output: Path) -> None:
    if len({target, backup, state_db, output, _checkpoint_path(target)}) != 5:
        raise AuditRestoreError("audit restore inputs and outputs must differ")
    _validate_state_database(state_db)
    if output.exists() or output.is_symlink():
        raise AuditRestoreError("preservation output already exists")
    if not target.parent.is_dir():
        raise AuditRestoreError("audit restore target directory is missing")


def _verify_expected_backup(backup: Path, expected_sha256: str) -> AuditBackupSummary:
    try:
        return verify_audit_backup(backup, expected_sha256=expected_sha256)
    except AuditBackupError as exc:
        raise AuditRestoreError(str(exc)) from None


def _validate_owned_regular_file(path: Path, *, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError:
        raise AuditRestoreError(f"{label} is missing") from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise AuditRestoreError(f"{label} must be a regular non-symlink file")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise AuditRestoreError(f"{label} must be owned by the runtime user")


def _validate_state_database(path: Path) -> None:
    _validate_owned_regular_file(path, label="state database")
    try:
        with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT value FROM aico_schema WHERE key = 'schema_version'"
            ).fetchone()
            healthy = connection.execute("PRAGMA quick_check").fetchall() == [("ok",)]
        if row is None or int(row[0]) != STATE_SCHEMA_VERSION or not healthy:
            raise AuditRestoreError("state database is not a healthy supported AICO database")
    except AuditRestoreError:
        raise
    except (sqlite3.Error, TypeError, ValueError):
        raise AuditRestoreError("state database identity verification failed") from None


def _require_materialized_parity(
    event_count: int,
    head_sha256: str,
    restored: AuditLedgerSummary,
) -> None:
    if (
        restored.event_count != event_count
        or restored.head_sha256 != head_sha256
        or not restored.sealed
        or restored.checkpoint_lag
    ):
        raise AuditRestoreError("drill materialized ledger does not match backup")


def _validated_workspace(workspace: Path | None) -> Path | None:
    if workspace is None:
        return None
    resolved = _absolute_path(workspace)
    if not resolved.is_dir():
        raise AuditRestoreError("drill workspace is missing or not a directory")
    return resolved


def _validated_new_output(path: Path | None, *, forbidden: set[Path]) -> Path | None:
    if path is None:
        return None
    output = _absolute_path(path)
    if output in forbidden:
        raise AuditRestoreError("drill report and backup must differ")
    if output.exists() or output.is_symlink():
        raise AuditRestoreError("drill report already exists")
    return output


def _write_new_private_file(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_file(path)
    published = False
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise AuditRestoreError("drill report already exists") from None
        published = True
        _sync_directory(path.parent)
    except AuditRestoreError:
        if published:
            _discard_published_file(temporary, path)
        raise
    except Exception:
        if published:
            _discard_published_file(temporary, path)
        raise AuditRestoreError("drill report publication failed") from None
    finally:
        temporary.unlink(missing_ok=True)


def _archive_member_digest(archive: zipfile.ZipFile, name: str) -> tuple[int, str]:
    digest = hashlib.sha256()
    copied = 0
    with archive.open(name) as source:
        while chunk := source.read(_COPY_CHUNK_BYTES):
            digest.update(chunk)
            copied += len(chunk)
    return copied, digest.hexdigest()


def _member_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info


def _temporary_file(target: Path) -> Path:
    descriptor, raw = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(descriptor)
    return Path(raw)


def _publish_new_file(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
    except FileExistsError:
        raise AuditRestoreError("preservation output already exists") from None


def _discard_published_file(source: Path, destination: Path) -> None:
    try:
        if destination.exists() and os.path.samefile(source, destination):
            destination.unlink()
            _sync_directory(destination.parent)
    except OSError:
        pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_COPY_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


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
