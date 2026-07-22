# Evidence Manifest — Round 1

**Date**: 2026-06-18
**Revision**: uncommitted workspace; must be replaced by a commit SHA before release
**Goal**: Phase 1 governed metadata contract closure

## Deterministic evidence

- `uv run pytest projects/sme-agent/tests -q` → 10 passed after relationship/glossary/filter/governance corrections.
- `uv run ruff check projects/sme-agent/src projects/sme-agent/tests` → passed.
- `uv run mypy --config-file projects/sme-agent/pyproject.toml projects/sme-agent/src projects/sme-agent/tests` → passed.
- `uv run pytest -q` from the AICO root → 452 passed, 1 skipped.
- Root ruff, format check, AICO mypy, SME Agent strict mypy, and diff check → passed.
- Root CI workflow now contains an explicit SME Agent strict-mypy step.

## Behavior evidence

Input question: `华东区本月收入为什么下降？`

Structured grounding resolves:

- glossary: `term.recognized_revenue`
- metric: `metric.revenue`
- filters: region=`华东区`, order_month=`本月`
- dimensions: `dimension.region`, `dimension.order_month`
- warehouse: `table.analytics.fact_order_line`
- entity: `entity.order`
- knowledge reference: `document.finance.revenue_policy`

This is metadata grounding, not a cited passage or causal answer.

## Independent review evidence

- Lead review: conditional support; required relationship policy, glossary traversal, and artifact reconciliation before persistence.
- Challenger review: conditional support; additionally required explicit filters, steward approval, durable evidence, CI strict mypy, and real AICO recovery dogfood.
- Valid findings were incorporated in this round. External Claude CLI review was not used because workspace export to a third-party model was not authorized.

## Remaining gates

- AICO runtime switch passed: the old poller was stopped and the SME-configured runtime started with isolated state/memory/audit paths.
- User-side Telegram commands, task/trace IDs, and restart/morning evidence remain; the local Telegram desktop app did not stay open in this automation environment.
- Human finance/data-steward semantic approval.
- Commit SHA replacing the uncommitted revision marker.
