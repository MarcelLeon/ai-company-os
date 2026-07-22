# Dead-Man Receiver Worker Readiness

**Status**: Complete — Round 209

## Goal Brief

**User outcome**: A deployed dead-man receiver must stop advertising readiness when its expiry and
notification worker is no longer making progress, so an external supervisor can restart it without a
present owner.

**Decision owner**: The receiver process owns only its local worker-health evidence. It may report
generic readiness, but it must not expose runtime identities, notification targets, exception text,
tokens, filesystem paths, or monitor/event state on public health endpoints.

## In scope

- Keep `/healthz` as process liveness: a responsive event loop returns HTTP 200.
- Make `/readyz` require both a successful SQLite ping and recent successful worker progress.
- Record worker success/failure with a monotonic clock, not wall time.
- Allow at most two consecutive internal worker failures; the third makes readiness fail closed.
- Make readiness stale when no successful worker pass has completed within three configured sweep
  intervals, even if no exception was observed.
- A later successful pass resets consecutive failures and restores readiness.
- Startup must complete one immediate coordinator pass before serving ready.
- Readiness failures return only HTTP 503 and a generic body. Stable exception type may remain in the
  receiver log; exception text must not be returned or persisted.
- Keep Compose healthcheck on `/readyz`, so repeated not-ready results can trigger the existing
  restart policy.

## Out of scope

- Persisting process-local worker-health state across restart. Startup recomputes it with an immediate
  pass; stale process evidence must not survive a new process.
- Treating downstream notification rejection as worker death. The coordinator persists that as
  pending/backoff and a completed coordinator pass remains healthy.
- Adding public metrics, monitor identities, event counts, exception detail, or notification status.
- Claiming that this replaces an external container/host supervisor or the B-012 second-failure-domain
  deployment evidence.
- Adding a generic health framework. This is one concrete receiver-owned loop and remains local.

## Acceptance checks

1. `/healthz` stays 200 while `/readyz` returns generic 503 for stale worker evidence.
2. One and two consecutive worker exceptions remain ready; the third fails closed.
3. A later successful pass clears the failure count and restores readiness.
4. Worker staleness is based on monotonic elapsed time and three sweep intervals.
5. SQLite ping failure yields the same generic 503 without leaking exception text.
6. Background wake/timeout behavior and immediate startup reconciliation remain intact.
7. Compose still probes `/readyz` and has `restart: unless-stopped`.
8. Full tests, Ruff, mypy, touched format, structure, diff, and container static gates pass.

## Stop conditions

- Stop if public readiness exposes monitor/event/endpoint/secret/exception details.
- Stop if wall-clock changes can mark a healthy worker stale or extend its readiness window.
- Stop if downstream delivery backoff itself marks the worker dead.
- Stop if a new process can report ready before one immediate coordinator pass succeeds.
- Stop if the readiness model requires persistence or pollutes the receiver SQLite truth boundary.

## Completion evidence

- Receiver suites pass with direct coverage for health-vs-readiness separation, monotonic staleness,
  one/two/three failure threshold, recovery, generic database failure, and downstream backoff remaining
  ready.
- The static container test and Compose config prove `/readyz` remains the supervised healthcheck and
  `restart: unless-stopped` remains enabled.
- Full root and SME suites, Ruff, mypy, touched format, production structure, CLI, Compose, and diff
  gates pass. Full-root format still reports only the untouched existing data-agent file.
