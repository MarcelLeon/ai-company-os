from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import aico.app.recovery_backup_scheduler as recovery_scheduler_module
from aico.app.recovery_backup import (
    RecoveryBackupReceipt,
    RecoveryBackupRecord,
    RecoveryBackupStatus,
    RecoveryCustodyStatus,
    SQLiteRecoveryBackupStore,
)
from aico.app.recovery_backup_scheduler import (
    RecoveryArtifactEvidence,
    RecoveryBackupConfig,
    RecoveryBackupError,
    RecoveryBackupScheduler,
    RecoveryDrillEvidence,
)
from aico.app.recovery_drill import (
    RecoveryDrillRecord,
    RecoveryDrillStatus,
    SQLiteRecoveryDrillStore,
)
from aico.core.models import HealthStatus

_REVISION = "a" * 40
_HEAD = "b" * 64


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def _scheduler(
    tmp_path: Path,
    *,
    clock: MutableClock,
    capture: object,
    verify: object,
    backup_interval_seconds: float = 3_600,
    custody_interval_seconds: float = 60,
    custody_max_age_seconds: float = 120,
    retention_enabled: bool = False,
    retention_after_seconds: float = 2_592_000,
    retention_min_generations: int = 7,
    retention_check_interval_seconds: float = 21_600,
    retention_max_prunes_per_run: int = 2,
    drill_enabled: bool = False,
    drill_interval_seconds: float = 604_800,
    drill_max_age_seconds: float = 1_209_600,
    drill_workspace: Path | None = None,
    drill: object | None = None,
) -> tuple[RecoveryBackupScheduler, SQLiteRecoveryBackupStore, Path]:
    checkout = tmp_path / "checkout"
    output = tmp_path / "recovery"
    checkout.mkdir(exist_ok=True)
    output.mkdir(exist_ok=True)
    output.chmod(0o700)
    state = tmp_path / "state.db"
    store = SQLiteRecoveryBackupStore(state)
    scheduler = RecoveryBackupScheduler(
        config=RecoveryBackupConfig(
            state_path=state,
            audit_path=tmp_path / "audit.jsonl",
            memory_path=tmp_path / "memory.jsonl",
            checkout_path=checkout,
            project_config_path=checkout / "projects.json",
            expected_config_revision=_REVISION,
            output_dir=output,
            interval_seconds=backup_interval_seconds,
            max_age_seconds=7_200,
            custody_check_interval_seconds=custody_interval_seconds,
            custody_max_age_seconds=custody_max_age_seconds,
            retention_enabled=retention_enabled,
            retention_after_seconds=retention_after_seconds,
            retention_min_generations=retention_min_generations,
            retention_check_interval_seconds=retention_check_interval_seconds,
            retention_max_prunes_per_run=retention_max_prunes_per_run,
            drill_enabled=drill_enabled,
            drill_interval_seconds=drill_interval_seconds,
            drill_max_age_seconds=drill_max_age_seconds,
            drill_workspace=drill_workspace,
        ),
        store=store,
        drill_store=(
            SQLiteRecoveryDrillStore(state) if drill_enabled or retention_enabled else None
        ),
        clock=clock,
        capture=capture,  # type: ignore[arg-type]
        verify=verify,  # type: ignore[arg-type]
        drill=drill,  # type: ignore[arg-type]
    )
    return scheduler, store, output


def _artifact_evidence(path: Path, created_at: datetime) -> RecoveryArtifactEvidence:
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    return RecoveryArtifactEvidence(
        artifact_name=path.name,
        created_at=created_at,
        capture_window_seconds=1.5,
        state_schema_version=13,
        state_table_count=15,
        audit_event_count=4,
        audit_head_sha256=_HEAD,
        memory_record_count=3,
        memory_head_sha256=_HEAD,
        config_revision=_REVISION,
        artifact_sha256=sha256,
    )


def _generation_evidence(path: Path) -> RecoveryArtifactEvidence:
    created_at = datetime.fromisoformat(path.read_text().removeprefix("generation at "))
    return _artifact_evidence(path, created_at)


def _drill_evidence(path: Path, completed_at: datetime) -> RecoveryDrillEvidence:
    artifact = _generation_evidence(path)
    return RecoveryDrillEvidence(
        backup_sha256=artifact.artifact_sha256,
        state_schema_version=artifact.state_schema_version,
        state_table_count=artifact.state_table_count,
        audit_event_count=artifact.audit_event_count,
        audit_head_sha256=artifact.audit_head_sha256,
        memory_record_count=artifact.memory_record_count,
        memory_head_sha256=artifact.memory_head_sha256,
        config_revision=artifact.config_revision,
        unresolved_asset_count=0,
        post_restore_evidence_asset_count=5,
        completed_at=completed_at,
    )


