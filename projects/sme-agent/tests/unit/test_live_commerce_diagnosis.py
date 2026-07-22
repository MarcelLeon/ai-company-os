from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from sme_agent.commercialization.live_commerce_diagnosis import (
    LiveCommerceDiagnosisRunner,
    LiveCommerceReportMarkdownRenderer,
)
from sme_agent.domains import DomainFieldMappingService, build_live_commerce_template

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_live_commerce_mapping_maps_chinese_export_headers_to_template_fields() -> None:
    template = build_live_commerce_template()
    headers = (
        "一级类目",
        "店铺ID",
        "平台",
        "直播场次ID",
        "主播ID",
        "观看人数",
        "商品ID",
        "订单编号",
        "下单时间",
        "订单状态",
        "订单金额",
        "支付状态",
        "支付金额",
        "退款金额",
        "买家匿名ID",
    )

    report = DomainFieldMappingService().evaluate(template, headers)

    assert report.required_coverage_ratio == Decimal("1.00")
    assert report.missing_required_fields == ()
    assert "metric.paid_gmv" in report.computable_metric_ids
    assert "metric.gpm" in report.computable_metric_ids
    assert "买家匿名ID" in report.sensitive_source_columns


def test_live_commerce_diagnosis_computes_paid_gmv_gpm_refund_and_conversion() -> None:
    sample_dir = PROJECT_ROOT / "sample_data" / "live_commerce_public_dogfood"

    report = LiveCommerceDiagnosisRunner().run(
        primary_question="公开来源缩放样例里，直播间成交效率和退款风险是否值得继续追问？",
        live_sessions_csv=sample_dir / "live_sessions.csv",
        orders_csv=sample_dir / "orders.csv",
    )

    assert report.mapping_report.required_coverage_ratio == Decimal("1.00")
    assert report.metrics.gmv == Decimal("2850")
    assert report.metrics.paid_gmv == Decimal("2249")
    assert report.metrics.pay_order_count == 5
    assert report.metrics.pay_buyer_count == 5
    assert report.metrics.average_order_value == Decimal("449.80")
    assert report.metrics.refund_rate == Decimal("0.17")
    assert report.metrics.gpm == Decimal("398.97")
    assert report.metrics.payment_conversion_rate == Decimal("0.0009")
    assert any("退款率" in finding.title for finding in report.findings)
    assert any("GPM" in finding.title for finding in report.findings)


def test_live_commerce_report_renderer_exposes_mapping_and_human_checks() -> None:
    sample_dir = PROJECT_ROOT / "sample_data" / "live_commerce_public_dogfood"
    report = LiveCommerceDiagnosisRunner().run(
        primary_question="公开来源缩放样例里，直播间成交效率和退款风险是否值得继续追问？",
        live_sessions_csv=sample_dir / "live_sessions.csv",
        orders_csv=sample_dir / "orders.csv",
    )

    markdown = LiveCommerceReportMarkdownRenderer().render(report)

    assert "# 直播电商经营诊断报告（人工复核草稿）" in markdown
    assert "字段映射覆盖率：100%" in markdown
    assert "支付 GMV：2249" in markdown
    assert "GPM：398.97" in markdown
    assert "确认平台 GMV 是否包含未支付、取消或退款订单" in markdown


def test_public_web_dogfood_fixture_runs_through_live_commerce_agent() -> None:
    sample_dir = PROJECT_ROOT / "sample_data" / "live_commerce_public_dogfood"

    report = LiveCommerceDiagnosisRunner().run(
        primary_question="公开来源缩放样例里，直播间成交效率和退款风险是否值得继续追问？",
        live_sessions_csv=sample_dir / "live_sessions.csv",
        orders_csv=sample_dir / "orders.csv",
    )

    assert report.mapping_report.required_coverage_ratio == Decimal("1.00")
    assert report.metrics.gmv == Decimal("2850")
    assert report.metrics.paid_gmv == Decimal("2249")
    assert report.metrics.pay_order_count == 5
    assert report.metrics.average_order_value == Decimal("449.80")
    assert report.metrics.refund_rate == Decimal("0.17")
    assert report.metrics.gpm == Decimal("398.97")
    assert report.metrics.payment_conversion_rate == Decimal("0.0009")


def test_public_web_findings_attribute_gpm_and_refund_to_entities() -> None:
    sample_dir = PROJECT_ROOT / "sample_data" / "live_commerce_public_dogfood"

    report = LiveCommerceDiagnosisRunner().run(
        primary_question="公开来源缩放样例里，直播间成交效率和退款风险是否值得继续追问？",
        live_sessions_csv=sample_dir / "live_sessions.csv",
        orders_csv=sample_dir / "orders.csv",
    )
    finding_text = "\n".join(
        (finding.title + "\n" + "\n".join(finding.evidence) + "\n" + finding.recommended_action)
        for finding in report.findings
    )

    assert "食品饮料" in finding_text
    assert "KUAILIVE-PUBLIC-001" in finding_text
    assert "ANCHOR-PUBLIC-01" in finding_text
    assert "SKU-PUBLIC-F" in finding_text
    assert "289" in finding_text
    assert "0.04%" in finding_text
    assert "不是 LLM 猜测" in finding_text


def test_live_commerce_loader_rejects_paid_orders_missing_pay_amount(tmp_path: Path) -> None:
    sample_dir = PROJECT_ROOT / "sample_data" / "live_commerce_week_one"
    bad_orders = tmp_path / "orders.csv"
    header = (
        "一级类目,店铺ID,平台,直播场次ID,商品ID,订单编号,下单时间,"
        "订单状态,订单金额,支付状态,支付金额,退款金额,买家匿名ID"
    )
    row = (
        "食品饮料,KS-SEED-001,快手,LIVE-20260619-A,SKU-A,O-LIVE-1001,"
        "2026/6/19 20:05,已支付,599,已支付,,0,U-0001"
    )
    bad_orders.write_text(
        "\n".join([header, row]) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc_info:
        LiveCommerceDiagnosisRunner().run(
            primary_question="为什么这场直播比上一场差？",
            live_sessions_csv=sample_dir / "live_sessions.csv",
            orders_csv=bad_orders,
        )

    assert "支付金额缺失" in str(exc_info.value)
    assert "LIVE-20260619-A" in str(exc_info.value)
    assert "O-LIVE-1001" in str(exc_info.value)
