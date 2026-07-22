"""Deterministic metadata repository used by tests and early domain discovery."""

from __future__ import annotations

from sme_agent.metadata.models import CatalogAsset, MetadataRelation


class InMemoryMetadataRepository:
    def __init__(self) -> None:
        self._assets: dict[str, CatalogAsset] = {}
        self._relations: list[MetadataRelation] = []

    def get(self, asset_id: str) -> CatalogAsset | None:
        return self._assets.get(asset_id)

    def upsert(self, asset: CatalogAsset) -> CatalogAsset:
        self._assets[asset.asset_id] = asset
        return asset

    def list_assets(self) -> tuple[CatalogAsset, ...]:
        return tuple(self._assets.values())

    def add_relation(self, relation: MetadataRelation) -> MetadataRelation:
        if relation not in self._relations:
            self._relations.append(relation)
        return relation

    def list_relations(self) -> tuple[MetadataRelation, ...]:
        return tuple(self._relations)
