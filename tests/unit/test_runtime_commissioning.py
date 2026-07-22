from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aico.app.dead_man_evidence_signing import (
    load_evidence_signer,
    serialize_signed_evidence_envelope,
)
from aico.app.runtime_commissioning import (
    RuntimeCommissioningError,
    RuntimeCommissioningHealth,
    RuntimeCommissioningReceipt,
    create_runtime_commissioning_receipt,
    verify_runtime_commissioning_receipt,
)
from aico.app.runtime_commissioning_cli import main
from aico.core.models import HealthStatus


@dataclass(frozen=True)
class Materials:
    checkout: Path
    project_config: Path
    dotenv: Path
    evidence: Path
    public_key: Path
    receipt: Path
    revision: str


def test_commissioning_receipt_binds_current_config_dotenv_and_external_evidence(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 12, 5, tzinfo=UTC)
    materials = _materials(tmp_path, now)

    created = create_runtime_commissioning_receipt(
        **_arguments(materials),
        runtime_id="owner-runtime",
        maximum_evidence_age_seconds=300,
        output_path=materials.receipt,
        clock=lambda: now,
    )
    verified = verify_runtime_commissioning_receipt(
        **_arguments(materials),
        expected_runtime_id="owner-runtime",
        receipt_path=materials.receipt,
        expected_receipt_sha256=created.receipt_sha256,
        clock=lambda: now + timedelta(seconds=30),
    )

    receipt = RuntimeCommissioningReceipt.model_validate_json(materials.receipt.read_bytes())
    assert created.operation == "create"
    assert verified.operation == "verify"
    assert verified.receipt_sha256 == created.receipt_sha256
    assert verified.runtime_id == "owner-runtime"
    assert receipt.expires_at == datetime(2026, 7, 22, 12, 9, tzinfo=UTC)
    assert stat.S_IMODE(materials.receipt.stat().st_mode) == 0o600
    rendered = materials.receipt.read_text()
    assert str(materials.dotenv) not in rendered
    assert str(materials.evidence) not in rendered
    assert "owner-private-token" not in rendered
    assert receipt.dotenv_path_recorded is False
    assert receipt.dotenv_content_hash_recorded is False
    assert receipt.schema_version == 2
    assert receipt.receiver_evidence_signature_verified is True
    assert receipt.receiver_host_attested is False
    assert receipt.business_absence_ready is False
    with pytest.raises(RuntimeCommissioningError, match="already exists"):
        create_runtime_commissioning_receipt(
            **_arguments(materials),
            runtime_id="owner-runtime",
            maximum_evidence_age_seconds=300,
            output_path=materials.receipt,
            clock=lambda: now,
        )


def test_commissioning_verification_rejects_dotenv_and_evidence_drift(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 12, 5, tzinfo=UTC)
    materials = _materials(tmp_path, now)
    create_runtime_commissioning_receipt(
        **_arguments(materials),
        runtime_id="owner-runtime",
        maximum_evidence_age_seconds=300,
        output_path=materials.receipt,
        clock=lambda: now,
    )

    with pytest.raises(RuntimeCommissioningError, match="runtime identity"):
        verify_runtime_commissioning_receipt(
            **_arguments(materials),
            expected_runtime_id="different-runtime",
            receipt_path=materials.receipt,
            clock=lambda: now,
        )

    materials.dotenv.write_text("AICO_TELEGRAM_BOT_TOKEN=rotated-private-token\n")
    materials.dotenv.chmod(0o600)
    with pytest.raises(RuntimeCommissioningError, match="stale or mismatched"):
        verify_runtime_commissioning_receipt(
            **_arguments(materials),
            expected_runtime_id="owner-runtime",
            receipt_path=materials.receipt,
            clock=lambda: now,
        )

    materials = _materials(tmp_path / "evidence-drift", now)
    create_runtime_commissioning_receipt(
        **_arguments(materials),
        runtime_id="owner-runtime",
        maximum_evidence_age_seconds=300,
        output_path=materials.receipt,
        clock=lambda: now,
    )
    materials.evidence.write_bytes(materials.evidence.read_bytes() + b"\n")
    with pytest.raises(RuntimeCommissioningError, match="stale or mismatched"):
        verify_runtime_commissioning_receipt(
            **_arguments(materials),
            expected_runtime_id="owner-runtime",
            receipt_path=materials.receipt,
            clock=lambda: now,
        )


