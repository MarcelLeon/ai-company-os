"""First sellable ecommerce diagnosis slice.

The module intentionally stays deterministic. LLMs may polish wording later,
but paid delivery needs traceable calculations before prose.
"""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pydantic import Field

from sme_agent.metadata.models import FrozenModel


class OrderRecord(FrozenModel):
    order_id: str = Field(min_length=1)
    order_date: str = Field(min_length=1)
    region: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    quantity: int = Field(ge=0)
    gross_revenue: Decimal = Field(ge=Decimal("0"))
    refund_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class AdSpendRecord(FrozenModel):
    date: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    spend: Decimal = Field(ge=Decimal("0"))
    attributed_revenue: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class InventoryRecord(FrozenModel):
    sku: str = Field(min_length=1)
    stock_qty: int = Field(ge=0)
    units_sold_30d: int = Field(ge=0)
    unit_cost: Decimal = Field(ge=Decimal("0"))


class MetricSnapshot(FrozenModel):
    order_count: int = Field(ge=0)
    net_revenue: Decimal = Field(ge=Decimal("0"))
    refund_rate: Decimal = Field(ge=Decimal("0"))
    average_order_value: Decimal = Field(ge=Decimal("0"))
    ad_spend: Decimal = Field(ge=Decimal("0"))
    roas: Decimal | None = None
    slow_mover_count: int = Field(ge=0)
    inventory_value: Decimal = Field(ge=Decimal("0"))


class DiagnosisFinding(FrozenModel):
    title: str = Field(min_length=1)
    evidence: tuple[str, ...] = Field(min_length=1)
    recommended_action: str = Field(min_length=1)
    human_check: str = Field(min_length=1)


class EcommerceDiagnosisReport(FrozenModel):
    title: str = Field(min_length=1)
    primary_question: str = Field(min_length=1)
    metrics: MetricSnapshot
    findings: tuple[DiagnosisFinding, ...]
    required_human_checks: tuple[str, ...]
    disclaimers: tuple[str, ...]


