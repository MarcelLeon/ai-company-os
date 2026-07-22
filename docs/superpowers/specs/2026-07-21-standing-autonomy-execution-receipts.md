# Standing Autonomy Execution Receipts

**Status**: Implemented and locally verified — Round 215

## Goal Brief

**User outcome**: When the owner returns after an unattended standing-charter run, `/inbox` and
`/morning` show a compact, restart-safe receipt that identifies the proposal/task relationship and
whether execution completed, is still running, failed, timed out/interrupted, was rejected, or was
accepted but has no task evidence.

**Decision owner**: The receipt is a read projection over existing durable proposal and task truth.
It must not introduce a second outcome table, infer success from provider text, refund/retry a grant,
or mutate execution state while rendering.

## In scope

- Derive receipts only for `decision_mode=preauthorized` standing proposals.
- Join by the persisted `proposal.task_id` to TaskBus snapshots; retain proposal/charter/grant
  linkage and terminal timestamps without copying payload or provider output.
- Surface an explicit `evidence_missing` receipt when a preauthorized accepted proposal has no task
  ID or matching snapshot. This covers the intentional at-most-once crash window between budget
  consumption and TaskBus submission.
- Show recent receipts in interactive and scheduled morning handoffs and the boss inbox.
- Failed/interrupted/rejected/missing receipts become a higher-priority recovery action; running
  receipts become monitor actions; done receipts remain evidence but do not create false attention.
- Display only short proposal/task/authorization references, status, charter, and bounded terminal
  elapsed time. Never display owner ID, target ID, payload, provider output, grant path, or raw error.
- Rebuild identical receipts after SQLite restart from existing `standing_proposals` and task state.
- Run preauthorized standing work through the ordinary TaskBus stream plus its own timeout; do not
  apply `/overnight` handoff grading to a different execution intent.

## Out of scope

- Persisting a new receipt/outcome table or altering state schema.
- LLM grading, semantic acceptance of provider output, automatic retry/refund, or cost/token claims.
- Replacing `/task`, audit, provider output, or the real scheduled provider/IM sample required by
  B-014.
- Showing manual proposal decisions as autonomous receipts.

## Acceptance checks

1. Completed, running, failed, interrupted, rejected, and missing-evidence states project
   deterministically from proposal/task truth.
2. Terminal elapsed seconds are non-negative and derived from proposal decision to final snapshot;
   running/missing receipts do not claim a completed duration.
3. Manual decisions and unrelated task snapshots never appear as autonomous receipts.
4. SQLite restart reconstructs the same completed receipt without a receipt table or state mutation.
5. `/inbox` prioritizes failed/interrupted/rejected/missing over running, shows done receipts without
   claiming pending work, and supplies `/task` only when a task ID exists.
6. `/morning` shows recent autonomous receipts after generic Done/Blocked sections; a second morning
   tick after a successful scheduled run shows one done receipt and does not re-execute the grant.
7. Receipt text contains no full authorization/owner/target identity, payload, provider output,
   reason, path, secret, or raw exception.
8. Targeted/full tests, SME tests, Ruff, mypy, touched format, AICO structure, JSON, Compose, and
   `git diff --check` pass.
9. A normal read-only standing output reaches `DONE`; the overnight handoff grader cannot rewrite it
   to `FAILED`.

## Stop conditions

- Stop if receipt rendering writes state, consumes budget, or triggers proposal refresh/execution.
- Stop if a second persisted outcome can disagree with the authoritative task snapshot.
- Stop if `DONE` is inferred from natural-language output rather than TaskBus terminal state.
- Stop if accepted-without-task is hidden or automatically retried.
- Stop if a receipt is described as provider/IM E2E evidence rather than local durable projection.
