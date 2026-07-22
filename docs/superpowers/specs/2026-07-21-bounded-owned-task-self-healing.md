# Bounded Owned-Task Self-Healing

**Status**: Complete — Round 205

## Goal Brief

**User outcome**: When the boss is absent, AICO should recover a locally owned polling or schedule
task that dies while the process remains alive, without turning a Telegram, Feishu, or provider
outage into a process restart loop.

**Decision owner**: The single runtime owner may restart only background tasks whose lifecycle it
directly owns. External dependency recovery remains the dependency's responsibility.

## In scope

- Distinguish local owned-task liveness from synthetic network/provider health.
- Supervise Telegram polling and the enabled morning-push scheduler in the existing runtime
  heartbeat loop.
- Restart a dead owned task in process, then require a stabilization interval before clearing the
  incident.
- Limit repeated recovery attempts and open a cooldown circuit after three failed stabilizations.
- Persist only stable component names, recovery state, attempt count, and check time in heartbeat.
- Make doctor report recovering as WARN and an open recovery circuit as FAIL.
- Keep Feishu webhook and external Adapter/Channel failures outside the automatic-recovery trigger.

## Out of scope

- Restarting the process, mutating LaunchAgent state, or adding a second supervisor daemon.
- Automatically retrying interrupted business Tasks or assuming whether an external side effect
  happened.
- Using exception text, credentials, URLs, target IDs, or command arguments as recovery evidence.
- Treating Bot API/provider reachability as proof that an owned background task is alive.
- Out-of-band alerts; this round makes the failure machine-visible but does not add a second Channel.

## Recovery policy

- A task that was healthy and remains alive is `healthy`.
- A dead task is restarted immediately and remains `recovering` until it survives 60 seconds.
- Each restart call is bounded to 5 seconds so the heartbeat supervisor cannot be captured by a
  hanging component cleanup.
- Death before stabilization consumes another attempt. After three attempts, its circuit is `open`
  for 15 minutes.
- An open circuit never performs a tight retry. After cooldown, one new bounded recovery cycle may
  begin.
- External health failures affect component health only; they never consume a recovery attempt.

## Acceptance checks

1. Telegram polling death is restarted without restarting the process.
2. Morning scheduler death is restarted without duplicating a live task.
3. A recovered task must survive the grace period before attempts reset.
4. A restart call is bounded; three failed stabilizations open a circuit and checks during cooldown
   do not restart again.
5. Cooldown expiry permits a new attempt.
6. Telegram API or Adapter failure with live owned tasks performs no recovery action.
7. Heartbeat schema records secret-free self-healing state; doctor maps recovering/open correctly.
8. Telegram CLI and Feishu lifespan both retain the established owner/start/stop ordering.
9. Full root/SME tests, Ruff, mypy, touched format, structure, and diff gates pass.

## Stop conditions

- Stop if generic `HealthStatus.FAILED` can trigger a restart.
- Stop if the supervisor can restart a task not owned by the current runtime.
- Stop if a live task can be duplicated or a stopped runtime can be resurrected during shutdown.
- Stop if retries can happen without attempt, grace, and cooldown bounds.
- Stop if recovery output can contain raw exception or configuration data.

## Completion evidence

- Unit/integration coverage proves Telegram and scheduler task restart, no live duplication,
  shutdown non-resurrection, stabilization, bounded attempts, cooldown retry, hanging-restart
  timeout, external-component exclusion, secret redaction, and recovery-before-health ordering.
- Related runtime/channel/service gate: `71 passed`;full root:`616 passed, 1 skipped`;SME:
  `53 passed`.
- Ruff and mypy pass. Touched format, production class/function structure, and `git diff --check`
  pass;full-root format retains only the unrelated pre-existing data-agent file finding.
- Current-checkout doctor remains truthful:runtime executable ready,`.env` missing,and service/owner/
  heartbeat not installed. No real LaunchAgent,credential,or IM state was changed.