async def _dispatch_generations(
    scheduler: RecoveryBackupScheduler,
    clock: MutableClock,
    *,
    count: int,
    spacing_seconds: float = 11,
) -> list[RecoveryBackupRecord]:
    records: list[RecoveryBackupRecord] = []
    for index in range(count):
        record = await scheduler.dispatch_once()
        assert record is not None
        assert record.status is RecoveryBackupStatus.VERIFIED
        records.append(record)
        if index + 1 < count:
            clock.now += timedelta(seconds=spacing_seconds)
    return records


@pytest.mark.asyncio
async def test_backup_persists_intent_before_capture_and_verifies_sidecar(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 1, tzinfo=UTC))
    observed: list[RecoveryBackupStatus] = []
    store_ref: list[SQLiteRecoveryBackupStore] = []

    def capture(path: Path) -> RecoveryArtifactEvidence:
        latest = store_ref[0].latest("unused")
        del latest
        with store_ref[0]._database.connect() as connection:  # noqa: SLF001
            status = connection.execute("SELECT status FROM scheduled_recovery_backups").fetchone()
        observed.append(RecoveryBackupStatus(str(status[0])))
        path.write_bytes(b"verified recovery")
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    store_ref.append(store)

    record = await scheduler.dispatch_once()

    assert record is not None
    assert record.status is RecoveryBackupStatus.VERIFIED
    assert record.attempts == 1
    assert observed == [RecoveryBackupStatus.RUNNING]
    assert record.receipt is not None
    assert record.receipt.global_transaction is False
    assert record.receipt.business_restore_ready is False
    assert (output / f"aico-core-{record.backup_id}.zip").is_file()
    assert (output / f"aico-core-{record.backup_id}.receipt.json").is_file()


@pytest.mark.asyncio
async def test_artifact_only_crash_is_reconciled_without_recapture(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 2, tzinfo=UTC))
    captures = 0

    def interrupted_capture(path: Path) -> RecoveryArtifactEvidence:
        nonlocal captures
        captures += 1
        path.write_bytes(b"survived crash")
        path.chmod(0o600)
        raise RuntimeError("crash after publish")

    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=interrupted_capture,
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    with pytest.raises(RuntimeError, match="crash after publish"):
        await scheduler.dispatch_once()
    record = store.latest(next(iter(_bindings(store))))
    assert record is not None
    assert record.status is RecoveryBackupStatus.RETRYING

    clock.now += timedelta(seconds=61)
    recovery, _, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=lambda _path: pytest.fail("artifact must not be recaptured"),
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    settled = await recovery.dispatch_once()

    assert settled is not None
    assert settled.status is RecoveryBackupStatus.VERIFIED
    assert captures == 1
    assert (output / f"aico-core-{settled.backup_id}.receipt.json").is_file()


@pytest.mark.asyncio
async def test_receipt_without_artifact_fails_closed(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 3, tzinfo=UTC))

    def fail_before_capture(_path: Path) -> RecoveryArtifactEvidence:
        raise RuntimeError("no artifact")

    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=fail_before_capture,
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    with pytest.raises(RuntimeError):
        await scheduler.dispatch_once()
    record = _only_record(store)
    sidecar = output / f"aico-core-{record.backup_id}.receipt.json"
    sidecar.write_text("{}", encoding="utf-8")
    sidecar.chmod(0o600)
    clock.now += timedelta(seconds=61)

    with pytest.raises(RecoveryBackupError, match="without its artifact"):
        await scheduler.dispatch_once()


@pytest.mark.asyncio
async def test_published_artifact_and_receipt_are_reverified_after_state_crash(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 3, 30, tzinfo=UTC))
    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=lambda _path: pytest.fail("published artifact must not be recaptured"),
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    backup_id = "recovery-" + "9" * 32
    artifact = output / f"aico-core-{backup_id}.zip"
    artifact.write_bytes(b"published before state commit")
    artifact.chmod(0o600)
    evidence = _artifact_evidence(artifact, clock())
    receipt = RecoveryBackupReceipt(
        backup_id=backup_id,
        artifact_name=artifact.name,
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
        destination_fingerprint_sha256=recovery_scheduler_module._destination_fingerprint(  # noqa: SLF001
            output
        ),
    )
    sidecar = output / f"aico-core-{backup_id}.receipt.json"
    sidecar.write_text(receipt.model_dump_json(), encoding="utf-8")
    sidecar.chmod(0o600)
    store.ensure(
        RecoveryBackupRecord(
            backup_id=backup_id,
            binding_sha256=scheduler._binding_sha256,  # noqa: SLF001
            scheduled_for=clock(),
            created_at=clock(),
            updated_at=clock(),
        )
    )

    settled = await scheduler.dispatch_once()

    assert settled is not None
    assert settled.status is RecoveryBackupStatus.VERIFIED
    assert settled.receipt == receipt
    assert settled.receipt_sha256 == hashlib.sha256(sidecar.read_bytes()).hexdigest()


