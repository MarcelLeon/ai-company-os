# Goal Brief — Governed live-commerce customer workspace

**Status**: Implemented — Round 20; merchant-owner usefulness review pending
**Delivery owner**: SME Agent Lead
**Semantic decision owner**: merchant owner / finance or data steward
**Human checkpoint**: confirm authorization, anonymization, platform semantics, and whether the draft is fit to deliver

## User outcome

An authorized operator can turn two merchant live-commerce CSV exports into a
run-scoped, resumable customer workspace. The workspace must make evidence,
field readiness, privacy risk, and the next human action inspectable even when
the owner is absent.

## In scope

- A run-scoped workspace that never silently overwrites a previous diagnosis.
- A required analysis-authorization reference recorded in the intake artifact.
- SHA-256 fingerprints and row counts for both submitted sources.
- Mapping report, missing-field questions, redaction checklist, evidence
  manifest, and delivery status artifacts for every accepted run.
- Diagnosis draft only when required fields and rows are present and no obvious
  direct-personal-data header blocks delivery.
- Optional local source retention only when explicitly requested and only after
  readiness/privacy gates pass.
- A standard-library CLI suitable for an operator or later AICO task adapter.
- Tests for ready, missing-field, redaction-blocked, overwrite, retention, and
  CLI behavior.

## Out of scope

- Cloud storage, buyer login, tenancy, encryption key management, or remote
  delivery.
- Automatic proof that an authorization reference is legally sufficient.
- Guessing missing values/column semantics or removing personal data.
- Finalizing the report without merchant/finance/data-steward review.
- Changing existing metric formulas, prices, or external campaign actions.

## Acceptance checks

1. [x] A unique run produces a customer workspace under a stable customer/run path.
2. [x] Reusing the same run ID fails before any existing evidence is overwritten.
3. [x] Intake records customer, service tier, primary question, run ID, and the
   non-empty authorization reference.
4. [x] Mapping, questions, redaction, evidence manifest, and delivery status exist
   for ready and blocked runs.
5. [x] Missing fields/no rows produce no diagnosis draft and a blocked status with
   concrete follow-up questions.
6. [x] Obvious direct-personal-data headers produce no diagnosis draft or raw copy
   and a blocked-redaction status.
7. [x] Ready evidence produces the governed diagnosis; raw source copies are absent
   by default and written only with explicit retention opt-in.
8. [x] Evidence manifest records source filename, row count, SHA-256, retention
   state, limitations, and human-check requirements.
9. [ ] CLI and library contracts have red-green tests; SME and parent pytest,
   Ruff, mypy, touched format, diff, and structure gates pass. Full-root format
   still reports the unrelated pre-existing data-agent file recorded in status.

## Decision record

- **Chosen**: one immutable run directory per customer diagnosis. This preserves
  evidence history and makes retries/audits safe under boss absence.
- **Chosen**: authorization reference as required input, not a default boolean;
  it creates an auditable claim without pretending SME Agent can validate law.
- **Chosen**: derived artifacts by default, explicit opt-in for local raw copies.
- **Rejected**: writing over `customer-id/work/diagnosis-draft.md`, because a
  retry could erase the evidence the previous decision relied on.
- **Rejected**: copying raw files before readiness/redaction checks, because a
  convenience path must not silently retain risky customer data.
- **Rejected**: a new workflow framework or database. This is the second delivery
  vertical, so it reuses current concrete services and stays file-backed.

## Stop conditions

- Stop before storing or sending data outside the operator-selected local path.
- Stop before claiming the authorization reference or anonymization is legally
  sufficient.
- Register a blocker if a run can overwrite prior evidence or produce a report
  while readiness/privacy is blocked.
