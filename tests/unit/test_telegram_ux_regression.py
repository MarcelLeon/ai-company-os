"""Regression checks for Telegram boss-readable output."""

from __future__ import annotations

from aico.core.models import MessageTextStyle
from aico.core.native_output import agent_output_message


def test_real_review_output_bad_signatures_are_removed() -> None:
    message = agent_output_message(
        "Findings1. CI does not enforce Data-Agent mypy. "
        "[.github/workflows/ci.yml]"
        "(/Users/wangzq/VsCodeProjects/ai-company-os/.github/workflows/ci.yml:38) "
        "runs root mypy.2. Unignored runtime state is present."
        "Missing Tests未看到 SQL/evidence contract tests."
        "Verdict: oppose"
    )

    assert "Findings1." not in message.text
    assert ".2. Unignored" not in message.text
    assert "Missing Tests未" not in message.text
    assert "](/Users/" not in message.text
    assert ".github/workflows/ci.yml:38" in message.text


def test_small_markdown_table_renders_as_compact_telegram_table() -> None:
    message = agent_output_message(
        "Decision matrix\n"
        "| Option | Decision |\n"
        "|---|---|\n"
        "| Start v2 | Reject |\n"
        "| Fix AICO | Accept |"
    )

    assert "| Option | Decision |" not in message.text
    assert "| --- | --- |" not in message.text
    assert "Option" in message.text
    assert "Decision" in message.text
    assert "Start v2" in message.text
    assert "Reject" in message.text
    assert "• Option:" not in message.text


def test_wide_markdown_table_renders_as_truncated_telegram_table_with_details() -> None:
    message = agent_output_message(
        "Decision matrix\n"
        "| Option | Decision | Owner | Evidence |\n"
        "|---|---|---|---|\n"
        "| Start v2 | Reject | lead | needs another full benchmark cycle |\n"
        "| Fix AICO | Accept | implementer | directly improves Telegram evidence |"
    )

    assert "|---|---|---|---|" not in message.text
    assert "| Option | Decision | Owner | Evidence |" not in message.text
    assert "Option" in message.text
    assert "Decision" in message.text
    assert "Evidence" in message.text
    assert "needs an…" in message.text
    assert "详情: /view 查看完整表格" in message.text


def test_glued_markdown_table_is_split_before_rendering() -> None:
    message = agent_output_message(
        "👥 本轮角色分工(R7-01)"
        "| 角色 | seat | 状态 | 交付 |"
        "|---|---|---|---|"
        "| lead(我) | data-agent-v1-lead | active | 决策 memo |"
        "| reviewer | data-agent-v1-reviewer | on-file only | 复核 |"
    )

    assert "|---|---|---|---|" not in message.text
    assert "本轮角色分工(R7-01)\n" in message.text
    assert "角色" in message.text
    assert "seat" in message.text
    assert "lead(我)" in message.text
    assert "data-age…" in message.text


def test_malformed_table_extra_cells_use_boss_readable_label() -> None:
    message = agent_output_message(
        "| 角色 | 状态 | 交付 |\n|---|---|---|\n| lead | active | 决策 | 这是额外说明 |"
    )

    assert "col 4" not in message.text
    assert "补充1" in message.text
    assert "这是额外…" in message.text


def test_chinese_numbered_heading_is_split_before_list() -> None:
    message = agent_output_message(
        "今日验收 3 条要点1. 小表保留 Markdown 表格。"
        "2. 宽表降级为字段列表。3. /view 先解释再发附件。"
    )

    assert "要点1." not in message.text
    assert "今日验收 3 条要点\n\n1. 小表保留 Markdown 表格。" in message.text
    assert "\n\n2. 宽表降级为字段列表。" in message.text
    assert "\n\n3. /view 先解释再发附件。" in message.text


