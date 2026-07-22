# Domain templates

## Why this exists

SME Agent should not claim to understand every small business spreadsheet. A useful business agent needs a vertical semantic spine:

- who the merchant is;
- what business process produced the data;
- which dimensions explain changes;
- which metrics matter;
- which fields are sensitive;
- which conclusions require human checks.

The first serious vertical is live/content commerce for Douyin/Kuaishou-style small merchants.

## Live/content commerce template

Target users:

- Douyin/Kuaishou small merchants.
- Livestream anchor teams.
- Content-commerce operators.

Supported processes:

- content;
- live room;
- product;
- order;
- payment;
- refund;
- fulfillment.

Core dimensions:

- industry: category, price band, brand type;
- seller: shop, platform, seller type, operator;
- content: short video or traffic source;
- live room: session, anchor, views, duration;
- product: product, SKU, title, cost;
- order: order id, status, gross amount, buyer;
- payment: payment status, paid amount, refund amount.

Core metrics:

- GMV;
- paid GMV;
- paid order count;
- paid buyer count;
- average order value;
- refund rate;
- GPM;
- payment conversion rate.

## Extension design

New verticals are added as templates, not as changes to the agent runtime. Current template kinds:

- `live_commerce`: content/live ecommerce merchants.
- `local_services`: store and coupon-verification merchants.
- `performance_ads`: advertisers and lead-generation businesses.

The same application can later route customer data into the matching template:

```text
uploaded files
  -> field mapping
  -> domain template
  -> metadata catalog
  -> deterministic metrics
  -> report / alert / agent answer
```

## How this proves the project is not a toy

Toy agents treat every uploaded file as text. SME Agent uses templates to decide:

- which fields are expected;
- which metrics can be computed;
- which dimensions are meaningful;
- which identifiers require redaction;
- which human checks are mandatory.

This makes the system extensible without claiming universal understanding.

## Next implementation slices

1. Field-mapping assistant: map platform exports to template fields.
2. Live-commerce diagnosis runner: compute paid GMV, GPM, refund rate, conversion, and AOV from mapped files.
3. Output profiles: boss brief, full diagnosis, alert message.
4. Alert rules: refund rate, GPM drop, paid GMV drop, low payment conversion.
5. Knowledge ingestion: merchant personnel, SOP, product policy, and platform notes.
