# Durable Out-of-Band Runtime Alerts

**Status**: Complete — Round 206

## Goal Brief

**User outcome**: When the boss is absent and AICO exhausts safe recovery of a locally owned
background task, a separately configured endpoint must receive one durable incident-open alert and
one recovery alert without depending on the failed primary IM Channel.

**Decision owner**: The single runtime owner may create runtime incident facts. The owner explicitly
configures the secondary webhook endpoint; a remote receiver owns event-id idempotency.

## In scope

- Convert only owned-task self-healing transitions into alerts: first `open` creates an incident;
  later `healthy` resolves that same incident. `recovering` neither opens nor resolves it.
- Persist active incidents and immutable alert events in the configured AICO SQLite state database.
- Insert incident state and outbox event in one SQLite transaction.
- Retry undelivered events in row order with persisted 1-minute, 5-minute, then 15-minute capped
  backoff, stopping at a deferred head event or first failure so open/resolved ordering cannot invert.
- Deliver secret-free JSON through a `RuntimeAlertSink` plugin; provide a generic HTTPS webhook sink
  with a stable `Idempotency-Key` header and optional bearer token.
- Expose disabled/healthy/pending/failed delivery status in heartbeat and `aico-service doctor`.
- Include runtime-alert tables and pending count in `aico-state` summary/reset.

## Out of scope

- Sending through the same failed Telegram/Feishu Channel or selecting a vendor-specific Slack,
  Teams, PagerDuty, email, SMS, or phone-call payload.
- Exactly-once remote delivery. A crash after HTTP acceptance but before SQLite acknowledgement may
  retry the same immutable event id; the receiver must deduplicate it.
- Alerting on generic Channel/Adapter/network health failure, every failed recovery attempt, or
  business Task failure.
- Storing exception text, webhook URL, bearer token, target identifier, command, prompt, or raw
  heartbeat payload in SQLite, heartbeat, logs, or alert JSON.
- Creating or guessing a real webhook credential, installing a LaunchAgent, or sending externally
  without owner configuration.

## Incident and delivery semantics

- Identity is one generated `incident_id` per component open cycle. Repeated `open` snapshots are
  idempotent.
- `incident_opened` records component, attempt count, and snapshot time.
- An active incident remains open through cooldown and `recovering`; only `healthy` produces one
  `incident_resolved` event and removes the active incident.
- New failure after resolution gets a new incident id.
- Each event has a stable generated `event_id`; webhook payload and `Idempotency-Key` use that id.
- Sink failure leaves the event pending with persisted bounded backoff. Later heartbeat or process
  restart retries the exact event when due.
- Disabled alerting is explicit WARN, pending delivery is WARN, and internal alerting failure is
  FAIL. Owned-task circuit open remains FAIL independently of delivery status.

## Acceptance checks

1. First open inserts one active incident and one pending opened event transactionally.
2. Repeated open creates no duplicates, including after rebuilding the coordinator.
3. Recovering does not resolve; healthy produces exactly one resolved event for the same incident.
4. A new open after resolution creates a new incident.
5. Sink failure preserves pending events; restart retries immutable ids and payloads in order.
6. Append/accept-before-ack retry presents the same `Idempotency-Key` to the receiver.
7. Generic external health failure creates no runtime alert.
8. Webhook request and all persisted/heartbeat/doctor/log output contain no URL, token, exception,
   target, command, or prompt.
9. Enabling a webhook without durable `AICO_STATE_DB_PATH` or the heartbeat loop fails settings
   validation.
10. Heartbeat v4 and doctor truthfully report disabled/healthy/pending/failed alert delivery.
11. State CLI shows and resets incident/outbox rows and pending alert count.
12. Full root/SME tests, Ruff, mypy, touched format, structure, and diff gates pass.

## Stop conditions

- Stop if generic `HealthStatus.FAILED` can create an alert incident.
- Stop if a repeated heartbeat can create duplicate open/resolved events.
- Stop if resolved can overtake an undelivered opened event.
- Stop if sink success can be acknowledged before the sink returns.
- Stop if a failed sink can be hammered every heartbeat without persisted backoff.
- Stop if webhook configuration or exception detail can reach durable evidence or output.
- Stop if alerting can mutate business Task state or automatically replay a Task.

## Completion evidence

- Transaction rollback proves an incident cannot exist without its immutable open event. Repeated
  open/healthy snapshots and coordinator rebuilds are idempotent; a later failure starts a new
  incident.
- Sink failure/restart preserves exact events, persisted 1/5/15-minute backoff, and strict
  open-before-resolved ordering. HTTP accept-before-ack retries the same `Idempotency-Key`.
- Request/persistence/log assertions prove event JSON excludes endpoint/token and sink exception
  detail. Settings/service checks expose only key names and status.
- Related runtime/heartbeat/settings/state/service gate:`96 passed`;full root:`631 passed, 1
  skipped`;SME:`53 passed`.
- Ruff and mypy pass. Touched format, production class/function structure, and `git diff --check`
  pass;full-root format retains only the unrelated pre-existing data-agent file finding.
- Current-checkout doctor remains truthful:`.env` missing and plist/owner/heartbeat not installed.
  No real endpoint,credential,LaunchAgent,IM,or webhook state was created or changed.
