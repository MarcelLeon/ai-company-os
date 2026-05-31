"""Project/team-scoped shared memory primitives for Phase 7."""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import Field, model_validator

from aico.core.models import FrozenModel, utc_now


class MemoryScopeType(StrEnum):
    BOSS = "boss"
    PROJECT = "project"
    TEAM = "team"
    ROLE = "role"
    AGENT = "agent"


class MemorySensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    SECRET = "secret"


class MemoryStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class MemoryPurpose(StrEnum):
    GENERAL_CONTEXT = "general_context"
    PUBLIC_BROADCAST = "public_broadcast"
    TASK_KEY_PROGRESS = "task_key_progress"
    TASK_PRIVATE = "task_private"
    DECISION_REVIEW = "decision_review"


class MemoryEdgeType(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVED_FROM = "derived_from"
    BROADCAST_TO = "broadcast_to"
    SUPERSEDES = "supersedes"


class MemoryKind(StrEnum):
    FACT = "fact"
    EXPERIENCE = "experience"


class ExperienceMeta(FrozenModel):
    applies_to: tuple[str, ...] = ()
    triggers: tuple[str, ...] = ()
    injection_count: int = Field(default=0, ge=0)
    verdict_hits: int = Field(default=0, ge=0)
    verdict_misses: int = Field(default=0, ge=0)


class MemoryScope(FrozenModel):
    owner_type: MemoryScopeType
    owner_id: str = Field(min_length=1)
    project_id: str | None = None
    team_id: str | None = None
    role_id: str | None = None
    agent_id: str | None = None

    @classmethod
    def boss(cls, boss_id: str) -> MemoryScope:
        return cls(owner_type=MemoryScopeType.BOSS, owner_id=boss_id)

    @classmethod
    def project(cls, project_id: str) -> MemoryScope:
        return cls(
            owner_type=MemoryScopeType.PROJECT,
            owner_id=project_id,
            project_id=project_id,
        )

    @classmethod
    def team(cls, project_id: str, team_id: str) -> MemoryScope:
        return cls(
            owner_type=MemoryScopeType.TEAM,
            owner_id=f"{project_id}/{team_id}",
            project_id=project_id,
            team_id=team_id,
        )

    @classmethod
    def role(cls, project_id: str, team_id: str, role_id: str) -> MemoryScope:
        return cls(
            owner_type=MemoryScopeType.ROLE,
            owner_id=f"{project_id}/{team_id}/{role_id}",
            project_id=project_id,
            team_id=team_id,
            role_id=role_id,
        )

    @classmethod
    def agent(cls, project_id: str, team_id: str, agent_id: str) -> MemoryScope:
        return cls(
            owner_type=MemoryScopeType.AGENT,
            owner_id=f"{project_id}/{team_id}/{agent_id}",
            project_id=project_id,
            team_id=team_id,
            agent_id=agent_id,
        )

    @model_validator(mode="after")
    def _validate_scope_boundary(self) -> MemoryScope:
        match self.owner_type:
            case MemoryScopeType.BOSS:
                return self
            case MemoryScopeType.PROJECT:
                _require_fields(self.project_id, "project_id")
            case MemoryScopeType.TEAM:
                _require_fields(self.project_id, "project_id", self.team_id, "team_id")
            case MemoryScopeType.ROLE:
                _require_fields(
                    self.project_id,
                    "project_id",
                    self.team_id,
                    "team_id",
                    self.role_id,
                    "role_id",
                )
            case MemoryScopeType.AGENT:
                _require_fields(
                    self.project_id,
                    "project_id",
                    self.team_id,
                    "team_id",
                    self.agent_id,
                    "agent_id",
                )
        return self

    def matches(self, scope: MemoryScope) -> bool:
        return self.owner_type is scope.owner_type and self.owner_id == scope.owner_id


class MemoryEvidence(FrozenModel):
    ref: str = Field(min_length=1)
    source: str = Field(min_length=1)
    captured_at: datetime = Field(default_factory=utc_now)
    note: str | None = None


class MemoryAtom(FrozenModel):
    memory_id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    evidence: tuple[MemoryEvidence, ...] = Field(min_length=1)
    scope: MemoryScope
    source: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    created_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)
    ttl_seconds: int = Field(default=90 * 24 * 60 * 60, ge=1)
    sensitivity: MemorySensitivity = MemorySensitivity.INTERNAL
    status: MemoryStatus = MemoryStatus.ACTIVE
    tags: tuple[str, ...] = ()
    purpose_tags: tuple[MemoryPurpose, ...] = (MemoryPurpose.GENERAL_CONTEXT,)
    archived_at: datetime | None = None
    reason: str | None = None
    kind: MemoryKind = MemoryKind.FACT
    experience: ExperienceMeta | None = None
    trace_id: str | None = None

    @model_validator(mode="after")
    def _validate_purpose_tags(self) -> MemoryAtom:
        if not self.purpose_tags:
            raise ValueError("purpose_tags must not be empty")
        return self

    @model_validator(mode="after")
    def _validate_kind_experience(self) -> MemoryAtom:
        if self.kind is MemoryKind.EXPERIENCE and self.experience is None:
            raise ValueError("kind=experience requires experience metadata")
        if self.kind is MemoryKind.FACT and self.experience is not None:
            raise ValueError("kind=fact must not carry experience metadata")
        return self

    def archived(self, *, reason: str | None = None) -> MemoryAtom:
        return self.model_copy(
            update={
                "archived_at": utc_now(),
                "reason": reason,
                "status": MemoryStatus.ARCHIVED,
            }
        )


