# AGENTS.md

This is the only correct entry point for an agent working on SME Agent.

Read in order:

1. `NORTH_STAR.md`
2. `STATUS.md`
3. `docs/operating-model/alignment.md`
4. `docs/journal/ROUNDS.md` (latest three rounds)
5. `docs/journal/PITFALLS.md`
6. `docs/journal/BLOCKERS.md`
7. The relevant architecture decision and source files

## Hard rules

- Build a maintainable SME product, not an AICO demo.
- AICO is the development organization plane; SME Agent is the business runtime.
- `projects/` and `benchmarks/` must stay conceptually separate:
  `projects/<name>` is a product workspace; `benchmarks/<name>` is an AICO
  validation scorecard/evidence trail. SME Agent is a commercial product
  workspace, not a benchmark evidence directory.
- One class must stay below 500 lines and one function below 100 lines.
- LLMs, tools, skill storage, memory storage, and metadata storage must sit behind ports.
- Every behavior change needs tests and an evidence bundle.
- Do not mark work done from model prose alone. Record the command or artifact that proves it.
- Update `STATUS.md`, `docs/journal/ROUNDS.md`, and `docs/handoffs/current.md` after every development round.
- Record unresolved uncertainty in `docs/journal/BLOCKERS.md`; do not hide it in prompts or TODOs.

## Definition of aligned

An agent may start implementation only when the active Goal Brief states:

- user outcome;
- in-scope and out-of-scope behavior;
- acceptance checks;
- decision owner;
- evidence required for completion.

If any of these are missing, improve the Goal Brief before changing code.
