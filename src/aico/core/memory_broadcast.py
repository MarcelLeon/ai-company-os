"""Broadcast shared memory into team-scoped consensus."""

from __future__ import annotations

from uuid import uuid4

from aico.core.memory import (
    MemoryAtom,
    MemoryEdge,
    MemoryEdgeType,
    MemoryEvidence,
    MemoryScope,
    MemoryScopeType,
    MemoryStore,
)
from aico.core.models import FrozenModel, utc_now


class MemoryBroadcastReceipt(FrozenModel):
    receipt_id: str
    source_memory_id: str
    broadcast_memory_id: str
    team_scope: MemoryScope
    recipients: tuple[str, ...] = ()


class MemoryBroadcastService:
    """Promote a scoped memory into a team-visible consensus atom."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def broadcast_to_team(
        self,
        *,
        source_memory_id: str,
        team_scope: MemoryScope,
        recipients: tuple[str, ...],
        created_by: str,
        reason: str = "team broadcast",
    ) -> MemoryBroadcastReceipt:
        if team_scope.owner_type is not MemoryScopeType.TEAM:
            raise ValueError("team_scope must be a team memory scope")
        source = self._source_atom(source_memory_id)
        if source.scope.project_id is not None and source.scope.project_id != team_scope.project_id:
            raise ValueError("cannot broadcast memory across projects")

        broadcast = self._store.append_atom(
            MemoryAtom(
                memory_id=f"mem-{uuid4().hex[:12]}",
                claim=source.claim,
                evidence=(
                    *source.evidence,
                    MemoryEvidence(
                        ref=source.memory_id,
                        source="memory_broadcast",
                        captured_at=utc_now(),
                        note=reason,
                    ),
                ),
                scope=team_scope,
                source="memory_broadcast",
                confidence=source.confidence,
                created_by=created_by,
                ttl_seconds=source.ttl_seconds,
                sensitivity=source.sensitivity,
                tags=_broadcast_tags(source.tags),
                reason=reason,
            )
        )
        edge = MemoryEdge(
            edge_id=f"edge-{uuid4().hex[:12]}",
            source_memory_id=source.memory_id,
            target_memory_id=broadcast.memory_id,
            edge_type=MemoryEdgeType.BROADCAST_TO,
        )
        self._store.append_edge(edge)
        return MemoryBroadcastReceipt(
            receipt_id=edge.edge_id,
            source_memory_id=source.memory_id,
            broadcast_memory_id=broadcast.memory_id,
            team_scope=team_scope,
            recipients=recipients,
        )

    def _source_atom(self, source_memory_id: str) -> MemoryAtom:
        source = self._store.get_atom(source_memory_id)
        if source is None:
            raise KeyError(f"Unknown memory id: {source_memory_id}")
        return source


def _broadcast_tags(tags: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    values: list[str] = []
    for tag in (*tags, "broadcast", "team-consensus"):
        if tag in seen:
            continue
        seen.add(tag)
        values.append(tag)
    return tuple(values)
