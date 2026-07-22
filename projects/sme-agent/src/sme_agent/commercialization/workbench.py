"""Local browser workbench for dogfooding SME Agent diagnosis flows."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, TypeAlias
from urllib.parse import urlparse

from sme_agent.commercialization.live_commerce_comparison import (
    LiveCommerceComparisonRunner,
    comparison_to_payload,
)
from sme_agent.commercialization.live_commerce_delivery import (
    LiveCommerceDeliveryPreview,
    LiveCommerceDeliveryStatus,
    preview_live_commerce_delivery,
)
from sme_agent.commercialization.live_commerce_diagnosis import (
    LiveCommerceDiagnosisReport,
    LiveCommerceReportMarkdownRenderer,
)
from sme_agent.commercialization.live_commerce_intake import (
    LiveCommerceCsvIntakeService,
    LiveCommerceIntakeAssessment,
)
from sme_agent.domains import FieldMappingReport

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SampleConfig: TypeAlias = dict[str, str | Path]

SAMPLES: dict[str, SampleConfig] = {
    "public-dogfood": {
        "name": "公开来源直播电商样例",
        "question": "公开来源缩放样例里，直播间成交效率和退款风险是否值得继续追问？",
        "directory": PROJECT_ROOT / "sample_data" / "live_commerce_public_dogfood",
        "source_note": "来源形态参考公开数据集和论文聚合信息，已缩放；不能冒充真实商家后台。",
    },
    "week-one": {
        "name": "直播电商拟真样例",
        "question": "昨晚直播间 GMV 为什么看着不差，但老板感觉利润和成交效率都不稳？",
        "directory": PROJECT_ROOT / "sample_data" / "live_commerce_week_one",
        "source_note": "本地拟真样例，用于验证字段映射、指标计算和报告结构。",
    },
}
MAX_INTAKE_REQUEST_BYTES = 4_100_000


def build_live_commerce_payload(sample_id: str) -> dict[str, Any]:
    """Build the JSON payload used by the local workbench UI."""
    sample = _sample(sample_id)
    sample_dir = _sample_directory(sample)
    assessment = LiveCommerceCsvIntakeService().assess(
        primary_question=str(sample["question"]),
        live_sessions_csv=(sample_dir / "live_sessions.csv").read_text(encoding="utf-8"),
        orders_csv=(sample_dir / "orders.csv").read_text(encoding="utf-8"),
    )
    report = _required_report(assessment)
    preview = preview_live_commerce_delivery(assessment)
    return {
        "sample_id": sample_id,
        "sample_name": sample["name"],
        "source_note": sample["source_note"],
        "question": sample["question"],
        "business_context": _business_context_payload(),
        "mapping": _mapping_payload(report),
        "metrics": _metrics_payload(report),
        "findings": _findings_payload(report),
        "human_checks": list(report.required_human_checks),
        "disclaimers": list(report.disclaimers),
        "decision": _delivery_decision_payload(preview.status),
        "delivery_preview": _delivery_preview_payload(preview),
        "report_markdown": LiveCommerceReportMarkdownRenderer().render(report),
    }


def build_live_commerce_comparison_payload(sample_id: str) -> dict[str, Any]:
    """Build the two-session comparison payload used by the local workbench."""
    sample = _sample(sample_id)
    sample_dir = _sample_directory(sample)
    report = LiveCommerceComparisonRunner().run(
        question="为什么这场直播比上一场差？",
        live_sessions_csv=sample_dir / "live_sessions.csv",
        orders_csv=sample_dir / "orders.csv",
    )
    payload = comparison_to_payload(report)
    payload["sample_id"] = sample_id
    payload["sample_name"] = sample["name"]
    return payload


def build_live_commerce_intake_payload(
    *,
    primary_question: str,
    live_sessions_csv: str,
    orders_csv: str,
) -> dict[str, Any]:
    """Build a boss-readable payload from non-persistent merchant CSV text."""
    assessment = LiveCommerceCsvIntakeService().assess(
        primary_question=primary_question,
        live_sessions_csv=live_sessions_csv,
        orders_csv=orders_csv,
    )
    preview = preview_live_commerce_delivery(assessment)
    report = (
        assessment.report
        if preview.status is LiveCommerceDeliveryStatus.READY_FOR_HUMAN_REVIEW
        else None
    )
    return {
        "sample_id": "self-serve",
        "sample_name": "你的本地 CSV",
        "source_note": "文件仅在本机进程内分析，SME Agent 不会持久化本次 intake。",
        "question": primary_question.strip(),
        "business_context": _business_context_payload(),
        "mapping": _field_mapping_payload(assessment.mapping_report),
        "table_profiles": _table_profiles_payload(assessment),
        "follow_up_questions": list(assessment.follow_up_questions),
        "metrics": _metrics_payload(report) if report is not None else None,
        "findings": _findings_payload(report) if report is not None else [],
        "human_checks": list(report.required_human_checks) if report is not None else [],
        "disclaimers": list(report.disclaimers) if report is not None else [],
        "decision": _delivery_decision_payload(preview.status),
        "delivery_preview": _delivery_preview_payload(preview),
        "report_markdown": (
            LiveCommerceReportMarkdownRenderer().render(report) if report is not None else ""
        ),
    }


def render_workbench_html() -> str:
    """Render a self-contained local workbench page."""
    return _WORKBENCH_HTML


def serve_workbench(host: str = "127.0.0.1", port: int = 8767) -> None:
    """Start the local workbench HTTP server."""
    server = ThreadingHTTPServer((host, port), WorkbenchRequestHandler)
    print(f"SME Agent workbench: http://{host}:{server.server_port}")
    server.serve_forever()


class WorkbenchRequestHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for the local diagnosis workbench."""

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._send_text(render_workbench_html(), "text/html; charset=utf-8")
            return
        if path.startswith("/api/live-commerce/sample/"):
            self._send_sample(path.rsplit("/", 1)[-1])
            return
        if path.startswith("/api/live-commerce/comparison/"):
            self._send_comparison(path.rsplit("/", 1)[-1])
            return
        self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/live-commerce/intake":
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json_body()
            self._send_json(
                build_live_commerce_intake_payload(
                    primary_question=_required_text(payload, "primary_question"),
                    live_sessions_csv=_required_text(payload, "live_sessions_csv"),
                    orders_csv=_required_text(payload, "orders_csv"),
                )
            )
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_sample(self, sample_id: str) -> None:
        try:
            self._send_json(build_live_commerce_payload(sample_id))
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _send_comparison(self, sample_id: str) -> None:
        try:
            self._send_json(build_live_commerce_comparison_payload(sample_id))
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _read_json_body(self) -> dict[str, Any]:
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            raise ValueError("缺少 Content-Length")
        try:
            body_length = int(content_length)
        except ValueError as exc:
            raise ValueError("Content-Length 无效") from exc
        if body_length <= 0:
            raise ValueError("intake 请求不能为空")
        if body_length > MAX_INTAKE_REQUEST_BYTES:
            raise ValueError("intake 请求过大；请缩小 CSV 时间范围")
        try:
            payload = json.loads(self.rfile.read(body_length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("intake 请求必须是 UTF-8 JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("intake JSON 必须是对象")
        return payload

    def _send_text(
        self,
        body: str,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(
        self,
        body: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        encoded = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _sample(sample_id: str) -> SampleConfig:
    if sample_id not in SAMPLES:
        raise ValueError(f"unknown sample: {sample_id}")
    return SAMPLES[sample_id]


def _sample_directory(sample: SampleConfig) -> Path:
    directory = sample["directory"]
    if not isinstance(directory, Path):
        raise ValueError("sample directory must be a path")
    return directory


def _mapping_payload(report: LiveCommerceDiagnosisReport) -> dict[str, object]:
    return _field_mapping_payload(report.mapping_report)


def _field_mapping_payload(mapping_report: FieldMappingReport) -> dict[str, object]:
    ratio = mapping_report.required_coverage_ratio
    return {
        "coverage_decimal": ratio,
        "coverage_ratio": str(ratio),
        "coverage_percent": int(ratio * Decimal("100")),
        "mapped_fields": [
            {
                "field_id": mapping.field_id,
                "source_column": mapping.source_column,
                "required": mapping.required,
                "sensitive": mapping.sensitive,
            }
            for mapping in mapping_report.mappings
        ],
        "missing_required_fields": list(mapping_report.missing_required_fields),
        "computable_metric_ids": list(mapping_report.computable_metric_ids),
        "sensitive_source_columns": list(mapping_report.sensitive_source_columns),
    }


def _table_profiles_payload(assessment: LiveCommerceIntakeAssessment) -> dict[str, object]:
    return {
        "live_sessions": assessment.live_sessions_profile.model_dump(),
        "orders": assessment.orders_profile.model_dump(),
    }


def _metrics_payload(report: LiveCommerceDiagnosisReport) -> dict[str, str]:
    metrics = report.metrics
    return {
        "gmv": str(metrics.gmv),
        "paid_gmv": str(metrics.paid_gmv),
        "pay_order_count": str(metrics.pay_order_count),
        "pay_buyer_count": str(metrics.pay_buyer_count),
        "average_order_value": str(metrics.average_order_value),
        "refund_rate": str(metrics.refund_rate),
        "gpm": str(metrics.gpm),
        "payment_conversion_rate": str(metrics.payment_conversion_rate),
        "live_room_view_count": str(metrics.live_room_view_count),
    }


def _business_context_payload() -> dict[str, object]:
    return {
        "pain_points": [
            "直播间 GMV 看起来不差，但老板不知道是不是靠低效流量、退款或补贴堆出来。",
            "平台后台指标分散，运营、主播、商品和订单口径对不上，复盘只能靠感觉。",
            "中小商家没有专职数据团队，需要先知道数据够不够诊断，再拿到可执行结论。",
        ],
        "data_tables": [
            {
                "name": "live_sessions.csv",
                "meaning": "直播场次表，描述平台、店铺、主播、直播场次和观看人数。",
            },
            {
                "name": "orders.csv",
                "meaning": "订单支付表，描述订单、商品、支付状态、支付金额、退款金额和匿名买家。",
            },
        ],
        "entities": [
            "行业类目",
            "店铺",
            "平台",
            "直播场次",
            "主播",
            "商品",
            "订单",
            "支付",
            "匿名买家",
        ],
        "relationships": [
            "一个店铺在一个平台上开多场直播。",
            "一场直播由一个主播承接，并带来观看人数。",
            "一场直播关联多个订单，订单关联商品、支付和退款。",
            "匿名买家用于去重计算支付买家数，不用于识别个人。",
        ],
        "business_process": [
            "开播获得流量：用观看人数表示直播间入口规模。",
            "商品讲解产生下单：订单金额形成 GMV，但不代表真实收款。",
            "支付完成才形成支付 GMV：支付订单数、支付买家数和客单价来自支付口径。",
            "售后退款侵蚀成交质量：退款金额除以支付 GMV 得到退款率。",
            "成交效率用 GPM 和支付转化判断：看每千次观看带来多少支付 GMV。",
        ],
        "output_logic": [
            "先看字段映射覆盖率，覆盖率不足就不输出付费结论。",
            "再计算支付 GMV、退款率、GPM、支付转化等老板可理解指标。",
            "最后把异常指标翻译成诊断发现、证据、建议动作和人工确认项。",
        ],
        "next_after_validation": [
            "如果样例诊断看得懂，下一步接入真实 CSV 上传或粘贴。",
            "真实数据覆盖率不足时，系统应先追问缺字段，而不是猜结论。",
            "确认有付费价值后，再做客户 workspace、两期对比和淘宝/千牛首发流程。",
        ],
    }


def _findings_payload(report: LiveCommerceDiagnosisReport) -> list[dict[str, object]]:
    return [
        {
            "title": finding.title,
            "evidence": list(finding.evidence),
            "recommended_action": finding.recommended_action,
            "human_check": finding.human_check,
        }
        for finding in report.findings
    ]


def _delivery_decision_payload(status: LiveCommerceDeliveryStatus) -> dict[str, str]:
    if status is LiveCommerceDeliveryStatus.BLOCKED_REDACTION:
        return {
            "commercial_readiness": status.value,
            "next_action": "检测到直接个人信息字段；先删除、打码或不可逆匿名化，再重新检查。",
        }
    if status is LiveCommerceDeliveryStatus.BLOCKED_MISSING_FIELDS:
        return {
            "commercial_readiness": status.value,
            "next_action": "字段不足，先按问题补齐脱敏导出；当前不会生成付费结论。",
        }
    if status is LiveCommerceDeliveryStatus.BLOCKED_NO_ROWS:
        return {
            "commercial_readiness": status.value,
            "next_action": "字段可识别，但还需要至少一行脱敏数据才能计算指标。",
        }
    return {
        "commercial_readiness": "needs_human_review",
        "next_action": "已完成本地诊断草稿；交付前请确认平台口径和敏感字段处理。",
    }


def _delivery_preview_payload(preview: LiveCommerceDeliveryPreview) -> dict[str, object]:
    return preview.model_dump(mode="json")


def _required_report(assessment: LiveCommerceIntakeAssessment) -> LiveCommerceDiagnosisReport:
    if assessment.report is None:
        raise RuntimeError("bundled sample did not produce a diagnosis report")
    return assessment.report


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} 不能为空")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SME Agent local workbench.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8767, type=int)
    args = parser.parse_args()
    serve_workbench(host=args.host, port=args.port)


_WORKBENCH_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SME Agent 直播诊断工作台</title>
  <style>
    :root {
      --bg: #f7f8f5;
      --ink: #1f2a24;
      --muted: #657069;
      --line: #dbe1da;
      --panel: #ffffff;
      --green: #176b4d;
      --green-2: #e3f2ea;
      --amber: #9a6514;
      --red: #a33a32;
      --shadow: 0 18px 50px rgba(31, 42, 36, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }
    header {
      padding: 24px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--line);
      background: rgba(247, 248, 245, 0.92);
      position: sticky;
      top: 0;
      z-index: 2;
      backdrop-filter: blur(12px);
    }
    .brand { font-weight: 800; letter-spacing: 0.01em; }
    .status { color: var(--muted); font-size: 14px; }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 36px 24px 56px;
    }
    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
      gap: 28px;
      align-items: stretch;
      margin-bottom: 28px;
    }
    h1 {
      font-size: clamp(34px, 5vw, 62px);
      line-height: 1.02;
      margin: 0 0 18px;
      max-width: 760px;
    }
    h2 { margin: 0 0 16px; font-size: 22px; }
    h3 { margin: 0 0 10px; font-size: 17px; }
    p { color: var(--muted); margin: 0 0 18px; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 22px;
    }
    .actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 24px; }
    button {
      border: 1px solid var(--green);
      background: var(--green);
      color: #fff;
      border-radius: 6px;
      padding: 11px 15px;
      font-weight: 700;
      font-size: 14px;
      cursor: pointer;
    }
    button.secondary { background: #fff; color: var(--green); }
    button:disabled { cursor: progress; opacity: 0.62; }
    .grid {
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 18px;
      align-items: start;
    }
    .steps { display: grid; gap: 12px; }
    .step {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .step strong { display: block; margin-bottom: 4px; }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #fbfcfa;
    }
    .metric label {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 8px;
    }
    .metric strong { font-size: 24px; }
    .metric.warning strong { color: var(--amber); }
    .metric.risk strong { color: var(--red); }
    .finding {
      border-left: 4px solid var(--green);
      padding: 14px 16px;
      background: #fbfcfa;
      margin-bottom: 12px;
      border-radius: 0 8px 8px 0;
    }
    .finding p { margin: 6px 0; }
    .explain-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }
    .explain-card {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    .explain-card ul,
    .flow-card ol {
      margin: 0;
      padding-left: 20px;
      color: var(--muted);
    }
    .explain-card li,
    .flow-card li { margin: 7px 0; }
    .flow-card {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 18px;
    }
    .intake-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    .intake-field { display: grid; gap: 7px; }
    .intake-field.full { grid-column: 1 / -1; }
    .intake-field label { font-weight: 700; }
    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 11px 12px;
      background: #fbfcfa;
      color: var(--ink);
      font: inherit;
    }
    textarea { min-height: 118px; resize: vertical; font-family: ui-monospace, monospace; }
    .privacy-note { color: var(--green); font-weight: 700; }
    .questions {
      margin-top: 14px;
      border-left: 4px solid var(--amber);
      padding: 12px 14px;
      background: #fff8e9;
    }
    .artifact-list { display: grid; gap: 9px; margin: 14px 0; }
    .artifact {
      display: grid;
      grid-template-columns: minmax(180px, 0.55fr) minmax(0, 1fr) auto;
      gap: 12px;
      align-items: center;
      border-top: 1px solid var(--line);
      padding-top: 9px;
    }
    .artifact:first-child { border-top: 0; padding-top: 0; }
    .artifact code { overflow-wrap: anywhere; }
    .artifact span { color: var(--muted); }
    .artifact-state { font-weight: 700; color: var(--green); }
    .artifact-state.omitted { color: var(--amber); }
    .safety-strip {
      border-radius: 8px;
      padding: 12px 14px;
      background: var(--green-2);
      color: var(--green);
      font-weight: 700;
    }
    .acceptance-list { display: grid; gap: 10px; margin: 14px 0; }
    .acceptance-item {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 10px;
      align-items: start;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      cursor: pointer;
    }
    .acceptance-item input { width: auto; margin-top: 4px; }
    .acceptance-progress { color: var(--green); font-weight: 800; }
    .relation {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }
    .relation span {
      background: var(--green-2);
      color: var(--green);
      border-radius: 8px;
      padding: 10px;
      font-size: 13px;
      font-weight: 700;
      text-align: center;
    }
    .tag {
      display: inline-flex;
      background: var(--green-2);
      color: var(--green);
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 12px;
      font-weight: 700;
      margin-right: 6px;
      margin-bottom: 6px;
    }
    pre {
      white-space: pre-wrap;
      background: #17211c;
      color: #edf7f0;
      padding: 18px;
      border-radius: 8px;
      overflow: auto;
      min-height: 360px;
      font-size: 13px;
    }
    .section { margin-top: 18px; }
    .empty {
      min-height: 240px;
      display: grid;
      place-items: center;
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 8px;
      background: #fff;
      text-align: center;
      padding: 22px;
    }
    @media (max-width: 860px) {
      header { padding: 18px; align-items: flex-start; gap: 8px; flex-direction: column; }
      main { padding: 24px 16px 40px; }
      .hero, .grid { grid-template-columns: 1fr; }
      .explain-grid { grid-template-columns: 1fr; }
      .intake-grid { grid-template-columns: 1fr; }
      .intake-field.full { grid-column: auto; }
      .relation { grid-template-columns: 1fr 1fr; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .artifact { grid-template-columns: 1fr; gap: 4px; }
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">SME Agent</div>
    <div class="status" id="status">本地诊断工作台 · 数据不离开本机进程 · 人工复核后交付</div>
  </header>

  <main>
    <section class="hero">
      <div>
        <h1>直播间经营诊断，不再只看 GMV。</h1>
        <p>
          给中小商家老板、直播达人和运营负责人看的本地诊断台。先检查字段是否足够，
          再计算支付 GMV、退款率、GPM 和支付转化，最后生成可人工复核的交付报告。
        </p>
        <div class="actions">
          <button id="publicSample">使用公开 dogfood 样例</button>
          <button class="secondary" id="weekSample">使用拟真直播样例</button>
          <button class="secondary" id="weekCompare">回答：为什么这场比上一场差？</button>
          <button class="secondary" id="copyReport" disabled>复制交付报告</button>
        </div>
      </div>
      <div class="panel">
        <h2>验收重点</h2>
        <p>这不是营销页。你应该能亲手点出一份报告，并判断它是否有商业可信度。</p>
        <span class="tag">字段映射</span>
        <span class="tag">确定性指标</span>
        <span class="tag">证据链</span>
        <span class="tag">人工确认项</span>
      </div>
    </section>

    <section class="section">
      <div class="explain-grid">
        <div class="explain-card">
          <h2>解决什么痛点</h2>
          <ul>
            <li>GMV 好看，但不知道真实成交质量。</li>
            <li>运营、主播、商品、订单指标分散，复盘靠感觉。</li>
            <li>中小商家没有数据团队，需要先判断数据够不够诊断。</li>
          </ul>
        </div>
        <div class="explain-card">
          <h2>样例数据怎么建模</h2>
          <ul>
            <li><strong>live_sessions.csv</strong>：直播场次、主播、观看人数。</li>
            <li><strong>orders.csv</strong>：订单、商品、支付、退款、匿名买家。</li>
            <li>两张表通过 <strong>直播场次ID</strong> 连接。</li>
          </ul>
        </div>
        <div class="explain-card">
          <h2>输出结论怎么看</h2>
          <ul>
            <li>字段覆盖率决定能不能下结论。</li>
            <li>指标先算支付 GMV、退款率、GPM 和支付转化。</li>
            <li>发现必须带证据、建议动作和人工确认项。</li>
          </ul>
        </div>
      </div>

      <div class="flow-card">
        <h2>实体关系和直播业务过程</h2>
        <div class="relation">
          <span>店铺 / 平台</span>
          <span>直播场次 / 主播</span>
          <span>商品 / 订单</span>
          <span>支付 / 退款 / 买家</span>
        </div>
        <ol>
          <li>店铺在平台上开播，直播场次记录主播和观看人数。</li>
          <li>直播间讲解商品并产生订单，订单金额形成 GMV。</li>
          <li>订单支付后才形成支付 GMV，同时产生支付订单数、买家数和客单价。</li>
          <li>退款会侵蚀成交质量，退款金额除以支付 GMV 得到退款率。</li>
          <li>GPM 和支付转化用来判断流量是否真的带来成交效率。</li>
        </ol>
      </div>

      <div class="flow-card">
        <h2>你验收没问题后怎么继续</h2>
        <ol>
          <li>先用两个内置样例确认页面、指标和报告是否能让商家老板看懂。</li>
          <li>选择或粘贴自己的脱敏 CSV；覆盖率不足时先回答缺字段问题。</li>
          <li>用两期直播对比回答“为什么这场比上场差”。</li>
          <li>最后接客户 workspace、证据 manifest、脱敏检查和淘宝/千牛首发流程。</li>
        </ol>
      </div>

      <div class="flow-card" id="selfServeIntake">
        <h2>选择你自己的 CSV</h2>
        <p>
          可以选择本机文件，也可以展开“粘贴 CSV 文本”。浏览器仅发送到当前本地工作台进程；
          服务端只在内存中分析，不写入客户 workspace 或日志。
        </p>
        <p class="privacy-note">提交前请先脱敏 buyer_id 等个人信息字段。</p>
        <div class="intake-grid">
          <div class="intake-field full">
            <label for="intakeQuestion">你想回答的经营问题</label>
            <input id="intakeQuestion" value="这场直播的成交效率和退款风险怎么样？">
          </div>
          <div class="intake-field">
            <label for="sessionsFile">live_sessions.csv</label>
            <input id="sessionsFile" type="file" accept=".csv,text/csv">
          </div>
          <div class="intake-field">
            <label for="ordersFile">orders.csv</label>
            <input id="ordersFile" type="file" accept=".csv,text/csv">
          </div>
          <details class="intake-field">
            <summary>粘贴 CSV 文本：直播场次表</summary>
            <textarea id="sessionsPaste" placeholder="直播场次ID,主播ID,观看人数,..."></textarea>
          </details>
          <details class="intake-field">
            <summary>粘贴 CSV 文本：订单表</summary>
            <textarea
              id="ordersPaste"
              placeholder="订单编号,商品ID,支付状态,支付金额,..."
            ></textarea>
          </details>
        </div>
        <div class="actions">
          <button id="runIntake">检查字段并生成本地诊断</button>
        </div>
        <div id="intakeQuestions" class="questions" hidden></div>
      </div>
    </section>

    <section class="grid">
      <aside class="steps">
        <div class="step">
          <strong>1. 选择样例</strong>
          <span>公开来源缩放样例或本地拟真样例。</span>
        </div>
        <div class="step">
          <strong>2. 检查映射</strong>
          <span>覆盖率不到 100% 就不能卖结论。</span>
        </div>
        <div class="step">
          <strong>3. 复核报告</strong>
          <span>确认平台口径、敏感字段和建议证据。</span>
        </div>
      </aside>

      <div>
        <div id="empty" class="empty">
          请选择内置样例，或在上方选择自己的脱敏 CSV。数据仅进入当前本机工作台进程。
        </div>
        <div id="result" hidden>
          <div class="panel">
            <h2 id="sampleName"></h2>
            <p id="sourceNote"></p>
            <div class="metrics" id="metrics"></div>
          </div>
          <div class="panel section">
            <h2>字段映射</h2>
            <p id="mappingSummary"></p>
            <div id="mappingTags"></div>
          </div>
          <div class="panel section">
            <h2>初步发现</h2>
            <div id="findings"></div>
          </div>
          <div class="panel section">
            <h2>复制给客户前必须确认</h2>
            <div id="checks"></div>
          </div>
          <div class="section">
            <pre id="report"></pre>
          </div>
        </div>
        <div id="comparison" hidden>
          <div class="panel">
            <h2>两场直播对比结论</h2>
            <p id="comparisonQuestion"></p>
            <div class="metrics" id="comparisonMetrics"></div>
          </div>
          <div class="panel section">
            <h2>为什么变差</h2>
            <div id="comparisonFindings"></div>
          </div>
          <div class="panel section">
            <h2>SKU 拖累拆解</h2>
            <div id="skuDeltas"></div>
          </div>
          <div class="panel section">
            <h2>当前不能归因的因素</h2>
            <div id="comparisonLimits"></div>
          </div>
        </div>
        <div class="panel section" id="deliveryPreviewPanel" hidden>
          <h2>不可变交付包预览</h2>
          <p id="deliveryPreviewStatus"></p>
          <div id="deliveryArtifacts" class="artifact-list"></div>
          <div id="redactionWarning" class="questions" hidden></div>
          <p class="safety-strip">
            预览不会创建客户 workspace、不会保留 raw CSV，也不会生成授权记录。
          </p>
        </div>
        <div class="panel section" id="ownerAcceptance" hidden>
          <h2>199 元入口验收</h2>
          <p>
            这些选择只存在当前页面，不发送、不落盘，也不代表法律或平台口径批准。
            “是否值得 199 元”只能由你本人勾选。
          </p>
          <div class="acceptance-list">
            <label class="acceptance-item">
              <input class="acceptance-check" type="checkbox">
              <span>我能在 3 分钟内看懂核心指标、发现和下一步。</span>
            </label>
            <label class="acceptance-item">
              <input class="acceptance-check" type="checkbox">
              <span>每条结论都能回到字段、指标或 evidence manifest。</span>
            </label>
            <label class="acceptance-item">
              <input class="acceptance-check" type="checkbox">
              <span>缺字段或个人信息风险会阻止付费结论，而不是靠免责声明放行。</span>
            </label>
            <label class="acceptance-item">
              <input class="acceptance-check" type="checkbox">
              <span>建议动作对商家老板或运营来说足够具体。</span>
            </label>
            <label class="acceptance-item">
              <input class="acceptance-check" type="checkbox">
              <span>如果这是我的店，我愿意为这份字段体检 / 轻诊断支付 199 元。</span>
            </label>
          </div>
          <div id="acceptanceProgress" class="acceptance-progress">已确认 0 / 5 项</div>
        </div>
      </div>
    </section>
  </main>

  <script>
    const sampleEndpoints = {
      "public-dogfood": "/api/live-commerce/sample/public-dogfood",
      "week-one": "/api/live-commerce/sample/week-one",
    };

    const comparisonEndpoints = {
      "week-one": "/api/live-commerce/comparison/week-one",
    };

    const labels = {
      gmv: "GMV",
      paid_gmv: "支付 GMV",
      pay_order_count: "支付订单数",
      pay_buyer_count: "支付买家数",
      average_order_value: "客单价",
      refund_rate: "退款率",
      gpm: "GPM",
      payment_conversion_rate: "支付转化",
    };

    const metricOrder = [
      "gmv", "paid_gmv", "refund_rate", "gpm",
      "payment_conversion_rate", "average_order_value", "pay_order_count", "pay_buyer_count"
    ];

    document
      .getElementById("publicSample")
      .addEventListener("click", () => loadSample("public-dogfood"));
    document
      .getElementById("weekSample")
      .addEventListener("click", () => loadSample("week-one"));
    document
      .getElementById("weekCompare")
      .addEventListener("click", () => loadComparison("week-one"));
    document.getElementById("runIntake").addEventListener("click", submitIntake);
    document.getElementById("copyReport").addEventListener("click", copyReport);
    for (const checkbox of document.querySelectorAll(".acceptance-check")) {
      checkbox.addEventListener("change", updateAcceptanceProgress);
    }

    async function loadSample(sampleId) {
      setBusy(true);
      try {
        const response = await fetch(sampleEndpoints[sampleId]);
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "diagnosis failed");
        renderPayload(payload);
      } catch (error) {
        document.getElementById("status").textContent = `诊断失败：${error.message}`;
      } finally {
        setBusy(false);
      }
    }

    async function loadComparison(sampleId) {
      setBusy(true);
      try {
        const response = await fetch(comparisonEndpoints[sampleId]);
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "comparison failed");
        renderComparison(payload);
      } catch (error) {
        document.getElementById("status").textContent = `对比失败：${error.message}`;
      } finally {
        setBusy(false);
      }
    }

    async function submitIntake() {
      setBusy(true);
      try {
        const payload = {
          primary_question: document.getElementById("intakeQuestion").value,
          live_sessions_csv: await selectedOrPastedText("sessionsFile", "sessionsPaste"),
          orders_csv: await selectedOrPastedText("ordersFile", "ordersPaste"),
        };
        const response = await fetch("/api/live-commerce/intake", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "intake failed");
        if (result.metrics === null) {
          renderBlockedIntake(result);
        } else {
          document.getElementById("intakeQuestions").hidden = true;
          renderPayload(result);
        }
      } catch (error) {
        document.getElementById("status").textContent = `本地 intake 失败：${error.message}`;
      } finally {
        setBusy(false);
      }
    }

    async function selectedOrPastedText(fileInputId, textareaId) {
      const file = document.getElementById(fileInputId).files[0];
      if (file) return file.text();
      const text = document.getElementById(textareaId).value;
      if (!text.trim()) throw new Error("请选择两个 CSV 文件，或粘贴两张表的 CSV 文本");
      return text;
    }

    function renderBlockedIntake(payload) {
      document.getElementById("empty").hidden = false;
      document.getElementById("result").hidden = true;
      document.getElementById("comparison").hidden = true;
      document.getElementById("report").textContent = "";
      document.getElementById("copyReport").disabled = true;
      const questions = document.getElementById("intakeQuestions");
      questions.hidden = false;
      const blockers = [
        ...payload.follow_up_questions,
        ...payload.delivery_preview.redaction_fields.map(
          (field) => `直接个人信息字段“${field}”必须先删除、打码或不可逆匿名化。`
        ),
      ];
      questions.innerHTML = `<h3>还不能生成经营结论</h3>` + blockers
        .map((item) => `<p>· ${escapeHtml(item)}</p>`)
        .join("");
      renderDeliveryPreview(payload.delivery_preview);
      document.getElementById("status").textContent = payload.decision.next_action;
    }

    function renderPayload(payload) {
      document.getElementById("empty").hidden = true;
      document.getElementById("result").hidden = false;
      document.getElementById("comparison").hidden = true;
      document.getElementById("sampleName").textContent = payload.sample_name;
      document.getElementById("sourceNote").textContent = payload.source_note;
      document.getElementById("metrics").innerHTML = metricOrder
        .map((key) => metricCard(key, payload.metrics[key]))
        .join("");
      document.getElementById("mappingSummary").textContent =
        `必需字段覆盖率 ${payload.mapping.coverage_percent}% · ` +
        `可计算指标 ${payload.mapping.computable_metric_ids.length} 个 · ` +
        `敏感字段 ${payload.mapping.sensitive_source_columns.join("、") || "无"}`;
      document.getElementById("mappingTags").innerHTML = payload.mapping.mapped_fields
        .filter((field) => field.required)
        .map((field) =>
          `<span class="tag">${escapeHtml(field.field_id)} ← ` +
          `${escapeHtml(field.source_column)}</span>`
        )
        .join("");
      document.getElementById("findings").innerHTML = payload.findings.map(findingCard).join("");
      document.getElementById("checks").innerHTML = payload.human_checks
        .map((item) => `<p>· ${escapeHtml(item)}</p>`)
        .join("");
      document.getElementById("report").textContent = payload.report_markdown;
      document.getElementById("copyReport").disabled = false;
      renderDeliveryPreview(payload.delivery_preview);
      document.getElementById("status").textContent = payload.decision.next_action;
    }

    function renderComparison(payload) {
      document.getElementById("empty").hidden = true;
      document.getElementById("result").hidden = true;
      document.getElementById("comparison").hidden = false;
      document.getElementById("deliveryPreviewPanel").hidden = true;
      document.getElementById("ownerAcceptance").hidden = true;
      document.getElementById("comparisonQuestion").textContent = payload.question;
      const baseline = payload.baseline;
      const comparison = payload.comparison;
      const deltas = payload.metric_deltas;
      document.getElementById("comparisonMetrics").innerHTML = [
        deltaCard("支付 GMV", baseline.paid_gmv, comparison.paid_gmv, deltas.paid_gmv),
        deltaCard("GPM", baseline.gpm, comparison.gpm, deltas.gpm),
        deltaCard(
          "支付订单",
          baseline.pay_order_count,
          comparison.pay_order_count,
          deltas.pay_order_count
        ),
        deltaCard("退款率", baseline.refund_rate, comparison.refund_rate, deltas.refund_rate),
      ].join("");
      document.getElementById("comparisonFindings").innerHTML = payload.findings
        .map((finding) => `<div class="finding"><p>${escapeHtml(finding)}</p></div>`)
        .join("");
      document.getElementById("skuDeltas").innerHTML = payload.sku_contributions
        .map((item) =>
          `<span class="tag">${escapeHtml(item.product_id)}: ` +
          `${escapeHtml(item.baseline_paid_gmv)} → ` +
          `${escapeHtml(item.comparison_paid_gmv)} ` +
          `(${escapeHtml(item.paid_gmv_delta)})</span>`
        )
        .join("");
      document.getElementById("comparisonLimits").innerHTML = payload.data_limits
        .map((item) => `<p>· ${escapeHtml(item)}</p>`)
        .join("");
      document.getElementById("status").textContent =
        "已生成两场直播对比。先看支付 GMV / GPM / SKU 拖累，再补外部归因字段。";
    }

    function renderDeliveryPreview(preview) {
      document.getElementById("deliveryPreviewPanel").hidden = false;
      const ready = preview.status === "ready_for_human_review";
      document.getElementById("deliveryPreviewStatus").textContent =
        `状态：${preview.status} · raw 默认不保留 · 创建交付 run 时必须提供授权引用。`;
      document.getElementById("deliveryArtifacts").innerHTML = preview.artifacts
        .map((artifact) => {
          const state = artifact.included ? "会生成" : "当前不生成";
          const stateClass = artifact.included ? "artifact-state" : "artifact-state omitted";
          return `<div class="artifact"><code>${escapeHtml(artifact.path)}</code>` +
            `<span>${escapeHtml(artifact.purpose)}</span>` +
            `<strong class="${stateClass}">${state}</strong></div>`;
        })
        .join("");
      const warning = document.getElementById("redactionWarning");
      warning.hidden = preview.redaction_fields.length === 0;
      warning.innerHTML = preview.redaction_fields.length === 0
        ? ""
        : `<h3>隐私阻塞</h3><p>必须先处理：${preview.redaction_fields
            .map(escapeHtml).join("、")}</p>`;
      document.getElementById("ownerAcceptance").hidden = !ready;
      resetAcceptance();
    }

    function resetAcceptance() {
      for (const checkbox of document.querySelectorAll(".acceptance-check")) {
        checkbox.checked = false;
      }
      updateAcceptanceProgress();
    }

    function updateAcceptanceProgress() {
      const checks = [...document.querySelectorAll(".acceptance-check")];
      const confirmed = checks.filter((checkbox) => checkbox.checked).length;
      const suffix = confirmed === checks.length ? " · 可以提交给老板做产品决策" : "";
      document.getElementById("acceptanceProgress").textContent =
        `已确认 ${confirmed} / ${checks.length} 项${suffix}`;
    }

    function deltaCard(label, before, after, delta) {
      return `<div class="metric">` +
        `<label>${label}</label>` +
        `<strong>${escapeHtml(after)}</strong>` +
        `<p>前一场 ${escapeHtml(before)} · 变化 ${escapeHtml(delta)}</p>` +
        `</div>`;
    }

    function metricCard(key, value) {
      const kind = key === "refund_rate"
        ? "risk"
        : (key === "gpm" || key === "payment_conversion_rate" ? "warning" : "");
      return `<div class="metric ${kind}">` +
        `<label>${labels[key]}</label><strong>${escapeHtml(value)}</strong>` +
        `</div>`;
    }

    function findingCard(finding) {
      const evidence = finding.evidence.map((item) => `<p>证据：${escapeHtml(item)}</p>`).join("");
      return `<div class="finding"><h3>${escapeHtml(finding.title)}</h3>` +
        `${evidence}<p>建议：${escapeHtml(finding.recommended_action)}</p>` +
        `<p>人工确认：${escapeHtml(finding.human_check)}</p></div>`;
    }

    async function copyReport() {
      await navigator.clipboard.writeText(document.getElementById("report").textContent);
      document.getElementById("status").textContent = "报告已复制。发送前请先完成人工确认项。";
    }

    function setBusy(isBusy) {
      for (const button of document.querySelectorAll("button")) button.disabled = isBusy;
      if (!isBusy) {
        document.getElementById("copyReport").disabled =
          !document.getElementById("report").textContent;
      }
      if (isBusy) document.getElementById("status").textContent = "正在生成诊断...";
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
