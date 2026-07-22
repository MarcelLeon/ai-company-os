"""Default-disabled, restart-safe scheduler for verified core recovery sets."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import stat
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from aico.app.recovery_backup import (
    RecoveryBackupReceipt,
    RecoveryBackupRecord,
    RecoveryBackupStatus,
    RecoveryBackupStore,
    RecoveryCustodyStatus,
)
from aico.app.recovery_drill import (
    RecoveryDrillReceipt,
    RecoveryDrillRecord,
    RecoveryDrillStatus,
    RecoveryDrillStore,
)
from aico.core.models import HealthStatus

log = logging.getLogger(__name__)
_Clock = Callable[[], datetime]
_Sleep = Callable[[float], Awaitable[None]]
_ArtifactOperation = Callable[[Path], "RecoveryArtifactEvidence"]
_DrillOperation = Callable[[Path, str], "RecoveryDrillEvidence"]
_MAX_RECEIPT_BYTES = 64 * 1024


class _RecoverySummary(Protocol):
    artifact_name: str
    created_at: datetime
    capture_window_seconds: float
    state_schema_version: int
    state_table_counts: dict[str, int]
    audit_event_count: int
    audit_head_sha256: str
    memory_record_count: int
    memory_head_sha256: str
    config_revision: str
    sha256: str


class RecoveryBackupError(RuntimeError):
    """A scheduled recovery backup could not be safely settled."""


class RecoveryArtifactEvidence(BaseModel):
    """Minimum verified recovery-set evidence needed by the scheduler."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_name: str
    created_at: AwareDatetime
    capture_window_seconds: float = Field(ge=0)
    state_schema_version: int = Field(ge=1)
    state_table_count: int = Field(ge=0)
    audit_event_count: int = Field(ge=0)
    audit_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    memory_record_count: int = Field(ge=0)
    memory_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class RecoveryDrillEvidence(BaseModel):
    """Secret-free materialization evidence returned by a recovery-set drill."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    backup_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    state_schema_version: int = Field(ge=1)
    state_table_count: int = Field(ge=0)
    audit_event_count: int = Field(ge=0)
    audit_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    memory_record_count: int = Field(ge=0)
    memory_head_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    unresolved_asset_count: int = Field(ge=0)
    post_restore_evidence_asset_count: int = Field(ge=0)
    completed_at: AwareDatetime


@dataclass(frozen=True)
class RecoveryBackupConfig:
    state_path: Path
    audit_path: Path
    memory_path: Path
    checkout_path: Path
    project_config_path: Path
    expected_config_revision: str
    output_dir: Path
    interval_seconds: float = 86_400
    max_age_seconds: float = 172_800
    custody_check_interval_seconds: float = 3_600
    custody_max_age_seconds: float = 7_200
    retention_enabled: bool = False
    retention_after_seconds: float = 2_592_000
    retention_min_generations: int = 7
    retention_check_interval_seconds: float = 21_600
    retention_max_prunes_per_run: int = 2
    drill_enabled: bool = False
    drill_interval_seconds: float = 604_800
    drill_max_age_seconds: float = 1_209_600
    drill_workspace: Path | None = None
    persona_config_path: Path | None = None

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("recovery backup interval must be positive")
        if self.max_age_seconds < self.interval_seconds:
            raise ValueError("recovery backup max age must cover one interval")
        if self.custody_check_interval_seconds <= 0:
            raise ValueError("recovery custody interval must be positive")
        if self.custody_max_age_seconds < self.custody_check_interval_seconds:
            raise ValueError("recovery custody max age must cover one interval")
        if self.retention_min_generations < 2:
            raise ValueError("recovery retention must preserve at least two generations")
        if self.retention_enabled and (
            self.retention_after_seconds < self.interval_seconds * self.retention_min_generations
        ):
            raise ValueError("recovery retention age must cover all preserved generations")
        if self.retention_check_interval_seconds <= 0:
            raise ValueError("recovery retention check interval must be positive")
        if self.retention_max_prunes_per_run < 1:
            raise ValueError("recovery retention prune limit must be positive")
        if self.drill_interval_seconds <= 0:
            raise ValueError("recovery drill interval must be positive")
        if self.drill_max_age_seconds < self.drill_interval_seconds:
            raise ValueError("recovery drill max age must cover one interval")
        if _full_revision(self.expected_config_revision) is None:
            raise ValueError("recovery backup requires a full reviewed revision")
        _validate_output_directory(self.output_dir, self.checkout_path)
        if self.drill_workspace is not None:
            _validate_drill_workspace(
                self.drill_workspace,
                checkout_path=self.checkout_path,
                output_dir=self.output_dir,
            )


class RecoveryDrillCoordinator:
    """Run disposable recovery drills without owning another background task."""

    def __init__(
        self,
        *,
        config: RecoveryBackupConfig,
        binding_sha256: str,
        backup_store: RecoveryBackupStore,
        drill_store: RecoveryDrillStore | None,
        clock: _Clock,
        artifact_path: Callable[[str], Path],
        verify_custody: Callable[[RecoveryBackupRecord], None],
        drill: _DrillOperation,
    ) -> None:
        self._config = config
        self._binding_sha256 = binding_sha256
        self._backup_store = backup_store
        self._store = drill_store
        self._clock = clock
        self._artifact_path = artifact_path
        self._verify_custody = verify_custody
        self._drill = drill

    async def dispatch_once(self, now: datetime) -> RecoveryDrillRecord | None:
        if not self._config.drill_enabled:
            return None
        store = self._required_store()
        record = store.next_open(self._binding_sha256) or self._ensure_occurrence(now)
        if record is None:
            return store.latest(self._binding_sha256)
        if record.next_attempt_at is not None and record.next_attempt_at > now:
            return record
        running = store.begin_attempt(record.drill_id, now=now)
        if running.status is not RecoveryDrillStatus.RUNNING:
            return running
        try:
            receipt, receipt_sha256 = await asyncio.to_thread(self._settle, running)
            verified = store.mark_verified(
                running.drill_id,
                receipt=receipt,
                receipt_sha256=receipt_sha256,
                now=self._aware_now(),
            )
            self._backup_store.mark_custody_verified(
                running.backup_id,
                now=self._aware_now(),
            )
            return verified
        except Exception:
            try:
                store.defer(running.drill_id, now=self._aware_now())
            except Exception as exc:
                log.error("Recovery drill defer failed: type=%s", type(exc).__name__)
            raise

    def health(self, now: datetime) -> HealthStatus:
        if not self._config.drill_enabled:
            return HealthStatus.OK
        if self._store is None:
            return HealthStatus.FAILED
        if self._config.drill_workspace is not None:
            try:
                _validate_drill_workspace(
                    self._config.drill_workspace,
                    checkout_path=self._config.checkout_path,
                    output_dir=self._config.output_dir,
                )
            except ValueError:
                return HealthStatus.FAILED
        latest = self._store.latest(self._binding_sha256)
        if latest is None:
            return HealthStatus.DEGRADED
        if latest.status is RecoveryDrillStatus.EXHAUSTED:
            return HealthStatus.FAILED
        if latest.status is not RecoveryDrillStatus.VERIFIED:
            return HealthStatus.DEGRADED
        if latest.verified_at is None:
            return HealthStatus.FAILED
        age = (now - latest.verified_at).total_seconds()
        if age > self._config.drill_max_age_seconds:
            return HealthStatus.FAILED
        if age >= self._config.drill_interval_seconds:
            return HealthStatus.DEGRADED
        return HealthStatus.OK

    def reconcile_interrupted(self, now: datetime) -> int:
        if self._store is None:
            return 0
        return self._store.reconcile_interrupted(self._binding_sha256, now=now)

    def protected_backup_ids(self) -> frozenset[str]:
        if self._store is None:
            return frozenset()
        return self._store.protected_backup_ids(self._binding_sha256)

    def next_at(self, now: datetime, *, backup_target: datetime) -> datetime:
        if not self._config.drill_enabled or self._store is None:
            return now + timedelta(seconds=self._config.drill_interval_seconds)
        open_record = self._store.next_open(self._binding_sha256)
        if open_record is not None:
            return open_record.next_attempt_at or now
        latest = self._store.latest(self._binding_sha256)
        if latest is None:
            return (
                now
                if self._backup_store.latest_verified(self._binding_sha256) is not None
                else backup_target
            )
        return (latest.verified_at or latest.updated_at) + timedelta(
            seconds=self._config.drill_interval_seconds
        )

    def _ensure_occurrence(self, now: datetime) -> RecoveryDrillRecord | None:
        store = self._required_store()
        latest = store.latest(self._binding_sha256)
        if latest is not None:
            reference = latest.verified_at or latest.updated_at
            if now < reference + timedelta(seconds=self._config.drill_interval_seconds):
                return None
            if latest.status not in {
                RecoveryDrillStatus.VERIFIED,
                RecoveryDrillStatus.EXHAUSTED,
            }:
                return None
        backup = self._backup_store.latest_verified(self._binding_sha256)
        if (
            backup is None
            or backup.receipt is None
            or backup.receipt_sha256 is None
            or backup.custody_status is not RecoveryCustodyStatus.VERIFIED
        ):
            return None
        scheduled_for = now.replace(microsecond=0)
        policy_sha256 = _drill_policy_sha256(self._config)
        return store.ensure(
            RecoveryDrillRecord(
                drill_id=_drill_id(
                    self._binding_sha256,
                    backup.backup_id,
                    policy_sha256,
                    scheduled_for,
                ),
                binding_sha256=self._binding_sha256,
                backup_id=backup.backup_id,
                policy_sha256=policy_sha256,
                scheduled_for=scheduled_for,
                created_at=now,
                updated_at=now,
            )
        )

    def _settle(self, record: RecoveryDrillRecord) -> tuple[RecoveryDrillReceipt, str]:
        backup = self._backup_store.load(record.backup_id)
        if (
            backup is None
            or backup.status is not RecoveryBackupStatus.VERIFIED
            or backup.receipt is None
            or backup.receipt_sha256 is None
            or backup.custody_status is not RecoveryCustodyStatus.VERIFIED
        ):
            raise RecoveryBackupError("recovery drill target is no longer verified")
        self._verify_custody(backup)
        evidence = self._drill(
            self._artifact_path(backup.backup_id),
            backup.receipt.artifact_sha256,
        )
        _validate_drill_evidence(backup, evidence)
        receipt = _drill_receipt(record, backup, evidence)
        return receipt, _json_sha256(receipt.model_dump(mode="json"))

    def _required_store(self) -> RecoveryDrillStore:
        if self._store is None:
            raise RecoveryBackupError("scheduled recovery drill store is unavailable")
        return self._store

    def _aware_now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("recovery drill clock must return timezone-aware values")
        return now


class RecoveryBackupScheduler:
    """Capture and immediately verify one durable recovery artifact per interval."""

    def __init__(
        self,
        *,
        config: RecoveryBackupConfig,
        store: RecoveryBackupStore,
        drill_store: RecoveryDrillStore | None = None,
        clock: _Clock | None = None,
        sleep: _Sleep = asyncio.sleep,
        capture: _ArtifactOperation | None = None,
        verify: _ArtifactOperation | None = None,
        drill: _DrillOperation | None = None,
    ) -> None:
        self._config = config
        self._store = store
        self._drill_store = drill_store
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sleep = sleep
        self._binding_sha256 = _binding_sha256(config)
        self._capture = capture or self._capture_artifact
        self._verify = verify or self._verify_artifact
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._last_retention_check_at: datetime | None = None
        if (config.drill_enabled or config.retention_enabled) and drill_store is None:
            raise ValueError("recovery retention or drill requires a durable drill store")
        self._drill_coordinator = RecoveryDrillCoordinator(
            config=config,
            binding_sha256=self._binding_sha256,
            backup_store=store,
            drill_store=drill_store,
            clock=self._clock,
            artifact_path=self._artifact_path,
            verify_custody=self._verify_persisted_custody,
            drill=drill or self._drill_artifact,
        )

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._start_task()

    async def stop(self) -> None:
        self._running = False
        if self._task is None:
            return
        if not self._task.done():
            self._task.cancel()
        await self._consume_task()
        self._task = None

    async def health_check(self) -> HealthStatus:
        if self._task is None or self._task.done():
            return HealthStatus.FAILED
        if self._store.next_pruning(self._binding_sha256) is not None:
            return HealthStatus.FAILED
        latest = self._store.latest(self._binding_sha256)
        verified = self._store.latest_verified(self._binding_sha256)
        if latest is not None and latest.status is RecoveryBackupStatus.EXHAUSTED:
            return HealthStatus.FAILED
        if verified is None:
            return HealthStatus.DEGRADED
        if verified.verified_at is None:
            return HealthStatus.FAILED
        if verified.receipt is None or verified.custody_checked_at is None:
            return HealthStatus.FAILED
        try:
            _validate_output_directory(self._config.output_dir, self._config.checkout_path)
            current_destination = _destination_fingerprint(self._config.output_dir)
        except (OSError, ValueError):
            return HealthStatus.FAILED
        if current_destination != verified.receipt.destination_fingerprint_sha256:
            return HealthStatus.FAILED
        if verified.custody_status is RecoveryCustodyStatus.FAILED:
            return HealthStatus.FAILED
        custody_age = self._aware_now() - verified.custody_checked_at
        if custody_age.total_seconds() > self._config.custody_max_age_seconds:
            return HealthStatus.FAILED
        age = self._aware_now() - verified.verified_at
        if age.total_seconds() > self._config.max_age_seconds:
            return HealthStatus.FAILED
        if latest is not None and latest.status is not RecoveryBackupStatus.VERIFIED:
            return HealthStatus.DEGRADED
        if self._config.retention_enabled:
            if self._retention_candidates(self._aware_now()):
                return HealthStatus.DEGRADED
        return self._drill_coordinator.health(self._aware_now())

    def owned_task_alive(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    async def restart_owned_task(self) -> None:
        if not self._running or self.owned_task_alive():
            return
        if self._task is not None:
            await self._consume_task()
        if self._running:
            self._start_task()

    async def dispatch_once(self) -> RecoveryBackupRecord | None:
        now = self._aware_now()
        record = self._store.next_open(self._binding_sha256)
        if record is None:
            record = self._ensure_occurrence(now)
        if record is None:
            return None
        if record.next_attempt_at is not None and record.next_attempt_at > now:
            return record
        running = self._store.begin_attempt(record.backup_id, now=now)
        if running.status is not RecoveryBackupStatus.RUNNING:
            return running
        try:
            receipt, receipt_sha256 = await asyncio.to_thread(self._settle_artifact, running)
            return self._store.mark_verified(
                running.backup_id,
                receipt=receipt,
                receipt_sha256=receipt_sha256,
                now=self._aware_now(),
            )
        except Exception:
            try:
                self._store.defer(running.backup_id, now=self._aware_now())
            except Exception as exc:
                log.error("Recovery backup defer failed: type=%s", type(exc).__name__)
            raise

    async def attest_once(self) -> RecoveryBackupRecord | None:
        now = self._aware_now()
        record = self._store.latest_verified(self._binding_sha256)
        if record is None or record.custody_checked_at is None:
            return record
        due_at = record.custody_checked_at + timedelta(
            seconds=self._config.custody_check_interval_seconds
        )
        if now < due_at:
            return record
        try:
            await asyncio.to_thread(self._verify_persisted_custody, record)
            return self._store.mark_custody_verified(record.backup_id, now=self._aware_now())
        except Exception:
            try:
                self._store.mark_custody_failed(record.backup_id, now=self._aware_now())
            except Exception as exc:
                log.error("Recovery custody failure persist failed: type=%s", type(exc).__name__)
            raise

    async def drill_once(self) -> RecoveryDrillRecord | None:
        return await self._drill_coordinator.dispatch_once(self._aware_now())

    async def prune_once(self) -> tuple[RecoveryBackupRecord, ...]:
        now = self._aware_now()
        pruned: list[RecoveryBackupRecord] = []
        try:
            interrupted = self._store.next_pruning(self._binding_sha256)
            if interrupted is not None:
                await asyncio.to_thread(self._prune_artifact_pair, interrupted)
                pruned.append(self._store.mark_pruned(interrupted.backup_id, now=self._aware_now()))
            if not self._config.retention_enabled:
                return tuple(pruned)
            remaining = self._config.retention_max_prunes_per_run - len(pruned)
            if remaining <= 0:
                return tuple(pruned)
            policy_sha256 = _retention_policy_sha256(self._config)
            for candidate in self._retention_candidates(now)[:remaining]:
                pruning = self._store.begin_prune(
                    candidate.backup_id,
                    policy_sha256=policy_sha256,
                    now=self._aware_now(),
                )
                if pruning.status is not RecoveryBackupStatus.PRUNING:
                    continue
                await asyncio.to_thread(self._prune_artifact_pair, pruning)
                pruned.append(self._store.mark_pruned(pruning.backup_id, now=self._aware_now()))
            return tuple(pruned)
        finally:
            self._last_retention_check_at = self._aware_now()

    async def _run(self) -> None:
        self._store.reconcile_interrupted(self._binding_sha256, now=self._aware_now())
        self._drill_coordinator.reconcile_interrupted(self._aware_now())
        await self._safe_dispatch()
        await self._safe_attest()
        await self._safe_drill()
        await self._safe_prune()
        while True:
            await self._sleep(self._seconds_until_work())
            await self._safe_dispatch()
            await self._safe_attest()
            await self._safe_drill()
            await self._safe_prune()

    def _start_task(self) -> None:
        self._task = asyncio.create_task(self._run(), name="aico-recovery-backup")

    async def _consume_task(self) -> None:
        if self._task is None:
            return
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log.error("Recovery backup task stopped unexpectedly: type=%s", type(exc).__name__)

    async def _safe_dispatch(self) -> None:
        try:
            await self.dispatch_once()
        except Exception as exc:
            log.error("Recovery backup attempt failed: type=%s", type(exc).__name__)

    async def _safe_attest(self) -> None:
        try:
            await self.attest_once()
        except Exception as exc:
            log.error("Recovery custody check failed: type=%s", type(exc).__name__)

    async def _safe_drill(self) -> None:
        try:
            await self.drill_once()
        except Exception as exc:
            log.error("Recovery drill attempt failed: type=%s", type(exc).__name__)

    async def _safe_prune(self) -> None:
        try:
            await self.prune_once()
        except Exception as exc:
            log.error("Recovery retention failed: type=%s", type(exc).__name__)

    def _ensure_occurrence(self, now: datetime) -> RecoveryBackupRecord | None:
        latest = self._store.latest(self._binding_sha256)
        if latest is not None:
            reference = latest.verified_at or latest.updated_at
            if now < reference + timedelta(seconds=self._config.interval_seconds):
                return None
        scheduled_for = now.replace(microsecond=0)
        backup_id = _backup_id(self._binding_sha256, scheduled_for)
        return self._store.ensure(
            RecoveryBackupRecord(
                backup_id=backup_id,
                binding_sha256=self._binding_sha256,
                scheduled_for=scheduled_for,
                created_at=now,
                updated_at=now,
            )
        )

    def _settle_artifact(
        self,
        record: RecoveryBackupRecord,
    ) -> tuple[RecoveryBackupReceipt, str]:
        _validate_output_directory(self._config.output_dir, self._config.checkout_path)
        destination_fingerprint = _destination_fingerprint(self._config.output_dir)
        self._require_destination_continuity(destination_fingerprint)
        artifact = self._artifact_path(record.backup_id)
        sidecar = self._sidecar_path(record.backup_id)
        artifact_exists = _secure_file_exists(artifact)
        sidecar_exists = _secure_file_exists(sidecar)
        if sidecar_exists and not artifact_exists:
            raise RecoveryBackupError("recovery receipt exists without its artifact")
        if artifact_exists:
            sha256 = _file_sha256(artifact)
            evidence = self._verify_with_expected(artifact, sha256)
        else:
            evidence = self._capture(artifact)
            if evidence.artifact_name != artifact.name:
                raise RecoveryBackupError("recovery capture artifact identity mismatch")
            evidence = self._verify_with_expected(artifact, evidence.artifact_sha256)
        receipt = _receipt(record.backup_id, evidence, destination_fingerprint)
        if sidecar_exists:
            persisted, receipt_sha256 = _read_receipt(sidecar)
            if persisted != receipt:
                raise RecoveryBackupError("recovery receipt evidence mismatch")
            return persisted, receipt_sha256
        return receipt, _publish_receipt(sidecar, receipt)

    def _verify_persisted_custody(self, record: RecoveryBackupRecord) -> None:
        if record.receipt is None or record.receipt_sha256 is None:
            raise RecoveryBackupError("recovery custody receipt is missing")
        _validate_output_directory(self._config.output_dir, self._config.checkout_path)
        current_destination = _destination_fingerprint(self._config.output_dir)
        if current_destination != record.receipt.destination_fingerprint_sha256:
            raise RecoveryBackupError("recovery destination identity changed")
        artifact = self._artifact_path(record.backup_id)
        sidecar = self._sidecar_path(record.backup_id)
        if not _secure_file_exists(artifact) or not _secure_file_exists(sidecar):
            raise RecoveryBackupError("recovery custody artifact pair is missing")
        persisted, receipt_sha256 = _read_receipt(sidecar)
        if persisted != record.receipt or receipt_sha256 != record.receipt_sha256:
            raise RecoveryBackupError("recovery custody receipt drift")
        evidence = self._verify_with_expected(artifact, persisted.artifact_sha256)
        if _receipt(record.backup_id, evidence, current_destination) != persisted:
            raise RecoveryBackupError("recovery custody artifact evidence drift")

    def _require_destination_continuity(self, current_fingerprint: str) -> None:
        latest = self._store.latest_verified(self._binding_sha256)
        if latest is None:
            return
        if latest.receipt is None:
            raise RecoveryBackupError("recovery destination baseline is missing")
        if latest.receipt.destination_fingerprint_sha256 != current_fingerprint:
            raise RecoveryBackupError("recovery destination identity changed")

    def _prune_artifact_pair(self, record: RecoveryBackupRecord) -> None:
        if record.status is not RecoveryBackupStatus.PRUNING:
            raise RecoveryBackupError("recovery backup has no prune intent")
        if record.receipt is None or record.receipt_sha256 is None:
            raise RecoveryBackupError("recovery prune receipt is missing")
        _validate_output_directory(self._config.output_dir, self._config.checkout_path)
        current_destination = _destination_fingerprint(self._config.output_dir)
        if current_destination != record.receipt.destination_fingerprint_sha256:
            raise RecoveryBackupError("recovery destination identity changed")
        artifact = self._artifact_path(record.backup_id)
        sidecar = self._sidecar_path(record.backup_id)
        artifact_exists = _secure_file_exists(artifact)
        sidecar_exists = _secure_file_exists(sidecar)
        if artifact_exists and sidecar_exists:
            self._verify_persisted_custody(record)
            _unlink_and_sync(artifact)
            _unlink_and_sync(sidecar)
            return
        if artifact_exists:
            raise RecoveryBackupError("recovery prune lost receipt before artifact")
        if sidecar_exists:
            persisted, receipt_sha256 = _read_receipt(sidecar)
            if persisted != record.receipt or receipt_sha256 != record.receipt_sha256:
                raise RecoveryBackupError("recovery prune receipt drift")
            _unlink_and_sync(sidecar)

    def _retention_candidates(self, now: datetime) -> tuple[RecoveryBackupRecord, ...]:
        candidates = self._store.retention_candidates(
            self._binding_sha256,
            older_than=now - timedelta(seconds=self._config.retention_after_seconds),
            keep_generations=self._config.retention_min_generations,
        )
        protected = self._drill_coordinator.protected_backup_ids()
        return tuple(record for record in candidates if record.backup_id not in protected)

    def _capture_artifact(self, artifact: Path) -> RecoveryArtifactEvidence:
        from aico.app.recovery_set import create_recovery_set

        summary = create_recovery_set(
            self._config.state_path,
            self._config.audit_path,
            self._config.memory_path,
            artifact,
            checkout_path=self._config.checkout_path,
            project_config_path=self._config.project_config_path,
            persona_config_path=self._config.persona_config_path,
            expected_config_revision=self._config.expected_config_revision,
        )
        return _evidence(summary)

    def _verify_artifact(self, artifact: Path) -> RecoveryArtifactEvidence:
        from aico.app.recovery_set import verify_recovery_set

        return _evidence(verify_recovery_set(artifact, expected_sha256=_file_sha256(artifact)))

    def _drill_artifact(self, artifact: Path, expected_sha256: str) -> RecoveryDrillEvidence:
        from aico.app.recovery_set import drill_recovery_set

        summary = drill_recovery_set(
            artifact,
            expected_sha256=expected_sha256,
            workspace=self._config.drill_workspace,
        )
        return RecoveryDrillEvidence(
            backup_sha256=summary.backup_sha256,
            state_schema_version=summary.state_schema_version,
            state_table_count=len(summary.state_table_counts),
            audit_event_count=summary.audit_event_count,
            audit_head_sha256=summary.audit_head_sha256,
            memory_record_count=summary.memory_record_count,
            memory_head_sha256=summary.memory_head_sha256,
            config_revision=summary.config_revision,
            unresolved_asset_count=len(summary.unresolved_assets),
            post_restore_evidence_asset_count=len(summary.post_restore_evidence_assets),
            completed_at=summary.completed_at,
        )

    def _verify_with_expected(
        self,
        artifact: Path,
        expected_sha256: str,
    ) -> RecoveryArtifactEvidence:
        actual = _file_sha256(artifact)
        if actual != expected_sha256:
            raise RecoveryBackupError("recovery artifact digest mismatch")
        evidence = self._verify(artifact)
        if evidence.artifact_sha256 != actual or evidence.artifact_name != artifact.name:
            raise RecoveryBackupError("recovery verification evidence mismatch")
        return evidence

    def _artifact_path(self, backup_id: str) -> Path:
        return self._config.output_dir / f"aico-core-{backup_id}.zip"

    def _sidecar_path(self, backup_id: str) -> Path:
        return self._config.output_dir / f"aico-core-{backup_id}.receipt.json"

    def _seconds_until_work(self) -> float:
        now = self._aware_now()
        backup_target = self._next_backup_at(now)
        custody_target = self._next_custody_at(now)
        drill_target = self._next_drill_at(now)
        retention_target = self._next_retention_at(now)
        return max(
            (
                min(backup_target, custody_target, drill_target, retention_target) - now
            ).total_seconds(),
            0.01,
        )

    def _next_backup_at(self, now: datetime) -> datetime:
        open_record = self._store.next_open(self._binding_sha256)
        if open_record is not None:
            return open_record.next_attempt_at or now
        latest = self._store.latest(self._binding_sha256)
        return (
            now
            if latest is None
            else (latest.verified_at or latest.updated_at)
            + timedelta(seconds=self._config.interval_seconds)
        )

    def _next_custody_at(self, now: datetime) -> datetime:
        latest = self._store.latest_verified(self._binding_sha256)
        if latest is None or latest.custody_checked_at is None:
            return now + timedelta(seconds=self._config.custody_check_interval_seconds)
        return latest.custody_checked_at + timedelta(
            seconds=self._config.custody_check_interval_seconds
        )

    def _next_drill_at(self, now: datetime) -> datetime:
        return self._drill_coordinator.next_at(
            now,
            backup_target=self._next_backup_at(now),
        )

    def _next_retention_at(self, now: datetime) -> datetime:
        if self._store.next_pruning(self._binding_sha256) is not None:
            return now
        if not self._config.retention_enabled:
            return now + timedelta(seconds=self._config.retention_check_interval_seconds)
        if self._last_retention_check_at is None:
            return now
        return self._last_retention_check_at + timedelta(
            seconds=self._config.retention_check_interval_seconds
        )

    def _aware_now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("recovery backup clock must return timezone-aware values")
        return now


def _evidence(summary: _RecoverySummary) -> RecoveryArtifactEvidence:
    values = {
        "artifact_name": summary.artifact_name,
        "created_at": summary.created_at,
        "capture_window_seconds": summary.capture_window_seconds,
        "state_schema_version": summary.state_schema_version,
        "state_table_count": len(summary.state_table_counts),
        "audit_event_count": summary.audit_event_count,
        "audit_head_sha256": summary.audit_head_sha256,
        "memory_record_count": summary.memory_record_count,
        "memory_head_sha256": summary.memory_head_sha256,
        "config_revision": summary.config_revision,
        "artifact_sha256": summary.sha256,
    }
    return RecoveryArtifactEvidence.model_validate(values)


def _receipt(
    backup_id: str,
    evidence: RecoveryArtifactEvidence,
    destination_fingerprint_sha256: str,
) -> RecoveryBackupReceipt:
    return RecoveryBackupReceipt(
        backup_id=backup_id,
        artifact_name=evidence.artifact_name,
        artifact_sha256=evidence.artifact_sha256,
        created_at=evidence.created_at,
        capture_window_seconds=evidence.capture_window_seconds,
        state_schema_version=evidence.state_schema_version,
        state_table_count=evidence.state_table_count,
        audit_event_count=evidence.audit_event_count,
        audit_head_sha256=evidence.audit_head_sha256,
        memory_record_count=evidence.memory_record_count,
        memory_head_sha256=evidence.memory_head_sha256,
        config_revision=evidence.config_revision,
        destination_fingerprint_sha256=destination_fingerprint_sha256,
    )


def _validate_drill_evidence(
    backup: RecoveryBackupRecord,
    evidence: RecoveryDrillEvidence,
) -> None:
    if backup.receipt is None:
        raise RecoveryBackupError("recovery drill target receipt is missing")
    expected = (
        backup.receipt.artifact_sha256,
        backup.receipt.state_schema_version,
        backup.receipt.state_table_count,
        backup.receipt.audit_event_count,
        backup.receipt.audit_head_sha256,
        backup.receipt.memory_record_count,
        backup.receipt.memory_head_sha256,
        backup.receipt.config_revision,
    )
    actual = (
        evidence.backup_sha256,
        evidence.state_schema_version,
        evidence.state_table_count,
        evidence.audit_event_count,
        evidence.audit_head_sha256,
        evidence.memory_record_count,
        evidence.memory_head_sha256,
        evidence.config_revision,
    )
    if actual != expected:
        raise RecoveryBackupError("recovery drill evidence drift")


def _drill_receipt(
    record: RecoveryDrillRecord,
    backup: RecoveryBackupRecord,
    evidence: RecoveryDrillEvidence,
) -> RecoveryDrillReceipt:
    if backup.receipt_sha256 is None:
        raise RecoveryBackupError("recovery drill target receipt SHA is missing")
    return RecoveryDrillReceipt(
        drill_id=record.drill_id,
        backup_id=backup.backup_id,
        policy_sha256=record.policy_sha256,
        artifact_sha256=evidence.backup_sha256,
        backup_receipt_sha256=backup.receipt_sha256,
        state_schema_version=evidence.state_schema_version,
        state_table_count=evidence.state_table_count,
        audit_event_count=evidence.audit_event_count,
        audit_head_sha256=evidence.audit_head_sha256,
        memory_record_count=evidence.memory_record_count,
        memory_head_sha256=evidence.memory_head_sha256,
        config_revision=evidence.config_revision,
        unresolved_asset_count=evidence.unresolved_asset_count,
        post_restore_evidence_asset_count=evidence.post_restore_evidence_asset_count,
        completed_at=evidence.completed_at,
    )


def _read_receipt(path: Path) -> tuple[RecoveryBackupReceipt, str]:
    try:
        raw = path.read_bytes()
        if len(raw) > _MAX_RECEIPT_BYTES:
            raise RecoveryBackupError("recovery receipt is too large")
        return RecoveryBackupReceipt.model_validate_json(raw), hashlib.sha256(raw).hexdigest()
    except RecoveryBackupError:
        raise
    except Exception:
        raise RecoveryBackupError("recovery receipt is invalid") from None


def _publish_receipt(path: Path, receipt: RecoveryBackupReceipt) -> str:
    raw = (json.dumps(receipt.model_dump(mode="json"), sort_keys=True) + "\n").encode()
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".aico-receipt-", dir=path.parent)
        temporary = Path(name)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, path)
        _sync_directory(path.parent)
        return hashlib.sha256(raw).hexdigest()
    except FileExistsError:
        raise RecoveryBackupError("recovery receipt already exists") from None
    except RecoveryBackupError:
        raise
    except Exception:
        raise RecoveryBackupError("recovery receipt publish failed") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _secure_file_exists(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise RecoveryBackupError("recovery artifact path is not a regular file")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise RecoveryBackupError("recovery artifact permissions are unsafe")
    return True


def _validate_output_directory(output_dir: Path, checkout_path: Path) -> None:
    if not output_dir.is_absolute():
        raise ValueError("recovery backup output directory must be absolute")
    try:
        metadata = output_dir.lstat()
        output = output_dir.resolve(strict=True)
        checkout = checkout_path.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError("recovery backup paths must already exist") from None
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise ValueError("recovery backup output must be a real directory")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ValueError("recovery backup output directory must be owner-only")
    if output == checkout or checkout in output.parents or output in checkout.parents:
        raise ValueError("recovery backup output must be outside the checkout tree")


def _validate_drill_workspace(
    workspace: Path,
    *,
    checkout_path: Path,
    output_dir: Path,
) -> None:
    if not workspace.is_absolute():
        raise ValueError("recovery drill workspace must be absolute")
    try:
        metadata = workspace.lstat()
        resolved = workspace.resolve(strict=True)
        checkout = checkout_path.resolve(strict=True)
        output = output_dir.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError("recovery drill workspace must already exist") from None
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise ValueError("recovery drill workspace must be a real directory")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ValueError("recovery drill workspace must be owner-only")
    if any(
        resolved == path or path in resolved.parents or resolved in path.parents
        for path in (checkout, output)
    ):
        raise ValueError("recovery drill workspace must be isolated from source paths")


def _destination_fingerprint(output_dir: Path) -> str:
    metadata = output_dir.lstat()
    filesystem = os.statvfs(output_dir)
    payload = {
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "filesystem": getattr(filesystem, "f_fsid", None),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _binding_sha256(config: RecoveryBackupConfig) -> str:
    payload = {
        "state": str(config.state_path.resolve()),
        "audit": str(config.audit_path.resolve()),
        "memory": str(config.memory_path.resolve()),
        "checkout": str(config.checkout_path.resolve()),
        "project_config": str(config.project_config_path.resolve()),
        "persona_config": (
            None
            if config.persona_config_path is None
            else str(config.persona_config_path.resolve())
        ),
        "revision": config.expected_config_revision,
        "output": str(config.output_dir.resolve()),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _retention_policy_sha256(config: RecoveryBackupConfig) -> str:
    payload = {
        "schema_version": 1,
        "enabled": config.retention_enabled,
        "after_seconds": config.retention_after_seconds,
        "min_generations": config.retention_min_generations,
        "check_interval_seconds": config.retention_check_interval_seconds,
        "max_prunes_per_run": config.retention_max_prunes_per_run,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _drill_policy_sha256(config: RecoveryBackupConfig) -> str:
    workspace_sha256 = None
    if config.drill_workspace is not None:
        workspace_sha256 = hashlib.sha256(
            str(config.drill_workspace.resolve()).encode()
        ).hexdigest()
    payload = {
        "schema_version": 1,
        "enabled": config.drill_enabled,
        "interval_seconds": config.drill_interval_seconds,
        "max_age_seconds": config.drill_max_age_seconds,
        "workspace_sha256": workspace_sha256,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _backup_id(binding_sha256: str, scheduled_for: datetime) -> str:
    raw = f"{binding_sha256}:{scheduled_for.isoformat()}".encode()
    return f"recovery-{hashlib.sha256(raw).hexdigest()[:32]}"


def _drill_id(
    binding_sha256: str,
    backup_id: str,
    policy_sha256: str,
    scheduled_for: datetime,
) -> str:
    raw = f"{binding_sha256}:{backup_id}:{policy_sha256}:{scheduled_for.isoformat()}".encode()
    return f"drill-{hashlib.sha256(raw).hexdigest()[:32]}"


def _json_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _full_revision(value: str) -> str | None:
    normalized = value.strip().lower()
    if len(normalized) not in {40, 64} or any(
        char not in "0123456789abcdef" for char in normalized
    ):
        return None
    return normalized


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
    except OSError:
        raise RecoveryBackupError("recovery artifact could not be read") from None
    return digest.hexdigest()


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _unlink_and_sync(path: Path) -> None:
    try:
        path.unlink()
        _sync_directory(path.parent)
    except OSError:
        raise RecoveryBackupError("recovery retention file removal failed") from None
