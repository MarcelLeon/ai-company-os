"""Two-session comparison for live-commerce diagnosis."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pydantic import Field

from sme_agent.commercialization.live_commerce_diagnosis import (
    LiveCommerceCsvLoader,
    LiveCommerceOrderRecord,
    LiveCommerceSessionRecord,
)
from sme_agent.domains import DomainFieldMappingService, build_live_commerce_template
from sme_agent.metadata.models import FrozenModel


class SessionMetricBreakdown(FrozenModel):
    live_session_id: str = Field(min_length=1)
    anchor_id: str = Field(min_length=1)
    category_l1: str = Field(min_length=1)
    live_room_view_count: int = Field(ge=0)
    paid_gmv: Decimal = Field(ge=Decimal("0"))
    pay_order_count: int = Field(ge=0)
    pay_buyer_count: int = Field(ge=0)
    average_order_value: Decimal = Field(ge=Decimal("0"))
    refund_amount: Decimal = Field(ge=Decimal("0"))
    refund_rate: Decimal = Field(ge=Decimal("0"))
    gpm: Decimal = Field(ge=Decimal("0"))
    payment_conversion_rate: Decimal = Field(ge=Decimal("0"))


class SkuContribution(FrozenModel):
    product_id: str = Field(min_length=1)
    baseline_paid_gmv: Decimal = Field(ge=Decimal("0"))
    comparison_paid_gmv: Decimal = Field(ge=Decimal("0"))
    paid_gmv_delta: Decimal
    baseline_refund_amount: Decimal = Field(ge=Decimal("0"))
    comparison_refund_amount: Decimal = Field(ge=Decimal("0"))


class SessionComparisonReport(FrozenModel):
    question: str = Field(min_length=1)
    baseline: SessionMetricBreakdown
    comparison: SessionMetricBreakdown
    metric_deltas: dict[str, str]
    sku_contributions: tuple[SkuContribution, ...]
    findings: tuple[str, ...]
    data_limits: tuple[str, ...]


class LiveCommerceComparisonRunner:
    """Compare two live sessions and explain the main deterministic drivers."""

    def run(
        self,
        *,
        question: str,
        live_sessions_csv: Path,
        orders_csv: Path,
        baseline_session_id: str | None = None,
        comparison_session_id: str | None = None,
    ) -> SessionComparisonReport:
        loader = LiveCommerceCsvLoader()
        mapping_report = DomainFieldMappingService().evaluate(
            build_live_commerce_template(),
            tuple(dict.fromkeys(loader.headers(live_sessions_csv) + loader.headers(orders_csv))),
        )
        sessions = loader.load_live_sessions(live_sessions_csv, mapping_report)
        orders = loader.load_orders(orders_csv, mapping_report)
        baseline_id, comparison_id = _session_ids(
            sessions, baseline_session_id, comparison_session_id
        )
        baseline = _session_breakdown(baseline_id, sessions, orders)
        comparison = _session_breakdown(comparison_id, sessions, orders)
        sku_contributions = _sku_contributions(baseline_id, comparison_id, orders)
        return SessionComparisonReport(
            question=question,
            baseline=baseline,
            comparison=comparison,
            metric_deltas=_metric_deltas(baseline, comparison),
            sku_contributions=sku_contributions,
            findings=_comparison_findings(baseline, comparison, sku_contributions),
            data_limits=(
                "当前样例没有地区、流量来源、活动/节日、世界杯、暑假、商品点击、加购和停留字段。",
                "因此只能做场次、主播、商品、订单、支付、退款归因，不能推断外部事件原因。",
            ),
        )


def comparison_to_payload(report: SessionComparisonReport) -> dict[str, object]:
    return {
        "question": report.question,
        "baseline": _breakdown_payload(report.baseline),
        "comparison": _breakdown_payload(report.comparison),
        "metric_deltas": report.metric_deltas,
        "sku_contributions": [
            {
                "product_id": item.product_id,
                "baseline_paid_gmv": str(item.baseline_paid_gmv),
                "comparison_paid_gmv": str(item.comparison_paid_gmv),
                "paid_gmv_delta": str(item.paid_gmv_delta),
                "baseline_refund_amount": str(item.baseline_refund_amount),
                "comparison_refund_amount": str(item.comparison_refund_amount),
            }
            for item in report.sku_contributions
        ],
        "findings": list(report.findings),
        "data_limits": list(report.data_limits),
    }


def _session_ids(
    sessions: tuple[LiveCommerceSessionRecord, ...],
    baseline_session_id: str | None,
    comparison_session_id: str | None,
) -> tuple[str, str]:
    session_ids = tuple(session.live_session_id for session in sessions)
    if len(session_ids) < 2:
        raise ValueError("至少需要两个直播场次才能做对比。")
    baseline_id = baseline_session_id or session_ids[0]
    comparison_id = comparison_session_id or session_ids[1]
    if baseline_id not in session_ids or comparison_id not in session_ids:
        raise ValueError("指定的直播场次不存在。")
    if baseline_id == comparison_id:
        raise ValueError("对比场次不能和基准场次相同。")
    return baseline_id, comparison_id


def _session_breakdown(
    live_session_id: str,
    sessions: tuple[LiveCommerceSessionRecord, ...],
    orders: tuple[LiveCommerceOrderRecord, ...],
) -> SessionMetricBreakdown:
    session = next(item for item in sessions if item.live_session_id == live_session_id)
    session_orders = tuple(order for order in orders if order.live_session_id == live_session_id)
    paid_orders = tuple(order for order in session_orders if _is_paid(order.payment_status))
    paid_gmv = sum((order.pay_amount for order in paid_orders), Decimal("0"))
    refund_amount = sum((order.refund_amount for order in paid_orders), Decimal("0"))
    pay_order_count = len({order.order_id for order in paid_orders})
    pay_buyer_count = len({order.buyer_id for order in paid_orders if order.buyer_id})
    return SessionMetricBreakdown(
        live_session_id=session.live_session_id,
        anchor_id=session.anchor_id,
        category_l1=session.category_l1,
        live_room_view_count=session.live_room_view_count,
        paid_gmv=paid_gmv,
        pay_order_count=pay_order_count,
        pay_buyer_count=pay_buyer_count,
        average_order_value=_money_ratio(paid_gmv, Decimal(pay_order_count)),
        refund_amount=refund_amount,
        refund_rate=_ratio(refund_amount, paid_gmv, Decimal("0.01")),
        gpm=_money_ratio(paid_gmv * Decimal("1000"), Decimal(session.live_room_view_count)),
        payment_conversion_rate=_ratio(
            Decimal(pay_buyer_count), Decimal(session.live_room_view_count), Decimal("0.0001")
        ),
    )


def _sku_contributions(
    baseline_session_id: str,
    comparison_session_id: str,
    orders: tuple[LiveCommerceOrderRecord, ...],
) -> tuple[SkuContribution, ...]:
    baseline = _sku_summary(baseline_session_id, orders)
    comparison = _sku_summary(comparison_session_id, orders)
    product_ids = tuple(sorted(set(baseline) | set(comparison)))
    contributions = tuple(
        SkuContribution(
            product_id=product_id,
            baseline_paid_gmv=baseline.get(product_id, _empty_sku())["paid_gmv"],
            comparison_paid_gmv=comparison.get(product_id, _empty_sku())["paid_gmv"],
            paid_gmv_delta=(
                comparison.get(product_id, _empty_sku())["paid_gmv"]
                - baseline.get(product_id, _empty_sku())["paid_gmv"]
            ),
            baseline_refund_amount=baseline.get(product_id, _empty_sku())["refund_amount"],
            comparison_refund_amount=comparison.get(product_id, _empty_sku())["refund_amount"],
        )
        for product_id in product_ids
    )
    return tuple(sorted(contributions, key=lambda item: item.paid_gmv_delta))


def _sku_summary(
    live_session_id: str,
    orders: tuple[LiveCommerceOrderRecord, ...],
) -> dict[str, dict[str, Decimal]]:
    summary: dict[str, dict[str, Decimal]] = {}
    for order in orders:
        if order.live_session_id != live_session_id or not _is_paid(order.payment_status):
            continue
        item = summary.setdefault(order.product_id, _empty_sku())
        item["paid_gmv"] += order.pay_amount
        item["refund_amount"] += order.refund_amount
    return summary


def _comparison_findings(
    baseline: SessionMetricBreakdown,
    comparison: SessionMetricBreakdown,
    sku_contributions: tuple[SkuContribution, ...],
) -> tuple[str, ...]:
    top_drops = tuple(item for item in sku_contributions if item.paid_gmv_delta < 0)[:3]
    findings = [
        (
            f"{comparison.live_session_id} 比 {baseline.live_session_id} 差，"
            f"核心是支付 GMV 从 {baseline.paid_gmv} 降到 {comparison.paid_gmv}，"
            f"GPM 从 {baseline.gpm} 降到 {comparison.gpm}。"
        )
    ]
    if comparison.pay_order_count == baseline.pay_order_count:
        findings.append(
            f"支付订单数仍是 {comparison.pay_order_count}，所以不是没人买，"
            "而是同样订单数卖出了更少的钱。"
        )
    if top_drops:
        drops = "、".join(f"{item.product_id} 少 {abs(item.paid_gmv_delta)}" for item in top_drops)
        findings.append(f"主要 SKU 拖累是：{drops}，这些解释了支付 GMV 的主要下降。")
    if comparison.refund_rate > baseline.refund_rate:
        findings.append(
            f"退款率从 {_percent(baseline.refund_rate)} 升到 "
            f"{_percent(comparison.refund_rate)}，成交质量也变差。"
        )
    findings.append(
        "下一步先查这些 SKU 是否改了价格、优惠券、补贴或支付口径；"
        "当前数据不足以归因到地区、节日、世界杯或暑假。"
    )
    return tuple(findings)


def _metric_deltas(
    baseline: SessionMetricBreakdown,
    comparison: SessionMetricBreakdown,
) -> dict[str, str]:
    return {
        "paid_gmv": str(comparison.paid_gmv - baseline.paid_gmv),
        "live_room_view_count": str(
            comparison.live_room_view_count - baseline.live_room_view_count
        ),
        "gpm": str(comparison.gpm - baseline.gpm),
        "pay_order_count": str(comparison.pay_order_count - baseline.pay_order_count),
        "pay_buyer_count": str(comparison.pay_buyer_count - baseline.pay_buyer_count),
        "average_order_value": str(comparison.average_order_value - baseline.average_order_value),
        "refund_rate": str(comparison.refund_rate - baseline.refund_rate),
        "payment_conversion_rate": str(
            comparison.payment_conversion_rate - baseline.payment_conversion_rate
        ),
    }


def _breakdown_payload(item: SessionMetricBreakdown) -> dict[str, str]:
    return {
        "live_session_id": item.live_session_id,
        "anchor_id": item.anchor_id,
        "category_l1": item.category_l1,
        "live_room_view_count": str(item.live_room_view_count),
        "paid_gmv": str(item.paid_gmv),
        "pay_order_count": str(item.pay_order_count),
        "pay_buyer_count": str(item.pay_buyer_count),
        "average_order_value": str(item.average_order_value),
        "refund_amount": str(item.refund_amount),
        "refund_rate": str(item.refund_rate),
        "gpm": str(item.gpm),
        "payment_conversion_rate": str(item.payment_conversion_rate),
    }


def _empty_sku() -> dict[str, Decimal]:
    return {"paid_gmv": Decimal("0"), "refund_amount": Decimal("0")}


def _is_paid(payment_status: str) -> bool:
    return payment_status.strip().lower() in {"paid", "已支付", "支付成功", "已付款"}


def _money_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    return _ratio(numerator, denominator, Decimal("0.01"))


def _ratio(numerator: Decimal, denominator: Decimal, quant: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
    return (numerator / denominator).quantize(quant)


def _percent(value: Decimal) -> str:
    percent = value * Decimal("100")
    if Decimal("0") < percent < Decimal("0.1"):
        return f"{percent.quantize(Decimal('0.01'))}%"
    return f"{percent.quantize(Decimal('0.1'))}%"
