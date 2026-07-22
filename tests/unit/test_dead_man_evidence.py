from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from aico.app.dead_man_evidence_cli import (
    DeadManEvidenceVerificationError,
    main,
    verify_evidence_bytes,
)
from aico.app.dead_man_receiver import (
    DeadManEvidenceBundle,
    DeadManNotificationCoordinator,
    SQLiteDeadManReceiverStore,
)
from aico.app.runtime_liveness import RuntimeLivenessPulse


class RecordingSink:
    async def send(self, event: object) -> None:
        _ = event


class FailingSink:
    async def send(self, event: object) -> None:
        _ = event
        raise RuntimeError("private downstream failure")


async def test_evidence_survives_restart_and_records_local_delivery(tmp_path: Path) -> None:
    path = tmp_path / "receiver.db"
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    event_ids = iter(("event-open", "event-resolved"))
    store = SQLiteDeadManReceiverStore(
        path,
        outage_id_factory=lambda: "outage-1",
        event_id_factory=lambda: next(event_ids),
    )
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    store.accept(
        _pulse(sequence=1, sent_at=now + timedelta(seconds=181)),
        received_at=now + timedelta(seconds=181),
    )
    await DeadManNotificationCoordinator(store=store, sink=RecordingSink()).check(
        now=now + timedelta(seconds=181)
    )

    bundle = SQLiteDeadManReceiverStore(path).export_evidence(
        "owner-runtime",
        generated_at=now + timedelta(seconds=182),
        max_outages=20,
    )

    assert bundle.schema_version == 5
    assert bundle.notification_policy.configured_routes == 1
    assert bundle.runtime_id == "owner-runtime"
    assert bundle.monitor is not None
    assert len(bundle.outages) == 1
    outage = bundle.outages[0]
    assert outage.outage_id == "outage-1"
    assert outage.opened.event_id == "event-open"
    assert outage.opened.delivered is True
    assert outage.resolved is not None
    assert outage.resolved.event_id == "event-resolved"
    assert outage.resolved.delivered is True


async def test_evidence_records_pending_retry_without_failure_detail(tmp_path: Path) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = SQLiteDeadManReceiverStore(
        tmp_path / "receiver.db",
        outage_id_factory=lambda: "outage-1",
        event_id_factory=lambda: "event-open",
    )
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    await DeadManNotificationCoordinator(store=store, sink=FailingSink()).check(
        now=now + timedelta(seconds=180)
    )

    bundle = store.export_evidence(
        "owner-runtime",
        generated_at=now + timedelta(seconds=181),
        max_outages=20,
    )

    opened = bundle.outages[0].opened
    assert opened.delivered is False
    assert opened.delivery_attempts == 1
    assert opened.next_attempt_at == now + timedelta(seconds=240)
    assert "private downstream" not in bundle.model_dump_json()


