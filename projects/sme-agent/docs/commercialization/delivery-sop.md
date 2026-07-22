# Week-one delivery SOP

## Promise

Deliver a human-reviewed AI business diagnosis report from buyer-provided ecommerce data. The first version accepts CSV or Excel-exported tables that can be converted to CSV.

## Intake

1. Ask the buyer for one primary question, for example: "为什么最近收入下降？"
2. Ask which tables they can provide: orders, inventory, ad spend, refunds, customers.
3. Ask for explicit authorization to analyze the submitted data.
4. Ask the buyer to remove or minimize personal data before upload.
5. Reject or downgrade the order if the buyer cannot provide data or a concrete question.

## Data folder convention

```text
customer-projects/<customer-id>/
  intake.md
  raw/
    orders.csv
    ad_spend.csv
    inventory.csv
  work/
    diagnosis-draft.md
  delivery/
    final-report.md
    evidence-manifest.md
```

## First supported CSV schemas

### orders.csv

Required columns:

- `order_id`
- `order_date`
- `region`
- `channel`
- `sku`
- `quantity`
- `gross_revenue`
- `refund_amount`

### ad_spend.csv

Required columns:

- `date`
- `channel`
- `spend`
- `attributed_revenue`

### inventory.csv

Required columns:

- `sku`
- `stock_qty`
- `units_sold_30d`
- `unit_cost`

## Delivery workflow

1. Run deterministic intake assessment.
2. Load CSVs and generate the diagnosis draft.
3. Check whether the draft only states evidence-backed findings.
4. Manually verify business semantics: revenue, refunds, ad attribution, inventory seasonality.
5. Polish the report for buyer readability.
6. Deliver the report and ask for usefulness feedback.
7. Convert anonymized lessons into product backlog and Xiaohongshu content.

## Stop conditions

- The buyer asks for guaranteed sales growth.
- The buyer sends sensitive personal information that is unnecessary for the diagnosis.
- The data cannot support the primary question.
- The question requires legal, tax, accounting, investment, or medical advice.
