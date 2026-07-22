# Single Runtime Ownership

**Status**: Complete — Round 204

## Goal Brief

**User outcome**: One local AICO company state can have exactly one active runtime owner. A manual
terminal,LaunchAgent restart,or second webhook process must never steal live tasks or duplicate IM
consumption while the boss is absent.

**Decision owner**: Phase1 runtime lifecycle;operator stops the existing owner before replacement.

## Failure case

Round 202/203 correctly reconcile persisted `RUNNING` as orphaned during startup,but they assume a
single runtime. If runtime A is still active and runtime B opens the same SQLite state,B currently
marks A's live tasks interrupted and may start a second Telegram poller/Feishu server.

## In scope

- Derive one owner-lock path from the canonical SQLite state path;without SQLite,use the canonical
  local `.aico/runtime-owner.lock` fallback.
- Acquire a non-blocking OS advisory lock before any startup reconciliation,Channel start,scheduler,
  or heartbeat.
- Keep the lock handle for the complete runtime lifetime and release it on normal stop,start failure,
  or process death.
- Persist only secret-free owner metadata:lock schema,state,PID,started/stopped time,and protected
  resource path.
- Reject a competing owner with an actionable error containing lock path and owner PID when known.
- Delay TaskBus recovery from object construction to an explicit startup step inside the lock.
- Cover both Telegram CLI and Feishu FastAPI through their shared Phase1 lifespan.
- Add `aico-service doctor` owner status:loaded service without an active owner is failed;an active
  owner without installed/loaded launchd is visible as a manual owner warning.

## Out of scope

- Multi-host or distributed leases,leader election,Postgres,Redis,or fencing tokens.
- Running multiple runtimes against one state DB.
- Automatically killing or replacing an existing owner.
- Treating lock-file existence as ownership;only the kernel advisory lock is authoritative.
- Using the owner lock to auto-resume or replay tasks.

## Acceptance checks

1. Runtime owner is acquired before TaskBus recovery and released after Channel/scheduler cleanup.
2. A competing runtime fails before reconciliation and does not alter a live `RUNNING` snapshot.
3. Normal stop and startup failure release ownership so a replacement can start.
4. Abrupt process exit releases the kernel lock even if the metadata file remains.
5. Same canonical state DB produces the same lock path;different state DBs remain isolated.
6. Telegram and Feishu shared lifespans enforce the same ownership contract.
7. `aico-service doctor` reports owner active/free without exposing environment values or secrets.
8. Existing restart outbox,approval,terminal,and boss-view behavior remains green.
9. Full root/SME tests,Ruff,mypy,touched format,structure,and diff gates pass.

## Stop conditions

- Stop if duplicate startup can reconcile state before ownership is proven.
- Stop if stale lock-file contents can block recovery after process death.
- Stop if the implementation kills an existing runtime automatically.
- Stop if different state databases unintentionally share one lock.

## Completion evidence

- Competing Phase1 runtime fails before recovery/Channel start;the live persisted snapshot remains
  `RUNNING` until the first owner exits.
- Normal stop,start failure,and SIGKILL all release the kernel lock;replacement acquisition succeeds.
- Real multi-process dogfood:competitor rejected while owner live,then owner kill → replacement
  acquire → orphan `RUNNING → INTERRUPTED` → final owner active false.
- Feishu TestClient proves shared lifespan owner active during serving and free after shutdown.
- Doctor tests cover missing owner,healthy launchd PID match,and manual-owner PID mismatch failure.
- Related gate: `91 passed`;full root: `604 passed, 1 skipped`;SME: `53 passed`.
- Ruff,mypy,touched format,class/method structure,and `git diff --check` pass.
- Current checkout doctor truthfully reports `.env` missing,service not installed,owner missing,and
  heartbeat not installed;no real LaunchAgent or IM state was changed.
- Full-root format retains one unrelated pre-existing finding in
  `projects/data-agent-v1/src/data_agent_v1/engine.py`;Round 204 did not touch it.
