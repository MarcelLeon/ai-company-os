# Pop Culture Memory + Dream Showcase Design

## Goal

Use two familiar pop-culture-inspired scenarios to verify and explain AICO shared memory and `/dream` experience learning:

- A long-lived fantasy party case inspired by *Frieren*: memory must preserve what companions learned across time, and dream must turn repeated task signals into reusable experience.
- A high-stakes castle raid case inspired by *Demon Slayer: Infinity Castle*: team intelligence, approval boundaries, collaboration audit, and post-battle lessons must be traceable.

The public artifacts must highlight AICO's strength without implying official affiliation, using "inspired-by" narrative framing and original role names instead of copied character art or official assets.

## Product Claims To Validate

1. Shared memory is project scoped and injected into role tasks as `Shared memory`.
2. Candidate experiences from `/dream` are not injected until promoted.
3. Promoted experiences appear in role prompts as `Reusable experience (promoted lessons)` and are tracked by `aico.injected_experience_ids`.
4. Collaboration directives create child tasks and `collaboration_requested` audit events.
5. Publicity copy must distinguish product reality from story metaphor.

## Expected Product Self-Inspection

If the showcase exposes product mismatch, fix the smallest underlying product issue instead of hiding it in the case text. Current expected fixes:

- `/dream` should guide the user toward `/experience review` and `/experience promote`, not `/remember`, because its output is candidate experience.
- Shared memory retrieval should inject fact memory only; promoted experience belongs in the dedicated Experience layer.

## Files

- `docs/showcase/frieren-memory-dream-case.md`
- `docs/showcase/infinity-castle-memory-dream-case.md`
- `tests/unit/test_pop_culture_memory_dream_showcase.py`
- `src/aico/core/dream.py`
- `src/aico/core/memory.py`
- `docs/superpowers/plans/2026-07-07-pop-culture-memory-dream-showcase.md`

## Verification

Run:

```bash
uv run pytest tests/unit/test_pop_culture_memory_dream_showcase.py tests/unit/test_orchestrator.py::test_orchestrator_dream_writes_reviewable_candidate_memory tests/unit/test_orchestrator.py::test_orchestrator_promoted_experience_injects_into_role_prompt -q
uv run pytest tests/unit/test_memory.py tests/unit/test_memory_kind.py -q
```

Then run a broader smoke if the targeted tests pass:

```bash
uv run pytest tests/unit/test_pop_culture_memory_dream_showcase.py tests/unit/test_orchestrator.py tests/unit/test_memory.py -q
```
