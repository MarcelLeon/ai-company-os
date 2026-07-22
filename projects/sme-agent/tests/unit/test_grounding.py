from __future__ import annotations

import pytest

from sme_agent.adapters.in_memory_metadata import InMemoryMetadataRepository
from sme_agent.application import DimensionFilter, GroundingRequest, MetadataGroundingService
from sme_agent.metadata import Dimension, MetadataCatalog, Metric
from sme_agent.samples import load_east_china_revenue_sample


def _service() -> tuple[MetadataCatalog, MetadataGroundingService]:
    catalog = MetadataCatalog(InMemoryMetadataRepository())
    load_east_china_revenue_sample(catalog)
    return catalog, MetadataGroundingService(catalog)


def test_grounding_assembles_cited_context_for_revenue_question() -> None:
    _, service = _service()

    result = service.ground(
        GroundingRequest(
            question="华东区本月收入为什么下降？",
            metric_query="营业收入",
            filters=(
                DimensionFilter(dimension_query="地区", value="华东区"),
                DimensionFilter(dimension_query="月份", value="本月"),
            ),
        )
    )

    assert tuple(item.asset_id for item in result.terms) == ("term.recognized_revenue",)
    assert result.metric.asset_id == "metric.revenue"
    assert tuple(item.asset_id for item in result.dimensions) == (
        "dimension.region",
        "dimension.order_month",
    )
    assert tuple(item.value for item in result.filters) == ("华东区", "本月")
    assert tuple(item.asset_id for item in result.warehouse_assets) == (
        "table.analytics.fact_order_line",
    )
    assert tuple(item.asset_id for item in result.entities) == ("entity.order",)
    assert tuple(item.asset_id for item in result.documents) == ("document.finance.revenue_policy",)
    assert result.evidence_ids == (
        "term.recognized_revenue",
        "metric.revenue",
        "dimension.region",
        "dimension.order_month",
        "table.analytics.fact_order_line",
        "entity.order",
        "document.finance.revenue_policy",
    )


def test_grounding_rejects_dimension_not_governed_for_metric() -> None:
    catalog, service = _service()
    catalog.register(
        Dimension(
            asset_id="dimension.employee",
            name="Employee",
            description="Employee responsible for an internal workflow.",
            aliases=("员工",),
            data_type="string",
        )
    )

    with pytest.raises(ValueError, match="not governed"):
        service.ground(
            GroundingRequest(
                question="按员工看收入",
                metric_query="营业收入",
                filters=(DimensionFilter(dimension_query="员工", value="张三"),),
            )
        )


def test_grounding_rejects_ambiguous_metric_alias() -> None:
    catalog, service = _service()
    for asset_id, name in (
        ("metric.gross_revenue", "Gross revenue"),
        ("metric.booked_revenue", "Booked revenue"),
    ):
        catalog.register(
            Metric(
                asset_id=asset_id,
                name=name,
                description=f"Experimental definition for {name}.",
                aliases=("冲突口径",),
                formula="sum(order_amount)",
                aggregation="sum",
            )
        )

    with pytest.raises(ValueError, match="ambiguous metric"):
        service.ground(
            GroundingRequest(
                question="冲突口径是多少？",
                metric_query="冲突口径",
            )
        )