def test_commissioning_verification_rejects_expiry_checkout_and_receipt_tampering(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 12, 5, tzinfo=UTC)
    materials = _materials(tmp_path, now)
    create_runtime_commissioning_receipt(
        **_arguments(materials),
        runtime_id="owner-runtime",
        maximum_evidence_age_seconds=300,
        output_path=materials.receipt,
        clock=lambda: now,
    )

    with pytest.raises(RuntimeCommissioningError):
        verify_runtime_commissioning_receipt(
            **_arguments(materials),
            expected_runtime_id="owner-runtime",
            receipt_path=materials.receipt,
            clock=lambda: now + timedelta(minutes=5),
        )

    (materials.checkout / "app.py").write_text("print('reviewed v2')\n")
    _commit(materials.checkout, "reviewed-v2")
    with pytest.raises(RuntimeCommissioningError, match="invalid"):
        verify_runtime_commissioning_receipt(
            **_arguments(materials),
            expected_runtime_id="owner-runtime",
            receipt_path=materials.receipt,
            clock=lambda: now,
        )

    materials = _materials(tmp_path / "tampered", now)
    created = create_runtime_commissioning_receipt(
        **_arguments(materials),
        runtime_id="owner-runtime",
        maximum_evidence_age_seconds=300,
        output_path=materials.receipt,
        clock=lambda: now,
    )
    payload = json.loads(materials.receipt.read_text())
    payload["business_absence_ready"] = True
    materials.receipt.write_text(json.dumps(payload))
    materials.receipt.chmod(0o600)
    with pytest.raises(RuntimeCommissioningError, match="SHA-256"):
        verify_runtime_commissioning_receipt(
            **_arguments(materials),
            expected_runtime_id="owner-runtime",
            receipt_path=materials.receipt,
            expected_receipt_sha256=created.receipt_sha256,
            clock=lambda: now,
        )


def test_commissioning_requires_owner_only_artifacts_outside_checkout(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 12, 5, tzinfo=UTC)
    materials = _materials(tmp_path, now)
    with pytest.raises(RuntimeCommissioningError, match="outside commissioning bounds"):
        create_runtime_commissioning_receipt(
            **_arguments(materials),
            runtime_id="owner-runtime",
            maximum_evidence_age_seconds=3601,
            output_path=materials.receipt,
            clock=lambda: now,
        )

    materials.evidence.chmod(0o644)

    with pytest.raises(RuntimeCommissioningError, match="owner-only"):
        create_runtime_commissioning_receipt(
            **_arguments(materials),
            runtime_id="owner-runtime",
            maximum_evidence_age_seconds=300,
            output_path=materials.receipt,
            clock=lambda: now,
        )

    materials.evidence.chmod(0o600)
    with pytest.raises(RuntimeCommissioningError, match="outside"):
        create_runtime_commissioning_receipt(
            **_arguments(materials),
            runtime_id="owner-runtime",
            maximum_evidence_age_seconds=300,
            output_path=materials.checkout / "receipt.json",
            clock=lambda: now,
        )


def test_commissioning_rejects_unsigned_wrong_key_and_checkout_pinned_key(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 12, 5, tzinfo=UTC)

    unsigned = _materials(tmp_path / "unsigned", now)
    unsigned.evidence.write_bytes(
        json.dumps(_evidence_payload(now), separators=(",", ":")).encode()
    )
    with pytest.raises(RuntimeCommissioningError, match="creation failed"):
        create_runtime_commissioning_receipt(
            **_arguments(unsigned),
            runtime_id="owner-runtime",
            maximum_evidence_age_seconds=300,
            output_path=unsigned.receipt,
            clock=lambda: now,
        )

    wrong_key = _materials(tmp_path / "wrong-key", now)
    _, replacement_public_key = _receiver_key_pair(wrong_key.public_key.parent / "replacement")
    with pytest.raises(RuntimeCommissioningError, match="creation failed"):
        create_runtime_commissioning_receipt(
            **{
                **_arguments(wrong_key),
                "trusted_receiver_public_key_path": replacement_public_key,
            },
            runtime_id="owner-runtime",
            maximum_evidence_age_seconds=300,
            output_path=wrong_key.receipt,
            clock=lambda: now,
        )

    checkout_key = _materials(tmp_path / "checkout-key", now)
    in_checkout = checkout_key.checkout / "receiver-public.pem"
    in_checkout.write_bytes(checkout_key.public_key.read_bytes())
    with pytest.raises(RuntimeCommissioningError, match="creation failed"):
        create_runtime_commissioning_receipt(
            **{
                **_arguments(checkout_key),
                "trusted_receiver_public_key_path": in_checkout,
            },
            runtime_id="owner-runtime",
            maximum_evidence_age_seconds=300,
            output_path=checkout_key.receipt,
            clock=lambda: now,
        )


