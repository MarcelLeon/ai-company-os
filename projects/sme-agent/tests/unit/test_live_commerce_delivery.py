from __future__ import annotations

import json
from pathlib import Path

import pytest

from sme_agent.commercialization.live_commerce_delivery import (
    LiveCommerceDeliveryInput,
    LiveCommerceDeliveryRunner,
    LiveCommerceDeliveryStatus,
    preview_live_commerce_delivery,
)
from sme_agent.commercialization.live_commerce_delivery_cli import main
from sme_agent.commercialization.live_commerce_intake import LiveCommerceCsvIntakeService

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _sample_path(filename: str) -> Path:
    return PROJECT_ROOT / "sample_data" / "live_commerce_public_dogfood" / filename


def _delivery_input(
    tmp_path: Path,
    *,
    run_id: str = "run-001",
    persist_source_files: bool = False,
    live_sessions_csv: Path | None = None,
    orders_csv: Path | None = None,
) -> LiveCommerceDeliveryInput:
    return LiveCommerceDeliveryInput(
        output_dir=tmp_path / "customers",
        customer_id="seed-live-shop",
        display_name="种子直播店",
        run_id=run_id,
        primary_question="这场直播的成交效率和退款风险怎么样？",
        authorization_reference="wecom-consent-20260721-001",
        live_sessions_csv=live_sessions_csv or _sample_path("live_sessions.csv"),
        orders_csv=orders_csv or _sample_path("orders.csv"),
        persist_source_files=persist_source_files,
    )


def test_ready_delivery_writes_auditable_artifacts_without_raw_files_by_default(
    tmp_path: Path,
) -> None:
    result = LiveCommerceDeliveryRunner().run(_delivery_input(tmp_path))

    assert result.status is LiveCommerceDeliveryStatus.READY_FOR_HUMAN_REVIEW
    assert result.workspace.root == tmp_path / "customers/seed-live-shop/runs/run-001"
    assert result.report_path is not None
    assert "支付 GMV：2249" in result.report_path.read_text(encoding="utf-8")
    assert result.persisted_source_paths == ()
    assert not any(result.workspace.raw_dir.iterdir())

    for path in (
        result.mapping_report_path,
        result.missing_field_questions_path,
        result.redaction_checklist_path,
        result.evidence_manifest_path,
        result.delivery_status_path,
    ):
        assert path.exists()

    intake = result.workspace.intake_path.read_text(encoding="utf-8")
    assert "run-001" in intake
    assert "wecom-consent-20260721-001" in intake
    manifest = result.evidence_manifest_path.read_text(encoding="utf-8")
    assert "SHA-256" in manifest
    assert "Rows: 2" in manifest
    assert "Rows: 7" in manifest
    assert "Retained in workspace: no" in manifest


def test_delivery_preview_matches_ready_runner_artifact_contract() -> None:
    assessment = LiveCommerceCsvIntakeService().assess(
        primary_question="这场直播的成交效率和退款风险怎么样？",
        live_sessions_csv=_sample_path("live_sessions.csv").read_text(encoding="utf-8"),
        orders_csv=_sample_path("orders.csv").read_text(encoding="utf-8"),
    )

    preview = preview_live_commerce_delivery(assessment)

    assert preview.status is LiveCommerceDeliveryStatus.READY_FOR_HUMAN_REVIEW
    assert preview.creates_workspace is False
    assert preview.raw_retention_default is False
    assert preview.authorization_reference_required is True
    assert [artifact.path for artifact in preview.artifacts if artifact.included] == [
        "intake.md",
        "work/field-mapping.md",
        "work/missing-field-questions.md",
        "delivery/redaction-checklist.md",
        "delivery/evidence-manifest.md",
        "delivery/delivery-status.md",
        "work/diagnosis-draft.md",
    ]


def test_delivery_preview_blocks_direct_personal_data_and_omits_diagnosis() -> None:
    order_lines = _sample_path("orders.csv").read_text(encoding="utf-8").splitlines()
    orders_csv = "\n".join(
        [order_lines[0] + ",手机号", *[line + ",13800000000" for line in order_lines[1:]]]
    )
    assessment = LiveCommerceCsvIntakeService().assess(
        primary_question="这场直播表现如何？",
        live_sessions_csv=_sample_path("live_sessions.csv").read_text(encoding="utf-8"),
        orders_csv=orders_csv + "\n",
    )

    preview = preview_live_commerce_delivery(assessment)

    assert preview.status is LiveCommerceDeliveryStatus.BLOCKED_REDACTION
    assert "手机号" in preview.redaction_fields
    diagnosis = next(
        artifact for artifact in preview.artifacts if artifact.path == "work/diagnosis-draft.md"
    )
    assert diagnosis.included is False
    assert "删除" in preview.next_action


def test_delivery_refuses_to_overwrite_an_existing_run(tmp_path: Path) -> None:
    blank_authorization = _delivery_input(tmp_path, run_id="blank-auth").model_copy(
        update={"authorization_reference": "   "}
    )
    with pytest.raises(ValueError, match="must not be blank"):
        LiveCommerceDeliveryRunner().run(blank_authorization)
    assert not (tmp_path / "customers/seed-live-shop/runs/blank-auth").exists()

    delivery_input = _delivery_input(tmp_path)
    result = LiveCommerceDeliveryRunner().run(delivery_input)
    original = result.delivery_status_path.read_text(encoding="utf-8")

    with pytest.raises(FileExistsError, match="run already exists"):
        LiveCommerceDeliveryRunner().run(delivery_input)

    assert result.delivery_status_path.read_text(encoding="utf-8") == original


