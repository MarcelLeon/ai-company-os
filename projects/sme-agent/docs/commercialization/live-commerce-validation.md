# Live-commerce validation loop

This document is the first acceptance path for proving SME Agent is useful for
Douyin/Kuaishou-style livestream merchants.

## Validation question

Can a merchant export be mapped into a business template and produce traceable,
boss-readable metrics before any LLM wording is added?

## Required input

Minimum fields across live-session and order/payment exports:

- industry: category;
- seller: shop id and platform;
- live room: live session id, anchor id, view count;
- product: product id;
- order: order id, order created time, order status, gross amount;
- payment: payment status, paid amount, refund amount;
- buyer: anonymized buyer id.

Real customer files may use Chinese platform headers. The field-mapping service
matches canonical field ids, field names, and known aliases such as `订单编号`,
`直播场次ID`, `观看人数`, `支付金额`, and `买家匿名ID`.

## Acceptance gates

1. **Mapping coverage**: required field coverage should be 100% for a paid
   diagnosis. If below 100%, ask the merchant for missing columns instead of
   guessing.
2. **Metric computability**: paid GMV, paid order count, paid buyer count, AOV,
   refund rate, GPM, and payment conversion should be computable from mapped
   fields.
3. **Sensitive fields**: buyer ids and internal operator ids must be anonymized
   or replaced with irreversible ids.
4. **Human checks**: GMV, view count, refund, and paid amount platform口径 must be
   confirmed before the report is used for incentives or external claims.
5. **Merchant value**: the merchant should be able to recognize at least one
   actionable bottleneck: refund, GPM, payment conversion, product mix, traffic
   source, or live-room process.

## Sample data

Use the included sample files for local verification:

- `sample_data/live_commerce_week_one/live_sessions.csv`
- `sample_data/live_commerce_week_one/orders.csv`

Use the public-web-derived dogfood fixture when you want a source-linked but
non-customer dataset:

- `sample_data/live_commerce_public_dogfood/live_sessions.csv`
- `sample_data/live_commerce_public_dogfood/orders.csv`
- `sample_data/live_commerce_public_dogfood/SOURCE.md`

Expected core results:

- field mapping coverage: 100%;
- GMV: 3675;
- paid GMV: 2927;
- paid order count: 6;
- paid buyer count: 6;
- AOV: 487.83;
- refund rate: 0.17;
- GPM: 418.14;
- payment conversion rate: 0.0009.

Expected public-web dogfood results:

- field mapping coverage: 100%;
- GMV: 2850;
- paid GMV: 2249;
- paid order count: 5;
- paid buyer count: 5;
- AOV: 449.80;
- refund rate: 0.17;
- GPM: 398.97;
- payment conversion rate: 0.0009.

Generated evidence report:

- `docs/evidence/public-web-dogfood-report.md`

## Why this is commercially stronger than a generic AI chat

The agent does not start by summarizing a spreadsheet. It first checks whether
the uploaded data can support the promised business metrics. That makes the
first sales promise narrower but more credible:

> “Give me your platform export; I will first tell you whether the data is
> enough to diagnose the live room, then produce a traceable report with
> assumptions and human checks.”

## Next build slice

- Add a customer-facing runner that writes mapping report, diagnosis report, and
  evidence manifest into the delivery workspace.
- Add field-mapping override support for platform-specific renamed columns.
- Add trend comparison across two live sessions or two weeks.
