# Goal Brief — Phase 1 Governed Metadata

**Status**: Implemented contract; pending real AICO project-office dogfood and human semantic acceptance
**Delivery owner**: SME Agent Lead
**Semantic decision owner**: business/data steward
**Human checkpoint**: metric meaning, filter meaning, source authority, and usefulness

## User outcome

An operations analyst can ask “Why did East China revenue decline this month?” and the system can resolve the governed revenue metric, region dimension, business entity, warehouse source, and explanatory knowledge without guessing their meaning.

## In scope

- A representative small-business dataset containing at least one asset of every metadata kind.
- Create, update, fetch, search, and relate governed metadata.
- Traverse metric → dimension → warehouse asset → entity → knowledge evidence.
- Preserve owner, aliases, descriptions, stable identifiers, versions, source references, and steward approval.
- Represent question filter values separately from dimension definitions.
- Enforce allowed relationship directions and source/target metadata kinds.
- Application tests for valid and invalid relationships.

## Out of scope

- Natural-language-to-SQL execution.
- Document chunking, embeddings, reranking, or an LLM call.
- Web UI, tenant authentication, and production deployment.
- Choosing the permanent database before access patterns are measured.

## Acceptance evidence

1. [x] A fixture represents revenue, region, orders, an order fact table, and a business-definition document.
2. [x] `营业收入` resolves through the glossary `DEFINES` edge to the governed revenue metric.
3. [x] Starting from revenue returns allowed dimensions, filter values, and the source warehouse asset.
4. [x] Grounding output names every metadata ID used; it does not claim to contain a cited document passage yet.
5. [x] Unknown endpoints, self-relations, invalid type/direction signatures, ambiguous aliases, and unrelated dimensions fail deterministically.
6. [x] Metadata changes require a higher version; approved records require a steward and source references.
7. [x] Unit/application tests, ruff, formatting, and strict mypy pass locally.
8. [ ] Real AICO Lead → Challenger → decision → restart/morning recovery evidence is captured.

## Stop conditions

- Stop and ask the human if two competing definitions of revenue are both plausible.
- Stop and register a blocker if permissions cannot be represented without leaking restricted metadata.
- Do not add infrastructure merely to make the demo look complete.
