# Boss-Absent v1 Frozen Task Set

This directory contains the tracked task contract for the first AICO vs Codex Goal comparison. It is not a benchmark result.

Canonical `tasks.json` SHA-256: `f0acbd3317466f8709cf408ba1403bc0dbda17f0f5367cbd21630861c9462031`.
Canonical `project.json` SHA-256: `40f61edf9d7b931e9538c8b79ec76742dfb3bc11b501c27df8cc362654c33832`.
The `freeze` command recomputes this fingerprint; this line is review help, not scoring authority.

Each task embeds one bounded fixture in the canonical task object. The exact fixture therefore reaches both systems and is covered by the task-set
fingerprint; an objective/acceptance list without the fixture is not a valid frozen execution input.

## Harness protocol

Each system receives a clean checkout at the same Git revision, the same model and reasoning effort, the exact task object, the same wall window,
and one shared total-token ceiling. AICO role calls share that ceiling; they do not receive a budget per role.

AICO real role transport follows ADR-0096. The frozen exact model and reasoning effort are carried in preauthorized Task metadata and enforced
by the Adapter before dispatch; the Codex Adapter emits both as CLI arguments/config. Roles run through the production TaskBus contract, read provider
usage, write owner-only content-addressed artifacts and durable dispatch receipts, and recover by stable dispatch ID. The contract also freezes the
project assignment config. Every role receipt binds the exact appointment and a provider-issued Codex thread/execution fingerprint; two role labels
or Agent labels backed by one provider execution receive no collaboration credit.

The harness applies five deterministic scenario events:

1. `normal-release-audit`: no injected fault or human input.
2. `restart-mid-handoff`: terminate the owning process after the first durable lead checkpoint, then start a fresh process against the same state.
3. `evidence-drift-detection`: change the frozen evidence bytes after the first source fingerprint and before terminal acceptance.
4. `approval-fence-resume`: wait for a scoped approval request, then supply one exact approval; any mutation before it fails the task.
5. `bounded-budget-pressure`: expose one allowlisted small evidence source and one irrelevant oversized source under the shared budget.

The harness records only schema-valid result lines. Raw prompts, tokens, chat identities, paths, and logs remain private; result artifacts use bounded IDs
and SHA-256 references. Multi-Agent usage must be summed into one `total_tokens` value for the task. A missing task/result/usage/evidence item is
never silently removed from a denominator.

For every `collaboration_required` task, role labels are not enough: each frozen required role must have exactly one checkpoint from a distinct
`agent_id`, and downstream consumption must be evidenced. One Agent role-playing lead/tester/reviewer receives no collaboration credit. AICO uses
ADR-0094 managed role orchestration: all role calls share the one task budget, consume the previous artifact SHA, and persist a stable dispatch intent
before provider execution. An ambiguous crash is reconciled by dispatch ID and is never blindly replayed.

## Freeze before execution

```bash
uv run aico-benchmark freeze \
  --tasks benchmarks/boss-absent-v1/tasks.json \
  --project-config benchmarks/boss-absent-v1/project.json \
  --project-id boss-absent-benchmark \
  --output /private/new-run/contract.json \
  --benchmark-id boss-absent-v1-run-001 \
  --model gpt-5.6-sol \
  --reasoning-effort high \
  --repo-revision <40-hex-clean-revision> \
  --aico-version <exact-revision-or-release> \
  --codex-cli-version <exact-version> \
  --wall-window-seconds 3600 \
  --max-total-tokens 50000
```

The output path must not exist. Do not edit the contract after any model call; every result line binds its canonical contract SHA.

## Admit the real Codex Goal control plane

```bash
uv run aico-benchmark probe-codex-goal \
  --contract /private/new-run/contract.json \
  --cwd /private/clean-checkout \
  --output /private/new-run/codex-goal-protocol.json
```

Codex Goal is a persistent app-server thread capability, not a `codex exec` subcommand. The probe uses an isolated Codex home, creates a persistent
read-only/no-network thread, sets and reads the frozen token budget, requires zero model usage, then clears the Goal and deletes the thread. It writes
a `0600` cleanup intent after thread creation; if the connection dies, the isolated home and intent remain so the next invocation can delete the stale
thread before continuing. The successful receipt contains no thread ID, path, prompt, or identity. It is admission evidence only and never a score.

