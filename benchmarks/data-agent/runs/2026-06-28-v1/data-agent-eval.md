# Data-Agent Eval 证据

## 命令

```bash
PYTHONPATH=projects/data-agent-v1/src uv run pytest projects/data-agent-v1/tests -q
PYTHONPATH=projects/data-agent-v1/src uv run python -m data_agent_v1.eval_runner
```

## 期望结果

- 单测通过。
- Golden eval 输出 `golden_eval: 20/20 passed`。

## 实际结果

```text
PYTHONPATH=projects/data-agent-v1/src uv run pytest projects/data-agent-v1/tests tests/unit/test_data_agent_project.py -q
7 passed

PYTHONPATH=projects/data-agent-v1/src uv run python -m data_agent_v1.eval_runner
golden_eval: 20/20 passed

PYTHONPATH=projects/data-agent-v1/src uv run pytest -q
478 passed, 1 skipped
```

2026-07-02 复验:

```text
golden_eval: 20/20 passed
targeted pytest: 7 passed
```

## 三条人工验收问题

这些问题用于判断新用户能否不读源码,得到有证据的业务回答。

### 1. 本月华东区收入为什么下降？

```text
Intent: east_china_revenue_drop
Answer: 华东区本月 paid revenue 为 84,000, 上月为 120,000, 下降 36,000, 降幅 30.0%。最大拖累渠道是 Douyin, 环比减少 17,000。
Evidence:
- 2026-05 East paid revenue = 120000
- 2026-06 East paid revenue = 84000
- Douyin channel delta = -17000
Calculation: (120000 - 84000) / 120000 = 30.0% revenue drop
SQL: SELECT month, SUM(paid_revenue) FROM orders WHERE region='East' AND status='paid' GROUP BY month;
Follow-up questions:
- 是否以 paid revenue 而不是 gross revenue 作为收入口径？
- 是否需要拆到渠道、商品、客户分群三层看原因？
```

### 2. 广告 ROAS 低是哪个渠道拖累的？

```text
Intent: roas_drag
Answer: 华东区本月广告 ROAS 最低的是 Douyin: paid revenue 28,000 / ad spend 20,000 = 1.40。Kuaishou 为 2.10, Search 为 4.00。
Evidence:
- Douyin paid revenue = 28000, ad spend = 20000
- Kuaishou paid revenue = 21000, ad spend = 10000
- Search paid revenue = 20000, ad spend = 5000
Calculation: channel_roas = paid revenue attributed to channel / ad spend
SQL: SELECT channel, SUM(paid_revenue) / SUM(spend) AS roas FROM orders JOIN ad_spend USING(month, region, channel) WHERE month='2026-06' AND region='East' GROUP BY channel;
Follow-up questions:
- 是否按点击归因、直播间归因还是订单来源归因计算 ROAS？
```

### 3. 退款率上升主要来自哪些商品或客户分群？

```text
Intent: refund_contributors
Answer: 退款上升主要来自 Smart Camera: 本月退款 14,000, 占华东退款 87.5%。客户分群上 new 与 returning 各 8,000 和 7,000, 都需要复核质量原因。
Evidence:
- Smart Camera refund amount = 14000
- Total East refunds in 2026-06 = 16000
- Top refund segment = new (8000)
Calculation: refund_rate = 16000 / 84000 = 19.0%
SQL: SELECT product_name, SUM(refund_amount) FROM refunds WHERE month='2026-06' AND region='East' GROUP BY product_name;
Follow-up questions:
- 是否需要按主播话术、批次、履约 SLA 继续拆 Smart Camera？
```

## 当前产品验收摘要

- Quickstart 路径:通过。
- 三条人工业务问题:通过。
- Golden eval:20/20 通过。
- 产品限制:这是基于 synthetic CSV 的 deterministic benchmark 产品,不是数据库后端或 LLM-powered 企业部署。
- 评分含义:Data-Agent 产品半边有较强可运行证据;真实感和实用性仍需要人类判断。
