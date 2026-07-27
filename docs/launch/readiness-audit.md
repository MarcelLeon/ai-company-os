# Launch Readiness Audit — AI Company OS

> Purpose: keep public launch claims tied to current evidence. This file is an audit
> ledger, not marketing copy. If a claim cannot be proven from current repo state,
> test output, or live GitHub state, keep it out of public launch text.

## Audit Scope

- Workspace: `/Users/wangzq/VsCodeProjects/ai-company-os`
- Branch: `codex/aico-closeout`
- Audit window: 2026-07-27 personal HOTL release-candidate closeout.
- Important caveat: local gates prove only the current workspace state. GitHub Actions
  proves a release candidate only after the same changes are committed, pushed, and the
  CI run for that pushed commit succeeds.

## Evidence Collected

| Area | Evidence | Result | Public wording allowed |
|---|---|---:|---|
| No-token demo | `uv run aico demo` | blocked by the same user-owned zero-byte Release Room config | no runnable-demo claim until the config decision and clean-checkout rerun |
| Full local tests | `uv run pytest -q` | `3 failed, 1187 passed, 1 skipped`; all 3 failures come from the user-owned zero-byte `examples/release-room/aico-project.json` | no passing-suite claim until the owner restores or intentionally replaces that file |
| Isolated unaffected suite | full suite with the exact 3 affected node IDs deselected | `1187 passed, 1 skipped, 3 deselected` | only use as diagnosis, not as the final release claim |
| Phase 8 contract gate | `docs/playbooks/phase-8-absence-loop.md` gate | `41 passed` | “machine gate covers absence-loop contracts” |
| Lint | `uv run ruff check .` | Pass | “ruff release gate passes locally” |
| Formatting | `uv run ruff format --check .` | Pass | “format gate passes locally” |
| Types | `uv run mypy src tests` | Pass | “mypy gate passes locally” |
| Diff hygiene | `git diff --check` | Pass | “no whitespace errors in current diff” |
| Latest pushed CI | `gh run list` / `gh run view` | live status must be checked against the current release-candidate HEAD before tagging | “CI is configured”; require a fresh current-HEAD CI success before release |
| Chinese article pack | Markdown link check + draw.io XML parser | Pass | “Chinese launch materials are prepared” |
| GitHub visibility | `gh repo view ... --json visibility` | `PUBLIC` | “repository is public” |
| GitHub About metadata | `gh repo view ... --json description,homepageUrl,repositoryTopics` | description, homepage, and 19 recommended topics are configured | “GitHub About metadata is configured” |
| GitHub social preview | `uv run aico-github-social-preview` + exact remote/local SHA-256 comparison + visual check | latest HOTL image is live at `1280 x 640`, 49,393 bytes; remote and local SHA-256 both equal `0eab69510c4ed81c207bd7831b1282f89c062ef6f3e6f63f8c6fabd4258c517c`; status is `ok` | “the personal HOTL social preview is live” |

## Claim Boundaries

| Claim | Status | Notes |
|---|---|---|
| Telegram is the primary stable control plane | Supported | README and launch text can say Telegram today. |
| Feishu is stable public control plane | Not yet | Feishu first slice is implemented, but production callback smoke is still pending. |
| AICO is a sandbox | False | AICO is approval + audit + capability gate in front of local CLIs. |
| AICO is cloud-only or laptop-free | False | AICO controls local AI CLIs on the developer’s machine. |
| OpenClaw/company CLI adapter is implemented | False | Public text may say future/internal CLIs can implement the Adapter contract. |
| `/overnight` is a complete autonomous scheduler | Not yet | Current public wording should say offline delegation / first absence-loop slice. |
| `/view` is a full default web console | Not yet | Current public wording should say read-only HTML snapshot via IM when enabled. |
| Multi-agent framework replacement | False | Wedge is operations for local agents, not agent authoring/runtime replacement. |
| Enterprise multi-tenant control plane | False | AICO is personal and local-first: one developer operates agents on their own computer. |

## Release Notes Rules

- Prefer durable counts over brittle exact journal counts. “270+ documented development
  rounds” survives final pre-release work better than an exact number that changes every round.
- Keep exact test count only when it was run in this launch audit window.
- If a new PITFALL is added before release, update the PITFALLS index claim or remove that line.
- Do not say “CI green” for uncommitted changes. Say local gates passed, then require CI after push.

## Before Tagging `v0.1.0`

1. Commit the current launch/docs/test changes. (Completed locally in Round 274; push/merge remains pending.)
2. Push `main`.
3. Wait for GitHub Actions CI on the pushed commit to complete successfully.
4. Record the pushed commit SHA and CI result in `STATUS.md` / `ROUNDS.md`.
5. Re-run or spot-check the no-token demo from a clean checkout.
6. Have the repository owner confirm GitHub UI:
   - visibility is public (live audit already confirmed `PUBLIC`),
   - description and topics match `docs/human/github-publication.md` (live audit confirmed configured metadata),
   - the new `docs/assets/social-preview.png` is uploaded as Social preview (completed and visually checked in Round 274).
7. Run `uv run aico-github-social-preview`; it must not return `status: needs-owner-upload` (completed with `status=ok`).
8. Only then create and push `v0.1.0`, using `docs/launch/v0.1.0-release-notes.md`.

## Current Go / No-Go

**Go for local RC quality**: not yet. The unaffected test suite, Ruff check, mypy and
targeted HOTL prompt tests pass, but the user-owned zero-byte Release Room config keeps
the full suite and no-token demo red. The file has deliberately not been overwritten.

**Go for public release**: no. The repository is public and the new HOTL preview is live,
but `codex/aico-closeout` has not been pushed/merged to `main`, current-head CI has not
run, and the full test/demo gate is not green.
