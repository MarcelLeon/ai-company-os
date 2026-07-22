# PITFALLS.md

## P-001 — Confusing AICO organization memory with business knowledge

**Status**: Preventive
**Risk**: AICO memory records how the development team works; SME Agent knowledge records governed enterprise facts and evidence.

**Rule**: Keep the stores, schemas, retention, permissions, and retrieval policies separate. References may cross the boundary only through explicit project artifacts.

## P-002 — Calling provider introspection a skill registry

**Status**: Preventive
**Risk**: AICO `/skills` and `/tools` ask a provider what it can do. They do not provide versioned business Skill/Tool lifecycle management.

**Rule**: SME Agent must implement explicit registries with schemas, versions, policies, audit, and evaluation.

## P-003 — Treating incomplete CSV evidence as zero business performance

**Status**: Resolved in Round 19
**Risk**: Header-only files, missing payment columns, or empty exports can look like zero GMV/conversion if diagnosis runs before evidence readiness is established.

**Rule**: Map and validate required fields plus at least one data row before diagnosis. When evidence is insufficient, return explicit questions and keep metrics, findings, and report absent; never sell a zero-valued conclusion from missing evidence.

## P-004 — Overwriting customer evidence or retaining raw exports by convenience

**Status**: Resolved in Round 20
**Risk**: Reusing one customer report path can erase the facts behind an earlier decision; eagerly copying raw CSVs can retain personal data even when the run is blocked.

**Rule**: Use a unique immutable run ID, fail on collision, record an authorization reference and source fingerprint, always preserve blocked-state artifacts, and retain raw sources only after explicit opt-in plus readiness/redaction gates.

## P-005 — Treating privacy warning copy as a delivery gate

**Status**: Resolved in Round 21
**Risk**: A workbench can warn the operator to anonymize data yet still render and copy a paid diagnosis when direct-personal-data headers are present, while the governed delivery runner correctly blocks the same evidence.

**Rule**: Every product surface must derive readiness and redaction from the same delivery assessment. `blocked_redaction` must suppress metrics, findings, report display/copy, and commercial acceptance controls; instructional copy is not enforcement.
