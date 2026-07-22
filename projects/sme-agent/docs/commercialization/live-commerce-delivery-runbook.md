# Live-commerce customer delivery runbook

Use this runbook after the buyer has authorized local analysis and the operator
has two UTF-8 CSV exports. This command creates one immutable run; it does not
upload or send data anywhere.

## Required operator inputs

- a stable customer ID, such as `merchant-001`;
- a unique run ID, such as `20260721-first-diagnosis`;
- a traceable authorization reference, such as an order/ticket/chat record ID;
- an anonymized live-session CSV and order/payment CSV;
- the business question the buyer expects the report to answer.

The authorization reference is an audit claim, not legal proof. The operator
must still verify authorization and platform semantics.

## Run

From the AI Company OS repository root:

```bash
uv run --project projects/sme-agent sme-agent-live-commerce-deliver \
  --output-dir projects/sme-agent/customer-projects \
  --customer-id merchant-001 \
  --display-name "示例直播店" \
  --run-id 20260721-first-diagnosis \
  --question "这场直播的成交效率和退款风险怎么样？" \
  --authorization-reference order-or-ticket-001 \
  --live-sessions-csv /absolute/path/to/live_sessions.csv \
  --orders-csv /absolute/path/to/orders.csv
```

Raw source files are **not** copied by default. If the buyer explicitly
authorized local workspace retention and the operator needs a reproducible raw
package, add:

```text
--persist-source-files
```

Even with this flag, SME Agent does not copy sources when fields/rows are
insufficient or obvious direct-personal-data headers block delivery.

## Workspace contract

```text
customer-projects/<customer-id>/runs/<run-id>/
  intake.md
  raw/                              # empty unless explicitly retained
  work/
    field-mapping.md
    missing-field-questions.md
    diagnosis-draft.md              # only when ready
  delivery/
    redaction-checklist.md
    evidence-manifest.md
    delivery-status.md
```

Every accepted run writes mapping, questions, redaction, manifest, and status.
The evidence manifest records each source filename, row count, SHA-256, and
whether a raw copy was retained. Reusing a run ID fails instead of overwriting
earlier evidence.

## Delivery states

- `ready_for_human_review`: a diagnosis draft exists; verify all human checks
  before sending it.
- `blocked_missing_fields`: answer the named field questions and create a new
  run ID.
- `blocked_no_rows`: provide at least one anonymized row per table and create a
  new run ID.
- `blocked_redaction`: remove or irreversibly anonymize the flagged fields; no
  report or raw copy was written.

## Final human gate

Before buyer delivery:

- verify the authorization reference against the original record;
- confirm buyer/operator identifiers are anonymized and stable only where
  needed for counting;
- confirm GMV/payment/refund/view-count semantics with the merchant or steward;
- compare the report claims with `evidence-manifest.md` and the SHA-256 values;
- keep the report boundary statement and do not add unsupported attribution.
