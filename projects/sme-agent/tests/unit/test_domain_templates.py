from __future__ import annotations

import pytest

from sme_agent.domains import (
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


def test_live_commerce_template_contains_seller_order_payment_and_live_metrics() -> None:
    template = build_live_commerce_template()

    dimension_ids = {dimension.dimension_id for dimension in template.dimensions}
    metric_ids = {metric.metric_id for metric in template.metrics}
    required_fields = set(template.required_field_ids())

    assert template.kind is DomainKind.LIVE_COMMERCE
    assert {
        "dimension.industry",
        "dimension.seller",
        "dimension.live_room",
        "dimension.order",
        "dimension.payment",
    }.issubset(dimension_ids)
    assert {
        "metric.gmv",
        "metric.paid_gmv",
        "metric.pay_order_count",
        "metric.pay_buyer_count",
        "metric.average_order_value",
        "metric.refund_rate",
        "metric.gpm",
        "metric.payment_conversion_rate",
    }.issubset(metric_ids)
    assert {"shop_id", "order_id", "pay_amount", "payment_status"}.issubset(required_fields)
    assert "alert_rules" in template.extension_points


def test_live_commerce_template_marks_buyer_and_operator_identifiers_sensitive() -> None:
    template = build_live_commerce_template()
    sensitive_fields = {
        field.field_id
        for dimension in template.dimensions
        for field in dimension.fields
        if field.sensitive
    }

    assert "buyer_id" in sensitive_fields
    assert "operator_id" in sensitive_fields


def test_registry_supports_future_vertical_templates_without_runtime_rewrite() -> None:
    registry = DomainTemplateRegistry(
        (
            build_live_commerce_template(),
            build_local_services_template(),
            build_advertising_template(),
        )
    )

    assert registry.get(DomainKind.LOCAL_SERVICES).name == "本地生活商家经营诊断"
    assert registry.get(DomainKind.PERFORMANCE_ADS).name == "商业化广告投放诊断"
    assert len(registry.list()) == 3


def test_registry_rejects_duplicate_template_kind() -> None:
    registry = DomainTemplateRegistry((build_live_commerce_template(),))

    with pytest.raises(ValueError, match="duplicate domain template"):
        registry.register(build_live_commerce_template())


def test_registry_rejects_duplicate_field_ids_inside_template() -> None:
    duplicate_template = DomainTemplate(
        kind=DomainKind.LIVE_COMMERCE,
        name="bad",
        target_users=("test",),
        supported_processes=(BusinessProcess.ORDER,),
        dimensions=(
            DimensionSpec(
                dimension_id="dimension.bad",
                name="bad",
                scope="bad",
                description="bad",
                fields=(
                    FieldSpec(
                        field_id="order_id",
                        name="订单 ID",
                        data_type="string",
                        description="订单",
                    ),
                    FieldSpec(
                        field_id="order_id",
                        name="订单 ID again",
                        data_type="string",
                        description="重复",
                    ),
                ),
            ),
        ),
        metrics=(
            MetricSpec(
                metric_id="metric.bad",
                name="bad",
                formula="sum(x)",
                description="bad",
                processes=(BusinessProcess.ORDER,),
                required_fields=("order_id",),
            ),
        ),
    )

    with pytest.raises(ValueError, match="duplicate field ids"):
        DomainTemplateRegistry((duplicate_template,))