@pytest.mark.asyncio
async def test_five_failed_attempts_exhaust_and_fail_scheduler_health(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 3, 45, tzinfo=UTC))

    def fail_capture(_path: Path) -> RecoveryArtifactEvidence:
        raise RuntimeError("capture failed")

    scheduler, store, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=fail_capture,
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    latest: RecoveryBackupRecord | None = None
    for _ in range(5):
        with pytest.raises(RuntimeError, match="capture failed"):
            await scheduler.dispatch_once()
        latest = _only_record(store)
        if latest.next_attempt_at is not None:
            clock.now = latest.next_attempt_at

    assert latest is not None
    assert latest.status is RecoveryBackupStatus.EXHAUSTED
    assert latest.attempts == 5
    scheduler.start()
    await asyncio.sleep(0)
    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()


@pytest.mark.asyncio
async def test_interrupted_running_intent_retries_same_identity(tmp_path: Path) -> None:
    now = datetime(2026, 7, 22, 4, tzinfo=UTC)
    clock = MutableClock(now)
    scheduler, store, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=lambda path: _artifact_evidence(path, clock()),
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    binding = scheduler._binding_sha256  # noqa: SLF001
    pending = store.ensure(
        RecoveryBackupRecord(
            backup_id="recovery-" + "c" * 32,
            binding_sha256=binding,
            scheduled_for=now,
            created_at=now,
            updated_at=now,
        )
    )
    running = store.begin_attempt(pending.backup_id, now=now)

    assert running.status is RecoveryBackupStatus.RUNNING
    assert store.reconcile_interrupted(binding, now=now) == 1
    recovered = store.load(pending.backup_id)
    assert recovered is not None
    assert recovered.status is RecoveryBackupStatus.RETRYING
    assert recovered.attempts == 0
    assert recovered.next_attempt_at == now


@pytest.mark.asyncio
async def test_health_reports_verified_rpo_and_staleness(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 5, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(b"healthy")
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, _, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    scheduler.start()
    for _ in range(100):
        if await scheduler.health_check() is HealthStatus.OK:
            break
        await __import__("asyncio").sleep(0.01)
    assert await scheduler.health_check() is HealthStatus.OK

    clock.now += timedelta(seconds=7_201)
    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()
    assert await scheduler.health_check() is HealthStatus.FAILED


@pytest.mark.asyncio
async def test_periodic_custody_revalidates_latest_artifact_and_receipt(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 6, tzinfo=UTC))
    artifact_created_at = clock()
    verifications = 0

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(b"durable custody")
        path.chmod(0o600)
        return _artifact_evidence(path, artifact_created_at)

    def verify(path: Path) -> RecoveryArtifactEvidence:
        nonlocal verifications
        verifications += 1
        return _artifact_evidence(path, artifact_created_at)

    scheduler, store, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=verify,
    )
    created = await scheduler.dispatch_once()
    assert created is not None
    first_checked_at = created.custody_checked_at

    clock.now += timedelta(seconds=61)
    attested = await scheduler.attest_once()

    assert attested is not None
    assert attested.custody_status is RecoveryCustodyStatus.VERIFIED
    assert attested.custody_checked_at == clock()
    assert attested.custody_checked_at != first_checked_at
    assert attested.custody_failures == 0
    assert verifications == 2
    assert store.load(attested.backup_id) == attested


