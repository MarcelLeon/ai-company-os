from __future__ import annotations

import hashlib
import io
import json
import stat
import subprocess
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aico.app.provider_auth_probe import (
    ProviderAuthenticationProbeError,
    ProviderProbeResult,
)
from aico.app.provider_authentication import (
    ProviderAuthenticationError,
    create_provider_authentication_receipt,
    verify_provider_authentication_receipt,
)
from aico.app.recovery_cli import run
from aico.app.recovery_reinjection import (
    RecoveryReinjectionError,
    create_recovery_reinjection_receipt,
    verify_recovery_reinjection_receipt,
)
from aico.app.recovery_set import (
    RECOVERY_SET_AUDIT_MEMBER,
    RECOVERY_SET_MANIFEST_MEMBER,
    RECOVERY_SET_MEMORY_MEMBER,
    RECOVERY_SET_STATE_MEMBER,
    RecoverySetError,
    RecoverySetSummary,
    create_recovery_set,
    drill_recovery_set,
    verify_recovery_checkout,
    verify_recovery_set,
)
from aico.core import (
    AuditEvent,
    AuditEventType,
    InMemoryAuditLog,
    JsonlAuditSink,
    JsonlMemoryStore,
    MemoryAtom,
    MemoryEvidence,
    MemoryScope,
    Task,
)
from aico.core.task_store import SQLiteTaskStateStore


class _SuccessfulProviderProbe:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def execute(self, challenge: str) -> ProviderProbeResult:
        self._calls.append(challenge)
        return ProviderProbeResult()


class _FailedProviderProbe:
    def execute(self, challenge: str) -> ProviderProbeResult:
        raise ProviderAuthenticationProbeError(f"private failure: {challenge}")


def test_recovery_set_captures_fixed_core_scope_and_verifies_offline(tmp_path: Path) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(
        tmp_path, secret="merchant private operation"
    )
    output = tmp_path / "exports" / "core-recovery.zip"
    times = iter(_times())

    created = _capture(
        state,
        audit,
        memory,
        output,
        checkout,
        project,
        persona,
        clock=lambda: next(times),
    )
    verified = verify_recovery_set(output, expected_sha256=created.sha256)

    assert created.operation == "capture"
    assert verified.operation == "verify"
    assert created.sha256 == verified.sha256
    assert created.capture_window_seconds == 6
    assert created.scope == "core_state_audit_memory_config_revision_reinjection"
    assert created.global_transaction is False
    assert created.business_restore_ready is False
    assert created.included_components == ("state", "audit", "memory")
    assert created.unresolved_assets == ()
    assert created.post_restore_evidence_assets == (
        "project_config",
        "persona_config",
        "control_plane_secrets",
        "standing_grant",
        "ai_provider_authentication",
        "dead_man_receiver_state",
    )
    assert created.state_table_counts["task_records"] == 1
    assert created.audit_event_count == 1
    assert created.memory_record_count == 1
    assert created.config_count == 2
    assert created.persona_source == "tracked_file"
    assert created.runtime_channel == "telegram"
    assert created.secret_slot_count == 1
    assert created.standing_grant_required is False
    assert created.provider_names == ("claude-code",)
    assert created.provider_count == 1
    assert (
        verify_recovery_checkout(
            output,
            expected_sha256=created.sha256,
            checkout_path=checkout,
        ).revision
        == created.config_revision
    )
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {
            RECOVERY_SET_MANIFEST_MEMBER,
            RECOVERY_SET_STATE_MEMBER,
            RECOVERY_SET_AUDIT_MEMBER,
            RECOVERY_SET_MEMORY_MEMBER,
        }
        manifest = archive.read(RECOVERY_SET_MANIFEST_MEMBER).decode()
        assets = json.loads(manifest)["assets"]
        receiver = next(asset for asset in assets if asset["name"] == "dead_man_receiver_state")
        assert receiver == {
            "name": "dead_man_receiver_state",
            "included": False,
            "recovery_contract_ready": True,
            "required_for_business_restore": True,
            "requires_post_restore_evidence": True,
            "disposition": "external_component_recovery",
        }
        provider = next(asset for asset in assets if asset["name"] == "ai_provider_authentication")
        assert provider["recovery_contract_ready"] is True
        assert provider["disposition"] == "post_restore_live_probe"
    assert "sequential_component_snapshots" in manifest
    assert '"memory"' in manifest
    assert "merchant private operation" not in manifest
    assert "test-private-telegram-token" not in manifest
    assert str(state) not in manifest
    assert str(audit) not in manifest
    assert str(memory) not in manifest