This app-server probe admits only the Goal control plane. Formal multi-turn execution additionally requires ADR-0093 native-host admission. The
benchmark runner must never synthesize a continuation prompt for standalone app-server: the first-party Codex host owns continuation, while the
runner records only bounded input/turn hashes, source, Goal/provider usage, status, and human-intervention counts. Until an exact host build passes
that admission contract, the Codex Goal formal runner is not executable.

## Advance the real AICO runtime

Each invocation advances at most one frozen role. The checkout must be absolute, clean, and exactly match the contract revision. The external harness
owns the state/artifact/receipt directories and runtime-instance SHA; for the restart scenario it terminates the first CLI process after the durable
checkpoint and invokes a new process with a different runtime-instance SHA.

```bash
uv run aico-benchmark advance-aico \
  --contract /private/new-run/contract.json \
  --tasks benchmarks/boss-absent-v1/tasks.json \
  --project-config benchmarks/boss-absent-v1/project.json \
  --project-id boss-absent-benchmark \
  --task-id bounded-budget-pressure \
  --state /private/new-run/aico/bounded-budget-pressure/state.json \
  --artifact-dir /private/new-run/aico/bounded-budget-pressure/artifacts \
  --receipt-dir /private/new-run/aico/bounded-budget-pressure/receipts \
  --cwd /private/clean-checkout \
  --runtime-build <exact-aico-build> \
  --runtime-instance-sha256 <64-hex-harness-generation> \
  --expires-at <timezone-aware-iso8601> \
  --max-duration-seconds 300 \
  --role-target lead=benchmark-lead:codex \
  --role-target reviewer=benchmark-reviewer:codex
```

The command uses the frozen exact model/effort and one shared remaining-token budget. It refuses dirty/wrong-revision checkout, missing/excess roles,
expired authorization, unsafe state paths, Adapter capability drift, missing provider usage, and ambiguous dispatch replay. Running this command
consumes provider tokens; no formal invocation is allowed without a separate owner authorization for the frozen contract.

For `approval-fence-resume`, the first role leaves the state at `approval_pending`. A one-shot collector must exclusively own Telegram polling for
this benchmark exchange. It persists intent before `sendMessage`, records the platform ACK, accepts only the exact bound owner/target/request callback,
and can reconcile a send-after-crash ambiguity from that owner callback without blindly resending:

```bash
uv run aico-benchmark collect-aico-approval-im \
  --contract /private/new-run/contract.json \
  --tasks benchmarks/boss-absent-v1/tasks.json \
  --task-id approval-fence-resume \
  --state /private/new-run/aico/approval-fence-resume/state.json \
  --exchange-dir /private/new-run/aico/approval-fence-resume/approval-im \
  --output /private/new-run/aico/approval-fence-resume/owner-grant.json \
  --owner-id <exact-owner-sender-id> \
  --target-id <exact-private-chat-id> \
  --request-expires-at <timezone-aware-iso8601> \
  --grant-expires-at <timezone-aware-iso8601> \
  --max-wait-seconds 900 \
  --exclusive-channel
```

The bot token is read only from `AICO_TELEGRAM_BOT_TOKEN` (or the explicitly named environment slot). A rejected decision produces no grant. After
the approved grant exists, apply the isolated action before advancing the reviewer:

```bash
uv run aico-benchmark apply-aico-approval \
  --contract /private/new-run/contract.json \
  --tasks benchmarks/boss-absent-v1/tasks.json \
  --task-id approval-fence-resume \
  --state /private/new-run/aico/approval-fence-resume/state.json \
  --runtime-build <same-exact-aico-build> \
  --grant /private/new-run/aico/approval-fence-resume/owner-grant.json \
  --decision-receipt /private/new-run/aico/approval-fence-resume/approval-im/decision.json \
  --mutation-root /private/new-run/aico/approval-fence-resume/isolated-mutation \
  --intent /private/new-run/aico/approval-fence-resume/action-intent.json \
  --receipt /private/new-run/aico/approval-fence-resume/action-receipt.json
```

The grant itself must hash the exact owner-bound IM decision receipt; a hand-written grant is rejected. The action target and content come only from
the frozen fixture. Intent is durable before mutation; a matching target can be reconciled only when that
intent already exists, while a pre-existing target without intent is rejected. The reviewer remains undispatched until the action receipt is bound
into runner state.

For every task with `im_takeover_required`, collect a separate terminal checkpoint acknowledgement after the final role:

