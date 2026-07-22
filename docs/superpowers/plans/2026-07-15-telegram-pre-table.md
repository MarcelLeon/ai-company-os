# Telegram Native Pre Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send compact table rows as one Telegram HTML `<pre>` block while preserving inline code and `/view` lazy details.

**Architecture:** Keep table detection and width control in the existing platform-neutral renderer. Add a Telegram Channel mapping rule that groups adjacent full-line code spans into one preformatted block; isolated code spans continue to map to `<code>`.

**Tech Stack:** Python 3.11, Pydantic message models, httpx MockTransport, pytest, Ruff, mypy.

## Global Constraints

- No new dependencies.
- No business-copy or language rewrite.
- No raw Markdown pipe table in Telegram payloads.
- Table content must be HTML-escaped before entering `<pre>`.
- Full-line code grouping requires at least two adjacent lines; inline code remains `<code>`.
- Existing class and method size limits remain enforced.

---

### Task 1: Telegram Payload Golden

**Files:**
- Modify: `tests/unit/test_telegram_channel.py`
- Test: `tests/unit/test_telegram_channel.py`

**Interfaces:**
- Consumes: `agent_output_message(text: str) -> MessageContent`
- Produces: failing payload assertions for one `<pre>` table block and external `<code>/view</code>`

- [x] **Step 1: Write the failing tests**

Update compact and wide table payload tests to assert:

```python
assert payload["text"].count("<pre>") == 1
assert payload["text"].count("</pre>") == 1
assert "<pre>Option" in payload["text"]
assert "<code>Option" not in payload["text"]
assert "<code>/view</code>" in payload["text"]
```

- [x] **Step 2: Run tests to verify red**

Run: `uv run pytest tests/unit/test_telegram_channel.py -k 'table' -q`

Expected: FAIL because the current payload emits a separate `<code>` tag for every table row.

### Task 2: Group Full-Line Code Spans

**Files:**
- Modify: `src/aico/channel/telegram.py`
- Test: `tests/unit/test_telegram_channel.py`

**Interfaces:**
- Consumes: `MessageContent.text` and ordered `MessageTextSpan` values
- Produces: `_html_text(content: MessageContent) -> str` with Telegram `<pre>` grouping

- [x] **Step 1: Add minimal grouping helpers**

Add focused private helpers that identify a run of two or more `CODE` spans where every span covers
a complete line and adjacent spans are separated by exactly one newline. Escape the entire run and
wrap it once with `<pre>`.

- [x] **Step 2: Preserve existing span behavior**

Keep bold, italic, isolated code, overlapping-span rejection, native HTML, and inline action payload
behavior unchanged.

- [x] **Step 3: Run the red tests to verify green**

Run: `uv run pytest tests/unit/test_telegram_channel.py -k 'table or renders_text_spans' -q`

Expected: PASS.

### Task 3: Regression And Quality Gates

**Files:**
- Modify: `tests/unit/test_telegram_ux_regression.py` only if a visual contract assertion is missing
- Modify: `CHANGELOG.md`
- Modify: `STATUS.md`
- Modify: `docs/journal/ROUNDS.md`
- Modify: `docs/journal/PITFALLS.md` if the `<code>` versus `<pre>` distinction is not already recorded

**Interfaces:**
- Consumes: final renderer and Telegram payload behavior
- Produces: durable regression evidence and project handoff records

- [x] **Step 1: Run targeted Telegram gates**

Run:

```bash
uv run pytest tests/unit/test_telegram_ux_regression.py tests/unit/test_message_rendering.py tests/unit/test_native_output.py tests/unit/test_telegram_channel.py -q
```

- [x] **Step 2: Run full repository gates**

Run:

```bash
uv run pytest -q
uv run mypy src tests
uv run ruff check src/aico/channel/telegram.py tests/unit/test_telegram_channel.py
uv run ruff format --check src/aico/channel/telegram.py tests/unit/test_telegram_channel.py
git diff --check
```

- [x] **Step 3: Run a real Telegram Web sample**

Start the current runtime, send one real inbound command, then use the production
`agent_output_message -> TelegramChannel -> Bot API` path for a deterministic table sample. Confirm
the new Bot API send event and inspect the new Telegram Web bubble. Evidence must come from the newly
sent message, not old history.

- [x] **Step 4: Record exact evidence**

Update `STATUS.md` and `docs/journal/ROUNDS.md` with red/green results, payload proof, real-client
result, and any remaining risk. Update `PITFALLS.md` only if this run establishes a new reusable pitfall.
