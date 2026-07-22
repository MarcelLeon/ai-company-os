"""Template-backed live/content commerce diagnosis.

This slice is intentionally deterministic. It answers the first commercial
validation question: can a Douyin/Kuaishou-style merchant export be mapped to a
business template and produce traceable metrics before any LLM prose is added?
"""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path

from pydantic import Field

from sme_agent.domains import (
    DomainFieldMappingService,
    FieldMappingReport,
    build_live_commerce_template,
)
from sme_agent.metadata.models import FrozenModel


class LiveCommerceSessionRecord(FrozenModel):
    category_l1: str = Field(min_length=1)
    shop_id: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    live_session_id: str = Field(min_length=1)
    anchor_id: str = Field(min_length=1)
    live_room_view_count: int = Field(ge=0)


LiveSessionRecord = LiveCommerceSessionRecord


class LiveCommerceOrderRecord(FrozenModel):
    category_l1: str = Field(min_length=1)
    shop_id: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    live_session_id: str = Field(min_length=1)
    order_gross_amount: Decimal = Field(ge=Decimal("0"))
    payment_status: str = Field(min_length=1)
    pay_amount: Decimal = Field(ge=Decimal("0"))
    refund_amount: Decimal = Field(ge=Decimal("0"))
    buyer_id: str = Field(min_length=1)


class LiveCommerceMetricSnapshot(FrozenModel):
    gmv: Decimal = Field(ge=Decimal("0"))
    paid_gmv: Decimal = Field(ge=Decimal("0"))
    pay_order_count: int = Field(ge=0)
    pay_buyer_count: int = Field(ge=0)
    average_order_value: Decimal = Field(ge=Decimal("0"))
    refund_rate: Decimal = Field(ge=Decimal("0"))
    gpm: Decimal = Field(ge=Decimal("0"))
    payment_conversion_rate: Decimal = Field(ge=Decimal("0"))
    live_room_view_count: int = Field(ge=0)


class LiveCommerceFinding(FrozenModel):
    title: str = Field(min_length=1)
    evidence: tuple[str, ...] = Field(min_length=1)
    recommended_action: str = Field(min_length=1)
    human_check: str = Field(min_length=1)


class LiveCommerceDiagnosisReport(FrozenModel):
    title: str = Field(min_length=1)
    primary_question: str = Field(min_length=1)
    mapping_report: FieldMappingReport
    metrics: LiveCommerceMetricSnapshot
    findings: tuple[LiveCommerceFinding, ...]
    required_human_checks: tuple[str, ...]
    disclaimers: tuple[str, ...]


class LiveCommerceCsvLoader:
    """Load mapped live-session and order exports."""

    def headers(self, path: Path) -> tuple[str, ...]:
        with path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            return tuple(reader.fieldnames or ())

    def headers_from_text(self, content: str) -> tuple[str, ...]:
        reader = csv.DictReader(StringIO(content.lstrip("\ufeff")))
        return tuple(reader.fieldnames or ())

    def load_live_sessions(
        self, path: Path, mapping_report: FieldMappingReport
    ) -> tuple[LiveCommerceSessionRecord, ...]:
        return self.load_live_session_rows(_rows(path), mapping_report)

    def load_live_sessions_text(
        self, content: str, mapping_report: FieldMappingReport
    ) -> tuple[LiveCommerceSessionRecord, ...]:
        return self.load_live_session_rows(_rows_from_text(content), mapping_report)

    def load_live_session_rows(
        self,
        rows: list[dict[str, str]],
        mapping_report: FieldMappingReport,
    ) -> tuple[LiveCommerceSessionRecord, ...]:
        return tuple(
            LiveCommerceSessionRecord(
                category_l1=_value(row, mapping_report, "category_l1"),
                shop_id=_value(row, mapping_report, "shop_id"),
                platform=_value(row, mapping_report, "platform"),
                live_session_id=_value(row, mapping_report, "live_session_id"),
                anchor_id=_value(row, mapping_report, "anchor_id"),
                live_room_view_count=_int(
                    _value(row, mapping_report, "live_room_view_count"),
                    "live_room_view_count",
                ),
            )
            for row in rows
        )

    def load_orders(
        self, path: Path, mapping_report: FieldMappingReport
    ) -> tuple[LiveCommerceOrderRecord, ...]:
        return self.load_order_rows(_rows(path), mapping_report)

    def load_orders_text(
        self, content: str, mapping_report: FieldMappingReport
    ) -> tuple[LiveCommerceOrderRecord, ...]:
        return self.load_order_rows(_rows_from_text(content), mapping_report)

    def load_order_rows(
        self,
        rows: list[dict[str, str]],
        mapping_report: FieldMappingReport,
    ) -> tuple[LiveCommerceOrderRecord, ...]:
        return tuple(self._order_record(row, mapping_report) for row in rows)

    def _order_record(
        self,
        row: dict[str, str],
        mapping_report: FieldMappingReport,
    ) -> LiveCommerceOrderRecord:
        payment_status = _value(row, mapping_report, "payment_status")
        pay_amount = _value(row, mapping_report, "pay_amount")
        if _is_paid(payment_status) and not pay_amount.strip():
            live_session_id = _value(row, mapping_report, "live_session_id")
            order_id = _value(row, mapping_report, "order_id")
            product_id = _value(row, mapping_report, "product_id")
            raise ValueError(
                "支付金额缺失："
                f"场次 {live_session_id} 订单 {order_id} 商品 {product_id} "
                "为已支付，但 pay_amount/支付金额为空。"
            )
        return LiveCommerceOrderRecord(
            category_l1=_value(row, mapping_report, "category_l1"),
            shop_id=_value(row, mapping_report, "shop_id"),
            platform=_value(row, mapping_report, "platform"),
            product_id=_value(row, mapping_report, "product_id"),
            order_id=_value(row, mapping_report, "order_id"),
            live_session_id=_value(row, mapping_report, "live_session_id"),
            order_gross_amount=_money(
                _value(row, mapping_report, "order_gross_amount"),
                "order_gross_amount",
            ),
            payment_status=payment_status,
            pay_amount=_money(pay_amount, "pay_amount"),
            refund_amount=_money(
                _value(row, mapping_report, "refund_amount", "0"),
                "refund_amount",
            ),
            buyer_id=_value(row, mapping_report, "buyer_id", "unknown"),
        )


