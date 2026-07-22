# Durable Local Runtime Service

**Status**: Complete — Round 200 (inherited full-repository format exception recorded below)

## Goal Brief

**User outcome**: AICO keeps receiving work, scheduling morning handoffs, and leaving a verifiable
liveness trail after the boss closes the terminal or logs back into the Mac. A local operator can
install, inspect, restart, and remove the service without copying secrets into launchd metadata.

**Decision owner**: local machine owner for install/restart/uninstall; AICO runtime for heartbeat.

## In scope

- Fix the Phase 1 runtime lifecycle so the morning scheduler remains alive until runtime stop.
- Write a secret-free JSON heartbeat with running/stopped state, PID, start time, and latest beat.
- Add an `aico-service` CLI for macOS launchd render/install/restart/status/doctor/uninstall.
- Use absolute repo, venv executable, log, plist, and heartbeat paths.
- Load AICO secrets from the ignored repository `.env`; never serialize secret values into plist,
  status, doctor output, or logs.
- Configure launchd `RunAtLoad`, crash restart, throttling, background process type, and stdout/
  stderr logs.
- Back up a replaced plist and move an uninstalled plist to Trash for recovery.
- Make readiness and installed-state checks deterministic and testable without touching the real
  user LaunchAgents directory or live launchctl domain.

## Out of scope

- Installing or changing the real user's LaunchAgent without an explicit CLI invocation.
- Preventing Mac sleep, keeping the network alive while the lid is closed, or remote wake.
- Cloud deployment, Docker, system-wide daemons, Linux systemd, or Windows services.
- Storing Telegram, Feishu, provider, or other credentials in plist.
- Claiming Telegram/provider health solely because the process heartbeat is fresh.

## Acceptance checks

1. Runtime start leaves the morning scheduler active; runtime stop cancels it exactly once.
2. Heartbeat writes atomically, contains no environment or credential values, becomes fresh while
   running, and records stopped state on graceful shutdown.
3. Rendered plist uses the absolute Channel-specific entrypoint (`aico-phase1` for Telegram,
   `aico-feishu-webhook` for Feishu), repository working directory, `.aico` logs, `RunAtLoad`,
   crash-only `KeepAlive`, and only non-secret environment variables.
4. Install refuses unsupported platforms or missing repo/executable/`.env`, backs up changed
   metadata, then uses the current user's launchd domain. Uninstall is recoverable.
5. Doctor reports platform, repo, executable, `.env` presence/permissions/required key names,
   plist agreement, launchctl loaded state, and heartbeat freshness without printing values.
6. Parser/lifecycle/doctor tests run against temporary paths and fake command runners. A local
   dry-run renders and audits the real checkout without installing a service.
7. Full pytest, SME tests, Ruff, mypy, touched-file format, structure, diff, and continuity gates
   pass. Any inherited full-repository format failure must be named and left untouched.

## Evidence required

- Red-green scheduler lifecycle and heartbeat tests.
- Golden plist assertions proving no token/key values are present.
- Fake launchctl install/restart/status/uninstall tests, including failure and recovery paths.
- `aico-service render` and pre-install `doctor` output against this checkout.
- Explicit record that real launchd installation and real Telegram delivery still require owner
  execution/authorization.

## Completion evidence

- Targeted lifecycle/heartbeat/service/settings gate: `49 passed`.
- Full root: `572 passed, 1 skipped`;SME: `53 passed`;Ruff and mypy passed.
- Touched-file format, structure scan and `git diff --check` passed. Full-repository format still
  reports only the pre-existing, out-of-scope `projects/data-agent-v1/src/data_agent_v1/engine.py`.
- `aico-service render | plutil -lint -` returned `<stdin>: OK`.
- Real-checkout doctor reported repo/executable ready and `.env`/plist/heartbeat absent. No real
  LaunchAgent was installed and no IM/provider E2E claim was made.

## Stop conditions

- Stop if any secret value is copied into plist, stdout, status, doctor output, or committed files.
- Stop if install silently overwrites service metadata without a recoverable copy.
- Stop if launchd restart semantics cause intentional clean exits to loop.
- Stop if a fresh process heartbeat is presented as proof of IM/provider connectivity.