class MemoryEdge(FrozenModel):
    edge_id: str = Field(min_length=1)
    source_memory_id: str = Field(min_length=1)
    target_memory_id: str = Field(min_length=1)
    edge_type: MemoryEdgeType
    weight: float = Field(default=1.0, gt=0.0)


class MemoryPacketItem(FrozenModel):
    memory_id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    scope: MemoryScope
    tags: tuple[str, ...] = ()
    purpose_tags: tuple[MemoryPurpose, ...] = (MemoryPurpose.GENERAL_CONTEXT,)


class MemoryCitation(FrozenModel):
    memory_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class MemoryRetrievalQuery(FrozenModel):
    scopes: tuple[MemoryScope, ...] = Field(min_length=1)
    query: str = ""
    role_id: str | None = None
    agent_id: str | None = None
    task_kind: str | None = None
    allowed_purposes: tuple[MemoryPurpose, ...] = ()
    top_k: int = Field(default=5, ge=1, le=20)
    max_tokens: int = Field(default=480, ge=32)


class MemoryRetrievalHit(FrozenModel):
    atom: MemoryAtom
    semantic_score: float = Field(ge=0.0, le=1.0)
    scope_score: float = Field(ge=0.0, le=1.0)
    recency_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_score: float = Field(ge=0.0, le=1.0)
    graph_score: float = Field(ge=0.0, le=1.0)
    final_score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class MemoryGraphMatch(FrozenModel):
    edge_type: MemoryEdgeType
    score: float = Field(ge=0.0, le=1.0)


class MemoryPacket(FrozenModel):
    items: tuple[MemoryPacketItem, ...] = ()
    citations: tuple[MemoryCitation, ...] = ()
    generated_at: datetime = Field(default_factory=utc_now)
    policy_summary: str = Field(default="max_sensitivity=internal; min_confidence=0.0")

    def render_prompt_section(self) -> str:
        if not self.items:
            return ""
        lines = ["Shared memory:"]
        for item in self.items:
            purposes = ", ".join(purpose.value for purpose in item.purpose_tags)
            lines.append(
                f"- [{item.memory_id}] {item.claim} "
                f"(confidence: {item.confidence:.2f}; scope: {_scope_label(item.scope)}; "
                f"purpose: {purposes})"
            )
        if self.citations:
            lines.append(
                "Citations: " + ", ".join(citation.memory_id for citation in self.citations)
            )
        return "\n".join(lines)


