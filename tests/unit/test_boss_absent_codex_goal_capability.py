from __future__ import annotations

import json
from pathlib import Path

import pytest

from aico.app.boss_absent_codex_goal_capability import (
    attest_codex_goal_app_server_schema,
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


def _schema_bundle(root: Path, *, continuation: bool = False) -> None:
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
