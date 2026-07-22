# Restart Task Reconciliation

**Status**: Complete — Round 202

## Goal Brief

**User outcome**: After a crash or service restart, AICO must never tell the absent boss that an
orphaned task is still running. It must preserve safe decisions, expose uncertain execution as an
interruption, and require side-effect verification before any retry.

**Decision owner**: TaskBus startup reconciliation; boss/operator for any retry.

## In scope

- Reconcile persisted `RUNNING` task snapshots when a new TaskBus owns the state database.
- Change each recovered `RUNNING` snapshot to `INTERRUPTED` with a deterministic recovery reason.
- Persist the reconciled snapshot before it can appear in `/status`, `/tasks`, `/inbox`, `/morning`,
  `/view`, metrics, or approval/interrupt commands.
- Record one `TASK_INTERRUPTED` audit event in the new runtime for every reconciled task.
- Preserve original Task record, Adapter name, risk level, metadata, created time, and trace IDs.
- Preserve `WAITING_APPROVAL`: no external execution started, so the new runtime may still approve
  or reject it through the normal policy.
- Preserve terminal `DONE`, `FAILED`, `INTERRUPTED`, and `REJECTED` states unchanged.
- Explain that execution ownership was lost and external side effects must be checked before a new
  task is submitted.

## Out of scope

- Automatically resuming or replaying an Adapter process.
- Assuming a child CLI definitely stopped when the parent process exited.
- Adding `/retry`;retry semantics need idempotency keys and per-operation side-effect contracts.
- Reconstructing partial stdout that was never persisted as a completed TaskOutput.
- Supporting multiple concurrent AICO runtimes against one SQLite state database.

## Acceptance checks

1. SQLite `RUNNING` restored into a new TaskBus becomes persisted `INTERRUPTED` before reads.
2. The reason says runtime restarted, execution ownership was lost, and side effects need review.
3. New runtime audit contains exactly one matching `TASK_INTERRUPTED` event per reconciled task.
4. A third restart does not emit another reconciliation event for the already interrupted task.
5. `WAITING_APPROVAL` remains pending and can still be approved by an authorized reviewer.
6. Terminal tasks remain byte-for-byte equivalent except for normal store round-trip parsing.
7. `/inbox` and `/morning` classify the recovered task as attention/blocked, never running.
8. Full root/SME tests, Ruff, mypy, touched format, structure and diff gates pass.

## Stop conditions

- Stop if startup automatically dispatches, retries, or resumes a recovered task.
- Stop if pending approval is canceled merely because the runtime restarted.
- Stop if reconciliation discards task metadata, risk, project scope, or Adapter identity.
- Stop if an interrupted task can be reconciled repeatedly on each restart.

## Completion evidence

- TaskBus/store/read-model regression gate: `177 passed`.
- Full root: `590 passed, 1 skipped`;SME: `53 passed`.
- Ruff, mypy, touched format, class/method structure and `git diff --check` pass.
- Temporary real SQLite + JSONL dogfood: first owner restored `running → interrupted`,second owner remained
  `interrupted`,and persisted audit count remained exactly one `task_interrupted`.
- Full-root format has one pre-existing unrelated finding in
  `projects/data-agent-v1/src/data_agent_v1/engine.py`;Round 202 did not touch it.
