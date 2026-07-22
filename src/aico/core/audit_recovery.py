"""Crash-safe materialization primitives for audit-ledger recovery."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from aico.core.audit_ledger import (
    AuditIntegrityError,
    AuditLedgerSummary,
    _checkpoint_path,
    _copy_new_private_file,
    _ledger_lock,
    _load_state,
    _same_path,
    _sync_directory,
    _validate_owner_file,
    copy_audit_ledger_snapshot,
)


@dataclass(frozen=True)
class AuditRawSnapshot:
    ledger_present: bool
    checkpoint_present: bool


def copy_raw_audit_ledger_snapshot(path: Path, output_path: Path) -> AuditRawSnapshot:
    """Preserve owned regular audit files without claiming that they are valid."""
    checkpoint = _checkpoint_path(path)
    checkpoint_output = _checkpoint_path(output_path)
    if not path.exists() and not checkpoint.exists():
        raise AuditIntegrityError("audit ledger does not exist")
    if _same_path(output_path, path) or _same_path(checkpoint_output, checkpoint):
        raise AuditIntegrityError("audit snapshot output must differ from the live ledger")
    if any(
        candidate.exists() or candidate.is_symlink()
        for candidate in (output_path, checkpoint_output)
    ):
        raise AuditIntegrityError("audit snapshot output already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        with _ledger_lock(path):
            _validate_restore_source(path)
            if path.exists():
                _copy_new_private_file(path, output_path)
                created.append(output_path)
            if checkpoint.exists():
                _copy_new_private_file(checkpoint, checkpoint_output)
                created.append(checkpoint_output)
        _sync_directory(output_path.parent)
        return AuditRawSnapshot(
            ledger_present=output_path.exists(),
            checkpoint_present=checkpoint_output.exists(),
        )
    except BaseException:
        for created_path in created:
            created_path.unlink(missing_ok=True)
        raise


def replace_audit_ledger_snapshot(path: Path, snapshot_path: Path) -> AuditLedgerSummary:
    """Replace a ledger/checkpoint pair; an interrupted pair remains fail-closed."""
    if _same_path(path, snapshot_path):
        raise AuditIntegrityError("audit restore target and snapshot must differ")
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.parent / f".{path.name}.{uuid4().hex}.restore"
    staged_checkpoint = _checkpoint_path(staged)
    try:
        expected = copy_audit_ledger_snapshot(snapshot_path, staged)
        with _ledger_lock(path):
            _validate_restore_source(path)
            os.replace(staged, path)
            _sync_directory(path.parent)
            os.replace(staged_checkpoint, _checkpoint_path(path))
            _sync_directory(path.parent)
            restored = _load_state(path, require_sealed=True).summary()
        if restored != expected:
            raise AuditIntegrityError("restored audit ledger does not match its snapshot")
        return restored
    finally:
        staged.unlink(missing_ok=True)
        staged_checkpoint.unlink(missing_ok=True)


def _validate_restore_source(path: Path) -> None:
    for candidate in (path, _checkpoint_path(path)):
        if candidate.exists():
            _validate_owner_file(candidate, require_private=False)
        elif candidate.is_symlink():
            raise AuditIntegrityError("audit ledger must not use symlink files")
