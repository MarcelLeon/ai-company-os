from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Order:
    order_id: str
    date: str
    month: str
    region: str
    channel: str
    customer_id: str
    customer_segment: str
    product_id: str
    product_name: str
    gross_revenue: float
    paid_revenue: float
    status: str


@dataclass(frozen=True)
class AdSpend:
    month: str
    region: str
    channel: str
    spend: float


@dataclass(frozen=True)
class Refund:
    refund_id: str
    order_id: str
    month: str
    region: str
    product_id: str
    product_name: str
    customer_segment: str
    refund_amount: float
    reason: str


@dataclass(frozen=True)
class InventoryItem:
    product_id: str
    product_name: str
    on_hand_units: int
    unit_cost: float
    monthly_units_sold: int


@dataclass(frozen=True)
class Customer:
    customer_id: str
    region: str
    customer_segment: str
    industry: str


@dataclass(frozen=True)
class EnterpriseData:
    orders: tuple[Order, ...]
    ad_spend: tuple[AdSpend, ...]
    refunds: tuple[Refund, ...]
    inventory: tuple[InventoryItem, ...]
    customers: tuple[Customer, ...]


@dataclass(frozen=True)
class QueryResponse:
    intent: str
    answer: str
    evidence: tuple[str, ...]
    calculation: str
    sql: str
    caveats: tuple[str, ...]
    follow_up_questions: tuple[str, ...]
    facts: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
