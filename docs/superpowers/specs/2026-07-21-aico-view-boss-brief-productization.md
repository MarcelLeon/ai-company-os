# AICO View Boss Brief Productization

## Context

`/view` already sends a self-contained read-only HTML attachment into IM. Its
first screen currently leads with generic event/memory counts and the latest
event, then quickly falls into recent tasks and Timeline. That is an observability
page, not yet the secretary-style recovery surface promised by the absence-first
product contract.

The current roadmap explicitly requires the first screen to prioritize pending
decisions, blockers, overnight handoffs, and the boss's first action. Inspection
also found a stricter risk: task/audit data was loaded globally while the HTML
title named one project, so a project snapshot could include another project's
task description or timeline event.

## User outcome

After `/view <project>`, the boss opens one HTML attachment and can answer in the
first viewport:

1. Is a decision waiting for me?
2. What is blocked?
3. What happened overnight?
4. What single action should I take first?

The boss can jump back to IM through command links; no write action occurs in
the HTML and no other project's data appears.

## Scope

- Project-scope task records/snapshots, audit events, memory, and overnight
  delegation records before rendering.
- Replace generic first-screen emphasis with approval/blocker/running/overnight
  counts, a single first-action card, and compact attention cards.
- Preserve recent tasks, Timeline, Trace, and Memory as lower detail layers.
- Keep provider session IDs summarized and HTML escaped.
- Keep `/view` as a self-contained IM attachment with no localhost/external CSS.
- Desktop and 390-pixel mobile rendered QA plus command-link interaction.

## Non-goals

- No write API, auto-approval, auto-send-on-project, public tunnel, or new web
  server behavior.
- No LLM-generated summary; first-screen priority remains deterministic.
- No persistence of full provider output or replacement of `/task` as the exact
  trace surface.
- No Feishu attachment implementation in this round.

## Acceptance

1. Pending approval outranks failed/running/overnight work as First action and
   exposes `/approve`, `/reject`, and `/task` links.
2. Without approval, blocker outranks running and overnight; empty state routes
   to `/inbox` and `/morning`.
3. First-screen cards show current-project approvals, blockers, and overnight
   records before `recent tasks` and `recent timeline`.
4. Overnight cards include goal, lead role/agent, task status, and review count.
5. Another project's task payload, failure reason, audit event, memory, and
   overnight goal do not appear in the attachment.
6. Existing self-contained/document delivery, session-ID redaction, task detail,
   trace, and memory contracts remain green.
7. Desktop/mobile DOM, screenshot, console, overflow, and one deep-link click are
   verified through the Browser plugin.
8. Targeted/full tests, Ruff, mypy, structure scan, and continuity records pass;
   unrelated existing format debt remains explicitly separated.

## Decision

Reuse SQLite task/offline-delegation truth and deterministic status priority.
Do not introduce another dashboard state store or summary agent. The snapshot is
a disposable, project-scoped projection; IM remains the write surface.

## Round 197 verification status

- Acceptance 1-6 are covered by deterministic unit/integration tests.
- Targeted snapshot/view/offline-delegation regression: 22 passed; full root:
  546 passed and 1 skipped. Ruff, mypy, touched format, structure, and diff
  checks pass. Full-root format retains one unrelated pre-existing data-agent
  file that this round did not touch.
- Browser plugin rejected the local `file://` attachment by URL policy. The
  session was finalized without a localhost or alternate-browser workaround.
  Acceptance 7 remains open as B-009; it must not be reported as visually
  verified until a policy-allowed real attachment target is available.
