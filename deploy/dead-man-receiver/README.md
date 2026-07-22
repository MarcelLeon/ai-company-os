# Independent Dead-Man Receiver

> Optional advanced reliability component. The normal AICO quickstart does not require a second
> computer or cloud server. Deploy this only when whole-machine outage detection is part of your
> reliability target.

This service must run outside the Mac it monitors. Running it beside AICO proves the API but does
not create an independent failure domain.

## Security and persistence contract

- Put TLS in front of `127.0.0.1:8080` with an owner-controlled reverse proxy or managed ingress.
- Generate separate pulse/admin tokens with at least 32 random characters, for example
  `openssl rand -hex 32`. Pulse authority cannot arm, disarm, or read monitors.
- Keep `/data/dead-man.db` on a persistent volume and back it up. Receiver restart must retain armed
  monitors, active outages, and notification outbox rows.
- Generate one unencrypted PKCS#8 Ed25519 evidence-signing key on the receiver host. Keep the private
  key owner-only (`0600`) and outside the AICO checkout; copy only its SPKI public key to the AICO
  operator. Back up and rotate the private key independently. Rotation requires a new evidence
  export, updated owner-pinned public key, and recommissioning.
- Receiver schema v2 accepts pulse schema v2. `disabled`/`healthy` alert-delivery signals renew the
  monitor; `pending`/`failed` signals are ordered but do not renew it. Upgrade and migrate the
  receiver before pointing a v2 publisher at an older deployment.
- The receiver process holds `/data/dead-man.db.owner.lock` for its full lifespan. Online backup may
  run while it is active; restore must acquire that kernel lock and therefore requires a stopped
  receiver. Deleting the lock file is never a valid stop or recovery action.
- `AICO_DEAD_MAN_NOTIFICATION_WEBHOOK_URL` is the downstream owner notification endpoint, not this
  receiver's pulse URL. It must deduplicate the event-id `Idempotency-Key`.
- For commercial absence coverage, configure `AICO_DEAD_MAN_NOTIFICATION_FALLBACK_WEBHOOK_URL` on a
  different HTTPS origin with an independent credential. Both routes receive the same immutable
  event concurrently. `AICO_DEAD_MAN_NOTIFICATION_MINIMUM_ACKNOWLEDGEMENTS=1` provides 1-of-2
  availability; set it to `2` only when both local platform ACKs are required. Different origins do
  not prove different clouds, accounts, networks, or physical failure domains.
- The receiver stores the active route/quorum policy and freezes it into every new outbox event.
  It refuses startup if configuration changes while delivery is pending; restore the old policy and
  drain the exact pending event before changing policy. Back up any pre-v5 receiver before migration.
- Schema v4 also records the last bounded ACK vector and slot-level health. A partial quorum emits a
  durable `notification_route_degraded` event through any surviving route; a later real outage-event
  ACK emits `notification_route_recovered`. These meta-alerts use any-route ACK so a 2-of-2 policy
  cannot suppress the warning. Back up v3 before upgrade. They are event-driven observations, not a
  continuous canary.
- Schema v5 adds an explicit, default-disabled silent probe contract. Enable
  `AICO_DEAD_MAN_NOTIFICATION_PROBE_CONTRACT=silent-route-probe-v1` only after both real webhook
  bridges guarantee that `notification_route_probe` is idempotently ACKed but never displayed to
  the owner or routed into incident automation. It reuses the real URL/token/POST path, persists the
  exact probe before send, marks one failed window suspect, and emits a degraded edge only after the
  configured consecutive-failure threshold. A later probe ACK emits recovered. HEAD checks,
  alternate probe credentials, and fake sinks are not equivalent evidence.
- The compose binding is loopback-only. Do not publish plain HTTP directly to the internet.
- The image runs as uid `10001`, drops Linux capabilities, uses a read-only root filesystem, and only
  writes the `/data` volume and tmpfs `/tmp`.
- `/healthz` only proves the HTTP process responds. `/readyz` also requires SQLite and recent
  expiry/delivery worker progress; three consecutive internal failures or three missed sweep windows
  return generic HTTP 503 so the Compose restart policy can recover the process. A downstream
  notification retry remains ready because its durable backoff is expected degraded operation.

## Start