def test_recovery_set_drills_both_components_without_touching_live(tmp_path: Path) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(
        tmp_path, secret="private customer task"
    )
    output = tmp_path / "core-recovery.zip"
    workspace = tmp_path / "workspace"
    report = tmp_path / "evidence" / "core-drill.json"
    workspace.mkdir()
    created = _capture(state, audit, memory, output, checkout, project, persona)
    state_before = state.read_bytes()
    audit_before = audit.read_bytes()
    memory_before = memory.read_bytes()

    drilled = drill_recovery_set(
        output,
        expected_sha256=created.sha256,
        workspace=workspace,
        report_path=report,
        clock=lambda: datetime(2026, 7, 22, 12, tzinfo=UTC),
    )

    assert drilled.operation == "drill"
    assert drilled.backup_sha256 == created.sha256
    assert drilled.business_restore_ready is False
    assert drilled.config_revision == created.config_revision
    assert drilled.secret_slot_count == 1
    assert drilled.standing_grant_required is False
    assert drilled.provider_names == ("claude-code",)
    assert drilled.provider_count == 1
    assert drilled.report_name == report.name
    assert tuple(workspace.iterdir()) == ()
    assert state.read_bytes() == state_before
    assert audit.read_bytes() == audit_before
    assert memory.read_bytes() == memory_before
    assert stat.S_IMODE(report.stat().st_mode) == 0o600
    rendered = report.read_text()
    assert json.loads(rendered) == drilled.model_dump(mode="json")
    assert "private customer task" not in rendered
    assert str(state) not in rendered


def test_reinjection_receipt_is_owner_only_secret_free_and_reverifiable(
    tmp_path: Path,
) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(tmp_path)
    recovery_set = tmp_path / "core-recovery.zip"
    receipt = tmp_path / "evidence/reinjection.json"
    created = _capture(state, audit, memory, recovery_set, checkout, project, persona)

    issued = create_recovery_reinjection_receipt(
        recovery_set,
        expected_recovery_set_sha256=created.sha256,
        checkout_path=checkout,
        output_path=receipt,
        owner_decision_ref="incident-2026-07-22-001",
        clock=lambda: datetime(2026, 7, 22, 13, tzinfo=UTC),
    )

    assert issued.operation == "reinjection-receipt"
    assert issued.recovery_set_sha256 == created.sha256
    assert issued.secret_slot_count == 1
    assert issued.standing_grant_count == 0
    assert issued.owner_decision_ref == "incident-2026-07-22-001"
    assert issued.business_restore_ready is False
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    rendered = receipt.read_text()
    assert '"external_authentication_live_verified":false' in rendered
    assert "test-private-telegram-token" not in rendered
    assert str(checkout) not in rendered
    assert "owner-test" not in rendered
    assert "chat-test" not in rendered

    env_path = checkout / ".env"
    env_path.write_text(
        env_path.read_text().replace(
            "test-private-telegram-token",
            "rotated-private-telegram-token",
        )
    )
    verified = verify_recovery_reinjection_receipt(
        recovery_set,
        expected_recovery_set_sha256=created.sha256,
        checkout_path=checkout,
        receipt_path=receipt,
        expected_receipt_sha256=issued.receipt_sha256,
    )
    assert verified.operation == "verify-reinjection"
    assert verified.receipt_sha256 == issued.receipt_sha256


