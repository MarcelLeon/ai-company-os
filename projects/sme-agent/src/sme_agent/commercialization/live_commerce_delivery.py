"""Run-scoped, governed delivery workspaces for live-commerce diagnosis."""

from __future__ import annotations

import hashlib
import shutil
from enum import StrEnum
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
from sme_agent.commercialization.live_commerce_diagnosis import (
    LiveCommerceReportMarkdownRenderer,
)
from sme_agent.commercialization.live_commerce_intake import (
    IntakeReadiness,
    LiveCommerceCsvIntakeService,
    LiveCommerceIntakeAssessment,
)
from sme_agent.metadata.models import FrozenModel


class LiveCommerceDeliveryStatus(StrEnum):
    """Commercial handoff states that remain clear under owner absence."""

    READY_FOR_HUMAN_REVIEW = "ready_for_human_review"
    BLOCKED_MISSING_FIELDS = "blocked_missing_fields"
    BLOCKED_NO_ROWS = "blocked_no_rows"
    BLOCKED_REDACTION = "blocked_redaction"


class LiveCommerceDeliveryInput(FrozenModel):
    """Authorized inputs for one immutable customer diagnosis run."""

    output_dir: Path
    customer_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    display_name: str = Field(min_length=1)
    run_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    primary_question: str = Field(min_length=1)
    authorization_reference: str = Field(min_length=1)
    live_sessions_csv: Path
    orders_csv: Path
    service_tier: str = Field(default="intro_diagnosis", min_length=1)
    persist_source_files: bool = False


class LiveCommerceDeliveryResult(FrozenModel):
    """Paths and state needed for a human or AICO handoff."""

    status: LiveCommerceDeliveryStatus
    workspace: ProjectWorkspace
    mapping_report_path: Path
    missing_field_questions_path: Path
    redaction_checklist_path: Path
    evidence_manifest_path: Path
    delivery_status_path: Path
    report_path: Path | None
    persisted_source_paths: tuple[Path, ...]


class LiveCommerceDeliveryArtifactPreview(FrozenModel):
    """One file promised by a future immutable delivery run."""

    path: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    included: bool


class LiveCommerceDeliveryPreview(FrozenModel):
    """Non-persistent package contract shown before owner acceptance."""

    status: LiveCommerceDeliveryStatus
    artifacts: tuple[LiveCommerceDeliveryArtifactPreview, ...]
    redaction_fields: tuple[str, ...]
    next_action: str = Field(min_length=1)
    creates_workspace: bool = False
    raw_retention_default: bool = False
    authorization_reference_required: bool = True


def preview_live_commerce_delivery(
    assessment: LiveCommerceIntakeAssessment,
) -> LiveCommerceDeliveryPreview:
    """Preview the runner's status and files without writing customer state."""
    redaction = RedactionScanner().scan_headers(
        assessment.live_sessions_profile.headers + assessment.orders_profile.headers
    )
    status = _delivery_status(assessment.readiness, redaction)
    return LiveCommerceDeliveryPreview(
        status=status,
        artifacts=_preview_artifacts(status),
        redaction_fields=tuple(finding.field_name for finding in redaction.findings),
        next_action=_preview_next_action(status),
    )


