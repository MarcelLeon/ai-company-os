from __future__ import annotations

import csv
from pathlib import Path

from data_agent_v1.models import AdSpend, Customer, EnterpriseData, InventoryItem, Order, Refund


def load_enterprise_data(sample_dir: Path) -> EnterpriseData:
    return EnterpriseData(
        orders=_load_orders(sample_dir / "orders.csv"),
        ad_spend=_load_ad_spend(sample_dir / "ad_spend.csv"),
        refunds=_load_refunds(sample_dir / "refunds.csv"),
        inventory=_load_inventory(sample_dir / "inventory.csv"),
        customers=_load_customers(sample_dir / "customers.csv"),
    )


def _rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _load_orders(path: Path) -> tuple[Order, ...]:
    return tuple(
        Order(
            order_id=row["order_id"],
            date=row["date"],
            month=row["month"],
            region=row["region"],
            channel=row["channel"],
            customer_id=row["customer_id"],
            customer_segment=row["customer_segment"],
            product_id=row["product_id"],
            product_name=row["product_name"],
            gross_revenue=float(row["gross_revenue"]),
            paid_revenue=float(row["paid_revenue"]),
            status=row["status"],
        )
        for row in _rows(path)
    )


def _load_ad_spend(path: Path) -> tuple[AdSpend, ...]:
    return tuple(
        AdSpend(
            month=row["month"],
            region=row["region"],
            channel=row["channel"],
            spend=float(row["spend"]),
        )
        for row in _rows(path)
    )


def _load_refunds(path: Path) -> tuple[Refund, ...]:
    return tuple(
        Refund(
            refund_id=row["refund_id"],
            order_id=row["order_id"],
            month=row["month"],
            region=row["region"],
            product_id=row["product_id"],
            product_name=row["product_name"],
            customer_segment=row["customer_segment"],
            refund_amount=float(row["refund_amount"]),
            reason=row["reason"],
        )
        for row in _rows(path)
    )


def _load_inventory(path: Path) -> tuple[InventoryItem, ...]:
    return tuple(
        InventoryItem(
            product_id=row["product_id"],
            product_name=row["product_name"],
            on_hand_units=int(row["on_hand_units"]),
            unit_cost=float(row["unit_cost"]),
            monthly_units_sold=int(row["monthly_units_sold"]),
        )
        for row in _rows(path)
    )


def _load_customers(path: Path) -> tuple[Customer, ...]:
    return tuple(
        Customer(
            customer_id=row["customer_id"],
            region=row["region"],
            customer_segment=row["customer_segment"],
            industry=row["industry"],
        )
        for row in _rows(path)
    )
