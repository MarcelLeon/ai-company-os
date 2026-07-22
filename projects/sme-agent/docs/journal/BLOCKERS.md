# BLOCKERS.md

## B-001 — Real AICO project-office sample needs one human Telegram message sequence

**Status**: Waiting for human IM sample
**Observed**: The previously recorded SME runtime/state evidence is stale (last updated 2026-06-24), and this shell has no confirmed current bot token/runtime. A read-only attempt to use Telegram Web was rejected by the active browser safety policy because this task must not use Telegram Web; no alternate browser, Bot API, raw CDP, or credential-store workaround was attempted.

**Resolution**: start the SME-configured runtime through the documented runbook, then from the user's Telegram phone/client send `/use project sme-agent`, `/team`, `/inbox`, and `/proposals`. Accept or reject the candidate and inspect `/morning`; then send one bounded Lead request if deeper task/trace evidence is desired.

**Workaround**: deterministic tests and a real-config temporary-SQLite dogfood prove proposal generation, persistence, and no execution-before-accept. Do not claim the runtime is currently running or the real IM sample complete.

Deferred product decisions:

- Authentication and tenant isolation require a concrete deployment target.
- Persistent metadata storage choice waits for the Phase 1 query and write patterns.
- Embedding, reranking, and model providers wait for an evaluation dataset and budget.

## B-002 — Xiaohongshu desktop web blocks public note comment follow-up

**Status**: Waiting for App/manual comment surface
**Observed**: After the first SME Agent Xiaohongshu note passed review, Creator Center exposed the title, created time, metrics, and note id `6a4cba32000000001603fd2f`. Opening `https://www.xiaohongshu.com/explore/6a4cba32000000001603fd2f` in desktop web redirects to an App-scan page with `当前笔记暂时无法浏览`, and the Creator Center note card did not expose a safe comment input.

**Latest check**: 2026-07-09 10:00 heartbeat confirmed the desktop public URL still redirects to the App-scan page. Creator Center note management shows 10 views and 0 comments, but still no browser comment input.

**Impact**: The note is published and measurable, but the prepared first comment cannot be added by the current browser automation path.

**Resolution**: Add the prepared first comment from Xiaohongshu App or a Creator Center comment entry if one becomes available. After adding it, update `docs/commercialization/launch-execution-log.md` and start recording any comments, DMs, WeChat adds, field submissions, or paid intent in `docs/commercialization/lead-log-template.md`.

**Workaround**: A five-day Codex heartbeat follow-up named `SME Agent 小红书首帖跟进` will continue to check Creator Center metrics and lead signals from 2026-07-08.