def test_evidence_limit_keeps_recent_outages_whole_and_survives_disarm(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    outage_ids = iter(("outage-1", "outage-2", "outage-3"))
    event_ids = iter(
        (
            "event-open-1",
            "event-resolved-1",
            "event-open-2",
            "event-resolved-2",
            "event-open-3",
            "event-resolved-3",
        )
    )
    store = SQLiteDeadManReceiverStore(
        tmp_path / "receiver.db",
        outage_id_factory=lambda: next(outage_ids),
        event_id_factory=lambda: next(event_ids),
    )
    store.arm("owner-runtime", expires_after_seconds=180, armed_at=now)
    for sequence, offset in enumerate((181, 362, 543), start=1):
        store.evaluate(now=now + timedelta(seconds=offset - 1))
        store.accept(
            _pulse(sequence=sequence, sent_at=now + timedelta(seconds=offset)),
            received_at=now + timedelta(seconds=offset),
        )
    store.disarm("owner-runtime")

    bundle = store.export_evidence(
        "owner-runtime",
        generated_at=now + timedelta(seconds=544),
        max_outages=2,
    )

    assert bundle.monitor is None
    assert [outage.outage_id for outage in bundle.outages] == ["outage-2", "outage-3"]
    assert all(outage.resolved is not None for outage in bundle.outages)


def test_evidence_model_rejects_resolved_before_opened_and_secret_extra() -> None:
    payload = _valid_bundle_payload()
    outage = payload["outages"][0]
    assert isinstance(outage, dict)
    outage["opened"], outage["resolved"] = outage["resolved"], outage["opened"]
    with pytest.raises(ValidationError):
        DeadManEvidenceBundle.model_validate(payload)

    payload = _valid_bundle_payload()
    payload["notification_policy"]["minimum_acknowledgements"] = 3
    with pytest.raises(ValidationError):
        DeadManEvidenceBundle.model_validate(payload)

    payload = _valid_bundle_payload()
    payload["notification_url"] = "https://private.example/path"
    with pytest.raises(ValidationError):
        DeadManEvidenceBundle.model_validate(payload)

    payload = _valid_bundle_payload()
    opened = payload["outages"][0]["opened"]
    assert isinstance(opened, dict)
    opened["acknowledged_routes"] = [True]
    opened["last_attempt_at"] = "2026-07-21T12:03:00Z"
    with pytest.raises(ValidationError, match="acknowledgements"):
        DeadManEvidenceBundle.model_validate(payload)


def test_offline_verifier_emits_exact_byte_hash_and_enforces_acceptance() -> None:
    raw = json.dumps(_valid_bundle_payload(), separators=(",", ":")).encode()

    summary = verify_evidence_bytes(
        raw,
        expected_runtime_id="owner-runtime",
        minimum_complete_outages=1,
        require_all_delivered=True,
    )

    assert summary.status == "valid"
    assert summary.complete_outages == 1
    assert summary.delivered_events == 2
    assert summary.sha256 == hashlib.sha256(raw).hexdigest()

    with pytest.raises(DeadManEvidenceVerificationError, match="runtime"):
        verify_evidence_bytes(raw, expected_runtime_id="other-runtime")
    with pytest.raises(DeadManEvidenceVerificationError, match="completed"):
        verify_evidence_bytes(raw, minimum_complete_outages=2)

    payload = _valid_bundle_payload()
    opened = payload["outages"][0]["opened"]
    resolved = payload["outages"][0]["resolved"]
    assert isinstance(opened, dict)
    assert isinstance(resolved, dict)
    opened["delivered"] = False
    resolved["delivered"] = False
    with pytest.raises(DeadManEvidenceVerificationError, match="pending"):
        verify_evidence_bytes(
            json.dumps(payload).encode(),
            require_all_delivered=True,
        )


def test_offline_verifier_enforces_bounded_current_external_evidence() -> None:
    now = datetime(2026, 7, 21, 12, 5, tzinfo=UTC)
    payload = _valid_bundle_payload()
    probe = payload["notification_probe"]
    assert isinstance(probe, dict)
    probe.update(
        {
            "contract": "silent-route-probe-v1",
            "next_probe_at": "2026-07-21T12:19:00Z",
            "last_completed_at": "2026-07-21T12:03:00Z",
            "last_acknowledged_routes": [True, True],
            "updated_at": "2026-07-21T12:00:00Z",
        }
    )
    payload["notification_probe_fresh"] = True
    routes = payload["notification_routes"]
    assert isinstance(routes, list)
    for route in routes:
        assert isinstance(route, dict)
        route.update(
            {
                "status": "healthy",
                "last_attempt_at": "2026-07-21T12:03:00Z",
                "last_acknowledged_at": "2026-07-21T12:03:00Z",
                "last_probe_at": "2026-07-21T12:03:00Z",
                "last_probe_acknowledged_at": "2026-07-21T12:03:00Z",
                "updated_at": "2026-07-21T12:03:00Z",
            }
        )
    raw = json.dumps(payload).encode()

    verify_evidence_bytes(
        raw,
        maximum_evidence_age_seconds=120,
        require_fresh_notification_probe=True,
        require_all_routes_healthy=True,
        now=now,
    )

    with pytest.raises(DeadManEvidenceVerificationError, match="freshness requirement"):
        verify_evidence_bytes(raw, maximum_evidence_age_seconds=30, now=now)
    for invalid_age in (0, -1, float("nan"), float("inf")):
        with pytest.raises(DeadManEvidenceVerificationError, match="must be positive"):
            verify_evidence_bytes(
                raw,
                maximum_evidence_age_seconds=invalid_age,
                now=now,
            )
    with pytest.raises(DeadManEvidenceVerificationError, match="future"):
        verify_evidence_bytes(
            raw,
            maximum_evidence_age_seconds=120,
            now=datetime(2026, 7, 21, 12, 3, tzinfo=UTC),
        )
    with pytest.raises(DeadManEvidenceVerificationError, match="probe freshness"):
        verify_evidence_bytes(
            raw,
            require_fresh_notification_probe=True,
            now=datetime(2026, 7, 21, 12, 40, tzinfo=UTC),
        )

    unproven_probe_payload = _valid_bundle_payload()
    unproven_probe = unproven_probe_payload["notification_probe"]
    assert isinstance(unproven_probe, dict)
    unproven_probe.update(
        {
            "contract": "silent-route-probe-v1",
            "next_probe_at": "2026-07-21T12:19:00Z",
            "updated_at": "2026-07-21T12:03:00Z",
        }
    )
    unproven_probe_payload["notification_probe_fresh"] = True
    with pytest.raises(DeadManEvidenceVerificationError, match="probe freshness"):
        verify_evidence_bytes(
            json.dumps(unproven_probe_payload).encode(),
            require_fresh_notification_probe=True,
            now=now,
        )

    payload["notification_probe_fresh"] = False
    probe["last_completed_at"] = "2026-07-21T11:00:00Z"
    with pytest.raises(DeadManEvidenceVerificationError, match="probe freshness"):
        verify_evidence_bytes(
            json.dumps(payload).encode(),
            require_fresh_notification_probe=True,
            now=now,
        )

    payload = _valid_bundle_payload()
    with pytest.raises(DeadManEvidenceVerificationError, match="route health"):
        verify_evidence_bytes(
            json.dumps(payload).encode(),
            require_all_routes_healthy=True,
            now=now,
        )

    payload = _valid_bundle_payload()
    payload["route_health_alerts"] = [
        {
            "event_id": "route-alert-1",
            "event_type": "notification_route_degraded",
            "route_slot": 2,
            "triggering_event_id": "event-open",
            "runtime_id": "owner-runtime",
            "occurred_at": "2026-07-21T12:03:00Z",
            "delivered": False,
            "delivery_attempts": 1,
            "next_attempt_at": "2026-07-21T12:04:00Z",
        }
    ]
    with pytest.raises(DeadManEvidenceVerificationError, match="pending"):
        verify_evidence_bytes(
            json.dumps(payload).encode(),
            require_all_delivered=True,
        )


def test_evidence_cli_reads_local_bundle_and_prints_compact_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "evidence.json"
    raw = json.dumps(_valid_bundle_payload(), separators=(",", ":")).encode()
    path.write_bytes(raw)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "aico-dead-man-evidence",
            str(path),
            "--runtime-id",
            "owner-runtime",
            "--minimum-complete-outages",
            "1",
            "--require-all-delivered",
        ],
    )

    main()

    summary = json.loads(capsys.readouterr().out)
    assert summary == {
        "status": "valid",
        "schema_version": 5,
        "runtime_id": "owner-runtime",
        "complete_outages": 1,
        "event_count": 2,
        "delivered_events": 2,
        "route_health_alerts": 0,
        "delivered_route_health_alerts": 0,
        "degraded_routes": 0,
        "notification_probe_enabled": False,
        "notification_probe_pending": False,
        "notification_probe_fresh": False,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "payload_sha256": hashlib.sha256(raw).hexdigest(),
        "receiver_signature_verified": False,
        "receiver_public_key_sha256": None,
    }


