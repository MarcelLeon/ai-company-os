# Data-Agent AICO Benchmark

> Purpose: validate AI Company OS by using it to build a real enterprise
> data-agent product, then score both AICO's orchestration experience and the
> produced product.

## Why This Benchmark Exists

AICO's north star is not "many agents chat together." It is a boss-absent
operating layer for local AI CLI tools. The most direct product test is:

> Can a human boss use AICO to delegate a complex dynamic product project to a
> local Claude/Codex team, leave the loop, come back through IM handoff, and
> receive a high-quality product that can be judged by a real user?

The benchmark product is an enterprise data-agent because it stresses the
parts where AICO should be strong:

- multi-role planning, implementation, testing, review, and challenge;
- ambiguity handling instead of hallucinated certainty;
- evidence, audit, and repeatable acceptance;
- a useful artifact the human can inspect without reading implementation code.

## Benchmark Loop

Run this loop whenever AICO has a meaningful product-experience improvement:

1. **Baseline**: use the current AICO to build `data-agent-v1`.
2. **Human scoring**: the human scores AICO and `data-agent-v1` with
   `benchmarks/data-agent/scorecard.md`.
3. **AICO improvement**: fix only the highest-impact AICO experience gaps.
4. **Rerun**: use the improved AICO to build `data-agent-v2` under the same
   benchmark contract.
5. **Compare**: score delta decides whether AICO actually improved.

Do not change the scoring criteria after seeing the result of a run. Add new
criteria only for the next named benchmark version.

## Product Contract: Data-Agent

The produced data-agent must be a local product, not a prose-only report.

Minimum deliverables:

- A runnable CLI or lightweight local Web UI.
- Sample enterprise datasets covering orders, revenue, customers, ad spend,
  inventory, refunds, region, channel, and time.
- A semantic layer with metric definitions, dimensions, entities, source
  authority, and ambiguity rules.
- Natural-language business questions that return the SQL or deterministic
  calculation path, answer, caveats, and evidence.
- Ambiguity handling: ask follow-up questions when metric, time, or source
  authority is unclear.
- A 20-question golden evaluation set with expected answers.
- Automated tests for core parsing, semantic mapping, calculations, and evals.
- Human quickstart, product README, known limits, and handoff evidence.

## AICO Contract

A benchmark run must use AICO as the development organization plane.

Required roles:

- `lead`: owns goal framing, slice plan, delegation, final handoff.
- `architect`: owns data-agent system boundary and semantic-layer shape.
- `implementer`: owns code changes for the active slice.
- `tester`: owns deterministic gates and golden evals.
- `reviewer`: owns maintainability, security, and evidence review.
- `challenger`: attacks scope, usefulness, evidence, and toy-product risk.

Required AICO evidence:

- Project office and team view.
- Goal Brief for the data-agent build.
- At least one challenger review before implementation.
- At least one tester/reviewer gate before completion.
- `/overnight` or equivalent boss-absent work order for a bounded slice.
- `/morning`, `/inbox`, `/task`, and `/view` evidence for recovery and trace.

Direct terminal work is allowed for benchmark setup, fixture inspection, and
emergency recovery. The data-agent product implementation should be delegated
through AICO wherever the runtime is available.

## UX Verification Methods

### Machine Gates

Run deterministic checks before asking the human to judge the result:

- data-agent unit tests and golden evals;
- AICO task/audit/state evidence exists for the run;
- no required docs are missing;
- no sensitive data is present in sample fixtures;
- no action claims completion without command output or artifact evidence.

### Agent Computer-Use Checks

Use local UI inspection only for experience that cannot be judged by unit tests:

- Telegram Desktop or another IM client first-screen readability;
- whether `/view` creates and opens a usable HTML snapshot;
- whether handoff messages expose the next action without scrolling through
  raw provider output;
- whether browser-based quickstart or local UI flows are usable.

Computer-use actions must stop before external publication, account creation,
payment, file upload to third parties, or sensitive-data transmission unless
the human explicitly confirms that exact action.

### Human Sample

After machine and agent UI checks, the human scores:

- Can I understand what happened from `/morning` and `/view`?
- Can I operate the produced data-agent without reading code?
- Would I trust this data-agent enough to keep iterating?
- Did AICO ask me only for real decisions, approval, or subjective acceptance?

## Scoring

The score is 100 points:

- 50 points for AICO orchestration experience.
- 50 points for produced data-agent quality.

Use `benchmarks/data-agent/scorecard.md`.

Suggested interpretation:

- **90-100**: strong proof; use as public or investor-facing dogfood evidence.
- **75-89**: useful product loop; optimize the lowest scoring areas.
- **60-74**: promising but not yet a compelling AICO validation.
- **Below 60**: treat as failed benchmark; do not claim product readiness.

For a v2 rerun to count as an AICO improvement, it should either improve the
total score by at least 10 points or fix a previously blocking category while
not regressing total score.

## Anti-Cheating Rules

- Do not hand-edit the final product to hide AICO orchestration failures.
- Do not accept model prose as proof of tests, evals, or product behavior.
- Do not present synthetic or scaled data as real customer data.
- Do not move goalposts after seeing the data-agent result.
- Do not mark a run complete if `/morning` or `/view` leaves the human unable
  to resume or judge the work.

## Benchmark Artifacts

Expected per-run artifacts:

```text
projects/data-agent-v1/
  AGENTS.md
  STATUS.md
  README.md
  docs/
  src/
  tests/

benchmarks/data-agent/runs/<YYYY-MM-DD>-v1/
  goal-brief.md
  aico-evidence.md
  data-agent-eval.md
  human-scorecard.md
  screenshots-or-ui-notes.md
```

`runs/` should store evidence summaries, not large raw logs. Raw audit/state
paths can be referenced by file path when they stay local.

## First Baseline Prompt

Use this as the first human-authored boss request after the project office is
configured:

```text
/goal lead 研发企业级 data-agent v1。验收: 本地可运行; 有语义层; 能回答20个golden业务问题; 回答必须给出SQL或确定性计算依据; 遇到歧义必须追问; 有测试、README、quickstart、handoff和AICO证据。停止: 需要真实外部账号、付费、上传第三方、或无法确定企业语义口径。
```

The next task after this document is to create the baseline project scaffold
and AICO project config, then run `data-agent-v1` through the SOP.
