# Lead Standing Charter Proposal Queue

**Status**: Complete — Round 199

## Goal Brief

**User outcome**: when the boss is absent and the active project has no work in progress, the
appointed lead can surface one bounded, evidence-defined next-work proposal from the project's
standing charter. The proposal is visible in `/inbox` and `/morning`, survives restart, and cannot
start work until the boss explicitly accepts it.

**Decision owner**: boss for accept/reject; project lead for the proposal execution after accept.

## In scope

- Project configuration may declare ordered standing-charter items with an objective, role,
  acceptance evidence, stop conditions, and proposal cooldown.
- `/inbox`, manual `/morning`, and scheduled morning push refresh at most one candidate when the
  project is idle and its required lead/challenger team is complete.
- Candidate, accepted, and rejected proposals persist through the configured AICO state store.
- `/proposals` lists the active project's proposal queue.
- `/proposal accept <id>` starts the proposal through the normal project role, risk, approval,
  audit, task-state, memory, and interrupt path.
- `/proposal reject <id> [reason]` records the decision without creating a task.
- Inbox/morning prioritize existing approvals, failures, running work, and handoffs before a
  standing-charter proposal.

## Out of scope

- Automatically accepting or executing proposals.
- Bypassing `/approve` for risky accepted tasks.
- LLM-generated charter objectives, arbitrary background cron workers, or multiple simultaneous
  self-started plans.
- Reading `STATUS.md` or `BLOCKERS.md` heuristically to invent work.
- Treating a proposal as legal, financial, publication, customer-data, or spending authorization.
- Solving Telegram credentials, browser policy, or process supervision in this slice.

## Acceptance checks

1. A configured idle project with a complete team gets at most one candidate; an active project,
   incomplete team, unconfigured project, or proposal still in cooldown gets none.
2. Candidate data is project-scoped, immutable at the model boundary, restart-safe under SQLite,
   included in state summary/reset, and never contains channel credentials.
3. `/inbox` and `/morning` show objective plus exact accept/reject commands without outranking
   approvals, failed/running work, or overnight handoffs.
4. Accept resolves only a unique candidate in the active project, records the task id, and routes
   through the configured project role and normal TaskBus controls.
5. Reject records optional reason, creates no task, and does not immediately regenerate the same
   charter item before cooldown.
6. Parser, domain/store, inbox/morning, orchestrator, restart, and state reset contracts pass.
7. Full pytest, Ruff, mypy, format, structure, diff, and continuity gates pass.

## Evidence required

- Red-green tests for generation, persistence, command parsing, accept/reject, priority, and
  scheduled/manual recovery surfaces.
- A machine dogfood using the real `projects/sme-agent/aico-project.json` configuration and an
  isolated temporary SQLite database.
- Explicit record that real Telegram delivery remains pending when runtime credentials or browser
  policy prevent it.

## Stop conditions

- Stop if a proposal runs before explicit boss acceptance.
- Stop if rejecting or merely viewing a proposal creates a task.
- Stop if project scope, team readiness, cooldown, risk assessment, approval, or interrupt paths
  can be bypassed.
- Stop if this feature requires parsing free-form project documents in core orchestration.
