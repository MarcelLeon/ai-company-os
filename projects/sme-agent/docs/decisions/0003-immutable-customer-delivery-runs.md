# ADR-0003: Immutable, authorization-referenced customer delivery runs

**Status**: Accepted
**Date**: 2026-07-21

## Decision

Live-commerce customer delivery uses one run-scoped workspace at
`<output>/<customer-id>/runs/<run-id>`. A runner refuses an existing run ID,
requires an operator-provided authorization reference, writes derived evidence
artifacts for blocked and ready states, and retains raw CSVs only after explicit
opt-in plus readiness/redaction gates.

## Why

- Boss-absent execution must not erase the evidence behind an earlier decision.
- A report without an authorization trace, field-readiness state, input
  fingerprint, or privacy decision is not commercially auditable.
- Missing evidence and privacy risk are legitimate delivery outcomes; they must
  survive handoff as artifacts instead of disappearing in a terminal error.
- Raw merchant exports are higher-risk than derived mapping/fingerprint
  artifacts and should not be retained by default.

## Rejected

- Reusing `customer-id/work/diagnosis-draft.md`: retries silently overwrite
  history and break evidence review.
- A boolean `authorized=true`: it cannot tell the next operator which order,
  ticket, or chat record supported the claim.
- Copying raw CSVs before validation: this retains unnecessary or direct
  personal data even when no valid diagnosis can be produced.
- A database/workflow engine: the second delivery vertical does not yet justify
  another infrastructure layer; file-backed immutable runs are inspectable and
  sufficient for current scale.

## Consequences

- Operators and future AICO adapters must generate a unique run ID and carry an
  authorization reference.
- Every accepted run has mapping, questions, redaction, manifest, and status;
  only ready runs have a diagnosis draft.
- SHA-256 identifies the exact submitted bytes but does not prove the source is
  truthful or semantically correct.
- Removing/anonymizing data or answering missing-field questions creates a new
  run; existing evidence is never mutated by the runner.
- Cloud storage, encryption, retention policy, and legal authorization checks
  remain deployment decisions rather than hidden assumptions in this runner.
