# Standing Autonomy Deployment Preflight

**Status**: Implemented and locally verified — Round 214

## Goal Brief

**User outcome**: Before installing or restarting a boss-absent runtime, the owner can run
`aico-service doctor` and prove that a configured standing-autonomy grant is not merely a safe file,
but resolves through the same project, charter, appointment, persona, Adapter, scheduled target, and
hard-read-only eligibility used by the real runtime.

**Decision owner**: Preflight remains local and read-only. It may parse configuration and construct
in-memory routing objects, but must not initialize SQLite, create logs, start Channels, spawn an AI
CLI, call a network, consume a proposal, or mutate grant budget.

## In scope

- Reuse Phase 1's actual Adapter/persona/project/grant validation path from a public non-mutating
  preflight function.
- `aico-service doctor` derives only standing-autonomy-relevant settings from its owner-only `.env`;
  relative project/persona/workspace paths resolve against `--repo`, matching launchd's working dir.
- A configured grant set must be non-empty and must match the one scheduled morning target.
- Project and charter must exist; the charter role must resolve to an appointed Agent whose live
  Adapter implements the hard `read_only` preauthorization boundary.
- Codex must be enabled and its executable basename must be exactly `codex`; wrappers and broad
  Adapters remain ineligible.
- Successful output reports only a bounded grant count. Failure output may name a safe failure
  category but never owner ID, grant ID, target, path, token, raw JSON/Pydantic error, or command.

## Out of scope

- Creating, signing, renewing, editing, or consuming a grant.
- Installing LaunchAgent, starting the runtime, invoking Codex, sending IM, or proving remote receipt.
- Replacing the real runtime's startup validation or declaring B-014 complete.
- Cryptographic owner identity, dedicated OS user isolation, usage/cost accounting, or write-capable
  autonomy.

## Acceptance checks

1. A fully valid repo-relative project config, exact morning binding, enabled real Codex command, and
   external owner-only grant produce `standing autonomy: OK` with bounded count.
2. The same fixture is accepted by `build_phase1_runtime`; doctor must not maintain a looser shadow
   policy.
3. Target/thread/project mismatch, unknown project/charter, missing appointment/persona, disabled
   Codex, non-Codex executable, malformed config, or empty grant set fail before installation.
4. Failure details contain no owner/grant/target identity, secret, absolute path, raw parser text, or
   configured command.
5. Preflight leaves state DB, audit/memory/log paths, runtime lock, heartbeat, and proposal history
   absent and does not call Adapter or Channel methods.
6. Disabled standing autonomy remains WARN rather than blocking ordinary runtime deployment.
7. Targeted/full tests, SME tests, Ruff, mypy, touched format, AICO production structure, JSON,
   Compose, and `git diff --check` pass.

## Stop conditions

- Stop if doctor constructs a full runtime or opens a stateful store merely to validate config.
- Stop if doctor and runtime have separate authorization eligibility rules that can drift.
- Stop if a safe-looking wrapper can self-declare Codex hard-read-only eligibility.
- Stop if an error exposes any owner-controlled identity, command, path, secret, or raw exception.
- Stop if a successful preflight is described as a real scheduled provider/IM sample.
