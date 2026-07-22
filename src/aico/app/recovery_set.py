"""Portable, explicitly non-transactional recovery set for core AICO assets."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from aico.app.audit_backup import (
    AuditBackupError,
    AuditBackupSummary,
    create_audit_backup,
    verify_audit_backup,
)
from aico.app.audit_restore import AuditRestoreError, drill_audit_backup
from aico.app.config_revision import (
    ConfigCheckoutSummary,
    ConfigRevisionError,
    ConfigRevisionEvidence,
    capture_config_revision,
    verify_config_checkout,
)
from aico.app.memory_recovery import (
    MemoryBackupSummary,
    MemoryRecoveryError,
    create_memory_backup,
    drill_memory_backup,
    verify_memory_backup,
)
from aico.app.runtime_reinjection import (
    ProviderName,
    RuntimeReinjectionContract,
    RuntimeReinjectionError,
    RuntimeReinjectionEvidence,
    capture_runtime_reinjection_contract,
    verify_runtime_reinjection,
)
from aico.app.state_backup import (
    StateBackupError,
    StateBackupSummary,
    create_state_backup,
    drill_state_backup,
    verify_state_backup,
)

RECOVERY_SET_SCHEMA_VERSION = 6
RECOVERY_SET_MANIFEST_MEMBER = "recovery-set.json"
RECOVERY_SET_STATE_MEMBER = "state.db"
RECOVERY_SET_AUDIT_MEMBER = "audit.zip"
RECOVERY_SET_MEMORY_MEMBER = "memory.zip"
_EXPECTED_MEMBERS = frozenset(
    {
        RECOVERY_SET_MANIFEST_MEMBER,
        RECOVERY_SET_STATE_MEMBER,
        RECOVERY_SET_AUDIT_MEMBER,
        RECOVERY_SET_MEMORY_MEMBER,
    }
)
_MAX_MANIFEST_BYTES = 128 * 1024
_COPY_CHUNK_BYTES = 1024 * 1024

AssetName = Literal[
    "state",
    "audit",
    "memory",
    "project_config",
    "persona_config",
    "control_plane_secrets",
    "standing_grant",
    "ai_provider_authentication",
    "dead_man_receiver_state",
    "ephemeral_runtime",
]
AssetDisposition = Literal[
    "captured",
    "restore_from_reviewed_revision",
    "reinject_and_attest",
    "post_restore_live_probe",
    "external_backup_required",
    "external_component_recovery",
    "excluded_ephemeral",
]


class RecoverySetError(RuntimeError):
    """A core recovery set could not be created, trusted, or drilled safely."""


class RecoverySetFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=128)
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class RecoverySetStateComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["state"] = "state"
    capture_order: Literal[3] = 3
    capture_completed_at: AwareDatetime
    artifact: RecoverySetFile
    schema_version: int = Field(ge=1)
    table_counts: dict[str, int]


class RecoverySetAuditComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["audit"] = "audit"
    capture_order: Literal[4] = 4
    capture_completed_at: AwareDatetime
    artifact: RecoverySetFile
    event_count: int = Field(ge=0)
    ledger_bytes: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class RecoverySetMemoryComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["memory"] = "memory"
    capture_order: Literal[5] = 5
    capture_completed_at: AwareDatetime
    artifact: RecoverySetFile
    record_count: int = Field(ge=0)
    ledger_bytes: int = Field(ge=0)
    head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class RecoverySetConfigComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["configuration"] = "configuration"
    capture_order: Literal[1] = 1
    capture_completed_at: AwareDatetime
    evidence: ConfigRevisionEvidence


class RecoverySetRuntimeReinjectionComponent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["runtime_reinjection"] = "runtime_reinjection"
    capture_order: Literal[2] = 2
    capture_completed_at: AwareDatetime
    contract: RuntimeReinjectionContract


class RecoveryAssetDisposition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: AssetName
    included: bool
    recovery_contract_ready: bool
    required_for_business_restore: bool
    requires_post_restore_evidence: bool
    disposition: AssetDisposition


class RecoverySetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[6] = 6
    created_at: AwareDatetime
    capture_started_at: AwareDatetime
    capture_completed_at: AwareDatetime
    scope: Literal["core_state_audit_memory_config_revision_reinjection"] = (
        "core_state_audit_memory_config_revision_reinjection"
    )
    consistency: Literal["sequential_component_snapshots"] = "sequential_component_snapshots"
    global_transaction: Literal[False] = False
    business_restore_ready: Literal[False] = False
    configuration: RecoverySetConfigComponent
    runtime_reinjection: RecoverySetRuntimeReinjectionComponent
    state: RecoverySetStateComponent
    audit: RecoverySetAuditComponent
    memory: RecoverySetMemoryComponent
    assets: tuple[RecoveryAssetDisposition, ...] = Field(min_length=10, max_length=10)

    @model_validator(mode="after")
    def validate_contract(self) -> RecoverySetManifest:
        if not (
            self.capture_started_at
            <= self.configuration.capture_completed_at
            <= self.runtime_reinjection.capture_completed_at
            <= self.state.capture_completed_at
            <= self.audit.capture_completed_at
            <= self.memory.capture_completed_at
            <= self.capture_completed_at
        ):
            raise ValueError("recovery set capture timestamps are out of order")
        if self.created_at != self.capture_completed_at:
            raise ValueError("recovery set creation time must close the capture window")
        if self.state.artifact.name != RECOVERY_SET_STATE_MEMBER:
            raise ValueError("recovery set state member name is invalid")
        if self.audit.artifact.name != RECOVERY_SET_AUDIT_MEMBER:
            raise ValueError("recovery set audit member name is invalid")
        if self.memory.artifact.name != RECOVERY_SET_MEMORY_MEMBER:
            raise ValueError("recovery set memory member name is invalid")
        if self.assets != _asset_contract():
            raise ValueError("recovery set asset coverage contract is invalid")
        return self


class RecoverySetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["capture", "verify"]
    artifact_name: str
    created_at: AwareDatetime
    capture_window_seconds: float = Field(ge=0)
    scope: Literal["core_state_audit_memory_config_revision_reinjection"] = (
        "core_state_audit_memory_config_revision_reinjection"
    )
    global_transaction: Literal[False] = False
    business_restore_ready: Literal[False] = False
    included_components: tuple[Literal["state"], Literal["audit"], Literal["memory"]]
    unresolved_assets: tuple[AssetName, ...]
    post_restore_evidence_assets: tuple[AssetName, ...]
    state_schema_version: int = Field(ge=1)
    state_table_counts: dict[str, int]
    audit_event_count: int = Field(ge=0)
    audit_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    memory_record_count: int = Field(ge=0)
    memory_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    config_tree_oid: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    config_count: int = Field(ge=1, le=2)
    persona_source: Literal["tracked_file", "built_in_at_revision"]
    runtime_channel: Literal["telegram", "feishu"]
    secret_slot_count: int = Field(ge=1, le=5)
    standing_grant_required: bool
    provider_names: tuple[ProviderName, ...] = Field(min_length=1, max_length=6)
    provider_count: int = Field(ge=1, le=6)
    artifact_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class RecoverySetDrillSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["drill"] = "drill"
    artifact_name: str
    backup_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    state_schema_version: int = Field(ge=1)
    state_table_counts: dict[str, int]
    audit_event_count: int = Field(ge=0)
    audit_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    memory_record_count: int = Field(ge=0)
    memory_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    secret_slot_count: int = Field(ge=1, le=5)
    standing_grant_required: bool
    provider_names: tuple[ProviderName, ...] = Field(min_length=1, max_length=6)
    provider_count: int = Field(ge=1, le=6)
    global_transaction: Literal[False] = False
    business_restore_ready: Literal[False] = False
    unresolved_assets: tuple[AssetName, ...]
    post_restore_evidence_assets: tuple[AssetName, ...]
    completed_at: AwareDatetime
    report_name: str | None = None


class RecoverySetCheckoutSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["verify-checkout"] = "verify-checkout"
    artifact_name: str
    backup_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    tree_oid: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    config_count: int = Field(ge=1, le=2)
    clean: Literal[True] = True
    persona_source: Literal["tracked_file", "built_in_at_revision"]


def create_recovery_set(
    state_path: Path,
    audit_path: Path,
    memory_path: Path,
    output_path: Path,
    *,
    checkout_path: Path,
    project_config_path: Path,
    expected_config_revision: str,
    persona_config_path: Path | None = None,
    clock: Callable[[], datetime] | None = None,
) -> RecoverySetSummary:
    state = _absolute_path(state_path)
    audit = _absolute_path(audit_path)
    memory = _absolute_path(memory_path)
    output = _absolute_path(output_path)
    _validate_capture_paths(state, audit, memory, output)
    _require_output_outside_checkout(output, _absolute_path(checkout_path))
    now = clock or (lambda: datetime.now(UTC))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_file(output)
    published = False
    try:
        with tempfile.TemporaryDirectory(prefix="aico-recovery-set-", dir=output.parent) as raw:
            directory = Path(raw)
            directory.chmod(0o700)
            started_at = _aware_now(now, "capture start")
            config_evidence, _ = capture_config_revision(
                checkout_path,
                project_config_path,
                persona_config_path,
                expected_revision=expected_config_revision,
            )
            config_completed_at = _aware_now(now, "configuration capture completion")
            reinjection_contract, _ = capture_runtime_reinjection_contract(checkout_path)
            reinjection_completed_at = _aware_now(now, "runtime reinjection capture completion")
            state_artifact = directory / RECOVERY_SET_STATE_MEMBER
            state_summary = create_state_backup(state, state_artifact)
            state_completed_at = _aware_now(now, "state capture completion")
            audit_artifact = directory / RECOVERY_SET_AUDIT_MEMBER
            audit_summary = create_audit_backup(audit, audit_artifact, clock=now)
            memory_artifact = directory / RECOVERY_SET_MEMORY_MEMBER
            memory_summary = create_memory_backup(memory, memory_artifact, clock=now)
            completed_at = _aware_now(now, "capture completion")
            manifest = _build_manifest(
                state_artifact,
                audit_artifact,
                memory_artifact,
                state_summary=state_summary,
                audit_summary=audit_summary,
                memory_summary=memory_summary,
                config_evidence=config_evidence,
                reinjection_contract=reinjection_contract,
                started_at=started_at,
                config_completed_at=config_completed_at,
                reinjection_completed_at=reinjection_completed_at,
                state_completed_at=state_completed_at,
                completed_at=completed_at,
            )
            _write_archive(temporary, state_artifact, audit_artifact, memory_artifact, manifest)
        summary, _, _ = _inspect_recovery_set(
            temporary,
            operation="capture",
            artifact_name=output.name,
        )
        _sync_file(temporary)
        _publish_new_file(temporary, output)
        published = True
        _sync_directory(output.parent)
        return summary
    except RecoverySetError:
        if published:
            _discard_published_file(temporary, output)
        raise
    except (
        AuditBackupError,
        ConfigRevisionError,
        MemoryRecoveryError,
        RuntimeReinjectionError,
        StateBackupError,
    ) as exc:
        if published:
            _discard_published_file(temporary, output)
        raise RecoverySetError(str(exc)) from None
    except Exception:
        if published:
            _discard_published_file(temporary, output)
        raise RecoverySetError("core recovery set capture failed") from None
    finally:
        temporary.unlink(missing_ok=True)


def verify_recovery_set(
    recovery_set_path: Path,
    *,
    expected_sha256: str,
) -> RecoverySetSummary:
    recovery_set = _absolute_path(recovery_set_path)
    try:
        summary, _, _ = _inspect_recovery_set(
            recovery_set,
            operation="verify",
            artifact_name=recovery_set.name,
            expected_sha256=expected_sha256,
        )
        return summary
    except RecoverySetError:
        raise
    except Exception:
        raise RecoverySetError("core recovery set verification failed") from None


def verify_recovery_checkout(
    recovery_set_path: Path,
    *,
    expected_sha256: str,
    checkout_path: Path,
) -> RecoverySetCheckoutSummary:
    recovery_set = _absolute_path(recovery_set_path)
    try:
        verified, checkout, _ = _inspect_recovery_set(
            recovery_set,
            operation="verify",
            artifact_name=recovery_set.name,
            expected_sha256=expected_sha256,
            checkout_path=_absolute_path(checkout_path),
        )
        if checkout is None:
            raise RecoverySetError("checkout verification did not run")
        return RecoverySetCheckoutSummary(
            artifact_name=verified.artifact_name,
            backup_sha256=verified.sha256,
            revision=checkout.revision,
            tree_oid=checkout.tree_oid,
            config_count=checkout.config_count,
            persona_source=checkout.persona_source,
        )
    except RecoverySetError:
        raise
    except Exception:
        raise RecoverySetError("recovery checkout verification failed") from None


def verify_recovery_runtime_reinjection(
    recovery_set_path: Path,
    *,
    expected_sha256: str,
    checkout_path: Path,
) -> tuple[RecoverySetSummary, RuntimeReinjectionEvidence]:
    recovery_set = _absolute_path(recovery_set_path)
    try:
        verified, checkout, reinjection = _inspect_recovery_set(
            recovery_set,
            operation="verify",
            artifact_name=recovery_set.name,
            expected_sha256=expected_sha256,
            checkout_path=_absolute_path(checkout_path),
            verify_reinjection=True,
        )
        if checkout is None or reinjection is None:
            raise RecoverySetError("runtime reinjection verification did not run")
        return verified, reinjection
    except RecoverySetError:
        raise
    except Exception:
        raise RecoverySetError("runtime reinjection verification failed") from None


def drill_recovery_set(
    recovery_set_path: Path,
    *,
    expected_sha256: str,
    workspace: Path | None = None,
    report_path: Path | None = None,
    clock: Callable[[], datetime] | None = None,
) -> RecoverySetDrillSummary:
    recovery_set = _absolute_path(recovery_set_path)
    drill_workspace = _validated_workspace(workspace)
    report = _validated_report(report_path, recovery_set=recovery_set)
    now = clock or (lambda: datetime.now(UTC))
    try:
        verified, _, _ = _inspect_recovery_set(
            recovery_set,
            operation="verify",
            artifact_name=recovery_set.name,
            expected_sha256=expected_sha256,
            drill_workspace=drill_workspace,
            perform_drill=True,
        )
        completed_at = _aware_now(now, "drill completion")
        summary = RecoverySetDrillSummary(
            artifact_name=verified.artifact_name,
            backup_sha256=verified.sha256,
            state_schema_version=verified.state_schema_version,
            state_table_counts=verified.state_table_counts,
            audit_event_count=verified.audit_event_count,
            audit_head_sha256=verified.audit_head_sha256,
            memory_record_count=verified.memory_record_count,
            memory_head_sha256=verified.memory_head_sha256,
            config_revision=verified.config_revision,
            secret_slot_count=verified.secret_slot_count,
            standing_grant_required=verified.standing_grant_required,
            provider_names=verified.provider_names,
            provider_count=verified.provider_count,
            unresolved_assets=verified.unresolved_assets,
            post_restore_evidence_assets=verified.post_restore_evidence_assets,
            completed_at=completed_at,
            report_name=report.name if report is not None else None,
        )
    except RecoverySetError:
        raise
    except Exception:
        raise RecoverySetError("core recovery set drill failed") from None
    if report is not None:
        _write_new_report(report, summary.model_dump_json() + "\n")
    return summary


def _build_manifest(
    state_path: Path,
    audit_path: Path,
    memory_path: Path,
    *,
    state_summary: StateBackupSummary,
    audit_summary: AuditBackupSummary,
    memory_summary: MemoryBackupSummary,
    config_evidence: ConfigRevisionEvidence,
    reinjection_contract: RuntimeReinjectionContract,
    started_at: datetime,
    config_completed_at: datetime,
    reinjection_completed_at: datetime,
    state_completed_at: datetime,
    completed_at: datetime,
) -> RecoverySetManifest:
    return RecoverySetManifest(
        created_at=completed_at,
        capture_started_at=started_at,
        capture_completed_at=completed_at,
        configuration=RecoverySetConfigComponent(
            capture_completed_at=config_completed_at,
            evidence=config_evidence,
        ),
        runtime_reinjection=RecoverySetRuntimeReinjectionComponent(
            capture_completed_at=reinjection_completed_at,
            contract=reinjection_contract,
        ),
        state=RecoverySetStateComponent(
            capture_completed_at=state_completed_at,
            artifact=_file_manifest(RECOVERY_SET_STATE_MEMBER, state_path),
            schema_version=state_summary.schema_version,
            table_counts=state_summary.table_counts,
        ),
        audit=RecoverySetAuditComponent(
            capture_completed_at=audit_summary.created_at,
            artifact=_file_manifest(RECOVERY_SET_AUDIT_MEMBER, audit_path),
            event_count=audit_summary.event_count,
            ledger_bytes=audit_summary.ledger_bytes,
            head_sha256=audit_summary.head_sha256,
        ),
        memory=RecoverySetMemoryComponent(
            capture_completed_at=memory_summary.created_at,
            artifact=_file_manifest(RECOVERY_SET_MEMORY_MEMBER, memory_path),
            record_count=memory_summary.record_count,
            ledger_bytes=memory_summary.ledger_bytes,
            head_sha256=memory_summary.head_sha256,
        ),
        assets=_asset_contract(),
    )


def _inspect_recovery_set(
    path: Path,
    *,
    operation: Literal["capture", "verify"],
    artifact_name: str,
    expected_sha256: str | None = None,
    drill_workspace: Path | None = None,
    perform_drill: bool = False,
    checkout_path: Path | None = None,
    verify_reinjection: bool = False,
) -> tuple[
    RecoverySetSummary,
    ConfigCheckoutSummary | None,
    RuntimeReinjectionEvidence | None,
]:
    _validate_private_file(path)
    artifact_sha = _sha256(path)
    _require_expected_sha256(artifact_sha, expected_sha256)
    try:
        with zipfile.ZipFile(path) as archive:
            members = _validated_members(archive)
            manifest = _read_manifest(archive, members[RECOVERY_SET_MANIFEST_MEMBER])
            _validate_member_manifests(manifest, members)
            with tempfile.TemporaryDirectory(
                prefix="aico-recovery-verify-",
                dir=drill_workspace,
            ) as raw:
                directory = Path(raw)
                directory.chmod(0o700)
                state_path = directory / RECOVERY_SET_STATE_MEMBER
                audit_path = directory / RECOVERY_SET_AUDIT_MEMBER
                memory_path = directory / RECOVERY_SET_MEMORY_MEMBER
                _extract_member(
                    archive, members[RECOVERY_SET_STATE_MEMBER], state_path, manifest.state.artifact
                )
                _extract_member(
                    archive, members[RECOVERY_SET_AUDIT_MEMBER], audit_path, manifest.audit.artifact
                )
                _extract_member(
                    archive,
                    members[RECOVERY_SET_MEMORY_MEMBER],
                    memory_path,
                    manifest.memory.artifact,
                )
                state = verify_state_backup(state_path)
                audit = verify_audit_backup(
                    audit_path,
                    expected_sha256=manifest.audit.artifact.sha256,
                )
                memory = verify_memory_backup(
                    memory_path,
                    expected_sha256=manifest.memory.artifact.sha256,
                )
                _require_component_parity(manifest, state, audit, memory)
                if perform_drill:
                    _drill_components(directory, state_path, audit_path, memory_path, manifest)
            checkout = (
                verify_config_checkout(manifest.configuration.evidence, checkout_path)
                if checkout_path is not None
                else None
            )
            reinjection = (
                verify_runtime_reinjection(
                    manifest.runtime_reinjection.contract,
                    checkout_path,
                )
                if verify_reinjection and checkout_path is not None
                else None
            )
    except RecoverySetError:
        raise
    except (
        AuditBackupError,
        AuditRestoreError,
        ConfigRevisionError,
        EOFError,
        MemoryRecoveryError,
        OSError,
        RuntimeReinjectionError,
        RuntimeError,
        StateBackupError,
        ValidationError,
        ValueError,
        zipfile.BadZipFile,
    ):
        raise RecoverySetError("core recovery set integrity verification failed") from None
    return (
        _summary(path, operation, artifact_name, artifact_sha, manifest),
        checkout,
        reinjection,
    )


def _drill_components(
    directory: Path,
    state_path: Path,
    audit_path: Path,
    memory_path: Path,
    manifest: RecoverySetManifest,
) -> None:
    drill_state_backup(
        state_path,
        expected_sha256=manifest.state.artifact.sha256,
        workspace=directory,
    )
    drill_audit_backup(
        audit_path,
        expected_sha256=manifest.audit.artifact.sha256,
        workspace=directory,
    )
    drill_memory_backup(
        memory_path,
        expected_sha256=manifest.memory.artifact.sha256,
        workspace=directory,
    )


def _asset_contract() -> tuple[RecoveryAssetDisposition, ...]:
    return (
        RecoveryAssetDisposition(
            name="state",
            included=True,
            recovery_contract_ready=True,
            required_for_business_restore=True,
            requires_post_restore_evidence=False,
            disposition="captured",
        ),
        RecoveryAssetDisposition(
            name="audit",
            included=True,
            recovery_contract_ready=True,
            required_for_business_restore=True,
            requires_post_restore_evidence=False,
            disposition="captured",
        ),
        RecoveryAssetDisposition(
            name="memory",
            included=True,
            recovery_contract_ready=True,
            required_for_business_restore=True,
            requires_post_restore_evidence=False,
            disposition="captured",
        ),
        RecoveryAssetDisposition(
            name="project_config",
            included=False,
            recovery_contract_ready=True,
            required_for_business_restore=True,
            requires_post_restore_evidence=True,
            disposition="restore_from_reviewed_revision",
        ),
        RecoveryAssetDisposition(
            name="persona_config",
            included=False,
            recovery_contract_ready=True,
            required_for_business_restore=True,
            requires_post_restore_evidence=True,
            disposition="restore_from_reviewed_revision",
        ),
        RecoveryAssetDisposition(
            name="control_plane_secrets",
            included=False,
            recovery_contract_ready=True,
            required_for_business_restore=True,
            requires_post_restore_evidence=True,
            disposition="reinject_and_attest",
        ),
        RecoveryAssetDisposition(
            name="standing_grant",
            included=False,
            recovery_contract_ready=True,
            required_for_business_restore=True,
            requires_post_restore_evidence=True,
            disposition="reinject_and_attest",
        ),
        RecoveryAssetDisposition(
            name="ai_provider_authentication",
            included=False,
            recovery_contract_ready=True,
            required_for_business_restore=True,
            requires_post_restore_evidence=True,
            disposition="post_restore_live_probe",
        ),
        RecoveryAssetDisposition(
            name="dead_man_receiver_state",
            included=False,
            recovery_contract_ready=True,
            required_for_business_restore=True,
            requires_post_restore_evidence=True,
            disposition="external_component_recovery",
        ),
        RecoveryAssetDisposition(
            name="ephemeral_runtime",
            included=False,
            recovery_contract_ready=True,
            required_for_business_restore=False,
            requires_post_restore_evidence=False,
            disposition="excluded_ephemeral",
        ),
    )


def _summary(
    path: Path,
    operation: Literal["capture", "verify"],
    artifact_name: str,
    artifact_sha: str,
    manifest: RecoverySetManifest,
) -> RecoverySetSummary:
    unresolved = tuple(
        asset.name
        for asset in manifest.assets
        if asset.required_for_business_restore and not asset.recovery_contract_ready
    )
    post_restore = tuple(
        asset.name for asset in manifest.assets if asset.requires_post_restore_evidence
    )
    return RecoverySetSummary(
        operation=operation,
        artifact_name=artifact_name,
        created_at=manifest.created_at,
        capture_window_seconds=(
            manifest.capture_completed_at - manifest.capture_started_at
        ).total_seconds(),
        included_components=("state", "audit", "memory"),
        unresolved_assets=unresolved,
        post_restore_evidence_assets=post_restore,
        state_schema_version=manifest.state.schema_version,
        state_table_counts=manifest.state.table_counts,
        audit_event_count=manifest.audit.event_count,
        audit_head_sha256=manifest.audit.head_sha256,
        memory_record_count=manifest.memory.record_count,
        memory_head_sha256=manifest.memory.head_sha256,
        config_revision=manifest.configuration.evidence.revision,
        config_tree_oid=manifest.configuration.evidence.tree_oid,
        config_count=len(manifest.configuration.evidence.configs),
        persona_source=manifest.configuration.evidence.persona_source,
        runtime_channel=manifest.runtime_reinjection.contract.channel,
        secret_slot_count=len(manifest.runtime_reinjection.contract.secret_slots),
        standing_grant_required=(manifest.runtime_reinjection.contract.standing_grant_required),
        provider_names=manifest.runtime_reinjection.contract.provider_names,
        provider_count=manifest.runtime_reinjection.contract.provider_count,
        artifact_bytes=path.stat().st_size,
        sha256=artifact_sha,
    )


def _write_archive(
    path: Path,
    state_path: Path,
    audit_path: Path,
    memory_path: Path,
    manifest: RecoverySetManifest,
) -> None:
    payload = (
        json.dumps(
            manifest.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        _write_bytes_member(archive, RECOVERY_SET_MANIFEST_MEMBER, payload)
        _write_file_member(archive, RECOVERY_SET_STATE_MEMBER, state_path)
        _write_file_member(archive, RECOVERY_SET_AUDIT_MEMBER, audit_path)
        _write_file_member(archive, RECOVERY_SET_MEMORY_MEMBER, memory_path)
    path.chmod(0o600)


def _validated_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = archive.infolist()
    names = [info.filename for info in infos]
    if len(infos) != len(_EXPECTED_MEMBERS) or set(names) != _EXPECTED_MEMBERS:
        raise RecoverySetError("core recovery set members are invalid")
    for info in infos:
        if info.is_dir() or info.flag_bits & 0x1 or info.compress_type != zipfile.ZIP_STORED:
            raise RecoverySetError("core recovery set member encoding is invalid")
        if info.file_size != info.compress_size:
            raise RecoverySetError("core recovery set member size is invalid")
    if archive.getinfo(RECOVERY_SET_MANIFEST_MEMBER).file_size > _MAX_MANIFEST_BYTES:
        raise RecoverySetError("core recovery set manifest is too large")
    return {info.filename: info for info in infos}


def _read_manifest(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> RecoverySetManifest:
    try:
        return RecoverySetManifest.model_validate_json(archive.read(info))
    except ValidationError:
        raise RecoverySetError("core recovery set manifest is invalid") from None


def _validate_member_manifests(
    manifest: RecoverySetManifest,
    members: dict[str, zipfile.ZipInfo],
) -> None:
    for file in (
        manifest.state.artifact,
        manifest.audit.artifact,
        manifest.memory.artifact,
    ):
        if members[file.name].file_size != file.bytes:
            raise RecoverySetError("core recovery set member size does not match manifest")


def _require_component_parity(
    manifest: RecoverySetManifest,
    state: StateBackupSummary,
    audit: AuditBackupSummary,
    memory: MemoryBackupSummary,
) -> None:
    if (
        state.schema_version != manifest.state.schema_version
        or state.table_counts != manifest.state.table_counts
    ):
        raise RecoverySetError("state artifact does not match recovery set manifest")
    if (
        audit.created_at != manifest.audit.capture_completed_at
        or audit.event_count != manifest.audit.event_count
        or audit.ledger_bytes != manifest.audit.ledger_bytes
        or audit.head_sha256 != manifest.audit.head_sha256
    ):
        raise RecoverySetError("audit artifact does not match recovery set manifest")
    if (
        memory.created_at != manifest.memory.capture_completed_at
        or memory.record_count != manifest.memory.record_count
        or memory.ledger_bytes != manifest.memory.ledger_bytes
        or memory.head_sha256 != manifest.memory.head_sha256
    ):
        raise RecoverySetError("memory artifact does not match recovery set manifest")


def _extract_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    target: Path,
    expected: RecoverySetFile,
) -> None:
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    digest = hashlib.sha256()
    copied = 0
    with archive.open(info) as source, os.fdopen(descriptor, "wb", closefd=True) as output:
        while chunk := source.read(_COPY_CHUNK_BYTES):
            output.write(chunk)
            digest.update(chunk)
            copied += len(chunk)
        output.flush()
        os.fsync(output.fileno())
    if copied != expected.bytes or not hmac.compare_digest(digest.hexdigest(), expected.sha256):
        raise RecoverySetError("core recovery set member hash does not match manifest")


def _write_bytes_member(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    with archive.open(_member_info(name), "w") as output:
        output.write(payload)


def _write_file_member(archive: zipfile.ZipFile, name: str, source: Path) -> None:
    with source.open("rb") as input_file, archive.open(_member_info(name), "w") as output:
        shutil.copyfileobj(input_file, output, length=_COPY_CHUNK_BYTES)


def _member_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info


def _file_manifest(name: str, path: Path) -> RecoverySetFile:
    return RecoverySetFile(name=name, bytes=path.stat().st_size, sha256=_sha256(path))


def _validate_capture_paths(state: Path, audit: Path, memory: Path, output: Path) -> None:
    forbidden = {
        state,
        Path(f"{state}-wal"),
        Path(f"{state}-shm"),
        Path(f"{state}.owner.lock"),
        audit,
        audit.with_name(f"{audit.name}.checkpoint.json"),
        audit.with_name(f"{audit.name}.lock"),
        memory,
        memory.with_name(f"{memory.name}.checkpoint.json"),
        memory.with_name(f"{memory.name}.lock"),
    }
    if output in forbidden or len({state, audit, memory}) != 3:
        raise RecoverySetError("recovery set inputs and output must differ")
    if output.exists() or output.is_symlink():
        raise RecoverySetError("recovery set output already exists")


def _require_output_outside_checkout(output: Path, checkout: Path) -> None:
    try:
        candidate = _canonical_uncreated_path(output)
        candidate.relative_to(checkout.resolve(strict=True))
    except ValueError:
        return
    except OSError:
        raise RecoverySetError("recovery set output location is invalid") from None
    raise RecoverySetError("recovery set output must be outside the reviewed checkout")


def _canonical_uncreated_path(path: Path) -> Path:
    missing: list[str] = []
    ancestor = path.parent
    while not ancestor.exists() and not ancestor.is_symlink():
        missing.append(ancestor.name)
        parent = ancestor.parent
        if parent == ancestor:
            raise OSError("no existing output ancestor")
        ancestor = parent
    resolved = ancestor.resolve(strict=True)
    for name in reversed(missing):
        resolved /= name
    return resolved / path.name


def _validate_private_file(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError:
        raise RecoverySetError("core recovery set artifact is missing") from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RecoverySetError("core recovery set must be a regular non-symlink file")
    if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
        raise RecoverySetError("core recovery set must be owned by the current user")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise RecoverySetError("core recovery set must be owner-only")


def _require_expected_sha256(actual: str, expected: str | None) -> None:
    if expected is None:
        return
    normalized = expected.lower()
    if re.fullmatch(r"[a-f0-9]{64}", normalized) is None:
        raise RecoverySetError("expected core recovery set SHA-256 is invalid")
    if not hmac.compare_digest(actual, normalized):
        raise RecoverySetError("core recovery set SHA-256 does not match expected value")


def _validated_workspace(workspace: Path | None) -> Path | None:
    if workspace is None:
        return None
    resolved = _absolute_path(workspace)
    if not resolved.is_dir():
        raise RecoverySetError("recovery drill workspace is missing or not a directory")
    return resolved


def _validated_report(path: Path | None, *, recovery_set: Path) -> Path | None:
    if path is None:
        return None
    report = _absolute_path(path)
    if report == recovery_set:
        raise RecoverySetError("recovery drill report and artifact must differ")
    if report.exists() or report.is_symlink():
        raise RecoverySetError("recovery drill report already exists")
    return report


def _write_new_report(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_file(path)
    published = False
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.chmod(0o600)
        _sync_file(temporary)
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise RecoverySetError("recovery drill report already exists") from None
        published = True
        _sync_directory(path.parent)
    except RecoverySetError:
        if published:
            _discard_published_file(temporary, path)
        raise
    except Exception:
        if published:
            _discard_published_file(temporary, path)
        raise RecoverySetError("recovery drill report publication failed") from None
    finally:
        temporary.unlink(missing_ok=True)


def _aware_now(clock: Callable[[], datetime], label: str) -> datetime:
    value = clock()
    if value.tzinfo is None:
        raise RecoverySetError(f"{label} clock must be timezone-aware")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_COPY_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _temporary_file(target: Path) -> Path:
    descriptor, raw = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(descriptor)
    return Path(raw)


def _publish_new_file(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
    except FileExistsError:
        raise RecoverySetError("recovery set output already exists") from None


def _discard_published_file(source: Path, destination: Path) -> None:
    try:
        if destination.exists() and os.path.samefile(source, destination):
            destination.unlink()
            _sync_directory(destination.parent)
    except OSError:
        pass


def _sync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))