class MemoryStore(Protocol):
    def get_atom(self, memory_id: str) -> MemoryAtom | None: ...

    def append_atom(self, atom: MemoryAtom) -> MemoryAtom: ...

    def append_edge(self, edge: MemoryEdge) -> MemoryEdge: ...

    def list_edges(self, source_memory_id: str | None = None) -> tuple[MemoryEdge, ...]: ...

    def list_atoms(
        self,
        scope: MemoryScope,
        *,
        include_archived: bool = False,
    ) -> tuple[MemoryAtom, ...]: ...

    def search(self, scope: MemoryScope, query: str) -> tuple[MemoryAtom, ...]: ...

    def archive(self, memory_id: str, *, reason: str | None = None) -> MemoryAtom: ...


class MemorySemanticScorer(Protocol):
    """Score whether a query is semantically relevant to a memory atom."""

    def score(self, query: str, atom: MemoryAtom) -> float: ...


class JsonlMemoryStore:
    """Append-only JSONL memory store with in-memory indexes rebuilt on startup."""

    def __init__(
        self,
        path: Path,
        *,
        semantic_scorer: MemorySemanticScorer | None = None,
    ) -> None:
        self._path = path
        self._semantic_scorer = semantic_scorer or LocalHybridMemoryScorer()
        self._atoms: dict[str, MemoryAtom] = {}
        self._edges: list[MemoryEdge] = []
        self._load()

    def append_atom(self, atom: MemoryAtom) -> MemoryAtom:
        self._atoms[atom.memory_id] = atom
        self._append_record("atom", atom)
        return atom

    def get_atom(self, memory_id: str) -> MemoryAtom | None:
        return self._atoms.get(memory_id)

    def append_edge(self, edge: MemoryEdge) -> MemoryEdge:
        self._edges.append(edge)
        self._append_record("edge", edge)
        return edge

    def list_atoms(
        self,
        scope: MemoryScope,
        *,
        include_archived: bool = False,
    ) -> tuple[MemoryAtom, ...]:
        atoms = [
            atom
            for atom in self._atoms.values()
            if atom.scope.matches(scope)
            and (include_archived or atom.status is not MemoryStatus.ARCHIVED)
        ]
        return tuple(sorted(atoms, key=lambda atom: atom.created_at))

    def search(self, scope: MemoryScope, query: str) -> tuple[MemoryAtom, ...]:
        if not query.strip():
            return self.list_atoms(scope)
        scored = [
            (self._semantic_scorer.score(query, atom), atom) for atom in self.list_atoms(scope)
        ]
        matches = [(score, atom) for score, atom in scored if score > 0]
        ranked = sorted(
            matches,
            key=lambda item: (item[0], item[1].confidence, item[1].created_at),
            reverse=True,
        )
        return tuple(atom for _, atom in ranked)

    def archive(self, memory_id: str, *, reason: str | None = None) -> MemoryAtom:
        atom = self._atoms.get(memory_id)
        if atom is None:
            raise KeyError(f"Unknown memory id: {memory_id}")
        archived = atom.archived(reason=reason)
        return self.append_atom(archived)

    def list_edges(self, source_memory_id: str | None = None) -> tuple[MemoryEdge, ...]:
        if source_memory_id is None:
            return tuple(self._edges)
        return tuple(edge for edge in self._edges if edge.source_memory_id == source_memory_id)

    def _load(self) -> None:
        if not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            match payload.get("record_type"):
                case "atom":
                    atom = MemoryAtom.model_validate(payload["payload"])
                    self._atoms[atom.memory_id] = atom
                case "edge":
                    self._edges.append(MemoryEdge.model_validate(payload["payload"]))

    def _append_record(self, record_type: str, payload: FrozenModel) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {"payload": payload.model_dump(mode="json"), "record_type": record_type},
            ensure_ascii=False,
            sort_keys=True,
        )
        with self._path.open("a", encoding="utf-8") as file:
            file.write(f"{line}\n")


