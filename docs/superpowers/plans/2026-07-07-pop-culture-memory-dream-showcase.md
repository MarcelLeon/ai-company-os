# Pop Culture Memory Dream Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two vivid, machine-verifiable showcase cases for AICO shared memory and `/dream` experience learning.

**Architecture:** Keep showcase material as docs and deterministic unit tests. Fix only the smallest product gaps revealed by the cases: `/dream` next-action copy and fact-vs-experience prompt separation.

**Tech Stack:** Python 3.11, pytest, existing AICO Orchestrator/TaskBus/JsonlMemoryStore test doubles.

## Global Constraints

- Do not use official anime images, logos, or copied dialogue in public artifacts.
- Use "inspired-by" wording and original role/task names.
- Keep code changes inside existing core boundaries and tests.
- Follow TDD: write failing tests before production changes.

---

### Task 1: Product Boundary Red Tests

**Files:**
- Modify: `tests/unit/test_memory.py`
- Modify: `tests/unit/test_orchestrator.py`

**Interfaces:**
- Consumes: `MemoryAtom.kind`, `MemoryGovernor.project`, `dream_review_message`
- Produces: failing expectations for fact-only shared memory and `/dream` experience next actions

- [ ] Add a test proving active `kind=experience` atoms are excluded from the `Shared memory` packet.
- [ ] Add a test proving `/dream` suggests `/experience review` and `/experience promote`, not `/remember`.
- [ ] Run the new focused tests and confirm they fail.

### Task 2: Minimal Product Fix

**Files:**
- Modify: `src/aico/core/memory.py`
- Modify: `src/aico/core/dream.py`

**Interfaces:**
- Consumes: red tests from Task 1
- Produces: fact-only memory packet and correct dream next-action guidance

- [ ] Update `MemoryGovernor.allows()` to return `False` for non-fact atoms.
- [ ] Update `dream_review_message()` next actions to route candidate experience through `/experience review` and `/experience promote <id> as <role>`.
- [ ] Run Task 1 focused tests and confirm green.

### Task 3: Showcase E2E Cases

**Files:**
- Create: `tests/unit/test_pop_culture_memory_dream_showcase.py`

**Interfaces:**
- Consumes: `Orchestrator`, `TaskBus`, `JsonlMemoryStore`, collaboration directives, dream/promote commands
- Produces: two deterministic E2E tests, one fantasy-party memory case and one castle-raid audit/dream case

- [ ] Add test helpers for a recording channel and scripted adapters.
- [ ] Add the fantasy-party case: project fact memory is injected; a blocked task feeds `/dream`; promoted experience injects into the next role task.
- [ ] Add the castle-raid case: source role asks reviewer via `@reviewer`; audit records collaboration; dream turns blocked approval into candidate experience; promoted experience injects into implementer.
- [ ] Run the new test file and confirm green.

### Task 4: Publicity-Ready Docs

**Files:**
- Create: `docs/showcase/frieren-memory-dream-case.md`
- Create: `docs/showcase/infinity-castle-memory-dream-case.md`

**Interfaces:**
- Consumes: verified behavior from Task 3
- Produces: case design, objective-reality review, verification script, and promotional angle

- [ ] Write the fantasy-party showcase doc with commands, expected visible effects, product claim, objective limits, and publicity copy.
- [ ] Write the castle-raid showcase doc with commands, expected visible effects, product claim, objective limits, and publicity copy.
- [ ] Keep each doc explicit that it is inspired-by and uses no official assets.

### Task 5: Verification And Journal Update

**Files:**
- Modify: `STATUS.md`
- Modify: `docs/journal/ROUNDS.md`
- Modify if needed: `docs/journal/PITFALLS.md`

**Interfaces:**
- Consumes: all changed code/docs
- Produces: fresh verification evidence and handoff notes

- [ ] Run targeted tests.
- [ ] Run relevant broader tests.
- [ ] Update `STATUS.md` with this round and next recommended validation.
- [ ] Append `ROUNDS.md` with decision notes, rejected alternatives, verification, and next steps.
