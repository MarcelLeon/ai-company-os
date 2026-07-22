from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from sme_agent.commercialization.workbench import (
    WorkbenchRequestHandler,
    build_live_commerce_comparison_payload,
    build_live_commerce_intake_payload,
    build_live_commerce_payload,
    render_workbench_html,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _sample_text(sample: str, filename: str) -> str:
    return (PROJECT_ROOT / "sample_data" / sample / filename).read_text(encoding="utf-8")


def test_workbench_payload_exposes_public_dogfood_metrics_and_report() -> None:
    payload = build_live_commerce_payload("public-dogfood")

    assert payload["sample_id"] == "public-dogfood"
    assert payload["sample_name"] == "公开来源直播电商样例"
    assert payload["mapping"]["coverage_ratio"] == "1.00"
    assert payload["metrics"]["paid_gmv"] == "2249"
    assert payload["metrics"]["gpm"] == "398.97"
    assert payload["metrics"]["refund_rate"] == "0.17"
    assert payload["metrics"]["payment_conversion_rate"] == "0.0009"
    assert payload["decision"]["commercial_readiness"] == "needs_human_review"
    assert "pain_points" in payload["business_context"]
    assert "relationships" in payload["business_context"]
    assert "next_after_validation" in payload["business_context"]
    assert "退款率偏高" in payload["report_markdown"]


def test_workbench_payload_exposes_week_one_sample() -> None:
    payload = build_live_commerce_payload("week-one")

    assert payload["sample_name"] == "直播电商拟真样例"
    assert payload["metrics"]["paid_gmv"] == "4457"
    assert payload["metrics"]["gpm"] == "342.85"


def test_workbench_comparison_payload_explains_drop() -> None:
    payload = build_live_commerce_comparison_payload("week-one")

    assert payload["sample_name"] == "直播电商拟真样例"
    assert payload["metric_deltas"]["paid_gmv"] == "-1397"
    assert payload["comparison"]["gpm"] == "255.00"
    assert payload["sku_contributions"][0]["product_id"] == "SKU-C"
    assert any("不是没人买" in finding for finding in payload["findings"])


def test_workbench_intake_payload_blocks_missing_fields_without_fake_metrics() -> None:
    payload = build_live_commerce_intake_payload(
        primary_question="这场直播为什么不赚钱？",
        live_sessions_csv="直播场次ID,观看人数\nLIVE-1,1000\n",
        orders_csv="直播场次ID,订单编号,支付状态\nLIVE-1,O-1,已支付\n",
    )

    assert payload["decision"]["commercial_readiness"] == "blocked_missing_fields"
    assert payload["metrics"] is None
    assert payload["findings"] == []
    assert payload["report_markdown"] == ""
    assert any("支付金额" in item for item in payload["follow_up_questions"])
    assert payload["delivery_preview"]["status"] == "blocked_missing_fields"
    assert payload["delivery_preview"]["creates_workspace"] is False


def test_workbench_intake_blocks_direct_personal_data_before_showing_report() -> None:
    order_lines = _sample_text("live_commerce_public_dogfood", "orders.csv").splitlines()
    orders_csv = "\n".join(
        [order_lines[0] + ",手机号", *[line + ",13800000000" for line in order_lines[1:]]]
    )

    payload = build_live_commerce_intake_payload(
        primary_question="这场直播表现如何？",
        live_sessions_csv=_sample_text("live_commerce_public_dogfood", "live_sessions.csv"),
        orders_csv=orders_csv + "\n",
    )

    assert payload["decision"]["commercial_readiness"] == "blocked_redaction"
    assert payload["metrics"] is None
    assert payload["findings"] == []
    assert payload["report_markdown"] == ""
    assert payload["delivery_preview"]["redaction_fields"] == ["手机号"]


def test_workbench_intake_http_endpoint_diagnoses_complete_local_csv() -> None:
    body = json.dumps(
        {
            "primary_question": "这场直播的成交效率和退款风险怎么样？",
            "live_sessions_csv": _sample_text("live_commerce_public_dogfood", "live_sessions.csv"),
            "orders_csv": _sample_text("live_commerce_public_dogfood", "orders.csv"),
        }
    ).encode()
    handler = cast(Any, object.__new__(WorkbenchRequestHandler))
    handler.path = "/api/live-commerce/intake"
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = BytesIO(body)
    handler.wfile = BytesIO()
    response: dict[str, object] = {}
    handler.send_response = lambda status: response.update(status=status)
    handler.send_header = lambda *_args: None
    handler.end_headers = lambda: None

    WorkbenchRequestHandler.do_POST(handler)
    payload = json.loads(handler.wfile.getvalue())

    assert response["status"] == 200
    assert payload["decision"]["commercial_readiness"] == "needs_human_review"
    assert payload["metrics"]["paid_gmv"] == "2249"
    assert payload["source_note"] == "文件仅在本机进程内分析，SME Agent 不会持久化本次 intake。"


def test_workbench_html_is_a_boss_readable_product_surface() -> None:
    html = render_workbench_html()

    assert "SME Agent 直播诊断工作台" in html
    assert "解决什么痛点" in html
    assert "样例数据怎么建模" in html
    assert "实体关系和直播业务过程" in html
    assert "你验收没问题后怎么继续" in html
    assert "使用公开 dogfood 样例" in html
    assert "字段映射" in html
    assert "复制交付报告" in html
    assert "/api/live-commerce/sample/public-dogfood" in html
    assert "回答：为什么这场比上一场差？" in html
    assert "/api/live-commerce/comparison/week-one" in html
    assert "选择你自己的 CSV" in html
    assert 'type="file"' in html
    assert "粘贴 CSV 文本" in html
    assert "/api/live-commerce/intake" in html
    assert "仅发送到当前本地工作台进程" in html
    assert "不可变交付包预览" in html
    assert "预览不会创建客户 workspace" in html
    assert "199 元入口验收" in html
    assert "我愿意为这份字段体检 / 轻诊断支付 199 元" in html
    assert "acceptanceProgress" in html