def test_provider_auth_receipt_is_live_bounded_secret_free_and_reverifiable(
    tmp_path: Path,
) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(tmp_path)
    recovery_set = tmp_path / "core-recovery.zip"
    reinjection_path = tmp_path / "evidence/reinjection.json"
    provider_path = tmp_path / "evidence/provider-auth.json"
    env_path = checkout / ".env"
    env_path.write_text(
        env_path.read_text()
        + "AICO_ENABLE_CODEX_ADAPTER=true\n"
        + "AICO_CODEX_COMMAND=codex --ask-for-approval never exec --sandbox read-only\n"
    )
    created = _capture(state, audit, memory, recovery_set, checkout, project, persona)
    reinjection = create_recovery_reinjection_receipt(
        recovery_set,
        expected_recovery_set_sha256=created.sha256,
        checkout_path=checkout,
        output_path=reinjection_path,
        owner_decision_ref="incident-2026-07-22-provider",
    )
    calls: list[str] = []
    challenges = iter(("aico-auth-v1-" + "d" * 48, "aico-auth-v1-" + "e" * 48))

    issued = create_provider_authentication_receipt(
        recovery_set,
        expected_recovery_set_sha256=created.sha256,
        checkout_path=checkout,
        reinjection_receipt_path=reinjection_path,
        expected_reinjection_receipt_sha256=reinjection.receipt_sha256,
        output_path=provider_path,
        probe_factory=lambda _provider, _command: _SuccessfulProviderProbe(calls),
        challenge_factory=lambda: next(challenges),
        clock=lambda: datetime(2026, 7, 22, 14, tzinfo=UTC),
    )

    assert issued.operation == "provider-auth-receipt"
    assert issued.provider_names == ("claude-code", "codex")
    assert issued.provider_count == 2
    assert issued.live_probe_executed is True
    assert issued.live_probe_replayed is False
    assert calls == ["aico-auth-v1-" + "d" * 48, "aico-auth-v1-" + "e" * 48]
    assert stat.S_IMODE(provider_path.stat().st_mode) == 0o600
    rendered = provider_path.read_text()
    assert all(challenge not in rendered for challenge in calls)
    assert "test-private-telegram-token" not in rendered
    assert str(checkout) not in rendered
    assert '"prompts_recorded":false' in rendered
    assert '"provider_outputs_recorded":false' in rendered

    verified = verify_provider_authentication_receipt(
        recovery_set,
        expected_recovery_set_sha256=created.sha256,
        checkout_path=checkout,
        reinjection_receipt_path=reinjection_path,
        expected_reinjection_receipt_sha256=reinjection.receipt_sha256,
        receipt_path=provider_path,
        expected_receipt_sha256=issued.receipt_sha256,
        clock=lambda: datetime(2026, 7, 22, 14, 10, tzinfo=UTC),
    )
    assert verified.operation == "verify-provider-auth"
    assert verified.live_probe_executed is False
    assert verified.live_probe_replayed is False


def test_provider_auth_receipt_rejects_failure_expiry_and_command_drift(
    tmp_path: Path,
) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(tmp_path)
    recovery_set = tmp_path / "core-recovery.zip"
    reinjection_path = tmp_path / "reinjection.json"
    failed_path = tmp_path / "failed-provider-auth.json"
    provider_path = tmp_path / "provider-auth.json"
    created = _capture(state, audit, memory, recovery_set, checkout, project, persona)
    reinjection = create_recovery_reinjection_receipt(
        recovery_set,
        expected_recovery_set_sha256=created.sha256,
        checkout_path=checkout,
        output_path=reinjection_path,
        owner_decision_ref="incident-2026-07-22-provider-failure",
    )
    challenge = "aico-auth-v1-" + "e" * 48

    with pytest.raises(ProviderAuthenticationError, match="creation failed") as failure:
        create_provider_authentication_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            reinjection_receipt_path=reinjection_path,
            expected_reinjection_receipt_sha256=reinjection.receipt_sha256,
            output_path=failed_path,
            probe_factory=lambda _provider, _command: _FailedProviderProbe(),
            challenge_factory=lambda: challenge,
        )
    assert challenge not in str(failure.value)
    assert not failed_path.exists()

    issued = create_provider_authentication_receipt(
        recovery_set,
        expected_recovery_set_sha256=created.sha256,
        checkout_path=checkout,
        reinjection_receipt_path=reinjection_path,
        expected_reinjection_receipt_sha256=reinjection.receipt_sha256,
        output_path=provider_path,
        probe_factory=lambda _provider, _command: _SuccessfulProviderProbe([]),
        challenge_factory=lambda: challenge,
        clock=lambda: datetime(2026, 7, 22, 15, tzinfo=UTC),
    )
    with pytest.raises(ProviderAuthenticationError, match="SHA-256 does not match"):
        verify_provider_authentication_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            reinjection_receipt_path=reinjection_path,
            expected_reinjection_receipt_sha256=reinjection.receipt_sha256,
            receipt_path=provider_path,
            expected_receipt_sha256="0" * 64,
            clock=lambda: datetime(2026, 7, 22, 15, 10, tzinfo=UTC),
        )
    with pytest.raises(ProviderAuthenticationError, match="stale"):
        verify_provider_authentication_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            reinjection_receipt_path=reinjection_path,
            expected_reinjection_receipt_sha256=reinjection.receipt_sha256,
            receipt_path=provider_path,
            expected_receipt_sha256=issued.receipt_sha256,
            clock=lambda: datetime(2026, 7, 22, 15, 31, tzinfo=UTC),
        )

    env_path = checkout / ".env"
    env_path.write_text(env_path.read_text() + "AICO_CLAUDE_COMMAND=/opt/bin/claude\n")
    with pytest.raises(ProviderAuthenticationError, match="stale"):
        verify_provider_authentication_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            reinjection_receipt_path=reinjection_path,
            expected_reinjection_receipt_sha256=reinjection.receipt_sha256,
            receipt_path=provider_path,
            expected_receipt_sha256=issued.receipt_sha256,
            clock=lambda: datetime(2026, 7, 22, 15, 10, tzinfo=UTC),
        )


