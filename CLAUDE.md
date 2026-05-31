# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

AI Company OS (AICO) is an "absence-first" remote control layer that lets a developer
manage local AI CLIs (Claude Code, Codex, Cursor, CodeFlicker, Trae, Gemini, …) as a
project team from IM (Telegram primary, Feishu in progress). It is **not** a chat UI or a
single-agent wrapper. Risky local actions go through approval/audit; project state lives
in JSONL/SQLite so it survives restarts.

The product bet — and the way every PR must be justified — is captured in three sentences
in [`NORTH_STAR.md`](NORTH_STAR.md). If a change cannot be tied to one of those three
sentences, the change should be cut.

## Required reading order before coding

This repo is structured so any agent (human or AI) can pick up mid-project. **Do not skip
the journal — most "good ideas" have already been considered and rejected here.**

1. [`NORTH_STAR.md`](NORTH_STAR.md) — the three-sentence constitution. Every decision
   must be traceable to one of them.
2. [`STATUS.md`](STATUS.md) — current round, current phase, "next round suggested" list.
   This is the single source of truth for "what to do next".
3. [`docs/journal/ROUNDS.md`](docs/journal/ROUNDS.md) — what previous rounds tried and
   **why proposals were rejected**. Read this to avoid re-inventing rejected designs.
4. [`docs/journal/PITFALLS.md`](docs/journal/PITFALLS.md) — grep for keywords related to
   your task before writing code.
5. [`docs/journal/BLOCKERS.md`](docs/journal/BLOCKERS.md) — open blockers; resolving one
   is the highest-priority task you can take.
6. [`AGENTS.md`](AGENTS.md) — full agent SOP, hard rules, and self-check list.

For coding standards / patterns: [`docs/agent/02-coding-standards.md`](docs/agent/02-coding-standards.md),
[`docs/agent/03-design-patterns.md`](docs/agent/03-design-patterns.md),
[`docs/agent/05-python-best-practices.md`](docs/agent/05-python-best-practices.md),
[`docs/agent/06-testing-guide.md`](docs/agent/06-testing-guide.md).

When docs disagree, the precedence is:
`NORTH_STAR.md > STATUS.md > docs/decisions/ (ADR) > docs/journal/ > docs/agent/ > docs/architecture/ > code comments`.

## Hard rules (violating these gets work rejected)

- **Single class < 500 lines, single method < 100 lines.** Hard physical limit, not a
  guideline. Split when crossed.
- **Program to interfaces.** Adapters, channels, storage backends, persona/approval
  strategies must implement the published Protocol. Core code depends on the interface,
  never on a concrete class.
- **No `if tool == "claude_code"` style branching in core.** New capability = new plugin,
  not a core edit.
- **Don't widen task scope.** A bugfix PR doesn't refactor adjacent code; an adapter PR
  doesn't restructure the orchestrator.
- **Don't bury uncertainty in `// TODO` / `# TODO`.** Either link it to a `BLOCKERS.md`
  entry, or write `# TODO(B-001): ...` / `# TODO(@user, YYYY-MM-DD): ...`. Untraceable
  TODOs are treated as a code smell at review.
- **Every code change updates docs.** At minimum `STATUS.md` and
  `docs/journal/ROUNDS.md`. New pitfalls → `PITFALLS.md`. New unresolved blocker →
  `BLOCKERS.md`. Architectural decision → new ADR in `docs/decisions/`.
- **Tests required.** Core modules target ≥80% coverage; every Adapter and every
  Channel needs mock-based unit tests plus at least one integration test path.
- **No early abstraction.** Rule of three — copy/paste twice, abstract on the third
  occurrence. See `docs/agent/03-design-patterns.md`.
- **Communicate with the user in Chinese.** Code identifiers and inline comments stay in
  English; user-facing docs are bilingual where it matters.

## Common commands

Python 3.11+ with `uv` is the only supported toolchain. Examples assume the repo root.

```bash
# Install / sync (locked deps + dev group)
env UV_CACHE_DIR=/tmp/aico-uv-cache uv sync --python 3.11

# Tests (pytest, asyncio_mode=auto, testpaths=tests)
uv run pytest                               # full suite
uv run pytest tests/unit/test_orchestrator.py            # one file
uv run pytest tests/unit/test_orchestrator.py::test_name # one test
uv run pytest -k "memory and not feishu"                 # by keyword

# Lint / format / types — these are what CI gates on (.github/workflows/ci.yml)
uv run ruff check .
uv run ruff format --check .   # use `ruff format .` to fix
uv run mypy src tests          # strict mode, see [tool.mypy] in pyproject.toml

# No-token deterministic demo (fake adapters, no Telegram/Claude/Codex calls)
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-release-room-demo

# Real Telegram runtime (needs the env vars below)
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-phase1

# Other CLI entry points (see [project.scripts] in pyproject.toml)
uv run aico-feishu-webhook   # Feishu channel webhook server
uv run aico-glance           # compact local status glance
uv run aico-metrics          # metrics CLI
uv run aico-state --db .aico/state.db   # inspect SQLite state; `reset --yes` clears AICO tables
```

Minimum env vars for the real Telegram runtime (full list in
[`docs/human/quickstart.md`](docs/human/quickstart.md)):

```
AICO_TELEGRAM_BOT_TOKEN
AICO_CLAUDE_WORKING_DIRECTORY
AICO_PERSONA_CONFIG_PATH=config/personas.example.json
AICO_PROJECT_CONFIG_PATH=config/projects.example.json
AICO_AUDIT_LOG_PATH=/tmp/aico-audit.jsonl
AICO_MEMORY_PATH=/tmp/aico-memory.jsonl
AICO_STATE_DB_PATH=/tmp/aico-state.db   # `true` maps to .aico/state.db
```

