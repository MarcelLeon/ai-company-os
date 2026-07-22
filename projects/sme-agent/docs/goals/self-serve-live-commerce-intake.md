# Goal Brief — Self-serve live-commerce CSV intake

**Status**: Implemented — Round 19; merchant-owner usefulness review pending
**Delivery owner**: SME Agent Lead
**Semantic decision owner**: merchant owner / finance or data steward
**Human checkpoint**: whether the returned field questions are understandable and whether a complete diagnosis is worth the 199 RMB entry offer

## User outcome

A live-commerce merchant can select or paste two local CSV exports in the browser workbench, learn whether the data is sufficient for diagnosis, and receive either evidence-backed deterministic metrics or concrete missing-field questions without sending the files to an external service.

## In scope

- Local browser selection and paste input for `live_sessions.csv` and `orders.csv`.
- Same-origin localhost intake; uploaded content stays in memory and is not persisted by SME Agent.
- Bounded input size and row count, malformed/duplicate-header rejection, and boss-readable errors.
- Domain-template field mapping before diagnosis.
- Missing-field and no-data questions when evidence is insufficient; no metrics or paid conclusion in that state.
- Reuse of the existing deterministic live-commerce diagnosis and report when required fields and rows are present.
- Tests for service contracts, HTTP intake, UI affordances, evidence preservation, and existing sample compatibility.

## Out of scope

- Cloud upload, authentication, tenancy, permanent storage, background jobs, or a platform plugin.
- XLSX parsing, automatic field-semantic inference, manual mapping UI, or LLM-generated conclusions.
- Real customer data handling or external publication.
- Changing metric formulas, platform semantics, prices, or the Xiaohongshu campaign.

## Acceptance checks

1. [x] A merchant can choose two CSV files or paste their text and submit them from the local workbench.
2. [x] The browser sends data only to the same local workbench endpoint; the server does not write intake content to disk.
3. [x] Valid complete CSVs produce the same governed metrics, findings, human checks, and report contract as bundled samples.
4. [x] Missing required fields return explicit field names and follow-up questions, with no metrics/findings/report presented as a diagnosis.
5. [x] Header-only input asks for a small anonymized data row instead of producing zero-valued business conclusions.
6. [x] Empty, malformed, duplicate-header, oversized, or over-row-limit inputs fail deterministically with a boss-readable message.
7. [x] Existing sample and comparison routes remain compatible.
8. [ ] SME tests, Ruff, format, strict mypy, and parent pytest/Ruff/mypy/diff gates pass; the full-root format check still reports the pre-existing unrelated `projects/data-agent-v1/src/data_agent_v1/engine.py`.

## Decision record for this slice

- **Chosen**: browser file reading plus JSON to a local in-memory intake service. This creates a real merchant interaction while keeping the current local-product boundary.
- **Rejected**: temporary-file upload, because customer exports should not be persisted as an implementation shortcut.
- **Rejected**: FastAPI/frontend dependencies, because the standard-library workbench already supplies the required local surface.
- **Rejected**: guessing column meaning or missing values with an LLM, because the North Star requires governed evidence and explicit uncertainty.
- **Rejected**: cloud/SaaS upload, because authentication, tenant isolation, retention, and deployment decisions are intentionally unresolved.

## Stop conditions

- Stop before changing a metric formula or claiming a platform field has a specific financial meaning without a named steward.
- Stop before storing, publishing, or sending real merchant data outside the local process.
- Register a blocker if a safe local interaction cannot distinguish insufficient evidence from a valid zero value.
