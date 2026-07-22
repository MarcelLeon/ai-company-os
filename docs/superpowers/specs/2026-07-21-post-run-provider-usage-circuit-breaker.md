# Post-run Provider Usage Circuit Breaker

**Status**: Implemented and locally verified — Round 216

## Goal Brief

**User outcome**: unattended standing work leaves provider-grounded token evidence, and a grant
stops authorizing later runs once observed cumulative usage reaches its owner-set threshold or any
consumed run lacks usage evidence.

**Truth boundary**: Codex emits usage only with terminal `turn.completed`. This feature is a
post-run cumulative circuit breaker, not a hard cap on the currently running provider turn.

## In scope

- Use Codex `--json` for fixed preauthorized execution and extract only completed agent messages.
- Capture non-negative input/output/cached/cache-write/reasoning usage from `turn.completed`.
- Write a structured TaskBus usage audit before task completion audit.
- Persist usage on the accepted standing proposal and rebuild it after SQLite restart.
- Require `token_stop_threshold` in every standing grant.
- Before dispatch, sum prior usage for the exact grant and stop when threshold is reached.
- Fail closed when any consumed preauthorized run under the grant lacks usage evidence.
- Show total tokens in `/inbox` and `/morning` terminal receipts without provider output or identity.

## Out of scope

- Interrupting a turn at an exact token count or guaranteeing that one run cannot overshoot.
- Estimating dollar cost without provider model, billing tier, auth mode, and pricing evidence.
- Reading private non-ephemeral Codex rollout files or persisting raw JSONL.
- Automatically retrying/refunding a run with missing usage.
- A paid provider, scheduler, or remote IM acceptance sample.

## Acceptance checks

1. JSONL thread/tool/status events are suppressed; completed agent text reaches the existing stream.
2. `turn.completed` produces one `TaskUsage` with total=input+output and optional fields defaulting to zero.
3. Invalid/missing usage does not create an audit receipt and blocks later grant consumption.
4. TaskBus records usage before completion and existing metrics consume the same detail.
5. Completed proposal usage survives SQLite restart and appears as bounded `tokens=N` in boss views.
6. Prior observed usage at threshold blocks a new task; prior missing usage blocks it independently of run count.
7. Grant files without `token_stop_threshold` fail strict validation and doctor preflight.
8. Existing read-only/no-network/no-resume/no-collaboration and wall-clock boundaries remain unchanged.
9. Full tests, SME tests, Ruff, mypy, structure, JSON, Compose, and diff gates pass.

## Stop conditions

- Stop if implementation claims a per-turn hard cap from terminal-only usage.
- Stop if missing/invalid usage is treated as zero or permits another unattended run.
- Stop if raw JSONL, thread ID, tool payload, owner identity, or provider output is persisted in usage truth.
- Stop if cost is inferred from a mutable public price table rather than provider billing evidence.
