"""Secret-free runtime heartbeat for local service supervision."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from aico.app.runtime_alerts import (
    RuntimeAlertDeliverySnapshot,
    RuntimeAlertDeliveryStatus,
    failed_runtime_alert_snapshot,
)
from aico.app.runtime_health import RuntimeHealthSnapshot
from aico.app.runtime_liveness import (
    RuntimeLivenessSnapshot,
    RuntimeLivenessStatus,
    failed_runtime_liveness_snapshot,
)
from aico.app.runtime_self_healing import RecoveryStatus, RuntimeSelfHealingSnapshot
from aico.core.models import HealthStatus

HeartbeatStatus = Literal["ok", "warn", "fail"]
HealthProbe = Callable[[], Awaitable[RuntimeHealthSnapshot]]
SelfHealingProbe = Callable[[], Awaitable[RuntimeSelfHealingSnapshot]]
AlertProbe = Callable[
    [RuntimeSelfHealingSnapshot, RuntimeHealthSnapshot | None],
    Awaitable[RuntimeAlertDeliverySnapshot],
]
LivenessProbe = Callable[
    [RuntimeAlertDeliverySnapshot | None],
    Awaitable[RuntimeLivenessSnapshot],
]

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class HeartbeatHealth:
    status: HeartbeatStatus
    detail: str


class RuntimeHeartbeat:
    """Write process liveness without copying configuration or secrets."""

    def __init__(
        self,
        path: Path,
        *,
        interval_seconds: float = 30,
        clock: Callable[[], datetime] | None = None,
        pid_factory: Callable[[], int] = os.getpid,
        health_probe: HealthProbe | None = None,
        self_healing_probe: SelfHealingProbe | None = None,
        alert_probe: AlertProbe | None = None,
        liveness_probe: LivenessProbe | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if alert_probe is not None and self_healing_probe is None:
            raise ValueError("runtime alert probe requires a self-healing probe")
        self._path = path
        self._interval_seconds = interval_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self._pid_factory = pid_factory
        self._health_probe = health_probe
        self._self_healing_probe = self_healing_probe
        self._alert_probe = alert_probe
        self._liveness_probe = liveness_probe
        self._started_at: datetime | None = None
        self._task: asyncio.Task[None] | None = None
        self._last_health: RuntimeHealthSnapshot | None = None
        self._last_self_healing: RuntimeSelfHealingSnapshot | None = None
        self._last_alerting: RuntimeAlertDeliverySnapshot | None = None
        self._last_liveness: RuntimeLivenessSnapshot | None = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._started_at = self._clock()
        await self._refresh()
        self._task = asyncio.create_task(self._run(), name="aico-runtime-heartbeat")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            finally:
                self._task = None
        if self._started_at is not None:
            self._write("stopped")

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval_seconds)
            await self._refresh()

    async def _refresh(self) -> None:
        if self._self_healing_probe is not None:
            try:
                self._last_self_healing = await self._self_healing_probe()
            except Exception as exc:
                log.error(
                    "Runtime self-healing probe failed: type=%s",
                    type(exc).__name__,
                )
                self._last_self_healing = RuntimeSelfHealingSnapshot(
                    status=RecoveryStatus.OPEN,
                    checked_at=self._clock(),
                    components=(),
                )
        if self._health_probe is not None:
            try:
                self._last_health = await self._health_probe()
            except Exception as exc:
                log.error(
                    "Runtime health probe failed: type=%s",
                    type(exc).__name__,
                )
                self._last_health = RuntimeHealthSnapshot(
                    status=HealthStatus.FAILED,
                    checked_at=self._clock(),
                    components=(),
                )
        if self._alert_probe is not None and self._last_self_healing is not None:
            try:
                self._last_alerting = await self._alert_probe(
                    self._last_self_healing,
                    self._last_health,
                )
            except Exception as exc:
                log.error(
                    "Runtime alert probe failed: type=%s",
                    type(exc).__name__,
                )
                self._last_alerting = failed_runtime_alert_snapshot(self._clock())
        if self._liveness_probe is not None:
            try:
                self._last_liveness = await self._liveness_probe(self._last_alerting)
            except Exception as exc:
                log.error(
                    "Runtime liveness probe failed: type=%s",
                    type(exc).__name__,
                )
                self._last_liveness = failed_runtime_liveness_snapshot(self._clock())
        self._write("running")

    def _write(self, state: Literal["running", "stopped"]) -> None:
        started_at = self._started_at or self._clock()
        payload: dict[str, object] = {
            "schema_version": _heartbeat_schema_version(
                self._last_self_healing,
                self._last_alerting,
                self._last_liveness,
            ),
            "state": state,
            "pid": self._pid_factory(),
            "started_at": started_at.isoformat(),
            "heartbeat_at": self._clock().isoformat(),
        }
        if self._last_health is not None:
            payload["health"] = self._last_health.to_payload()
        if self._last_self_healing is not None:
            payload["self_healing"] = self._last_self_healing.to_payload()
        if self._last_alerting is not None:
            payload["alerting"] = self._last_alerting.to_payload()
        if self._last_liveness is not None:
            payload["liveness"] = self._last_liveness.to_payload()
        _atomic_write_json(self._path, payload)


def heartbeat_health(
    path: Path,
    *,
    now: datetime | None = None,
    stale_after_seconds: float = 90,
) -> HeartbeatHealth:
    if not path.exists():
        return HeartbeatHealth(status="warn", detail="missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        state = str(payload["state"])
        heartbeat_at = datetime.fromisoformat(str(payload["heartbeat_at"]))
    except (OSError, ValueError, KeyError, TypeError):
        return HeartbeatHealth(status="fail", detail="invalid heartbeat file")
    if state != "running":
        return HeartbeatHealth(status="warn", detail=f"state={state}")
    current = now or datetime.now(UTC)
    if heartbeat_at.tzinfo is None:
        heartbeat_at = heartbeat_at.replace(tzinfo=UTC)
    age_seconds = max(0.0, (current - heartbeat_at).total_seconds())
    if age_seconds > stale_after_seconds:
        return HeartbeatHealth(status="fail", detail=f"stale ({age_seconds:.0f}s old)")
    return _component_health(payload, age_seconds=age_seconds)


def _component_health(payload: object, *, age_seconds: float) -> HeartbeatHealth:
    if not isinstance(payload, dict):
        return HeartbeatHealth(status="fail", detail="invalid heartbeat file")
    health = payload.get("health")
    if not isinstance(health, dict):
        return HeartbeatHealth(
            status="warn",
            detail=f"fresh ({age_seconds:.0f}s old); component health unavailable",
        )
    aggregate = health.get("status")
    components = health.get("components")
    if aggregate not in {status.value for status in HealthStatus} or not isinstance(
        components, list
    ):
        return HeartbeatHealth(status="fail", detail="invalid component health")
    recovery_health = _self_healing_health(payload)
    if recovery_health is not None and recovery_health.status == "fail":
        return recovery_health
    alert_health = _alerting_health(payload)
    liveness_health = _liveness_health(payload)
    affected = _affected_component_names(components)
    if aggregate == HealthStatus.FAILED.value:
        detail = "components failed"
        return HeartbeatHealth(
            status="fail",
            detail=f"{detail}: {', '.join(affected)}" if affected else detail,
        )
    if alert_health is not None and alert_health.status == "fail":
        return alert_health
    if liveness_health is not None and liveness_health.status == "fail":
        return liveness_health
    if aggregate == HealthStatus.DEGRADED.value:
        detail = "components degraded"
        return HeartbeatHealth(
            status="warn",
            detail=f"{detail}: {', '.join(affected)}" if affected else detail,
        )
    if recovery_health is not None:
        return recovery_health
    if alert_health is not None:
        return alert_health
    if liveness_health is not None:
        return liveness_health
    return HeartbeatHealth(
        status="ok",
        detail=f"fresh ({age_seconds:.0f}s old); components healthy",
    )


def _alerting_health(payload: dict[str, object]) -> HeartbeatHealth | None:
    alerting = payload.get("alerting")
    if alerting is None:
        if payload.get("schema_version") in {4, 5}:
            return HeartbeatHealth(status="fail", detail="invalid alerting state")
        return None
    if not isinstance(alerting, dict):
        return HeartbeatHealth(status="fail", detail="invalid alerting state")
    status = alerting.get("status")
    pending = alerting.get("pending_events")
    if status not in {item.value for item in RuntimeAlertDeliveryStatus}:
        return HeartbeatHealth(status="fail", detail="invalid alerting state")
    if status == RuntimeAlertDeliveryStatus.FAILED.value:
        if pending is not None:
            return HeartbeatHealth(status="fail", detail="invalid alerting state")
        return HeartbeatHealth(status="fail", detail="out-of-band alerting failed")
    if status == RuntimeAlertDeliveryStatus.DISABLED.value:
        if pending != 0:
            return HeartbeatHealth(status="fail", detail="invalid alerting state")
        return HeartbeatHealth(status="warn", detail="out-of-band alerting disabled")
    if status == RuntimeAlertDeliveryStatus.PENDING.value:
        if not isinstance(pending, int) or isinstance(pending, bool) or pending <= 0:
            return HeartbeatHealth(status="fail", detail="invalid alerting state")
        return HeartbeatHealth(
            status="warn",
            detail=f"out-of-band alerts pending: {pending}",
        )
    if pending != 0:
        return HeartbeatHealth(status="fail", detail="invalid alerting state")
    return None


def _heartbeat_schema_version(
    self_healing: RuntimeSelfHealingSnapshot | None,
    alerting: RuntimeAlertDeliverySnapshot | None,
    liveness: RuntimeLivenessSnapshot | None,
) -> int:
    if liveness is not None:
        return 5
    if alerting is not None:
        return 4
    if self_healing is not None:
        return 3
    return 2


def _liveness_health(payload: dict[str, object]) -> HeartbeatHealth | None:
    liveness = payload.get("liveness")
    if liveness is None:
        if payload.get("schema_version") == 5:
            return HeartbeatHealth(status="fail", detail="invalid liveness state")
        return None
    if not isinstance(liveness, dict):
        return HeartbeatHealth(status="fail", detail="invalid liveness state")
    status = liveness.get("status")
    checked_at = liveness.get("checked_at")
    last_success = liveness.get("last_success_at")
    expires_at = liveness.get("expires_at")
    if status not in {item.value for item in RuntimeLivenessStatus}:
        return HeartbeatHealth(status="fail", detail="invalid liveness state")
    checked = _parse_timestamp(checked_at)
    last = _parse_timestamp(last_success)
    expires = _parse_timestamp(expires_at)
    if checked is None:
        return HeartbeatHealth(status="fail", detail="invalid liveness state")
    has_success = last is not None and expires is not None
    if (last_success is None) != (expires_at is None):
        return HeartbeatHealth(status="fail", detail="invalid liveness state")
    if last_success is not None and not has_success:
        return HeartbeatHealth(status="fail", detail="invalid liveness state")
    if last is not None and expires is not None and expires <= last:
        return HeartbeatHealth(status="fail", detail="invalid liveness state")
    if (
        status
        in {
            RuntimeLivenessStatus.HEALTHY.value,
            RuntimeLivenessStatus.DEGRADED.value,
        }
        and not has_success
    ):
        return HeartbeatHealth(status="fail", detail="invalid liveness state")
    if status == RuntimeLivenessStatus.DISABLED.value:
        if last_success is not None or expires_at is not None:
            return HeartbeatHealth(status="fail", detail="invalid liveness state")
        return HeartbeatHealth(status="warn", detail="external liveness pulse disabled")
    if status == RuntimeLivenessStatus.FAILED.value:
        if expires is not None and checked < expires:
            return HeartbeatHealth(status="fail", detail="invalid liveness state")
        return HeartbeatHealth(status="fail", detail="external liveness pulse failed")
    if status == RuntimeLivenessStatus.DEGRADED.value:
        return HeartbeatHealth(status="warn", detail="external liveness pulse degraded")
    return None


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _self_healing_health(payload: dict[str, object]) -> HeartbeatHealth | None:
    self_healing = payload.get("self_healing")
    if self_healing is None:
        return None
    if not isinstance(self_healing, dict):
        return HeartbeatHealth(status="fail", detail="invalid self-healing state")
    status = self_healing.get("status")
    components = self_healing.get("components")
    if status not in {item.value for item in RecoveryStatus} or not isinstance(components, list):
        return HeartbeatHealth(status="fail", detail="invalid self-healing state")
    affected = _affected_recovery_names(components)
    if status == RecoveryStatus.OPEN.value:
        detail = "owned task recovery open"
        return HeartbeatHealth(
            status="fail",
            detail=f"{detail}: {', '.join(affected)}" if affected else detail,
        )
    if status == RecoveryStatus.RECOVERING.value:
        detail = "owned task recovering"
        return HeartbeatHealth(
            status="warn",
            detail=f"{detail}: {', '.join(affected)}" if affected else detail,
        )
    return None


def _affected_recovery_names(components: list[object]) -> tuple[str, ...]:
    affected: list[str] = []
    for component in components:
        if not isinstance(component, dict):
            continue
        if component.get("status") == RecoveryStatus.HEALTHY.value:
            continue
        name = component.get("name")
        if isinstance(name, str):
            affected.append(name)
    return tuple(affected)


def _affected_component_names(components: list[object]) -> tuple[str, ...]:
    affected: list[str] = []
    for component in components:
        if not isinstance(component, dict) or component.get("status") == HealthStatus.OK.value:
            continue
        kind = component.get("kind")
        name = component.get("name")
        if isinstance(kind, str) and isinstance(name, str):
            affected.append(f"{kind}:{name}")
    return tuple(affected)


def _atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