class EcommerceCsvLoader:
    """Load the first supported CSV schemas for week-one service delivery."""

    def headers(self, path: Path) -> tuple[str, ...]:
        with path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            return tuple(reader.fieldnames or ())

    def load_orders(self, path: Path) -> tuple[OrderRecord, ...]:
        return tuple(
            OrderRecord(
                order_id=row["order_id"],
                order_date=row["order_date"],
                region=row["region"],
                channel=row["channel"],
                sku=row["sku"],
                quantity=self._int(row["quantity"], "quantity"),
                gross_revenue=self._money(row["gross_revenue"], "gross_revenue"),
                refund_amount=self._money(row.get("refund_amount", "0"), "refund_amount"),
            )
            for row in self._rows(path)
        )

    def load_ad_spend(self, path: Path) -> tuple[AdSpendRecord, ...]:
        return tuple(
            AdSpendRecord(
                date=row["date"],
                channel=row["channel"],
                spend=self._money(row["spend"], "spend"),
                attributed_revenue=self._money(
                    row.get("attributed_revenue", "0"), "attributed_revenue"
                ),
            )
            for row in self._rows(path)
        )

    def load_inventory(self, path: Path) -> tuple[InventoryRecord, ...]:
        return tuple(
            InventoryRecord(
                sku=row["sku"],
                stock_qty=self._int(row["stock_qty"], "stock_qty"),
                units_sold_30d=self._int(row["units_sold_30d"], "units_sold_30d"),
                unit_cost=self._money(row["unit_cost"], "unit_cost"),
            )
            for row in self._rows(path)
        )

    def _rows(self, path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as csv_file:
            return list(csv.DictReader(csv_file))

    def _int(self, value: str, field_name: str) -> int:
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an integer") from exc

    def _money(self, value: str, field_name: str) -> Decimal:
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise ValueError(f"{field_name} must be a decimal number") from exc


class EcommerceDiagnosisService:
    """Create a conservative diagnosis draft from buyer-provided tables."""

    def diagnose(
        self,
        *,
        primary_question: str,
        orders: tuple[OrderRecord, ...],
        ad_spend: tuple[AdSpendRecord, ...] = (),
        inventory: tuple[InventoryRecord, ...] = (),
    ) -> EcommerceDiagnosisReport:
        metrics = self._metrics(orders, ad_spend, inventory)
        findings = self._findings(metrics)
        return EcommerceDiagnosisReport(
            title="AI 电商经营诊断报告（人工复核草稿）",
            primary_question=primary_question,
            metrics=metrics,
            findings=findings,
            required_human_checks=(
                "确认收入口径是否为成交额减退款，是否包含未发货或预售订单。",
                "确认广告归因口径是否与店铺后台一致。",
                "确认库存成本和滞销判断是否符合当前行业季节性。",
            ),
            disclaimers=(
                "本报告基于客户提供样表生成，不能替代财务、税务、法律或投资建议。",
                "所有经营建议必须由店铺负责人结合实际业务复核后执行。",
                "涉及个人信息的数据应先脱敏或按最小必要字段提供。",
            ),
        )

    def _metrics(
        self,
        orders: tuple[OrderRecord, ...],
        ad_spend: tuple[AdSpendRecord, ...],
        inventory: tuple[InventoryRecord, ...],
    ) -> MetricSnapshot:
        gross_revenue = sum((order.gross_revenue for order in orders), Decimal("0"))
        refunds = sum((order.refund_amount for order in orders), Decimal("0"))
        net_revenue = max(gross_revenue - refunds, Decimal("0"))
        ad_cost = sum((item.spend for item in ad_spend), Decimal("0"))
        ad_revenue = sum((item.attributed_revenue for item in ad_spend), Decimal("0"))
        inventory_value = sum(
            (item.unit_cost * Decimal(item.stock_qty) for item in inventory), Decimal("0")
        )
        order_count = len({order.order_id for order in orders})
        return MetricSnapshot(
            order_count=order_count,
            net_revenue=net_revenue,
            refund_rate=self._ratio(refunds, gross_revenue),
            average_order_value=self._ratio(net_revenue, Decimal(order_count)),
            ad_spend=ad_cost,
            roas=self._ratio(ad_revenue, ad_cost) if ad_cost > 0 else None,
            slow_mover_count=len(self._slow_movers(inventory)),
            inventory_value=inventory_value,
        )

    def _findings(self, metrics: MetricSnapshot) -> tuple[DiagnosisFinding, ...]:
        findings: list[DiagnosisFinding] = []
        if metrics.refund_rate >= Decimal("0.08"):
            findings.append(
                DiagnosisFinding(
                    title="退款率偏高，需要先拆商品和渠道",
                    evidence=(f"样表退款率为 {self._percent(metrics.refund_rate)}。",),
                    recommended_action="先按商品、渠道、地区拆退款，再决定是商品质量、承诺不符还是投放人群问题。",
                    human_check="确认退款字段是否包含仅退款、退货退款和售后赔付。",
                )
            )
        if metrics.roas is not None and metrics.roas < Decimal("2.0"):
            findings.append(
                DiagnosisFinding(
                    title="广告 ROAS 偏低，不能只看消耗",
                    evidence=(f"样表广告 ROAS 为 {metrics.roas:.2f}。",),
                    recommended_action="把投放计划和商品毛利、退款、复购放在一起复核，先停掉低毛利低转化组合。",
                    human_check="确认广告成交金额是否包含自然流量或跨渠道重复归因。",
                )
            )
        if metrics.slow_mover_count > 0:
            findings.append(
                DiagnosisFinding(
                    title="存在疑似滞销库存",
                    evidence=(
                        f"样表中 {metrics.slow_mover_count} 个 SKU 近 30 天销量不足库存 10%。",
                    ),
                    recommended_action="先分出高毛利可促销、低毛利应清仓、季节性可保留三类库存。",
                    human_check="确认近 30 天销量是否覆盖所有销售渠道。",
                )
            )
        if not findings:
            findings.append(
                DiagnosisFinding(
                    title="当前样表未触发高风险规则",
                    evidence=("退款率、广告 ROAS、滞销库存未超过首版诊断阈值。",),
                    recommended_action="补充按周趋势和商品/渠道拆解后再做经营判断。",
                    human_check="确认样表时间范围是否足够代表最近经营变化。",
                )
            )
        return tuple(findings)

    def _slow_movers(self, inventory: tuple[InventoryRecord, ...]) -> tuple[InventoryRecord, ...]:
        return tuple(
            item
            for item in inventory
            if item.stock_qty > 0 and item.units_sold_30d / item.stock_qty < 0.1
        )

    def _ratio(self, numerator: Decimal, denominator: Decimal) -> Decimal:
        if denominator <= 0:
            return Decimal("0")
        return (numerator / denominator).quantize(Decimal("0.01"))

    def _percent(self, value: Decimal) -> str:
        return f"{(value * Decimal('100')).quantize(Decimal('0.1'))}%"


class EcommerceReportMarkdownRenderer:
    """Render a buyer-facing draft that remains clear about human review."""

    def render(self, report: EcommerceDiagnosisReport) -> str:
        lines = [
            f"# {report.title}",
            "",
            f"客户问题：{report.primary_question}",
            "",
            "## 关键指标",
            f"- 订单数：{report.metrics.order_count}",
            f"- 净收入：{report.metrics.net_revenue}",
            f"- 退款率：{report.metrics.refund_rate}",
            f"- 客单价：{report.metrics.average_order_value}",
            f"- 广告消耗：{report.metrics.ad_spend}",
            f"- 广告 ROAS：{self._roas_text(report)}",
            f"- 疑似滞销 SKU 数：{report.metrics.slow_mover_count}",
            f"- 库存成本估值：{report.metrics.inventory_value}",
            "",
            "## 诊断发现",
        ]
        for index, finding in enumerate(report.findings, start=1):
            lines.extend(self._finding_lines(index, finding))
        lines.extend(["", "## 必须人工确认", *self._bullets(report.required_human_checks)])
        lines.extend(["", "## 边界声明", *self._bullets(report.disclaimers)])
        return "\n".join(lines)

    def _finding_lines(self, index: int, finding: DiagnosisFinding) -> list[str]:
        return [
            f"### {index}. {finding.title}",
            "",
            "证据：",
            *self._bullets(finding.evidence),
            "",
            f"建议动作：{finding.recommended_action}",
            "",
            f"人工确认：{finding.human_check}",
            "",
        ]

    def _bullets(self, values: tuple[str, ...]) -> list[str]:
        return [f"- {value}" for value in values]

    def _roas_text(self, report: EcommerceDiagnosisReport) -> str:
        return str(report.metrics.roas) if report.metrics.roas is not None else "无广告数据"