class LiveCommerceDiagnosisRunner:
    """Map customer exports, compute metrics, and produce a reviewable report."""

    def run(
        self,
        *,
        primary_question: str,
        live_sessions_csv: Path,
        orders_csv: Path,
    ) -> LiveCommerceDiagnosisReport:
        loader = LiveCommerceCsvLoader()
        mapping_report = DomainFieldMappingService().evaluate(
            build_live_commerce_template(),
            tuple(dict.fromkeys(loader.headers(live_sessions_csv) + loader.headers(orders_csv))),
        )
        live_sessions = loader.load_live_sessions(live_sessions_csv, mapping_report)
        orders = loader.load_orders(orders_csv, mapping_report)
        return self._build_report(primary_question, mapping_report, live_sessions, orders)

    def run_text(
        self,
        *,
        primary_question: str,
        live_sessions_csv: str,
        orders_csv: str,
    ) -> LiveCommerceDiagnosisReport:
        """Run the same governed diagnosis against non-persistent CSV text."""
        loader = LiveCommerceCsvLoader()
        mapping_report = DomainFieldMappingService().evaluate(
            build_live_commerce_template(),
            tuple(
                dict.fromkeys(
                    loader.headers_from_text(live_sessions_csv)
                    + loader.headers_from_text(orders_csv)
                )
            ),
        )
        live_sessions = loader.load_live_sessions_text(live_sessions_csv, mapping_report)
        orders = loader.load_orders_text(orders_csv, mapping_report)
        return self._build_report(primary_question, mapping_report, live_sessions, orders)

    @staticmethod
    def _build_report(
        primary_question: str,
        mapping_report: FieldMappingReport,
        live_sessions: tuple[LiveCommerceSessionRecord, ...],
        orders: tuple[LiveCommerceOrderRecord, ...],
    ) -> LiveCommerceDiagnosisReport:
        metrics = LiveCommerceDiagnosisService().metrics(live_sessions, orders)
        return LiveCommerceDiagnosisReport(
            title="直播电商经营诊断报告（人工复核草稿）",
            primary_question=primary_question,
            mapping_report=mapping_report,
            metrics=metrics,
            findings=LiveCommerceDiagnosisService().findings(metrics, live_sessions, orders),
            required_human_checks=(
                "确认平台 GMV 是否包含未支付、取消或退款订单。",
                "确认观看人数口径是曝光、进入直播间还是有效观看。",
                "确认支付金额是否包含运费、优惠券、平台补贴。",
                "确认 buyer_id 已替换为不可逆匿名 ID。",
            ),
            disclaimers=(
                "本报告基于客户提供样表生成，不能替代财务、税务、法律或投资建议。",
                "所有经营建议必须由店铺负责人结合实际业务复核后执行。",
                "平台口径、归因周期和退款口径未确认前，不应直接用于绩效奖惩。",
            ),
        )


