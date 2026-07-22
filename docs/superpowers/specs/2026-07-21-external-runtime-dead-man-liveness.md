# External Runtime Dead-Man Liveness

**Status**: Complete — Round 207

## Goal Brief

**User outcome**: When the AICO process, launch path, network path, or Mac disappears while the boss
is absent, an independently deployed receiver can infer the outage from a missing pulse and later
infer recovery from a new pulse. The failed sender is never required to report its own death.

**Decision owner**: The owner explicitly arms and disarms one stable, secret-free runtime identity at
the independent receiver. AICO owns pulse emission only; the receiver owns TTL expiry and external
open/resolved notification.

## In scope

- Emit one immediate pulse after runtime ownership and heartbeat startup, then low-frequency pulses.
- Use a stable owner-configured `runtime_id`, a fresh per-process `boot_id`, and a monotonic
  per-process `sequence`.
- Keep at most one failed pulse in memory and retry that exact pulse/idempotency key; do not persist a
  pulse history or add pulse rows to the runtime incident outbox.
- Use a dedicated HTTPS liveness transport while keeping a distinct `RuntimeLivenessSink` protocol
  and pulse payload. Round 208 superseded the original URL/token reuse after strict endpoint
  integration proved incident and pulse schemas cannot safely share one route.
- Make receiver expiry depend on receiver acceptance time plus the declared TTL, not sender clock.
- Provide a deterministic receiver-side tracker contract for arm, duplicate/out-of-order rejection,
  TTL stale/open, recovery/resolved, process replacement, and explicit disarm.
- Expose disabled/healthy/degraded/failed publisher state in heartbeat v5 and configuration readiness
  in `aico-service doctor` without exposing identities, URL, token, or exception detail.

## Out of scope

- Hosting or choosing a real independent receiver, vendor, account, URL, or credential.
- Claiming current-Mac availability from local heartbeat or publisher state.
- Persisting unlimited pulse history, creating a liveness SQLite outbox, or treating each pulse as an
  incident/audit event.
- Automatically disarming on clean process stop. A clean stop can be a restart, deployment, crash
  precursor, or permanent uninstall; only the receiver owner can safely declare permanent intent.
- Treating laptop sleep as healthy. Sleep or network partition beyond TTL is unavailable by default.
- Exactly-once delivery. The receiver must deduplicate the stable pulse idempotency key.

## Pulse and receiver semantics

- Pulse payload is strict and secret-free: schema/event type, `runtime_id`, `boot_id`, `sequence`,
  sender `sent_at`, `interval_seconds`, and `expires_after_seconds`.
- A publisher creates a new `boot_id` on every process start and sends sequence 1 immediately.
- Failed delivery retains the same pulse in memory and retries no faster than 60 seconds or the pulse
  interval, whichever is lower. A successful delivery schedules the next sequence after the interval.
- Local publisher status is `degraded` while a retry is pending but the previous success is inside
  TTL, and `failed` if no pulse ever succeeded or the local success age reaches TTL.
- The receiver must be explicitly armed with a TTL. It opens once if no first pulse arrives by
  `armed_at + TTL`; after acceptance it evaluates staleness using `received_at + TTL`, and resolves
  once when it accepts a later valid pulse.
- Same-boot sequence must increase. A different boot replaces the current boot only when its sender
  timestamp is not older; this conservative boundary avoids a delayed old boot replacing a new one.
- Restart sends a new boot immediately and should recover before TTL. Permanent uninstall requires
  owner-side receiver disarm before stopping the runtime.

## Acceptance checks

1. Startup sends sequence 1 immediately with no URL/token/host/path in payload or local heartbeat.
2. No pulse is sent before interval; the next due pulse increments sequence.
3. Send failure retains the exact pulse and `Idempotency-Key`; retry is bounded and success advances.
4. Publisher reports failed before first success, degraded during an in-TTL failure, and failed after
   TTL.
5. A rebuilt publisher has a new boot id and immediate sequence 1 without durable pulse history.
6. Receiver ignores duplicate/out-of-order pulses, opens once after TTL, resolves once on recovery,
   and accepts a valid replacement boot.
7. Explicit disarm prevents stale alerting; process stop itself sends no disarm event.
8. Enabling liveness requires HTTPS runtime webhook, heartbeat, a safe runtime id, interval at least
   the heartbeat interval, and TTL at least three pulse intervals.
9. Heartbeat v5 and doctor distinguish disabled/healthy/degraded/failed/config-invalid without
   printing receiver secrets or runtime identity.
10. Full root/SME tests, Ruff, mypy, touched format, structure, and diff gates pass.

## Stop conditions

- Stop if missing-pulse detection depends on any AICO process callback.
- Stop if a pulse is appended to the durable runtime incident outbox or unbounded local history.
- Stop if clean shutdown automatically suppresses external stale detection.
- Stop if sender time determines receiver TTL expiry.
- Stop if a failed send creates a new sequence/idempotency key on each retry.
- Stop if URL, bearer token, exception, hostname, filesystem path, or arbitrary owner label reaches
  pulse/heartbeat/log output.

## Completion evidence

- Publisher tests prove immediate sequence 1, interval scheduling, exact pending-pulse retry,
  first-failure/TTL health, new-process boot replacement, and stable HTTP idempotency without
  endpoint/token leakage.
- Receiver tests prove arm-without-first-pulse timeout, acceptance-time expiry, single open/resolved,
  duplicate/out-of-order/old-boot rejection, replacement boot, and explicit disarm.
- Heartbeat v5 tests prove recovery → incident alert → liveness → component health order and strict
  disabled/healthy/degraded/failed validation without runtime identity in the file.
- Settings and doctor tests prove HTTPS, safe identity, heartbeat cadence, and three-interval TTL
  gates; Feishu and Telegram use the same runtime heartbeat lifecycle.
- Related gate: `98 passed`; full root: `647 passed, 1 skipped`; SME: `53 passed`. Ruff, mypy,
  touched format, production structure, and diff gates pass. Full-root format retains only the
  unrelated pre-existing data-agent file finding.
- No real receiver, credential, LaunchAgent, IM, or webhook state was created or changed. B-012
  remains deferred for independent deployment and outage samples.
