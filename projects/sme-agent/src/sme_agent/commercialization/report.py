"""Deterministic report outline generation for human-reviewed delivery."""

from __future__ import annotations

from pydantic import Field

from sme_agent.application.grounding import GroundedQuestion
from sme_agent.metadata.models import FrozenModel


class ReportSection(FrozenModel):
    title: str = Field(min_length=1)
    prompts: tuple[str, ...] = Field(min_length=1)


class DiagnosticReportOutline(FrozenModel):
    title: str = Field(min_length=1)
    customer_question: str = Field(min_length=1)
    evidence_ids: tuple[str, ...]
    sections: tuple[ReportSection, ...]
    disclaimers: tuple[str, ...]


class ReportTemplateService:
    """Create the first paid report skeleton without inventing conclusions."""

    def outline_from_grounding(self, grounded: GroundedQuestion) -> DiagnosticReportOutline:
        metric_name = grounded.metric.name
        dimension_names = "、".join(dimension.name for dimension in grounded.dimensions) or "无"
        return DiagnosticReportOutline(
            title=f"{metric_name}经营诊断报告",
            customer_question=grounded.question,
            evidence_ids=grounded.evidence_ids,
            sections=(
                ReportSection(
                    title="1. 问题复述与诊断边界",
                    prompts=(
                        f"客户问题：{grounded.question}",
                        "明确本报告只基于客户提交数据、已治理口径和人工复核结论。",
                    ),
                ),
                ReportSection(
                    title="2. 指标口径与数据来源",
                    prompts=(
                        f"核心指标：{metric_name}，公式：{grounded.metric.formula}",
                        f"分析维度：{dimension_names}",
                        "列出实际使用的数据表、文档和缺失数据。",
                    ),
                ),
                ReportSection(
                    title="3. 关键发现",
                    prompts=(
                        "只写可由数据或业务知识支持的发现。",
                        "每条发现必须引用 evidence_ids 中的依据或标记为人工判断。",
                    ),
                ),
                ReportSection(
                    title="4. 建议动作与人工确认项",
                    prompts=(
                        "把建议分成今天能查、三天能做、一周能验证。",
                        "列出仍需老板或业务负责人确认的口径、异常和决策。",
                    ),
                ),
            ),
            disclaimers=(
                "本报告不是财务、税务、法律或投资建议。",
                "AI 仅辅助整理和初步分析，最终结论需由人类复核。",
                "客户应先脱敏或最小化提供涉及个人信息的数据字段。",
            ),
        )
