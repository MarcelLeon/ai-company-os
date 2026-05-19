# Issue 003: v0.2 Release

## User Story

As a developer using Notes CLI as a local scratchpad, I want to tag, search, and
export notes so I can use the CLI in scripts and small release workflows.

## Scope

- Add optional tags to `add`.
- Add `search <query>` across note text and tags.
- Add `export --format json`.
- Fix `done <id>` so missing ids return a non-zero exit code.
- Update README, CHANGELOG, and release notes.

## Acceptance Criteria

- Existing v0.1 tests still pass.
- v0.2 contract tests are no longer skipped and pass.
- JSON export includes `id`, `text`, `done`, `tags`, and `created_at`.
- Search supports both text search and tag search.
- README can be followed by a first-time user.

## Collaboration Notes

- PM owns scope and release plan.
- Implementer owns code and docs changes.
- Tester owns regression strategy and test execution.
- Reviewer owns risk and maintainability review.
- Release manager owns final notes and handoff.

