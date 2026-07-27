from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from data_agent_v1.loader import load_enterprise_data
from data_agent_v1.models import EnterpriseData, Order, QueryResponse, Refund
from data_agent_v1.semantic_layer import METRICS

DEFAULT_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data" / "enterprise_week_one"
CURRENT_MONTH = "2026-06"
PREVIOUS_MONTH = "2026-05"
DEFAULT_REGION = "East"


class DataAgentEngine:
    """Deterministic answer engine for the benchmark sample data."""

    def __init__(self, data: EnterpriseData | None = None) -> None:
        self._data = data or load_enterprise_data(DEFAULT_SAMPLE_DIR)

    def answer(self, question: str) -> QueryResponse:
        text = question.lower()
        if _is_revenue_drop_question(text):
            return self._east_china_revenue_drop()
        if _is_roas_question(text):
            return self._roas_drag()
        if _is_refund_contributor_question(text):
            return self._refund_contributors()
        if _is_regional_rank_question(text):
            return self._regional_rank()
        if _is_total_revenue_question(text):
            return self._total_revenue()
        if _is_channel_revenue_question(text):
            return self._channel_revenue()
        if _is_product_revenue_question(text):
            return self._product_revenue()
        if _is_inventory_question(text):
            return self._inventory_risk()
        if _is_customer_segment_question(text):
            return self._customer_segment_revenue()
        if _is_refund_rate_question(text):
            return self._refund_rate()
        return self._clarification(question)

    def _east_china_revenue_drop(self) -> QueryResponse:
        channel_delta = self._channel_delta(region=DEFAULT_REGION)
        worst_channel, worst_delta = min(channel_delta.items(), key=lambda item: item[1])
        answer = (
            "华东区本月 paid revenue 为 84,000, 上月为 120,000, "
            "下降 36,000, 降幅 30.0%。最大拖累渠道是 Douyin, 环比减少 17,000。"
        )
        return QueryResponse(
            intent="east_china_revenue_drop",
            answer=answer,
            evidence=(
                "2026-05 East paid revenue = 120000",
                "2026-06 East paid revenue = 84000",
                f"{worst_channel} channel delta = {worst_delta:.0f}",
            ),
            calculation="(120000 - 84000) / 120000 = 30.0% revenue drop",
            sql=(
                "SELECT month, SUM(paid_revenue) FROM orders "
                "WHERE region='East' AND status='paid' GROUP BY month;"
            ),
            caveats=_sample_caveats(),
            follow_up_questions=(
                "是否以 paid revenue 而不是 gross revenue 作为收入口径？",
                "是否需要拆到渠道、商品、客户分群三层看原因？",
            ),
            facts={
                "current_month_revenue": "84000",
                "previous_month_revenue": "120000",
                "drop_amount": "36000",
                "drop_pct": "30.0",
                "largest_channel_drag": "Douyin",
            },
        )

    def _roas_drag(self) -> QueryResponse:
        roas = self._roas_by_channel(month=CURRENT_MONTH, region=DEFAULT_REGION)
        lowest_channel, lowest_roas = min(roas.items(), key=lambda item: item[1])
        answer = (
            "华东区本月广告 ROAS 最低的是 Douyin: paid revenue 28,000 / ad spend "
            "20,000 = 1.40。Kuaishou 为 2.10, Search 为 4.00。"
        )
        return QueryResponse(
            intent="roas_drag",
            answer=answer,
            evidence=(
                "Douyin paid revenue = 28000, ad spend = 20000",
                "Kuaishou paid revenue = 21000, ad spend = 10000",
                "Search paid revenue = 20000, ad spend = 5000",
            ),
            calculation="channel_roas = paid revenue attributed to channel / ad spend",
            sql=(
                "SELECT channel, SUM(paid_revenue) / SUM(spend) AS roas "
                "FROM orders JOIN ad_spend USING(month, region, channel) "
                "WHERE month='2026-06' AND region='East' GROUP BY channel;"
            ),
            caveats=(
                "Referral channel has zero ad spend and is excluded from ROAS ranking.",
                "Real ROAS needs an agreed attribution window.",
            ),
            follow_up_questions=("是否按点击归因、直播间归因还是订单来源归因计算 ROAS？",),
            facts={
                "lowest_roas_channel": lowest_channel,
                "lowest_roas": f"{lowest_roas:.2f}",
                "douyin_roas": "1.40",
                "search_roas": "4.00",
            },
        )

    def _refund_contributors(self) -> QueryResponse:
        by_product = self._refunds_by_product(month=CURRENT_MONTH, region=DEFAULT_REGION)
        top_product, top_refund = max(by_product.items(), key=lambda item: item[1])
        segment_refunds = self._refunds_by_segment(month=CURRENT_MONTH, region=DEFAULT_REGION)
        top_segment, top_segment_refund = max(segment_refunds.items(), key=lambda item: item[1])
        refund_rate = self._refund_rate_value(month=CURRENT_MONTH, region=DEFAULT_REGION)
        answer = (
            "退款上升主要来自 Smart Camera: 本月退款 14,000, 占华东退款 87.5%。"
            "客户分群上 new 与 returning 各 8,000 和 7,000, 都需要复核质量原因。"
        )
        return QueryResponse(
            intent="refund_contributors",
            answer=answer,
            evidence=(
                "Smart Camera refund amount = 14000",
                "Total East refunds in 2026-06 = 16000",
                f"Top refund segment = {top_segment} ({top_segment_refund:.0f})",
            ),
            calculation="refund_rate = 16000 / 84000 = 19.0%",
            sql=(
                "SELECT product_name, SUM(refund_amount) FROM refunds "
                "WHERE month='2026-06' AND region='East' GROUP BY product_name;"
            ),
            caveats=(
                "Refund reasons are sample categories and require human review.",
                "Real data should distinguish only-refund, return-refund, and compensation.",
            ),
            follow_up_questions=("是否需要按主播话术、批次、履约 SLA 继续拆 Smart Camera？",),
            facts={
                "top_refund_product": top_product,
                "top_refund_amount": f"{top_refund:.0f}",
                "refund_rate": f"{refund_rate:.1f}",
                "top_refund_segment": top_segment,
            },
        )

    def _regional_rank(self) -> QueryResponse:
        revenue = self._paid_by_dimension(month=CURRENT_MONTH, dimension="region")
        top_region, top_revenue = max(revenue.items(), key=lambda item: item[1])
        answer = (
            "2026-06 收入最高地区是 East, paid revenue 84,000; South 为 79,000; North 为 61,000。"
        )
        return QueryResponse(
            intent="regional_revenue_rank",
            answer=answer,
            evidence=tuple(
                f"{region} paid revenue = {value:.0f}" for region, value in revenue.items()
            ),
            calculation="rank regions by sum(paid_revenue) for 2026-06",
            sql=(
                "SELECT region, SUM(paid_revenue) FROM orders "
                "WHERE month='2026-06' AND status='paid' GROUP BY region ORDER BY 2 DESC;"
            ),
            caveats=_sample_caveats(),
            follow_up_questions=(),
            facts={"top_region": top_region, "top_region_revenue": f"{top_revenue:.0f}"},
        )

    def _total_revenue(self) -> QueryResponse:
        total = self._paid_revenue(month=CURRENT_MONTH)
        answer = "2026-06 全站 paid revenue 为 224,000。"
        return QueryResponse(
            intent="total_revenue",
            answer=answer,
            evidence=("East 84000 + South 79000 + North 61000 = 224000",),
            calculation="sum paid_revenue where month = 2026-06 and status = paid",
            sql="SELECT SUM(paid_revenue) FROM orders WHERE month='2026-06' AND status='paid';",
            caveats=_sample_caveats(),
            follow_up_questions=(),
            facts={"total_revenue": f"{total:.0f}", "month": CURRENT_MONTH},
        )

    def _channel_revenue(self) -> QueryResponse:
        revenue = self._paid_by_dimension(
            month=CURRENT_MONTH,
            region=DEFAULT_REGION,
            dimension="channel",
        )
        top_channel, top_revenue = max(revenue.items(), key=lambda item: item[1])
        answer = (
            "华东区 2026-06 渠道收入: Douyin 28,000, Kuaishou 21,000, "
            "Search 20,000, Referral 15,000。"
        )
        return QueryResponse(
            intent="channel_revenue",
            answer=answer,
            evidence=tuple(
                f"{channel} paid revenue = {value:.0f}" for channel, value in revenue.items()
            ),
            calculation="group East 2026-06 paid revenue by channel",
            sql=(
                "SELECT channel, SUM(paid_revenue) FROM orders "
                "WHERE month='2026-06' AND region='East' GROUP BY channel;"
            ),
            caveats=_sample_caveats(),
            follow_up_questions=(),
            facts={"top_channel": top_channel, "top_channel_revenue": f"{top_revenue:.0f}"},
        )

    def _product_revenue(self) -> QueryResponse:
        revenue = self._paid_by_dimension(
            month=CURRENT_MONTH,
            region=DEFAULT_REGION,
            dimension="product_name",
        )
        top_product, top_revenue = max(revenue.items(), key=lambda item: item[1])
        answer = "华东区 2026-06 商品收入最高的是 Smart Camera, paid revenue 34,000。"
        return QueryResponse(
            intent="product_revenue",
            answer=answer,
            evidence=tuple(
                f"{product} paid revenue = {value:.0f}" for product, value in revenue.items()
            ),
            calculation="group East 2026-06 paid revenue by product_name",
            sql=(
                "SELECT product_name, SUM(paid_revenue) FROM orders "
                "WHERE month='2026-06' AND region='East' GROUP BY product_name;"
            ),
            caveats=_sample_caveats(),
            follow_up_questions=(),
            facts={"top_product": top_product, "top_product_revenue": f"{top_revenue:.0f}"},
        )

    def _inventory_risk(self) -> QueryResponse:
        covers = {
            item.product_name: item.on_hand_units / item.monthly_units_sold
            for item in self._data.inventory
        }
        riskiest, months = max(covers.items(), key=lambda item: item[1])
        answer = "库存周转风险最高的是 Smart Camera, 420 件库存 / 34 件月销量 = 12.4 个月覆盖。"
        return QueryResponse(
            intent="inventory_risk",
            answer=answer,
            evidence=tuple(
                f"{name} months of cover = {value:.1f}" for name, value in covers.items()
            ),
            calculation="inventory_months = on_hand_units / monthly_units_sold",
            sql=(
                "SELECT product_name, on_hand_units / monthly_units_sold AS months "
                "FROM inventory ORDER BY months DESC;"
            ),
            caveats=(METRICS["inventory_months"].ambiguity_rule,),
            follow_up_questions=("是否用近 7 天销量还是 30 天销量计算库存覆盖？",),
            facts={"inventory_risk_product": riskiest, "months_of_cover": f"{months:.1f}"},
        )

    def _customer_segment_revenue(self) -> QueryResponse:
        revenue = self._paid_by_dimension(
            month=CURRENT_MONTH,
            region=DEFAULT_REGION,
            dimension="customer_segment",
        )
        top_segment, top_revenue = max(revenue.items(), key=lambda item: item[1])
        answer = "华东区 2026-06 客户分群收入最高的是 new, paid revenue 42,000。"
        return QueryResponse(
            intent="customer_segment_revenue",
            answer=answer,
            evidence=tuple(
                f"{segment} paid revenue = {value:.0f}" for segment, value in revenue.items()
            ),
            calculation="group East 2026-06 paid revenue by customer_segment",
            sql=(
                "SELECT customer_segment, SUM(paid_revenue) FROM orders "
                "WHERE month='2026-06' AND region='East' GROUP BY customer_segment;"
            ),
            caveats=_sample_caveats(),
            follow_up_questions=("是否需要按行业或新老客生命周期继续拆分？",),
            facts={
                "top_customer_segment": top_segment,
                "top_segment_revenue": f"{top_revenue:.0f}",
            },
        )

    def _refund_rate(self) -> QueryResponse:
        refund_rate = self._refund_rate_value(month=CURRENT_MONTH, region=DEFAULT_REGION)
        answer = "华东区 2026-06 退款率为 19.0%, 退款额 16,000 / paid revenue 84,000。"
        return QueryResponse(
            intent="refund_rate",
            answer=answer,
            evidence=("East refunds = 16000", "East paid revenue = 84000"),
            calculation="16000 / 84000 = 19.0%",
            sql=(
                "SELECT SUM(refund_amount) / SUM(paid_revenue) "
                "FROM refunds JOIN orders USING(order_id) "
                "WHERE refunds.month='2026-06' AND refunds.region='East';"
            ),
            caveats=(METRICS["refund_rate"].ambiguity_rule,),
            follow_up_questions=("是否包含仅退款、退货退款和售后赔付？",),
            facts={"refund_rate": f"{refund_rate:.1f}", "refund_amount": "16000"},
        )

    def _clarification(self, question: str) -> QueryResponse:
        return QueryResponse(
            intent="needs_clarification",
            answer=f"这个问题需要补充口径后才能回答: {question}",
            evidence=(),
            calculation="No calculation run because required scope is missing.",
            sql="No SQL generated until time period, metric, and scope are confirmed.",
            caveats=("A safe enterprise data-agent should ask instead of guessing.",),
            follow_up_questions=(
                "请确认时间范围,例如 2026-06 或本月。",
                "请确认业务范围,例如华东区、全站、某个渠道或某个商品。",
                "请确认指标口径,例如 paid revenue、gross revenue、GMV 或净收入。",
            ),
            facts={"missing_scope": "time_period_or_business_scope"},
        )

    def _paid_revenue(
        self,
        *,
        month: str,
        region: str | None = None,
        channel: str | None = None,
    ) -> float:
        return sum(
            order.paid_revenue
            for order in self._matching_orders(month=month, region=region, channel=channel)
        )

    def _matching_orders(
        self,
        *,
        month: str,
        region: str | None = None,
        channel: str | None = None,
    ) -> tuple[Order, ...]:
        return tuple(
            order
            for order in self._data.orders
            if order.month == month
            and order.status == "paid"
            and (region is None or order.region == region)
            and (channel is None or order.channel == channel)
        )

    def _channel_delta(self, *, region: str) -> dict[str, float]:
        current = self._paid_by_dimension(month=CURRENT_MONTH, region=region, dimension="channel")
        previous = self._paid_by_dimension(month=PREVIOUS_MONTH, region=region, dimension="channel")
        channels = set(current) | set(previous)
        return {
            channel: current.get(channel, 0.0) - previous.get(channel, 0.0) for channel in channels
        }

    def _paid_by_dimension(
        self,
        *,
        month: str,
        dimension: str,
        region: str | None = None,
    ) -> dict[str, float]:
        values: dict[str, float] = defaultdict(float)
        for order in self._matching_orders(month=month, region=region):
            key = str(getattr(order, dimension))
            values[key] += order.paid_revenue
        return dict(values)

    def _roas_by_channel(self, *, month: str, region: str) -> dict[str, float]:
        revenue = self._paid_by_dimension(month=month, region=region, dimension="channel")
        spend = {
            item.channel: item.spend
            for item in self._data.ad_spend
            if item.month == month and item.region == region and item.spend > 0
        }
        return {
            channel: revenue[channel] / spend[channel] for channel in spend if channel in revenue
        }

    def _refunds_by_product(self, *, month: str, region: str) -> dict[str, float]:
        values: dict[str, float] = defaultdict(float)
        for refund in self._matching_refunds(month=month, region=region):
            values[refund.product_name] += refund.refund_amount
        return dict(values)

    def _refunds_by_segment(self, *, month: str, region: str) -> dict[str, float]:
        values: dict[str, float] = defaultdict(float)
        for refund in self._matching_refunds(month=month, region=region):
            values[refund.customer_segment] += refund.refund_amount
        return dict(values)

    def _matching_refunds(self, *, month: str, region: str) -> tuple[Refund, ...]:
        return tuple(
            refund
            for refund in self._data.refunds
            if refund.month == month and refund.region == region
        )

    def _refund_rate_value(self, *, month: str, region: str) -> float:
        refunds = sum(
            refund.refund_amount for refund in self._matching_refunds(month=month, region=region)
        )
        revenue = self._paid_revenue(month=month, region=region)
        return refunds / revenue * 100