@pytest.mark.asyncio
async def test_deleted_artifact_fails_custody_and_required_health(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 7, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(b"delete detection")
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    created = await scheduler.dispatch_once()
    assert created is not None
    (output / f"aico-core-{created.backup_id}.zip").unlink()
    clock.now += timedelta(seconds=61)

    with pytest.raises(RecoveryBackupError, match="pair is missing"):
        await scheduler.attest_once()

    failed = store.load(created.backup_id)
    assert failed is not None
    assert failed.custody_status is RecoveryCustodyStatus.FAILED
    assert failed.custody_failures == 1
    scheduler.start()
    await asyncio.sleep(0)
    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()


@pytest.mark.asyncio
async def test_tampered_artifact_fails_periodic_custody(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 8, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(b"original bytes")
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    created = await scheduler.dispatch_once()
    assert created is not None
    artifact = output / f"aico-core-{created.backup_id}.zip"
    artifact.write_bytes(b"tampered bytes")
    artifact.chmod(0o600)
    clock.now += timedelta(seconds=61)

    with pytest.raises(RecoveryBackupError, match="digest mismatch"):
        await scheduler.attest_once()

    failed = store.load(created.backup_id)
    assert failed is not None
    assert failed.custody_status is RecoveryCustodyStatus.FAILED


@pytest.mark.asyncio
async def test_replaced_destination_identity_cannot_silently_rebaseline(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 9, tzinfo=UTC))
    captures = 0

    def capture(path: Path) -> RecoveryArtifactEvidence:
        nonlocal captures
        captures += 1
        path.write_bytes(b"destination baseline")
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, _, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    created = await scheduler.dispatch_once()
    assert created is not None
    preserved = tmp_path / "recovery-preserved"
    output.rename(preserved)
    output.mkdir()
    output.chmod(0o700)
    scheduler.start()
    await asyncio.sleep(0)
    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()

    clock.now += timedelta(seconds=3_601)
    with pytest.raises(RecoveryBackupError, match="identity changed"):
        await scheduler.dispatch_once()
    assert captures == 1


@pytest.mark.asyncio
async def test_custody_age_expires_before_backup_rpo(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 10, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(b"custody freshness")
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, _, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    assert await scheduler.dispatch_once() is not None
    scheduler.start()
    await asyncio.sleep(0)
    assert await scheduler.health_check() is HealthStatus.OK

    clock.now += timedelta(seconds=121)

    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()


@pytest.mark.asyncio
async def test_cadence_change_preserves_destination_custody_baseline(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 11, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(b"stable destination binding")
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    first, _, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
        backup_interval_seconds=3_600,
    )
    created = await first.dispatch_once()
    assert created is not None
    second, _, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=lambda _path: pytest.fail("cadence change must not create a new baseline"),
        verify=lambda path: _artifact_evidence(path, clock()),
        backup_interval_seconds=7_200,
    )

    assert second._binding_sha256 == first._binding_sha256  # noqa: SLF001
    assert await second.attest_once() == created


@pytest.mark.asyncio
async def test_widened_destination_permissions_fail_health_immediately(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 12, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(b"permission continuity")
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, _, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
    )
    assert await scheduler.dispatch_once() is not None
    scheduler.start()
    await asyncio.sleep(0)
    assert await scheduler.health_check() is HealthStatus.OK

    output.chmod(0o755)

    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()


@pytest.mark.asyncio
async def test_retention_is_default_disabled_and_never_deletes(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 13, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, _, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
        backup_interval_seconds=10,
        retention_after_seconds=20,
        retention_min_generations=2,
    )
    records = await _dispatch_generations(scheduler, clock, count=3)
    clock.now += timedelta(days=365)

    assert await scheduler.prune_once() == ()
    for record in records:
        assert (output / f"aico-core-{record.backup_id}.zip").is_file()
        assert (output / f"aico-core-{record.backup_id}.receipt.json").is_file()


@pytest.mark.asyncio
async def test_retention_keeps_minimum_generations_and_bounds_each_run(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 14, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=_generation_evidence,
        backup_interval_seconds=10,
        retention_enabled=True,
        retention_after_seconds=20,
        retention_min_generations=2,
        retention_check_interval_seconds=5,
        retention_max_prunes_per_run=2,
    )
    records = await _dispatch_generations(scheduler, clock, count=5)

    first_run = await scheduler.prune_once()
    second_run = await scheduler.prune_once()

    assert [record.backup_id for record in first_run] == [
        records[0].backup_id,
        records[1].backup_id,
    ]
    assert [record.backup_id for record in second_run] == [records[2].backup_id]
    for record in records[:3]:
        tombstone = store.load(record.backup_id)
        assert tombstone is not None
        assert tombstone.status is RecoveryBackupStatus.PRUNED
        assert tombstone.retention_policy_sha256 is not None
        assert tombstone.retention_started_at is not None
        assert tombstone.pruned_at is not None
        assert not (output / f"aico-core-{record.backup_id}.zip").exists()
        assert not (output / f"aico-core-{record.backup_id}.receipt.json").exists()
    for record in records[3:]:
        assert (output / f"aico-core-{record.backup_id}.zip").is_file()


@pytest.mark.asyncio
async def test_retention_age_gate_protects_recent_oldest_generation(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 15, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, _, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
        backup_interval_seconds=10,
        retention_enabled=True,
        retention_after_seconds=30,
        retention_min_generations=2,
        retention_check_interval_seconds=5,
    )
    records = await _dispatch_generations(scheduler, clock, count=3)

    assert await scheduler.prune_once() == ()
    assert (output / f"aico-core-{records[0].backup_id}.zip").is_file()


@pytest.mark.asyncio
async def test_retention_reverifies_before_delete_and_leaves_durable_intent(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 16, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
        backup_interval_seconds=10,
        retention_enabled=True,
        retention_after_seconds=20,
        retention_min_generations=2,
        retention_check_interval_seconds=5,
    )
    records = await _dispatch_generations(scheduler, clock, count=3)
    artifact = output / f"aico-core-{records[0].backup_id}.zip"
    artifact.write_bytes(b"tampered before retention")
    artifact.chmod(0o600)

    with pytest.raises(RecoveryBackupError, match="digest mismatch"):
        await scheduler.prune_once()

    intent = store.load(records[0].backup_id)
    assert intent is not None
    assert intent.status is RecoveryBackupStatus.PRUNING
    assert artifact.is_file()
    assert (output / f"aico-core-{records[0].backup_id}.receipt.json").is_file()
    newer_at = clock() + timedelta(seconds=1)
    store.ensure(
        RecoveryBackupRecord(
            backup_id="recovery-" + "f" * 32,
            binding_sha256=scheduler._binding_sha256,  # noqa: SLF001
            scheduled_for=newer_at,
            created_at=newer_at,
            updated_at=newer_at,
        )
    )
    scheduler.start()
    await asyncio.sleep(0)
    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()


@pytest.mark.asyncio
async def test_prune_crash_after_artifact_delete_finishes_sidecar(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 17, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
        backup_interval_seconds=10,
        retention_enabled=True,
        retention_after_seconds=20,
        retention_min_generations=2,
        retention_check_interval_seconds=5,
    )
    records = await _dispatch_generations(scheduler, clock, count=3)
    intent = _begin_oldest_prune(scheduler, store, records[0], clock())
    artifact = output / f"aico-core-{intent.backup_id}.zip"
    sidecar = output / f"aico-core-{intent.backup_id}.receipt.json"
    artifact.unlink()

    settled = await scheduler.prune_once()

    assert [record.status for record in settled] == [RecoveryBackupStatus.PRUNED]
    assert not sidecar.exists()


@pytest.mark.asyncio
async def test_prune_crash_after_pair_delete_settles_tombstone(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 18, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
        backup_interval_seconds=10,
        retention_enabled=True,
        retention_after_seconds=20,
        retention_min_generations=2,
        retention_check_interval_seconds=5,
    )
    records = await _dispatch_generations(scheduler, clock, count=3)
    intent = _begin_oldest_prune(scheduler, store, records[0], clock())
    (output / f"aico-core-{intent.backup_id}.zip").unlink()
    (output / f"aico-core-{intent.backup_id}.receipt.json").unlink()

    settled = await scheduler.prune_once()

    assert [record.status for record in settled] == [RecoveryBackupStatus.PRUNED]


@pytest.mark.asyncio
async def test_prune_crash_with_artifact_only_fails_closed(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 19, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
        backup_interval_seconds=10,
        retention_enabled=True,
        retention_after_seconds=20,
        retention_min_generations=2,
        retention_check_interval_seconds=5,
    )
    records = await _dispatch_generations(scheduler, clock, count=3)
    intent = _begin_oldest_prune(scheduler, store, records[0], clock())
    artifact = output / f"aico-core-{intent.backup_id}.zip"
    (output / f"aico-core-{intent.backup_id}.receipt.json").unlink()

    with pytest.raises(RecoveryBackupError, match="lost receipt before artifact"):
        await scheduler.prune_once()

    assert artifact.is_file()
    persisted = store.load(intent.backup_id)
    assert persisted is not None
    assert persisted.status is RecoveryBackupStatus.PRUNING


@pytest.mark.asyncio
async def test_disabling_retention_still_reconciles_existing_prune_intent(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 20, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    enabled, store, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=_generation_evidence,
        backup_interval_seconds=10,
        retention_enabled=True,
        retention_after_seconds=20,
        retention_min_generations=2,
        retention_check_interval_seconds=5,
    )
    records = await _dispatch_generations(enabled, clock, count=3)
    _begin_oldest_prune(enabled, store, records[0], clock())
    disabled, _, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=lambda _path: pytest.fail("reconciliation must not capture"),
        verify=_generation_evidence,
        backup_interval_seconds=10,
        retention_enabled=False,
        retention_after_seconds=20,
        retention_min_generations=2,
        retention_check_interval_seconds=5,
    )

    settled = await disabled.prune_once()

    assert [record.status for record in settled] == [RecoveryBackupStatus.PRUNED]
    assert not (output / f"aico-core-{records[0].backup_id}.zip").exists()


