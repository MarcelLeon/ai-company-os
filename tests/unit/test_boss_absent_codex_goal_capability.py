from __future__ import annotations

import json
from pathlib import Path

import pytest

from aico.app.boss_absent_codex_goal_capability import (
    CodexCodeSignatureIdentity,
    CodexGoalHostSurfaceReceipt,
    attest_codex_goal_app_server_schema,
    attest_codex_goal_native_host_candidate,
)

_CONTRACT_SHA = "a" * 64


def test_app_server_schema_attests_control_plane_but_refuses_native_host(
    tmp_path: Path,
) -> None:
    _schema_bundle(tmp_path)

    receipt = attest_codex_goal_app_server_schema(
        tmp_path,
        contract_sha256=_CONTRACT_SHA,
        codex_cli_version="0.144.5",
    )

    assert receipt.goal_control_plane_present
    assert receipt.turn_start_requires_client_input
    assert receipt.remote_control_transport_present
    assert not receipt.native_continuation_candidates
    assert not receipt.formal_run_admitted
    assert receipt.blocking_reasons == (
        "native_continuation_surface_absent",
        "native_host_build_receipt_required",
    )


def test_candidate_continuation_method_still_requires_native_host_build_receipt(
    tmp_path: Path,
) -> None:
    _schema_bundle(tmp_path, continuation=True)

    receipt = attest_codex_goal_app_server_schema(
        tmp_path,
        contract_sha256=_CONTRACT_SHA,
        codex_cli_version="0.145.0",
    )

    assert receipt.native_continuation_candidates == ("thread/goal/continue",)
    assert receipt.blocking_reasons == ("native_host_build_receipt_required",)
    assert not receipt.formal_run_admitted


def test_goal_fork_semantics_are_native_continuation_surface_evidence(
    tmp_path: Path,
) -> None:
    _schema_bundle(tmp_path, goal_fork_continuation=True)

    receipt = attest_codex_goal_app_server_schema(
        tmp_path,
        contract_sha256=_CONTRACT_SHA,
        codex_cli_version="0.145.0-alpha.30",
    )

    assert receipt.native_continuation_candidates == ("thread/fork.deferGoalContinuation",)
    assert receipt.blocking_reasons == ("native_host_build_receipt_required",)
    assert not receipt.formal_run_admitted


def test_signed_native_host_candidate_still_requires_live_isolated_observation() -> None:
    surface = CodexGoalHostSurfaceReceipt(
        contract_sha256=_CONTRACT_SHA,
        codex_cli_version="0.145.0-alpha.30",
        schema_bundle_sha256="b" * 64,
        remote_control_transport_present=True,
        native_continuation_candidates=("thread/fork.deferGoalContinuation",),
        blocking_reasons=("native_host_build_receipt_required",),
    )
    app_signature = CodexCodeSignatureIdentity(
        identifier="com.openai.codex",
        team_identifier="2DC432GLL2",
        cdhash_sha256="c" * 64,
    )
    cli_signature = CodexCodeSignatureIdentity(
        identifier="codex",
        team_identifier="2DC432GLL2",
        cdhash_sha256="d" * 64,
    )

    receipt = attest_codex_goal_native_host_candidate(
        surface,
        bundle_identifier="com.openai.codex",
        app_version="26.715.72359",
        app_build="5718",
        app_signature=app_signature,
        cli_signature=cli_signature,
        expected_team_identifier="2DC432GLL2",
        notarization_ticket_stapled=True,
    )

    assert receipt.first_party_signature_verified
    assert receipt.native_continuation_surface_present
    assert not receipt.live_native_continuation_observed
    assert not receipt.formal_run_admitted
    assert receipt.blocking_reasons == (
        "live_native_continuation_observation_required",
        "isolated_run_state_observation_required",
    )


@pytest.mark.parametrize(
    ("bundle_identifier", "team_identifier", "notarized"),
    (
        ("com.example.codex", "2DC432GLL2", True),
        ("com.openai.codex", "ABCDEFGHIJ", True),
        ("com.openai.codex", "2DC432GLL2", False),
    ),
)
def test_native_host_candidate_rejects_wrong_identity(
    bundle_identifier: str,
    team_identifier: str,
    notarized: bool,
) -> None:
    surface = CodexGoalHostSurfaceReceipt(
        contract_sha256=_CONTRACT_SHA,
        codex_cli_version="0.145.0-alpha.30",
        schema_bundle_sha256="b" * 64,
        remote_control_transport_present=True,
        native_continuation_candidates=("thread/fork.deferGoalContinuation",),
        blocking_reasons=("native_host_build_receipt_required",),
    )
    app_signature = CodexCodeSignatureIdentity(
        identifier=bundle_identifier,
        team_identifier=team_identifier,
        cdhash_sha256="c" * 64,
    )
    cli_signature = CodexCodeSignatureIdentity(
        identifier="codex",
        team_identifier=team_identifier,
        cdhash_sha256="d" * 64,
    )

    with pytest.raises(ValueError, match="signed build"):
        attest_codex_goal_native_host_candidate(
            surface,
            bundle_identifier=bundle_identifier,
            app_version="26.715.72359",
            app_build="5718",
            app_signature=app_signature,
            cli_signature=cli_signature,
            expected_team_identifier="2DC432GLL2",
            notarization_ticket_stapled=notarized,
        )


def test_schema_attestation_rejects_missing_control_plane_or_explicit_input(
    tmp_path: Path,
) -> None:
    _schema_bundle(tmp_path)
    (tmp_path / "ClientRequest.json").write_text(
        json.dumps({"methods": ["thread/goal/get", "turn/start"]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="control plane"):
        attest_codex_goal_app_server_schema(
            tmp_path,
            contract_sha256=_CONTRACT_SHA,
            codex_cli_version="0.144.5",
        )

    _schema_bundle(tmp_path)
    (tmp_path / "v2" / "TurnStartParams.json").write_text(
        json.dumps({"required": ["threadId"]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="explicit client input"):
        attest_codex_goal_app_server_schema(
            tmp_path,
            contract_sha256=_CONTRACT_SHA,
            codex_cli_version="0.144.5",
        )


def _schema_bundle(
    root: Path,
    *,
    continuation: bool = False,
    goal_fork_continuation: bool = False,
) -> None:
    methods = [
        "thread/goal/set",
        "thread/goal/get",
        "thread/goal/clear",
        "thread/resume",
        "turn/start",
        "remoteControl/status/read",
    ]
    if continuation:
        methods.append("thread/goal/continue")
    if goal_fork_continuation:
        methods.append("thread/fork")
    root.mkdir(parents=True, exist_ok=True)
    (root / "ClientRequest.json").write_text(
        json.dumps({"methods": methods}, sort_keys=True),
        encoding="utf-8",
    )
    v2 = root / "v2"
    v2.mkdir(exist_ok=True)
    (v2 / "TurnStartParams.json").write_text(
        json.dumps({"required": ["input", "threadId"]}, sort_keys=True),
        encoding="utf-8",
    )
    if goal_fork_continuation:
        (v2 / "ThreadForkParams.json").write_text(
            json.dumps(
                {
                    "properties": {
                        "deferGoalContinuation": {
                            "type": "boolean",
                            "description": (
                                "When true, carry the source thread's current goal into "
                                "the fork without starting its initial automatic continuation. "
                                "The next explicit turn owns the goal lifecycle, and normal "
                                "automatic continuation resumes after it."
                            ),
                        }
                    }
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
