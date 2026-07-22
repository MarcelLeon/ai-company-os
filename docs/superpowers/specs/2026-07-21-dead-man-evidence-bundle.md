# Dead-Man Outage Evidence Bundle

**Status**: Complete — Round 210

## Goal Brief

**User outcome**: After a real second-failure-domain outage exercise, an owner must be able to export
receiver truth and verify it offline without screenshots, database access, or disclosure of receiver
credentials and transport configuration.

**Decision owner**: Only the admin credential may export evidence. Pulse authority cannot read
monitor or outage history. The receiver owns immutable outage edges and local delivery acceptance;
the verifier checks structural truth but must not claim where the receiver ran or what physical fault
the owner performed.

## In scope

- An admin-only `GET /v1/monitors/{runtime_id}/evidence` endpoint.
- A strict versioned JSON bundle containing generated time, safe runtime id, optional current monitor
  snapshot, and a bounded set of most-recent complete outage groups.
- Each outage group contains exactly one opened edge and zero or one resolved edge, plus local
  delivery state, retry count, and pending next-attempt time for each immutable event.
- Evidence export evaluates current receiver-time expiry first, so an elapsed but unswept outage is
  not omitted.
- Evidence survives receiver/store reconstruction and remains available after explicit disarm because
  immutable outbox rows are retained.
- Export is bounded by outage count, not raw event count, so a response never begins with a resolved
  edge whose opened edge was truncated.
- A local `aico-dead-man-evidence` CLI that strictly parses a saved bundle, verifies runtime identity,
  outage/event uniqueness, opened-before-resolved order, timestamps, and delivery order, and can
  require a minimum completed-outage count and all events locally delivered.
- The verifier prints a compact JSON summary and SHA-256 of the exact artifact bytes for later
  integrity comparison. The hash is not an origin signature.

## Out of scope

- Reading admin/pulse tokens from a bundle or CLI argument, making network calls, arming/disarming a
  monitor, or triggering a fault.
- Storing endpoint URL, bearer token, exception text, hostname, filesystem/database path, request
  headers/body, arbitrary operator notes, or physical-fault labels in evidence.
- Claiming that a valid bundle proves independent hosting, TLS configuration, a kill/network action,
  downstream exactly-once delivery, or B-012 completion.
- Cryptographic origin signatures or a new key-management system. TLS capture and owner-controlled
  artifact storage remain deployment evidence; SHA-256 only detects later byte changes when compared
  with a previously recorded digest.
- Unbounded history export, public evidence routes, or pulse-authority read access.

## Acceptance checks

1. Store reconstruction exports the same outage/event identities and delivery metadata.
2. The latest-N outage limit returns whole outage groups in chronological event order.
3. An active outage exports opened only; a resolved outage exports opened then resolved.
4. A delivered resolved edge cannot appear while its opened edge is pending.
5. Evidence remains exportable after disarm; a runtime with neither monitor nor events is 404.
6. Admin token succeeds; pulse/missing/wrong token fails without leaking bundle or secrets.
7. Export payload has no URL/token/path/exception/request/operator-note fields and rejects extras.
8. CLI accepts a valid saved bundle, emits deterministic facts plus exact-byte SHA-256, and fails for
   wrong runtime, insufficient completed outages, pending delivery when required, or malformed order.
9. Existing receiver startup, pulse, notification, readiness, and container contracts remain green.
10. Full root/SME tests, Ruff, mypy, touched format, structure, CLI, Compose, and diff gates pass.

## Stop conditions

- Stop if export requires direct SQLite access or exposes a transport/secret field.
- Stop if response truncation can separate resolved from its opened edge.
- Stop if pulse authority can read evidence or if export mutates arm/disarm policy.
- Stop if the CLI performs network or external mutations.
- Stop if a valid local bundle is described as proof of independent deployment or physical outage.

## Completion evidence

- Store/API/verifier suites cover restart persistence, delivered and pending retry metadata, complete
  recent-outage truncation, disarm retention, admin-only authority, unknown runtime 404, secret-free
  payloads, strict ordering/extras, acceptance thresholds, exact-byte hash, and the packaged CLI main
  path reading a real local artifact.
- Full root and SME suites, Ruff, mypy, touched format, production structure, both CLIs, Compose, and
  diff gates pass. Full-root format still reports only the untouched existing data-agent file.
- No independent receiver host, TLS route, owner credential, physical fault exercise, or downstream
  receipt was created; B-012 remains external-evidence pending.
