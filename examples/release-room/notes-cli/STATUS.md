# STATUS.md

**Project**: Notes CLI
**Current target**: v0.2 release
**State**: Planning

## v0.1 Done

- Add notes from the command line.
- List notes.
- Mark notes as done.
- Store notes in a local JSON file.

## v0.2 Scope

- Add optional tags when creating a note.
- Search notes by text or tag.
- Export notes as JSON.
- Fix `done <id>` so unknown ids fail with a non-zero exit code.
- Update README, CHANGELOG, and release notes.
- Convert `tests/test_v02_contract.py` from skipped release contracts into passing tests.

## Acceptance

- `python -m pytest` passes from this directory.
- README shows first-time usage for add/list/search/export/done.
- CHANGELOG has Added / Fixed / Changed / Verification sections for v0.2.
- Release notes summarize done, blocked, risks, and next actions.