class LiveCommerceDiagnosisService:
    """Compute live-commerce metrics from normalized records."""

    def metrics(
        self,
        live_sessions: tuple[LiveCommerceSessionRecord, ...],
        orders: tuple[LiveCommerceOrderRecord, ...],
    ) -> LiveCommerceMetricSnapshot:
        paid_orders = tuple(order for order in orders if _is_paid(order.payment_status))
        gmv = sum((order.order_gross_amount for order in orders), Decimal("0"))
        paid_gmv = sum((order.pay_amount for order in paid_orders), Decimal("0"))
        refund_amount = sum((order.refund_amount for order in paid_orders), Decimal("0"))
        pay_order_count = len({order.order_id for order in paid_orders})
        pay_buyer_count = len({order.buyer_id for order in paid_orders if order.buyer_id})
        live_room_view_count = sum(session.live_room_view_count for session in live_sessions)
        return LiveCommerceMetricSnapshot(
            gmv=gmv,
            paid_gmv=paid_gmv,
            pay_order_count=pay_order_count,
            pay_buyer_count=pay_buyer_count,
            average_order_value=_money_ratio(paid_gmv, Decimal(pay_order_count)),
            refund_rate=_ratio(refund_amount, paid_gmv, Decimal("0.01")),
            gpm=_money_ratio(paid_gmv * Decimal("1000"), Decimal(live_room_view_count)),
            payment_conversion_rate=_ratio(
                Decimal(pay_buyer_count), Decimal(live_room_view_count), Decimal("0.0001")
            ),
            live_room_view_count=live_room_view_count,
        )

    def findings(
        self,
        metrics: LiveCommerceMetricSnapshot,
        live_sessions: tuple[LiveCommerceSessionRecord, ...],
        orders: tuple[LiveCommerceOrderRecord, ...],
    ) -> tuple[LiveCommerceFinding, ...]:
        findings: list[LiveCommerceFinding] = []
        if metrics.refund_rate >= Decimal("0.08"):
            top_refund = _top_refund_product(orders)
            findings.append(
                LiveCommerceFinding(
                    title=f"退款率偏高，主要先查商品 {top_refund['product_id']}",
                    evidence=(
                        f"支付口径退款率为 {_percent(metrics.refund_rate)}。",
                        (
                            f"{top_refund['category_l1']} / {top_refund['product_id']} "
                            f"贡献退款 {top_refund['refund_amount']}，占总退款 "
                            f"{top_refund['refund_share']}。"
                        ),
                        (
                            f"关联场次 {top_refund['live_session_id']}，"
                            f"不是 LLM 猜测，是订单退款金额按商品汇总。"
                        ),
                    ),
                    recommended_action=(
                        f"先复核 {top_refund['product_id']} 的讲解承诺、价格机制、发货和售后原因；"
                        "如果该 SKU 属于福利品或高退货品，不要把它和其他商品混在总 GMV 里判断。"
                    ),
                    human_check="确认是否包含仅退款、退货退款和售后赔付。",
                )
            )
        if metrics.gpm < Decimal("500"):
            low_session = _lowest_gpm_session(live_sessions, orders)
            findings.append(
                LiveCommerceFinding(
                    title=(
                        f"GPM 被 {low_session['category_l1']} 场次 "
                        f"{low_session['live_session_id']} 拉低"
                    ),
                    evidence=(
                        f"整体 GPM 为 {metrics.gpm}，即千次观看支付 GMV。",
                        (
                            f"{low_session['category_l1']} / {low_session['anchor_id']} "
                            f"拿到 {low_session['view_share']} 的观看，但只贡献 "
                            f"{low_session['paid_gmv_share']} 的支付 GMV。"
                        ),
                        (
                            f"该场次 GPM 为 {low_session['gpm']}，低于整体 {metrics.gpm}；"
                            "不是 LLM 猜测，是按直播场次聚合支付 GMV 和观看人数。"
                        ),
                    ),
                    recommended_action=(
                        f"先检查 {low_session['live_session_id']} 的流量来源和商品承接："
                        f"同样观看量下，{low_session['category_l1']} 场次支付 GMV 偏少，"
                        "优先复盘引流人群、开场福利品、商品排序和主播讲解转支付的环节。"
                    ),
                    human_check="确认观看人数是曝光、进入直播间还是有效观看，避免口径错配。",
                )
            )
        if metrics.payment_conversion_rate < Decimal("0.003"):
            conversion_session = _lowest_conversion_session(live_sessions, orders)
            findings.append(
                LiveCommerceFinding(
                    title=(f"支付转化率偏低，先看场次 {conversion_session['live_session_id']}"),
                    evidence=(
                        f"观看到支付买家的转化率为 {_percent(metrics.payment_conversion_rate)}。",
                        (
                            f"{conversion_session['category_l1']} / "
                            f"{conversion_session['anchor_id']} 的支付转化为 "
                            f"{conversion_session['conversion_rate']}，支付买家 "
                            f"{conversion_session['paid_buyer_count']}，观看 "
                            f"{conversion_session['view_count']}。"
                        ),
                    ),
                    recommended_action=(
                        f"先围绕 {conversion_session['live_session_id']} 补直播间停留、"
                        "商品点击和加购字段；当前样例没有地区、节假日或世界杯等外部因子，"
                        "不能把低转化归因到这些因素。"
                    ),
                    human_check="确认 buyer_id 已匿名且能稳定去重。",
                )
            )
        if not findings:
            findings.append(
                LiveCommerceFinding(
                    title="首版规则未发现高风险信号",
                    evidence=("支付 GMV、退款率、GPM 和支付转化未触发首版阈值。",),
                    recommended_action="补充按周趋势、商品毛利和流量来源后再判断增长动作。",
                    human_check="确认样表时间范围是否能代表最近经营变化。",
                )
            )
        return tuple(findings)