def test_evidence_cli_accepts_composed_current_health_requirements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    current = datetime.now(UTC).replace(microsecond=0)
    payload = _valid_bundle_payload()
    payload["generated_at"] = current.isoformat()
    probe = payload["notification_probe"]
    assert isinstance(probe, dict)
    probe.update(
        {
            "contract": "silent-route-probe-v1",
            "next_probe_at": (current + timedelta(minutes=15)).isoformat(),
            "last_completed_at": current.isoformat(),
            "last_acknowledged_routes": [True, True],
            "updated_at": current.isoformat(),
        }
    )
    payload["notification_probe_fresh"] = True
    routes = payload["notification_routes"]
    assert isinstance(routes, list)
    for route in routes:
        assert isinstance(route, dict)
        route.update(
            {
                "status": "healthy",
                "last_attempt_at": current.isoformat(),
                "last_acknowledged_at": current.isoformat(),
                "last_probe_at": current.isoformat(),
                "last_probe_acknowledged_at": current.isoformat(),
                "updated_at": current.isoformat(),
            }
        )
    path = tmp_path / "current-evidence.json"
    path.write_text(json.dumps(payload))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "aico-dead-man-evidence",
            str(path),
            "--runtime-id",
            "owner-runtime",
            "--minimum-complete-outages",
            "1",
            "--require-all-delivered",
            "--maximum-evidence-age-seconds",
            "300",
            "--require-fresh-notification-probe",
            "--require-all-routes-healthy",
        ],
    )

    main()

    assert json.loads(capsys.readouterr().out)["status"] == "valid"


