"""Application service for the first governed metadata vertical slice."""

from __future__ import annotations

from sme_agent.metadata.models import CatalogAsset, MetadataRelation
from sme_agent.metadata.relation_policy import validate_relation_signature
from sme_agent.metadata.repository import MetadataRepository


class MetadataCatalog:
    def __init__(self, repository: MetadataRepository) -> None:
        self._repository = repository

    def register(self, asset: CatalogAsset) -> CatalogAsset:
        current = self._repository.get(asset.asset_id)
        if current is not None and current != asset:
            if current.kind is not asset.kind:
                raise ValueError("metadata kind cannot change across versions")
            if asset.version <= current.version:
                raise ValueError("metadata updates must increment version")
        return self._repository.upsert(asset)

    def get(self, asset_id: str) -> CatalogAsset | None:
        return self._repository.get(asset_id)

    def connect(self, relation: MetadataRelation) -> MetadataRelation:
        if relation.source_id == relation.target_id:
            raise ValueError("metadata relation cannot point to itself")
        source = self._repository.get(relation.source_id)
        if source is None:
            raise ValueError(f"unknown source asset: {relation.source_id}")
        target = self._repository.get(relation.target_id)
        if target is None:
            raise ValueError(f"unknown target asset: {relation.target_id}")
        validate_relation_signature(relation.kind, source.kind, target.kind)
        return self._repository.add_relation(relation)

    def search(self, query: str) -> tuple[CatalogAsset, ...]:
        normalized = query.strip().casefold()
        if not normalized:
            return ()
        matches = []
        for asset in self._repository.list_assets():
            searchable = (asset.name, asset.description, *asset.aliases, *asset.tags)
            if any(normalized in value.casefold() for value in searchable):
                matches.append(asset)
        return tuple(matches)

    def neighbors(self, asset_id: str) -> tuple[CatalogAsset, ...]:
        if self._repository.get(asset_id) is None:
            raise ValueError(f"unknown asset: {asset_id}")
        neighbor_ids: list[str] = []
        for relation in self._repository.list_relations():
            if relation.source_id == asset_id:
                neighbor_ids.append(relation.target_id)
            elif relation.target_id == asset_id:
                neighbor_ids.append(relation.source_id)
        return tuple(
            asset
            for neighbor_id in dict.fromkeys(neighbor_ids)
            if (asset := self._repository.get(neighbor_id)) is not None
        )

    def relations_for(self, asset_id: str) -> tuple[MetadataRelation, ...]:
        if self._repository.get(asset_id) is None:
            raise ValueError(f"unknown asset: {asset_id}")
        return tuple(
            relation
            for relation in self._repository.list_relations()
            if relation.source_id == asset_id or relation.target_id == asset_id
        )
