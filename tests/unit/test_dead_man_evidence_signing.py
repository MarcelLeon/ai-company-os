from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from fastapi.testclient import TestClient
from pydantic import BaseModel

from aico.app.dead_man_evidence_signing import (
    DeadManEvidenceSigningError,
    SignedDeadManEvidenceEnvelope,
    load_evidence_signer,
    serialize_evidence_payload,
    serialize_signed_evidence_envelope,
    verify_signed_evidence_bytes,
)
from aico.app.dead_man_receiver import (
    DeadManEvidenceBundle,
    DeadManNotificationAttemptResult,
    DeadManOutboundEvent,
)
from aico.app.dead_man_receiver_app import (
    DeadManReceiverSettings,
    build_dead_man_receiver_app,
)

PULSE_SECRET = "p" * 32
ADMIN_SECRET = "a" * 32


class AcknowledgingSink:
    async def send(self, _event: DeadManOutboundEvent) -> DeadManNotificationAttemptResult:
        return DeadManNotificationAttemptResult(acknowledged_routes=(True,))


def test_signed_evidence_round_trip_binds_exact_payload_and_trusted_key(tmp_path: Path) -> None:
    private_path, public_path = _ed25519_key_pair(tmp_path)
    signer = load_evidence_signer(private_path)
    payload = b'{"schema_version":5,"runtime_id":"runtime-a"}\n'
    raw = serialize_signed_evidence_envelope(signer.sign(payload))

    verified = verify_signed_evidence_bytes(raw, trusted_public_key_path=public_path)

    assert verified.payload == payload
    assert verified.payload_sha256 == signer.sign(payload).payload_sha256
    assert verified.public_key_sha256 == signer.public_key_sha256
    assert len(verified.envelope_sha256) == 64
    assert public_path.read_bytes() not in raw


def test_signed_evidence_rejects_payload_signature_key_and_base64_tampering(
    tmp_path: Path,
) -> None:
    private_path, public_path = _ed25519_key_pair(tmp_path / "trusted")
    _, wrong_public_path = _ed25519_key_pair(tmp_path / "wrong")
    signer = load_evidence_signer(private_path)
    envelope = signer.sign(b"trusted payload")
    raw = serialize_signed_evidence_envelope(envelope)

    with pytest.raises(DeadManEvidenceSigningError, match="public key"):
        verify_signed_evidence_bytes(raw, trusted_public_key_path=wrong_public_path)

    decoded = json.loads(raw)
    decoded["payload_base64"] = base64.b64encode(b"forged payload").decode()
    decoded["payload_sha256"] = hashlib.sha256(b"forged payload").hexdigest()
    forged = json.dumps(decoded).encode()
    with pytest.raises(DeadManEvidenceSigningError, match="invalid"):
        verify_signed_evidence_bytes(forged, trusted_public_key_path=public_path)

    decoded = json.loads(raw)
    signature = bytearray(base64.b64decode(decoded["signature_base64"]))
    signature[0] ^= 1
    decoded["signature_base64"] = base64.b64encode(signature).decode()
    with pytest.raises(DeadManEvidenceSigningError, match="invalid"):
        verify_signed_evidence_bytes(
            json.dumps(decoded).encode(), trusted_public_key_path=public_path
        )

    decoded = json.loads(raw)
    decoded["payload_base64"] = "not-base64!"
    with pytest.raises(DeadManEvidenceSigningError, match="invalid"):
        verify_signed_evidence_bytes(
            json.dumps(decoded).encode(), trusted_public_key_path=public_path
        )