class LiveCommerceReportMarkdownRenderer:
    """Render a buyer-facing draft with explicit mapping confidence."""

    def render(self, report: LiveCommerceDiagnosisReport) -> str:
        coverage = int(report.mapping_report.required_coverage_ratio * Decimal("100"))
        lines = [
            f"# {report.title}",
            "",
            f"客户问题：{report.primary_question}",
            "",
            "## 字段映射与可计算性",
            f"- 字段映射覆盖率：{coverage}%",
            f"- 可计算指标：{', '.join(report.mapping_report.computable_metric_ids)}",
            f"- 敏感字段来源：{', '.join(report.mapping_report.sensitive_source_columns)}",
            "",
            "## 关键指标",
            f"- GMV：{report.metrics.gmv}",
            f"- 支付 GMV：{report.metrics.paid_gmv}",
            f"- 支付订单数：{report.metrics.pay_order_count}",
            f"- 支付买家数：{report.metrics.pay_buyer_count}",
            f"- 客单价：{report.metrics.average_order_value}",
            f"- 退款率：{report.metrics.refund_rate}",
            f"- GPM：{report.metrics.gpm}",
            f"- 支付转化率：{report.metrics.payment_conversion_rate}",
            "",
            "## 初步发现",
        ]
        for finding in report.findings:
            lines.extend(
                [
                    f"### {finding.title}",
                    *[f"- 证据：{item}" for item in finding.evidence],
                    f"- 建议动作：{finding.recommended_action}",
                    f"- 人工确认：{finding.human_check}",
                    "",
                ]
            )
        lines.append("## 必须人工确认")
        lines.extend(f"- {item}" for item in report.required_human_checks)
        lines.extend(["", "## 边界声明"])
        lines.extend(f"- {item}" for item in report.disclaimers)
        return "\n".join(lines) + "\n"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def _rows_from_text(content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(content.lstrip("\ufeff"))))


def _value(
    row: dict[str, str], mapping_report: FieldMappingReport, field_id: str, default: str = ""
) -> str:
    try:
        return row.get(mapping_report.source_column_for(field_id), default)
    except ValueError:
        return default


