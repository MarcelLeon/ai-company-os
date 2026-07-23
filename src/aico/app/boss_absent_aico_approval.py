"""At-most-once isolated mutation executor for the AICO approval scenario."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from aico.app.boss_absent_aico_runner import (
    AicoApprovalCheckpoint,
    AicoBenchmarkRunPhase,
    AicoBenchmarkRunState,
    AicoBenchmarkRuntimeAdmission,
    AicoBenchmarkStateStore,
    record_aico_approval_checkpoint,
)
from aico.core.boss_absent_benchmark import (
    BossAbsentBenchmarkContract,
    BossAbsentTask,
    canonical_sha256,
)
from aico.core.models import FrozenModel, utc_now

_MAX_APPROVAL_FILE_BYTES = 65_536
_MAX_ACTION_CONTENT_BYTES = 16_384


class AicoBenchmarkApprovalGrant(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["approved"] = "approved"
    granted_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_window(self) -> AicoBenchmarkApprovalGrant:
        if (
            self.granted_at.tzinfo is None
            or self.granted_at.utcoffset() is None
            or self.expires_at.tzinfo is None
            or self.expires_at.utcoffset() is None
            or self.expires_at <= self.granted_at
        ):
            raise ValueError("AICO benchmark approval grant window is invalid")
        return self


class AicoApprovalActionIntent(FrozenModel):
    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    grant_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    target_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AicoApprovalActionReceipt(FrozenModel):
    version: Literal[1] = 1
    intent_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    grant_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    target_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_count: Literal[1] = 1
    reconciled_after_write: bool


def approval_action_fingerprints(task: BossAbsentTask) -> tuple[str, str, str]:
    action_id, target_name, content = _action_from_fixture(task)
    return action_id, _sha(target_name.encode("utf-8")), _sha(content)


def execute_aico_approval_action(
    contract: BossAbsentBenchmarkContract,
    task: BossAbsentTask,
    admission: AicoBenchmarkRuntimeAdmission,
    store: AicoBenchmarkStateStore,
    *,
    grant_path: Path,
    mutation_root: Path,
    intent_path: Path,
    receipt_path: Path,
    now: datetime | None = None,
) -> AicoBenchmarkRunState:
    """Execute or reconcile one exact approved fixture mutation, then release the runner."""
    state = store.load()
    if state is None:
        raise ValueError("AICO approval action has no pending run state")
    state_identity = (
        task.approval_required
        and state.contract_sha256 == canonical_sha256(contract)
        and state.runtime_admission_sha256 == canonical_sha256(admission)
        and state.benchmark_id == contract.benchmark_id
        and state.task_id == task.task_id
    )
    if not state_identity:
        raise ValueError("AICO approval action run identity drifted")
    existing = _existing_receipt(receipt_path)
    if existing is not None and state.approval_checkpoint is not None:
        _validate_completed_state(state, existing)
        return state
    if (
        state.phase is not AicoBenchmarkRunPhase.APPROVAL_PENDING
        or state.approval_request_sha256 is None
    ):
        raise ValueError("AICO approval action is not at a pending boundary")
    action_id, target_name, content = _action_from_fixture(task)
    grant_bytes = _read_owner_file(grant_path)
    try:
        grant = AicoBenchmarkApprovalGrant.model_validate_json(grant_bytes)
    except ValueError:
        raise ValueError("AICO approval grant is invalid") from None
    current = now or utc_now()
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("AICO approval action clock must be timezone-aware")
    identity = (
        grant.contract_sha256 == canonical_sha256(contract)
        and grant.task_id == task.task_id
        and grant.request_sha256 == state.approval_request_sha256
        and grant.granted_at <= current < grant.expires_at
    )
    if not identity:
        raise ValueError("AICO approval grant does not match the pending action")
    grant_sha = _sha(grant_bytes)
    target = _safe_target(mutation_root, target_name)
    intent = AicoApprovalActionIntent(
        contract_sha256=canonical_sha256(contract),
        task_id=task.task_id,
        request_sha256=state.approval_request_sha256,
        grant_sha256=grant_sha,
        action_id=action_id,
        target_sha256=_sha(target_name.encode("utf-8")),
        content_sha256=_sha(content),
    )
    intent_existed = intent_path.exists() or intent_path.is_symlink()
    if not intent_existed and target.exists():
        raise ValueError("AICO approval mutation target predates the durable intent")
    _write_or_match(intent_path, intent.model_dump_json(indent=2).encode("utf-8") + b"\n")
    reconciled = _write_action_target(target, content)
    receipt = AicoApprovalActionReceipt(
        intent_sha256=canonical_sha256(intent),
        contract_sha256=intent.contract_sha256,
        task_id=intent.task_id,
        request_sha256=intent.request_sha256,
        grant_sha256=grant_sha,
        action_id=action_id,
        target_sha256=intent.target_sha256,
        content_sha256=intent.content_sha256,
        reconciled_after_write=reconciled,
    )
    receipt_bytes = receipt.model_dump_json(indent=2).encode("utf-8") + b"\n"
    _write_or_match(receipt_path, receipt_bytes)
    return record_aico_approval_checkpoint(
        contract,
        task,
        admission,
        AicoApprovalCheckpoint(
            after_sequence=1,
            request_sha256=state.approval_request_sha256,
            grant_sha256=grant_sha,
            action_receipt_sha256=_sha(receipt_bytes),
        ),
        store,
    )


def _action_from_fixture(task: BossAbsentTask) -> tuple[str, str, bytes]:
    try:
        payload = json.loads(task.fixture, object_pairs_hook=_unique_object)
    except json.JSONDecodeError:
        raise ValueError("AICO approval fixture is not valid JSON") from None
    if not isinstance(payload, dict):
        raise ValueError("AICO approval fixture must be a JSON object")
    action_id = payload.get("action_id")
    target = payload.get("target")
    content = payload.get("content")
    if (
        not isinstance(action_id, str)
        or not isinstance(target, str)
        or not isinstance(content, str)
        or not action_id
        or not target
        or not content
    ):
        raise ValueError("AICO approval fixture action is incomplete")
    encoded = content.encode("utf-8")
    if len(encoded) > _MAX_ACTION_CONTENT_BYTES:
        raise ValueError("AICO approval action content exceeds bounded size")
    return action_id, target, encoded


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("AICO approval fixture contains a duplicate key")
        result[key] = value
    return result


def _safe_target(root: Path, relative_name: str) -> Path:
    relative = Path(relative_name)
    if (
        not root.is_absolute()
        or relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError("AICO approval mutation target is unsafe")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    _validate_private_directory(root)
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        current.mkdir(mode=0o700, exist_ok=True)
        _validate_private_directory(current)
    target = root / relative
    if target.is_symlink():
        raise ValueError("AICO approval mutation target is unsafe")
    return target


def _write_action_target(path: Path, content: bytes) -> bool:
    if path.exists():
        existing = _read_owner_file(path)
        if existing != content:
            raise ValueError("AICO approval mutation target already has different content")
        return True
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        _fsync_directory(path.parent)
    except BaseException:
        if path.exists() and path.stat().st_size == 0:
            path.unlink()
        raise
    return False


def _write_or_match(path: Path, payload: bytes) -> None:
    if not path.is_absolute():
        raise ValueError("AICO approval artifact path must be absolute")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _validate_private_directory(path.parent)
    if path.exists() or path.is_symlink():
        if _read_owner_file(path) != payload:
            raise ValueError("AICO approval artifact identity drifted")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        _fsync_directory(path.parent)
    except BaseException:
        if path.exists() and path.stat().st_size == 0:
            path.unlink()
        raise


def _existing_receipt(path: Path) -> AicoApprovalActionReceipt | None:
    if not path.exists() and not path.is_symlink():
        return None
    payload = _read_owner_file(path)
    try:
        return AicoApprovalActionReceipt.model_validate_json(payload)
    except ValueError:
        raise ValueError("AICO approval action receipt is invalid") from None


def _validate_completed_state(
    state: AicoBenchmarkRunState,
    receipt: AicoApprovalActionReceipt,
) -> None:
    checkpoint = state.approval_checkpoint
    assert checkpoint is not None
    if (
        checkpoint.request_sha256 != receipt.request_sha256
        or checkpoint.grant_sha256 != receipt.grant_sha256
        or checkpoint.action_receipt_sha256
        != _sha(receipt.model_dump_json(indent=2).encode("utf-8") + b"\n")
    ):
        raise ValueError("AICO completed approval state drifted from the action receipt")


def _read_owner_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("AICO approval artifact must be a regular non-symlink file")
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077
        or info.st_size > _MAX_APPROVAL_FILE_BYTES
    ):
        raise ValueError("AICO approval artifact must be owner-only and bounded")
    return path.read_bytes()


def _validate_private_directory(path: Path) -> None:
    info = path.lstat()
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077
    ):
        raise ValueError("AICO approval artifact directory must be owner-only")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
