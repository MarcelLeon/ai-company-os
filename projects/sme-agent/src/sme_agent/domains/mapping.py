"""Field mapping checks for vertical domain templates."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from sme_agent.domains.templates import DomainTemplate, FieldSpec
from sme_agent.metadata.models import FrozenModel


class FieldMapping(FrozenModel):
    field_id: str = Field(min_length=1)
    source_column: str = Field(min_length=1)
    required: bool
    sensitive: bool


class FieldMappingReport(FrozenModel):
    template_name: str = Field(min_length=1)
    mappings: tuple[FieldMapping, ...]
    missing_required_fields: tuple[str, ...]
    required_coverage_ratio: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    computable_metric_ids: tuple[str, ...]
    sensitive_source_columns: tuple[str, ...]

    def source_column_for(self, field_id: str) -> str:
        for mapping in self.mappings:
            if mapping.field_id == field_id:
                return mapping.source_column
        raise ValueError(f"field is not mapped: {field_id}")

    def has_field(self, field_id: str) -> bool:
        return any(mapping.field_id == field_id for mapping in self.mappings)


class DomainFieldMappingService:
    """Evaluate whether uploaded columns can support a domain template."""

    def evaluate(
        self,
        template: DomainTemplate,
        source_headers: tuple[str, ...],
        manual_mapping: dict[str, str] | None = None,
    ) -> FieldMappingReport:
        manual_mapping = manual_mapping or {}
        fields = _fields_by_id(template)
        mappings = tuple(
            mapping
            for field in fields.values()
            if (mapping := self._map_field(field, source_headers, manual_mapping)) is not None
        )
        mapped_ids = {mapping.field_id for mapping in mappings}
        required_ids = set(template.required_field_ids())
        missing_required = tuple(
            field_id for field_id in template.required_field_ids() if field_id not in mapped_ids
        )
        sensitive_columns = tuple(
            mapping.source_column for mapping in mappings if mapping.sensitive
        )
        computable_metrics = tuple(
            metric.metric_id
            for metric in template.metrics
            if set(metric.required_fields).issubset(mapped_ids)
        )
        return FieldMappingReport(
            template_name=template.name,
            mappings=mappings,
            missing_required_fields=missing_required,
            required_coverage_ratio=_coverage(
                len(required_ids) - len(missing_required), len(required_ids)
            ),
            computable_metric_ids=computable_metrics,
            sensitive_source_columns=sensitive_columns,
        )

    def _map_field(
        self,
        field: FieldSpec,
        source_headers: tuple[str, ...],
        manual_mapping: dict[str, str],
    ) -> FieldMapping | None:
        manual_column = manual_mapping.get(field.field_id)
        if manual_column is not None:
            if manual_column not in source_headers:
                return None
            return _mapping(field, manual_column)
        candidates = (field.field_id, field.name, *field.aliases)
        candidate_keys = {_normalize(candidate) for candidate in candidates}
        for header in source_headers:
            if _normalize(header) in candidate_keys:
                return _mapping(field, header)
        return None


def _fields_by_id(template: DomainTemplate) -> dict[str, FieldSpec]:
    return {
        field.field_id: field for dimension in template.dimensions for field in dimension.fields
    }


def _mapping(field: FieldSpec, source_column: str) -> FieldMapping:
    return FieldMapping(
        field_id=field.field_id,
        source_column=source_column,
        required=field.required,
        sensitive=field.sensitive,
    )


def _coverage(mapped_required_count: int, required_count: int) -> Decimal:
    if required_count == 0:
        return Decimal("1.00")
    return (Decimal(mapped_required_count) / Decimal(required_count)).quantize(Decimal("0.01"))


def _normalize(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("：", "")
        .replace(":", "")
    )