@pytest.mark.asyncio
async def test_failed_custody_is_never_a_retention_candidate(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 21, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, store, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=lambda path: _artifact_evidence(path, clock()),
        backup_interval_seconds=10,
        retention_enabled=True,
        retention_after_seconds=20,
        retention_min_generations=2,
        retention_check_interval_seconds=5,
    )
    records = await _dispatch_generations(scheduler, clock, count=3)
    store.mark_custody_failed(records[0].backup_id, now=clock())

    assert await scheduler.prune_once() == ()
    assert (output / f"aico-core-{records[0].backup_id}.zip").is_file()


@pytest.mark.asyncio
async def test_scheduled_drill_is_default_disabled(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 22, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, _, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=_generation_evidence,
    )
    backup = await scheduler.dispatch_once()

    assert backup is not None
    assert await scheduler.drill_once() is None
    assert (output / f"aico-core-{backup.backup_id}.zip").is_file()


@pytest.mark.asyncio
async def test_scheduled_drill_persists_intent_before_materialization(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 22, 23, tzinfo=UTC))
    store_ref: list[SQLiteRecoveryDrillStore] = []
    observed: list[RecoveryDrillStatus] = []

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    def drill(path: Path, expected_sha256: str) -> RecoveryDrillEvidence:
        latest = store_ref[0].latest(_only_binding(store_ref[0]))
        assert latest is not None
        observed.append(latest.status)
        evidence = _drill_evidence(path, clock())
        assert evidence.backup_sha256 == expected_sha256
        return evidence

    scheduler, _, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=_generation_evidence,
        drill_enabled=True,
        drill_interval_seconds=20,
        drill_max_age_seconds=40,
        drill=drill,
    )
    drill_store = _required_drill_store(scheduler)
    store_ref.append(drill_store)
    backup = await scheduler.dispatch_once()

    record = await scheduler.drill_once()

    assert backup is not None
    assert record is not None
    assert record.status is RecoveryDrillStatus.VERIFIED
    assert record.attempts == 1
    assert record.backup_id == backup.backup_id
    assert observed == [RecoveryDrillStatus.RUNNING]
    assert record.receipt is not None
    assert record.receipt.artifact_sha256 == backup.receipt.artifact_sha256  # type: ignore[union-attr]
    assert record.receipt.state_schema_version == 13
    assert record.receipt.post_restore_evidence_asset_count == 5
    assert record.receipt.business_restore_ready is False
    assert record.receipt_sha256 is not None