class LiveCommerceDeliveryRunner:
    """Create one auditable delivery run without silently retaining raw data."""

    def run(self, delivery_input: LiveCommerceDeliveryInput) -> LiveCommerceDeliveryResult:
        self._validate_run_target(delivery_input)
        self._validate_authorization(delivery_input.authorization_reference)
        session_bytes, session_text = _read_utf8(delivery_input.live_sessions_csv)
        order_bytes, order_text = _read_utf8(delivery_input.orders_csv)
        assessment = LiveCommerceCsvIntakeService().assess(
            primary_question=delivery_input.primary_question,
            live_sessions_csv=session_text,
            orders_csv=order_text,
        )
        redaction = RedactionScanner().scan_headers(
            assessment.live_sessions_profile.headers + assessment.orders_profile.headers
        )
        status = _delivery_status(assessment.readiness, redaction)
        workspace = self._create_workspace(delivery_input)
        _write_derived_artifacts(workspace, assessment, redaction)
        persisted = self._persist_sources_if_allowed(
            delivery_input,
            workspace,
            status,
        )
        report_path = self._write_report_if_ready(workspace, assessment, status)
        manifest_path = self._write_manifest(
            delivery_input,
            workspace,
            assessment,
            status,
            session_bytes,
            order_bytes,
            persisted,
        )
        workspace.delivery_status_path.write_text(
            _render_delivery_status(status, report_path, persisted),
            encoding="utf-8",
        )
        return LiveCommerceDeliveryResult(
            status=status,
            workspace=workspace,
            mapping_report_path=workspace.mapping_report_path,
            missing_field_questions_path=workspace.missing_field_questions_path,
            redaction_checklist_path=workspace.redaction_checklist_path,
            evidence_manifest_path=manifest_path,
            delivery_status_path=workspace.delivery_status_path,
            report_path=report_path,
            persisted_source_paths=persisted,
        )

    @staticmethod
    def _validate_run_target(delivery_input: LiveCommerceDeliveryInput) -> None:
        target = (
            delivery_input.output_dir / delivery_input.customer_id / "runs" / delivery_input.run_id
        )
        if target.exists():
            raise FileExistsError(
                f"run already exists: {delivery_input.customer_id}/{delivery_input.run_id}"
            )

    @staticmethod
    def _validate_authorization(reference: str) -> None:
        if not reference.strip():
            raise ValueError("authorization_reference must not be blank")

    @staticmethod
    def _create_workspace(delivery_input: LiveCommerceDeliveryInput) -> ProjectWorkspace:
        return ProjectWorkspaceService().create(
            delivery_input.output_dir,
            CustomerProjectSpec(
                customer_id=delivery_input.customer_id,
                display_name=delivery_input.display_name,
                primary_question=delivery_input.primary_question,
                service_tier=delivery_input.service_tier,
                run_id=delivery_input.run_id,
                authorization_reference=delivery_input.authorization_reference,
            ),
        )

    @staticmethod
    def _persist_sources_if_allowed(
        delivery_input: LiveCommerceDeliveryInput,
        workspace: ProjectWorkspace,
        status: LiveCommerceDeliveryStatus,
    ) -> tuple[Path, ...]:
        if (
            status is not LiveCommerceDeliveryStatus.READY_FOR_HUMAN_REVIEW
            or not delivery_input.persist_source_files
        ):
            return ()
        destinations = (
            workspace.raw_dir / "live_sessions.csv",
            workspace.raw_dir / "orders.csv",
        )
        for source, destination in zip(
            (delivery_input.live_sessions_csv, delivery_input.orders_csv),
            destinations,
            strict=True,
        ):
            _atomic_copy(source, destination)
        return destinations

    @staticmethod
    def _write_report_if_ready(
        workspace: ProjectWorkspace,
        assessment: LiveCommerceIntakeAssessment,
        status: LiveCommerceDeliveryStatus,
    ) -> Path | None:
        if status is not LiveCommerceDeliveryStatus.READY_FOR_HUMAN_REVIEW:
            return None
        if assessment.report is None:
            raise RuntimeError("ready delivery is missing its diagnosis report")
        workspace.diagnosis_draft_path.write_text(
            LiveCommerceReportMarkdownRenderer().render(assessment.report),
            encoding="utf-8",
        )
        return workspace.diagnosis_draft_path

    @staticmethod
    def _write_manifest(
        delivery_input: LiveCommerceDeliveryInput,
        workspace: ProjectWorkspace,
        assessment: LiveCommerceIntakeAssessment,
        status: LiveCommerceDeliveryStatus,
        session_bytes: bytes,
        order_bytes: bytes,
        persisted: tuple[Path, ...],
    ) -> Path:
        retained = bool(persisted)
        manifest = EvidenceManifestService().build(
            customer_id=delivery_input.customer_id,
            primary_question=delivery_input.primary_question,
            evidence=(
                _evidence_item(
                    "live-sessions",
                    delivery_input.live_sessions_csv,
                    "live_session_export",
                    "直播场次、主播和观看人数",
                    session_bytes,
                    assessment.live_sessions_profile.row_count,
                    retained,
                    "raw/live_sessions.csv" if retained else None,
                ),
                _evidence_item(
                    "orders",
                    delivery_input.orders_csv,
                    "live_order_export",
                    "直播订单、支付、退款和匿名买家",
                    order_bytes,
                    assessment.orders_profile.row_count,
                    retained,
                    "raw/orders.csv" if retained else None,
                ),
            ),
            limitations=_manifest_limitations(status),
        )
        return EvidenceManifestService().write(workspace, manifest)


