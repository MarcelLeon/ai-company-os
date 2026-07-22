from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from sme_agent.adapters.in_memory_metadata import InMemoryMetadataRepository
from sme_agent.application import DimensionFilter, GroundingRequest, MetadataGroundingService
from sme_agent.commercialization import (
    BusinessPain,
    CustomerIntake,
    CustomerProjectSpec,
    DataAssetSubmission,
    EcommerceCsvLoader,
    EcommerceDeliveryInput,
    EcommerceDeliveryRunner,
    EcommerceDiagnosisService,
    EcommerceReportMarkdownRenderer,
    EvidenceItem,
    EvidenceManifestService,
    IntakeAssessmentService,
    ProjectWorkspaceService,
    RedactionScanner,
    ReportTemplateService,
    ServiceTier,
)
from sme_agent.metadata import MetadataCatalog
from sme_agent.samples import load_east_china_revenue_sample

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_intake_assessment_recommends_standard_report_when_data_is_ready() -> None:
    intake = CustomerIntake(
        company_name="样例商家",
        contact_channel="千牛",
        industry="电商零售",
        monthly_order_volume=1200,
        pains=(BusinessPain.REVENUE_DROP, BusinessPain.AD_ROI),
        primary_question="华东区本月收入为什么下降？",
        data_assets=(
            DataAssetSubmission(
                name="订单明细",
                business_meaning="近三个月订单收入和退款",
                format="xlsx",
            ),
            DataAssetSubmission(
                name="广告消耗",
                business_meaning="投放渠道消耗和成交金额",
                format="csv",
            ),
            DataAssetSubmission(
                name="商品库存",
                business_meaning="商品库存和近 30 天销量",
                format="xlsx",
            ),
        ),
        has_authorized_analysis=True,
        allows_anonymized_case_study=True,
    )

    assessment = IntakeAssessmentService().assess(intake)

    assert assessment.tier is ServiceTier.STANDARD_REPORT
    assert assessment.score >= 80
    assert assessment.missing_items == ()
    assert assessment.human_review_required is True
    assert any("广告投放数据" in item for item in assessment.recommended_next_questions)


def test_intake_assessment_rejects_unauthorized_or_missing_data() -> None:
    intake = CustomerIntake(
        company_name="样例商家",
        contact_channel="小红书私信",
        industry="本地生活",
        pains=(BusinessPain.CASHFLOW,),
        primary_question="现金流",
    )

    assessment = IntakeAssessmentService().assess(intake)

    assert assessment.tier is ServiceTier.NOT_READY
    assert "客户需明确授权基于其提交数据做经营诊断" in assessment.missing_items
    assert "至少需要一份订单、客户、库存、广告或财务相关数据" in assessment.missing_items


def test_customer_intake_rejects_authorization_without_data_assets() -> None:
    with pytest.raises(ValueError, match="requires at least one submitted data asset"):
        CustomerIntake(
            company_name="样例商家",
            contact_channel="千牛",
            industry="电商零售",
            pains=(BusinessPain.REVENUE_DROP,),
            primary_question="最近一个月收入为什么下降？",
            has_authorized_analysis=True,
        )


def test_report_outline_uses_grounding_without_inventing_conclusions() -> None:
    catalog = MetadataCatalog(InMemoryMetadataRepository())
    load_east_china_revenue_sample(catalog)
    grounding = MetadataGroundingService(catalog).ground(
        GroundingRequest(
            question="华东区本月收入为什么下降？",
            metric_query="营业收入",
            filters=(
                DimensionFilter(dimension_query="地区", value="华东区"),
                DimensionFilter(dimension_query="月份", value="本月"),
            ),
        )
    )

    outline = ReportTemplateService().outline_from_grounding(grounding)

    assert outline.title == "Revenue经营诊断报告"
    assert outline.evidence_ids == grounding.evidence_ids
    assert len(outline.sections) == 4
    assert any("不是财务、税务、法律或投资建议" in item for item in outline.disclaimers)


def test_ecommerce_diagnosis_generates_traceable_findings_from_sample_data() -> None:
    sample_dir = PROJECT_ROOT / "sample_data" / "ecommerce_week_one"
    loader = EcommerceCsvLoader()

    report = EcommerceDiagnosisService().diagnose(
        primary_question="最近收入下降是不是广告投放导致的？",
        orders=loader.load_orders(sample_dir / "orders.csv"),
        ad_spend=loader.load_ad_spend(sample_dir / "ad_spend.csv"),
        inventory=loader.load_inventory(sample_dir / "inventory.csv"),
    )

    assert report.metrics.order_count == 8
    assert report.metrics.net_revenue == Decimal("2120")
    assert report.metrics.refund_rate >= Decimal("0.1")
    assert report.metrics.roas is not None
    assert report.metrics.roas < Decimal("2")
    assert report.metrics.slow_mover_count == 2
    assert any("退款率偏高" in finding.title for finding in report.findings)
    assert any("广告 ROAS 偏低" in finding.title for finding in report.findings)
    assert any("滞销库存" in finding.title for finding in report.findings)


