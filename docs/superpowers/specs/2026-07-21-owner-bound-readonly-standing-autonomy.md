# Owner-Bound Read-Only Standing Autonomy

**Status**: Implemented and locally verified — Round 213

## Goal Brief

**User outcome**: When the boss is absent, one explicitly preauthorized standing-charter item may
start from the scheduled morning loop without another IM tap, while AICO can prove who authorized it,
where results may be sent, how much execution is allowed, and why the selected Adapter cannot mutate
the workspace or silently fan out to another Agent.

**Decision owner**: Autonomy is opt-in through an owner-only grant file outside every managed project
repository. A project charter is intent, not authorization. A morning chat target is a destination,
not requester identity. Only the exact conjunction of grant, candidate, target, budget, read-only risk,
and an Adapter-enforced execution boundary may create a preauthorized task.

## In scope

- Optional `AICO_STANDING_AUTONOMY_GRANT_PATH` points to a regular, non-symlink, current-user-owned,
  owner-only file outside managed repositories.
- Strict versioned JSON grants bind `grant_id`, `owner_id`, channel/target/thread, project, charter,
  aware expiry time, total `max_runs`, per-run `max_duration_seconds`, and mode `read_only`.
- Scheduled `/morning` is the only automatic trigger. Interactive `/morning`, `/inbox`, `/proposals`,
  proposal refresh, and runtime startup alone remain read-only and never execute a grant.
- One candidate at most is claimed per scheduled tick. A synthetic request uses the grant owner as
  `Task.requester_id` and the exact granted `ChannelTarget` as its source.
- Every preauthorized task carries grant/charter/proposal metadata, disables collaboration, removes
  provider-session metadata, and is checked by TaskBus before dispatch.
- TaskBus accepts it only when text risk is read-only and the selected Adapter declares an enforced
  preauthorized `read_only` boundary. This gate also applies to any caller that manually forges the
  metadata.
- Codex uses a dedicated command shape for such tasks: approval never, sandbox read-only,
  user config ignored, exec-policy rules ignored, ephemeral session, strict config, explicit
  `experimental_network.enabled=false`, no search flag, and no resume. Other configured Codex
  arguments cannot weaken that command.
- Grant consumption is persisted with the standing proposal decision. Restart must not reset
  `max_runs`. Expired, exhausted, target-mismatched, risky, session-bearing, collaboration-enabled,
  unknown, or broad-permission execution remains a candidate for manual review.
- Per-run wall-clock budget is enforced by AICO. On timeout AICO interrupts the TaskBus task, cancels
  the local stream waiter, and sends a bounded hold message to the granted target.

## Out of scope

- Autonomous file edits, shell mutations, publishing, customer messaging, purchases, secret use,
  web search, multi-Agent delegation, or automatic approval of risky work.
- Treating prompt `permissions`, role names, charter text, chat IDs, or `read_only` wording as an
  enforceable sandbox.
- Cryptographic signatures, remote policy services, usage-token/cost accounting unavailable from
  current CLI Adapters, or unattended grant creation/renewal.
- Enabling a real grant in `.env.example`, installing LaunchAgent, sending a real IM, or consuming
  paid provider work without owner credentials and explicit deployment authorization.

## Acceptance checks

1. Missing, in-repo, symlink, non-regular, wrong-owner, group/world-accessible, oversized, malformed,
   duplicate, naive-expiry, or unsupported-version grant files fail closed without leaking paths or
   raw parser errors.
2. Exact owner, target/thread, project, charter, unexpired time, and remaining run count are required.
3. A scheduled tick can run one granted candidate; interactive surfaces still create/list candidates
   without execution.
4. Persisted restart history exhausts `max_runs`; a new grant ID has its own budget, while editing the
   same grant cannot erase prior consumption.
5. Preauthorized tasks contain audit-safe grant identity, exact requester identity, no provider
   session, and disabled collaboration.
6. TaskBus rejects forged preauthorization sent to Claude/broad fake Adapters, risky text, enabled
   collaboration, resume metadata, or unsupported modes before Adapter dispatch.
7. Codex command construction always uses the dedicated hard-safe flags and ignores configurable
   bypass/write/search/resume arguments for preauthorized tasks.
8. Runtime timeout interrupts the task and leaves it non-running; normal completion is not interrupted.
9. Output and hold messages contain no grant-file path, full owner ID, secret, raw exception, or task
   payload.
10. Targeted/full tests, SME tests, Ruff, mypy, touched format, production structure, packaged CLI,
    Compose, and `git diff --check` pass.

## Stop conditions

- Stop if grant scope can be inferred from project text, target/chat identity, or prompt permissions.
- Stop if any broad-permission Adapter can opt in without an Adapter-owned hard execution boundary.
- Stop if an autonomous parent can create collaboration children or resume a mutable provider session.
- Stop if budget accounting is in-memory only or a failed/timeout dispatch can retry without consuming
  the claimed run.
- Stop if a local machine test is described as a real owner grant, paid provider run, or production
  boss-absent deployment.
