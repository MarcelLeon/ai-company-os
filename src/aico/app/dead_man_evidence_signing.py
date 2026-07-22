"""Detached receiver-key provenance for exact dead-man evidence bytes."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

_DOMAIN = b"AICO-DEAD-MAN-EVIDENCE-V1\x00"
MAX_EVIDENCE_PAYLOAD_BYTES = 4 * 1024 * 1024
MAX_SIGNED_ENVELOPE_BYTES = 6 * 1024 * 1024
_MAX_KEY_BYTES = 64 * 1024


class DeadManEvidenceSigningError(ValueError):
    """Evidence signature material is missing, unsafe, or invalid."""


class SignedDeadManEvidenceEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    algorithm: Literal["ed25519"] = "ed25519"
    payload_base64: str = Field(min_length=4, max_length=5_592_408)
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    signature_base64: str = Field(min_length=88, max_length=88)
    public_key_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_encoded_material(self) -> SignedDeadManEvidenceEnvelope:
        payload = _decode_base64(self.payload_base64, "evidence payload")
        signature = _decode_base64(self.signature_base64, "evidence signature")
        if not payload or len(payload) > MAX_EVIDENCE_PAYLOAD_BYTES:
            raise ValueError("signed evidence payload size is invalid")
        if len(signature) != 64:
            raise ValueError("signed evidence signature size is invalid")
        if not hmac.compare_digest(hashlib.sha256(payload).hexdigest(), self.payload_sha256):
            raise ValueError("signed evidence payload digest does not match")
        return self

    def payload_bytes(self) -> bytes:
        return _decode_base64(self.payload_base64, "evidence payload")

    def signature_bytes(self) -> bytes:
        return _decode_base64(self.signature_base64, "evidence signature")


@dataclass(frozen=True)
class VerifiedSignedDeadManEvidence:
    payload: bytes
    envelope_sha256: str
    payload_sha256: str
    public_key_sha256: str


@dataclass(frozen=True)
class DeadManEvidenceSigner:
    private_key: Ed25519PrivateKey
    public_key_sha256: str

    def sign(self, payload: bytes) -> SignedDeadManEvidenceEnvelope:
        _validate_payload(payload)
        signature = self.private_key.sign(_DOMAIN + payload)
        return SignedDeadManEvidenceEnvelope(
            payload_base64=base64.b64encode(payload).decode("ascii"),
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            signature_base64=base64.b64encode(signature).decode("ascii"),
            public_key_sha256=self.public_key_sha256,
        )


def load_evidence_signer(
    path: Path,
    *,
    forbidden_roots: tuple[Path, ...] = (),
) -> DeadManEvidenceSigner:
    raw = _read_key_file(
        path,
        label="evidence signing private key",
        require_mode=0o600,
        forbidden_roots=forbidden_roots,
    )
    try:
        key = serialization.load_pem_private_key(raw, password=None)
    except (TypeError, ValueError, UnsupportedAlgorithm):
        raise DeadManEvidenceSigningError("evidence signing private key is invalid") from None
    if not isinstance(key, Ed25519PrivateKey):
        raise DeadManEvidenceSigningError("evidence signing private key must use Ed25519")
    return DeadManEvidenceSigner(
        private_key=key,
        public_key_sha256=_public_key_sha256(key.public_key()),
    )


def verify_signed_evidence_bytes(
    raw: bytes,
    *,
    trusted_public_key_path: Path,
    forbidden_roots: tuple[Path, ...] = (),
) -> VerifiedSignedDeadManEvidence:
    if not raw or len(raw) > MAX_SIGNED_ENVELOPE_BYTES:
        raise DeadManEvidenceSigningError("signed evidence envelope size is invalid")
    key = _load_public_key(trusted_public_key_path, forbidden_roots=forbidden_roots)
    try:
        envelope = SignedDeadManEvidenceEnvelope.model_validate_json(raw)
        expected_key_id = _public_key_sha256(key)
        if not hmac.compare_digest(expected_key_id, envelope.public_key_sha256):
            raise DeadManEvidenceSigningError("signed evidence public key does not match")
        payload = envelope.payload_bytes()
        key.verify(envelope.signature_bytes(), _DOMAIN + payload)
    except DeadManEvidenceSigningError:
        raise
    except (InvalidSignature, ValidationError, ValueError):
        raise DeadManEvidenceSigningError("signed evidence envelope is invalid") from None
    return VerifiedSignedDeadManEvidence(
        payload=payload,
        envelope_sha256=hashlib.sha256(raw).hexdigest(),
        payload_sha256=envelope.payload_sha256,
        public_key_sha256=envelope.public_key_sha256,
    )


def serialize_signed_evidence_envelope(envelope: SignedDeadManEvidenceEnvelope) -> bytes:
    return (
        json.dumps(envelope.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def serialize_evidence_payload(payload: BaseModel) -> bytes:
    raw = (
        json.dumps(
            payload.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    _validate_payload(raw)
    return raw


def _load_public_key(
    path: Path,
    *,
    forbidden_roots: tuple[Path, ...],
) -> Ed25519PublicKey:
    raw = _read_key_file(
        path,
        label="trusted receiver public key",
        require_mode=None,
        forbidden_roots=forbidden_roots,
    )
    try:
        key = serialization.load_pem_public_key(raw)
    except (ValueError, UnsupportedAlgorithm):
        raise DeadManEvidenceSigningError("trusted receiver public key is invalid") from None
    if not isinstance(key, Ed25519PublicKey):
        raise DeadManEvidenceSigningError("trusted receiver public key must use Ed25519")
    return key


def _read_key_file(
    path: Path,
    *,
    label: str,
    require_mode: int | None,
    forbidden_roots: tuple[Path, ...],
) -> bytes:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        raise DeadManEvidenceSigningError(f"{label} path must be absolute")
    try:
        metadata = candidate.lstat()
        resolved = candidate.resolve(strict=True)
    except OSError:
        raise DeadManEvidenceSigningError(f"{label} is missing or unreadable") from None
    mode = stat.S_IMODE(metadata.st_mode)
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise DeadManEvidenceSigningError(f"{label} must be a regular non-symlink file")
    if metadata.st_uid != os.getuid():
        raise DeadManEvidenceSigningError(f"{label} must be owned by the current user")
    if require_mode is not None and mode != require_mode:
        raise DeadManEvidenceSigningError(f"{label} must use mode 0600")
    if require_mode is None and mode & 0o022:
        raise DeadManEvidenceSigningError(f"{label} must not be group or world writable")
    if any(_inside(resolved, root) for root in forbidden_roots):
        raise DeadManEvidenceSigningError(f"{label} must be outside the forbidden root")
    try:
        raw = resolved.read_bytes()
    except OSError:
        raise DeadManEvidenceSigningError(f"{label} is missing or unreadable") from None
    if not raw or len(raw) > _MAX_KEY_BYTES:
        raise DeadManEvidenceSigningError(f"{label} size is invalid")
    return raw


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.expanduser().resolve(strict=True))
    except (OSError, ValueError):
        return False
    return True


def _public_key_sha256(key: Ed25519PublicKey) -> str:
    der = key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()


def _validate_payload(payload: bytes) -> None:
    if not payload or len(payload) > MAX_EVIDENCE_PAYLOAD_BYTES:
        raise DeadManEvidenceSigningError("evidence payload size is invalid")


def _decode_base64(value: str, label: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError(f"{label} base64 is invalid") from None
