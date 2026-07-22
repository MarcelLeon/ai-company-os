# SME Agent dogfood deployment and usage

This is the current dogfooding path for SME Agent as of 2026-07-21.

## Product interaction status

SME Agent now has a local browser workbench for live-commerce diagnosis. It does
not yet have a cloud SaaS console, Telegram buyer surface, or Qianniu/Taobao
plugin UI.

The current interaction model is operator-driven:

1. The operator opens the local workbench.
2. The operator chooses a bundled sample or selects/pastes two anonymized CSV
   exports from a merchant.
3. SME Agent maps fields. Insufficient evidence returns missing-field questions
   without a diagnosis; complete evidence computes deterministic metrics and
   renders a browser-readable diagnosis plus Markdown delivery draft. Obvious
   direct-personal-data headers hard-block metrics and report display.
4. The operator reviews the non-persistent governed-artifact preview, evidence,
   redaction risk, platform口径, disclaimers, and the local `199 RMB` acceptance
   checklist.
5. Only a human decides whether the offer is worth paying for; the reviewed
   report is delivered manually to the buyer.

This is intentional for the week-one product. The sellable shape is a
service-backed AI business diagnosis, not a self-serve SaaS.

## What gets deployed

For dogfooding, "deployment" means a local browser runtime:

- Python package code under `projects/sme-agent/src`;
- bundled sample data under `projects/sme-agent/sample_data`;
- local HTTP workbench at `http://127.0.0.1:8767`;
- Markdown reports and customer workspaces generated on disk;
- no cloud database, public endpoint, external upload, or third-party platform
  credential.

This keeps the first commercial loop reviewable and low-risk while the product
promise is still being tested.

## Local setup

Run from the AI Company OS repository root:

```bash
uv run pytest projects/sme-agent/tests -q
```

Expected result:

```text
53 passed
```

If the environment is fresh and `uv` needs to fetch dependencies, run the same
command after dependency sync completes.

## Dogfood path A: local live-commerce workbench

Run:

```bash
PYTHONPATH=projects/sme-agent/src uv run python \
  -m sme_agent.commercialization.workbench
```

Open:

```text
http://127.0.0.1:8767
```

Use the buttons:

- `使用公开 dogfood 样例`;
- `使用拟真直播样例`;
- `复制交付报告`.

Or use `选择你自己的 CSV` to select or paste `live_sessions.csv` and
`orders.csv`. The browser sends them only to the same localhost workbench;
this intake path analyzes them in memory and does not write them to a customer
workspace or log. Anonymize personal fields before use. Direct-personal-data
headers such as `手机号` produce `blocked_redaction`: the page names the field,
hides metrics/findings/report, and disables report copying.

Expected product behavior:

- the first screen explains the merchant pain point, sample data model, entity
  relationships, live-commerce business process, and post-validation next steps;
- the page shows GMV, paid GMV, refund rate, GPM, payment conversion, AOV, order
  count, and buyer count;
- field mapping coverage is visible;
- findings include evidence, recommended action, and human check;
- the Markdown delivery report is visible and copyable only in the ready state;
- the immutable-package preview lists intake, mapping, missing-field questions,
  redaction checklist, evidence manifest, delivery status, and the conditional
  diagnosis draft;
- the page says previewing creates no customer workspace, retains no raw CSV,
  and creates no authorization record;
- five page-local owner checks show progress, while “worth 199 RMB” remains a
  human-only decision and is not persisted.

## Dogfood path B: live-commerce Python diagnosis

Use this path to answer the current core question:

> Can SME Agent take Douyin/Kuaishou-style live-commerce exports and produce a
> traceable, boss-readable diagnosis before any LLM prose is added?

Run:

```bash
PYTHONPATH=projects/sme-agent/src uv run python - <<'PY'
from pathlib import Path

from sme_agent.commercialization.live_commerce_diagnosis import (
    LiveCommerceDiagnosisRunner,
    LiveCommerceReportMarkdownRenderer,
)

sample = Path("projects/sme-agent/sample_data/live_commerce_public_dogfood")
report = LiveCommerceDiagnosisRunner().run(
    primary_question="这批公开来源形态样例能不能证明直播间经营诊断链路可用？",
    live_sessions_csv=sample / "live_sessions.csv",
    orders_csv=sample / "orders.csv",
)

print(LiveCommerceReportMarkdownRenderer().render(report))
PY
```

Expected signal:

- field mapping coverage: `100%`;
- GMV: `2850`;
- paid GMV: `2249`;
- paid orders: `5`;
- AOV: `449.80`;
- refund rate: `0.17`;
- GPM: `398.97`;
- payment conversion: `0.0009`;
- findings mention high refund rate, low GPM, and low payment conversion.

