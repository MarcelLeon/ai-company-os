# Round 7 Lead Decision — Slice Plan After Challenger Review

**Date**: 2026-07-06
**Author**: claude @ data-agent-v1-lead
**Trigger**: Boss `/ask lead` — "综合 challenger 意见，给出最终切片计划、角色分工、验收证据和第一步任务。"
**Scope**: `projects/data-agent-v1` only. Permissions: `docs`, `audit`.
**Status**: Proposed, awaiting boss approval on choice **A vs B**.

---

## 1. Decision

**Recommend Option B — Freeze `data-agent-v1`. Do NOT start `data-agent-v2` until
AICO orchestration produces at least one real Telegram baseline transcript.**

The single next slice inside this project is **Slice R7-01: Boss handoff**:
persist Round 7 evidence, produce the scoring bundle, and close the loop with a
filled `human-scorecard.md`. That slice is 100% docs / audit, zero code.

Everything else in this decision is options given for boss to pick, not
commitments I take without approval.

---

## 2. Why

Consulted evidence:

- `ai-critic-scorecard-draft.md` — strict verdict: AICO 4/50, Data-Agent 38/50.
  Explicit warning: "产品先做出来,AICO 编排后补证据" is the biggest benchmark risk.
- `ai-precheck-and-score.md` — even the friendly precheck refuses to go above
  8/50 for AICO without a real Telegram transcript.
- `scoring-brief.md` — makes "local injected baseline is not real IM evidence"
  a scoring rule, not a suggestion.
- `human-remaining-actions.md` — pre-committed the rule: if AICO < 30/50, do
  not launch `data-agent-v2`.

Six data-agent-v1 acceptance criteria are all green (see `STATUS.md` Round 7
matrix). The gap that keeps this benchmark from being a meaningful AICO proof
is not on the product side, it is on the orchestration side. Continuing to
extend the product before AICO can actually orchestrate it would:

- widen the "product-first, orchestration-later" post-hoc-proof risk the
  challenger called out;
- invalidate v1↔v2 comparisons because we would have moved the acceptance
  criteria after seeing product quality, which the appointment contract
  explicitly forbids.

---

## 3. Rejected alternatives

### A. Start `data-agent-v2` immediately

Rejected. Reasons:

- Challenger score line (`human-remaining-actions.md` §"后续流程") says do NOT
  start v2 while AICO score is below 30/50, and the pre-check ceiling is 8/50.
- The 20-question golden set is the stable acceptance anchor; expanding metrics
  or channels now would silently move that anchor.
- Product quality gains would not shift the benchmark's real weak spot.

### C. Have this lead seat try to fix AICO core (Telegram automation, `/view` state injection)

Rejected. Reasons:

- Appointment contract limits this seat to `docs` + `audit` inside
  `projects/data-agent-v1`. AICO core changes must live in the AICO project,
  under a different appointment and approval chain.
- Rounds 4–5 already exhausted the local UI automation angle; the fix belongs
  in AICO's channel / snapshot code, not in this benchmark's workspace.
- Trying to fix AICO from inside the benchmark would create exactly the
  circular proof the challenger warned about.

### D. Retry Telegram send via Computer Use / AppleScript one more time

Rejected. Rounds 4–5 established that this path is not reliable enough to be
worth another loop. The right escalation is to hand this to AICO core, not
retry a proven-broken path.

---

## 4. Options for the boss (pick one)

### Option B1 — Minimum path: fill scorecard, stop here

- Boss fills `human-scorecard.md` using either strict (AICO 4/50) or credited
  (AICO 8/50) score, referencing `ai-precheck-and-score.md`.
- Data-Agent V1 is archived as a passing benchmark scaffold.
- Next real work moves to AICO orchestration project (out of this appointment).

### Option B2 — Human-in-the-loop real Telegram baseline

- Boss personally runs the command sequence in `aico-evidence.md` §"真实
  Telegram 要发送的命令" from Telegram on any device.
- Boss pastes IM output back into `aico-evidence.md` §"人类粘贴真实 IM 证据".
- Then fills `human-scorecard.md`.
- Estimated boss time: 10-15 minutes of live IM interaction with `ai_co` bot.
- This unlocks AICO score above 8/50 legitimately.

### Option B3 — Escalate to a new AICO orchestration task

- Boss opens a new goal against AICO core (not this project) to fix:
  - Telegram real-send automation (or accept manual paste as the baseline flow).
  - `/view` snapshot state injection so the file is not empty.
  - `/morning` first-screen quality on data-agent-v1 fixtures.
- After AICO fix, re-run this exact same benchmark command sequence to get a
  real transcript; then fill `human-scorecard.md`.

