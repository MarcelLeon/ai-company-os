from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from sme_agent.commercialization.live_commerce_intake import (
    IntakeReadiness,
    LiveCommerceCsvIntakeService,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _sample_text(sample: str, filename: str) -> str:
    return (PROJECT_ROOT / "sample_data" / sample / filename).read_text(encoding="utf-8")


def test_complete_csv_intake_reuses_governed_diagnosis_without_persisting_files() -> None:
    assessment = LiveCommerceCsvIntakeService().assess(
        primary_question="这场直播的成交效率和退款风险怎么样？",
        live_sessions_csv=_sample_text("live_commerce_public_dogfood", "live_sessions.csv"),
        orders_csv=_sample_text("live_commerce_public_dogfood", "orders.csv"),
    )

    assert assessment.readiness is IntakeReadiness.READY_FOR_HUMAN_REVIEW
    assert assessment.mapping_report.required_coverage_ratio == 1
    assert assessment.live_sessions_profile.row_count == 2
    assert assessment.orders_profile.row_count == 7
    assert assessment.follow_up_questions == ()
    assert assessment.report is not None
    assert assessment.report.metrics.paid_gmv == 2249
    assert assessment.report.metrics.gpm == Decimal("398.97")


def test_missing_fields_return_questions_without_a_diagnosis() -> None:
    assessment = LiveCommerceCsvIntakeService().assess(
        primary_question="这场直播为什么没赚到钱？",
        live_sessions_csv="直播场次ID,观看人数\nLIVE-1,1000\n",
        orders_csv="直播场次ID,订单编号,支付状态\nLIVE-1,O-1,已支付\n",
    )

    assert assessment.readiness is IntakeReadiness.BLOCKED_MISSING_FIELDS
    assert assessment.report is None
    assert "pay_amount" in assessment.mapping_report.missing_required_fields
    assert any("支付金额" in question for question in assessment.follow_up_questions)
    assert any("店铺 ID" in question for question in assessment.follow_up_questions)


def test_header_only_intake_asks_for_anonymized_rows_instead_of_zero_metrics() -> None:
    sessions = _sample_text("live_commerce_public_dogfood", "live_sessions.csv")
    orders = _sample_text("live_commerce_public_dogfood", "orders.csv")

    assessment = LiveCommerceCsvIntakeService().assess(
        primary_question="这些字段够不够做诊断？",
        live_sessions_csv=sessions.splitlines()[0] + "\n",
        orders_csv=orders.splitlines()[0] + "\n",
    )

    assert assessment.readiness is IntakeReadiness.BLOCKED_NO_ROWS
    assert assessment.report is None
    assert any("脱敏数据行" in question for question in assessment.follow_up_questions)


def test_intake_rejects_duplicate_headers_and_bounded_payloads() -> None:
    service = LiveCommerceCsvIntakeService(max_bytes_per_table=80)

    with pytest.raises(ValueError, match="缺少有效表头"):
        service.assess(
            primary_question="字段是否够？",
            live_sessions_csv="",
            orders_csv="订单编号\nO-1\n",
        )

    with pytest.raises(ValueError, match="不是有效 CSV"):
        service.assess(
            primary_question="字段是否够？",
            live_sessions_csv='直播场次ID\n"LIVE-1\n',
            orders_csv="订单编号\nO-1\n",
        )

    with pytest.raises(ValueError, match="重复列名"):
        service.assess(
            primary_question="字段是否够？",
            live_sessions_csv="直播场次ID,直播场次ID\nLIVE-1,LIVE-1\n",
            orders_csv="订单编号\nO-1\n",
        )

    with pytest.raises(ValueError, match="超过 80 bytes"):
        service.assess(
            primary_question="字段是否够？",
            live_sessions_csv="直播场次ID\n" + ("x" * 100),
            orders_csv="订单编号\nO-1\n",
        )


def test_intake_rejects_too_many_rows_before_diagnosis() -> None:
    service = LiveCommerceCsvIntakeService(max_rows_per_table=1)

    with pytest.raises(ValueError, match="超过 1 行"):
        service.assess(
            primary_question="字段是否够？",
            live_sessions_csv="直播场次ID\nLIVE-1\nLIVE-2\n",
            orders_csv="订单编号\nO-1\n",
        )