def test_reinjection_receipt_rejects_missing_slot_forgery_and_checkout_output(
    tmp_path: Path,
) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(tmp_path)
    recovery_set = tmp_path / "core-recovery.zip"
    receipt = tmp_path / "reinjection.json"
    created = _capture(state, audit, memory, recovery_set, checkout, project, persona)
    env_path = checkout / ".env"
    env_path.write_text(env_path.read_text().replace("test-private-telegram-token", ""))

    with pytest.raises(RecoveryReinjectionError, match="integrity"):
        create_recovery_reinjection_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            output_path=receipt,
            owner_decision_ref="incident-2026-07-22-002",
        )
    assert not receipt.exists()

    env_path.write_text(
        env_path.read_text().replace(
            "AICO_TELEGRAM_BOT_TOKEN=",
            "AICO_TELEGRAM_BOT_TOKEN=restored-private-token",
        )
    )
    with pytest.raises(RecoveryReinjectionError, match="creation failed"):
        create_recovery_reinjection_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            output_path=receipt,
            owner_decision_ref="example-decision",
        )
    assert not receipt.exists()
    issued = create_recovery_reinjection_receipt(
        recovery_set,
        expected_recovery_set_sha256=created.sha256,
        checkout_path=checkout,
        output_path=receipt,
        owner_decision_ref="incident-2026-07-22-002",
    )
    forged = json.loads(receipt.read_text())
    forged["channel"] = "feishu"
    forged["secret_slots"] = [
        "AICO_FEISHU_APP_SECRET",
        "AICO_FEISHU_VERIFICATION_TOKEN",
    ]
    forged["secret_slot_count"] = 2
    receipt.write_bytes(_json_bytes(forged))
    receipt.chmod(0o600)
    with pytest.raises(RecoveryReinjectionError, match="does not match"):
        verify_recovery_reinjection_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            receipt_path=receipt,
            expected_receipt_sha256=_sha256(receipt),
        )

    with pytest.raises(RecoveryReinjectionError, match="outside"):
        create_recovery_reinjection_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            output_path=checkout / "receipt.json",
            owner_decision_ref="incident-2026-07-22-002",
        )
    linked_checkout = tmp_path / "linked-checkout"
    linked_checkout.symlink_to(checkout, target_is_directory=True)
    with pytest.raises(RecoveryReinjectionError, match="outside"):
        create_recovery_reinjection_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            output_path=linked_checkout / "receipt.json",
            owner_decision_ref="incident-2026-07-22-002",
        )
    assert issued.recovery_set_sha256 == created.sha256


def test_reinjection_receipt_rejects_hash_permissions_symlink_and_publish_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(tmp_path)
    recovery_set = tmp_path / "core-recovery.zip"
    receipt = tmp_path / "reinjection.json"
    created = _capture(state, audit, memory, recovery_set, checkout, project, persona)
    issued = create_recovery_reinjection_receipt(
        recovery_set,
        expected_recovery_set_sha256=created.sha256,
        checkout_path=checkout,
        output_path=receipt,
        owner_decision_ref="incident-2026-07-22-003",
    )

    with pytest.raises(RecoveryReinjectionError, match="does not match"):
        verify_recovery_reinjection_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            receipt_path=receipt,
            expected_receipt_sha256="0" * 64,
        )

    receipt.chmod(0o644)
    with pytest.raises(RecoveryReinjectionError, match="owner-only"):
        verify_recovery_reinjection_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            receipt_path=receipt,
            expected_receipt_sha256=issued.receipt_sha256,
        )
    receipt.chmod(0o600)
    linked = tmp_path / "linked-reinjection.json"
    linked.symlink_to(receipt)
    with pytest.raises(RecoveryReinjectionError, match="non-symlink"):
        verify_recovery_reinjection_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            receipt_path=linked,
            expected_receipt_sha256=issued.receipt_sha256,
        )

    before = receipt.read_bytes()
    with pytest.raises(RecoveryReinjectionError, match="already exists"):
        create_recovery_reinjection_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            output_path=receipt,
            owner_decision_ref="incident-2026-07-22-003",
        )
    assert receipt.read_bytes() == before

    failed_output = tmp_path / "failed-reinjection.json"

    def fail_sync(_path: Path) -> None:
        raise OSError("injected directory fsync failure")

    monkeypatch.setattr("aico.app.recovery_reinjection._sync_directory", fail_sync)
    with pytest.raises(RecoveryReinjectionError, match="creation failed"):
        create_recovery_reinjection_receipt(
            recovery_set,
            expected_recovery_set_sha256=created.sha256,
            checkout_path=checkout,
            output_path=failed_output,
            owner_decision_ref="incident-2026-07-22-003",
        )
    assert not failed_output.exists()


