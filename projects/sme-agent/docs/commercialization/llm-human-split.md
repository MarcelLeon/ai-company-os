# LLM and human division of labor

## Operating principle

LLMs accelerate drafting, classification, summarization, and code. Humans own trust, consent, business semantics, pricing decisions, and customer-facing delivery approval.

## Work split

| Workflow | LLM owns | Human owns | Gate |
|---|---|---|---|
| Xiaohongshu content | Draft titles, outlines, posts, comment replies | Publish, personal voice, platform compliance judgment | No hard external-link pushing |
| Prospect chat | Generate diagnostic questions and lead summary | Real conversation, price anchoring, qualification call | No promise before data check |
| Intake | Classify readiness, missing data, recommended tier | Confirm consent, reject risky/unclear customers | Explicit authorization |
| Data analysis | Field mapping, metadata grounding, report outline | Formula acceptance, anomaly interpretation, final conclusion | Named reviewer |
| Delivery | Draft report, FAQ, next questions | Final report approval and delivery through Taobao/Qianniu | Human-reviewed report |
| Product iteration | Turn repeated failures into backlog | Choose commercial priority | Weekly AICO decision |

## AICO roles

- Lead: chooses the daily commercial/product slice and records the decision.
- Growth Writer: creates posts, hooks, and DM scripts.
- Product Manager: turns prospect objections into product requirements.
- Metadata Engineer: maintains metrics, dimensions, entities, and data sources.
- Delivery Analyst: produces report outlines and evidence checklists.
- Challenger: attacks over-claims, weak evidence, and support-cost traps.
- Reviewer: checks customer-facing assets before publication.
- Tester: keeps deterministic gates green.

## Daily commands

```text
/use project sme-agent
/ask lead 今天按一周上线目标，选择唯一最重要的商业/产品切片，并给出验收证据
/ask challenger 挑战今天的销售承诺、交付风险和长期维护风险
/daily
```

## Human input required before live selling

- Taobao shop name, current category, and whether virtual/service items can be published.
- Whether the target buyer is Taobao sellers, offline retailers, local service shops, or B2B companies.
- Price floor and maximum manual delivery hours per order.
- Accepted data types and privacy boundary.
- Whether anonymized case studies are allowed by default or opt-in only.
