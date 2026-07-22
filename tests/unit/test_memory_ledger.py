from __future__ import annotations

import json
from pathlib import Path

import pytest

import aico.core.memory_ledger as memory_ledger_module
from aico.core import (
    JsonlMemoryStore,
    MemoryAtom,
    MemoryEvidence,
    MemoryIntegrityError,
    MemoryScope,
    seal_legacy_memory_ledger,
    verify_memory_ledger,
)


def test_memory_ledger_is_sealed_private_and_tamper_evident(tmp_path: Path) -> None:
    path = tmp_path / "private" / "memory.jsonl"
    store = JsonlMemoryStore(path)
    store.append_atom(_atom("mem-1", "merchant policy is reviewed"))

    summary = verify_memory_ledger(path)

    assert summary.record_count == 1
    assert summary.sealed is True
    assert summary.checkpoint_lag is False
    assert path.stat().st_mode & 0o077 == 0
    payload = json.loads(path.read_text())
    assert payload["_memory"]["entry_sha256"] == summary.head_sha256

    path.write_bytes(path.read_bytes().replace(b"merchant policy", b"merchant polity"))
    with pytest.raises(MemoryIntegrityError, match="hash chain"):
        verify_memory_ledger(path)


def test_memory_ledger_rejects_truncation_and_unsealed_legacy_until_sealed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "memory.jsonl"
    atom = _atom("legacy", "legacy owner-reviewed memory")
    path.write_text(
        json.dumps(
            {"payload": atom.model_dump(mode="json"), "record_type": "atom"},
            sort_keys=True,
        )
        + "\n"
    )
    path.chmod(0o600)

    with pytest.raises(MemoryIntegrityError, match="unsealed"):
        JsonlMemoryStore(path)

    sealed = seal_legacy_memory_ledger(path)
    store = JsonlMemoryStore(path)
    assert sealed.record_count == 1
    assert store.get_atom("legacy") == atom

    checkpoint = path.with_name("memory.jsonl.checkpoint.json")
    path.write_bytes(b"")
    with pytest.raises(MemoryIntegrityError, match="truncated"):
        verify_memory_ledger(path)
    assert checkpoint.exists()


def test_process_peers_refresh_before_append_and_preserve_version_semantics(
    tmp_path: Path,
) -> None:
    path = tmp_path / "memory.jsonl"
    first = JsonlMemoryStore(path)
    second = JsonlMemoryStore(path)

    first.append_atom(_atom("shared", "version one"))
    second.append_atom(_atom("other", "written by peer"))
    first.append_atom(_atom("shared", "version two"))

    recovered = JsonlMemoryStore(path)
    assert recovered.get_atom("shared") is not None
    assert recovered.get_atom("shared").claim == "version two"  # type: ignore[union-attr]
    assert recovered.get_atom("other") is not None
    assert verify_memory_ledger(path).record_count == 3


def test_append_failure_does_not_publish_phantom_in_memory_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "memory.jsonl"
    store = JsonlMemoryStore(path)

    def fail_append(_path: Path, _payload: bytes) -> None:
        raise OSError("synthetic durable write failure")

    monkeypatch.setattr(memory_ledger_module, "_append_bytes", fail_append)
    with pytest.raises(OSError, match="synthetic"):
        store.append_atom(_atom("phantom", "must not become visible"))

    assert store.get_atom("phantom") is None
    assert verify_memory_ledger(path).record_count == 0


def test_checkpoint_lag_is_repaired_without_losing_committed_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "memory.jsonl"
    store = JsonlMemoryStore(path)
    real_write = memory_ledger_module._write_checkpoint

    def fail_checkpoint(*_args: object, **_kwargs: object) -> None:
        raise OSError("synthetic checkpoint failure")

    monkeypatch.setattr(memory_ledger_module, "_write_checkpoint", fail_checkpoint)
    with pytest.raises(OSError, match="synthetic"):
        store.append_atom(_atom("committed", "record reached durable JSONL"))
    monkeypatch.setattr(memory_ledger_module, "_write_checkpoint", real_write)

    recovered = JsonlMemoryStore(path)
    assert recovered.get_atom("committed") is not None
    assert verify_memory_ledger(path).checkpoint_lag is False


def _atom(memory_id: str, claim: str) -> MemoryAtom:
    return MemoryAtom(
        memory_id=memory_id,
        claim=claim,
        evidence=(MemoryEvidence(ref=f"task:{memory_id}", source="test"),),
        scope=MemoryScope.project("aico"),
        source="test",
        confidence=0.9,
        created_by="test-agent",
    )
