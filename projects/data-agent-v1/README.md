# Data-Agent V1

Data-Agent V1 is the first benchmark product for AI Company OS. It is a local,
deterministic enterprise data-agent with sample data, a semantic layer, a small
CLI, and 20 golden eval questions.

## Quickstart

From the repository root:

```bash
PYTHONPATH=projects/data-agent-v1/src uv run python -m data_agent_v1.cli \
  "本月华东区收入为什么下降？"
```

Expected answer includes:

- intent `east_china_revenue_drop`;
- June vs May East China paid revenue;
- a 30.0% drop;
- SQL-like evidence;
- caveats about sample data and paid revenue.

Run the golden eval:

```bash
PYTHONPATH=projects/data-agent-v1/src uv run python -m data_agent_v1.eval_runner
```

Run tests:

```bash
PYTHONPATH=projects/data-agent-v1/src uv run pytest projects/data-agent-v1/tests -q
```

## Product Boundary

This is not a SaaS and not a real customer deployment. It uses local sample CSV
files to test whether AICO can organize a team to build a data-agent with
explicit semantics, deterministic evidence, and repeatable evals.

The sample data model is documented in
[`sample_data/enterprise_week_one/README.md`](sample_data/enterprise_week_one/README.md).

## Example Questions

```text
本月华东区收入为什么下降？
广告 ROAS 低是哪个渠道拖累的？
退款率上升主要来自哪些商品或客户分群？
```
