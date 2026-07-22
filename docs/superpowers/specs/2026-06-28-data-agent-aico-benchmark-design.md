# Data-Agent AICO Benchmark Design

## Context

The human hypothesis is that complex dynamic work should eventually be handled
by orchestrated multi-agent teams, with the human absent for most execution and
present for goal setting, risk approval, and acceptance. AICO's north star
matches this: local AI CLI tools should act like a remote team managed through
IM.

The product weakness is not missing primitives. AICO already has project
offices, roles, goal briefs, overnight delegation, morning handoff, audit,
task trace, and view snapshots. The weakness is that these primitives are not
yet packaged as a repeatable "use AICO to build a high-quality product" journey.

## Decision

Create a repeatable Data-Agent benchmark:

- Use AICO to build `data-agent-v1`.
- Score both AICO orchestration and the produced data-agent.
- Improve AICO based on the score.
- Build `data-agent-v2` under the same scorecard.
- Compare score deltas.

The benchmark product is an enterprise data-agent because it requires product
planning, semantic correctness, deterministic tests, ambiguity handling,
security boundaries, and a real human acceptance path.

## Artifacts

- `docs/benchmarks/data-agent-aico-benchmark.md`: benchmark contract and loop.
- `docs/human/data-agent-aico-sop.md`: human operating procedure.
- `benchmarks/data-agent/scorecard.md`: 100-point scorecard.

## Scope

This design only defines the benchmark and SOP. It does not yet create the
`data-agent-v1` project, AICO project config, datasets, evals, or runtime
evidence. Those are the next implementation slice.

## Acceptance

The design is acceptable when:

- the benchmark judges AICO by a real delivered product, not feature inventory;
- the data-agent contract requires runnable behavior and deterministic evals;
- the SOP keeps the human in a boss role instead of an operator role;
- the scorecard separately measures AICO orchestration and data-agent quality;
- anti-cheating rules prevent changing the goalposts after the run.

## Self-Review

- No placeholder criteria remain.
- The benchmark has explicit non-goals and fail conditions.
- Human, machine, and computer-use verification responsibilities are separated.
- The next implementation slice is clear: create `projects/data-agent-v1/`,
  its AICO project config, sample data, eval skeleton, and run evidence folder.
