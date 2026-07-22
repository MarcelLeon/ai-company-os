"""Single-process ownership for one local AICO runtime state."""

from __future__ import annotations

import fcntl
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO


class RuntimeOwnershipError(RuntimeError):
    """Raised when another process already owns the runtime resource."""


@dataclass(frozen=True)
class RuntimeOwnerStatus:
    active: bool
    owner_pid: int | None
    detail: str


class RuntimeOwnerLock:
    """Hold one non-blocking kernel lock for the complete runtime lifetime."""

    def __init__(self, path: Path, *, resource_path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.resource_path = resource_path.expanduser().resolve()
        self._handle: TextIO | None = None

    def acquire(self) -> None:
        if self._handle is not None:
            raise RuntimeOwnershipError(f"runtime owner lock already acquired: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            metadata = _read_metadata(handle)
            handle.close()
            owner_pid = _owner_pid(metadata)
            detail = f" lock={self.path}"
            if owner_pid is not None:
                detail += f" owner_pid={owner_pid}"
            raise RuntimeOwnershipError(f"runtime owner already active:{detail}") from exc
        except Exception:
            handle.close()
            raise
        try:
            _write_metadata(
                handle,
                {
                    "schema_version": 1,
                    "state": "running",
                    "owner_pid": os.getpid(),
                    "started_at": _now_iso(),
                    "resource_path": str(self.resource_path),
                },
            )
        except Exception:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
            raise
        self._handle = handle

    def release(self) -> None:
        handle = self._handle
        if handle is None:
            return
        metadata = _read_metadata(handle)
        metadata.update({"state": "stopped", "stopped_at": _now_iso()})
        try:
            _write_metadata(handle, metadata)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
            self._handle = None


def runtime_owner_lock_path(state_db_path: Path | None, *, base_dir: Path) -> Path:
    base = base_dir.expanduser().resolve()
    if state_db_path is None:
        return (base / ".aico/runtime-owner.lock").resolve()
    state = state_db_path.expanduser()
    canonical_state = (base / state).resolve() if not state.is_absolute() else state.resolve()
    return Path(f"{canonical_state}.owner.lock")


def runtime_owner_status(path: Path) -> RuntimeOwnerStatus:
    canonical = path.expanduser().resolve()
    if not canonical.exists():
        return RuntimeOwnerStatus(active=False, owner_pid=None, detail="missing")
    with canonical.open("a+", encoding="utf-8") as handle:
        metadata = _read_metadata(handle)
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            owner_pid = _owner_pid(metadata)
            detail = "active" if owner_pid is None else f"active pid={owner_pid}"
            return RuntimeOwnerStatus(active=True, owner_pid=owner_pid, detail=detail)
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    owner_pid = _owner_pid(metadata)
    detail = "free" if owner_pid is None else f"free last_owner_pid={owner_pid}"
    return RuntimeOwnerStatus(active=False, owner_pid=owner_pid, detail=detail)


def _read_metadata(handle: TextIO) -> dict[str, object]:
    handle.seek(0)
    raw = handle.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_metadata(handle: TextIO, metadata: dict[str, object]) -> None:
    handle.seek(0)
    handle.truncate()
    json.dump(metadata, handle, ensure_ascii=False, sort_keys=True)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())


def _owner_pid(metadata: dict[str, object]) -> int | None:
    value = metadata.get("owner_pid")
    return value if isinstance(value, int) and value > 0 else None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
