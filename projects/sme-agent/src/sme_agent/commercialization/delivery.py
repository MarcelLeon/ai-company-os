"""Delivery workspace, evidence, and redaction helpers for paid reports."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import Field

from sme_agent.metadata.models import FrozenModel


class CustomerProjectSpec(FrozenModel):
    customer_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    display_name: str = Field(min_length=1)
    primary_question: str = Field(min_length=1)
    service_tier: str = Field(min_length=1)
    run_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]+$")
    authorization_reference: str | None = Field(default=None, min_length=1)


class ProjectWorkspace(FrozenModel):
    root: Path
    intake_path: Path
    raw_dir: Path
    work_dir: Path
    delivery_dir: Path
    evidence_manifest_path: Path
    mapping_report_path: Path
    missing_field_questions_path: Path
    redaction_checklist_path: Path
    delivery_status_path: Path
    diagnosis_draft_path: Path


class EvidenceItem(FrozenModel):
    evidence_id: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    business_meaning: str = Field(min_length=1)
    human_check_required: bool = True
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    row_count: int | None = Field(default=None, ge=0)
    retained_in_workspace: bool | None = None
    workspace_path: str | None = Field(default=None, min_length=1)


class EvidenceManifest(FrozenModel):
    customer_id: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    primary_question: str = Field(min_length=1)
    evidence: tuple[EvidenceItem, ...]
    limitations: tuple[str, ...]


class RedactionFinding(FrozenModel):
    field_name: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    suggested_action: str = Field(min_length=1)


class RedactionChecklist(FrozenModel):
    findings: tuple[RedactionFinding, ...]

    @property
    def has_risk(self) -> bool:
        return bool(self.findings)


class ProjectWorkspaceService:
    """Create the repeatable folder structure for a service-backed diagnosis."""

    def create(self, base_dir: Path, spec: CustomerProjectSpec) -> ProjectWorkspace:
        customer_root = base_dir / spec.customer_id
        root = customer_root if spec.run_id is None else customer_root / "runs" / spec.run_id
        if spec.run_id is not None and root.exists():
            raise FileExistsError(f"run already exists: {spec.customer_id}/{spec.run_id}")
        raw_dir = root / "raw"
        work_dir = root / "work"
        delivery_dir = root / "delivery"
        for directory in (raw_dir, work_dir, delivery_dir):
            directory.mkdir(parents=True, exist_ok=True)
        intake_path = root / "intake.md"
        if not intake_path.exists():
            intake_path.write_text(self._intake_text(spec), encoding="utf-8")
        return ProjectWorkspace(
            root=root,
            intake_path=intake_path,
            raw_dir=raw_dir,
            work_dir=work_dir,
            delivery_dir=delivery_dir,
            evidence_manifest_path=delivery_dir / "evidence-manifest.md",
            mapping_report_path=work_dir / "field-mapping.md",
            missing_field_questions_path=work_dir / "missing-field-questions.md",
            redaction_checklist_path=delivery_dir / "redaction-checklist.md",
            delivery_status_path=delivery_dir / "delivery-status.md",
            diagnosis_draft_path=work_dir / "diagnosis-draft.md",
        )

    def _intake_text(self, spec: CustomerProjectSpec) -> str:
        run_id = spec.run_id or "legacy-unversioned"
        authorization = spec.authorization_reference or "pending"
        return "\n".join(
            [
                f"# {spec.display_name} intake",
                "",
                f"- Customer ID: {spec.customer_id}",
                f"- Run ID: {run_id}",
                f"- Service tier: {spec.service_tier}",
                f"- Primary question: {spec.primary_question}",
                f"- Analysis authorization: {authorization}",
                "- Personal data redaction: pending",
                "",
            ]
        )


class EvidenceManifestRenderer:
    """Render evidence so the buyer can see what each conclusion relies on."""

    def render(self, manifest: EvidenceManifest) -> str:
        lines = [
            "# Evidence manifest",
            "",
            f"- Customer ID: {manifest.customer_id}",
            f"- Generated at: {manifest.generated_at}",
            f"- Primary question: {manifest.primary_question}",
            "",
            "## Evidence items",
        ]
        for item in manifest.evidence:
            lines.extend(self._item_lines(item))
        lines.extend(["", "## Known limitations"])
        lines.extend(f"- {limitation}" for limitation in manifest.limitations)
        return "\n".join(lines) + "\n"

    def _item_lines(self, item: EvidenceItem) -> list[str]:
        check_text = "yes" if item.human_check_required else "no"
        lines = [
            f"### {item.evidence_id}",
            "",
            f"- Source: {item.source_name}",
            f"- Type: {item.source_type}",
            f"- Meaning: {item.business_meaning}",
            f"- Human check required: {check_text}",
        ]
        if item.content_sha256 is not None:
            lines.append(f"- SHA-256: {item.content_sha256}")
        if item.row_count is not None:
            lines.append(f"- Rows: {item.row_count}")
        if item.retained_in_workspace is not None:
            retained = "yes" if item.retained_in_workspace else "no"
            lines.append(f"- Retained in workspace: {retained}")
        if item.workspace_path is not None:
            lines.append(f"- Workspace path: {item.workspace_path}")
        return [*lines, ""]


class EvidenceManifestService:
    """Build and write evidence manifests for customer reports."""

    def build(
        self,
        *,
        customer_id: str,
        primary_question: str,
        evidence: tuple[EvidenceItem, ...],
        limitations: tuple[str, ...],
    ) -> EvidenceManifest:
        return EvidenceManifest(
            customer_id=customer_id,
            generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            primary_question=primary_question,
            evidence=evidence,
            limitations=limitations,
        )

    def write(self, workspace: ProjectWorkspace, manifest: EvidenceManifest) -> Path:
        rendered = EvidenceManifestRenderer().render(manifest)
        workspace.evidence_manifest_path.write_text(rendered, encoding="utf-8")
        return workspace.evidence_manifest_path


class RedactionScanner:
    """Detect obvious personal-data columns before the human reviews files."""

    _SENSITIVE_KEYWORDS = {
        "phone": "手机号或电话字段",
        "mobile": "手机号字段",
        "tel": "电话字段",
        "name": "姓名字段",
        "address": "地址字段",
        "id_card": "身份证字段",
        "身份证": "身份证字段",
        "手机号": "手机号字段",
        "电话": "电话字段",
        "姓名": "姓名字段",
        "地址": "地址字段",
        "微信": "微信号字段",
    }

    def scan_headers(self, headers: tuple[str, ...]) -> RedactionChecklist:
        findings: list[RedactionFinding] = []
        for header in headers:
            reason = self._reason(header)
            if reason is not None:
                findings.append(
                    RedactionFinding(
                        field_name=header,
                        reason=reason,
                        suggested_action="删除、打码或替换为不可逆匿名 ID 后再分析。",
                    )
                )
        return RedactionChecklist(findings=tuple(findings))

    def _reason(self, header: str) -> str | None:
        normalized = header.lower()
        for keyword, reason in self._SENSITIVE_KEYWORDS.items():
            if keyword in normalized or keyword in header:
                return reason
        return None
