"""Storage port for metadata catalogs."""

from __future__ import annotations

from typing import Protocol

from sme_agent.metadata.models import CatalogAsset, MetadataRelation


class MetadataRepository(Protocol):
    def get(self, asset_id: str) -> CatalogAsset | None: ...

    def upsert(self, asset: CatalogAsset) -> CatalogAsset: ...

    def list_assets(self) -> tuple[CatalogAsset, ...]: ...

    def add_relation(self, relation: MetadataRelation) -> MetadataRelation: ...

    def list_relations(self) -> tuple[MetadataRelation, ...]: ...