def test_recovery_set_rejects_component_rewrite_even_with_updated_outer_manifest(
    tmp_path: Path,
) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(tmp_path)
    output = tmp_path / "core-recovery.zip"
    _capture(state, audit, memory, output, checkout, project, persona)
    members = _members(output)
    members[RECOVERY_SET_STATE_MEMBER] = b"not a sqlite database"
    manifest = json.loads(members[RECOVERY_SET_MANIFEST_MEMBER])
    manifest["state"]["artifact"]["bytes"] = len(members[RECOVERY_SET_STATE_MEMBER])
    manifest["state"]["artifact"]["sha256"] = hashlib.sha256(
        members[RECOVERY_SET_STATE_MEMBER]
    ).hexdigest()
    members[RECOVERY_SET_MANIFEST_MEMBER] = _json_bytes(manifest)
    _rewrite(output, members)

    with pytest.raises(RecoverySetError, match="integrity"):
        verify_recovery_set(output, expected_sha256=_sha256(output))


def test_recovery_set_rejects_false_readiness_extra_member_and_compression(
    tmp_path: Path,
) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(tmp_path)
    output = tmp_path / "core-recovery.zip"
    _capture(state, audit, memory, output, checkout, project, persona)
    members = _members(output)
    manifest = json.loads(members[RECOVERY_SET_MANIFEST_MEMBER])
    manifest["business_restore_ready"] = True
    members[RECOVERY_SET_MANIFEST_MEMBER] = _json_bytes(manifest)
    _rewrite(output, members)
    with pytest.raises(RecoverySetError, match="manifest"):
        verify_recovery_set(output, expected_sha256=_sha256(output))

    members = _members(output)
    manifest = json.loads(members[RECOVERY_SET_MANIFEST_MEMBER])
    manifest["business_restore_ready"] = False
    project_asset = next(asset for asset in manifest["assets"] if asset["name"] == "project_config")
    project_asset["recovery_contract_ready"] = False
    members[RECOVERY_SET_MANIFEST_MEMBER] = _json_bytes(manifest)
    _rewrite(output, members)
    with pytest.raises(RecoverySetError, match="manifest"):
        verify_recovery_set(output, expected_sha256=_sha256(output))

    members = _members(output)
    manifest = json.loads(members[RECOVERY_SET_MANIFEST_MEMBER])
    project_asset = next(asset for asset in manifest["assets"] if asset["name"] == "project_config")
    project_asset["recovery_contract_ready"] = True
    manifest["assets"] = [
        {
            **asset,
            "recovery_contract_ready": False,
        }
        if asset["name"] == "control_plane_secrets"
        else asset
        for asset in manifest["assets"]
    ]
    members[RECOVERY_SET_MANIFEST_MEMBER] = _json_bytes(manifest)
    _rewrite(output, members)
    with pytest.raises(RecoverySetError, match="manifest"):
        verify_recovery_set(output, expected_sha256=_sha256(output))

    members = _members(output)
    members["unexpected.txt"] = b"not allowed"
    _rewrite(output, members)
    with pytest.raises(RecoverySetError, match="members"):
        verify_recovery_set(output, expected_sha256=_sha256(output))

    members.pop("unexpected.txt")
    _rewrite(output, members, compression=zipfile.ZIP_DEFLATED)
    with pytest.raises(RecoverySetError, match="encoding"):
        verify_recovery_set(output, expected_sha256=_sha256(output))


def test_checkout_verification_rejects_dirty_and_wrong_revision(
    tmp_path: Path,
) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(tmp_path)
    output = tmp_path / "core-recovery.zip"
    created = _capture(state, audit, memory, output, checkout, project, persona)

    (checkout / "app.py").write_text("print('dirty recovery')\n")
    with pytest.raises(RecoverySetError, match="integrity"):
        verify_recovery_checkout(
            output,
            expected_sha256=created.sha256,
            checkout_path=checkout,
        )
    assert verify_recovery_set(output, expected_sha256=created.sha256).sha256 == created.sha256

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
        "wrong recovery revision",
    )
    with pytest.raises(RecoverySetError, match="integrity"):
        verify_recovery_checkout(
            output,
            expected_sha256=created.sha256,
            checkout_path=checkout,
        )