class MemoryGovernor:
    """Project MemoryAtom records into a prompt-safe packet view."""

    def __init__(
        self,
        *,
        max_sensitivity: MemorySensitivity = MemorySensitivity.INTERNAL,
        min_confidence: float = 0.0,
    ) -> None:
        self._max_sensitivity = max_sensitivity
        self._min_confidence = min_confidence

    @property
    def policy_summary(self) -> str:
        return (
            f"max_sensitivity={self._max_sensitivity.value}; min_confidence={self._min_confidence}"
        )

    def allows(self, atom: MemoryAtom) -> bool:
        if atom.status is not MemoryStatus.ACTIVE:
            return False
        if atom.confidence < self._min_confidence:
            return False
        return _sensitivity_rank(atom.sensitivity) <= _sensitivity_rank(self._max_sensitivity)

    def project(self, atoms: tuple[MemoryAtom, ...]) -> MemoryPacket:
        items: list[MemoryPacketItem] = []
        citations: list[MemoryCitation] = []
        for atom in atoms:
            if not self.allows(atom):
                continue
            items.append(
                MemoryPacketItem(
                    memory_id=atom.memory_id,
                    claim=atom.claim,
                    confidence=atom.confidence,
                    scope=atom.scope,
                    tags=atom.tags,
                    purpose_tags=atom.purpose_tags,
                )
            )
            citations.append(MemoryCitation(memory_id=atom.memory_id, reason="scope=query match"))
        return MemoryPacket(
            items=tuple(items),
            citations=tuple(citations),
            policy_summary=self.policy_summary,
        )