def test_compact_severity_headings_expand_to_boss_cards() -> None:
    message = agent_output_message(
        "FindingsHigh: 表格仍然横向难读。Medium: /inbox 已经可读。"
        "Risks / approval need- 真实 Claude role 可能输出 unsupported HTML。"
        "Next Actions- 跑 3 条 Telegram 抽样。"
    )

    assert "FindingsHigh:" not in message.text
    assert "Risks / approval need-" not in message.text
    assert "Next Actions-" not in message.text
    assert "Findings\n\nHigh: 表格仍然横向难读。" in message.text
    assert "\n\nMedium: /inbox 已经可读。" in message.text
    assert "\n\nRisks / approval need\n真实 Claude role 可能输出 unsupported HTML。" in message.text
    assert "\n\nNext Actions\n跑 3 条 Telegram 抽样。" in message.text


def test_inline_markdown_bullets_become_scannable_list_items() -> None:
    message = agent_output_message(
        "Risks: - **High**: 宽表仍像后台 dump - **Medium**: 列表项缺少换行 "
        "- **Low**: 代码块需要保留等宽"
    )

    assert "- High" not in message.text
    assert "• High: 宽表仍像后台 dump" in message.text
    assert "\n\n• Medium: 列表项缺少换行" in message.text
    assert "\n\n• Low: 代码块需要保留等宽" in message.text


def test_unsupported_native_html_lists_fall_back_to_readable_bullets() -> None:
    message = agent_output_message(
        "<b>Risks</b><ul><li>High: 表格过宽</li><li>Medium: 列表粘连</li></ul>",
    )

    styles = [(span.offset, span.length, span.style) for span in message.spans]
    assert "<ul>" not in message.text
    assert "<li>" not in message.text
    assert "<b>" not in message.text
    assert "Risks" in message.text
    assert (message.text.index("Risks"), len("Risks"), MessageTextStyle.BOLD) in styles
    assert "• High: 表格过宽" in message.text
    assert "• Medium: 列表粘连" in message.text


def test_telegram_showcase_sample_uses_compact_tables_and_lazy_details() -> None:
    message = agent_output_message(
        "Telegram 展示样例\n"
        "小表\n"
        "| 风险项 | 状态 |\n"
        "|---|---|\n"
        "| HTML list | 已降级 |\n"
        "| Markdown table | 不裸发 |\n"
        "宽表\n"
        "| Item | Owner | Risk | Next |\n"
        "|---|---|---|---|\n"
        "| 表格 | reviewer | 错乱 | 改字段列表 |\n"
        "<b>Risks</b><ul><li>High: 表格错乱</li></ul>"
    )

    assert "|---|" not in message.text
    assert "| 风险项 | 状态 |" not in message.text
    assert "| Item | Owner | Risk | Next |" not in message.text
    assert "风险项" in message.text
    assert "HTML list" in message.text
    assert "Item" in message.text
    assert "改字段列…" in message.text
    assert "详情: /view 查看完整表格" in message.text
    assert "• High: 表格错乱" in message.text


def test_mixed_width_table_uses_embedded_header_instead_of_repeated_supplement() -> None:
    message = agent_output_message(
        "| 类型 | 状态 | 说明 |\n"
        "|---|---|---|\n"
        "| 小表 | OK | 三列可读 |\n"
        "| 宽表 | Risk | 移动端可能换行 |\n"
        "| 指标 | 数据来源 | 口径 | 当前值 | 期望值 | 风险 | 处理建议 |\n"
        "| GMV | sample_orders.csv | 已支付订单汇总 | 128000 | 130000 | "
        "差异需解释 | 展示口径和过滤条件 |\n"
        "| 转化率 | sample_funnel.csv | 下单人数 / 访问人数 | 8.6% | 9.0% | "
        "宽表在 Telegram 中可能折行 | 降级为字段列表 |"
    )

    assert "补充: 当前值" not in message.text
    assert "补充: 期望值" not in message.text
    assert "指标" in message.text
    assert "数据来源" in message.text
    assert "当前值" in message.text
    assert "GMV" in message.text
    assert "128000" in message.text
    assert "详情: /view 查看完整表格" in message.text
