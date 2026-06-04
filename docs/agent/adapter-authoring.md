# Adapter Authoring Guide

> Connect any local AI CLI — Cursor, Aider, OpenClaw, an internal company tool — to AICO
> as a first-class team member. This guide walks through the contract, the minimal
> implementation, registration, and how AICO routes work to your adapter.

## Why a separate adapter

AICO's core never branches on tool identity. There is no `if tool == "cursor"` anywhere
in the orchestrator, channel, or memory layers. New AI tools enter the system by
implementing the [`AIAdapter`](../../src/aico/adapter/base.py) Protocol — same contract,
same approval gate, same audit trail, same project memory.

This is what makes AICO an "AI company OS" rather than an N+1 wrapper: every adapter
shows up in `/agents`, can be appointed to a role with `/appoint <agent> as <role>`, and
runs under the same approval/audit/interrupt rules.

## The contract

```python
# src/aico/adapter/base.py
@runtime_checkable
class AIAdapter(Protocol):
    @property
    def name(self) -> str: ...

    def capabilities(self) -> frozenset[Capability]: ...

    async def receive_task(self, task: Task) -> TaskAck: ...

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]: ...

    def status(self) -> AdapterStatus: ...

    async def interrupt(self, task_id: str) -> None: ...

    async def health_check(self) -> HealthStatus: ...
```

### Method-by-method

| Method | What you do | What AICO expects |
|---|---|---|
| `name` | Return a stable lowercase identifier (e.g. `"cursor"`, `"openclaw"`) | Used everywhere — `/agents`, audit, persona aliases |
| `capabilities` | Return the set of [`Capability`](../../src/aico/core/models.py) flags your CLI supports | Used by risk gating: a `read_only` adapter cannot accept a `shell_exec` task |
| `receive_task(task)` | Validate, queue, or reject. Return `TaskAck(status=ACCEPTED \| BUSY \| REJECTED)` | If `BUSY`, AICO will surface "all slots taken" to the user |
| `stream_output(task_id)` | Async-yield `TaskOutput(type=TEXT \| STATUS \| ERROR \| DONE, content=...)` chunks | AICO streams these to IM. End with `DONE` (or `ERROR`) so the task transitions |
| `status` | Return current `AdapterStatus` (`IDLE`/`BUSY`/`BLOCKED`/`WAITING_APPROVAL`/`OFFLINE`) | Shown in `/status` and `/agents` |
| `interrupt(task_id)` | Best-effort cancel the underlying CLI / task | Called when the user runs `/interrupt <task_id>` |
| `health_check` | Quick CLI/network check | Surfaced via `aico-glance` and runtime startup |

### Capability flags and risk

`Capability` declares **what your CLI can do**, not what it must do for every task:

- `CODE_REVIEW` — read repo, summarize, propose changes (no writes)
- `CODE_EDIT` — write files
- `SHELL_EXEC` — execute shell commands
- `LONG_RUNNING` — task may exceed 30s
- `STREAM_OUTPUT` — supports incremental chunks
- `INTERRUPTIBLE` — supports cancellation

A read-only adapter (only `CODE_REVIEW`) is automatically rejected for tasks the risk
assessor classified as `WRITE_FILES` or higher. Lying about capabilities is a security
issue, not just a UX bug.

## Minimal real adapter — Cursor

The shortest real adapter in this repo is [`cursor.py`](../../src/aico/adapter/cursor.py)
— ~70 lines, reusing `ClaudeCodeAdapter`'s subprocess machinery:

```python
from aico.adapter.claude_code import ClaudeCodeAdapter
from aico.core.models import Capability, Task

DEFAULT_CURSOR_COMMAND = ("cursor-agent", "-p", "--force", "--output-format", "text")

class CursorAdapter(ClaudeCodeAdapter):
    def __init__(self, *, command=DEFAULT_CURSOR_COMMAND, cwd=None, ...):
        super().__init__(adapter_name="cursor", command=command, cwd=cwd, ...)

    def capabilities(self) -> frozenset[Capability]:
        return frozenset({
            Capability.CODE_EDIT, Capability.CODE_REVIEW,
            Capability.SHELL_EXEC, Capability.LONG_RUNNING,
            Capability.STREAM_OUTPUT, Capability.INTERRUPTIBLE,
        })

    def _command_for_task(self, task: Task) -> tuple[str, ...]:
        # Customize per-task argv; can read provider session from task metadata
        ...
```

If your CLI is also a stdin-fed subprocess that streams stdout text, subclass
`ClaudeCodeAdapter`. If not (HTTP API, embedded library, etc.), implement `AIAdapter`
directly — see `claude_code.py` for the canonical reference.

## Registering your adapter

Adapters are wired into the runtime in
[`src/aico/app/phase1.py`](../../src/aico/app/phase1.py). The pattern:

1. Add an env flag (e.g. `AICO_ENABLE_MYTOOL_ADAPTER=true`) to `Phase1Settings`.
2. In `build_phase1_runtime`, instantiate your adapter when the flag is set.
3. Register it with [`AdapterRegistry`](../../src/aico/core/adapter_registry.py)
   alongside the existing adapters.
4. Optionally add a default persona/alias so users can say `/ask mytool ...` or
   `@mytool review this`.

Optional adapters MUST default to off. AICO's promise is that nothing risky runs without
the user opting in.

## Provider sessions (resume)

If your CLI supports session resume (Claude Code's `--resume <id>`, Codex's
`exec resume`), use [`provider_session_from_task(task)`](../../src/aico/core/agent_session.py)
to read AICO's session intent from task metadata, and emit the right argv.

If your CLI does not support resume, ignore it — AICO will fall back to fresh prompts
without breaking anything.

## Testing your adapter

Every adapter ships with mock-based unit tests covering:

- Default command shape (no surprise argv)
- Capability declarations
- Streaming output ordering and `DONE`/`ERROR` termination
- `interrupt()` actually cancels the subprocess (or HTTP call)
- Provider session resume (if supported)
- Working directory / cwd injection

See [`tests/unit/test_cursor_adapter.py`](../../tests/unit/test_cursor_adapter.py) for a
template. Don't spawn the real CLI in unit tests — use a `ProcessFactory` fake. End-to-end
verification belongs in a manual smoke test under
[`docs/playbooks/optional-agent-adapters.md`](../playbooks/optional-agent-adapters.md).

## Hard rules (will block your PR)

- Single class < 500 lines, single method < 100 lines.
- No core code edits — your adapter is a new file in `src/aico/adapter/`, plus a registry
  entry in `phase1.py`. Anything else is over-scope.
- Capabilities must be honest. If your CLI cannot edit files, do not include `CODE_EDIT`.
- Default off. New adapters are opt-in via env flag.
- Tests + docs + journal entry. See [`08-self-update-protocol.md`](08-self-update-protocol.md).

## Asking for help

- Open a [Discussion](https://github.com/MarcelLeon/ai-company-os/discussions) with the
  `adapter` label if the contract feels wrong for your tool — don't bend the contract
  silently in a fork. Capability/contract gaps are exactly the kind of feedback that
  reshapes ADRs.
- File an issue from the
  [adapter request template](../../.github/ISSUE_TEMPLATE/feature_request.yml) for
  concrete tool requests; the template prompts for the CLI shape and capability matrix
  AICO needs.