Before showing this output externally, read:

- `sample_data/live_commerce_public_dogfood/SOURCE.md`;
- `docs/evidence/public-web-dogfood-report.md`.

Do not present the public dogfood fixture as real merchant backend data. It is a
source-linked, scaled sample for product dogfooding.

## Dogfood path C: ecommerce delivery package

Use this path to simulate the week-one buyer delivery workflow for a standard
ecommerce shop.

Run:

```bash
PYTHONPATH=projects/sme-agent/src uv run python - <<'PY'
from pathlib import Path

from sme_agent.commercialization import EcommerceDeliveryInput, EcommerceDeliveryRunner

sample = Path("projects/sme-agent/sample_data/ecommerce_week_one")
result = EcommerceDeliveryRunner().run(
    EcommerceDeliveryInput(
        output_dir=Path("projects/sme-agent/customer-projects"),
        customer_id="seed-shop-001",
        display_name="种子电商店",
        primary_question="最近收入下降是不是广告投放导致的？",
        orders_csv=sample / "orders.csv",
        ad_spend_csv=sample / "ad_spend.csv",
        inventory_csv=sample / "inventory.csv",
    )
)

print(result.report_path)
print(result.evidence_manifest_path)
print("redaction_risk:", result.redaction_checklist.has_risk)
PY
```

Expected files:

```text
projects/sme-agent/customer-projects/seed-shop-001/
  intake.md
  raw/
  work/diagnosis-draft.md
  delivery/evidence-manifest.md
```

Expected signal:

- a diagnosis draft is written;
- an evidence manifest is written;
- sample data redaction risk is `False`.

## Dogfood path D: governed live-commerce customer workspace

Use the installed project CLI after local intake is understandable and the
operator has a traceable analysis-authorization reference:

```bash
uv run --project projects/sme-agent sme-agent-live-commerce-deliver --help
```

The run-scoped workspace always records mapping, missing-field questions,
redaction checklist, SHA-256 evidence manifest, and delivery status. A diagnosis
draft exists only when field/row readiness and direct-personal-data checks pass.
Raw CSVs are not retained unless the operator explicitly adds
`--persist-source-files`; blocked runs never copy them. Full usage and artifact
contracts are in `docs/commercialization/live-commerce-delivery-runbook.md`.

Before delivery to a real buyer, the operator must confirm:

- the buyer authorized analysis;
- personal data fields are removed or irreversibly anonymized;
- revenue, refund, ad attribution, inventory, GMV, and view-count口径 are clear;
- every recommendation is supported by the evidence manifest;
- the disclaimer section remains in the final report.

## Buyer-facing dogfood script

Use this script for a first human dogfood review:

1. "Here are two CSV exports. One contains live-session view counts, one contains
   order/payment rows."
2. "First check whether the fields are enough for paid GMV, refund rate, GPM,
   and payment conversion."
3. "If fields are enough, generate a Markdown diagnosis draft with evidence and
   human confirmation items."
4. "The report is not final until a human confirms platform口径 and sensitive
   data handling."

The operator should judge:

- Does the first screen explain what business process is being modeled?
- Are the sample tables and entity relationships understandable without reading
  source code?
- Would a merchant understand the bottleneck without reading code?
- Does the report say what evidence supports each finding?
- Does it ask for missing口径 instead of guessing?
- Would the merchant be willing to pay for the next version with real exports?

## After local validation passes

If the local workbench feels clear and commercially credible, continue in this
order:

1. Dogfood self-serve intake with an authorized, anonymized merchant export and
   judge whether its questions and diagnosis support the 199 RMB entry offer.
2. Dogfood one governed customer workspace and verify its authorization,
   fingerprints, blocked/ready status, and handoff clarity.
3. Only after the owner accepts that flow, inspect Taobao/Qianniu publishing and
   stop before final publication or any paid/external action.

## Current gaps

- No cloud SaaS, buyer login, chat UI, authentication, or tenant isolation. The
  self-serve intake is localhost-only.
- No cloud deployment or tenant/auth layer.
- The live-commerce workspace runner is local/file-backed; it has no remote
  customer portal, encryption-key workflow, or cloud retention policy.
- No field override UI yet; missing-column questions are generated from the
  governed domain-template mapping.
- No Taobao/Qianniu publish-flow inspection yet.

## Current deployable slice

The current live-commerce delivery runner writes:

- mapping report;
- conditional diagnosis draft;
- evidence manifest;
- redaction checklist;
- missing-field questions;
- delivery status.

This makes local live-commerce dogfooding match the governed buyer delivery
workflow without claiming a cloud product or automatic final delivery.