def test_commissioning_rejects_public_key_replacement_and_legacy_receipt(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 12, 5, tzinfo=UTC)
    materials = _materials(tmp_path, now)
    create_runtime_commissioning_receipt(
        **_arguments(materials),
        runtime_id="owner-runtime",
        maximum_evidence_age_seconds=300,
        output_path=materials.receipt,
        clock=lambda: now,
    )

    _, replacement_public_key = _receiver_key_pair(materials.public_key.parent / "rotated")
    with pytest.raises(RuntimeCommissioningError, match="invalid"):
        verify_runtime_commissioning_receipt(
            **{
                **_arguments(materials),
                "trusted_receiver_public_key_path": replacement_public_key,
            },
            expected_runtime_id="owner-runtime",
            receipt_path=materials.receipt,
            clock=lambda: now,
        )

    legacy = json.loads(materials.receipt.read_text())
    legacy["schema_version"] = 1
    materials.receipt.write_text(json.dumps(legacy))
    materials.receipt.chmod(0o600)
    with pytest.raises(RuntimeCommissioningError, match="invalid"):
        verify_runtime_commissioning_receipt(
            **_arguments(materials),
            expected_runtime_id="owner-runtime",
            receipt_path=materials.receipt,
            clock=lambda: now,
        )


def test_commissioning_cli_creates_and_verifies_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    materials = _materials(tmp_path, now)
    common = [
        "--checkout",
        str(materials.checkout),
        "--project-config",
        str(materials.project_config),
        "--expected-config-revision",
        materials.revision,
        "--runtime-id",
        "owner-runtime",
        "--dotenv",
        str(materials.dotenv),
        "--dead-man-evidence",
        str(materials.evidence),
        "--trusted-receiver-public-key",
        str(materials.public_key),
    ]
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "aico-commission",
            "create",
            *common,
            "--maximum-evidence-age-seconds",
            "300",
            "--output",
            str(materials.receipt),
        ],
    )
    main()
    created = json.loads(capsys.readouterr().out)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "aico-commission",
            "verify",
            *common,
            "--receipt",
            str(materials.receipt),
            "--expected-receipt-sha256",
            created["receipt_sha256"],
        ],
    )
    main()

    assert json.loads(capsys.readouterr().out)["operation"] == "verify"


async def test_commissioning_health_fails_when_bound_evidence_expires(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 22, 12, 5, tzinfo=UTC)
    materials = _materials(tmp_path, now)
    create_runtime_commissioning_receipt(
        **_arguments(materials),
        runtime_id="owner-runtime",
        maximum_evidence_age_seconds=300,
        output_path=materials.receipt,
        clock=lambda: now,
    )
    current = now
    health = RuntimeCommissioningHealth(
        **_arguments(materials),
        expected_runtime_id="owner-runtime",
        receipt_path=materials.receipt,
        clock=lambda: current,
    )

    assert await health.health_check() is HealthStatus.OK
    current = now + timedelta(minutes=5)
    assert await health.health_check() is HealthStatus.FAILED


def _arguments(materials: Materials) -> dict[str, Any]:
    return {
        "checkout_path": materials.checkout,
        "project_config_path": materials.project_config,
        "expected_config_revision": materials.revision,
        "dotenv_path": materials.dotenv,
        "dead_man_evidence_path": materials.evidence,
        "trusted_receiver_public_key_path": materials.public_key,
    }


