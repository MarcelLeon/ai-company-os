"""Assess whether a prospect can be served by the first commercial package."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from sme_agent.metadata.models import FrozenModel


class BusinessPain(StrEnum):
    REVENUE_DROP = "revenue_drop"
    CUSTOMER_CHURN = "customer_churn"
    INVENTORY_PRESSURE = "inventory_pressure"
    AD_ROI = "ad_roi"
    CASHFLOW = "cashflow"
    OTHER = "other"


class ServiceTier(StrEnum):
    NOT_READY = "not_ready"
    INTRO_DIAGNOSIS = "intro_diagnosis"
    STANDARD_REPORT = "standard_report"
    DEEP_ASSISTANT = "deep_assistant"


class DataAssetSubmission(FrozenModel):
    name: str = Field(min_length=1)
    business_meaning: str = Field(min_length=1)
    format: str = Field(min_length=1)
    periods_covered: str | None = None
    contains_personal_data: bool = False


class CustomerIntake(FrozenModel):
    company_name: str = Field(min_length=1)
    contact_channel: str = Field(min_length=1)
    industry: str = Field(min_length=1)
    monthly_order_volume: int | None = Field(default=None, ge=0)
    pains: tuple[BusinessPain, ...] = Field(min_length=1)
    primary_question: str = Field(min_length=1)
    data_assets: tuple[DataAssetSubmission, ...] = ()
    has_authorized_analysis: bool = False
    allows_anonymized_case_study: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def _authorized_data_requires_assets(self) -> CustomerIntake:
        if self.has_authorized_analysis and not self.data_assets:
            raise ValueError("authorized analysis requires at least one submitted data asset")
        return self


class IntakeAssessment(FrozenModel):
    tier: ServiceTier
    score: int = Field(ge=0, le=100)
    missing_items: tuple[str, ...]
    recommended_next_questions: tuple[str, ...]
    human_review_required: bool


class IntakeAssessmentService:
    """Keep the first paid offer honest about deliverability."""

    def assess(self, intake: CustomerIntake) -> IntakeAssessment:
        missing_items = self._missing_items(intake)
        score = self._score(intake, missing_items)
        tier = self._tier(score, intake)
        next_questions = self._next_questions(intake)
        return IntakeAssessment(
            tier=tier,
            score=score,
            missing_items=missing_items,
            recommended_next_questions=next_questions,
            human_review_required=tier is not ServiceTier.NOT_READY,
        )

    def _missing_items(self, intake: CustomerIntake) -> tuple[str, ...]:
        items: list[str] = []
        if not intake.has_authorized_analysis:
            items.append("客户需明确授权基于其提交数据做经营诊断")
        if not intake.data_assets:
            items.append("至少需要一份订单、客户、库存、广告或财务相关数据")
        if len(intake.primary_question) < 8:
            items.append("经营问题需要具体到指标、时间或业务对象")
        if any(asset.contains_personal_data for asset in intake.data_assets):
            items.append("含个人信息的数据需要先脱敏或限定最小必要字段")
        return tuple(items)

    def _score(self, intake: CustomerIntake, missing_items: tuple[str, ...]) -> int:
        score = 35
        score += min(len(intake.data_assets), 3) * 15
        score += 10 if intake.has_authorized_analysis else 0
        score += 10 if intake.monthly_order_volume and intake.monthly_order_volume > 0 else 0
        score += 5 if intake.allows_anonymized_case_study else 0
        score -= len(missing_items) * 15
        return max(0, min(100, score))

    def _tier(self, score: int, intake: CustomerIntake) -> ServiceTier:
        if score < 45:
            return ServiceTier.NOT_READY
        if score < 65:
            return ServiceTier.INTRO_DIAGNOSIS
        if len(intake.data_assets) >= 3 and intake.has_authorized_analysis:
            return ServiceTier.STANDARD_REPORT
        return ServiceTier.INTRO_DIAGNOSIS

    def _next_questions(self, intake: CustomerIntake) -> tuple[str, ...]:
        questions = [
            "你最希望先解释哪个经营变化：收入、客户、库存、投放还是现金流？",
            "可否提供最近 3 个月的订单或交易明细导出？",
            "这些数据里哪些字段是你们内部确认过口径的？",
        ]
        if BusinessPain.AD_ROI in intake.pains:
            questions.append("广告投放数据能否按渠道、计划、消耗、成交金额导出？")
        if BusinessPain.INVENTORY_PRESSURE in intake.pains:
            questions.append("库存数据能否包含商品、可售库存、近 30 天销量和采购成本？")
        return tuple(questions)
