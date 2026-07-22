# AGENTS.md

This is the only correct entry point for agents working on Data-Agent V1.

Read in order:

1. `NORTH_STAR.md`
2. `STATUS.md`
3. `docs/goals/baseline-v1.md`
4. `docs/handoffs/current.md`
5. `docs/journal/ROUNDS.md`
6. `docs/journal/PITFALLS.md`
7. `docs/journal/BLOCKERS.md`
8. Relevant source files and tests

## Product Boundary

Data-Agent V1 is a benchmark product built by AICO. It is not AICO core.
AICO owns project organization, delegation, approval, audit, and handoff.
Data-Agent V1 owns enterprise sample data, semantic definitions, deterministic
answers, evals, tests, and user quickstart.

## Hard Rules

- Do not change AICO core to make this benchmark pass unless the task is
  explicitly about improving AICO after scoring.
- Do not claim enterprise data-agent quality from model prose alone.
- Every answer must expose evidence and a SQL or deterministic calculation path.
- Ask follow-up questions when metric, time period, region, source authority, or
  privacy boundary is unclear.
- Keep source files small and focused; no class above 500 lines, no function
  above 100 lines.
- Every behavior change needs tests or golden eval coverage.
- Update `STATUS.md`, `docs/journal/ROUNDS.md`, and `docs/handoffs/current.md`
  after each development round.

## Definition Of Done

The baseline scaffold is done only when:

- local CLI quickstart works;
- deterministic tests pass;
- 20 golden eval questions pass;
- AICO project config loads with lead, architect, implementer, tester, reviewer,
  and challenger roles;
- benchmark evidence files exist under `benchmarks/data-agent/runs/`;
- the next step is ready for a real AICO project-office run.
