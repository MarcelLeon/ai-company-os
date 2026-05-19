# Notes CLI

Notes CLI is a tiny local notes app used by the AI Company OS Release Room demo.

The project is intentionally small so an AI team can realistically complete a v0.2
release during a demo.

## Current Usage

```bash
python -m notes_cli --store notes.json add "Ship the demo"
python -m notes_cli --store notes.json list
python -m notes_cli --store notes.json done 1
```

## v0.2 Release Goal

The release-room team should add:

- `add --tag <tag>` support.
- `search <query>` for text and tag search.
- `export --format json`.
- A non-zero exit code when `done <id>` references a missing note.
- README, CHANGELOG, and release notes updates.

See [`issues/003-v02-release.md`](issues/003-v02-release.md).

