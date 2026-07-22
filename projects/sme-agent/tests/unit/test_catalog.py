from __future__ import annotations

import pytest
from pydantic import ValidationError

from sme_agent.adapters.in_memory_metadata import InMemoryMetadataRepository
from sme_agent.metadata import (
    BusinessEntity,
    Dimension,
    MetadataCatalog,
    MetadataRelation,
    Metric,
    RelationKind,
    WarehouseAsset,
)


def _catalog() -> MetadataCatalog:
    return MetadataCatalog(InMemoryMetadataRepository())


def test_catalog_registers_and_searches_governed_assets() -> None:
    catalog = _catalog()
    metric = Metric(
        asset_id="metric.revenue",
        name="Revenue",
        description="Recognized operating revenue",
        aliases=("营业收入", "收入"),
        formula="sum(order_amount)",
        aggregation="sum",
    )

    catalog.register(metric)

    assert catalog.search("营业收入") == (metric,)
    assert catalog.search("operating") == (metric,)


def test_catalog_connects_metric_dimension_warehouse_and_entity() -> None:
    catalog = _catalog()
    metric = catalog.register(
        Metric(
            asset_id="metric.revenue",
            name="Revenue",
            description="Recognized revenue",
            formula="sum(order_amount)",
            aggregation="sum",
        )
    )
    dimension = catalog.register(
        Dimension(
            asset_id="dimension.region",
            name="Region",
            description="Sales management region",
            data_type="string",
        )
    )
    warehouse = catalog.register(
        WarehouseAsset(
            asset_id="table.fact_order",
            name="Order fact",
            description="One row per order line",
            platform="postgres",
            qualified_name="analytics.fact_order",
        )
    )
    entity = catalog.register(
        BusinessEntity(
            asset_id="entity.order",
            name="Order",
            description="A customer purchase order",
            identifier_fields=("order_id",),
        )
    )

    catalog.connect(
        MetadataRelation(
            source_id=metric.asset_id,
            target_id=dimension.asset_id,
            kind=RelationKind.SLICED_BY,
        )
    )
    catalog.connect(
        MetadataRelation(
            source_id=metric.asset_id,
            target_id=warehouse.asset_id,
            kind=RelationKind.SOURCED_FROM,
        )
    )
    catalog.connect(
        MetadataRelation(
            source_id=warehouse.asset_id,
            target_id=entity.asset_id,
            kind=RelationKind.BELONGS_TO,
        )
    )

    assert catalog.neighbors(metric.asset_id) == (dimension, warehouse)
    assert catalog.neighbors(warehouse.asset_id) == (metric, entity)


def test_catalog_rejects_relations_to_unknown_assets() -> None:
    catalog = _catalog()
    catalog.register(
        Metric(
            asset_id="metric.revenue",
            name="Revenue",
            description="Recognized revenue",
            formula="sum(order_amount)",
            aggregation="sum",
        )
    )

    with pytest.raises(ValueError, match="unknown target asset"):
        catalog.connect(
            MetadataRelation(
                source_id="metric.revenue",
                target_id="dimension.missing",
                kind=RelationKind.SLICED_BY,
            )
        )


def test_catalog_deduplicates_identical_relations() -> None:
    repository = InMemoryMetadataRepository()
    catalog = MetadataCatalog(repository)
    for asset in (
        Dimension(
            asset_id="dimension.region",
            name="Region",
            description="Sales region",
            data_type="string",
        ),
        BusinessEntity(
            asset_id="entity.customer",
            name="Customer",
            description="A buying organization",
            identifier_fields=("customer_id",),
        ),
    ):
        catalog.register(asset)
    relation = MetadataRelation(
        source_id="dimension.region",
        target_id="entity.customer",
        kind=RelationKind.RELATED_TO,
    )

    catalog.connect(relation)
    catalog.connect(relation)

    assert repository.list_relations() == (relation,)


def test_metric_rejects_a_mismatched_metadata_kind() -> None:
    with pytest.raises(ValidationError):
        Metric.model_validate(
            {
                "asset_id": "metric.revenue",
                "name": "Revenue",
                "kind": "dimension",
                "description": "Recognized revenue",
                "formula": "sum(order_amount)",
                "aggregation": "sum",
            }
        )


def test_catalog_rejects_invalid_relation_signature() -> None:
    catalog = _catalog()
    warehouse = catalog.register(
        WarehouseAsset(
            asset_id="table.fact_order",
            name="Order fact",
            description="One row per order line",
            platform="postgres",
            qualified_name="analytics.fact_order",
        )
    )
    entity = catalog.register(
        BusinessEntity(
            asset_id="entity.order",
            name="Order",
            description="A customer purchase order",
            identifier_fields=("order_id",),
        )
    )

    with pytest.raises(ValueError, match="invalid metadata relation signature"):
        catalog.connect(
            MetadataRelation(
                source_id=warehouse.asset_id,
                target_id=entity.asset_id,
                kind=RelationKind.DESCRIBED_BY,
            )
        )


def test_catalog_requires_version_increment_for_changed_asset() -> None:
    catalog = _catalog()
    original = Metric(
        asset_id="metric.revenue",
        name="Revenue",
        description="Recognized revenue",
        formula="sum(order_amount)",
        aggregation="sum",
    )
    catalog.register(original)

    with pytest.raises(ValueError, match="increment version"):
        catalog.register(original.model_copy(update={"description": "Changed definition"}))

    updated = original.model_copy(update={"description": "Changed definition", "version": 2})
    assert catalog.register(updated) == updated
