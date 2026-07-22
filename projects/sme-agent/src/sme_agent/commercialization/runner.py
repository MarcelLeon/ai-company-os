"""Library entrypoint for generating a week-one ecommerce delivery package."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from sme_agent.commercialization.delivery import (
    CustomerProjectSpec,
    EvidenceItem,
    EvidenceManifestService,
    ProjectWorkspace,
    ProjectWorkspaceService,
    RedactionChecklist,
    RedactionScanner,
)
from sme_agent.commercialization.ecommerce_diagnosis import (
    EcommerceCsvLoader,
    EcommerceDiagnosisService,
    EcommerceReportMarkdownRenderer,
)
from sme_agent.metadata.models import FrozenModel


class EcommerceDeliveryInput(FrozenModel):
    output_dir: Path
    customer_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    primary_question: str = Field(min_length=1)
    service_tier: str = Field(default="standard_report", min_length=1)
    orders_csv: Path
    ad_spend_csv: Path | None = None
    inventory_csv: Path | None = None


class EcommerceDeliveryResult(FrozenModel):
    workspace: ProjectWorkspace
    report_path: Path
    evidence_manifest_path: Path
    redaction_checklist: RedactionChecklist


class EcommerceDeliveryRunner:
    """Generate the first customer-facing delivery artifacts from CSV paths."""

    def run(self, delivery_input: EcommerceDeliveryInput) -> EcommerceDeliveryResult:
        workspace = ProjectWorkspaceService().create(
            delivery_input.output_dir,
            CustomerProjectSpec(
                customer_id=delivery_input.customer_id,
                display_name=delivery_input.display_name,
                primary_question=delivery_input.primary_question,
                service_tier=delivery_input.service_tier,
            ),
        )
        loader = EcommerceCsvLoader()
        orders = loader.load_orders(delivery_input.orders_csv)
        ad_spend = (
            loader.load_ad_spend(delivery_input.ad_spend_csv)
            if delivery_input.ad_spend_csv is not None
            else ()
        )
        inventory = (
            loader.load_inventory(delivery_input.inventory_csv)
            if delivery_input.inventory_csv is not None
            else ()
        )
        report = EcommerceDiagnosisService().diagnose(
            primary_question=delivery_input.primary_question,
            orders=orders,
            ad_spend=ad_spend,
            inventory=inventory,
        )
        report_path = workspace.diagnosis_draft_path
        report_path.write_text(EcommerceReportMarkdownRenderer().render(report), encoding="utf-8")
        manifest = EvidenceManifestService().build(
            customer_id=delivery_input.customer_id,
            primary_question=delivery_input.primary_question,
            evidence=self._evidence(delivery_input),
            limitations=(
                "本交付包基于客户提供 CSV 文件生成，字段含义仍需人工复核。",
                "广告归因、收入口径、库存季节性必须由客户或交付人确认。",
            ),
        )
        evidence_path = EvidenceManifestService().write(workspace, manifest)
        return EcommerceDeliveryResult(
            workspace=workspace,
            report_path=report_path,
            evidence_manifest_path=evidence_path,
            redaction_checklist=self._redaction_checklist(loader, delivery_input.orders_csv),
        )

    def _evidence(self, delivery_input: EcommerceDeliveryInput) -> tuple[EvidenceItem, ...]:
        items = [
            EvidenceItem(
                evidence_id="orders",
                source_name=delivery_input.orders_csv.name,
                source_type="order_export",
                business_meaning="订单成交、渠道、地区、商品和退款明细",
            )
        ]
        if delivery_input.ad_spend_csv is not None:
            items.append(
                EvidenceItem(
                    evidence_id="ad_spend",
                    source_name=delivery_input.ad_spend_csv.name,
                    source_type="ad_export",
                    business_meaning="广告消耗和归因成交金额",
                )
            )
        if delivery_input.inventory_csv is not None:
            items.append(
                EvidenceItem(
                    evidence_id="inventory",
                    source_name=delivery_input.inventory_csv.name,
                    source_type="inventory_export",
                    business_meaning="SKU 库存、近 30 天销量和单位成本",
                )
            )
        return tuple(items)

    def _redaction_checklist(
        self, loader: EcommerceCsvLoader, orders_csv: Path
    ) -> RedactionChecklist:
        return RedactionScanner().scan_headers(loader.headers(orders_csv))
