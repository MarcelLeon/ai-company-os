from __future__ import annotations

from data_agent_v1 import DataAgentEngine


def test_answer_explains_east_china_revenue_drop() -> None:
    response = DataAgentEngine().answer("本月华东区收入为什么下降？")

    assert response.intent == "east_china_revenue_drop"
    assert response.facts["current_month_revenue"] == "84000"
    assert response.facts["previous_month_revenue"] == "120000"
    assert response.facts["drop_pct"] == "30.0"
    assert response.facts["largest_channel_drag"] == "Douyin"
    assert "SELECT month" in response.sql


def test_answer_identifies_low_roas_channel() -> None:
    response = DataAgentEngine().answer("广告 ROAS 低是哪个渠道拖累的？")

    assert response.intent == "roas_drag"
    assert response.facts["lowest_roas_channel"] == "Douyin"
    assert response.facts["douyin_roas"] == "1.40"
    assert response.facts["search_roas"] == "4.00"


def test_answer_identifies_refund_product_and_segment() -> None:
    response = DataAgentEngine().answer("退款率上升主要来自哪些商品或客户分群？")

    assert response.intent == "refund_contributors"
    assert response.facts["top_refund_product"] == "Smart Camera"
    assert response.facts["top_refund_amount"] == "14000"
    assert response.facts["refund_rate"] == "19.0"


def test_ambiguous_revenue_question_asks_follow_up() -> None:
    response = DataAgentEngine().answer("收入怎么样？")

    assert response.intent == "needs_clarification"
    assert response.follow_up_questions
    assert response.facts["missing_scope"] == "time_period_or_business_scope"
