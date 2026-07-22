# Runtime Component Health

**Status**: Complete — Round 201 (real installed-service E2E remains B-010)

## Goal Brief

**User outcome**: AICO must not report itself healthy merely because its Python process is alive.
When the boss is absent, operators must be able to distinguish process liveness from the health of
the IM intake loop, the default execution Adapter, optional Adapters, and scheduled morning handoff.

**Decision owner**: AICO runtime for health collection; local operator for remediation.

## In scope

- Produce one bounded, secret-free component-health snapshot on each runtime heartbeat refresh.
- Treat Channel, default Adapter, and enabled morning scheduler as required components.
- Treat additional Adapters as optional: their failure degrades the company but does not imply the
  primary command path is unavailable.
- Bound every health check by a timeout and convert plugin exceptions to status only; never persist
  exception text, command arguments, tokens, URLs, target IDs, or environment values.
- Make Telegram health fail when its active polling task is absent or unexpectedly completed, even
  if `getMe` still succeeds.
- Have `aico-service doctor` combine freshness and component health: required failure is FAIL,
  optional failure is WARN, missing component data is WARN.
- Select the supervised executable from the configured Channel and apply the same runtime+heartbeat
  lifespan to the Telegram polling and Feishu webhook entrypoints.
- Preserve backward reading of the Round 200 heartbeat shape without calling it fully healthy.

## Out of scope

- Automatically restarting the whole process for external network or provider outages.
- Sending alerts through the same failed Channel, adding a second monitoring service, or cloud
  telemetry.
- Proving provider authentication by checking only that an executable exists.
- Recording raw exception messages or configuration values in heartbeat JSON.
- Changing Adapter/Channel plugin protocols when their existing `health_check()` contract suffices.

## Health semantics

| Component | Required | FAILED effect | Evidence limit |
|---|---:|---|---|
| active IM Channel | yes | runtime `failed` | API reachability plus owned background-loop state where applicable |
| default Adapter | yes | runtime `failed` | current Adapter health contract; not a real task execution |
| optional Adapter | no | runtime `degraded` | current Adapter health contract |
| enabled morning scheduler | yes | runtime `failed` | scheduler task is running; not proof the last IM delivery arrived |

`DEGRADED` from any component makes aggregate health degraded. A timeout or unexpected exception is
mapped to FAILED for that component without persisting its message.

## Acceptance checks

1. Telegram health returns FAILED when started polling has died, even when Bot API `getMe` is OK.
2. Probe checks components concurrently with a bounded timeout and stable, secret-free names.
3. Required failure aggregates to failed; optional failure aggregates to degraded; all OK stays OK.
4. Heartbeat schema v2 contains process fields plus checked component statuses, no secrets/details.
5. Doctor returns FAIL for fresh+failed, WARN for fresh+degraded or legacy missing component data,
   and keeps stale/invalid process heartbeat as FAIL.
6. Runtime start/stop owns health heartbeat without changing real LaunchAgents in tests.
7. Telegram service renders `aico-phase1`;Feishu service renders `aico-feishu-webhook`,whose FastAPI
   lifespan writes the same running/stopped heartbeat contract.
8. Full root/SME tests, Ruff, mypy, touched format, structure and diff gates pass; real checkout
   render/doctor remains a non-mutating dry-run.

## Stop conditions

- Stop if a health payload could serialize exception text, credentials, command arguments, target
  identifiers, or environment values.
- Stop if an external outage causes an automatic restart loop.
- Stop if an optional Adapter outage marks the primary IM + default Adapter path fully failed.
- Stop if a synthetic executable check is described as provider authentication or task E2E.

## Completion evidence

- Red-green gate covers required/optional aggregation, all-healthy, timeout, plugin exception
  redaction, Telegram polling-task death, scheduler-task death, heartbeat v2 and doctor semantics.
- Related regression gate: `97 passed`;full root: `588 passed, 1 skipped`;SME: `53 passed`.
- Ruff and mypy passed. Touched format, structure and diff checks are recorded in Round 201.
- Real checkout render/doctor was run without installing or changing a LaunchAgent. Because `.env`
  is absent, the result remains readiness FAIL plus pre-install WARN, not an E2E health claim.