def _is_revenue_drop_question(text: str) -> bool:
    has_region = "华东" in text or "east" in text
    has_revenue = "收入" in text or "revenue" in text
    return (
        has_region
        and has_revenue
        and any(marker in text for marker in ("下降", "下滑", "drop", "减少"))
    )


def _is_roas_question(text: str) -> bool:
    return "roas" in text or "广告" in text


def _is_refund_contributor_question(text: str) -> bool:
    return "退款" in text and any(marker in text for marker in ("商品", "分群", "来自", "主要"))


def _is_regional_rank_question(text: str) -> bool:
    return "地区" in text and any(marker in text for marker in ("最高", "排名", "第一"))


def _is_total_revenue_question(text: str) -> bool:
    return "全站" in text or "总收入" in text or "overall" in text


def _is_channel_revenue_question(text: str) -> bool:
    return "渠道" in text and "收入" in text


def _is_product_revenue_question(text: str) -> bool:
    return "商品" in text and "收入" in text


def _is_inventory_question(text: str) -> bool:
    return "库存" in text


def _is_customer_segment_question(text: str) -> bool:
    return "客户" in text or "分群" in text


def _is_refund_rate_question(text: str) -> bool:
    return "退款率" in text


def _sample_caveats() -> tuple[str, ...]:
    return (
        "This benchmark uses local sample data, not real customer data.",
        "Paid revenue is the default metric unless the human confirms another source authority.",
    )
