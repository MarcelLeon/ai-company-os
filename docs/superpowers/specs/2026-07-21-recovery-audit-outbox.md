# Recovery Audit Transactional Outbox

**Status**: Complete — Round 203

## Goal Brief

**User outcome**: A crash can never leave the absent boss with reconciled task state but missing or
duplicated recovery evidence. Restart recovery must converge without replaying the task itself.

**Decision owner**: SQLite task-state store owns reconciliation intent;AuditLog owns delivery.

## Failure window

Round 202 writes `RUNNING → INTERRUPTED` to SQLite and then appends `TASK_INTERRUPTED` to audit
JSONL. A crash or sink failure between those writes leaves SQLite interrupted,so later startups no
longer know that the recovery audit still needs delivery. Reversing the order only changes the
failure into duplicate audits or a stale running snapshot.

## In scope

- In one SQLite transaction,write every recovered `INTERRUPTED` snapshot and a complete immutable
  `AuditEvent` outbox payload with a stable event id.
- Load pending recovery events even when no snapshot remains `RUNNING`.
- Deliver the exact persisted event through `InMemoryAuditLog` and configured sinks before marking
  the outbox row delivered.
- Make `InMemoryAuditLog` and `JsonlAuditSink` idempotent by event id;an id collision with different
  content must fail loudly in memory.
- Retry an undelivered event after sink failure or process restart without redispatching the Task.
- Keep SQLite business state and JSONL audit as their existing truth sources;the outbox is only a
  delivery coordinator.
- Advance shared SQLite schema metadata and state inspection/reset coverage.

## Out of scope

- A unified audit/task database or replacing JSONL audit.
- Multi-runtime writers,distributed transactions,Postgres,or a background message broker.
- Automatically retrying the interrupted Adapter task.
- Making arbitrary third-party `AuditSink` implementations idempotent;the built-in JSONL sink is
  covered.

## Acceptance checks

1. Snapshot update and outbox insert commit or roll back together in SQLite.
2. Outbox stores the complete `AuditEvent`,including stable event id,task/trace,Adapter,risk,reason,
   and timestamp.
3. A sink failure leaves the outbox pending and the next TaskBus retries the same event id.
4. A crash after JSONL append but before outbox acknowledgement produces one JSONL line after retry.
5. Successful delivery marks the row delivered;later restarts do not emit it again.
6. Normal submit/approval/terminal behavior and Round 202 boss views remain unchanged.
7. `aico-state` reports/resets the new table and schema version.
8. Full root/SME tests,Ruff,mypy,touched format,structure,and diff gates pass.

## Stop conditions

- Stop if audit delivery can dispatch or resume an Adapter task.
- Stop if the outbox becomes a second query truth for `/audit` or `/metrics`.
- Stop if state can become interrupted without a committed outbox intent.
- Stop if retry creates a new event id or duplicate built-in JSONL line.

## Completion evidence

- Forced SQLite trigger failure rolls back both snapshot and outbox insert.
- Failing sink leaves the exact persisted event pending;next startup delivers and acknowledges it.
- Append-before-ack simulation restarts through real Phase1 assembly with status `interrupted`,one
  JSONL event,the same event id,and `pending_recovery_audits: 0`.
- Targeted composition/store/audit gate: `77 passed`;full root: `598 passed, 1 skipped`;SME:
  `53 passed`.
- Ruff,mypy,touched format,class/method structure,and `git diff --check` pass.
- Full-root format retains one unrelated pre-existing finding in
  `projects/data-agent-v1/src/data_agent_v1/engine.py`;Round 203 did not touch it.
