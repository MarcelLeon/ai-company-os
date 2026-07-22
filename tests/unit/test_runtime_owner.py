import json
import subprocess
import sys
from pathlib import Path

import pytest

from aico.app.runtime_owner import (
    RuntimeOwnerLock,
    RuntimeOwnershipError,
    runtime_owner_lock_path,
    runtime_owner_status,
)


def test_runtime_owner_lock_rejects_competitor_and_releases_normally(tmp_path: Path) -> None:
    state_path = tmp_path / "state.db"
    lock_path = runtime_owner_lock_path(state_path, base_dir=tmp_path)
    first = RuntimeOwnerLock(lock_path, resource_path=state_path)
    second = RuntimeOwnerLock(lock_path, resource_path=state_path)

    first.acquire()

    status = runtime_owner_status(lock_path)
    assert status.active is True
    assert status.owner_pid is not None
    with pytest.raises(RuntimeOwnershipError, match="runtime owner lock already acquired"):
        first.acquire()
    with pytest.raises(RuntimeOwnershipError, match="runtime owner already active"):
        second.acquire()

    first.release()
    assert runtime_owner_status(lock_path).active is False

    second.acquire()
    second.release()
    metadata = json.loads(lock_path.read_text(encoding="utf-8"))
    assert set(metadata) == {
        "owner_pid",
        "resource_path",
        "schema_version",
        "started_at",
        "state",
        "stopped_at",
    }
    assert metadata["state"] == "stopped"


def test_runtime_owner_lock_path_is_canonical_and_state_scoped(tmp_path: Path) -> None:
    first_state = tmp_path / "a" / "state.db"
    equivalent_state = tmp_path / "a" / ".." / "a" / "state.db"
    second_state = tmp_path / "b" / "state.db"

    assert runtime_owner_lock_path(first_state, base_dir=tmp_path) == runtime_owner_lock_path(
        equivalent_state,
        base_dir=tmp_path,
    )
    assert runtime_owner_lock_path(first_state, base_dir=tmp_path) != runtime_owner_lock_path(
        second_state,
        base_dir=tmp_path,
    )
    assert (
        runtime_owner_lock_path(None, base_dir=tmp_path)
        == (tmp_path / ".aico/runtime-owner.lock").resolve()
    )


def test_runtime_owner_kernel_lock_is_released_after_process_kill(tmp_path: Path) -> None:
    lock_path = tmp_path / "runtime-owner.lock"
    child_code = """
import sys
import time
from pathlib import Path
from aico.app.runtime_owner import RuntimeOwnerLock

lock = RuntimeOwnerLock(Path(sys.argv[1]), resource_path=Path(sys.argv[1]))
lock.acquire()
print("locked", flush=True)
time.sleep(60)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", child_code, str(lock_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "locked"
        assert runtime_owner_status(lock_path).active is True
        process.kill()
        assert process.wait(timeout=5) != 0

        replacement = RuntimeOwnerLock(lock_path, resource_path=lock_path)
        replacement.acquire()
        replacement.release()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