def test_recovery_set_refuses_bad_inputs_and_existing_output_without_overwrite(
    tmp_path: Path,
) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(tmp_path)
    output = tmp_path / "core-recovery.zip"
    output.write_bytes(b"existing evidence")
    with pytest.raises(RecoverySetError, match="already exists"):
        _capture(state, audit, memory, output, checkout, project, persona)
    assert output.read_bytes() == b"existing evidence"

    output.unlink()
    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text(_event().model_dump_json() + "\n")
    legacy.chmod(0o600)
    with pytest.raises(RecoverySetError, match="unsealed"):
        _capture(state, legacy, memory, output, checkout, project, persona)
    assert not output.exists()

    with pytest.raises(RecoverySetError, match="differ"):
        _capture(
            state,
            audit,
            memory,
            Path(f"{state}-wal"),
            checkout,
            project,
            persona,
        )

    with pytest.raises(RecoverySetError, match="outside"):
        _capture(
            state,
            audit,
            memory,
            checkout / "recovery.zip",
            checkout,
            project,
            persona,
        )

    linked_checkout = tmp_path / "linked-checkout"
    linked_checkout.symlink_to(checkout, target_is_directory=True)
    with pytest.raises(RecoverySetError, match="outside"):
        _capture(
            state,
            audit,
            memory,
            linked_checkout / "recovery.zip",
            checkout,
            project,
            persona,
        )


def test_recovery_set_rejects_hash_permissions_symlink_and_report_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(tmp_path)
    output = tmp_path / "core-recovery.zip"
    report = tmp_path / "drill.json"
    created = _capture(state, audit, memory, output, checkout, project, persona)
    with pytest.raises(RecoverySetError, match="does not match"):
        verify_recovery_set(output, expected_sha256="0" * 64)

    output.chmod(0o644)
    with pytest.raises(RecoverySetError, match="owner-only"):
        verify_recovery_set(output, expected_sha256=created.sha256)
    output.chmod(0o600)
    link = tmp_path / "linked.zip"
    link.symlink_to(output)
    with pytest.raises(RecoverySetError, match="non-symlink"):
        verify_recovery_set(link, expected_sha256=created.sha256)

    def publish_race(_source: Path, destination: Path) -> None:
        destination.write_bytes(b"concurrent report")
        raise FileExistsError

    monkeypatch.setattr("aico.app.recovery_set.os.link", publish_race)
    with pytest.raises(RecoverySetError, match="already exists"):
        drill_recovery_set(
            output,
            expected_sha256=created.sha256,
            report_path=report,
        )
    assert report.read_bytes() == b"concurrent report"


