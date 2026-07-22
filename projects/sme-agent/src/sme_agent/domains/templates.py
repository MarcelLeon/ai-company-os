"""Configurable business-domain templates.

The templates are not data warehouses. They define the minimum semantic spine
needed to ingest merchant exports, ask useful questions, and prevent the agent
from treating every spreadsheet as an anonymous table.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from sme_agent.metadata.models import FrozenModel


class DomainKind(StrEnum):
    LIVE_COMMERCE = "live_commerce"
    LOCAL_SERVICES = "local_services"
    PERFORMANCE_ADS = "performance_ads"


class BusinessProcess(StrEnum):
    CONTENT = "content"
    LIVE_ROOM = "live_room"
    PRODUCT = "product"
    ORDER = "order"
    PAYMENT = "payment"
    REFUND = "refund"
    FULFILLMENT = "fulfillment"
    LEAD = "lead"
    STORE_VISIT = "store_visit"
    AD_DELIVERY = "ad_delivery"


class FieldSpec(FrozenModel):
    field_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required: bool = True
    aliases: tuple[str, ...] = ()
    sensitive: bool = False


class DimensionSpec(FrozenModel):
    dimension_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    description: str = Field(min_length=1)
    fields: tuple[FieldSpec, ...] = Field(min_length=1)


class MetricSpec(FrozenModel):
    metric_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    formula: str = Field(min_length=1)
    description: str = Field(min_length=1)
    processes: tuple[BusinessProcess, ...] = Field(min_length=1)
    required_fields: tuple[str, ...] = Field(min_length=1)
    human_checks: tuple[str, ...] = ()


class DomainTemplate(FrozenModel):
    kind: DomainKind
    name: str = Field(min_length=1)
    target_users: tuple[str, ...] = Field(min_length=1)
    supported_processes: tuple[BusinessProcess, ...] = Field(min_length=1)
    dimensions: tuple[DimensionSpec, ...] = Field(min_length=1)
    metrics: tuple[MetricSpec, ...] = Field(min_length=1)
    extension_points: tuple[str, ...] = ()

    def required_field_ids(self) -> tuple[str, ...]:
        ids: list[str] = []
        for dimension in self.dimensions:
            ids.extend(field.field_id for field in dimension.fields if field.required)
        for metric in self.metrics:
            ids.extend(metric.required_fields)
        return tuple(dict.fromkeys(ids))


class DomainTemplateRegistry:
    """A small registry so new verticals do not require agent-runtime rewrites."""

    def __init__(self, templates: tuple[DomainTemplate, ...] = ()) -> None:
        self._templates: dict[DomainKind, DomainTemplate] = {}
        for template in templates:
            self.register(template)

    def register(self, template: DomainTemplate) -> None:
        if template.kind in self._templates:
            raise ValueError(f"duplicate domain template: {template.kind}")
        _validate_unique_ids(template)
        self._templates[template.kind] = template

    def get(self, kind: DomainKind) -> DomainTemplate:
        try:
            return self._templates[kind]
        except KeyError as exc:
            raise ValueError(f"unknown domain template: {kind}") from exc

    def list(self) -> tuple[DomainTemplate, ...]:
        return tuple(self._templates.values())


def build_live_commerce_template() -> DomainTemplate:
    """Template for Douyin/Kuaishou-style live and content commerce merchants."""

    return DomainTemplate(
        kind=DomainKind.LIVE_COMMERCE,
        name="直播/内容电商经营诊断",
        target_users=("抖音/快手中小商家", "直播间主播团队", "内容电商代运营团队"),
        supported_processes=(
            BusinessProcess.CONTENT,
            BusinessProcess.LIVE_ROOM,
            BusinessProcess.PRODUCT,
            BusinessProcess.ORDER,
            BusinessProcess.PAYMENT,
            BusinessProcess.REFUND,
            BusinessProcess.FULFILLMENT,
        ),
        dimensions=(
            _industry_dimension(),
            _seller_dimension(),
            _content_dimension(),
            _live_room_dimension(),
            _product_dimension(),
            _order_dimension(),
            _payment_dimension(),
        ),
        metrics=(
            MetricSpec(
                metric_id="metric.gmv",
                name="GMV",
                formula="sum(order_gross_amount)",
                description="成交总额口径，需确认是否包含未支付、取消或退款订单。",
                processes=(BusinessProcess.ORDER, BusinessProcess.PAYMENT),
                required_fields=("order_gross_amount",),
                human_checks=("确认平台导出的 GMV 是否扣退款。",),
            ),
            MetricSpec(
                metric_id="metric.paid_gmv",
                name="支付 GMV",
                formula="sum(pay_amount where payment_status = paid)",
                description="实际支付成交金额，优先用于经营诊断主口径。",
                processes=(BusinessProcess.PAYMENT,),
                required_fields=("pay_amount", "payment_status"),
                human_checks=("确认支付金额是否包含运费、优惠券、平台补贴。",),
            ),
            MetricSpec(
                metric_id="metric.pay_order_count",
                name="支付订单数",
                formula="count_distinct(order_id where payment_status = paid)",
                description="已支付订单数量。",
                processes=(BusinessProcess.PAYMENT,),
                required_fields=("order_id", "payment_status"),
            ),
            MetricSpec(
                metric_id="metric.pay_buyer_count",
                name="支付买家数",
                formula="count_distinct(buyer_id where payment_status = paid)",
                description="已支付买家数量；需要脱敏 buyer_id。",
                processes=(BusinessProcess.PAYMENT,),
                required_fields=("buyer_id", "payment_status"),
                human_checks=("buyer_id 必须脱敏或替换为不可逆匿名 ID。",),
            ),
            MetricSpec(
                metric_id="metric.average_order_value",
                name="客单价",
                formula="paid_gmv / pay_order_count",
                description="单个支付订单的平均成交金额。",
                processes=(BusinessProcess.PAYMENT,),
                required_fields=("pay_amount", "order_id", "payment_status"),
            ),
            MetricSpec(
                metric_id="metric.refund_rate",
                name="退款率",
                formula="refund_amount / paid_gmv",
                description="退款金额占支付 GMV 的比例。",
                processes=(BusinessProcess.REFUND,),
                required_fields=("refund_amount", "pay_amount"),
                human_checks=("确认是否包含仅退款、退货退款和售后赔付。",),
            ),
            MetricSpec(
                metric_id="metric.gpm",
                name="GPM",
                formula="paid_gmv / live_room_view_count * 1000",
                description="千次直播间观看产生的支付 GMV，用于衡量直播流量成交效率。",
                processes=(BusinessProcess.LIVE_ROOM, BusinessProcess.PAYMENT),
                required_fields=("pay_amount", "live_room_view_count"),
                human_checks=("确认观看人数口径是曝光、进入直播间还是有效观看。",),
            ),
            MetricSpec(
                metric_id="metric.payment_conversion_rate",
                name="支付转化率",
                formula="pay_buyer_count / live_room_view_count",
                description="观看到支付买家的转化效率。",
                processes=(BusinessProcess.LIVE_ROOM, BusinessProcess.PAYMENT),
                required_fields=("buyer_id", "payment_status", "live_room_view_count"),
            ),
        ),
        extension_points=(
            "platform_field_mapping",
            "industry_category_taxonomy",
            "traffic_source_mapping",
            "refund_reason_taxonomy",
            "output_profile",
            "alert_rules",
        ),
    )


def build_local_services_template() -> DomainTemplate:
    return DomainTemplate(
        kind=DomainKind.LOCAL_SERVICES,
        name="本地生活商家经营诊断",
        target_users=("餐饮门店", "到店团购商家", "本地生活服务商家"),
        supported_processes=(
            BusinessProcess.STORE_VISIT,
            BusinessProcess.ORDER,
            BusinessProcess.PAYMENT,
            BusinessProcess.REFUND,
        ),
        dimensions=(
            DimensionSpec(
                dimension_id="dimension.store",
                name="门店",
                scope="seller",
                description="线下门店、商圈和城市。",
                fields=(
                    _field("store_id", "门店 ID", "string", "门店唯一标识"),
                    _field("city", "城市", "string", "门店所在城市"),
                    _field(
                        "business_district",
                        "商圈",
                        "string",
                        "门店所在商圈",
                        False,
                    ),
                ),
            ),
        ),
        metrics=(
            MetricSpec(
                metric_id="metric.verified_gmv",
                name="核销 GMV",
                formula="sum(verified_amount)",
                description="用户到店核销后确认的成交金额。",
                processes=(BusinessProcess.STORE_VISIT, BusinessProcess.PAYMENT),
                required_fields=("verified_amount",),
            ),
        ),
        extension_points=("coupon_mapping", "store_mapping", "verification_status_mapping"),
    )


def build_advertising_template() -> DomainTemplate:
    return DomainTemplate(
        kind=DomainKind.PERFORMANCE_ADS,
        name="商业化广告投放诊断",
        target_users=("中小投放主", "线索行业广告主", "内循环电商投放团队"),
        supported_processes=(
            BusinessProcess.AD_DELIVERY,
            BusinessProcess.LEAD,
            BusinessProcess.PAYMENT,
        ),
        dimensions=(
            DimensionSpec(
                dimension_id="dimension.campaign",
                name="投放计划",
                scope="advertising",
                description="广告账户、计划、单元和素材。",
                fields=(
                    _field("advertiser_id", "广告主 ID", "string", "广告账户标识"),
                    _field("campaign_id", "计划 ID", "string", "广告计划标识"),
                    _field("creative_id", "素材 ID", "string", "广告素材标识", False),
                ),
            ),
            DimensionSpec(
                dimension_id="dimension.lead",
                name="线索",
                scope="lead",
                description="线索提交、有效性和后链路转化。",
                fields=(
                    _field(
                        "lead_id",
                        "线索 ID",
                        "string",
                        "线索唯一标识",
                        sensitive=True,
                    ),
                    _field(
                        "lead_status",
                        "线索状态",
                        "string",
                        "有效、无效、跟进、成交等状态",
                    ),
                ),
            ),
        ),
        metrics=(
            MetricSpec(
                metric_id="metric.ad_spend",
                name="广告消耗",
                formula="sum(ad_spend)",
                description="广告投放消耗。",
                processes=(BusinessProcess.AD_DELIVERY,),
                required_fields=("ad_spend",),
            ),
            MetricSpec(
                metric_id="metric.cost_per_lead",
                name="线索成本",
                formula="ad_spend / valid_lead_count",
                description="每条有效线索的平均获客成本。",
                processes=(BusinessProcess.AD_DELIVERY, BusinessProcess.LEAD),
                required_fields=("ad_spend", "lead_id", "lead_status"),
            ),
        ),
        extension_points=(
            "inner_loop_order_mapping",
            "outer_loop_lead_mapping",
            "creative_taxonomy",
        ),
    )


def _industry_dimension() -> DimensionSpec:
    return DimensionSpec(
        dimension_id="dimension.industry",
        name="行业",
        scope="industry",
        description="平台类目、商品行业、价格带和品牌层级。",
        fields=(
            _field(
                "category_l1",
                "一级类目",
                "string",
                "平台一级行业类目",
                aliases=("行业大类", "主营类目"),
            ),
            _field("category_l2", "二级类目", "string", "平台二级行业类目", False),
            _field("price_band", "价格带", "string", "商品成交价格分层", False),
            _field(
                "brand_type",
                "品牌类型",
                "string",
                "白牌、自有品牌、代理品牌等",
                False,
            ),
        ),
    )


def _seller_dimension() -> DimensionSpec:
    return DimensionSpec(
        dimension_id="dimension.seller",
        name="卖家",
        scope="seller",
        description="店铺、主播团队和经营身份。",
        fields=(
            _field("shop_id", "店铺 ID", "string", "店铺唯一标识", aliases=("店铺ID",)),
            _field("platform", "平台", "string", "抖音、快手或其他平台"),
            _field(
                "seller_type",
                "卖家类型",
                "string",
                "品牌、达人、工厂、个体商家等",
                False,
            ),
            _field(
                "operator_id",
                "运营负责人",
                "string",
                "内部运营负责人",
                False,
                sensitive=True,
            ),
        ),
    )


def _content_dimension() -> DimensionSpec:
    return DimensionSpec(
        dimension_id="dimension.content",
        name="内容",
        scope="content",
        description="短视频、直播切片和内容来源。",
        fields=(
            _field("content_id", "内容 ID", "string", "短视频或内容唯一标识", False),
            _field(
                "traffic_source",
                "流量来源",
                "string",
                "自然、付费、短视频、直播推荐等",
                False,
            ),
        ),
    )


def _live_room_dimension() -> DimensionSpec:
    return DimensionSpec(
        dimension_id="dimension.live_room",
        name="直播间",
        scope="live_room",
        description="直播场次、主播和观看数据。",
        fields=(
            _field(
                "live_session_id",
                "直播场次 ID",
                "string",
                "直播场次唯一标识",
                aliases=("直播场次ID", "场次ID"),
            ),
            _field(
                "anchor_id",
                "主播 ID",
                "string",
                "主播或账号标识",
                aliases=("主播ID", "主播账号"),
            ),
            _field(
                "live_room_view_count",
                "直播间观看人数",
                "integer",
                "直播观看或进入人数",
                aliases=("观看人数", "进入直播间人数"),
            ),
            _field(
                "live_duration_minutes",
                "直播时长",
                "number",
                "直播时长分钟数",
                False,
            ),
        ),
    )


def _product_dimension() -> DimensionSpec:
    return DimensionSpec(
        dimension_id="dimension.product",
        name="商品",
        scope="product",
        description="商品、SKU、成本和库存属性。",
        fields=(
            _field(
                "product_id",
                "商品 ID",
                "string",
                "商品唯一标识",
                aliases=("商品ID",),
            ),
            _field("sku_id", "SKU ID", "string", "SKU 唯一标识", False),
            _field("product_title", "商品标题", "string", "商品名称或标题", False),
            _field("unit_cost", "单位成本", "decimal", "商品单位成本", False),
        ),
    )


def _order_dimension() -> DimensionSpec:
    return DimensionSpec(
        dimension_id="dimension.order",
        name="订单",
        scope="order",
        description="订单创建、状态、商品和渠道归因。",
        fields=(
            _field(
                "order_id",
                "订单 ID",
                "string",
                "订单唯一标识",
                aliases=("订单编号", "订单号"),
            ),
            _field("order_created_at", "下单时间", "datetime", "订单创建时间"),
            _field("order_status", "订单状态", "string", "待支付、已支付、取消、完成等状态"),
            _field("order_gross_amount", "订单金额", "decimal", "订单原始成交金额"),
            _field(
                "buyer_id",
                "买家 ID",
                "string",
                "买家匿名标识",
                False,
                sensitive=True,
                aliases=("买家匿名ID", "用户匿名ID"),
            ),
        ),
    )


def _payment_dimension() -> DimensionSpec:
    return DimensionSpec(
        dimension_id="dimension.payment",
        name="支付",
        scope="payment",
        description="支付状态、支付金额、退款金额和支付时间。",
        fields=(
            _field("payment_status", "支付状态", "string", "未支付、已支付、退款等状态"),
            _field("paid_at", "支付时间", "datetime", "支付完成时间", False),
            _field("pay_amount", "支付金额", "decimal", "实际支付金额"),
            _field("refund_amount", "退款金额", "decimal", "退款或售后金额", False),
        ),
    )


def _field(
    field_id: str,
    name: str,
    data_type: str,
    description: str,
    required: bool = True,
    *,
    aliases: tuple[str, ...] = (),
    sensitive: bool = False,
) -> FieldSpec:
    return FieldSpec(
        field_id=field_id,
        name=name,
        data_type=data_type,
        description=description,
        required=required,
        aliases=aliases,
        sensitive=sensitive,
    )


def _validate_unique_ids(template: DomainTemplate) -> None:
    dimension_ids = [dimension.dimension_id for dimension in template.dimensions]
    metric_ids = [metric.metric_id for metric in template.metrics]
    field_ids = [field.field_id for dimension in template.dimensions for field in dimension.fields]
    for label, values in (
        ("dimension", dimension_ids),
        ("metric", metric_ids),
        ("field", field_ids),
    ):
        duplicates = _duplicates(values)
        if duplicates:
            raise ValueError(f"duplicate {label} ids: {', '.join(duplicates)}")


def _duplicates(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return tuple(duplicates)
