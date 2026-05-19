# Release Room Local Transcript

This transcript is the Stage 2 no-token preview of the Release Room demo. It is
generated from the same management path covered by `tests/unit/test_release_room_acceptance.py`,
with deterministic fake adapters standing in for Claude/Codex.

## 1. Enter The Project Office

```text
Boss> /use project release-room
AICO> Project office
      release-room [Notes CLI Release Room]
      phase: v0.2 release planning

Boss> /team
AICO> Team for release-room [Notes CLI Release Room]
      lead: pm -> claude
      - pm -> claude [lead]
      - implementer -> claude
      - tester -> codex
      - reviewer -> codex
      - release-manager -> claude
```

## 2. Set Team Memory

```text
Boss> /remember v0.2 不接受没有测试的功能。
AICO> Memory saved

Boss> /remember README 必须面向第一次使用 CLI 的开源用户。
AICO> Memory saved

Boss> /remember release notes 必须包含 Added / Fixed / Changed / Verification。
AICO> Memory saved
```

## 3. Split Work By Role

```text
Boss> /ask pm 阅读 STATUS.md 和 issues/003-v02-release.md，把 v0.2 拆成角色任务、验收标准和风险清单。
AICO> Task accepted: release-task-001 [claude]
Claude/PM> Release plan: implementer owns tags/search/export and bug fix; tester owns contract tests; reviewer owns behavior and docs risk; release-manager owns notes and go/no-go.
```

## 4. Approve Risky Implementation Work

```text
Boss> /ask implementer update src/notes_cli/__main__.py, README and CHANGELOG, then run pytest for v0.2.
AICO> Approval required: release-task-002
      mentions shell or command execution
      Send /approve to continue, or /reject to stop.

Boss> /approve
AICO> Task approved: release-task-002
Claude/Implementer> Implementation handoff: code, tests, README, CHANGELOG, and release notes are ready for independent checks.
```

## 5. Independent Verification

```text
Boss> /ask tester 检查 tests/test_v02_contract.py 的回归策略并报告失败项。
AICO> Task accepted: release-task-003 [codex]
Codex/Tester> Test report: v0.2 contract covers tags, search, JSON export, and unknown-id exit code.

Boss> /ask reviewer review v0.2 release risk, test gaps, README and CHANGELOG consistency.
AICO> Task accepted: release-task-004 [codex]
Codex/Reviewer> Review findings: no release until skipped contracts are enabled and docs match behavior.
```

## 6. Overnight Handoff

```text
Boss> /overnight 推进 v0.2 release room，早上给我 done/blocked/risks/next actions。
AICO> Overnight delegation queued: night-release-
      project: release-room [Notes CLI Release Room]
      lead: pm -> claude

Claude/PM> Morning handoff: done = release plan and checks staged; blocked = real CLI changes still require real adapter run; risks = skipped v0.2 contracts; next = implement, unskip, record release notes.
```

## 7. Morning Review

```text
Boss> /daily release-room
AICO> Boss summary
      - Done: PM, implementer, tester, reviewer, and overnight handoff tasks are visible.
      - Blocked: v0.2 contract tests are still skipped in the seed repo.
      - Risks: do not publish until tests are unskipped and passing.
      - Next actions: implement release, run tests, update release notes.

Boss> /tasks
AICO> Recent tasks: release-task-001 ... release-task-006

Boss> /metrics
AICO> Metrics (live)

Boss> /audit
AICO> Recent audit events: task_submitted, approval_requested, approval_approved, adapter_dispatched, task_completed.
```