```bash
cd deploy/dead-man-receiver
cp .env.example .env
# Replace every placeholder and keep the file owner-only. The app rejects placeholder tokens.
chmod 600 .env
docker compose build
# One-time owner-invoked generation inside the isolated signing volume; refuses overwrite.
docker compose run --rm --no-deps --entrypoint python dead-man-receiver -c \
  'from pathlib import Path; import os; from cryptography.hazmat.primitives import serialization; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; p=Path("/signing/evidence-signing-private.pem"); fd=os.open(p, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600); os.write(fd, Ed25519PrivateKey.generate().private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())); os.close(fd)'
# Export only the public key to an owner-controlled operator path.
docker compose run --rm --no-deps --entrypoint python dead-man-receiver -c \
  'from pathlib import Path; from cryptography.hazmat.primitives import serialization; k=serialization.load_pem_private_key(Path("/signing/evidence-signing-private.pem").read_bytes(), password=None); print(k.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode(), end="")' \
  > /absolute/operator/receiver-evidence-public.pem
docker compose up --build -d
curl --fail http://127.0.0.1:8080/readyz
```

Configure the external TLS route so AICO can reach:

```text
https://receiver.example/v1/runtime-liveness/pulses
```

The AICO Mac uses this URL and the receiver pulse token as
`AICO_RUNTIME_LIVENESS_WEBHOOK_URL` / `AICO_RUNTIME_LIVENESS_WEBHOOK_BEARER_TOKEN`. The receiver
admin token never belongs on the AICO Mac. `AICO_RUNTIME_ALERT_WEBHOOK_URL` remains a separate
incident-alert protocol and must not point at the strict pulse endpoint.

## Explicit arm and disarm

Arm once before enabling AICO pulse delivery. Repeating the same TTL is idempotent and does not
reset the expiry window. Changing TTL requires disarm then arm.

```bash
curl --fail --request POST \
  --header "Authorization: Bearer $AICO_DEAD_MAN_ADMIN_BEARER_TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"expires_after_seconds":300}' \
  https://receiver.example/v1/monitors/owner-runtime/arm
```

Read status with the same admin credential:

```bash
curl --fail \
  --header "Authorization: Bearer $AICO_DEAD_MAN_ADMIN_BEARER_TOKEN" \
  https://receiver.example/v1/monitors/owner-runtime
```

Before permanent AICO uninstall, explicitly disarm. Normal AICO restart/stop never does this:

```bash
curl --fail --request POST \
  --header "Authorization: Bearer $AICO_DEAD_MAN_ADMIN_BEARER_TOKEN" \
  https://receiver.example/v1/monitors/owner-runtime/disarm
```

Existing immutable outage notifications remain deliverable after disarm; disarm suppresses future
stale transitions and never manufactures a false recovery.

## Required acceptance sample

After TLS, persistent volume, secrets, and downstream notification are configured:

1. Arm the monitor and start AICO; verify one accepted pulse and healthy monitor status.
2. Kill only the AICO child; launchd replacement should send a new boot before TTL, with no outage.
3. Prevent launch success past TTL; verify exactly one `outage_opened` notification.
4. Restore AICO; verify exactly one matching `outage_resolved` notification.
5. Repeat with network isolation past TTL, then restore.
6. Restart the receiver during an active outage and during a pending notification retry; state and
   event identity must survive.
7. Break only the secondary runtime-alert endpoint past TTL while pulse delivery remains healthy;
   verify one `alert_delivery_unhealthy` opened event, then one matching resolved event after alert
   delivery and a subsequent pulse recover. Do not treat this as a runtime crash.
8. With a fallback route configured, fail the primary notification endpoint and verify that both
   routes were attempted, the fallback received the stable event id, and 1-of-2 settled the outbox.
   Then fail both routes, verify durable pending/backoff, restore one route, and verify exact-event
   convergence. Repeat with quorum `2` if dual ACK is part of the owner policy.
9. Query the admin-only route checkpoint and verify that a partial ACK reports one degraded slot
   without exposing either endpoint:

   ```bash
   curl --fail --silent --show-error \
     -H "Authorization: Bearer ${AICO_DEAD_MAN_ADMIN_BEARER_TOKEN}" \
     https://receiver.example/v1/notification-routes
   ```

   The surviving provider should receive exactly one stable degraded edge. After a later real event
   reaches both routes, verify one recovered edge and a healthy slot. Repeated failures must not open
   duplicate edges.
10. If both bridges support the silent v1 contract, enable it at low frequency. Verify platform logs
    contain stable `notification_route_probe` requests while the owner device shows no probe message.
    Fail one route for the configured number of windows, verify suspect then one degraded edge, restore
    it, and verify one recovered edge plus evidence schema v5. Disable the contract immediately if a
    probe is user-visible or triggers incident automation.

After each exercise, export receiver truth with the admin credential. The response is bounded by
whole outage groups, so a resolved edge is never separated from its opened edge:

```bash
curl --fail \
  --header "Authorization: Bearer $AICO_DEAD_MAN_ADMIN_BEARER_TOKEN" \
  "https://receiver.example/v1/monitors/owner-runtime/signed-evidence?max_outages=20" \
  --output /absolute/private/signed-dead-man-evidence-owner-runtime.json
```

