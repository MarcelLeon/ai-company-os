# SME Agent

A maintainable agent platform for small and medium businesses, developed as a real project by an AI Company OS team.

The first vertical slice is a governed metadata catalog for glossary terms, knowledge documents, metrics, dimensions, warehouse assets, business entities, and their relationships.

## Local verification

From the AI Company OS repository root:

```bash
uv run pytest projects/sme-agent/tests -q
uv run ruff check projects/sme-agent/src projects/sme-agent/tests
uv run mypy --config-file projects/sme-agent/pyproject.toml \
  projects/sme-agent/src projects/sme-agent/tests
```

## Dogfood deployment and usage

The current week-one product now has a local browser diagnosis workbench. Run it
from the AI Company OS repository root:

```bash
PYTHONPATH=projects/sme-agent/src uv run python \
  -m sme_agent.commercialization.workbench
```

Then open:

```text
http://127.0.0.1:8767
```

Use the bundled live-commerce samples, or select/paste your own two anonymized
CSV exports. Missing fields return concrete follow-up questions without a
diagnosis; complete evidence produces field mapping, deterministic metrics,
findings, human checks, a copyable delivery report, and a preview of the exact
governed artifacts a later delivery run would create. The page also exposes a
five-item, page-local `199 RMB` owner acceptance checklist. Direct personal-data
headers hard-block metrics and report display. Local intake and checklist state
are not persisted by the workbench, and previewing does not create a workspace
or authorization record.

This is still a local dogfood surface, not a cloud SaaS deployment. See
`docs/operations/dogfood-deployment-usage.md` for the local dogfood setup,
live-commerce workbench flow, ecommerce delivery package flow, and current
product gaps.

## Governed customer delivery

After an operator has a traceable analysis authorization and anonymized CSVs,
create an immutable live-commerce customer run with:

```bash
uv run --project projects/sme-agent sme-agent-live-commerce-deliver --help
```

The runner writes mapping, missing-field questions, redaction checklist,
SHA-256 evidence manifest, delivery status, and—only when safe enough—a
human-review diagnosis draft. Raw CSV retention is opt-in. See
`docs/commercialization/live-commerce-delivery-runbook.md`.

## Project continuity

- Current state: `STATUS.md`
- Human/agent alignment: `docs/operating-model/alignment.md`
- AICO operation: `docs/operating-model/aico-runbook.md`
- Active Goal Brief: `docs/goals/phase-1-metadata.md`
- Current handoff: `docs/handoffs/current.md`
- Current evidence: `docs/evidence/round-1.md`
- Decisions: `docs/decisions/`
- History and known risks: `docs/journal/`
