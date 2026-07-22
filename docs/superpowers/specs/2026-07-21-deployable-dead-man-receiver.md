# Deployable Dead-Man Receiver

**Status**: Complete — Round 208

## Goal Brief

**User outcome**: An independently hosted receiver must keep monitoring AICO through receiver
restarts, detect a missing first or later pulse without any callback from the failed Mac, and durably
notify an owner-managed endpoint exactly once per outage edge modulo stable at-least-once retries.

**Decision owner**: A separately authenticated admin explicitly arms/disarms a runtime monitor. A
pulse credential may refresh liveness but cannot change monitoring policy. The receiver owns outage
identity, acceptance-time expiry, durable notification intent, and delivery retry.

## In scope

- A standalone FastAPI process and CLI entrypoint that can run outside the AICO Mac.
- A dedicated AICO liveness URL/token setting; incident-alert and pulse payloads must never share a
  strict endpoint merely because both use HTTPS.
- A dedicated receiver SQLite database; it must not share AICO Task/runtime state tables.
- Separate pulse and admin bearer tokens, required and unequal.
- Authenticated arm, disarm, monitor-status, and pulse endpoints; public health/readiness expose no
  identities, URLs, tokens, or event detail.
- Persistent armed monitor, TTL, latest accepted boot/sequence/sender time, receiver acceptance time,
  active outage identity, immutable notification outbox, retry attempts, and next-attempt time.
- First missing pulse and later missing pulse detection from receiver time.
- Atomic late-recovery handling: if TTL expired before a pulse arrives but the periodic sweep has not
  run, accepting that pulse must create ordered outage-open and outage-resolved events in the same
  transaction before updating health.
- Duplicate/out-of-order/old-boot rejection without extending TTL.
- HTTPS notification sink with stable event-id `Idempotency-Key`, optional bearer, strict open/resolved
  payload, success-before-ack, row-order delivery, and persisted 1/5/15-minute capped backoff.
- Background sweep/delivery worker with an immediate startup pass and prompt wake-up after state
  changes.
- A non-root Docker image contract with `/data` persistence and no embedded secrets.

## Out of scope

- Selecting or provisioning a real cloud, domain, TLS certificate, secret manager, SMS/email/Teams/
  PagerDuty vendor, or owner account.
- Running the receiver on the same Mac and calling that an independent failure domain.
- Remote exactly-once notification. Acceptance-before-local-ack may retry one immutable event id;
  downstream must deduplicate it.
- Automatically arming from the first pulse, automatically disarming on AICO stop, or silently
  changing an armed TTL. TTL change requires explicit disarm then arm.
- Replaying AICO business Tasks, mutating AICO runtime state, or receiving primary IM traffic.
- Keeping raw request headers, bearer tokens, endpoint URLs, exception text, hostname, or filesystem
  paths in the receiver database or notification payload.

## State and transaction semantics

- `arm(runtime_id, ttl)` inserts a new monitor. Repeating the same arm is idempotent and does not reset
  its acceptance window; a different TTL conflicts until explicit disarm.
- `disarm` removes the active monitor and suppresses future stale transitions. Existing immutable
  notification events remain deliverable; disarm does not manufacture a false recovery.
- Monitor expiry is `armed_at + ttl` before the first accepted pulse, then `last_received_at + ttl`.
- First expiry creates one active `outage_id` and one immutable opened event transactionally.
- A valid pulse while an outage is active creates one resolved event for the same outage, then clears
  the active outage transactionally.
- A valid pulse arriving after expiry but before sweep creates opened and resolved events in row order
  in that same transaction. Outage evidence cannot be erased by scheduler timing.
- Same-boot sequence must increase. A new boot must have a sender timestamp no older than the current
  boot. Sender time is only an ordering guard; it never decides TTL.
- Notification delivery stops at an undelivered/deferred head event so resolved cannot overtake open.

## Acceptance checks

1. Arm survives store/app reconstruction; no first pulse opens once after TTL.
2. Accepted pulse survives reconstruction and expires from receiver acceptance time, not sender time.
3. Duplicate/out-of-order/older-boot pulses return success without extending expiry.
4. Sweep opens once; later valid pulse resolves the same outage once.
5. Late recovery before sweep atomically creates ordered open/resolved events.
6. Different-TTL re-arm and pulse TTL mismatch fail closed; same arm is idempotent without reset.
7. Disarm persists and delayed pulses cannot re-arm or create future stale events.
8. Sink failure/restart retains exact events, stable idempotency keys, 1/5/15 backoff, and strict order.
9. HTTP pulse/admin credentials are separate; missing/wrong credentials, invalid idempotency key,
   extra fields, and unsafe identities fail without leaking secrets.
10. Background worker performs immediate restart reconciliation and can be woken after state changes.
11. Docker contract runs as non-root, persists `/data`, exposes only the receiver CLI, and contains no
    secret value.
12. Full root/SME tests, Ruff, mypy, touched format, structure, diff, and deployment static gates pass.

## Stop conditions

- Stop if a pulse can implicitly arm/disarm or change TTL.
- Stop if a late recovery can erase an elapsed outage boundary.
- Stop if sender time or sequence alone extends receiver TTL.
- Stop if opened/resolved state and its notification intent can commit separately.
- Stop if resolved can overtake an undelivered opened event.
- Stop if admin and pulse share one credential or if either appears in response/log/database.
- Stop if receiver DB uses the AICO Task-state schema or runs in the same process as AICO orchestration.
- Stop if container defaults to root or stores state outside the declared volume.

## Completion evidence

- Persistence/transaction/auth/worker/HTTP integration suites pass, including restart reconciliation,
  transaction rollback, late recovery ordering, strict validation, sender-to-receiver wire compatibility,
  stable retry identity, and static container security checks.
- `aico-dead-man-receiver --help` proves the packaged CLI entrypoint is available.
- Docker/Compose contracts were statically verified. A live image build was not claimed because the local
  Docker daemon was unavailable; independent-host deployment and real outage samples remain B-012.