def test_evidence_keys_require_safe_paths_permissions_and_ed25519(tmp_path: Path) -> None:
    private_path, public_path = _ed25519_key_pair(tmp_path / "safe")
    os.chmod(private_path, 0o644)
    with pytest.raises(DeadManEvidenceSigningError, match="0600"):
        load_evidence_signer(private_path)
    os.chmod(private_path, 0o600)

    symlink = tmp_path / "private-link.pem"
    symlink.symlink_to(private_path)
    with pytest.raises(DeadManEvidenceSigningError, match="non-symlink"):
        load_evidence_signer(symlink)
    with pytest.raises(DeadManEvidenceSigningError, match="forbidden root"):
        load_evidence_signer(private_path, forbidden_roots=(tmp_path,))

    x25519 = X25519PrivateKey.generate()
    x25519_path = tmp_path / "x25519.pem"
    x25519_path.write_bytes(
        x25519.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    os.chmod(x25519_path, 0o600)
    with pytest.raises(DeadManEvidenceSigningError, match="must use Ed25519"):
        load_evidence_signer(x25519_path)

    signer = load_evidence_signer(private_path)
    raw = serialize_signed_evidence_envelope(signer.sign(b"payload"))
    os.chmod(public_path, 0o666)
    with pytest.raises(DeadManEvidenceSigningError, match="writable"):
        verify_signed_evidence_bytes(raw, trusted_public_key_path=public_path)


def test_receiver_signed_endpoint_is_optional_secret_safe_and_verifiable(
    tmp_path: Path,
) -> None:
    private_path, public_path = _ed25519_key_pair(tmp_path / "keys")
    now = datetime(2026, 7, 22, 8, 0, tzinfo=UTC)
    unsigned_app = build_dead_man_receiver_app(
        _settings(tmp_path / "unsigned"),
        notification_sink=AcknowledgingSink(),
        clock=lambda: now,
    )
    with TestClient(unsigned_app) as client:
        _arm(client)
        response = client.get(
            "/v1/monitors/runtime-a/signed-evidence",
            headers=_admin_headers(),
        )
        assert response.status_code == 503
        assert response.json() == {"detail": "evidence signing is unavailable"}

    signed_app = build_dead_man_receiver_app(
        _settings(tmp_path / "signed", private_key=private_path),
        notification_sink=AcknowledgingSink(),
        clock=lambda: now,
    )
    with TestClient(signed_app) as client:
        _arm(client)
        unsigned = client.get(
            "/v1/monitors/runtime-a/evidence",
            headers=_admin_headers(),
        )
        signed = client.get(
            "/v1/monitors/runtime-a/signed-evidence",
            headers=_admin_headers(),
        )

    assert unsigned.status_code == 200
    assert unsigned.json()["schema_version"] == 5
    assert signed.status_code == 200
    verified = verify_signed_evidence_bytes(
        signed.content,
        trusted_public_key_path=public_path,
    )
    bundle = DeadManEvidenceBundle.model_validate_json(verified.payload)
    assert bundle.runtime_id == "runtime-a"
    assert SignedDeadManEvidenceEnvelope.model_validate_json(signed.content).algorithm == "ed25519"


def test_receiver_rejects_invalid_signing_key_without_leaking_path(tmp_path: Path) -> None:
    private_path, _ = _ed25519_key_pair(tmp_path / "keys")
    os.chmod(private_path, 0o644)
    settings = _settings(tmp_path / "receiver", private_key=private_path)

    with pytest.raises(RuntimeError, match="signing key is invalid") as error:
        build_dead_man_receiver_app(settings, notification_sink=AcknowledgingSink())

    assert str(private_path) not in str(error.value)


def test_evidence_payload_serialization_is_canonical_and_bounded(tmp_path: Path) -> None:
    _, public_path = _ed25519_key_pair(tmp_path)
    envelope = SignedDeadManEvidenceEnvelope(
        payload_base64=base64.b64encode(b"x").decode(),
        payload_sha256=hashlib.sha256(b"x").hexdigest(),
        signature_base64=base64.b64encode(b"s" * 64).decode(),
        public_key_sha256="a" * 64,
    )
    assert serialize_signed_evidence_envelope(envelope).endswith(b"\n")
    assert public_path.name not in serialize_signed_evidence_envelope(envelope).decode()

    with pytest.raises(DeadManEvidenceSigningError, match="size"):
        serialize_evidence_payload(_OversizedModel(value="x" * (4 * 1024 * 1024)))


class _OversizedModel(BaseModel):
    value: str


def _ed25519_key_pair(root: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_path = root / "receiver-private.pem"
    public_path = root / "receiver-public.pem"
    private_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    os.chmod(private_path, 0o600)
    os.chmod(public_path, 0o644)
    return private_path, public_path


def _settings(
    root: Path,
    *,
    private_key: Path | None = None,
) -> DeadManReceiverSettings:
    root.mkdir(parents=True, exist_ok=True)
    return DeadManReceiverSettings.model_validate(
        {
            "state_db_path": root / "receiver.db",
            "pulse_bearer_token": PULSE_SECRET,
            "admin_bearer_token": ADMIN_SECRET,
            "notification_webhook_url": "https://notify.example.test/private",
            "evidence_signing_private_key_path": private_key,
            "sweep_interval_seconds": 3600,
        }
    )


def _arm(client: TestClient) -> None:
    response = client.post(
        "/v1/monitors/runtime-a/arm",
        headers=_admin_headers(),
        json={"expires_after_seconds": 180},
    )
    assert response.status_code == 200


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_SECRET}"}