@pytest.mark.asyncio
async def test_scheduled_drill_cadence_targets_latest_verified_backup(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 23, 0, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, _, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=_generation_evidence,
        backup_interval_seconds=10,
        drill_enabled=True,
        drill_interval_seconds=20,
        drill_max_age_seconds=40,
        drill=lambda path, _expected: _drill_evidence(path, clock()),
    )
    first_backup = await scheduler.dispatch_once()
    first_drill = await scheduler.drill_once()
    clock.now += timedelta(seconds=11)
    second_backup = await scheduler.dispatch_once()

    not_due = await scheduler.drill_once()
    clock.now += timedelta(seconds=10)
    second_drill = await scheduler.drill_once()

    assert first_backup is not None and second_backup is not None
    assert first_drill is not None and second_drill is not None
    assert not_due == first_drill
    assert second_drill.drill_id != first_drill.drill_id
    assert second_drill.backup_id == second_backup.backup_id


@pytest.mark.asyncio
async def test_scheduled_drill_evidence_drift_retries_without_false_receipt(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2026, 7, 23, 1, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    def drifted(path: Path, _expected: str) -> RecoveryDrillEvidence:
        return _drill_evidence(path, clock()).model_copy(update={"audit_event_count": 99})

    scheduler, _, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=_generation_evidence,
        drill_enabled=True,
        drill_interval_seconds=20,
        drill_max_age_seconds=40,
        drill=drifted,
    )
    backup = await scheduler.dispatch_once()

    with pytest.raises(RecoveryBackupError, match="drill evidence drift"):
        await scheduler.drill_once()

    record = _required_drill_store(scheduler).latest(scheduler._binding_sha256)  # noqa: SLF001
    assert backup is not None and record is not None
    assert record.status is RecoveryDrillStatus.RETRYING
    assert record.receipt is None
    assert (output / f"aico-core-{backup.backup_id}.zip").is_file()