def _int(value: str, field_name: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _money(value: str, field_name: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} must be a decimal number") from exc


def _money_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    return _ratio(numerator, denominator, Decimal("0.01"))


def _ratio(numerator: Decimal, denominator: Decimal, quant: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
    return (numerator / denominator).quantize(quant)


def _is_paid(payment_status: str) -> bool:
    return payment_status.strip().lower() in {"paid", "已支付", "支付成功", "已付款"}


def _paid_orders(
    orders: tuple[LiveCommerceOrderRecord, ...],
) -> tuple[LiveCommerceOrderRecord, ...]:
    return tuple(order for order in orders if _is_paid(order.payment_status))


def _top_refund_product(orders: tuple[LiveCommerceOrderRecord, ...]) -> dict[str, str]:
    refund_by_product: dict[str, Decimal] = {}
    example_by_product: dict[str, LiveCommerceOrderRecord] = {}
    for order in _paid_orders(orders):
        refund_by_product[order.product_id] = (
            refund_by_product.get(order.product_id, Decimal("0")) + order.refund_amount
        )
        example_by_product.setdefault(order.product_id, order)
    if not refund_by_product:
        return _empty_product_attribution()
    product_id = max(refund_by_product, key=lambda key: refund_by_product[key])
    example = example_by_product[product_id]
    total_refund = sum(refund_by_product.values(), Decimal("0"))
    return {
        "category_l1": example.category_l1,
        "product_id": product_id,
        "live_session_id": example.live_session_id,
        "refund_amount": str(refund_by_product[product_id]),
        "refund_share": _percent(
            _ratio(refund_by_product[product_id], total_refund, Decimal("0.001"))
        ),
    }


def _lowest_gpm_session(
    live_sessions: tuple[LiveCommerceSessionRecord, ...],
    orders: tuple[LiveCommerceOrderRecord, ...],
) -> dict[str, str]:
    segments = _session_segments(live_sessions, orders)
    if not segments:
        return _empty_session_attribution()
    segment = min(segments, key=lambda item: Decimal(item["gpm"]))
    total_paid_gmv = sum((Decimal(item["paid_gmv"]) for item in segments), Decimal("0"))
    total_views = sum((Decimal(item["view_count"]) for item in segments), Decimal("0"))
    segment["paid_gmv_share"] = _percent(
        _ratio(Decimal(segment["paid_gmv"]), total_paid_gmv, Decimal("0.001"))
    )
    segment["view_share"] = _percent(
        _ratio(Decimal(segment["view_count"]), total_views, Decimal("0.001"))
    )
    return segment


def _lowest_conversion_session(
    live_sessions: tuple[LiveCommerceSessionRecord, ...],
    orders: tuple[LiveCommerceOrderRecord, ...],
) -> dict[str, str]:
    segments = _session_segments(live_sessions, orders)
    if not segments:
        return _empty_session_attribution()
    return min(segments, key=lambda item: Decimal(item["conversion_decimal"]))


def _session_segments(
    live_sessions: tuple[LiveCommerceSessionRecord, ...],
    orders: tuple[LiveCommerceOrderRecord, ...],
) -> list[dict[str, str]]:
    paid_by_session = _paid_orders_by_session(orders)
    segments: list[dict[str, str]] = []
    for session in live_sessions:
        paid_orders = paid_by_session.get(session.live_session_id, ())
        paid_gmv = sum((order.pay_amount for order in paid_orders), Decimal("0"))
        paid_buyer_count = len({order.buyer_id for order in paid_orders if order.buyer_id})
        view_count = Decimal(session.live_room_view_count)
        conversion = _ratio(Decimal(paid_buyer_count), view_count, Decimal("0.0001"))
        segments.append(
            {
                "category_l1": session.category_l1,
                "live_session_id": session.live_session_id,
                "anchor_id": session.anchor_id,
                "view_count": str(session.live_room_view_count),
                "paid_gmv": str(paid_gmv),
                "paid_buyer_count": str(paid_buyer_count),
                "gpm": str(_money_ratio(paid_gmv * Decimal("1000"), view_count)),
                "conversion_rate": _percent(conversion),
                "conversion_decimal": str(conversion),
            }
        )
    return segments


def _paid_orders_by_session(
    orders: tuple[LiveCommerceOrderRecord, ...],
) -> dict[str, tuple[LiveCommerceOrderRecord, ...]]:
    grouped: dict[str, list[LiveCommerceOrderRecord]] = {}
    for order in _paid_orders(orders):
        grouped.setdefault(order.live_session_id, []).append(order)
    return {session_id: tuple(items) for session_id, items in grouped.items()}


def _empty_product_attribution() -> dict[str, str]:
    return {
        "category_l1": "未知类目",
        "product_id": "未知商品",
        "live_session_id": "未知场次",
        "refund_amount": "0",
        "refund_share": "0.0%",
    }


def _empty_session_attribution() -> dict[str, str]:
    return {
        "category_l1": "未知类目",
        "live_session_id": "未知场次",
        "anchor_id": "未知主播",
        "view_count": "0",
        "paid_gmv": "0",
        "paid_buyer_count": "0",
        "gpm": "0",
        "conversion_rate": "0.0%",
        "conversion_decimal": "0",
        "paid_gmv_share": "0.0%",
        "view_share": "0.0%",
    }


def _percent(value: Decimal) -> str:
    percent = value * Decimal("100")
    if Decimal("0") < percent < Decimal("0.1"):
        return f"{percent.quantize(Decimal('0.01'))}%"
    return f"{percent.quantize(Decimal('0.1'))}%"