Copy the artifact to a trusted offline environment and verify it without any receiver credential:

```bash
chmod 600 /absolute/private/signed-dead-man-evidence-owner-runtime.json
uv run aico-dead-man-evidence /absolute/private/signed-dead-man-evidence-owner-runtime.json \
  --trusted-public-key /absolute/private/receiver-evidence-public.pem \
  --runtime-id owner-runtime \
  --minimum-complete-outages 1 \
  --require-all-delivered \
  --maximum-evidence-age-seconds 300 \
  --require-fresh-notification-probe \
  --require-all-routes-healthy
```

The v5 verifier also checks route checkpoints, per-event ACK masks, and route-health edge triggers.
The three final flags form the current-health acceptance layer: verification must happen within the
owner-selected export window, the enabled silent probe must have completed and still be fresh at
verification time, and every route snapshot must be healthy. Omit those flags only for historical
audit, not for commissioning or recommissioning.
For strict AICO runtime admission, set the final `.env` evidence, receiver public-key, and receipt
paths first, then use `aico-commission create` from the AICO checkout with
`--trusted-receiver-public-key /absolute/private/receiver-evidence-public.pem`. The receipt
additionally binds the clean reviewed Git configuration, dotenv metadata generation, exact signed
envelope, embedded payload, and receiver key identity, and expires at the earlier evidence/probe boundary.
Use a new evidence and receipt filename for every recommission; never overwrite prior evidence.
It prints event counts and the SHA-256 of the exact artifact bytes. `delivered=true` means
the event's frozen local acknowledgement quorum was met; it does not prove every route succeeded or a
human read the notification. Record that digest with
the exercise log so later byte changes are detectable. The Ed25519 signature proves possession of
the owner-pinned receiver key for the exact payload; it does not prove the key's physical host, the
TLS route, physical kill/network action, or downstream
exactly-once behavior. Keep the artifact as owner-only operational evidence.

Until these are captured from a genuinely separate host, B-012 remains external-evidence pending.

## Independent receiver backup and recovery

Receiver state is a second-failure-domain evidence source. Back it up on its own cadence; never put
its database inside the Mac-side core recovery set or automatically roll it back when AICO fails.
An online backup may be taken without stopping the receiver:

```bash
docker compose exec -T dead-man-receiver \
  aico-dead-man-recovery backup \
  --db /data/dead-man.db \
  --output /data/dead-man-20260722.db
docker compose cp \
  dead-man-receiver:/data/dead-man-20260722.db \
  ./dead-man-20260722.db
```

Record the command's SHA-256 in an independent authority, place the artifact in owner-approved
encrypted off-device storage, and remove the transient volume copy only under the retention policy.
On a reviewed checkout with the same AICO version, deep-verify and rehearse the copied bytes:

```bash
uv run aico-dead-man-recovery verify \
  --backup /secure/off-device/dead-man-20260722.db
mkdir -p /secure/private-receiver-drill
chmod 700 /secure/private-receiver-drill
uv run aico-dead-man-recovery drill \
  --backup /secure/off-device/dead-man-20260722.db \
  --expected-sha256 <independently-recorded-sha256> \
  --workspace /secure/private-receiver-drill \
  --report /secure/evidence/dead-man-drill-20260722.json
```

`verify` checks SQLite integrity, exact schema-v2 constraints, forbidden executable schema objects,
monitor checkpoints, outage open/resolved order, payload/column identity, delivery ordering, and
timezone-aware timestamps. It also rejects invalid alert-delivery states, partial renewal/ordered
pulse checkpoints, and outage-reason drift. Summaries and drill reports contain counts and digests, not runtime IDs,
event IDs, payloads, credentials, or absolute paths.

Restore is an explicit receiver-incident action only. First stop the receiver and confirm it no
longer owns the state lock; then run the one-off recovery process against the persistent volume:

```bash
docker compose stop dead-man-receiver
docker compose run --rm --no-deps \
  --entrypoint aico-dead-man-recovery \
  dead-man-receiver restore \
  --db /data/dead-man.db \
  --from /data/dead-man-20260722.db \
  --expected-sha256 <independently-recorded-sha256> \
  --yes
docker compose up -d dead-man-receiver
curl --fail http://127.0.0.1:8080/readyz
```

A valid live database is first captured as a verified `pre-restore` safety backup. If it cannot be
verified, its DB/WAL/SHM bytes are retained in an owner-only `unverified-pre-restore` quarantine
directory before replacement. Preserve either result until monitor status, pending delivery, and an
admin evidence export are checked. Never schedule `restore`, select “latest” automatically, or
restore the receiver merely because the monitored AICO Mac is being recovered.