def test_ecommerce_report_renderer_keeps_human_review_boundary() -> None:
    sample_dir = PROJECT_ROOT / "sample_data" / "ecommerce_week_one"
    loader = EcommerceCsvLoader()
    report = EcommerceDiagnosisService().diagnose(
        primary_question="最近收入下降是不是广告投放导致的？",
        orders=loader.load_orders(sample_dir / "orders.csv"),
        ad_spend=loader.load_ad_spend(sample_dir / "ad_spend.csv"),
        inventory=loader.load_inventory(sample_dir / "inventory.csv"),
    )

    markdown = EcommerceReportMarkdownRenderer().render(report)

    assert "# AI 电商经营诊断报告（人工复核草稿）" in markdown
    assert "## 必须人工确认" in markdown
    assert "不能替代财务、税务、法律或投资建议" in markdown
    assert "建议动作" in markdown


def test_project_workspace_service_creates_repeatable_delivery_structure(tmp_path: Path) -> None:
    spec = CustomerProjectSpec(
        customer_id="seed-shop-001",
        display_name="种子电商店",
        primary_question="最近收入下降是不是广告投放导致的？",
        service_tier="standard_report",
    )

    workspace = ProjectWorkspaceService().create(tmp_path, spec)

    assert workspace.root.name == "seed-shop-001"
    assert workspace.raw_dir.is_dir()
    assert workspace.work_dir.is_dir()
    assert workspace.delivery_dir.is_dir()
    assert workspace.intake_path.read_text(encoding="utf-8").startswith("# 种子电商店 intake")
    assert workspace.evidence_manifest_path.parent == workspace.delivery_dir


def test_evidence_manifest_service_writes_buyer_visible_sources(tmp_path: Path) -> None:
    spec = CustomerProjectSpec(
        customer_id="seed-shop-001",
        display_name="种子电商店",
        primary_question="最近收入下降是不是广告投放导致的？",
        service_tier="standard_report",
    )
    workspace = ProjectWorkspaceService().create(tmp_path, spec)
    manifest = EvidenceManifestService().build(
        customer_id=spec.customer_id,
        primary_question=spec.primary_question,
        evidence=(
            EvidenceItem(
                evidence_id="orders-2026-06",
                source_name="orders.csv",
                source_type="order_export",
                business_meaning="订单成交与退款明细",
            ),
        ),
        limitations=("广告归因口径待客户确认。",),
    )

    written_path = EvidenceManifestService().write(workspace, manifest)
    rendered = written_path.read_text(encoding="utf-8")

    assert written_path == workspace.evidence_manifest_path
    assert "orders-2026-06" in rendered
    assert "订单成交与退款明细" in rendered
    assert "广告归因口径待客户确认" in rendered


def test_redaction_scanner_flags_sensitive_headers() -> None:
    checklist = RedactionScanner().scan_headers(
        ("order_id", "buyer_phone", "收货地址", "sku", "gross_revenue")
    )

    assert checklist.has_risk is True
    assert {finding.field_name for finding in checklist.findings} == {"buyer_phone", "收货地址"}
    assert all("匿名 ID" in finding.suggested_action for finding in checklist.findings)


def test_ecommerce_delivery_runner_generates_workspace_report_and_manifest(tmp_path: Path) -> None:
    sample_dir = PROJECT_ROOT / "sample_data" / "ecommerce_week_one"

    result = EcommerceDeliveryRunner().run(
        EcommerceDeliveryInput(
            output_dir=tmp_path,
            customer_id="seed-shop-001",
            display_name="种子电商店",
            primary_question="最近收入下降是不是广告投放导致的？",
            orders_csv=sample_dir / "orders.csv",
            ad_spend_csv=sample_dir / "ad_spend.csv",
            inventory_csv=sample_dir / "inventory.csv",
        )
    )

    assert result.workspace.root.is_dir()
    assert result.report_path.exists()
    assert result.evidence_manifest_path.exists()
    assert "AI 电商经营诊断报告" in result.report_path.read_text(encoding="utf-8")
    assert "orders.csv" in result.evidence_manifest_path.read_text(encoding="utf-8")
    assert result.redaction_checklist.has_risk is False
