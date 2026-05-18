from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from aico.core import (
    JsonlMemoryStore,
    MemoryAtom,
    MemoryBroadcastReceipt,
    MemoryBroadcastService,
    MemoryCitation,
    MemoryEdge,
    MemoryEdgeType,
    MemoryEvidence,
    MemoryGovernor,
    MemoryPacket,
    MemoryPacketItem,
    MemoryRetriever,
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemoryStatus,
)


def test_memory_atom_requires_evidence_and_scoped_project_context() -> None:
    evidence = MemoryEvidence(
        ref="audit:event-1",
        source="audit",
        captured_at=datetime(2026, 5, 15, tzinfo=UTC),
        note="boss clarified Phase 7 memory direction",
    )
    atom = MemoryAtom(
        memory_id="mem-1",
        claim="Phase 7 memory must be maintained by agents, not by the boss.",
        evidence=(evidence,),
        scope=MemoryScope.project("aico"),
        source="boss_feedback",
        confidence=0.92,
        created_by="lead-agent",
        ttl_seconds=30 * 24 * 60 * 60,
        tags=("phase-7", "memory"),
    )

    assert atom.scope.owner_type is MemoryScopeType.PROJECT
    assert atom.scope.project_id == "aico"
    assert atom.status is MemoryStatus.ACTIVE
    assert atom.sensitivity is MemorySensitivity.INTERNAL
    assert atom.created_at.tzinfo == UTC

    with pytest.raises(ValidationError):
        MemoryAtom(
            memory_id="mem-no-evidence",
            claim="Missing evidence should fail.",
            evidence=(),
            scope=MemoryScope.project("aico"),
            source="agent",
            confidence=0.7,
            created_by="lead-agent",
        )


def test_memory_scope_requires_project_or_team_for_a2a_shared_memory() -> None:
    assert MemoryScope.boss("wang").owner_id == "wang"
    assert MemoryScope.team("aico", "core").owner_id == "aico/core"
    assert MemoryScope.role("aico", "core", "reviewer").owner_id == "aico/core/reviewer"
    assert MemoryScope.agent("aico", "core", "codex").owner_id == "aico/core/codex"

    with pytest.raises(ValidationError):
        MemoryScope(owner_type=MemoryScopeType.TEAM, owner_id="core")

    with pytest.raises(ValidationError):
        MemoryScope(owner_type=MemoryScopeType.AGENT, owner_id="codex", project_id="aico")