def test_missing_fields_write_questions_but_no_diagnosis_or_raw_copy(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    sessions = inputs / "live_sessions.csv"
    orders = inputs / "orders.csv"
    sessions.write_text("直播场次ID,观看人数\nLIVE-1,1000\n", encoding="utf-8")
    orders.write_text("直播场次ID,订单编号,支付状态\nLIVE-1,O-1,已支付\n", encoding="utf-8")

    result = LiveCommerceDeliveryRunner().run(
        _delivery_input(
            tmp_path,
            live_sessions_csv=sessions,
            orders_csv=orders,
            persist_source_files=True,
        )
    )

    assert result.status is LiveCommerceDeliveryStatus.BLOCKED_MISSING_FIELDS
    assert result.report_path is None
    assert result.persisted_source_paths == ()
    assert not any(result.workspace.raw_dir.iterdir())
    questions = result.missing_field_questions_path.read_text(encoding="utf-8")
    assert "支付金额" in questions
    assert "店铺 ID" in questions
    assert "blocked_missing_fields" in result.delivery_status_path.read_text(encoding="utf-8")


def test_header_only_sources_write_no_row_questions_without_a_report(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    sessions = inputs / "live_sessions.csv"
    orders = inputs / "orders.csv"
    sessions.write_text(
        _sample_path("live_sessions.csv").read_text(encoding="utf-8").splitlines()[0] + "\n",
        encoding="utf-8",
    )
    orders.write_text(
        _sample_path("orders.csv").read_text(encoding="utf-8").splitlines()[0] + "\n",
        encoding="utf-8",
    )

    result = LiveCommerceDeliveryRunner().run(
        _delivery_input(tmp_path, live_sessions_csv=sessions, orders_csv=orders)
    )

    assert result.status is LiveCommerceDeliveryStatus.BLOCKED_NO_ROWS
    assert result.report_path is None
    questions = result.missing_field_questions_path.read_text(encoding="utf-8")
    assert "只有表头" in questions
    assert "blocked_no_rows" in result.delivery_status_path.read_text(encoding="utf-8")


def test_direct_personal_data_blocks_report_and_raw_retention(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    sessions = inputs / "live_sessions.csv"
    orders = inputs / "orders.csv"
    sessions.write_text(_sample_path("live_sessions.csv").read_text(encoding="utf-8"))
    order_lines = _sample_path("orders.csv").read_text(encoding="utf-8").splitlines()
    orders.write_text(
        "\n".join(
            [order_lines[0] + ",手机号", *[line + ",13800000000" for line in order_lines[1:]]]
        )
        + "\n",
        encoding="utf-8",
    )

    result = LiveCommerceDeliveryRunner().run(
        _delivery_input(
            tmp_path,
            live_sessions_csv=sessions,
            orders_csv=orders,
            persist_source_files=True,
        )
    )

    assert result.status is LiveCommerceDeliveryStatus.BLOCKED_REDACTION
    assert result.report_path is None
    assert result.persisted_source_paths == ()
    assert not any(result.workspace.raw_dir.iterdir())
    checklist = result.redaction_checklist_path.read_text(encoding="utf-8")
    assert "手机号" in checklist
    assert "删除、打码或替换" in checklist


def test_explicit_retention_and_cli_create_a_run_scoped_workspace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "--output-dir",
            str(tmp_path / "customers"),
            "--customer-id",
            "cli-shop",
            "--display-name",
            "CLI 直播店",
            "--run-id",
            "cli-run-001",
            "--question",
            "这场直播表现如何？",
            "--authorization-reference",
            "ticket-001",
            "--live-sessions-csv",
            str(_sample_path("live_sessions.csv")),
            "--orders-csv",
            str(_sample_path("orders.csv")),
            "--persist-source-files",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ready_for_human_review"
    workspace = Path(output["workspace"])
    assert workspace == tmp_path / "customers/cli-shop/runs/cli-run-001"
    assert (workspace / "raw/live_sessions.csv").read_bytes() == _sample_path(
        "live_sessions.csv"
    ).read_bytes()
    assert (workspace / "raw/orders.csv").read_bytes() == _sample_path("orders.csv").read_bytes()

    second_exit_code = main(
        [
            "--output-dir",
            str(tmp_path / "customers"),
            "--customer-id",
            "cli-shop",
            "--display-name",
            "CLI 直播店",
            "--run-id",
            "cli-run-001",
            "--question",
            "这场直播表现如何？",
            "--authorization-reference",
            "ticket-001",
            "--live-sessions-csv",
            str(_sample_path("live_sessions.csv")),
            "--orders-csv",
            str(_sample_path("orders.csv")),
        ]
    )
    assert second_exit_code == 2
    error = json.loads(capsys.readouterr().err)
    assert error["status"] == "error"
    assert "run already exists" in error["message"]
