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


class MemoryEdgeType(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVED_FROM = "derived_from"
    BROADCAST_TO = "broadcast_to"
    SUPERSEDES = "supersedes"


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
    archived_at: datetime | None = None
    reason: str | None = None

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


class MemoryCitation(FrozenModel):
    memory_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


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
            lines.append(
                f"- [{item.memory_id}] {item.claim} "
                f"(confidence: {item.confidence:.2f}; scope: {_scope_label(item.scope)})"
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
        self._semantic_scorer = semantic_scorer or LocalSemanticMemoryScorer()
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
        self._semantic_scorer = semantic_scorer or LocalSemanticMemoryScorer()

    def retrieve_packet(
        self,
        *,
        scopes: tuple[MemoryScope, ...],
        query: str = "",
        governor: MemoryGovernor | None = None,
        top_k: int = 5,
    ) -> MemoryPacket:
        active_governor = governor or MemoryGovernor()
        atoms: list[MemoryAtom] = []
        seen: set[str] = set()
        for scope in scopes:
            scoped_atoms = self._store.list_atoms(scope)
            for atom in scoped_atoms:
                if atom.memory_id in seen:
                    continue
                seen.add(atom.memory_id)
                if active_governor.allows(atom) and (
                    not query.strip() or self._semantic_scorer.score(query, atom) > 0
                ):
                    atoms.append(atom)
        ranked = sorted(
            atoms,
            key=lambda atom: (
                self._semantic_scorer.score(query, atom),
                atom.confidence,
                atom.created_at,
            ),
            reverse=True,
        )
        return active_governor.project(tuple(ranked[:top_k]))


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


def _require_fields(*field_pairs: object) -> None:
    for value, name in zip(field_pairs[0::2], field_pairs[1::2], strict=True):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required for this memory scope")


def _search_text(atom: MemoryAtom) -> str:
    return f"{atom.claim} {' '.join(atom.tags)} {atom.source}".casefold()


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

_SEMANTIC_ALIASES: dict[str, tuple[str, ...]] = {
    "approval": ("审批", "批准", "review"),
    "contract": ("合同", "legal", "法务"),
    "contracts": ("合同", "legal", "法务"),
    "external": ("外部", "对外", "sharing"),
    "legal": ("法务", "合规", "review", "检查"),
    "memorypacket": ("memory", "packet", "citation"),
    "progress": ("进度", "阶段", "汇报", "report"),
    "report": ("汇报", "报告", "进度"),
    "review": ("检查", "评审", "审查", "法务"),
    "risk": ("风险", "卡点", "blocker"),
    "sharing": ("分享", "共享", "对外"),
    "stage": ("阶段", "进度"),
    "status": ("状态", "进度", "汇报"),
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
    "进度": ("progress", "status", "stage"),
    "风险": ("risk", "blocker"),
}
