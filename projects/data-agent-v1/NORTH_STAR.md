# NORTH_STAR.md

Data-Agent V1 exists to answer one benchmark question:

> Can AICO organize a local multi-agent team to build a useful enterprise
> data-agent product while the human behaves like a boss, not an operator?

## Product Promise

Data-Agent V1 should let a business user ask common revenue, advertising,
refund, customer, inventory, region, channel, and product questions over local
sample data and receive:

- the business answer;
- evidence rows or aggregates;
- a SQL-like query or deterministic calculation path;
- caveats and source authority;
- follow-up questions when the request is ambiguous.

## Non-Goals

- No cloud deployment.
- No tenant/auth system.
- No real customer data.
- No LLM-only answers.
- No claim that synthetic benchmark data represents a real company.

## Acceptance Anchor

The human should be able to run the product from the README, ask three business
questions, inspect the 20-question golden eval, and fill the benchmark scorecard
without reading source code.
