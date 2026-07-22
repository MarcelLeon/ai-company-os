"""Bounded, in-memory intake for merchant live-commerce CSV exports."""

from __future__ import annotations

import csv
from enum import StrEnum
from io import StringIO

from pydantic import Field

from sme_agent.commercialization.live_commerce_diagnosis import (
    LiveCommerceDiagnosisReport,
    LiveCommerceDiagnosisRunner,
)
from sme_agent.domains import (
    DomainFieldMappingService,
    FieldMappingReport,
    FieldSpec,
    build_live_commerce_template,
)
from sme_agent.metadata.models import FrozenModel

DEFAULT_MAX_BYTES_PER_TABLE = 2_000_000
DEFAULT_MAX_ROWS_PER_TABLE = 10_000


class IntakeReadiness(StrEnum):
    """Commercially honest outcomes for a local CSV intake."""

    READY_FOR_HUMAN_REVIEW = "ready_for_human_review"
    BLOCKED_MISSING_FIELDS = "blocked_missing_fields"
    BLOCKED_NO_ROWS = "blocked_no_rows"


class CsvTableProfile(FrozenModel):
    """Non-persistent shape evidence extracted from one submitted table."""

    table_name: str = Field(min_length=1)
    headers: tuple[str, ...] = Field(min_length=1)
    row_count: int = Field(ge=0)


class LiveCommerceIntakeAssessment(FrozenModel):
    """Mapping evidence plus an optional governed diagnosis."""

    readiness: IntakeReadiness
    mapping_report: FieldMappingReport
    live_sessions_profile: CsvTableProfile
    orders_profile: CsvTableProfile
    follow_up_questions: tuple[str, ...]
    report: LiveCommerceDiagnosisReport | None = None


class LiveCommerceCsvIntakeService:
    """Inspect local CSV text before allowing deterministic diagnosis."""

    def __init__(
        self,
        *,
        max_bytes_per_table: int = DEFAULT_MAX_BYTES_PER_TABLE,
        max_rows_per_table: int = DEFAULT_MAX_ROWS_PER_TABLE,
    ) -> None:
        if max_bytes_per_table <= 0 or max_rows_per_table <= 0:
            raise ValueError("intake limits must be positive")
        self._max_bytes_per_table = max_bytes_per_table
        self._max_rows_per_table = max_rows_per_table

    def assess(
        self,
        *,
        primary_question: str,
        live_sessions_csv: str,
        orders_csv: str,
    ) -> LiveCommerceIntakeAssessment:
        question = primary_question.strip()
        if not question:
            raise ValueError("经营问题不能为空")
        sessions = self._profile("live_sessions.csv", live_sessions_csv)
        orders = self._profile("orders.csv", orders_csv)
        template = build_live_commerce_template()
        mapping = DomainFieldMappingService().evaluate(
            template,
            tuple(dict.fromkeys(sessions.headers + orders.headers)),
        )
        follow_ups = _follow_up_questions(template_fields=_fields_by_id(), mapping=mapping)
        if mapping.missing_required_fields:
            return self._assessment(
                IntakeReadiness.BLOCKED_MISSING_FIELDS,
                mapping,
                sessions,
                orders,
                follow_ups,
            )
        empty_table_questions = _empty_table_questions(sessions, orders)
        if empty_table_questions:
            return self._assessment(
                IntakeReadiness.BLOCKED_NO_ROWS,
                mapping,
                sessions,
                orders,
                empty_table_questions,
            )
        report = LiveCommerceDiagnosisRunner().run_text(
            primary_question=question,
            live_sessions_csv=live_sessions_csv,
            orders_csv=orders_csv,
        )
        return LiveCommerceIntakeAssessment(
            readiness=IntakeReadiness.READY_FOR_HUMAN_REVIEW,
            mapping_report=mapping,
            live_sessions_profile=sessions,
            orders_profile=orders,
            follow_up_questions=(),
            report=report,
        )

    def _profile(self, table_name: str, content: str) -> CsvTableProfile:
        encoded_size = len(content.encode("utf-8"))
        if encoded_size > self._max_bytes_per_table:
            raise ValueError(
                f"{table_name} 超过 {self._max_bytes_per_table} bytes；"
                "请先导出较小时间范围或联系标准报告服务。"
            )
        try:
            reader = csv.DictReader(StringIO(content.lstrip("\ufeff")), strict=True)
            headers = tuple(header.strip() for header in (reader.fieldnames or ()))
            _validate_headers(table_name, headers)
            row_count = 0
            for row in reader:
                row_count += 1
                if row_count > self._max_rows_per_table:
                    raise ValueError(
                        f"{table_name} 超过 {self._max_rows_per_table} 行；"
                        "请先缩小时间范围或联系标准报告服务。"
                    )
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"{table_name} 存在与表头列数不一致的数据行")
        except csv.Error as exc:
            raise ValueError(f"{table_name} 不是有效 CSV：{exc}") from exc
        return CsvTableProfile(table_name=table_name, headers=headers, row_count=row_count)

    @staticmethod
    def _assessment(
        readiness: IntakeReadiness,
        mapping: FieldMappingReport,
        sessions: CsvTableProfile,
        orders: CsvTableProfile,
        questions: tuple[str, ...],
    ) -> LiveCommerceIntakeAssessment:
        return LiveCommerceIntakeAssessment(
            readiness=readiness,
            mapping_report=mapping,
            live_sessions_profile=sessions,
            orders_profile=orders,
            follow_up_questions=questions,
        )


def _validate_headers(table_name: str, headers: tuple[str, ...]) -> None:
    if not headers or any(not header for header in headers):
        raise ValueError(f"{table_name} 缺少有效表头")
    normalized = tuple(header.casefold() for header in headers)
    duplicates = tuple(
        header
        for index, header in enumerate(headers)
        if normalized.index(normalized[index]) < index
    )
    if duplicates:
        raise ValueError(f"{table_name} 存在重复列名：{', '.join(duplicates)}")


def _fields_by_id() -> dict[str, FieldSpec]:
    template = build_live_commerce_template()
    return {
        field.field_id: field for dimension in template.dimensions for field in dimension.fields
    }


def _follow_up_questions(
    *,
    template_fields: dict[str, FieldSpec],
    mapping: FieldMappingReport,
) -> tuple[str, ...]:
    questions: list[str] = []
    for field_id in mapping.missing_required_fields:
        field = template_fields[field_id]
        accepted = "、".join(dict.fromkeys((field.name, field.field_id, *field.aliases)))
        questions.append(
            f"缺少“{field.name}”（{field.field_id}）。"
            f"请补充包含以下任一列名的脱敏导出：{accepted}。"
        )
    return tuple(questions)


def _empty_table_questions(
    sessions: CsvTableProfile,
    orders: CsvTableProfile,
) -> tuple[str, ...]:
    return tuple(
        f"{profile.table_name} 只有表头；请至少保留一行脱敏数据行再生成诊断。"
        for profile in (sessions, orders)
        if profile.row_count == 0
    )
