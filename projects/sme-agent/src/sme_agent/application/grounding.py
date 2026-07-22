"""Assemble governed context for a business question without calling an LLM."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from pydantic import Field

from sme_agent.metadata.catalog import MetadataCatalog
from sme_agent.metadata.models import (
    BusinessEntity,
    CatalogAsset,
    Dimension,
    FrozenModel,
    GlossaryTerm,
    KnowledgeDocument,
    MetadataKind,
    MetadataRelation,
    Metric,
    RelationKind,
    WarehouseAsset,
)

AssetT = TypeVar("AssetT", bound=CatalogAsset)


class DimensionFilter(FrozenModel):
    dimension_query: str = Field(min_length=1)
    value: str = Field(min_length=1)


class GroundingRequest(FrozenModel):
    question: str = Field(min_length=1)
    metric_query: str = Field(min_length=1)
    filters: tuple[DimensionFilter, ...] = ()


class GroundedQuestion(FrozenModel):
    question: str
    terms: tuple[GlossaryTerm, ...]
    metric: Metric
    dimensions: tuple[Dimension, ...]
    filters: tuple[DimensionFilter, ...]
    warehouse_assets: tuple[WarehouseAsset, ...]
    entities: tuple[BusinessEntity, ...]
    documents: tuple[KnowledgeDocument, ...]
    evidence_ids: tuple[str, ...]


class MetadataGroundingService:
    """Resolve explicit business hints to governed metadata and evidence."""

    def __init__(self, catalog: MetadataCatalog) -> None:
        self._catalog = catalog

    def ground(self, request: GroundingRequest) -> GroundedQuestion:
        metric, terms = self._resolve_metric(request.metric_query)
        metric_relations = self._catalog.relations_for(metric.asset_id)
        dimensions = self._resolve_dimensions(request.filters, metric_relations)
        warehouses = self._related_assets(
            metric.asset_id,
            metric_relations,
            RelationKind.SOURCED_FROM,
            WarehouseAsset,
        )
        entities = self._entities_for(warehouses)
        documents = self._documents_for(metric, entities)
        evidence_ids = _stable_ids(
            (*terms, metric, *dimensions, *warehouses, *entities, *documents)
        )
        return GroundedQuestion(
            question=request.question,
            terms=terms,
            metric=metric,
            dimensions=dimensions,
            filters=request.filters,
            warehouse_assets=warehouses,
            entities=entities,
            documents=documents,
            evidence_ids=evidence_ids,
        )

    def _resolve_metric(self, query: str) -> tuple[Metric, tuple[GlossaryTerm, ...]]:
        terms = tuple(
            asset for asset in self._catalog.search(query) if isinstance(asset, GlossaryTerm)
        )
        if len(terms) > 1:
            ids = ", ".join(term.asset_id for term in terms)
            raise ValueError(f"ambiguous glossary term '{query}': {ids}")
        if not terms:
            return self._resolve_one(query, MetadataKind.METRIC, Metric), ()
        term = terms[0]
        metrics = self._related_assets(
            term.asset_id,
            self._catalog.relations_for(term.asset_id),
            RelationKind.DEFINES,
            Metric,
        )
        if not metrics:
            raise ValueError(f"glossary term does not define a metric: {term.asset_id}")
        if len(metrics) > 1:
            ids = ", ".join(metric.asset_id for metric in metrics)
            raise ValueError(f"glossary term defines ambiguous metrics: {ids}")
        return metrics[0], (term,)

    def _resolve_dimensions(
        self,
        filters: tuple[DimensionFilter, ...],
        metric_relations: tuple[MetadataRelation, ...],
    ) -> tuple[Dimension, ...]:
        allowed_ids = {
            relation.target_id
            for relation in metric_relations
            if relation.kind is RelationKind.SLICED_BY
        }
        dimensions = tuple(
            self._resolve_one(item.dimension_query, MetadataKind.DIMENSION, Dimension)
            for item in filters
        )
        unrelated = tuple(item.asset_id for item in dimensions if item.asset_id not in allowed_ids)
        if unrelated:
            raise ValueError(
                f"dimensions are not governed for the resolved metric: {', '.join(unrelated)}"
            )
        return dimensions

    def _entities_for(
        self,
        warehouses: tuple[WarehouseAsset, ...],
    ) -> tuple[BusinessEntity, ...]:
        entities: list[BusinessEntity] = []
        for warehouse in warehouses:
            entities.extend(
                self._related_assets(
                    warehouse.asset_id,
                    self._catalog.relations_for(warehouse.asset_id),
                    RelationKind.BELONGS_TO,
                    BusinessEntity,
                )
            )
        return _deduplicate_assets(entities)

    def _documents_for(
        self,
        metric: Metric,
        entities: tuple[BusinessEntity, ...],
    ) -> tuple[KnowledgeDocument, ...]:
        documents: list[KnowledgeDocument] = []
        for asset_id in (metric.asset_id, *(entity.asset_id for entity in entities)):
            documents.extend(
                self._related_assets(
                    asset_id,
                    self._catalog.relations_for(asset_id),
                    RelationKind.DESCRIBED_BY,
                    KnowledgeDocument,
                )
            )
        return _deduplicate_assets(documents)

    def _resolve_one(
        self,
        query: str,
        kind: MetadataKind,
        asset_type: type[AssetT],
    ) -> AssetT:
        matches = tuple(
            asset
            for asset in self._catalog.search(query)
            if asset.kind is kind and isinstance(asset, asset_type)
        )
        if not matches:
            raise ValueError(f"no governed {kind.value} matches: {query}")
        if len(matches) > 1:
            ids = ", ".join(asset.asset_id for asset in matches)
            raise ValueError(f"ambiguous {kind.value} '{query}': {ids}")
        return matches[0]

    def _related_assets(
        self,
        source_id: str,
        relations: tuple[MetadataRelation, ...],
        relation_kind: RelationKind,
        asset_type: type[AssetT],
    ) -> tuple[AssetT, ...]:
        assets: list[AssetT] = []
        for relation in relations:
            if relation.kind is not relation_kind or relation.source_id != source_id:
                continue
            asset = self._catalog.get(relation.target_id)
            if isinstance(asset, asset_type):
                assets.append(asset)
        return tuple(assets)


def _deduplicate_assets(assets: Iterable[AssetT]) -> tuple[AssetT, ...]:
    unique: dict[str, AssetT] = {}
    for asset in assets:
        unique[asset.asset_id] = asset
    return tuple(unique.values())


def _stable_ids(assets: Iterable[CatalogAsset]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(asset.asset_id for asset in assets))
