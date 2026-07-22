from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sme_agent.commercialization.live_commerce_comparison import (
    LiveCommerceComparisonRunner,
    comparison_to_payload,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_week_one_comparison_explains_why_second_session_dropped() -> None:
    sample_dir = PROJECT_ROOT / "sample_data" / "live_commerce_week_one"

    report = LiveCommerceComparisonRunner().run(
        question="为什么这场直播比上一场差？",
        live_sessions_csv=sample_dir / "live_sessions.csv",
        orders_csv=sample_dir / "orders.csv",
    )

    assert report.baseline.live_session_id == "LIVE-20260618-A"
    assert report.comparison.live_session_id == "LIVE-20260619-A"
    assert report.baseline.paid_gmv == 2927
    assert report.comparison.paid_gmv == 1530
    assert report.metric_deltas["paid_gmv"] == "-1397"
    assert report.metric_deltas["gpm"] == "-163.14"
    assert report.metric_deltas["pay_order_count"] == "0"
    assert report.metric_deltas["pay_buyer_count"] == "0"
    assert report.sku_contributions[0].product_id == "SKU-C"
    assert report.sku_contributions[0].paid_gmv_delta == -599
    assert any("不是没人买" in finding for finding in report.findings)
    assert any("SKU-C" in finding for finding in report.findings)
    assert any("地区、节日、世界杯或暑假" in finding for finding in report.findings)


def test_comparison_payload_is_workbench_ready() -> None:
    sample_dir = PROJECT_ROOT / "sample_data" / "live_commerce_week_one"
    report = LiveCommerceComparisonRunner().run(
        question="为什么这场直播比上一场差？",
        live_sessions_csv=sample_dir / "live_sessions.csv",
        orders_csv=sample_dir / "orders.csv",
    )

    payload = comparison_to_payload(report)
    metric_deltas = cast(dict[str, str], payload["metric_deltas"])
    comparison = cast(dict[str, str], payload["comparison"])
    sku_contributions = cast(list[dict[str, Any]], payload["sku_contributions"])

    assert metric_deltas["paid_gmv"] == "-1397"
    assert comparison["gpm"] == "255.00"
    assert sku_contributions[0]["product_id"] == "SKU-C"
