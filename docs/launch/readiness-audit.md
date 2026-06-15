# Launch Readiness Audit — AI Company OS

> Purpose: keep public launch claims tied to current evidence. This file is an audit
> ledger, not marketing copy. If a claim cannot be proven from current repo state,
> test output, or live GitHub state, keep it out of public launch text.

## Audit Scope

- Workspace: `/Users/wangzq/VsCodeProjects/ai-company-os`
- Branch: `main`
- Audit window: 2026-06-15 local release-candidate pass.
- Important caveat: local gates prove only the current workspace state. GitHub Actions
  proves a release candidate only after the same changes are committed, pushed, and the
  CI run for that pushed commit succeeds.

## Evidence Collected

| Area | Evidence | Result | Public wording allowed |
|---|---|---:|---|
| No-token demo | `uv run aico-release-room-demo` | Pass | “30-second no-token Release Room demo” |
| Full local tests | `uv run pytest -q` | `428 passed, 1 skipped` | “428 unit tests passing locally” |
| Phase 8 contract gate | `docs/playbooks/phase-8-absence-loop.md` gate | `41 passed` | “machine gate covers absence-loop contracts” |
| Lint | `uv run ruff check .` | Pass | “ruff release gate passes locally” |
| Formatting | `uv run ruff format --check .` | Pass | “format gate passes locally” |
| Types | `uv run mypy src tests` | Pass | “mypy gate passes locally” |
| Diff hygiene | `git diff --check` | Pass | “no whitespace errors in current diff” |
| Latest pushed CI | `gh run list` / `gh run view` | live status must be checked against the current release-candidate HEAD before tagging | “CI is configured”; require a fresh current-HEAD CI success before release |
| Chinese article pack | Markdown link check + draw.io XML parser | Pass | “Chinese launch materials are prepared” |
| GitHub visibility | `gh repo view ... --json visibility` | `PUBLIC` | “repository is public” |
| GitHub About metadata | `gh repo view ... --json description,homepageUrl,repositoryTopics` | description, homepage, and 19 recommended topics are configured | “GitHub About metadata is configured” |
| GitHub social preview | `gh repo view ... --json openGraphImageUrl` + downloaded OG image | still GitHub default repository card, not `docs/assets/social-preview.png` | do not claim custom social preview is live yet |

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

## Release Notes Rules

- Prefer durable counts over brittle exact journal counts. “150+ documented development
  rounds” survives final pre-release work better than an exact number that changes every round.
- Keep exact test count only when it was run in this launch audit window.
- If a new PITFALL is added before release, update the PITFALLS index claim or remove that line.
- Do not say “CI green” for uncommitted changes. Say local gates passed, then require CI after push.

## Before Tagging `v0.1.0`

1. Commit the current launch/docs/test changes.
2. Push `main`.
3. Wait for GitHub Actions CI on the pushed commit to complete successfully.
4. Record the pushed commit SHA and CI result in `STATUS.md` / `ROUNDS.md`.
5. Re-run or spot-check the no-token demo from a clean checkout.
6. Have the repository owner confirm GitHub UI:
   - visibility is public (live audit already confirmed `PUBLIC`),
   - description and topics match `docs/human/github-publication.md` (live audit confirmed configured metadata),
   - `docs/assets/social-preview.png` is uploaded as Social preview (live audit still shows GitHub default OG card).
7. Only then create and push `v0.1.0`, using `docs/launch/v0.1.0-release-notes.md`.

## Current Go / No-Go

**Go for local RC quality**: yes. Local tests, lint, types, Phase 8 gate, no-token demo,
article links, and diagram XML all pass.

**Go for public release**: almost, but not yet. The repository is public and metadata is
configured, but the GitHub social preview is still the default repository card. The owner
still needs to upload `docs/assets/social-preview.png` before tag / Release.
