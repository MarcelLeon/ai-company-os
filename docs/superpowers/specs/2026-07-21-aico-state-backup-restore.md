# AICO State Backup, Verification, and Restore

**Status**: Complete — Round 211

## Goal Brief

**User outcome**: A personal-company operator must be able to back up the live AICO business-state
database without stopping the runtime, verify a stored artifact offline, and restore it without racing
an active runtime or silently accepting corruption or the wrong artifact.

**Decision owner**: Backup is read-only and may run while the runtime owns the database. Restore and
reset are destructive state mutations and must acquire the same kernel owner lock as AICO before any
mutation. The owner explicitly confirms restore/reset; the system never schedules them autonomously.

## In scope

- `aico-state --db <path> backup --output <backup.db>` using SQLite's online backup API so WAL-backed
  live state is copied as one transaction-consistent standalone database.
- Backup output must be a new path, differ from the source, use owner-only `0600` permissions, contain
  no WAL dependency, and be left only after integrity/schema verification succeeds.
- `aico-state --db <path> verify --backup <backup.db>` opens the artifact read-only, runs full SQLite
  `integrity_check`, reads schema version and known table counts without mutating the artifact, and
  prints artifact SHA-256 and byte size.
- Verification requires the current supported AICO state schema. No implicit migration or metadata
  rewrite is allowed during verify.
- `aico-state --db <path> restore --from <backup.db> --expected-sha256 <digest> --yes` verifies the
  exact selected bytes and current schema before touching the target.
- Restore acquires the canonical runtime owner lock non-blockingly and holds it through safety backup,
  replacement, stale WAL/SHM cleanup, and release. An active runtime fails closed.
- Existing target state is first copied to a timestamped owner-only pre-restore safety backup. If that
  safety backup cannot be created and verified, restore stops before replacement.
- Restore materializes the chosen artifact through SQLite backup into a same-directory temporary DB,
  verifies it, fsyncs it, atomically replaces the main DB, and removes stale target WAL/SHM while the
  owner fence remains held.
- Existing destructive `reset --yes` must acquire the same owner fence; summary/verify/backup remain
  read-only.
- Machine-readable compact JSON summaries for backup/verify/restore. They may contain artifact
  filenames, schema/count/size/SHA facts, but never database payloads, task prompts, tokens, exception
  text, owner-lock metadata, or absolute source paths.

## Out of scope

- Automatic scheduled backups, cloud upload, encryption/key management, remote object storage,
  retention deletion, or unattended restore.
- Backing up JSONL audit, project/persona Git files, `.env`, receiver state, logs, or generated view
  snapshots. The first slice covers the authoritative AICO SQLite business state only.
- Restoring while AICO is running, bypassing a busy owner lock, forcing recovery from an already
  corrupt current DB when a safety backup cannot be made, or deleting old safety backups.
- Cross-version migration. A backup from another schema must be restored by a future explicit
  migration workflow, not silently rewritten by verify/restore.
- Claiming a local backup is disaster recovery until an actual restore drill has been run against a
  disposable target and the artifact is stored outside the AICO Mac.

## Acceptance checks

1. Online backup succeeds while the source runtime owner lock is held and captures a consistent point
   in time; later source writes do not appear in the artifact.
2. Backup artifact is standalone, `0600`, current schema, integrity `ok`, and emits exact-byte SHA-256.
3. Existing output, source=output, missing source, corrupt artifact, unsupported schema, and SHA mismatch
   fail without changing target/output.
4. Verify is read-only: artifact bytes and SHA are identical before and after verification.
5. Restore round-trip replaces newer target state with backed-up state and creates a verified safety
   backup containing the pre-restore state.
6. Active runtime owner rejects restore and reset before any database mutation.
7. Restore failure releases its acquired owner fence and leaves the original target usable.
8. Restore removes stale target `-wal`/`-shm` only while holding the fence; a subsequent SQLite open
   sees exactly the restored state.
9. CLI requires `--yes` and expected SHA for restore, retains reset confirmation, and emits no payload,
   secret, exception detail, or absolute source path.
10. Full root/SME tests, Ruff, mypy, touched format, structure, CLI and diff gates pass.

## Completion evidence

- Targeted backup/CLI suite: `9 passed`.
- Full root suite: `685 passed, 1 skipped`; isolated SME suite: `53 passed`.
- Ruff passed; mypy passed for `175 source files`; four touched Python files are format-clean.
- Production class/function structure, packaged `aico-state` help + real backup/verify, Compose config and
  `git diff --check` passed.
- External DR remains intentionally open as B-013: no off-device artifact, encryption/retention policy,
  or disposable-target restore drill exists in this checkout.

## Stop conditions

- Stop if backup copies raw DB/WAL files instead of using SQLite's online backup API.
- Stop if verify opens the artifact through a helper that mutates schema metadata.
- Stop if restore/reset can mutate while another runtime holds the canonical owner lock.
- Stop if restore replaces the target before backup/hash/integrity/schema/safety checks all pass.
- Stop if any command prints business payloads, secrets, raw exception text, or source absolute paths.
- Stop if this local capability is described as off-device disaster recovery without a real drill.