def test_recovery_cli_captures_verifies_and_drills_from_environment(tmp_path: Path) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(tmp_path)
    output = tmp_path / "core-recovery.zip"
    report = tmp_path / "core-drill.json"
    receipt = tmp_path / "reinjection.json"
    provider_receipt = tmp_path / "provider-auth.json"
    stdout = io.StringIO()
    environment = {
        "AICO_STATE_DB_PATH": str(state),
        "AICO_AUDIT_LOG_PATH": str(audit),
        "AICO_MEMORY_PATH": str(memory),
        "AICO_CHECKOUT_PATH": str(checkout),
        "AICO_PROJECT_CONFIG_PATH": str(project),
        "AICO_PERSONA_CONFIG_PATH": str(persona),
        "AICO_REVIEWED_CONFIG_REVISION": _head(checkout),
    }

    assert run(["capture", "--output", str(output)], stdout=stdout, environ=environment) == 0
    captured = json.loads(stdout.getvalue())
    stdout = io.StringIO()
    assert (
        run(
            [
                "verify",
                "--recovery-set",
                str(output),
                "--expected-sha256",
                captured["sha256"],
            ],
            stdout=stdout,
            environ={},
        )
        == 0
    )
    assert json.loads(stdout.getvalue())["operation"] == "verify"
    stdout = io.StringIO()
    assert (
        run(
            [
                "verify-checkout",
                "--recovery-set",
                str(output),
                "--expected-sha256",
                captured["sha256"],
                "--checkout",
                str(checkout),
            ],
            stdout=stdout,
            environ={},
        )
        == 0
    )
    assert json.loads(stdout.getvalue())["operation"] == "verify-checkout"
    stdout = io.StringIO()
    assert (
        run(
            [
                "reinjection-receipt",
                "--recovery-set",
                str(output),
                "--expected-sha256",
                captured["sha256"],
                "--checkout",
                str(checkout),
                "--output",
                str(receipt),
                "--owner-decision-ref",
                "incident-2026-07-22-cli",
            ],
            stdout=stdout,
            environ={},
        )
        == 0
    )
    reinjection = json.loads(stdout.getvalue())
    assert reinjection["operation"] == "reinjection-receipt"
    stdout = io.StringIO()
    assert (
        run(
            [
                "verify-reinjection",
                "--recovery-set",
                str(output),
                "--expected-sha256",
                captured["sha256"],
                "--checkout",
                str(checkout),
                "--receipt",
                str(receipt),
                "--expected-receipt-sha256",
                reinjection["receipt_sha256"],
            ],
            stdout=stdout,
            environ={},
        )
        == 0
    )
    assert json.loads(stdout.getvalue())["operation"] == "verify-reinjection"
    stdout = io.StringIO()
    assert (
        run(
            [
                "provider-auth-receipt",
                "--recovery-set",
                str(output),
                "--expected-sha256",
                captured["sha256"],
                "--checkout",
                str(checkout),
                "--reinjection-receipt",
                str(receipt),
                "--expected-reinjection-receipt-sha256",
                reinjection["receipt_sha256"],
                "--output",
                str(provider_receipt),
            ],
            stdout=stdout,
            environ={},
            provider_probe_factory=lambda _provider, _command: _SuccessfulProviderProbe([]),
        )
        == 0
    )
    provider = json.loads(stdout.getvalue())
    assert provider["operation"] == "provider-auth-receipt"
    stdout = io.StringIO()
    assert (
        run(
            [
                "verify-provider-auth",
                "--recovery-set",
                str(output),
                "--expected-sha256",
                captured["sha256"],
                "--checkout",
                str(checkout),
                "--reinjection-receipt",
                str(receipt),
                "--expected-reinjection-receipt-sha256",
                reinjection["receipt_sha256"],
                "--receipt",
                str(provider_receipt),
                "--expected-receipt-sha256",
                provider["receipt_sha256"],
            ],
            stdout=stdout,
            environ={},
        )
        == 0
    )
    assert json.loads(stdout.getvalue())["operation"] == "verify-provider-auth"
    stdout = io.StringIO()
    assert (
        run(
            [
                "drill",
                "--recovery-set",
                str(output),
                "--expected-sha256",
                captured["sha256"],
                "--report",
                str(report),
            ],
            stdout=stdout,
            environ={},
        )
        == 0
    )
    assert json.loads(stdout.getvalue())["operation"] == "drill"


def test_recovery_cli_errors_do_not_leak_paths_or_payload(tmp_path: Path) -> None:
    state, audit, memory, checkout, project, persona = _live_assets(
        tmp_path, secret="merchant secret payload"
    )
    output = tmp_path / "private-core-recovery.zip"
    created = _capture(state, audit, memory, output, checkout, project, persona)
    error = io.StringIO()

    exit_code = run(
        [
            "verify",
            "--recovery-set",
            str(output),
            "--expected-sha256",
            "0" * 64,
        ],
        stderr=error,
        environ={},
    )

    assert exit_code == 2
    assert "does not match" in error.getvalue()
    assert "merchant secret payload" not in error.getvalue()
    assert str(output) not in error.getvalue()
    assert created.sha256 not in error.getvalue()

    rejected_output = tmp_path / "wrong-revision.zip"
    error = io.StringIO()
    exit_code = run(
        [
            "capture",
            "--state-db",
            str(state),
            "--audit-log",
            str(audit),
            "--memory-log",
            str(memory),
            "--checkout",
            str(checkout),
            "--project-config",
            str(project),
            "--persona-config",
            str(persona),
            "--expected-config-revision",
            "0" * 40,
            "--output",
            str(rejected_output),
        ],
        stderr=error,
        environ={},
    )
    assert exit_code == 2
    assert "owner-reviewed" in error.getvalue()
    assert "merchant secret payload" not in error.getvalue()
    assert str(checkout) not in error.getvalue()
    assert not rejected_output.exists()