class MemoryRetriever:
    """Deterministic scoped retrieval for the first Memory Fabric slice."""

    def __init__(
        self,
        store: MemoryStore,
        *,
        semantic_scorer: MemorySemanticScorer | None = None,
    ) -> None:
        self._store = store
        self._semantic_scorer = semantic_scorer or LocalHybridMemoryScorer()

    def retrieve(
        self,
        retrieval_query: MemoryRetrievalQuery,
        *,
        governor: MemoryGovernor | None = None,
    ) -> tuple[MemoryRetrievalHit, ...]:
        active_governor = governor or MemoryGovernor()
        candidates = self._candidate_atoms(retrieval_query, active_governor)
        expanded_query = _expanded_query(retrieval_query)
        hits = tuple(
            hit
            for atom, graph_match in candidates
            if (
                hit := self._score_atom(
                    atom,
                    query=expanded_query,
                    scopes=retrieval_query.scopes,
                    graph_match=graph_match,
                )
            )
            is not None
        )
        ranked = sorted(
            hits,
            key=lambda hit: (hit.final_score, hit.atom.confidence, hit.atom.created_at),
            reverse=True,
        )
        return tuple(ranked[: retrieval_query.top_k])

    def retrieve_packet(
        self,
        *,
        scopes: tuple[MemoryScope, ...],
        query: str = "",
        governor: MemoryGovernor | None = None,
        top_k: int = 5,
        max_tokens: int = 480,
        allowed_purposes: tuple[MemoryPurpose, ...] = (),
    ) -> MemoryPacket:
        active_governor = governor or MemoryGovernor()
        hits = self.retrieve(
            MemoryRetrievalQuery(
                scopes=scopes,
                query=query,
                allowed_purposes=allowed_purposes,
                top_k=top_k,
                max_tokens=max_tokens,
            ),
            governor=active_governor,
        )
        return _packet_from_hits(
            _trim_hits_to_budget(hits, max_tokens=max_tokens),
            policy_summary=active_governor.policy_summary,
        )

    def _candidate_atoms(
        self,
        retrieval_query: MemoryRetrievalQuery,
        governor: MemoryGovernor,
    ) -> tuple[tuple[MemoryAtom, MemoryGraphMatch | None], ...]:
        scoped_atoms: dict[str, MemoryAtom] = {}
        direct_ids: list[str] = []
        graph_matches: dict[str, MemoryGraphMatch] = {}
        expanded_query = _expanded_query(retrieval_query)
        seen: set[str] = set()
        for scope in retrieval_query.scopes:
            for atom in self._store.list_atoms(scope):
                if atom.memory_id in seen:
                    continue
                seen.add(atom.memory_id)
                if not governor.allows(atom):
                    continue
                if not _purpose_allowed(atom, retrieval_query.allowed_purposes):
                    continue
                scoped_atoms[atom.memory_id] = atom
                if (
                    expanded_query.strip()
                    and self._semantic_scorer.score(
                        expanded_query,
                        atom,
                    )
                    <= 0
                ):
                    continue
                direct_ids.append(atom.memory_id)
        for memory_id in direct_ids:
            graph_matches.update(_graph_neighbors(self._store, memory_id, scoped_atoms))
        ordered_ids = [*direct_ids, *graph_matches.keys()]
        return tuple(
            (scoped_atoms[memory_id], graph_matches.get(memory_id))
            for memory_id in ordered_ids
            if memory_id in scoped_atoms
        )

    def _score_atom(
        self,
        atom: MemoryAtom,
        *,
        query: str,
        scopes: tuple[MemoryScope, ...],
        graph_match: MemoryGraphMatch | None = None,
    ) -> MemoryRetrievalHit | None:
        semantic_score = self._semantic_scorer.score(query, atom) if query.strip() else 0.0
        graph_score = 0.0 if graph_match is None else graph_match.score
        if query.strip() and semantic_score <= 0 and graph_score <= 0:
            return None
        scope_score = _scope_score(atom.scope, scopes)
        recency_score = _recency_score(atom)
        confidence_score = atom.confidence
        evidence_score = _evidence_score(atom)
        final_score = _weighted_score(
            semantic_score=semantic_score,
            scope_score=scope_score,
            recency_score=recency_score,
            confidence_score=confidence_score,
            evidence_score=evidence_score,
            graph_score=graph_score,
        )
        return MemoryRetrievalHit(
            atom=atom,
            semantic_score=semantic_score,
            scope_score=scope_score,
            recency_score=recency_score,
            confidence_score=confidence_score,
            evidence_score=evidence_score,
            graph_score=graph_score,
            final_score=final_score,
            reason=_retrieval_reason(
                atom,
                semantic_score=semantic_score,
                graph_match=graph_match,
            ),
        )


class LocalSemanticMemoryScorer:
    """Local semantic fallback that can later be replaced by embedding/LLM reranking."""

    def score(self, query: str, atom: MemoryAtom) -> float:
        query_units = _semantic_units(query)
        if not query_units:
            return 0.0
        memory_units = _semantic_units(_search_text(atom))
        if not memory_units:
            return 0.0
        overlap = query_units & memory_units
        if not overlap:
            return 0.0
        query_coverage = len(overlap) / len(query_units)
        memory_coverage = len(overlap) / len(memory_units)
        return (query_coverage * 0.75) + (memory_coverage * 0.25)


class LocalHybridMemoryScorer:
    """Local exact-plus-semantic scorer for operator recall commands."""

    def __init__(self, semantic_scorer: MemorySemanticScorer | None = None) -> None:
        self._semantic_scorer = semantic_scorer or LocalSemanticMemoryScorer()

    def score(self, query: str, atom: MemoryAtom) -> float:
        normalized_query = _normalize_search(query)
        if not normalized_query:
            return 0.0
        normalized_memory = _normalize_search(_search_text(atom))
        if normalized_query in normalized_memory:
            return 1.0
        phrase_score = _phrase_overlap_score(normalized_query, normalized_memory)
        semantic_score = self._semantic_scorer.score(query, atom)
        return min(1.0, max(phrase_score, semantic_score * 0.92))


