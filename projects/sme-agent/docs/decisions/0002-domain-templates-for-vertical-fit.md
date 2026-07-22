# ADR-0002: Domain templates for vertical fit

**Status**: Accepted
**Date**: 2026-06-24

## Decision

SME Agent will model merchant verticals with explicit domain templates before
data ingestion and agent diagnosis.

The first template is live/content commerce for Douyin/Kuaishou-style small
merchants. Local services and performance advertising are represented as early
extension templates so future work can add fields and metrics without changing
the agent runtime.

## Why

- A merchant-facing product must prove that it understands a business process,
  not merely that it can chat over uploaded spreadsheets.
- Live/content commerce diagnostics require industry, seller, content, live
  room, product, order, payment, refund, and fulfillment semantics.
- Different verticals share the same metadata and diagnosis pipeline, but their
  dimensions, metrics, sensitive identifiers, and human checks differ.
- Explicit templates make value validation measurable: can a real export map to
  required fields, compute the promised metrics, and produce evidence-backed
  recommendations?

## Rejected

- Treating every uploaded CSV as an anonymous table: faster to demo, but it
  produces toy answers and weak commercial trust.
- Hard-coding Douyin/Kuaishou fields into the diagnosis runner: blocks local
  services and advertising expansion.
- Building a universal ontology upfront: too abstract before real customer
  exports and paid feedback exist.

## Consequences

- New verticals are added by registering a `DomainTemplate`.
- Templates must declare required fields, dimensions, metrics, sensitive fields,
  human checks, and extension points.
- The next commercial validation slice should map real merchant exports into
  the live-commerce template before expanding the agent loop.
