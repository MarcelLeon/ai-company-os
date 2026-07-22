"""Business-domain templates for SME Agent vertical adaptation."""

from sme_agent.domains.mapping import (
    DomainFieldMappingService,
    FieldMapping,
    FieldMappingReport,
)
from sme_agent.domains.templates import (
    BusinessProcess,
    DimensionSpec,
    DomainKind,
    DomainTemplate,
    DomainTemplateRegistry,
    FieldSpec,
    MetricSpec,
    build_advertising_template,
    build_live_commerce_template,
    build_local_services_template,
)

__all__ = [
    "BusinessProcess",
    "DimensionSpec",
    "DomainFieldMappingService",
    "DomainKind",
    "DomainTemplate",
    "DomainTemplateRegistry",
    "FieldMapping",
    "FieldMappingReport",
    "FieldSpec",
    "MetricSpec",
    "build_advertising_template",
    "build_live_commerce_template",
    "build_local_services_template",
]
