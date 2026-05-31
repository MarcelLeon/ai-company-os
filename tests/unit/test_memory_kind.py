"""Memory `kind` + ExperienceMeta validation and JSONL backward compatibility."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aico.core import (
    ExperienceMeta,
    JsonlMemoryStore,
    MemoryAtom,
    MemoryEvidence,
    MemoryKind,
    MemoryScope,
)


def _make_atom(
    *,
    memory_id: str = "mem-kind-1",
    kind: MemoryKind = MemoryKind.FACT,
    experience: ExperienceMeta | None = None,
) -> MemoryAtom:
    return MemoryAtom(
        memory_id=memory_id,
        claim="Build reusable retry runbook for adapter idle timeout.",
        evidence=(MemoryEvidence(ref="audit:event-1", source="audit"),),
        scope=MemoryScope.project("aico"),
        source="dream_review",
        confidence=0.6,
        created_by="lead-agent",
        kind=kind,
        experience=experience,
    )


def test_memory_atom_default_kind_is_fact() -> None:
    atom = MemoryAtom(
        memory_id="mem-default",
        claim="Default kind atom.",
        evidence=(MemoryEvidence(ref="audit:event-1", source="audit"),),
        scope=MemoryScope.project("aico"),
        source="boss_feedback",
        confidence=0.6,
        created_by="lead-agent",
    )
    assert atom.kind is MemoryKind.FACT
    assert atom.experience is None


def test_memory_atom_experience_requires_meta() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _make_atom(kind=MemoryKind.EXPERIENCE)
    assert "experience metadata" in str(exc_info.value)


def test_memory_atom_fact_rejects_experience_meta() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _make_atom(
            kind=MemoryKind.FACT,
            experience=ExperienceMeta(triggers=("adapter_idle_timeout",)),
        )
    assert "must not carry experience metadata" in str(exc_info.value)


def test_memory_atom_experience_accepts_meta() -> None:
    atom = _make_atom(
        kind=MemoryKind.EXPERIENCE,
        experience=ExperienceMeta(
            applies_to=("implementer",),
            triggers=("adapter_idle_timeout",),
        ),
    )
    assert atom.kind is MemoryKind.EXPERIENCE
    assert atom.experience is not None
    assert atom.experience.applies_to == ("implementer",)
    assert atom.experience.triggers == ("adapter_idle_timeout",)
    assert atom.experience.injection_count == 0
    assert atom.experience.verdict_hits == 0
    assert atom.experience.verdict_misses == 0


def test_jsonl_store_loads_legacy_atom_without_kind(tmp_path: Path) -> None:
    """Old JSONL written before M1 lacks `kind`/`experience` fields; loading must succeed."""
    legacy_path = tmp_path / "memory.jsonl"
    legacy_atom_payload = {
        "memory_id": "legacy-1",
        "claim": "Legacy fact captured before M1.",
        "evidence": [{"ref": "audit:legacy", "source": "audit"}],
        "scope": {
            "owner_type": "project",
            "owner_id": "aico",
            "project_id": "aico",
        },
        "source": "boss_feedback",
        "confidence": 0.8,
        "created_by": "legacy-agent",
    }
    legacy_path.write_text(
        json.dumps({"record_type": "atom", "payload": legacy_atom_payload}) + "\n",
        encoding="utf-8",
    )

    store = JsonlMemoryStore(legacy_path)
    loaded = store.get_atom("legacy-1")
    assert loaded is not None
    assert loaded.kind is MemoryKind.FACT
    assert loaded.experience is None
