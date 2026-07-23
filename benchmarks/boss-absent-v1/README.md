# Boss-Absent v1 Frozen Task Set

This directory contains the tracked task contract for the first AICO vs Codex Goal comparison. It is not a benchmark result.

Canonical `tasks.json` SHA-256: `cb4898fed0a958a5778dd8744bbe910c2e179a3918a03153ed07cabd14ef9f34`.
The `freeze` command recomputes this fingerprint; this line is review help, not scoring authority.

## Harness protocol

Each system receives a clean checkout at the same Git revision, the same model and reasoning effort, the exact task object, the same wall window,
and one shared total-token ceiling. AICO role calls share that ceiling; they do not receive a budget per role.

AICO real role transport follows ADR-0096. The frozen exact model and reasoning effort are carried in preauthorized Task metadata and enforced
by the Adapter before dispatch; the Codex Adapter emits both as CLI arguments/config. Roles run through the production TaskBus contract, read provider
usage, write owner-only content-addressed artifacts and durable dispatch receipts, and recover by stable dispatch ID. A configured `agent_id` is only
runtime identity until the formal collector also binds project assignment and independent provider-session evidence.

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

## Score a completed run

Before appending an AICO task result, bind the durable role state to the independent harness receipt:

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