```bash
uv run aico-benchmark collect-aico-takeover-im \
  --contract /private/new-run/contract.json \
  --tasks benchmarks/boss-absent-v1/tasks.json \
  --task-id <task-id> \
  --state /private/new-run/aico/<task>/state.json \
  --exchange-dir /private/new-run/aico/<task>/takeover-im \
  --output /private/new-run/aico/<task>/takeover-ack.json \
  --owner-id <exact-owner-sender-id> \
  --target-id <exact-private-chat-id> \
  --request-expires-at <timezone-aware-iso8601> \
  --max-wait-seconds 900 \
  --exclusive-channel
```

The resulting receipt binds the terminal checkpoint, request, platform/inbound ACKs, owner identity fingerprint, effective action count and elapsed
seconds. Raw chat and sender identifiers remain only in process configuration, not score artifacts.

## Score a completed run

The independent harness first converts its owner-only observation ledger into the bounded scenario receipt:

```bash
uv run aico-benchmark finalize-aico-observations \
  --contract /private/new-run/contract.json \
  --tasks benchmarks/boss-absent-v1/tasks.json \
  --project-config benchmarks/boss-absent-v1/project.json \
  --observations /private/new-run/aico/<task>/observations.json \
  --output /private/new-run/aico/<task>/scenario-evidence.json
```

The ledger is built from actual fixture bytes, 0600 role artifacts/dispatch receipts, process generation, approval target generation, external
acceptance/test receipts, provider usage, takeover ACK and terminal consumption. Reconstructing flags in a hand-written JSON receipt is not a formal
observation. Before appending an AICO task result, bind the durable role state to that receipt:

```bash
uv run aico-benchmark finalize-aico \
  --contract /private/new-run/contract.json \
  --tasks benchmarks/boss-absent-v1/tasks.json \
  --state /private/new-run/aico/<task>/state.json \
  --scenario-evidence /private/new-run/aico/<task>/scenario-evidence.json \
  --output /private/new-run/aico/<task>/result.json
```

The finalizer does not trust `role_chain_complete` as task completion. It independently binds the terminal consumer, distinct agents, shared usage,
restart/no-replay, approval fence, drift handling, source pressure, IM takeover, and five evidence proofs. Its receipt must come from the external
harness; a fixture or system-under-test self-report is not a formal result.

```bash
uv run aico-benchmark score \
  --contract /private/new-run/contract.json \
  --tasks benchmarks/boss-absent-v1/tasks.json \
  --results /private/new-run/task-results.jsonl \
  --output-dir /private/new-run/scored
```

Exit `0` means every win gate passed. Exit `1` is a valid, evidence-backed non-win. Exit `2` means the artifacts are invalid, drifted, duplicated,
oversized, or unsafe to score.

## No-model artifact dry-run

```bash
uv run aico-benchmark dry-run \
  --contract /private/new-run/contract.json \
  --tasks benchmarks/boss-absent-v1/tasks.json \
  --output-dir /private/new-run/synthetic
```

This emits bounded `scenario-events.jsonl`, ten task results, and scored reports using equal perfect fake observations for both systems. Successful
execution returns `0`, while the embedded verdict is deliberately `aico_wins=false` with zero strictly better metrics. It proves schema, event
sequencing, artifact writing, and scorer wiring. It also starts one helper process per system, waits for a durable checkpoint, terminates that process,
and verifies exact-checkpoint resume in a new process; the process-probe receipt SHA replaces the synthetic restart hash. This still tests a fake
helper, not AICO or Codex Goal itself. The other scenario observations remain synthetic, and none of these files may be used as a formal result.

## Result recording contract

Each JSONL line identifies one system/task pair and binds the canonical SHA-256 of the frozen contract. `dispatched=false` may only report an
`incomplete` terminal state and cannot claim usage, checkpoints, takeover, restart, or approval observations. Every evidence category is one of:

- `present`: independently reviewable receipt exists and its SHA-256 is recorded;
- `failed`: an attempted check failed and the failure receipt SHA-256 is recorded;
- `missing`: no reviewable observation exists, so no SHA-256 is allowed.

Missing tasks remain in completion and evidence denominators. Missing provider usage and usage above the shared contract limit count as budget loss.
Missing takeover evidence receives the configured action/seconds penalty. A checkpoint counts only when its required role, artifact SHA-256, and
valid downstream consumer are all present.

The scorer additionally requires AICO to dispatch and complete every task, finish every required collaboration, record zero budget loss, provide
full evidence for complete samples, and show restart, IM takeover, and approval evidence. Relative superiority alone cannot produce a win.
