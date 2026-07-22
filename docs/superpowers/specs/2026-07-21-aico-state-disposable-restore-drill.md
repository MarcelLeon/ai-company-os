# AICO State Disposable Restore Drill

**Status**: Complete — Round 212

## Goal Brief

**User outcome**: An operator must be able to prove that a selected AICO state backup can pass the
actual restore path and reopen as usable current-schema SQLite state, without stopping or mutating the
live runtime database.

**Decision owner**: The drill is a non-destructive rehearsal. It restores only inside a disposable
temporary directory, removes that directory on success or failure, and may emit one new owner-only
evidence report. It never restores the configured live target and never upgrades the DR claim beyond
the evidence actually collected.

## In scope

- `aico-state --db <live-path> drill --backup <backup.db> --expected-sha256 <digest>`.
- `--db` remains syntactically required by the existing CLI but drill must not open, create, lock, or
  mutate that path. This makes the non-interference boundary machine-testable.
- Verify the selected artifact's exact bytes, integrity, and current schema before materialization.
- Create a private temporary directory, call the same owner-fenced restore primitive against a new
  disposable target, reopen that materialized DB read-only, and compare schema plus every known table
  count with the selected artifact.
- Delete the disposable DB, owner lock, WAL/SHM, and temporary directory on both success and failure.
- Optional `--workspace <existing-directory>` selects the filesystem used for temporary materialization;
  no workspace path appears in output.
- Optional `--report <new.json>` writes a compact JSON evidence artifact through a same-directory
  temporary file, `fsync`, atomic no-overwrite publish, owner-only `0600`, and directory `fsync`.
- Summary/report may include schema version, known table counts, artifact basename, input SHA, actual
  materialized DB SHA/bytes, and completion time. It must not include task payloads, secrets, exception
  text, live/workspace/backup absolute paths, or owner-lock metadata.

## Out of scope

- Copying the artifact to another host or proving it came from off-device storage.
- Encryption, key management, retention, cadence, RPO/RTO, automatic scheduling, or automatic restore.
- Restoring audit/memory JSONL, project/persona Git files, `.env`, logs, or dead-man receiver state.
- Claiming a local disposable drill proves Mac-loss recovery, credential recovery, IM reachability, or
  commercial disaster-recovery readiness.

## Acceptance checks

1. Drill succeeds while the real source/runtime owner is active and leaves live DB bytes, records, and
   live owner state unchanged.
2. Drill uses the production restore primitive, materializes a standalone DB, reopens it read-only,
   and proves schema/table-count parity with the selected backup.
3. Wrong SHA, corrupt backup, unsupported schema, missing workspace, report=backup, and existing report
   fail before publishing evidence.
4. Success and injected restore/verification failure leave no `aico-state-drill-*` directory, disposable
   DB, sidecar, or owner-lock artifact.
5. Report is `0600`, never overwrites an existing path even under publish race, and its JSON equals the
   returned summary.
6. Summary/report contains no payload, secret, raw exception, live DB absolute path, backup absolute
   path, or workspace absolute path.
7. CLI returns 0 on success and 3 on refused/failed drill, while preserving existing command behavior.
8. Full root/SME tests, Ruff, mypy, touched format, structure, packaged CLI, Compose, and diff gates pass.

## Stop conditions

- Stop if drill opens or locks `--db`, or if it can replace a non-disposable target.
- Stop if implementation duplicates restore steps instead of calling the production restore primitive.
- Stop if cleanup depends only on the happy path.
- Stop if evidence report can overwrite an existing artifact or exposes absolute paths/payloads.
- Stop if the resulting local report is described as off-device or full-asset DR proof.

## Completion evidence

- Targeted state backup/CLI tests: `12 passed`.
- Full root suite: `688 passed, 1 skipped`; isolated SME suite: `53 passed`.
- Ruff, mypy (175 source files), touched-file format, production structure, packaged real CLI,
  Compose config, and `git diff --check` passed.
- The packaged CLI restored a real backup into a disposable workspace, published a `0600` report,
  left an intentionally missing live `--db` path missing, and removed all temporary drill state.
- B-013 remains open for off-device encrypted storage, full-asset recovery, and isolated-checkout
  business/IM evidence; this local completion does not satisfy those external checks.
