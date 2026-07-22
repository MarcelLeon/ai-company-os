"""Tamper-evident, process-safe ledger mechanics for durable memory JSONL."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import stat
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

MEMORY_CHAIN_SCHEMA_VERSION = 1
_GENESIS_SHA256 = "0" * 64
_CHAIN_DOMAIN = b"aico-memory-chain-v1\0"
_LEGACY_DOMAIN = b"aico-memory-legacy-v1\0"


class MemoryIntegrityError(ValueError):
    """The durable memory ledger cannot be trusted or safely advanced."""


class _MemoryLink(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    previous_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    entry_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class _MemoryCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    record_count: int = Field(ge=0)
    byte_size: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class MemoryLedgerRecord:
    record_type: Literal["atom", "edge"]
    payload: dict[str, Any]

    def canonical_payload(self) -> dict[str, Any]:
        return {"payload": self.payload, "record_type": self.record_type}


@dataclass(frozen=True)
class MemoryLedgerSummary:
    record_count: int
    byte_size: int
    head_sha256: str
    sealed: bool
    checkpoint_lag: bool = False


@dataclass(frozen=True)
class _LedgerState:
    records: tuple[MemoryLedgerRecord, ...]
    byte_size: int
    head_sha256: str
    sealed: bool
    checkpoint_lag: bool

    def summary(self) -> MemoryLedgerSummary:
        return MemoryLedgerSummary(
            record_count=len(self.records),
            byte_size=self.byte_size,
            head_sha256=self.head_sha256,
            sealed=self.sealed,
            checkpoint_lag=self.checkpoint_lag,
        )


class MemoryLedger:
    """Serialize writers and maintain a checkpointed JSONL hash chain."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._thread_lock = Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        with _ledger_lock(path):
            state = _load_state(path, require_sealed=True)
            if not state.sealed or state.checkpoint_lag:
                _write_checkpoint(path, _checkpoint(state))
                state = _sealed_state(state)
        self._state = state
        self._file_identity = _file_identity(path)

    @property
    def records(self) -> tuple[MemoryLedgerRecord, ...]:
        return self._state.records

    @property
    def summary(self) -> MemoryLedgerSummary:
        return self._state.summary()

    def append(self, record_type: Literal["atom", "edge"], payload: Mapping[str, Any]) -> None:
        record = MemoryLedgerRecord(record_type=record_type, payload=dict(payload))
        with self._thread_lock, _ledger_lock(self._path):
            self._refresh_if_changed()
            encoded, head = _encode_record(record, self._state.head_sha256)
            _append_bytes(self._path, encoded)
            advanced = _LedgerState(
                records=(*self._state.records, record),
                byte_size=self._state.byte_size + len(encoded),
                head_sha256=head,
                sealed=True,
                checkpoint_lag=False,
            )
            _write_checkpoint(self._path, _checkpoint(advanced))
            self._state = advanced
            self._file_identity = _file_identity(self._path)

    def refresh(self) -> tuple[MemoryLedgerRecord, ...]:
        with self._thread_lock, _ledger_lock(self._path):
            self._refresh_if_changed()
            return self._state.records

    def _refresh_if_changed(self) -> None:
        checkpoint = _read_checkpoint(self._path)
        size = self._path.stat().st_size if self._path.exists() else 0
        if (
            size == self._state.byte_size
            and checkpoint == _checkpoint(self._state)
            and _file_identity(self._path) == self._file_identity
        ):
            return
        refreshed = _load_state(self._path, require_sealed=True)
        if refreshed.checkpoint_lag:
            _write_checkpoint(self._path, _checkpoint(refreshed))
            refreshed = _sealed_state(refreshed)
        self._state = refreshed
        self._file_identity = _file_identity(self._path)


def verify_memory_ledger(path: Path) -> MemoryLedgerSummary:
    if not path.exists() and not memory_checkpoint_path(path).exists():
        return MemoryLedgerSummary(0, 0, _GENESIS_SHA256, sealed=False)
    with _ledger_lock(path):
        return _load_state(path, require_sealed=True).summary()