def _read_utf8(path: Path) -> tuple[bytes, str]:
    if not path.is_file():
        raise ValueError(f"CSV source is not a file: {path}")
    content = path.read_bytes()
    try:
        return content, content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"CSV source must use UTF-8 encoding: {path.name}") from exc


def _delivery_status(
    readiness: IntakeReadiness,
    redaction: RedactionChecklist,
) -> LiveCommerceDeliveryStatus:
    if redaction.has_risk:
        return LiveCommerceDeliveryStatus.BLOCKED_REDACTION
    if readiness is IntakeReadiness.BLOCKED_MISSING_FIELDS:
        return LiveCommerceDeliveryStatus.BLOCKED_MISSING_FIELDS
    if readiness is IntakeReadiness.BLOCKED_NO_ROWS:
        return LiveCommerceDeliveryStatus.BLOCKED_NO_ROWS
    return LiveCommerceDeliveryStatus.READY_FOR_HUMAN_REVIEW


def _preview_artifacts(
    status: LiveCommerceDeliveryStatus,
) -> tuple[LiveCommerceDeliveryArtifactPreview, ...]:
    always = (
        ("intake.md", "客户、run、服务档位、经营问题和授权引用"),
        ("work/field-mapping.md", "字段映射、覆盖率、行数和可计算指标"),
        ("work/missing-field-questions.md", "缺字段或无数据时的补数问题"),
        ("delivery/redaction-checklist.md", "直接个人信息风险和处理动作"),
        ("delivery/evidence-manifest.md", "来源文件名、行数、SHA-256 和限制"),
        ("delivery/delivery-status.md", "当前状态、是否有报告和下一行动"),
    )
    artifacts = [
        LiveCommerceDeliveryArtifactPreview(path=path, purpose=purpose, included=True)
        for path, purpose in always
    ]
    artifacts.append(
        LiveCommerceDeliveryArtifactPreview(
            path="work/diagnosis-draft.md",
            purpose="可人工复核的经营诊断草稿",
            included=status is LiveCommerceDeliveryStatus.READY_FOR_HUMAN_REVIEW,
        )
    )
    return tuple(artifacts)


def _preview_next_action(status: LiveCommerceDeliveryStatus) -> str:
    if status is LiveCommerceDeliveryStatus.BLOCKED_REDACTION:
        return "删除、打码或不可逆匿名化直接个人信息字段，然后重新检查。"
    if status in {
        LiveCommerceDeliveryStatus.BLOCKED_MISSING_FIELDS,
        LiveCommerceDeliveryStatus.BLOCKED_NO_ROWS,
    }:
        return "按补数问题完善脱敏导出，然后重新检查。"
    return "由商家或数据负责人复核平台口径、证据和结论，再决定是否交付。"


def _write_derived_artifacts(
    workspace: ProjectWorkspace,
    assessment: LiveCommerceIntakeAssessment,
    redaction: RedactionChecklist,
) -> None:
    workspace.mapping_report_path.write_text(_render_mapping(assessment), encoding="utf-8")
    workspace.missing_field_questions_path.write_text(
        _render_questions(assessment.follow_up_questions),
        encoding="utf-8",
    )
    workspace.redaction_checklist_path.write_text(
        _render_redaction(redaction),
        encoding="utf-8",
    )