Optional adapters are off by default; enable per-adapter:
`AICO_ENABLE_CODEX_ADAPTER`, `AICO_ENABLE_CURSOR_ADAPTER`,
`AICO_ENABLE_CODEFLICKER_ADAPTER`, `AICO_ENABLE_TRAE_ADAPTER`,
`AICO_ENABLE_GEMINI_ADAPTER`.

## Architecture: the big picture

Three pluggable layers connected by an `EventBus`. Volatile platform/tool details stay
behind the layer boundary; core code only ever sees the abstract contract.

```
Human (IM)
   ↕
IM channel layer        src/aico/channel/      (telegram.py, feishu.py)        impl IMChannel
   ↕
Orchestration core      src/aico/core/         Router · TaskBus · Persona · Approval
                                               · Memory · Audit · ProjectAssignment
   ↕
AI adapter layer        src/aico/adapter/      (claude_code, codex, cursor,
                                                codeflicker, trae, gemini)    impl AIAdapter
   ↕
Local AI CLIs (subprocess)
```

Five abstractions you must understand before touching the orchestrator
([`docs/architecture/overview.md`](docs/architecture/overview.md) is the canonical map):

- `AIAdapter` — `src/aico/adapter/base.py`. Receives tasks, streams output, reports
  status, declares capabilities (`read_repo`, `code_edit`, `shell_exec`, `destructive`).
  Adding a new local AI CLI = new file in `src/aico/adapter/` + register in
  `core/adapter_registry.py` + persona/project config. Never edit core to special-case it.
- `IMChannel` — `src/aico/channel/base.py`. Parses inbound messages → events, sends/edits
  outbound. New channels must round-trip through the platform-neutral render contract
  (ADR-0013) and degrade gracefully (e.g. no message edit → fall back to new message).
- `TaskBus` + task state — `core/task_bus.py`, `core/task_state.py`, `core/task_store.py`,
  `core/sqlite_state.py`. State is observable, persisted, interruptible. Long tasks must
  be cancellable from a single IM command.
- `ProjectAssignmentDirectory` — `core/project_assignment.py`. Models project office /
  role / agent / appointment. **Sessions, prompts, working dir, capabilities bind to an
  appointment, not to an agent.** This is the layer the boss-facing commands
  (`/project`, `/team`, `/appoint`, `/lead`, `/ask`) talk to. See ADR-0011, ADR-0012.
- A2A Memory Fabric — `core/memory.py` + `core/memory_*.py`. Append-only JSONL, scope-bound
  (`boss / project / team / role / agent`); cross-team sharing only via `MemoryPacket` and
  `MemoryBroadcast`. Don't bypass scope. See ADR-0020 through ADR-0023, ADR-0027.

Dataflow worked example: a Telegram `/ask <role> <prompt>` enters `TelegramChannel`,
becomes an `IncomingMessage`, the `Router` resolves project/role/appointment via
`ProjectAssignmentDirectory`, `TaskBus` creates a Task, `Approval` gates risky
capabilities, the bound Adapter spawns the CLI, output streams back via `EventBus` to the
channel, and `Audit` writes a trace. The full trace is in `docs/architecture/overview.md`.

CLI entry points live in `src/aico/app/` and wire the layers together — read these to see
real composition without spelunking the core.

## Testing layout

```
tests/unit/      pure-Python unit tests, async via pytest-asyncio (asyncio_mode=auto)
tests/golden/    snapshot tests (e.g. metrics token rendering)
```

Conventions worth knowing:

- Adapters are tested with mocked CLI subprocesses; channels with mocked HTTP/SDK.
  Don't spin up a real Telegram bot or call a real Claude CLI in unit tests.
- Async mocks **must** use `unittest.mock.AsyncMock`, not `Mock`.
- Prefer Fakes (in-memory implementations) over deep `Mock` chains — Mocks bind to
  implementation details and rot fast.
- Test names follow `test_<method>_<expected behaviour>_<precondition>`.
- Phase acceptance tests live in `tests/unit/test_phase*_acceptance.py` — these are the
  end-to-end fixtures for each completed phase.

## Documentation update protocol

This is the most-skipped step and the most important one. After any code change:

| Change type | File to update |
|---|---|
| Any code change | `STATUS.md` (round +1, "next round" list) **and** `docs/journal/ROUNDS.md` (append round entry, **explain rejected alternatives**) |
| New pitfall hit | `docs/journal/PITFALLS.md` |
| Unresolved blocker | `docs/journal/BLOCKERS.md` (mark `RESOLVED` when fixed) |
| Architectural decision | new ADR in `docs/decisions/` |
| User-visible behaviour | `CHANGELOG.md` |
| New ops command | `docs/human/daily-ops.md` |

See [`docs/agent/08-self-update-protocol.md`](docs/agent/08-self-update-protocol.md) for
the exact templates.

## Commit & PR conventions

Conventional Commits, scoped to project areas:

```
<type>(<scope>): <subject>
```

- `type`: `feat | fix | docs | refactor | test | chore | adr`
- `scope`: `core | adapter | channel | persona | approval | journal | …`

Every PR body must answer: **"which sentence in `NORTH_STAR.md` does this serve, and
why?"** If none, close the PR. Self-check list lives in
[`CONTRIBUTING.md`](CONTRIBUTING.md).