I recommend **B2 for this scoring round** (cheapest boss time, unlocks real
score today) followed by **B3 as its own project** (structural fix so
future benchmarks don't repeat this bottleneck).

---

## 5. Slice R7-01 — the only slice I take this round

Only Slice R7-01 is committed under this appointment. Everything else waits on
the boss's choice above.

### 5.1 Scope

Docs + audit inside `projects/data-agent-v1` and its evidence run folder.
No code, no test change, no acceptance-criteria movement.

### 5.2 Roles for R7-01

| Role | Seat | Duty | Deliverable |
|---|---|---|---|
| lead (me) | data-agent-v1-lead | This decision doc; STATUS / ROUNDS / handoff sync; boss handoff line. | This file + cross-links. |
| challenger | data-agent-v1-challenger | Sign off that the slice plan does not sneak in acceptance-criteria movement. | Short verdict in handoff. |
| reviewer | data-agent-v1-reviewer | Sign off that Round 7 evidence in STATUS is verifiable and doc-only. | Short verdict in handoff. |
| tester | (idle) | Not activated. No product change to test. |  |
| implementer | (idle) | Not activated. No product change. |  |
| architect | (idle) | Not activated. No semantic layer change. |  |

Deliberate: 3 roles active, 3 idle. Multi-agent theatre without cause would
degrade the very "多 agent 分工真实,不是装饰" score the challenger flagged.

### 5.3 Acceptance evidence for R7-01

The slice is done when all of the below are true:

- `docs/decisions/2026-07-06-round7-slice-plan.md` exists (this file).
- `STATUS.md` Round 7 section references this decision and lists the boss
  options B1 / B2 / B3.
- `docs/journal/ROUNDS.md` Round 7 entry references this decision.
- `docs/handoffs/current.md` "First Action Next Round" points to boss picking
  B1 / B2 / B3.
- Challenger and reviewer verdicts are recorded (verbally in this doc if the
  boss does not want to spawn subagents).
- No file under `src/`, `tests/`, `evals/`, `sample_data/` has been touched.

### 5.4 First-step task

The first-step task on the lead side is **already executed in this Round 7
handoff**: this decision doc is written, and STATUS / ROUNDS / handoff have
been updated in Round 7 (see previous message in this thread).

The first-step task on the boss side is:

> Read this decision, pick one of B1 / B2 / B3, and either fill
> `human-scorecard.md` (B1) or run the Telegram command sequence in
> `aico-evidence.md` (B2) or open a separate AICO orchestration goal (B3).

---

## 6. Consulted roles

- **Challenger draft** (`ai-critic-scorecard-draft.md`) — read and adopted its
  strict verdict as the anchor of this decision.
- **AI precheck** (`ai-precheck-and-score.md`) — used as the ceiling on
  optimistic AICO scoring.
- **Reviewer body of work** — the scoring-brief and pitfalls doc are treated
  as reviewer voice on this project since no live reviewer agent was spawned
  this round; not spawning one is intentional to avoid decorative fan-out.
- **No live challenger subagent** was spawned this round. Reason: the on-file
  challenger draft is only 4 days old and its conclusions have not been
  invalidated by any product change since. Spawning a fresh challenger now
  would burn tokens without adding signal.

If the boss wants a live challenger pass on this specific decision, that is a
1-minute `/ask challenger` follow-up; call it and I will reopen the slice.

---

## 7. Risks

- **R1**: Boss picks B1 (strict scorecard, stop here). The benchmark closes
  with AICO 4/50 or 8/50 recorded as the v1 baseline. This is honest but
  publicly weak; future observers may confuse this with the product being bad.
  Mitigation: write plain-English caveat into the scorecard notes that says
  "AICO score is bottlenecked by IM-automation gap, not by product quality".
- **R2**: Boss picks B2 (manual Telegram run) but the runtime is not currently
  configured with a valid `AICO_TELEGRAM_BOT_TOKEN`. Mitigation: pre-check the
  environment (out of this appointment) before boss starts typing.
- **R3**: Boss picks B3 (escalate to AICO orchestration goal) and I get pulled
  into scope-creep to help fix AICO core. Mitigation: this appointment stays
  in `docs` / `audit`; AICO core work must go under a different seat.

---

## 8. Approval need

- No irreversible action requested.
- No credential, payment, publication, or destructive action.
- Boss approval requested only for **choosing B1 / B2 / B3**; not for
  executing R7-01 itself, which is docs-only and already inside my
  appointment's permission set.

---

## 9. Candidate v2 directions (parked, do not implement without approval)

Only listed so the boss knows the design space I would want to explore
**after** the AICO orchestration side is unblocked. None of these change v1
acceptance criteria.

- **Semantic layer generalization**: replace hardcoded intent branches in
  `engine.py` with a metric+dimension resolver so new questions do not need
  new Python functions.
- **Multi-turn clarification**: today `needs_clarification` is one-shot; v2
  could carry `pending_slots` across turns so `/ask` becomes an actual dialog.
- **Time-window & attribution axes**: paid_revenue currently only supports
  month × region × channel; v2 could add week / day / YoY / QoQ, and ROAS
  attribution windows.
- **Boundary axes challenger flagged**: RLS-like scoping, PII redaction,
  source-authority audit trail. These would raise the "安全和隐私" line item
  (currently 2/3).
- **Fixture scale**: today's sample is deliberately tiny; v2 could add a
  10×–100× fixture to relax the "benchmark 味浓" scoring critique — but ONLY
  if the golden set stays fixed on the small fixture so scores stay
  comparable.
- **Web UI seed**: a minimum FastAPI/HTMX view of the CLI response so the
  boss can query from a phone; keeps `/view`-style handoff optional.

Every one of these is a new goal, not a hidden extension of this round.