def read_memory_ledger(path: Path) -> tuple[MemoryLedgerRecord, ...]:
    if not path.exists() and not memory_checkpoint_path(path).exists():
        return ()
    with _ledger_lock(path):
        return _load_state(path, require_sealed=True).records


def seal_legacy_memory_ledger(path: Path) -> MemoryLedgerSummary:
    if not path.exists() and not memory_checkpoint_path(path).exists():
        raise MemoryIntegrityError("memory ledger does not exist")
    path.parent.mkdir(parents=True, exist_ok=True)
    with _ledger_lock(path):
        _secure_file(path)
        state = _load_state(path, require_sealed=False)
        _write_checkpoint(path, _checkpoint(state))
        return _sealed_state(state).summary()


def copy_memory_ledger_snapshot(path: Path, output_path: Path) -> MemoryLedgerSummary:
    checkpoint = memory_checkpoint_path(path)
    output_checkpoint = memory_checkpoint_path(output_path)
    if not path.exists() and not checkpoint.exists():
        raise MemoryIntegrityError("memory ledger does not exist")
    if _same_path(path, output_path) or _same_path(checkpoint, output_checkpoint):
        raise MemoryIntegrityError("memory snapshot output must differ from the live ledger")
    if any(item.exists() or item.is_symlink() for item in (output_path, output_checkpoint)):
        raise MemoryIntegrityError("memory snapshot output already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        with _ledger_lock(path):
            state = _load_state(path, require_sealed=True)
            if state.checkpoint_lag:
                _write_checkpoint(path, _checkpoint(state))
                state = _sealed_state(state)
            _copy_new_private_file(path if path.exists() else None, output_path)
            created.append(output_path)
            _copy_new_private_file(checkpoint, output_checkpoint)
            created.append(output_checkpoint)
        _sync_directory(output_path.parent)
        copied = _load_state(output_path, require_sealed=True)
        if copied.summary() != state.summary():
            raise MemoryIntegrityError("memory snapshot does not match the live recovery point")
        return copied.summary()
    except BaseException:
        for item in created:
            item.unlink(missing_ok=True)
        raise


def replace_memory_ledger_snapshot(path: Path, snapshot_path: Path) -> MemoryLedgerSummary:
    """Replace a ledger/checkpoint pair; interrupted publication remains fail-closed."""
    if _same_path(path, snapshot_path):
        raise MemoryIntegrityError("memory restore target and snapshot must differ")
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.parent / f".{path.name}.{uuid4().hex}.restore"
    staged_checkpoint = memory_checkpoint_path(staged)
    try:
        expected = copy_memory_ledger_snapshot(snapshot_path, staged)
        with _ledger_lock(path):
            _validate_replace_target(path)
            os.replace(staged, path)
            _sync_directory(path.parent)
            os.replace(staged_checkpoint, memory_checkpoint_path(path))
            _sync_directory(path.parent)
            restored = _load_state(path, require_sealed=True).summary()
        if restored != expected:
            raise MemoryIntegrityError("restored memory ledger does not match its snapshot")
        return restored
    finally:
        staged.unlink(missing_ok=True)
        staged_checkpoint.unlink(missing_ok=True)


def copy_raw_memory_ledger_snapshot(path: Path, output_path: Path) -> tuple[bool, bool]:
    checkpoint = memory_checkpoint_path(path)
    output_checkpoint = memory_checkpoint_path(output_path)
    if not path.exists() and not checkpoint.exists():
        raise MemoryIntegrityError("memory ledger does not exist")
    if any(item.exists() or item.is_symlink() for item in (output_path, output_checkpoint)):
        raise MemoryIntegrityError("memory snapshot output already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        with _ledger_lock(path):
            _validate_replace_target(path)
            if path.exists():
                _copy_new_private_file(path, output_path)
                created.append(output_path)
            if checkpoint.exists():
                _copy_new_private_file(checkpoint, output_checkpoint)
                created.append(output_checkpoint)
        _sync_directory(output_path.parent)
        return output_path.exists(), output_checkpoint.exists()
    except BaseException:
        for item in created:
            item.unlink(missing_ok=True)
        raise


def _load_state(path: Path, *, require_sealed: bool) -> _LedgerState:
    _validate_ledger_file(path)
    checkpoint = _read_checkpoint(path)
    raw = path.read_bytes() if path.exists() else b""
    records, head, snapshots, chained = _parse_ledger(raw)
    if checkpoint is None:
        if raw and require_sealed:
            raise MemoryIntegrityError("memory ledger is unsealed; run aico-memory seal")
        return _LedgerState(tuple(records), len(raw), head, False, False)
    if checkpoint.byte_size > len(raw):
        raise MemoryIntegrityError("memory ledger was truncated after its sealed checkpoint")
    prefix = snapshots.get(checkpoint.byte_size)
    if prefix != (checkpoint.record_count, checkpoint.head_sha256):
        raise MemoryIntegrityError("memory checkpoint does not match the record stream")
    if not chained and raw[checkpoint.byte_size :]:
        raise MemoryIntegrityError("memory ledger contains unchained records after sealing")
    return _LedgerState(
        tuple(records),
        len(raw),
        head,
        True,
        checkpoint.byte_size < len(raw),
    )


def _parse_ledger(
    raw: bytes,
) -> tuple[list[MemoryLedgerRecord], str, dict[int, tuple[int, str]], bool]:
    if raw and not raw.endswith(b"\n"):
        raise MemoryIntegrityError("memory ledger ends with an incomplete record")
    records: list[MemoryLedgerRecord] = []
    head = _GENESIS_SHA256
    offset = 0
    snapshots = {0: (0, head)}
    chained_seen = False
    for physical in raw.splitlines(keepends=True):
        line = physical[:-1]
        offset += len(physical)
        if not line.strip():
            if chained_seen:
                raise MemoryIntegrityError("memory ledger contains an empty chained record")
            head = _legacy_hash(head, line)
            snapshots[offset] = (len(records), head)
            continue
        record, head, chained = _parse_record(line, head, chained_seen)
        chained_seen = chained_seen or chained
        records.append(record)
        snapshots[offset] = (len(records), head)
    return records, head, snapshots, chained_seen


def _parse_record(
    raw_line: bytes,
    previous: str,
    chained_seen: bool,
) -> tuple[MemoryLedgerRecord, str, bool]:
    try:
        raw = json.loads(raw_line)
        if not isinstance(raw, dict):
            raise TypeError
        raw_link = raw.pop("_memory", None)
        record_type = raw.get("record_type")
        payload = raw.get("payload")
        if record_type not in {"atom", "edge"} or not isinstance(payload, dict):
            raise TypeError
        if set(raw) != {"payload", "record_type"}:
            raise TypeError
        record = MemoryLedgerRecord(record_type=record_type, payload=payload)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        raise MemoryIntegrityError("memory ledger contains an invalid record") from None
    if raw_link is None:
        if chained_seen:
            raise MemoryIntegrityError("memory ledger contains an unchained record after sealing")
        return record, _legacy_hash(previous, raw_line), False
    try:
        link = _MemoryLink.model_validate(raw_link)
    except ValidationError:
        raise MemoryIntegrityError("memory ledger contains an invalid integrity link") from None
    expected = _entry_hash(previous, record)
    if link.previous_sha256 != previous or link.entry_sha256 != expected:
        raise MemoryIntegrityError("memory ledger hash chain verification failed")
    if raw_line != _encoded_payload(record, link):
        raise MemoryIntegrityError("memory ledger chained record is not canonical")
    return record, expected, True


def _encode_record(record: MemoryLedgerRecord, previous: str) -> tuple[bytes, str]:
    head = _entry_hash(previous, record)
    link = _MemoryLink(previous_sha256=previous, entry_sha256=head)
    return _encoded_payload(record, link) + b"\n", head


def _encoded_payload(record: MemoryLedgerRecord, link: _MemoryLink) -> bytes:
    payload = record.canonical_payload()
    payload["_memory"] = link.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _entry_hash(previous: str, record: MemoryLedgerRecord) -> str:
    canonical = json.dumps(record.canonical_payload(), ensure_ascii=False, sort_keys=True).encode(
        "utf-8"
    )
    return hashlib.sha256(_CHAIN_DOMAIN + bytes.fromhex(previous) + canonical).hexdigest()


def _legacy_hash(previous: str, line: bytes) -> str:
    return hashlib.sha256(_LEGACY_DOMAIN + bytes.fromhex(previous) + line).hexdigest()


def _checkpoint(state: _LedgerState) -> _MemoryCheckpoint:
    return _MemoryCheckpoint(
        record_count=len(state.records),
        byte_size=state.byte_size,
        head_sha256=state.head_sha256,
    )


def _sealed_state(state: _LedgerState) -> _LedgerState:
    return _LedgerState(state.records, state.byte_size, state.head_sha256, True, False)


def _read_checkpoint(path: Path) -> _MemoryCheckpoint | None:
    checkpoint = memory_checkpoint_path(path)
    if not checkpoint.exists():
        return None
    _validate_owner_file(checkpoint)
    try:
        return _MemoryCheckpoint.model_validate_json(checkpoint.read_bytes())
    except (OSError, ValidationError):
        raise MemoryIntegrityError("memory ledger checkpoint is invalid") from None


def _write_checkpoint(path: Path, checkpoint: _MemoryCheckpoint) -> None:
    target = memory_checkpoint_path(path)
    _reject_symlink(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.{uuid4().hex}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(checkpoint.model_dump_json().encode("utf-8") + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        _sync_directory(target.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _append_bytes(path: Path, payload: bytes) -> None:
    _secure_file(path)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "ab", closefd=True) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _copy_new_private_file(source: Path | None, target: Path) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags, 0o600)
    with os.fdopen(descriptor, "wb", closefd=True) as output:
        if source is not None:
            with source.open("rb") as input_file:
                shutil.copyfileobj(input_file, output)
        output.flush()
        os.fsync(output.fileno())


@contextmanager
def _ledger_lock(path: Path) -> Iterator[None]:
    lock_path = path.with_name(f"{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink(lock_path)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        _validate_open_file(descriptor)
        os.fchmod(descriptor, 0o600)
    except BaseException:
        os.close(descriptor)
        raise
    with os.fdopen(descriptor, "r+b", closefd=True) as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def memory_checkpoint_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.checkpoint.json")


def _validate_ledger_file(path: Path) -> None:
    if not path.exists():
        _reject_symlink(path)
        return
    _validate_owner_file(path)


def _secure_file(path: Path) -> None:
    if not path.exists():
        _reject_symlink(path)
        return
    _validate_owner_file(path, require_private=False)
    path.chmod(0o600)


def _validate_replace_target(path: Path) -> None:
    for candidate in (path, memory_checkpoint_path(path)):
        if candidate.exists():
            _validate_owner_file(candidate, require_private=False)
        elif candidate.is_symlink():
            raise MemoryIntegrityError("memory ledger must not use symlink files")


def _validate_owner_file(path: Path, *, require_private: bool = True) -> None:
    try:
        metadata = path.lstat()
    except OSError:
        raise MemoryIntegrityError("memory ledger file metadata is unavailable") from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise MemoryIntegrityError("memory ledger must be a regular non-symlink file")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise MemoryIntegrityError("memory ledger must be owned by the runtime user")
    if require_private and stat.S_IMODE(metadata.st_mode) & 0o077:
        raise MemoryIntegrityError("memory ledger files must be owner-only")


def _validate_open_file(descriptor: int) -> None:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise MemoryIntegrityError("memory ledger lock must be a regular file")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise MemoryIntegrityError("memory ledger lock must be owned by the runtime user")


def _reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise MemoryIntegrityError("memory ledger must not use symlink files")


def _file_identity(path: Path) -> tuple[int, int, int] | None:
    if not path.exists():
        return None
    metadata = path.stat()
    return metadata.st_dev, metadata.st_ino, metadata.st_mtime_ns


def _same_path(left: Path, right: Path) -> bool:
    return os.path.abspath(left) == os.path.abspath(right)


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
