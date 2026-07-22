# Report generation runbook

This runbook is for the internal delivery operator. It generates the week-one ecommerce diagnosis package from CSV files.

## Sample input

Use the included sample data:

```text
sample_data/ecommerce_week_one/
  orders.csv
  ad_spend.csv
  inventory.csv
```

## Python invocation

Run from the repository root:

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

## Output

```text
customer-projects/<customer-id>/
  intake.md
  raw/
  work/
    diagnosis-draft.md
  delivery/
    evidence-manifest.md
```

## Human review checklist

Before sending the report to a buyer:

- Confirm the buyer authorized analysis.
- Confirm personal data fields were removed or anonymized.
- Confirm revenue, refund, ad attribution, and inventory semantics.
- Remove or rewrite any conclusion that is not supported by the evidence manifest.
- Keep the disclaimer section in the final report.