def _render_mapping(assessment: LiveCommerceIntakeAssessment) -> str:
    mapping = assessment.mapping_report
    coverage = int(mapping.required_coverage_ratio * 100)
    lines = [
        "# Field mapping",
        "",
        f"- Template: {mapping.template_name}",
        f"- Required coverage: {coverage}%",
        f"- Live-session rows: {assessment.live_sessions_profile.row_count}",
        f"- Order rows: {assessment.orders_profile.row_count}",
        f"- Computable metrics: {', '.join(mapping.computable_metric_ids) or 'none'}",
        f"- Sensitive source columns: {', '.join(mapping.sensitive_source_columns) or 'none'}",
        "",
        "## Mapped fields",
    ]
    lines.extend(f"- {item.field_id} <- {item.source_column}" for item in mapping.mappings)
    lines.extend(["", "## Missing required fields"])
    lines.extend(f"- {field_id}" for field_id in mapping.missing_required_fields)
    if not mapping.missing_required_fields:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _render_questions(questions: tuple[str, ...]) -> str:
    lines = ["# Missing-field questions", ""]
    if questions:
        lines.extend(f"{index}. {question}" for index, question in enumerate(questions, 1))
    else:
        lines.append("- none; required field and row readiness checks passed")
    return "\n".join(lines) + "\n"


def _render_redaction(checklist: RedactionChecklist) -> str:
    lines = ["# Redaction checklist", ""]
    if not checklist.findings:
        lines.extend(
            [
                "- Obvious direct-personal-data headers: none detected",
                "- Human confirmation is still required before delivery.",
            ]
        )
    else:
        lines.append("- Delivery is blocked until the following fields are removed or anonymized:")
        for finding in checklist.findings:
            lines.extend(
                [
                    f"  - Field: {finding.field_name}",
                    f"    Reason: {finding.reason}",
                    f"    Action: {finding.suggested_action}",
                ]
            )
    return "\n".join(lines) + "\n"


def _render_delivery_status(
    status: LiveCommerceDeliveryStatus,
    report_path: Path | None,
    persisted: tuple[Path, ...],
) -> str:
    return "\n".join(
        [
            "# Delivery status",
            "",
            f"- Status: {status.value}",
            f"- Diagnosis draft: {'written' if report_path is not None else 'not written'}",
            f"- Raw sources retained: {'yes' if persisted else 'no'}",
            f"- Next action: {_next_action(status)}",
            "- Final delivery: requires merchant/finance/data-steward review",
            "",
        ]
    )


def _next_action(status: LiveCommerceDeliveryStatus) -> str:
    if status is LiveCommerceDeliveryStatus.BLOCKED_REDACTION:
        return (
            "remove or irreversibly anonymize flagged direct personal data, then create a new run"
        )
    if status in {
        LiveCommerceDeliveryStatus.BLOCKED_MISSING_FIELDS,
        LiveCommerceDeliveryStatus.BLOCKED_NO_ROWS,
    }:
        return "answer the missing-field questions and create a new run"
    return "review platform semantics, evidence, and draft conclusions before delivery"


def _evidence_item(
    evidence_id: str,
    source: Path,
    source_type: str,
    business_meaning: str,
    content: bytes,
    row_count: int,
    retained: bool,
    workspace_path: str | None,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        source_name=source.name,
        source_type=source_type,
        business_meaning=business_meaning,
        content_sha256=hashlib.sha256(content).hexdigest(),
        row_count=row_count,
        retained_in_workspace=retained,
        workspace_path=workspace_path,
    )


def _manifest_limitations(status: LiveCommerceDeliveryStatus) -> tuple[str, ...]:
    limitations = [
        "The authorization reference is operator-provided and must be verified by a human.",
        "Platform field meanings and financial semantics require merchant or data-steward review.",
        "SHA-256 proves input identity for this run; it does not prove source truthfulness.",
    ]
    if status is not LiveCommerceDeliveryStatus.READY_FOR_HUMAN_REVIEW:
        limitations.append(
            f"No diagnosis draft was produced because delivery status is {status.value}."
        )
    return tuple(limitations)


def _atomic_copy(source: Path, destination: Path) -> None:
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    try:
        shutil.copyfile(source, temporary)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
