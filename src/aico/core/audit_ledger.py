"""Tamper-evident local ledger mechanics for durable audit JSONL."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from aico.core.models import AuditEvent

AUDIT_CHAIN_SCHEMA_VERSION = 1
_GENESIS_SHA256 = "0" * 64
_CHAIN_DOMAIN = b"aico-audit-chain-v1\0"
_LEGACY_DOMAIN = b"aico-audit-legacy-v1\0"


class AuditIntegrityError(ValueError):
    """The durable audit ledger cannot be trusted or safely advanced."""


class _AuditLink(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    previous_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    entry_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class _AuditCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    event_count: int = Field(ge=0)
    byte_size: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class AuditLedgerSummary:
    event_count: int
    byte_size: int
    head_sha256: str
    sealed: bool
    checkpoint_lag: bool = False


@dataclass(frozen=True)
class _LedgerState:
    events: tuple[AuditEvent, ...]
    events_by_id: dict[str, AuditEvent]
    event_count: int
    byte_size: int
    head_sha256: str
    sealed: bool
    checkpoint_lag: bool

    def summary(self) -> AuditLedgerSummary:
        return AuditLedgerSummary(
            event_count=self.event_count,
            byte_size=self.byte_size,
            head_sha256=self.head_sha256,
            sealed=self.sealed,
            checkpoint_lag=self.checkpoint_lag,
        )


class AuditLedger:
    """Serialize writers and keep an append-only JSONL hash chain checkpointed."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._thread_lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._locked():
            state = _load_state(path, require_sealed=True)
            if not state.sealed:
                _write_checkpoint(path, _checkpoint(state))
                state = _state_with_seal(state)
            elif state.checkpoint_lag:
                _write_checkpoint(path, _checkpoint(state))
                state = _state_without_lag(state)
        self._state = state
        self._file_identity = _file_identity(path)

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        return self._state.events

    @property
    def summary(self) -> AuditLedgerSummary:
        return self._state.summary()

    def append(self, event: AuditEvent) -> None:
        with self._thread_lock, self._locked():
            self._refresh_if_changed()
            existing = self._state.events_by_id.get(event.event_id)
            if existing is not None:
                if existing != event:
                    raise ValueError(f"audit event id collision: {event.event_id}")
                return
            encoded, head = _encode_chained_event(event, self._state.head_sha256)
            _append_bytes(self._path, encoded)
            advanced = _advance_state(self._state, event, encoded, head)
            _write_checkpoint(self._path, _checkpoint(advanced))
            self._state = advanced
            self._file_identity = _file_identity(self._path)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        with _ledger_lock(self._path):
            yield

    def _refresh_if_changed(self) -> None:
        checkpoint = _read_checkpoint(self._path)
        current_size = self._path.stat().st_size if self._path.exists() else 0
        if (
            current_size == self._state.byte_size
            and checkpoint == _checkpoint(self._state)
            and _file_identity(self._path) == self._file_identity
        ):
            return
        refreshed = _load_state(self._path, require_sealed=True)
        if refreshed.checkpoint_lag:
            _write_checkpoint(self._path, _checkpoint(refreshed))
            refreshed = _state_without_lag(refreshed)
        self._state = refreshed
        self._file_identity = _file_identity(self._path)


def read_audit_ledger(path: Path) -> tuple[AuditEvent, ...]:
    if not path.exists() and not _checkpoint_path(path).exists():
        return ()
    with _ledger_lock(path):
        return _load_state(path, require_sealed=True).events


def verify_audit_ledger(path: Path) -> AuditLedgerSummary:
    if not path.exists() and not _checkpoint_path(path).exists():
        return AuditLedgerSummary(0, 0, _GENESIS_SHA256, sealed=False)
    with _ledger_lock(path):
        return _load_state(path, require_sealed=True).summary()


def seal_legacy_audit_ledger(path: Path) -> AuditLedgerSummary:
    if not path.exists() and not _checkpoint_path(path).exists():
        raise AuditIntegrityError("audit ledger does not exist")
    path.parent.mkdir(parents=True, exist_ok=True)
    with _ledger_lock(path):
        _secure_ledger_file(path)
        state = _load_state(path, require_sealed=False)
        _write_checkpoint(path, _checkpoint(state))
        return _state_with_seal(state).summary()