def _packet_from_hits(
    hits: tuple[MemoryRetrievalHit, ...],
    *,
    policy_summary: str,
) -> MemoryPacket:
    return MemoryPacket(
        items=tuple(
            MemoryPacketItem(
                memory_id=hit.atom.memory_id,
                claim=hit.atom.claim,
                confidence=hit.atom.confidence,
                scope=hit.atom.scope,
                tags=hit.atom.tags,
                purpose_tags=hit.atom.purpose_tags,
            )
            for hit in hits
        ),
        citations=tuple(
            MemoryCitation(memory_id=hit.atom.memory_id, reason=hit.reason) for hit in hits
        ),
        policy_summary=policy_summary,
    )


def _trim_hits_to_budget(
    hits: tuple[MemoryRetrievalHit, ...],
    *,
    max_tokens: int,
) -> tuple[MemoryRetrievalHit, ...]:
    selected: list[MemoryRetrievalHit] = []
    used_tokens = 0
    for hit in hits:
        estimated_tokens = _estimated_tokens(hit.atom.claim)
        if used_tokens + estimated_tokens > max_tokens:
            continue
        selected.append(hit)
        used_tokens += estimated_tokens
    return tuple(selected)


def _graph_neighbors(
    store: MemoryStore,
    source_memory_id: str,
    scoped_atoms: dict[str, MemoryAtom],
) -> dict[str, MemoryGraphMatch]:
    matches: dict[str, MemoryGraphMatch] = {}
    for edge in store.list_edges(source_memory_id):
        if edge.edge_type not in _RETRIEVAL_EDGE_TYPES:
            continue
        if edge.target_memory_id not in scoped_atoms:
            continue
        matches[edge.target_memory_id] = MemoryGraphMatch(
            edge_type=edge.edge_type,
            score=_graph_edge_score(edge.edge_type),
        )
    return matches


def _graph_edge_score(edge_type: MemoryEdgeType) -> float:
    return {
        MemoryEdgeType.SUPPORTS: 0.80,
        MemoryEdgeType.DERIVED_FROM: 0.72,
        MemoryEdgeType.BROADCAST_TO: 0.68,
    }[edge_type]


def _expanded_query(retrieval_query: MemoryRetrievalQuery) -> str:
    parts = [retrieval_query.query]
    if retrieval_query.role_id:
        parts.extend(_ROLE_QUERY_HINTS.get(retrieval_query.role_id, (retrieval_query.role_id,)))
    if retrieval_query.agent_id:
        parts.append(retrieval_query.agent_id)
    if retrieval_query.task_kind:
        parts.extend(
            _TASK_KIND_QUERY_HINTS.get(retrieval_query.task_kind, (retrieval_query.task_kind,))
        )
    return " ".join(part for part in parts if part.strip())


def _weighted_score(
    *,
    semantic_score: float,
    scope_score: float,
    recency_score: float,
    confidence_score: float,
    evidence_score: float,
    graph_score: float,
) -> float:
    return min(
        1.0,
        (semantic_score * 0.45)
        + (scope_score * 0.20)
        + (confidence_score * 0.15)
        + (recency_score * 0.10)
        + (evidence_score * 0.05)
        + (graph_score * 0.05),
    )


def _scope_score(scope: MemoryScope, scopes: tuple[MemoryScope, ...]) -> float:
    if not any(scope.matches(candidate) for candidate in scopes):
        return 0.0
    return {
        MemoryScopeType.AGENT: 1.0,
        MemoryScopeType.ROLE: 0.92,
        MemoryScopeType.TEAM: 0.82,
        MemoryScopeType.PROJECT: 0.70,
        MemoryScopeType.BOSS: 0.55,
    }[scope.owner_type]


