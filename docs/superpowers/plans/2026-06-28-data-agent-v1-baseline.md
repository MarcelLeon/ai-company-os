# Data-Agent V1 Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the executable `data-agent-v1` benchmark scaffold so AICO can run a baseline product build with sample data, golden evals, project-office config, and run evidence templates.

**Architecture:** Keep the benchmark product under `projects/data-agent-v1/` as an independent modular Python package. AICO remains the organization plane through `aico-project.json`; the data-agent owns its semantic layer, deterministic query engine, CLI, sample data, and evals. Root tests only verify AICO can load the project config and continuity artifacts.

**Tech Stack:** Python 3.11, standard-library CSV/argparse/json, pytest, mypy, ruff, AICO `ProjectAssignmentConfig`.

---

### Task 1: Project Continuity Scaffold

**Files:**
- Create: `projects/data-agent-v1/AGENTS.md`
- Create: `projects/data-agent-v1/NORTH_STAR.md`
- Create: `projects/data-agent-v1/STATUS.md`
- Create: `projects/data-agent-v1/README.md`
- Create: `projects/data-agent-v1/docs/handoffs/current.md`
- Create: `projects/data-agent-v1/docs/journal/ROUNDS.md`
- Create: `projects/data-agent-v1/docs/journal/PITFALLS.md`
- Create: `projects/data-agent-v1/docs/journal/BLOCKERS.md`
- Create: `projects/data-agent-v1/docs/goals/baseline-v1.md`
- Create: `projects/data-agent-v1/docs/evidence/baseline-v1.md`

- [ ] **Step 1: Create continuity docs**

Write the project entrypoint, north star, current status, goal brief, and evidence template. The docs must state that `data-agent-v1` is a benchmark product built by AICO, not AICO core.

- [ ] **Step 2: Verify docs exist**

Run: `test -f projects/data-agent-v1/AGENTS.md && test -f projects/data-agent-v1/docs/goals/baseline-v1.md`

Expected: exit code 0.

### Task 2: AICO Project Office Config

**Files:**
- Create: `projects/data-agent-v1/aico-project.json`
- Test: `tests/unit/test_data_agent_project.py`

- [ ] **Step 1: Write config test**

Create a test that loads `projects/data-agent-v1/aico-project.json` with `ProjectAssignmentConfig` and asserts roles are `lead`, `architect`, `implementer`, `tester`, `reviewer`, and `challenger`, with no missing required team roles.

- [ ] **Step 2: Write project config**

Map Claude to lead/architect/implementer and Codex to tester/reviewer/challenger. Use workspace `projects/data-agent-v1`.

- [ ] **Step 3: Run config test**

Run: `uv run pytest tests/unit/test_data_agent_project.py -q`

Expected: all tests pass.

### Task 3: Deterministic Data-Agent Package

**Files:**
- Create: `projects/data-agent-v1/pyproject.toml`
- Create: `projects/data-agent-v1/src/data_agent_v1/__init__.py`
- Create: `projects/data-agent-v1/src/data_agent_v1/models.py`
- Create: `projects/data-agent-v1/src/data_agent_v1/semantic_layer.py`
- Create: `projects/data-agent-v1/src/data_agent_v1/loader.py`
- Create: `projects/data-agent-v1/src/data_agent_v1/engine.py`
- Create: `projects/data-agent-v1/src/data_agent_v1/cli.py`
- Test: `projects/data-agent-v1/tests/unit/test_engine.py`

- [ ] **Step 1: Write engine tests**

Cover three concrete business questions and one ambiguous question:

- East China monthly revenue drop.
- Channel ROAS drag.
- Refund-rate product contributors.
- Ambiguous revenue question asks a follow-up.

- [ ] **Step 2: Create sample data**

Create CSVs for orders, customers, ad spend, inventory, and refunds under `sample_data/enterprise_week_one/`.

- [ ] **Step 3: Implement semantic layer and engine**

Use deterministic intent matching and calculations. Every answer must include `answer`, `evidence`, `calculation`, `sql`, `caveats`, and `follow_up_questions`.

- [ ] **Step 4: Run product tests**

Run: `PYTHONPATH=projects/data-agent-v1/src uv run pytest projects/data-agent-v1/tests -q`

Expected: all product tests pass.

### Task 4: Golden Eval Set

**Files:**
- Create: `projects/data-agent-v1/evals/golden_questions.json`
- Create: `projects/data-agent-v1/src/data_agent_v1/eval_runner.py`
- Create: `projects/data-agent-v1/tests/unit/test_golden_eval.py`

- [ ] **Step 1: Add 20 golden questions**

Each case contains `id`, `question`, `expected_intent`, and key expected facts.

- [ ] **Step 2: Implement eval runner**

Run every case through the deterministic engine and compare expected intent and facts.

- [ ] **Step 3: Run eval tests**

Run: `PYTHONPATH=projects/data-agent-v1/src uv run pytest projects/data-agent-v1/tests/unit/test_golden_eval.py -q`

Expected: 20/20 golden cases pass.

### Task 5: Benchmark Evidence Templates

**Files:**
- Create: `benchmarks/data-agent/runs/2026-06-28-v1/goal-brief.md`
- Create: `benchmarks/data-agent/runs/2026-06-28-v1/aico-evidence.md`
- Create: `benchmarks/data-agent/runs/2026-06-28-v1/data-agent-eval.md`
- Create: `benchmarks/data-agent/runs/2026-06-28-v1/human-scorecard.md`
- Create: `benchmarks/data-agent/runs/2026-06-28-v1/screenshots-or-ui-notes.md`

- [ ] **Step 1: Create run evidence directory**

Populate the files with the first baseline prompt, AICO evidence checklist, eval result placeholder to be filled after runtime, and a copy of the scorecard.

- [ ] **Step 2: Verify no incomplete placeholder markers**

Run a case-sensitive search for unfinished marker words across
`projects/data-agent-v1` and `benchmarks/data-agent/runs/2026-06-28-v1`.

Expected: no matches.

### Task 6: Root Integration and Final Gates

**Files:**
- Modify: `pyproject.toml`
- Modify: `STATUS.md`
- Modify: `docs/journal/ROUNDS.md`

- [ ] **Step 1: Add data-agent tests to root pytest paths**

Update root `tool.pytest.ini_options.testpaths` to include `projects/data-agent-v1/tests`.

- [ ] **Step 2: Run targeted gates**

Run:

```bash
PYTHONPATH=projects/data-agent-v1/src uv run pytest projects/data-agent-v1/tests tests/unit/test_data_agent_project.py -q
uv run ruff check projects/data-agent-v1/src projects/data-agent-v1/tests tests/unit/test_data_agent_project.py
uv run mypy --config-file projects/data-agent-v1/pyproject.toml projects/data-agent-v1/src projects/data-agent-v1/tests
git diff --check
```

Expected: all pass.

- [ ] **Step 3: Update status and rounds**

Record that `data-agent-v1` baseline scaffold exists and the next step is to run it through real AICO project office / IM.