def copy_audit_ledger_snapshot(path: Path, output_path: Path) -> AuditLedgerSummary:
    """Copy one verified ledger/checkpoint recovery point while holding the writer lock."""
    checkpoint_output = _checkpoint_path(output_path)
    if not path.exists() and not _checkpoint_path(path).exists():
        raise AuditIntegrityError("audit ledger does not exist")
    if _same_path(output_path, path) or _same_path(checkpoint_output, _checkpoint_path(path)):
        raise AuditIntegrityError("audit snapshot output must differ from the live ledger")
    if (
        output_path.exists()
        or output_path.is_symlink()
        or checkpoint_output.exists()
        or checkpoint_output.is_symlink()
    ):
        raise AuditIntegrityError("audit snapshot output already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        with _ledger_lock(path):
            state = _load_state(path, require_sealed=True)
            if state.checkpoint_lag:
                _write_checkpoint(path, _checkpoint(state))
                state = _state_without_lag(state)
            _copy_new_private_file(path if path.exists() else None, output_path)
            created.append(output_path)
            _copy_new_private_file(_checkpoint_path(path), checkpoint_output)
            created.append(checkpoint_output)
        _sync_directory(output_path.parent)
        copied = _load_state(output_path, require_sealed=True)
        if copied.summary() != state.summary():
            raise AuditIntegrityError("audit snapshot does not match the live recovery point")
        return copied.summary()
    except BaseException:
        for created_path in created:
            created_path.unlink(missing_ok=True)
        raise


def _load_state(path: Path, *, require_sealed: bool) -> _LedgerState:
    _validate_ledger_file(path)
    checkpoint = _read_checkpoint(path)
    raw = path.read_bytes() if path.exists() else b""
    events, head, snapshots, chained = _parse_ledger(raw)
    events_by_id = _event_index(events)
    if checkpoint is None:
        if raw and require_sealed:
            raise AuditIntegrityError("audit ledger is unsealed; run aico-audit seal")
        return _LedgerState(
            events=events,
            events_by_id=events_by_id,
            event_count=len(events),
            byte_size=len(raw),
            head_sha256=head,
            sealed=False,
            checkpoint_lag=False,
        )
    if checkpoint.byte_size > len(raw):
        raise AuditIntegrityError("audit ledger was truncated after its sealed checkpoint")
    prefix = snapshots.get(checkpoint.byte_size)
    if prefix is None or prefix != (checkpoint.event_count, checkpoint.head_sha256):
        raise AuditIntegrityError("audit ledger checkpoint does not match the event stream")
    if chained is False and raw[checkpoint.byte_size :]:
        raise AuditIntegrityError("audit ledger contains unchained events after sealing")
    return _LedgerState(
        events=events,
        events_by_id=events_by_id,
        event_count=len(events),
        byte_size=len(raw),
        head_sha256=head,
        sealed=True,
        checkpoint_lag=checkpoint.byte_size < len(raw),
    )


def _parse_ledger(
    raw: bytes,
) -> tuple[tuple[AuditEvent, ...], str, dict[int, tuple[int, str]], bool]:
    if raw and not raw.endswith(b"\n"):
        raise AuditIntegrityError("audit ledger ends with an incomplete record")
    events: list[AuditEvent] = []
    head = _GENESIS_SHA256
    byte_offset = 0
    snapshots = {0: (0, head)}
    chained_seen = False
    for physical in raw.splitlines(keepends=True):
        line = physical[:-1]
        byte_offset += len(physical)
        if not line.strip():
            if chained_seen:
                raise AuditIntegrityError("audit ledger contains an empty chained record")
            head = _legacy_hash(head, line)
            snapshots[byte_offset] = (len(events), head)
            continue
        event, head, is_chained = _parse_record(line, head, chained_seen)
        chained_seen = chained_seen or is_chained
        events.append(event)
        snapshots[byte_offset] = (len(events), head)
    return tuple(events), head, snapshots, chained_seen


def _parse_record(
    raw_line: bytes,
    previous: str,
    chained_seen: bool,
) -> tuple[AuditEvent, str, bool]:
    try:
        payload = json.loads(raw_line)
        if not isinstance(payload, dict):
            raise TypeError
        raw_link = payload.pop("_audit", None)
        event = AuditEvent.model_validate(payload)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError, ValidationError):
        raise AuditIntegrityError("audit ledger contains an invalid event record") from None
    if raw_link is None:
        if chained_seen:
            raise AuditIntegrityError("audit ledger contains an unchained event after sealing")
        return event, _legacy_hash(previous, raw_line), False
    try:
        link = _AuditLink.model_validate(raw_link)
    except ValidationError:
        raise AuditIntegrityError("audit ledger contains an invalid integrity link") from None
    expected_head = _entry_hash(previous, event)
    if link.previous_sha256 != previous or link.entry_sha256 != expected_head:
        raise AuditIntegrityError("audit ledger hash chain verification failed")
    expected_line = _encoded_payload(event, link)
    if raw_line != expected_line:
        raise AuditIntegrityError("audit ledger chained record is not canonical")
    return event, expected_head, True


