# Current Handoff

## Goal

Create the `data-agent-v1` benchmark scaffold so AICO can run a real baseline
project-office dogfood.

## Done

- Project continuity documents exist.
- AICO project config exists.
- Local sample data exists.
- Deterministic engine and CLI exist.
- Golden eval set exists.
- Tests exist.
- Benchmark run evidence templates exist.
- Targeted gates pass: 7 tests, ruff, mypy.
- Full root pytest passes: 478 passed, 1 skipped.
- `sample_data/enterprise_week_one/README.md` now explains the underlying data
  model and why the canonical seed question is answerable.
- `benchmarks/data-agent/runs/2026-06-28-v1/scoring-brief.md` exists and maps
  scorecard categories to evidence.
- `benchmarks/data-agent/runs/2026-06-28-v1/data-agent-eval.md` includes the
  three SOP manual question outputs plus golden eval 20/20.
- Dedicated AICO runtime was started with isolated `.aico/data-agent-v1-*`
  state paths.
- Telegram Desktop read check found the logged-in `ai_co` chat in
  `/Applications/Telegram.app`; `/Applications/Telegram 2.app` is not logged in.
- Independent critic draft exists and scores current evidence harshly:
  AICO 4/50, Data-Agent 38/50.
- Local injected IM baseline transcript exists and exercises the command chain
  through AICO Orchestrator, but uses fake adapters and RecordingChannel.
- Local `/view` snapshot exists under the run directory.
- Scoring/operator docs have been localized to Chinese.
- `ai-precheck-and-score.md` contains the agent-completed objective checks,
  UX/aesthetic judgment, and suggested score.
- `human-remaining-actions.md` reduces human work to the remaining subjective
  decisions and final scorecard fill.

## Not Done

- Real AICO IM commands have not yet been sent because third-party Telegram
  sending could not be automated by current local UI tools.
- Real `/morning`, `/inbox`, `/task`, and `/view` evidence has not yet been
  captured.
- Human has not yet filled the scorecard.
- `data-agent-v2` comparison has not started.

## First Action Next Round

Ask the human to open `benchmarks/data-agent/runs/2026-06-28-v1/human-remaining-actions.md`
and decide whether to score AICO strictly (`4/50`) or with local command-contract
credit (`8/50`). Then fill `human-scorecard.md`. Do not call the local injected
transcript a real Telegram baseline.

## Round 7 verification snapshot (2026-07-06)

goal-bbecd160 acceptance re-checked against live commands on the current worktree:

- `pytest projects/data-agent-v1/tests tests/unit/test_data_agent_project.py -q` — 7 passed.
- `python -m data_agent_v1.eval_runner` — `golden_eval: 20/20 passed`.
- `ruff check` + `mypy --config-file projects/data-agent-v1/pyproject.toml` — both green.
- CLI ambiguity probe with `收入怎么样？` and `帮我看看数据` — both return
  `intent=needs_clarification` with time / scope / metric follow-up questions.
- Semantic layer file `src/data_agent_v1/semantic_layer.py` defines the four
  metrics used by every non-clarification `QueryResponse`, satisfying the
  "有语义层" bar.

Lead call this round: the build-lead side of goal-bbecd160 is done; the only
remaining acceptance evidence sits with the human scorecard, which is a boss
action, not a build-lead action. Not escalating; no product change proposed.

## Round 7 slice decision (2026-07-06)

See `docs/decisions/2026-07-06-round7-slice-plan.md` for the full memo.

Lead recommendation: **freeze data-agent-v1, do not start `data-agent-v2` until
AICO produces at least one real Telegram baseline transcript**. Boss must pick
one of:

- **B1** — strict scorecard (AICO 4/50 or credited 8/50), close v1 here.
- **B2** — boss personally runs the Telegram command sequence in
  `aico-evidence.md` §"真实 Telegram 要发送的命令" (10-15 min), then scores.
- **B3** — open a separate AICO orchestration goal to fix real-Telegram send,
  `/view` state injection, and `/morning` first-screen quality; rerun benchmark.

Slice R7-01 (this handoff itself) is docs+audit only:

- `docs/decisions/2026-07-06-round7-slice-plan.md` written.
- STATUS / ROUNDS updated to reference the memo.
- Roles active this round: lead + challenger (on-file draft) + reviewer
  (on-file scoring brief). Tester / implementer / architect deliberately idle
  because no product change is proposed.

Next action is boss-side, not lead-side. Once boss picks B1 / B2 / B3, the
appointment will either close (B1) or reopen with a different seat / goal
(B2 / B3).