@pytest.mark.asyncio
async def test_interrupted_drill_retries_same_intent_without_spending_attempt(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2026, 7, 23, 1, 30, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, _, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=_generation_evidence,
        drill_enabled=True,
        drill_interval_seconds=20,
        drill_max_age_seconds=40,
        drill=lambda path, _expected: _drill_evidence(path, clock()),
    )
    assert await scheduler.dispatch_once() is not None
    pending = scheduler._drill_coordinator._ensure_occurrence(clock())  # noqa: SLF001
    assert pending is not None
    drill_store = _required_drill_store(scheduler)
    running = drill_store.begin_attempt(pending.drill_id, now=clock())

    reconciled = drill_store.reconcile_interrupted(
        scheduler._binding_sha256,  # noqa: SLF001
        now=clock(),
    )
    recovered = drill_store.load(pending.drill_id)

    assert running.status is RecoveryDrillStatus.RUNNING
    assert reconciled == 1
    assert recovered is not None
    assert recovered.status is RecoveryDrillStatus.RETRYING
    assert recovered.attempts == 0
    assert recovered.next_attempt_at == clock()


@pytest.mark.asyncio
async def test_scheduled_drill_exhaustion_fails_required_health(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 23, 2, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    def fail_drill(_path: Path, _expected: str) -> RecoveryDrillEvidence:
        raise RuntimeError("materialization failed")

    scheduler, _, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=_generation_evidence,
        drill_enabled=True,
        drill_interval_seconds=20,
        drill_max_age_seconds=40,
        drill=fail_drill,
    )
    assert await scheduler.dispatch_once() is not None
    latest: RecoveryDrillRecord | None = None
    for _ in range(5):
        with pytest.raises(RuntimeError, match="materialization failed"):
            await scheduler.drill_once()
        latest = _required_drill_store(scheduler).latest(
            scheduler._binding_sha256  # noqa: SLF001
        )
        assert latest is not None
        if latest.next_attempt_at is not None:
            clock.now = latest.next_attempt_at

    assert latest is not None
    assert latest.status is RecoveryDrillStatus.EXHAUSTED
    scheduler.start()
    await asyncio.sleep(0)
    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduled_drill_health_distinguishes_due_and_stale(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 23, 3, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, _, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=_generation_evidence,
        custody_max_age_seconds=1_000,
        drill_enabled=True,
        drill_interval_seconds=20,
        drill_max_age_seconds=40,
        drill=lambda path, _expected: _drill_evidence(path, clock()),
    )
    assert await scheduler.dispatch_once() is not None
    assert await scheduler.drill_once() is not None
    scheduler.start()
    await asyncio.sleep(0)
    assert await scheduler.health_check() is HealthStatus.OK

    clock.now += timedelta(seconds=20)
    assert await scheduler.health_check() is HealthStatus.DEGRADED
    clock.now += timedelta(seconds=21)
    assert await scheduler.health_check() is HealthStatus.FAILED
    await scheduler.stop()


@pytest.mark.asyncio
async def test_open_drill_intent_protects_target_from_retention(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 7, 23, 4, tzinfo=UTC))

    def capture(path: Path) -> RecoveryArtifactEvidence:
        path.write_bytes(f"generation at {clock()}".encode())
        path.chmod(0o600)
        return _artifact_evidence(path, clock())

    scheduler, _, output = _scheduler(
        tmp_path,
        clock=clock,
        capture=capture,
        verify=_generation_evidence,
        backup_interval_seconds=10,
        retention_enabled=True,
        retention_after_seconds=20,
        retention_min_generations=2,
        retention_check_interval_seconds=5,
        retention_max_prunes_per_run=2,
        drill_enabled=True,
        drill_interval_seconds=20,
        drill_max_age_seconds=40,
        drill=lambda path, _expected: _drill_evidence(path, clock()),
    )
    records = await _dispatch_generations(scheduler, clock, count=5)
    drill_store = _required_drill_store(scheduler)
    policy_sha256 = recovery_scheduler_module._drill_policy_sha256(  # noqa: SLF001
        scheduler._config  # noqa: SLF001
    )
    drill_store.ensure(
        RecoveryDrillRecord(
            drill_id="drill-" + "d" * 32,
            binding_sha256=scheduler._binding_sha256,  # noqa: SLF001
            backup_id=records[0].backup_id,
            policy_sha256=policy_sha256,
            scheduled_for=clock(),
            created_at=clock(),
            updated_at=clock(),
        )
    )

    retention_only, _, _ = _scheduler(
        tmp_path,
        clock=clock,
        capture=lambda _path: pytest.fail("retention must not capture"),
        verify=_generation_evidence,
        backup_interval_seconds=10,
        retention_enabled=True,
        retention_after_seconds=20,
        retention_min_generations=2,
        retention_check_interval_seconds=5,
        retention_max_prunes_per_run=2,
        drill_enabled=False,
    )

    pruned = await retention_only.prune_once()

    assert [record.backup_id for record in pruned] == [
        records[1].backup_id,
        records[2].backup_id,
    ]
    assert (output / f"aico-core-{records[0].backup_id}.zip").is_file()


