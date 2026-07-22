"""A small retail metadata graph for the first business-question contract."""

from __future__ import annotations

from sme_agent.metadata import (
    BusinessEntity,
    Dimension,
    GlossaryTerm,
    GovernanceStatus,
    KnowledgeDocument,
    MetadataCatalog,
    MetadataRelation,
    Metric,
    RelationKind,
    WarehouseAsset,
)


def load_east_china_revenue_sample(catalog: MetadataCatalog) -> None:
    assets = (
        GlossaryTerm(
            asset_id="term.recognized_revenue",
            name="Recognized revenue",
            description="Revenue recognized after an order is paid and not refunded.",
            aliases=("确认收入", "营业收入口径", "营业收入"),
            owner="finance",
            governance_status=GovernanceStatus.APPROVED,
            source_refs=("docs://finance/revenue-recognition#definition",),
            approved_by="finance-steward",
        ),
        Metric(
            asset_id="metric.revenue",
            name="Revenue",
            description="Recognized operating revenue from valid order lines.",
            aliases=("营业收入", "收入"),
            owner="finance",
            governance_status=GovernanceStatus.APPROVED,
            source_refs=("docs://finance/revenue-recognition#formula",),
            approved_by="finance-steward",
            formula="sum(net_order_amount)",
            aggregation="sum",
        ),
        Dimension(
            asset_id="dimension.region",
            name="Sales region",
            description="Management region assigned from the customer's province.",
            aliases=("地区", "区域"),
            owner="sales-ops",
            governance_status=GovernanceStatus.APPROVED,
            source_refs=("docs://sales/region-governance",),
            approved_by="sales-ops-steward",
            data_type="string",
        ),
        Dimension(
            asset_id="dimension.order_month",
            name="Order month",
            description="Calendar month derived from paid_at.",
            aliases=("月份", "订单月"),
            owner="finance",
            governance_status=GovernanceStatus.APPROVED,
            source_refs=("docs://finance/calendar",),
            approved_by="finance-steward",
            data_type="date_month",
        ),
        WarehouseAsset(
            asset_id="table.analytics.fact_order_line",
            name="Order line fact",
            description="One row per paid order line with refund adjustments.",
            owner="data",
            governance_status=GovernanceStatus.APPROVED,
            source_refs=("catalog://analytics.fact_order_line",),
            approved_by="data-steward",
            platform="postgres",
            qualified_name="analytics.fact_order_line",
        ),
        BusinessEntity(
            asset_id="entity.order",
            name="Order",
            description="A customer purchase with one or more order lines.",
            owner="commerce",
            governance_status=GovernanceStatus.APPROVED,
            source_refs=("docs://commerce/order-model",),
            approved_by="commerce-steward",
            identifier_fields=("order_id",),
        ),
        KnowledgeDocument(
            asset_id="document.finance.revenue_policy",
            name="Revenue recognition policy",
            description="Finance policy for payment, refund, and recognition timing.",
            aliases=("收入确认规则",),
            owner="finance",
            governance_status=GovernanceStatus.APPROVED,
            source_refs=("docs://finance/revenue-recognition",),
            approved_by="finance-steward",
            source_uri="docs://finance/revenue-recognition",
        ),
    )
    for asset in assets:
        catalog.register(asset)

    relations = (
        MetadataRelation(
            source_id="term.recognized_revenue",
            target_id="metric.revenue",
            kind=RelationKind.DEFINES,
        ),
        MetadataRelation(
            source_id="metric.revenue",
            target_id="dimension.region",
            kind=RelationKind.SLICED_BY,
        ),
        MetadataRelation(
            source_id="metric.revenue",
            target_id="dimension.order_month",
            kind=RelationKind.SLICED_BY,
        ),
        MetadataRelation(
            source_id="metric.revenue",
            target_id="table.analytics.fact_order_line",
            kind=RelationKind.SOURCED_FROM,
        ),
        MetadataRelation(
            source_id="table.analytics.fact_order_line",
            target_id="entity.order",
            kind=RelationKind.BELONGS_TO,
        ),
        MetadataRelation(
            source_id="metric.revenue",
            target_id="document.finance.revenue_policy",
            kind=RelationKind.DESCRIBED_BY,
        ),
        MetadataRelation(
            source_id="entity.order",
            target_id="document.finance.revenue_policy",
            kind=RelationKind.DESCRIBED_BY,
        ),
    )
    for relation in relations:
        catalog.connect(relation)
