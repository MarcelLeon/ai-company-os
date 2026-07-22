"""Immutable domain objects for governed enterprise metadata."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MetadataKind(StrEnum):
    GLOSSARY_TERM = "glossary_term"
    KNOWLEDGE_DOCUMENT = "knowledge_document"
    METRIC = "metric"
    DIMENSION = "dimension"
    WAREHOUSE_ASSET = "warehouse_asset"
    BUSINESS_ENTITY = "business_entity"


class GovernanceStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class RelationKind(StrEnum):
    DEFINES = "defines"
    MEASURED_BY = "measured_by"
    SLICED_BY = "sliced_by"
    SOURCED_FROM = "sourced_from"
    DESCRIBED_BY = "described_by"
    BELONGS_TO = "belongs_to"
    RELATED_TO = "related_to"


class CatalogAsset(FrozenModel):
    asset_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: MetadataKind
    description: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    owner: str | None = None
    tags: tuple[str, ...] = ()
    version: int = Field(default=1, ge=1)
    governance_status: GovernanceStatus = GovernanceStatus.DRAFT
    source_refs: tuple[str, ...] = ()
    approved_by: str | None = None

    @model_validator(mode="after")
    def _approved_assets_require_human_evidence(self) -> CatalogAsset:
        if self.governance_status is not GovernanceStatus.APPROVED:
            return self
        if not self.approved_by:
            raise ValueError("approved metadata requires approved_by")
        if not self.source_refs:
            raise ValueError("approved metadata requires source_refs")
        return self


class GlossaryTerm(CatalogAsset):
    kind: Literal[MetadataKind.GLOSSARY_TERM] = MetadataKind.GLOSSARY_TERM


class KnowledgeDocument(CatalogAsset):
    kind: Literal[MetadataKind.KNOWLEDGE_DOCUMENT] = MetadataKind.KNOWLEDGE_DOCUMENT
    source_uri: str = Field(min_length=1)


class Metric(CatalogAsset):
    kind: Literal[MetadataKind.METRIC] = MetadataKind.METRIC
    formula: str = Field(min_length=1)
    aggregation: str = Field(min_length=1)


class Dimension(CatalogAsset):
    kind: Literal[MetadataKind.DIMENSION] = MetadataKind.DIMENSION
    data_type: str = Field(min_length=1)


class WarehouseAsset(CatalogAsset):
    kind: Literal[MetadataKind.WAREHOUSE_ASSET] = MetadataKind.WAREHOUSE_ASSET
    platform: str = Field(min_length=1)
    qualified_name: str = Field(min_length=1)


class BusinessEntity(CatalogAsset):
    kind: Literal[MetadataKind.BUSINESS_ENTITY] = MetadataKind.BUSINESS_ENTITY
    identifier_fields: tuple[str, ...] = Field(min_length=1)


class MetadataRelation(FrozenModel):
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    kind: RelationKind
    description: str | None = None