def test_recovery_cli_normalizes_enabled_state_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkout, project, persona = _reviewed_checkout(tmp_path)
    monkeypatch.chdir(checkout)
    state = checkout / ".aico" / "state.db"
    audit = checkout / ".aico" / "audit.jsonl"
    memory = checkout / ".aico" / "memory.jsonl"
    SQLiteTaskStateStore(state)
    JsonlAuditSink(audit).write(_event())
    JsonlMemoryStore(memory).append_atom(_memory_atom())
    output = tmp_path / "core-recovery.zip"

    exit_code = run(
        ["capture", "--output", str(output)],
        environ={
            "AICO_STATE_DB_PATH": "true",
            "AICO_AUDIT_LOG_PATH": str(audit),
            "AICO_MEMORY_PATH": str(memory),
            "AICO_PROJECT_CONFIG_PATH": str(project),
            "AICO_PERSONA_CONFIG_PATH": str(persona),
            "AICO_REVIEWED_CONFIG_REVISION": _head(checkout),
        },
    )

    assert exit_code == 0
    assert output.is_file()


def _live_assets(
    tmp_path: Path,
    *,
    secret: str = "inspect",
) -> tuple[Path, Path, Path, Path, Path, Path]:
    state = tmp_path / "private" / "state.db"
    audit = tmp_path / "private" / "audit.jsonl"
    memory = tmp_path / "private" / "memory.jsonl"
    SQLiteTaskStateStore(state).upsert_task_record(
        Task(
            task_id="task-1",
            payload=secret,
            requester_id="owner",
            target_persona="reviewer",
        )
    )
    JsonlAuditSink(audit).write(_event(payload=secret))
    JsonlMemoryStore(memory).append_atom(_memory_atom(claim=secret))
    checkout, project, persona = _reviewed_checkout(tmp_path)
    return state, audit, memory, checkout, project, persona


def _reviewed_checkout(tmp_path: Path) -> tuple[Path, Path, Path]:
    checkout = tmp_path / "checkout"
    config = checkout / "config"
    config.mkdir(parents=True)
    project = config / "projects.json"
    persona = config / "personas.json"
    project.write_text('{"projects":["aico"]}\n')
    persona.write_text('{"personas":["lead"]}\n')
    (checkout / ".gitignore").write_text(".aico/\n.env\n")
    (checkout / "app.py").write_text("print('reviewed')\n")
    (checkout / ".env").write_text(
        "\n".join(
            (
                "AICO_CHANNEL=telegram",
                "AICO_TELEGRAM_BOT_TOKEN=test-private-telegram-token",
                f"AICO_CLAUDE_WORKING_DIRECTORY={checkout}",
                "AICO_PROJECT_CONFIG_PATH=config/projects.json",
                "AICO_STATE_DB_PATH=.aico/state.db",
                "AICO_AUDIT_LOG_PATH=.aico/audit.jsonl",
                "AICO_MEMORY_PATH=.aico/memory.jsonl",
                "AICO_OWNER_SENDER_IDS=owner-test",
                "AICO_TRUSTED_TARGET_IDS=chat-test",
            )
        )
        + "\n"
    )
    (checkout / ".env").chmod(0o600)
    _git(checkout, "init", "-q")
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
        "reviewed config",
    )
    return checkout, project, persona


def _capture(
    state: Path,
    audit: Path,
    memory: Path,
    output: Path,
    checkout: Path,
    project: Path,
    persona: Path,
    *,
    clock: Callable[[], datetime] | None = None,
) -> RecoverySetSummary:
    return create_recovery_set(
        state,
        audit,
        memory,
        output,
        checkout_path=checkout,
        project_config_path=project,
        expected_config_revision=_head(checkout),
        persona_config_path=persona,
        clock=clock,
    )


def _git(checkout: Path, *args: str) -> None:
    subprocess.run(("git", *args), cwd=checkout, check=True, capture_output=True)


def _head(checkout: Path) -> str:
    return subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _memory_atom(*, claim: str = "inspect") -> MemoryAtom:
    return MemoryAtom(
        memory_id="memory-1",
        claim=claim,
        evidence=(MemoryEvidence(ref="task:task-1", source="test"),),
        scope=MemoryScope.project("aico"),
        source="test",
        confidence=0.9,
        created_by="test-agent",
    )


def _event(*, payload: str = "inspect") -> AuditEvent:
    return InMemoryAuditLog(event_id_factory=lambda: "event-1").record(
        AuditEventType.TASK_SUBMITTED,
        Task(
            task_id="task-1",
            payload=payload,
            requester_id="owner",
            target_persona="reviewer",
        ),
    )


def _times() -> tuple[datetime, ...]:
    start = datetime(2026, 7, 22, 11, tzinfo=UTC)
    return tuple(start + timedelta(seconds=offset) for offset in range(7))


def _members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _rewrite(
    path: Path,
    members: dict[str, bytes],
    *,
    compression: int = zipfile.ZIP_STORED,
) -> None:
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    path.chmod(0o600)


def _json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode() + b"\n"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