def test_jsonl_memory_store_persists_searches_and_archives(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory" / "records.jsonl"
    store = JsonlMemoryStore(memory_path)
    atom = _memory_atom(
        memory_id="mem-aico-1",
        claim="AICO memory recall must stay project scoped.",
        tags=("aico", "memory"),
    )

    store.append_atom(atom)
    assert store.list_atoms(MemoryScope.project("aico")) == (atom,)
    assert store.search(MemoryScope.project("aico"), "recall") == (atom,)
    assert store.search(MemoryScope.project("other"), "recall") == ()

    restored = JsonlMemoryStore(memory_path)
    assert restored.list_atoms(MemoryScope.project("aico")) == (atom,)

    archived = restored.archive("mem-aico-1", reason="superseded by team broadcast")
    assert archived.status is MemoryStatus.ARCHIVED
    assert archived.archived_at is not None
    assert restored.list_atoms(MemoryScope.project("aico")) == ()
    assert restored.list_atoms(MemoryScope.project("aico"), include_archived=True) == (archived,)

    recovered_again = JsonlMemoryStore(memory_path)
    assert recovered_again.list_atoms(MemoryScope.project("aico")) == ()
    assert recovered_again.list_atoms(
        MemoryScope.project("aico"),
        include_archived=True,
    ) == (archived,)


def test_jsonl_memory_store_persists_edges(tmp_path: Path) -> None:
    memory_path = tmp_path / "memory.jsonl"
    store = JsonlMemoryStore(memory_path)
    source = _memory_atom(memory_id="mem-source", claim="Team memory supports scoped recall.")
    target = _memory_atom(
        memory_id="mem-target",
        claim="Scoped recall reduces repeated A2A context.",
    )
    edge = MemoryEdge(
        edge_id="edge-1",
        source_memory_id=source.memory_id,
        target_memory_id=target.memory_id,
        edge_type=MemoryEdgeType.SUPPORTS,
    )

    store.append_atom(source)
    store.append_atom(target)
    store.append_edge(edge)

    restored = JsonlMemoryStore(memory_path)
    assert restored.list_edges(source.memory_id) == (edge,)


def test_memory_retriever_builds_governed_packet_without_cross_project_leakage(
    tmp_path: Path,
) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    aico_project = _memory_atom(
        memory_id="mem-aico-project",
        claim="AICO memory must be agent-driven.",
        tags=("memory",),
    )
    aico_team = _memory_atom(
        memory_id="mem-aico-team",
        claim="Core team should use MemoryPacket citations.",
        scope=MemoryScope.team("aico", "core"),
        tags=("citation",),
    )
    other_project = _memory_atom(
        memory_id="mem-other",
        claim="Other project memory must not leak.",
        scope=MemoryScope.project("other"),
    )
    candidate = _memory_atom(
        memory_id="mem-candidate",
        claim="Candidate memory should not enter prompt.",
        status=MemoryStatus.CANDIDATE,
    )
    restricted = _memory_atom(
        memory_id="mem-restricted",
        claim="Restricted details need higher policy.",
        sensitivity=MemorySensitivity.RESTRICTED,
    )
    archived = store.append_atom(_memory_atom(memory_id="mem-archived", claim="Old rule."))
    for atom in (aico_project, aico_team, other_project, candidate, restricted):
        store.append_atom(atom)
    store.archive(archived.memory_id, reason="outdated")

    packet = MemoryRetriever(store).retrieve_packet(
        scopes=(MemoryScope.project("aico"), MemoryScope.team("aico", "core")),
        query="memory citation",
        governor=MemoryGovernor(max_sensitivity=MemorySensitivity.INTERNAL),
        top_k=5,
    )

    assert packet.items == (
        MemoryPacketItem(
            memory_id="mem-aico-team",
            claim="Core team should use MemoryPacket citations.",
            confidence=0.9,
            scope=MemoryScope.team("aico", "core"),
            tags=("citation",),
        ),
        MemoryPacketItem(
            memory_id="mem-aico-project",
            claim="AICO memory must be agent-driven.",
            confidence=0.9,
            scope=MemoryScope.project("aico"),
            tags=("memory",),
        ),
    )
    assert packet.citations == (
        MemoryCitation(memory_id="mem-aico-team", reason="scope=query match"),
        MemoryCitation(memory_id="mem-aico-project", reason="scope=query match"),
    )
    assert packet.policy_summary == "max_sensitivity=internal; min_confidence=0.0"


def test_memory_retriever_uses_semantic_scoring_for_chinese_long_query(
    tmp_path: Path,
) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    store.append_atom(
        _memory_atom(
            memory_id="mem-progress-preference",
            claim="Boss feedback: 我更喜欢汇报进度时告诉我还有几阶段",
            scope=MemoryScope.boss("boss-1"),
            tags=("boss-feedback",),
        )
    )

    packet = MemoryRetriever(store).retrieve_packet(
        scopes=(MemoryScope.boss("boss-1"),),
        query="汇报当前项目进度,并告诉我还有几阶段",
    )

    assert packet.items == (
        MemoryPacketItem(
            memory_id="mem-progress-preference",
            claim="Boss feedback: 我更喜欢汇报进度时告诉我还有几阶段",
            confidence=0.9,
            scope=MemoryScope.boss("boss-1"),
            tags=("boss-feedback",),
        ),
    )


def test_memory_search_supports_bilingual_semantic_aliases(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    atom = store.append_atom(
        _memory_atom(
            memory_id="mem-legal-review",
            claim="Customer contracts require legal review before external sharing.",
            tags=("customer-contracts",),
        )
    )

    assert store.search(MemoryScope.project("aico"), "法务检查") == (atom,)


def test_memory_packet_renders_compact_prompt_section() -> None:
    packet = MemoryPacket(
        items=(
            MemoryPacketItem(
                memory_id="mem-1",
                claim="Boss prefers agent-driven memory.",
                confidence=0.92,
                scope=MemoryScope.boss("wang"),
                tags=("preference",),
            ),
        ),
        citations=(MemoryCitation(memory_id="mem-1", reason="scope=query match"),),
        policy_summary="max_sensitivity=internal; min_confidence=0.0",
    )

    assert packet.render_prompt_section() == "\n".join(
        (
            "Shared memory:",
            "- [mem-1] Boss prefers agent-driven memory. (confidence: 0.92; scope: boss:wang)",
            "Citations: mem-1",
        )
    )


def test_memory_broadcast_creates_team_memory_edge_and_receipt(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    source = store.append_atom(
        _memory_atom(
            memory_id="mem-source",
            claim="Phase 7 memory must stay agent-driven.",
            tags=("phase-7",),
        )
    )
    service = MemoryBroadcastService(store)

    receipt = service.broadcast_to_team(
        source_memory_id=source.memory_id,
        team_scope=MemoryScope.team("aico", "default"),
        recipients=("claude", "codex"),
        created_by="lead-agent",
        reason="team consensus",
    )

    team_atoms = store.list_atoms(MemoryScope.team("aico", "default"))
    edges = store.list_edges(source.memory_id)

    assert len(team_atoms) == 1
    assert team_atoms[0].claim == "Phase 7 memory must stay agent-driven."
    assert team_atoms[0].scope == MemoryScope.team("aico", "default")
    assert team_atoms[0].source == "memory_broadcast"
    assert team_atoms[0].created_by == "lead-agent"
    assert "broadcast" in team_atoms[0].tags
    assert len(edges) == 1
    assert edges[0].edge_type is MemoryEdgeType.BROADCAST_TO
    assert edges[0].source_memory_id == source.memory_id
    assert edges[0].target_memory_id == team_atoms[0].memory_id
    assert receipt == MemoryBroadcastReceipt(
        receipt_id=receipt.receipt_id,
        source_memory_id=source.memory_id,
        broadcast_memory_id=team_atoms[0].memory_id,
        team_scope=MemoryScope.team("aico", "default"),
        recipients=("claude", "codex"),
    )


def test_memory_broadcast_rejects_cross_project_team_scope(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    store.append_atom(
        _memory_atom(
            memory_id="mem-source",
            claim="AICO memory must stay project scoped.",
            scope=MemoryScope.project("aico"),
        )
    )
    service = MemoryBroadcastService(store)

    with pytest.raises(ValueError, match="cannot broadcast memory across projects"):
        service.broadcast_to_team(
            source_memory_id="mem-source",
            team_scope=MemoryScope.team("other", "default"),
            recipients=("claude",),
            created_by="lead-agent",
        )


def _memory_atom(
    *,
    memory_id: str,
    claim: str,
    scope: MemoryScope | None = None,
    sensitivity: MemorySensitivity = MemorySensitivity.INTERNAL,
    status: MemoryStatus = MemoryStatus.ACTIVE,
    tags: tuple[str, ...] = (),
) -> MemoryAtom:
    return MemoryAtom(
        memory_id=memory_id,
        claim=claim,
        evidence=(
            MemoryEvidence(
                ref=f"audit:{memory_id}",
                source="test",
                captured_at=datetime(2026, 5, 15, tzinfo=UTC),
            ),
        ),
        scope=scope or MemoryScope.project("aico"),
        source="test",
        confidence=0.9,
        created_by="tester",
        sensitivity=sensitivity,
        status=status,
        tags=tags,
    )
