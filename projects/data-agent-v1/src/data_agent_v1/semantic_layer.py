from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    label: str
    formula: str
    source: str
    ambiguity_rule: str


METRICS: dict[str, MetricDefinition] = {
    "paid_revenue": MetricDefinition(
        metric_id="paid_revenue",
        label="Paid revenue",
        formula="sum(orders.paid_revenue) where status = 'paid'",
        source="orders.csv",
        ambiguity_rule="Ask for time period and scope when missing.",
    ),
    "refund_rate": MetricDefinition(
        metric_id="refund_rate",
        label="Refund rate",
        formula="sum(refunds.refund_amount) / sum(orders.paid_revenue)",
        source="orders.csv + refunds.csv",
        ambiguity_rule="Ask whether to use paid revenue, gross revenue, or order count.",
    ),
    "roas": MetricDefinition(
        metric_id="roas",
        label="Advertising ROAS",
        formula="paid revenue attributed to channel / ad spend",
        source="orders.csv + ad_spend.csv",
        ambiguity_rule="Ask for attribution window when missing in real data.",
    ),
    "inventory_months": MetricDefinition(
        metric_id="inventory_months",
        label="Inventory months of cover",
        formula="inventory.on_hand_units / inventory.monthly_units_sold",
        source="inventory.csv",
        ambiguity_rule="Ask whether sales velocity should use 7d, 30d, or seasonal run rate.",
    ),
}


DIMENSIONS = {
    "month": "Calendar month in YYYY-MM format.",
    "region": "Business sales region.",
    "channel": "Acquisition or selling channel.",
    "product": "Product identifier and name.",
    "customer_segment": "Customer lifecycle or value segment.",
}


SOURCE_AUTHORITY = {
    "orders.csv": "Paid revenue and channel/product/customer aggregates.",
    "refunds.csv": "Refund amount, product refund contribution, and refund reasons.",
    "ad_spend.csv": "Channel-level ad spend for ROAS.",
    "inventory.csv": "On-hand units and monthly units sold.",
    "customers.csv": "Customer segment and industry metadata.",
}
