"""Allowed relationship signatures for the governed metadata graph."""

from __future__ import annotations

from sme_agent.metadata.models import MetadataKind, RelationKind

RelationSignature = tuple[MetadataKind, MetadataKind]

RELATION_SIGNATURES: dict[RelationKind, frozenset[RelationSignature]] = {
    RelationKind.DEFINES: frozenset(
        {
            (MetadataKind.GLOSSARY_TERM, MetadataKind.METRIC),
            (MetadataKind.GLOSSARY_TERM, MetadataKind.DIMENSION),
            (MetadataKind.GLOSSARY_TERM, MetadataKind.BUSINESS_ENTITY),
        }
    ),
    RelationKind.MEASURED_BY: frozenset({(MetadataKind.BUSINESS_ENTITY, MetadataKind.METRIC)}),
    RelationKind.SLICED_BY: frozenset({(MetadataKind.METRIC, MetadataKind.DIMENSION)}),
    RelationKind.SOURCED_FROM: frozenset({(MetadataKind.METRIC, MetadataKind.WAREHOUSE_ASSET)}),
    RelationKind.DESCRIBED_BY: frozenset(
        {
            (MetadataKind.METRIC, MetadataKind.KNOWLEDGE_DOCUMENT),
            (MetadataKind.DIMENSION, MetadataKind.KNOWLEDGE_DOCUMENT),
            (MetadataKind.WAREHOUSE_ASSET, MetadataKind.KNOWLEDGE_DOCUMENT),
            (MetadataKind.BUSINESS_ENTITY, MetadataKind.KNOWLEDGE_DOCUMENT),
        }
    ),
    RelationKind.BELONGS_TO: frozenset(
        {(MetadataKind.WAREHOUSE_ASSET, MetadataKind.BUSINESS_ENTITY)}
    ),
    RelationKind.RELATED_TO: frozenset(),
}


def validate_relation_signature(
    relation_kind: RelationKind,
    source_kind: MetadataKind,
    target_kind: MetadataKind,
) -> None:
    if relation_kind is RelationKind.RELATED_TO:
        return
    signature = (source_kind, target_kind)
    if signature not in RELATION_SIGNATURES[relation_kind]:
        raise ValueError(
            "invalid metadata relation signature: "
            f"{source_kind.value} -[{relation_kind.value}]-> {target_kind.value}"
        )
