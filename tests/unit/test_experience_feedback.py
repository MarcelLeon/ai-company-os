"""Outcome grader verdict parsing -> experience meta writeback."""

from __future__ import annotations

from pathlib import Path

import pytest

from aico.core import (
    ExperienceMeta,
    JsonlMemoryStore,
    MemoryAtom,
    MemoryEvidence,
    MemoryKind,
    MemoryScope,
    MemoryStatus,
    MetadataEntry,
    Task,
)
from aico.core.experience_feedback import (
    apply_verdict_to_owner_experiences,
    injected_experience_ids,
)
from aico.core.orchestrator_task_factory import INJECTED_EXPERIENCE_IDS_KEY
from aico.core.outcome_grader import GraderVerdict, parse_verdict


def _active_experience(memory_id: str, *, confidence: float = 0.6) -> MemoryAtom:
    return MemoryAtom(
        memory_id=memory_id,
        claim="Retry adapter with verbose logging after idle timeout.",
        evidence=(MemoryEvidence(ref=f"task:{memory_id}", source="dream_review"),),
        scope=MemoryScope.project("aico"),
        source="dream_review",
        confidence=confidence,
        created_by="lead-agent",
        status=MemoryStatus.ACTIVE,
        kind=MemoryKind.EXPERIENCE,
        experience=ExperienceMeta(applies_to=("implementer",)),
    )


def _owner_task(*injected: str) -> Task:
    metadata = (
        (
            MetadataEntry(
                key=INJECTED_EXPERIENCE_IDS_KEY,
                value=",".join(injected),
            ),
        )
        if injected
        else ()
    )
    return Task(
        task_id="task-owner-1",
        payload="ship the bugfix",
        requester_id="boss-1",
        target_persona="implementer",
        metadata=metadata,
    )


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("verdict: pass", GraderVerdict.PASS),
        ("VERDICT: PARTIAL", GraderVerdict.PARTIAL),
        ("**verdict:** fail", GraderVerdict.FAIL),
        ("1. verdict = pass\n2. evidence: ...", GraderVerdict.PASS),
        ("no canonical line here", None),
        ("", None),
    ],
)
def test_parse_verdict_tolerates_formatting(body: str, expected: GraderVerdict | None) -> None:
    assert parse_verdict(body) is expected


def test_injected_experience_ids_reads_metadata() -> None:
    assert injected_experience_ids(_owner_task("mem-a", "mem-b")) == ("mem-a", "mem-b")
    assert injected_experience_ids(_owner_task()) == ()


def test_pass_verdict_bumps_confidence_and_hits(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    store.append_atom(_active_experience("mem-pass", confidence=0.6))

    updated = apply_verdict_to_owner_experiences(
        store,
        owner_task=_owner_task("mem-pass"),
        verdict=GraderVerdict.PASS,
    )

    assert len(updated) == 1
    atom = store.get_atom("mem-pass")
    assert atom is not None
    assert atom.confidence == pytest.approx(0.65)
    assert atom.experience is not None
    assert atom.experience.verdict_hits == 1
    assert atom.experience.verdict_misses == 0
    assert atom.experience.injection_count == 1


def test_fail_verdict_drops_confidence_and_records_miss(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    store.append_atom(_active_experience("mem-fail", confidence=0.8))

    apply_verdict_to_owner_experiences(
        store,
        owner_task=_owner_task("mem-fail"),
        verdict=GraderVerdict.FAIL,
    )

    atom = store.get_atom("mem-fail")
    assert atom is not None
    assert atom.confidence == pytest.approx(0.7)
    assert atom.experience is not None
    assert atom.experience.verdict_hits == 0
    assert atom.experience.verdict_misses == 1
    assert atom.experience.injection_count == 1


def test_partial_verdict_keeps_confidence_but_counts_both(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    store.append_atom(_active_experience("mem-partial", confidence=0.5))

    apply_verdict_to_owner_experiences(
        store,
        owner_task=_owner_task("mem-partial"),
        verdict=GraderVerdict.PARTIAL,
    )

    atom = store.get_atom("mem-partial")
    assert atom is not None
    assert atom.confidence == pytest.approx(0.5)
    assert atom.experience is not None
    assert atom.experience.verdict_hits == 1
    assert atom.experience.verdict_misses == 1


def test_owner_task_without_injected_ids_is_a_no_op(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    store.append_atom(_active_experience("mem-untouched", confidence=0.7))

    updated = apply_verdict_to_owner_experiences(
        store,
        owner_task=_owner_task(),
        verdict=GraderVerdict.PASS,
    )

    assert updated == ()
    atom = store.get_atom("mem-untouched")
    assert atom is not None
    assert atom.confidence == pytest.approx(0.7)
    assert atom.experience is not None
    assert atom.experience.verdict_hits == 0


def test_apply_skips_unknown_or_non_experience_memory(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    store.append_atom(
        MemoryAtom(
            memory_id="mem-fact",
            claim="Boss prefers concise reports.",
            evidence=(MemoryEvidence(ref="raw:1", source="boss"),),
            scope=MemoryScope.project("aico"),
            source="boss",
            confidence=1.0,
            created_by="boss-1",
        )
    )

    updated = apply_verdict_to_owner_experiences(
        store,
        owner_task=_owner_task("mem-fact", "mem-missing"),
        verdict=GraderVerdict.PASS,
    )

    assert updated == ()
