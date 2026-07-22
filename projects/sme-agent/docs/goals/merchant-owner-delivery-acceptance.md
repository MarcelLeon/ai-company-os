# Goal Brief — Merchant-owner delivery acceptance console

**Status**: Complete — Round 21
**Delivery owner**: SME Agent Lead
**Decision owner**: merchant owner
**Evidence owner**: SME Agent Tester / Reviewer

## User outcome

After loading a bundled sample or two anonymized CSVs in the local workbench,
the merchant owner can see exactly which governed customer-delivery artifacts
would be created, which privacy/readiness gate controls the draft, and whether
the current 199 RMB field-check/mini-diagnosis is understandable enough to
accept. This preview must not create a workspace or claim authorization.

## In scope

- A delivery-package preview derived from the same readiness and redaction
  rules as `LiveCommerceDeliveryRunner`.
- A visible package status, artifact list, raw-retention default, authorization
  requirement, and next operator action.
- A local interactive acceptance checklist covering clarity, evidence,
  actionability, privacy, and willingness to pay.
- Direct-personal-data headers block metrics/report display in the workbench,
  matching the governed runner rather than relying on warning copy alone.
- Ready, missing-field, and redaction-blocked tests plus desktop/mobile browser
  evidence.

## Out of scope

- Creating a customer workspace from the browser.
- Persisting checkbox/acceptance decisions, CSV text, or authorization claims.
- Raw-source retention, cloud upload, authentication, tenancy, payment, or
  external delivery.
- Declaring the 199 RMB offer accepted on behalf of the merchant owner.
- Changing metric formulas, campaign copy, or external Xiaohongshu actions.

## Acceptance checks

1. [x] Ready evidence previews the six always-written governance artifacts plus
   `work/diagnosis-draft.md`, with raw retention off and authorization required.
2. [x] Missing-field/no-row evidence omits the diagnosis draft and gives the
   same blocked status/next action as the runner.
3. [x] Direct-personal-data headers produce `blocked_redaction`, expose the
   flagged field, and suppress metrics, findings, and copyable report.
4. [x] The page explicitly says previewing does not create a workspace or
   authorization record.
5. [x] Five owner acceptance checks are interactive and show progress without
   network or filesystem persistence; only the human can select “worth 199”.
6. [x] Existing sample, comparison, intake, and copy-report flows remain green.
7. [x] Desktop and 390-pixel mobile QA cover ready and redaction-blocked states,
   console health, no horizontal overflow, and checklist interaction.
8. [x] SME/root tests, Ruff, strict mypy, touched format, structure, diff, and
   continuity records pass; unrelated root format debt stays separate.

## Decision

- **Chosen**: preview the real governed package contract in the workbench before
  connecting persistence. This gives the owner a decision surface without
  crossing the Round 20 human checkpoint.
- **Chosen**: reuse delivery status/redaction logic rather than duplicate UI
  heuristics.
- **Rejected**: add a “create workspace” browser button now. It would let the UI
  manufacture authorization and durable customer state before owner acceptance.
- **Rejected**: leave privacy as instructional copy. A commercial workbench must
  enforce the same direct-personal-data stop as the delivery runner.

## Stop conditions

- Stop if previewing writes outside the existing localhost response.
- Stop if an acceptance checkbox or button is presented as legal/semantic
  approval.
- Register a blocker if UI and runner can disagree on delivery status.