def test_output_directory_must_be_existing_owner_only_and_outside_checkout(
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    unsafe = tmp_path / "unsafe"
    unsafe.mkdir()
    unsafe.chmod(0o755)

    with pytest.raises(ValueError, match="owner-only"):
        RecoveryBackupConfig(
            state_path=tmp_path / "state.db",
            audit_path=tmp_path / "audit.jsonl",
            memory_path=tmp_path / "memory.jsonl",
            checkout_path=checkout,
            project_config_path=checkout / "projects.json",
            expected_config_revision=_REVISION,
            output_dir=unsafe,
        )


def test_retention_policy_must_preserve_two_complete_backup_intervals(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    output = tmp_path / "recovery"
    output.mkdir()
    output.chmod(0o700)

    with pytest.raises(ValueError, match="cover all preserved generations"):
        RecoveryBackupConfig(
            state_path=tmp_path / "state.db",
            audit_path=tmp_path / "audit.jsonl",
            memory_path=tmp_path / "memory.jsonl",
            checkout_path=checkout,
            project_config_path=checkout / "projects.json",
            expected_config_revision=_REVISION,
            output_dir=output,
            interval_seconds=10,
            retention_enabled=True,
            retention_after_seconds=19,
            retention_min_generations=2,
        )


def test_scheduled_drill_requires_store_and_isolated_workspace(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    output = tmp_path / "recovery"
    output.mkdir()
    output.chmod(0o700)
    config = RecoveryBackupConfig(
        state_path=tmp_path / "state.db",
        audit_path=tmp_path / "audit.jsonl",
        memory_path=tmp_path / "memory.jsonl",
        checkout_path=checkout,
        project_config_path=checkout / "projects.json",
        expected_config_revision=_REVISION,
        output_dir=output,
        drill_enabled=True,
    )

    with pytest.raises(ValueError, match="requires a durable drill store"):
        RecoveryBackupScheduler(
            config=config,
            store=SQLiteRecoveryBackupStore(tmp_path / "state.db"),
        )
    with pytest.raises(ValueError, match="isolated from source paths"):
        RecoveryBackupConfig(
            state_path=tmp_path / "state.db",
            audit_path=tmp_path / "audit.jsonl",
            memory_path=tmp_path / "memory.jsonl",
            checkout_path=checkout,
            project_config_path=checkout / "projects.json",
            expected_config_revision=_REVISION,
            output_dir=output,
            drill_enabled=True,
            drill_workspace=output,
        )


def _begin_oldest_prune(
    scheduler: RecoveryBackupScheduler,
    store: SQLiteRecoveryBackupStore,
    record: RecoveryBackupRecord,
    now: datetime,
) -> RecoveryBackupRecord:
    return store.begin_prune(
        record.backup_id,
        policy_sha256=recovery_scheduler_module._retention_policy_sha256(  # noqa: SLF001
            scheduler._config  # noqa: SLF001
        ),
        now=now,
    )


def _required_drill_store(scheduler: RecoveryBackupScheduler) -> SQLiteRecoveryDrillStore:
    store = scheduler._drill_store  # noqa: SLF001
    assert isinstance(store, SQLiteRecoveryDrillStore)
    return store


def _only_binding(store: SQLiteRecoveryDrillStore) -> str:
    with store._database.connect() as connection:  # noqa: SLF001
        row = connection.execute(
            "SELECT DISTINCT binding_sha256 FROM scheduled_recovery_drills"
        ).fetchone()
    assert row is not None
    return str(row[0])


def _bindings(store: SQLiteRecoveryBackupStore) -> set[str]:
    with store._database.connect() as connection:  # noqa: SLF001
        rows = connection.execute(
            "SELECT DISTINCT binding_sha256 FROM scheduled_recovery_backups"
        ).fetchall()
    return {str(row[0]) for row in rows}


def _only_record(store: SQLiteRecoveryBackupStore) -> RecoveryBackupRecord:
    binding = next(iter(_bindings(store)))
    record = store.latest(binding)
    assert record is not None
    return record