def _valid_bundle_payload() -> dict[str, Any]:
    return {
        "schema_version": 5,
        "runtime_id": "owner-runtime",
        "generated_at": "2026-07-21T12:04:00Z",
        "notification_policy": {
            "configured_routes": 2,
            "minimum_acknowledgements": 1,
            "updated_at": "2026-07-21T12:00:00Z",
        },
        "notification_probe": {
            "contract": "disabled",
            "interval_seconds": 900,
            "failure_threshold": 2,
            "max_age_seconds": 1800,
            "pending_probe": None,
            "next_probe_at": None,
            "last_completed_at": None,
            "last_acknowledged_routes": None,
            "updated_at": "1970-01-01T00:00:00Z",
        },
        "notification_probe_fresh": False,
        "notification_routes": [
            {
                "route_slot": 1,
                "status": "unknown",
                "consecutive_failures": 0,
                "consecutive_probe_failures": 0,
                "last_attempt_at": None,
                "last_acknowledged_at": None,
                "last_probe_at": None,
                "last_probe_acknowledged_at": None,
                "updated_at": "1970-01-01T00:00:00Z",
            },
            {
                "route_slot": 2,
                "status": "unknown",
                "consecutive_failures": 0,
                "consecutive_probe_failures": 0,
                "last_attempt_at": None,
                "last_acknowledged_at": None,
                "last_probe_at": None,
                "last_probe_acknowledged_at": None,
                "updated_at": "1970-01-01T00:00:00Z",
            },
        ],
        "monitor": None,
        "outages": [
            {
                "outage_id": "outage-1",
                "opened": {
                    "event_id": "event-open",
                    "event_type": "outage_opened",
                    "reason": "pulse_expired",
                    "occurred_at": "2026-07-21T12:03:00Z",
                    "detected_at": "2026-07-21T12:03:00Z",
                    "delivered": True,
                    "delivery_attempts": 0,
                    "next_attempt_at": None,
                    "configured_routes": 2,
                    "minimum_acknowledgements": 1,
                },
                "resolved": {
                    "event_id": "event-resolved",
                    "event_type": "outage_resolved",
                    "reason": "pulse_expired",
                    "occurred_at": "2026-07-21T12:03:01Z",
                    "detected_at": "2026-07-21T12:03:01Z",
                    "delivered": True,
                    "delivery_attempts": 0,
                    "next_attempt_at": None,
                    "configured_routes": 2,
                    "minimum_acknowledgements": 1,
                },
            }
        ],
        "route_health_alerts": [],
    }


def _pulse(*, sequence: int, sent_at: datetime) -> RuntimeLivenessPulse:
    return RuntimeLivenessPulse(
        runtime_id="owner-runtime",
        boot_id="boot-1",
        sequence=sequence,
        sent_at=sent_at,
        interval_seconds=60,
        expires_after_seconds=180,
    )
