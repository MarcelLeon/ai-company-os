# STATUS.md

**Last updated**: 2026-07-06
**Current round**: Round 7
**Current phase**: Baseline acceptance re-verified for goal-bbecd160

## Current Truth

- Project continuity docs exist.
- AICO project config lives at `aico-project.json`.
- Deterministic data-agent source lives under `src/data_agent_v1`.
- Sample enterprise data lives under `sample_data/enterprise_week_one`.
- Golden evals live under `evals/golden_questions.json`.
- This project is a benchmark target, not AICO core.

## Round 7 acceptance re-verification (2026-07-06)

Each acceptance criterion from goal-bbecd160 now has a live evidence cell:

| # | Acceptance | Evidence (this round) |
|---|---|---|
| 1 | 本地可运行 | `README.md` quickstart, CLI on canonical seed question prints intent / answer / evidence / SQL / follow-ups. |
| 2 | 有语义层 | `src/data_agent_v1/semantic_layer.py` defines METRICS (paid_revenue / refund_rate / roas / inventory_months), DIMENSIONS, SOURCE_AUTHORITY; each metric carries an `ambiguity_rule` used by the engine. |
| 3 | 20 golden 业务问题 | `evals/golden_questions.json` holds 20 cases; `data_agent_v1.eval_runner` prints `golden_eval: 20/20 passed`. |
| 4 | SQL / 确定性计算依据 | All 10 answer intents in `src/data_agent_v1/engine.py` return a `QueryResponse` with `sql`, `calculation`, `evidence`; the clarification branch explicitly refuses SQL until scope is confirmed, instead of hallucinating one. |
| 5 | 歧义必须追问 | Two adversarial CLI runs (`收入怎么样？`, `帮我看看数据`) return `intent=needs_clarification` with three follow-up questions covering time / scope / metric. `test_ambiguous_revenue_question_asks_follow_up` locks this in as regression. |
| 6 | 测试 / README / quickstart / handoff / AICO 证据 | Targeted `pytest projects/data-agent-v1/tests tests/unit/test_data_agent_project.py -q` → 7 passed. README quickstart is executable. `docs/handoffs/current.md` + `benchmarks/data-agent/runs/2026-06-28-v1/` evidence tree exist. |

Machine gate this round (all green):

```text
pytest projects/data-agent-v1/tests tests/unit/test_data_agent_project.py -q   → 7 passed
python -m data_agent_v1.eval_runner                                            → golden_eval: 20/20 passed
ruff check ...                                                                 → All checks passed!
mypy --config-file projects/data-agent-v1/pyproject.toml ...                   → Success: no issues found in 10 source files
CLI ambiguity probe (2 cases)                                                  → needs_clarification, 3 follow-up questions each
```

## Done

- Defined product boundary and north star.
- Added baseline goal brief.
- Added handoff, journal, pitfalls, blockers, and evidence template.
- Added deterministic semantic-layer product skeleton and tests.
- Local targeted gates pass this round: 7 tests, ruff, mypy, golden eval 20/20.
- Full root pytest last verified 478 passed / 1 skipped on 2026-06-28.
- Sample data model README explains business process, ER view, table grain, join keys, metric definitions, and canonical seed question.
- Benchmark run evidence includes manual CLI outputs for the three SOP business questions, golden eval 20/20, targeted tests 7/7, scoring brief, and Telegram / Computer Use readiness notes.
- Independent critic draft: `benchmarks/data-agent/runs/2026-06-28-v1/ai-critic-scorecard-draft.md`.
- Local injected IM baseline: `benchmarks/data-agent/runs/2026-06-28-v1/local-im-baseline-transcript.md`.
- Local `/view` snapshot: `benchmarks/data-agent/runs/2026-06-28-v1/local-view-snapshots/aico-view-data-agent-v1.html`.
- Scoring / operator docs default to Chinese.
- AI precheck / suggested score: `benchmarks/data-agent/runs/2026-06-28-v1/ai-precheck-and-score.md`.
- Human remaining actions: `benchmarks/data-agent/runs/2026-06-28-v1/human-remaining-actions.md`.

## Lead decision this round

- **Decision**: goal-bbecd160 has full-coverage acceptance evidence at the product-and-tests layer, and is done from a build-lead perspective. The remaining un-done piece is the human scorecard for AICO orchestration UX, which is a boss-reserved action and I do not fill.
- **Why**: All 6 acceptance items map to live commands or files with green results. The stop conditions have not been touched: no external accounts, no payments, no third-party uploads, no undefined semantic dispute.
- **Rejected alternatives**:
  - Retrying real-Telegram send via Computer Use: rejected. Rounds 4–5 showed the local UI tooling cannot drive Telegram reliably, and the injected baseline already exercises the same AICO command chain deterministically.
  - Starting `data-agent-v2`: rejected. Bench discipline says do not iterate before the human scorecard captures where AICO orchestration UX is weak.
  - Widening product scope (more metrics, more channels): rejected. The 20-question golden set is stable acceptance; changing it after seeing quality would violate the benchmark rule.
- **Consulted roles**: relied on the on-file critic draft (AICO 4/50, Data-Agent 38/50) as the conservative reviewer voice; no live challenger delegation this round because no product code changed.
- **Risks**: The AICO half of the scorecard remains gated on a real-Telegram transcript that we cannot self-produce; local-injected baseline is command-contract evidence, not boss-experience evidence.
- **Approval need**: none for this round; boss action is only "fill the scorecard" or "waive the Telegram blocker".

## Lead slice decision this round

See `docs/decisions/2026-07-06-round7-slice-plan.md` for the full memo.
Recommendation: **freeze data-agent-v1, do not start v2 until AICO produces at
least one real Telegram baseline transcript**. Slice R7-01 (this handoff) is
docs+audit only. Three boss options are on the table:

- **B1** — Fill `human-scorecard.md` strictly (AICO 4/50) or with local credit
  (AICO 8/50) and stop here.
- **B2** — Boss personally runs the Telegram command sequence in
  `aico-evidence.md` §"真实 Telegram 要发送的命令" (10-15 min), then fills the
  scorecard. Unlocks real AICO score.
- **B3** — Open a separate AICO orchestration goal to fix Telegram automation,
  `/view` state injection, and `/morning` handoff quality; rerun the benchmark
  after fix.

## Next

1. Boss picks B1 / B2 / B3 from the decision memo.
2. Boss reads `benchmarks/data-agent/runs/2026-06-28-v1/human-remaining-actions.md`.
3. Boss fills `benchmarks/data-agent/runs/2026-06-28-v1/human-scorecard.md`.
4. Do not start `data-agent-v2` until the scorecard is filled AND the AICO
   score bottleneck is either accepted (B1) or repaired (B3).