def _materials(tmp_path: Path, now: datetime) -> Materials:
    checkout = tmp_path / "checkout"
    project_config = checkout / "config/projects.json"
    project_config.parent.mkdir(parents=True)
    project_config.write_text('{"projects":["aico"]}\n')
    (checkout / "app.py").write_text("print('reviewed')\n")
    (checkout / ".gitignore").write_text(".env\n")
    _git(checkout, "init", "-q")
    _git(checkout, "add", ".")
    _commit(checkout, "initial")
    dotenv = checkout / ".env"
    dotenv.write_text("AICO_TELEGRAM_BOT_TOKEN=owner-private-token\n")
    dotenv.chmod(0o600)
    private = tmp_path / "private"
    private.mkdir()
    private.chmod(0o700)
    evidence = private / "dead-man-evidence.json"
    private_key, public_key = _receiver_key_pair(private)
    payload = json.dumps(_evidence_payload(now), separators=(",", ":")).encode()
    envelope = load_evidence_signer(private_key).sign(payload)
    evidence.write_bytes(serialize_signed_evidence_envelope(envelope))
    evidence.chmod(0o600)
    return Materials(
        checkout=checkout,
        project_config=project_config,
        dotenv=dotenv,
        evidence=evidence,
        public_key=public_key,
        receipt=private / "commissioning.json",
        revision=_git(checkout, "rev-parse", "HEAD").stdout.strip(),
    )


def _receiver_key_pair(directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    private_key = directory / "receiver-private.pem"
    public_key = directory / "receiver-public.pem"
    private_key.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_key.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    os.chmod(private_key, 0o600)
    os.chmod(public_key, 0o644)
    return private_key, public_key


def _evidence_payload(now: datetime) -> dict[str, Any]:
    generated = now - timedelta(seconds=60)
    probe_completed = now - timedelta(seconds=90)
    return {
        "schema_version": 5,
        "runtime_id": "owner-runtime",
        "generated_at": generated.isoformat(),
        "notification_policy": {
            "configured_routes": 2,
            "minimum_acknowledgements": 1,
            "updated_at": (now - timedelta(minutes=3)).isoformat(),
        },
        "notification_probe": {
            "contract": "silent-route-probe-v1",
            "interval_seconds": 900,
            "failure_threshold": 2,
            "max_age_seconds": 1800,
            "pending_probe": None,
            "next_probe_at": (now + timedelta(minutes=15)).isoformat(),
            "last_completed_at": probe_completed.isoformat(),
            "last_acknowledged_routes": [True, True],
            "updated_at": (now - timedelta(minutes=3)).isoformat(),
        },
        "notification_probe_fresh": True,
        "notification_routes": [_healthy_route(slot, probe_completed) for slot in (1, 2)],
        "monitor": None,
        "outages": [
            {
                "outage_id": "outage-1",
                "opened": _event("event-open", "outage_opened", now - timedelta(minutes=2)),
                "resolved": _event(
                    "event-resolved",
                    "outage_resolved",
                    now - timedelta(seconds=100),
                ),
            }
        ],
        "route_health_alerts": [],
    }


def _healthy_route(slot: int, checked_at: datetime) -> dict[str, Any]:
    return {
        "route_slot": slot,
        "status": "healthy",
        "consecutive_failures": 0,
        "consecutive_probe_failures": 0,
        "last_attempt_at": checked_at.isoformat(),
        "last_acknowledged_at": checked_at.isoformat(),
        "last_probe_at": checked_at.isoformat(),
        "last_probe_acknowledged_at": checked_at.isoformat(),
        "updated_at": checked_at.isoformat(),
    }


def _event(event_id: str, event_type: str, occurred_at: datetime) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "reason": "pulse_expired",
        "occurred_at": occurred_at.isoformat(),
        "detected_at": occurred_at.isoformat(),
        "delivered": True,
        "delivery_attempts": 0,
        "next_attempt_at": None,
        "configured_routes": 2,
        "minimum_acknowledgements": 1,
    }


def _commit(checkout: Path, message: str) -> None:
    _git(checkout, "add", ".")
    _git(
        checkout,
        "-c",
        "user.name=AICO Test",
        "-c",
        "user.email=aico@example.invalid",
        "commit",
        "-q",
        "-m",
        message,
    )


def _git(checkout: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    )