def _event_index(events: tuple[AuditEvent, ...]) -> dict[str, AuditEvent]:
    index: dict[str, AuditEvent] = {}
    for event in events:
        existing = index.get(event.event_id)
        if existing is not None:
            raise AuditIntegrityError("duplicate audit event id in durable history")
        index[event.event_id] = event
    return index


def _encode_chained_event(event: AuditEvent, previous: str) -> tuple[bytes, str]:
    head = _entry_hash(previous, event)
    link = _AuditLink(previous_sha256=previous, entry_sha256=head)
    return _encoded_payload(event, link) + b"\n", head


def _encoded_payload(event: AuditEvent, link: _AuditLink) -> bytes:
    payload = event.model_dump(mode="json")
    payload["_audit"] = link.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _entry_hash(previous: str, event: AuditEvent) -> str:
    canonical = json.dumps(
        event.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(_CHAIN_DOMAIN + bytes.fromhex(previous) + canonical).hexdigest()


def _legacy_hash(previous: str, raw_line: bytes) -> str:
    return hashlib.sha256(_LEGACY_DOMAIN + bytes.fromhex(previous) + raw_line).hexdigest()


def _advance_state(
    state: _LedgerState,
    event: AuditEvent,
    encoded: bytes,
    head: str,
) -> _LedgerState:
    index = dict(state.events_by_id)
    index[event.event_id] = event
    return _LedgerState(
        events=(*state.events, event),
        events_by_id=index,
        event_count=state.event_count + 1,
        byte_size=state.byte_size + len(encoded),
        head_sha256=head,
        sealed=True,
        checkpoint_lag=False,
    )


def _state_with_seal(state: _LedgerState) -> _LedgerState:
    return _LedgerState(**{**state.__dict__, "sealed": True, "checkpoint_lag": False})


def _state_without_lag(state: _LedgerState) -> _LedgerState:
    return _LedgerState(**{**state.__dict__, "checkpoint_lag": False})


def _checkpoint(state: _LedgerState) -> _AuditCheckpoint:
    return _AuditCheckpoint(
        event_count=state.event_count,
        byte_size=state.byte_size,
        head_sha256=state.head_sha256,
    )


def _read_checkpoint(path: Path) -> _AuditCheckpoint | None:
    checkpoint_path = _checkpoint_path(path)
    if not checkpoint_path.exists():
        return None
    _validate_owner_file(checkpoint_path)
    try:
        return _AuditCheckpoint.model_validate_json(checkpoint_path.read_bytes())
    except (OSError, ValidationError):
        raise AuditIntegrityError("audit ledger checkpoint is invalid") from None


def _write_checkpoint(path: Path, checkpoint: _AuditCheckpoint) -> None:
    target = _checkpoint_path(path)
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
    _secure_ledger_file(path)
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
    lock_path = _lock_path(path)
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


def _validate_ledger_file(path: Path) -> None:
    if not path.exists():
        if path.is_symlink():
            raise AuditIntegrityError("audit ledger must not be a symlink")
        return
    _validate_owner_file(path)


def _secure_ledger_file(path: Path) -> None:
    if not path.exists():
        _reject_symlink(path)
        return
    _validate_owner_file(path, require_private=False)
    path.chmod(0o600)


def _validate_owner_file(path: Path, *, require_private: bool = True) -> None:
    try:
        metadata = path.lstat()
    except OSError:
        raise AuditIntegrityError("audit ledger file metadata is unavailable") from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise AuditIntegrityError("audit ledger must be a regular non-symlink file")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise AuditIntegrityError("audit ledger must be owned by the runtime user")
    if require_private and stat.S_IMODE(metadata.st_mode) & 0o077:
        raise AuditIntegrityError("audit ledger files must be owner-only")


def _validate_open_file(descriptor: int) -> None:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise AuditIntegrityError("audit ledger lock must be a regular file")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise AuditIntegrityError("audit ledger lock must be owned by the runtime user")


def _reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise AuditIntegrityError("audit ledger must not use symlink files")


def _checkpoint_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.checkpoint.json")


def _lock_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.lock")


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