def _recency_score(atom: MemoryAtom) -> float:
    age_seconds = max(0.0, (utc_now() - atom.created_at).total_seconds())
    return max(0.0, 1.0 - min(age_seconds / atom.ttl_seconds, 1.0))


def _evidence_score(atom: MemoryAtom) -> float:
    return min(1.0, len(atom.evidence) / 2) if atom.evidence else 0.0


def _retrieval_reason(
    atom: MemoryAtom,
    *,
    semantic_score: float,
    graph_match: MemoryGraphMatch | None,
) -> str:
    if semantic_score > 0:
        prefix = "semantic match"
    elif graph_match is not None:
        prefix = "graph match"
    else:
        prefix = "scope match"
    reason = (
        f"{prefix}; scope={_scope_label(atom.scope)}; "
        f"sensitivity={atom.sensitivity.value}; confidence={atom.confidence:.2f}"
    )
    if graph_match is not None:
        reason += f"; graph={graph_match.edge_type.value}"
    return reason


def _estimated_tokens(text: str) -> int:
    ascii_words = len([part for part in text.split() if part.strip()])
    cjk_chars = sum(1 for char in text if _is_cjk(char))
    if ascii_words:
        return max(1, ascii_words)
    return max(1, cjk_chars // 2)


def _require_fields(*field_pairs: object) -> None:
    for value, name in zip(field_pairs[0::2], field_pairs[1::2], strict=True):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required for this memory scope")


def _search_text(atom: MemoryAtom) -> str:
    purposes = " ".join(purpose.value for purpose in atom.purpose_tags)
    return f"{atom.claim} {' '.join(atom.tags)} {purposes} {atom.source}".casefold()


def _normalize_search(text: str) -> str:
    return " ".join(text.casefold().split())


def _phrase_overlap_score(query: str, memory_text: str) -> float:
    query_units = _semantic_units(query)
    if not query_units:
        return 0.0
    memory_units = _semantic_units(memory_text)
    overlap = query_units & memory_units
    if not overlap:
        return 0.0
    return min(0.95, len(overlap) / len(query_units))


def _purpose_allowed(atom: MemoryAtom, allowed_purposes: tuple[MemoryPurpose, ...]) -> bool:
    if allowed_purposes:
        return any(purpose in allowed_purposes for purpose in atom.purpose_tags)
    return MemoryPurpose.TASK_PRIVATE not in atom.purpose_tags


def _sensitivity_rank(sensitivity: MemorySensitivity) -> int:
    order = {
        MemorySensitivity.PUBLIC: 0,
        MemorySensitivity.INTERNAL: 1,
        MemorySensitivity.RESTRICTED: 2,
        MemorySensitivity.SECRET: 3,
    }
    return order[sensitivity]


def _scope_label(scope: MemoryScope) -> str:
    return f"{scope.owner_type.value}:{scope.owner_id}"


def _semantic_units(text: str) -> frozenset[str]:
    normalized = text.casefold()
    units: set[str] = set()
    ascii_token = ""
    cjk_block = ""
    for char in normalized:
        if char.isascii() and char.isalnum():
            if cjk_block:
                _add_cjk_units(units, cjk_block)
                cjk_block = ""
            ascii_token += char
            continue
        if _is_cjk(char):
            if ascii_token:
                _add_ascii_unit(units, ascii_token)
                ascii_token = ""
            cjk_block += char
            continue
        if ascii_token:
            _add_ascii_unit(units, ascii_token)
            ascii_token = ""
        if cjk_block:
            _add_cjk_units(units, cjk_block)
            cjk_block = ""
    if ascii_token:
        _add_ascii_unit(units, ascii_token)
    if cjk_block:
        _add_cjk_units(units, cjk_block)
    _add_semantic_aliases(units, normalized)
    return frozenset(units)


def _add_ascii_unit(units: set[str], token: str) -> None:
    if len(token) < 2 or token in _STOP_WORDS:
        return
    units.add(_stem_ascii_token(token))


def _add_cjk_units(units: set[str], block: str) -> None:
    if len(block) == 1:
        units.add(block)
        return
    for width in (2, 3, 4):
        if len(block) < width:
            continue
        for index in range(0, len(block) - width + 1):
            units.add(block[index : index + width])


def _add_semantic_aliases(units: set[str], text: str) -> None:
    for marker, aliases in _SEMANTIC_ALIASES.items():
        if marker in text:
            units.update(aliases)


def _stem_ascii_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    for suffix in ("ing", "ed", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


_STOP_WORDS = frozenset(
    {
        "and",
        "are",
        "before",
        "for",
        "from",
        "into",
        "must",
        "the",
        "this",
        "with",
    }
)

_RETRIEVAL_EDGE_TYPES = frozenset(
    {
        MemoryEdgeType.SUPPORTS,
        MemoryEdgeType.DERIVED_FROM,
        MemoryEdgeType.BROADCAST_TO,
    }
)

_ROLE_QUERY_HINTS: dict[str, tuple[str, ...]] = {
    "docs": ("docs", "documentation", "release notes", "changelog"),
    "implementer": ("implementation", "code", "change", "bugfix"),
    "pm": ("plan", "scope", "milestone", "risk", "status"),
    "release-manager": ("release", "changelog", "release notes", "handoff"),
    "reviewer": ("review", "risk", "audit", "approval"),
    "tester": ("test", "qa", "regression", "checklist", "quality"),
}

_TASK_KIND_QUERY_HINTS: dict[str, tuple[str, ...]] = {
    "daily": ("report", "status", "progress", "blocked", "next"),
    "overnight": ("handoff", "blocked", "risk", "next actions"),
    "release": ("release", "changelog", "release notes", "shipping"),
    "review": ("review", "risk", "audit", "approval"),
    "test": ("test", "qa", "regression", "checklist"),
}

_SEMANTIC_ALIASES: dict[str, tuple[str, ...]] = {
    "approval": ("审批", "批准", "review"),
    "contract": ("合同", "legal", "法务"),
    "contracts": ("合同", "legal", "法务"),
    "external": ("外部", "对外", "sharing"),
    "legal": ("法务", "合规", "review", "检查"),
    "memorypacket": ("memory", "packet", "citation"),
    "progress": ("进度", "阶段", "汇报", "report"),
    "report": ("汇报", "报告", "进度"),
    "runbook": ("剧本", "手册", "复盘", "dream"),
    "review": ("检查", "评审", "审查", "法务"),
    "risk": ("风险", "卡点", "blocker"),
    "sharing": ("分享", "共享", "对外"),
    "stage": ("阶段", "进度"),
    "status": ("状态", "进度", "汇报"),
    "dream": ("复盘", "反思", "记忆", "runbook"),
    "grader": ("验收", "评分", "检查", "outcome"),
    "handoff": ("交接", "早报", "morning", "接手"),
    "morning": ("早报", "交接", "handoff", "接手"),
    "outcome": ("结果", "验收", "评分", "grader"),
    "阶段": ("progress", "stage", "status"),
    "合同": ("contract", "legal", "review"),
    "外部": ("external", "sharing"),
    "审查": ("review", "legal", "检查"),
    "审批": ("approval", "review"),
    "报告": ("report", "status"),
    "检查": ("review", "qa", "legal"),
    "法务": ("legal", "review", "contract"),
    "汇报": ("report", "status", "progress"),
    "状态": ("status", "report"),
    "结果": ("outcome", "grader", "acceptance"),
    "记忆": ("memory", "dream", "runbook"),
    "评分": ("grader", "outcome", "review"),
    "进度": ("progress", "status", "stage"),
    "交接": ("handoff", "morning", "status"),
    "反思": ("dream", "runbook", "memory"),
    "复盘": ("dream", "runbook", "memory"),
    "接手": ("handoff", "morning"),
    "早报": ("morning", "handoff", "report"),
    "风险": ("risk", "blocker"),
}
