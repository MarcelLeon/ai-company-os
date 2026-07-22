from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from aico.adapter import AIAdapter
from aico.app.morning_scheduler import MorningPushScheduler
from aico.app.runtime_config_source import RuntimeConfigSourceHealth
from aico.app.runtime_health import RuntimeHealthProbe
from aico.channel import IMChannel
from aico.core import AdapterRegistry, HealthStatus


class HealthChannel:
    def __init__(self, status: HealthStatus) -> None:
        self._status = status

    @property
    def name(self) -> str:
        return "telegram"

    async def health_check(self) -> HealthStatus:
        return self._status


class HealthAdapter:
    def __init__(self, name: str, status: HealthStatus) -> None:
        self._name = name
        self._status = status

    @property
    def name(self) -> str:
        return self._name

    async def health_check(self) -> HealthStatus:
        return self._status


class HangingAdapter(HealthAdapter):
    async def health_check(self) -> HealthStatus:
        await asyncio.Event().wait()
        return HealthStatus.OK


class ExplodingAdapter(HealthAdapter):
    async def health_check(self) -> HealthStatus:
        raise RuntimeError("super-secret-provider-detail")


class HealthScheduler:
    def __init__(self, status: HealthStatus) -> None:
        self._status = status

    async def health_check(self) -> HealthStatus:
        return self._status


def _registry(*adapters: HealthAdapter) -> AdapterRegistry:
    return AdapterRegistry(
        [cast(AIAdapter, adapter) for adapter in adapters],
        default_adapter_name=adapters[0].name,
    )


async def test_runtime_health_probe_marks_optional_adapter_failure_degraded() -> None:
    checked_at = datetime(2026, 7, 21, 13, tzinfo=UTC)
    probe = RuntimeHealthProbe(
        channel=cast(IMChannel, HealthChannel(HealthStatus.OK)),
        registry=_registry(
            HealthAdapter("claude-code", HealthStatus.OK),
            HealthAdapter("codex", HealthStatus.FAILED),
        ),
        clock=lambda: checked_at,
    )

    snapshot = await probe.check()

    assert snapshot.status is HealthStatus.DEGRADED
    assert snapshot.checked_at == checked_at
    assert [
        (component.kind, component.name, component.required, component.status)
        for component in snapshot.components
    ] == [
        ("channel", "telegram", True, HealthStatus.OK),
        ("adapter", "claude-code", True, HealthStatus.OK),
        ("adapter", "codex", False, HealthStatus.FAILED),
    ]


async def test_runtime_health_probe_all_healthy_stays_healthy() -> None:
    probe = RuntimeHealthProbe(
        channel=cast(IMChannel, HealthChannel(HealthStatus.OK)),
        registry=_registry(
            HealthAdapter("claude-code", HealthStatus.OK),
            HealthAdapter("codex", HealthStatus.OK),
        ),
    )

    snapshot = await probe.check()

    assert snapshot.status is HealthStatus.OK


async def test_runtime_health_probe_marks_dotenv_generation_drift_failed(
    tmp_path: Path,
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("AICO_CHANNEL=telegram\n", encoding="utf-8")
    configuration = RuntimeConfigSourceHealth.capture(dotenv)
    dotenv.write_text("AICO_CHANNEL=feishu\n", encoding="utf-8")
    probe = RuntimeHealthProbe(
        channel=cast(IMChannel, HealthChannel(HealthStatus.OK)),
        registry=_registry(HealthAdapter("claude-code", HealthStatus.OK)),
        configuration=configuration,
    )

    snapshot = await probe.check()

    assert snapshot.status is HealthStatus.FAILED
    component = next(item for item in snapshot.components if item.kind == "configuration")
    assert component.name == "dotenv-generation"
    assert component.required is True
    assert component.status is HealthStatus.FAILED


async def test_runtime_health_probe_marks_commissioning_expiry_failed() -> None:
    probe = RuntimeHealthProbe(
        channel=cast(IMChannel, HealthChannel(HealthStatus.OK)),
        registry=_registry(HealthAdapter("claude-code", HealthStatus.OK)),
        commissioning=HealthScheduler(HealthStatus.FAILED),
    )

    snapshot = await probe.check()

    assert snapshot.status is HealthStatus.FAILED
    assert snapshot.failed_component_names() == ("configuration:commissioning-receipt",)


async def test_runtime_health_probe_marks_required_component_failure_failed() -> None:
    probe = RuntimeHealthProbe(
        channel=cast(IMChannel, HealthChannel(HealthStatus.FAILED)),
        registry=_registry(HealthAdapter("claude-code", HealthStatus.OK)),
    )

    snapshot = await probe.check()

    assert snapshot.status is HealthStatus.FAILED
    assert snapshot.failed_component_names() == ("channel:telegram",)


async def test_runtime_health_probe_includes_enabled_scheduler_as_required() -> None:
    probe = RuntimeHealthProbe(
        channel=cast(IMChannel, HealthChannel(HealthStatus.OK)),
        registry=_registry(HealthAdapter("claude-code", HealthStatus.OK)),
        morning_scheduler=cast(MorningPushScheduler, HealthScheduler(HealthStatus.FAILED)),
    )

    snapshot = await probe.check()

    assert snapshot.status is HealthStatus.FAILED
    assert snapshot.failed_component_names() == ("scheduler:morning-push",)


async def test_runtime_health_probe_requires_recovery_backup_rpo_health() -> None:
    probe = RuntimeHealthProbe(
        channel=cast(IMChannel, HealthChannel(HealthStatus.OK)),
        registry=_registry(HealthAdapter("claude-code", HealthStatus.OK)),
        recovery_backup_scheduler=HealthScheduler(HealthStatus.FAILED),
    )

    snapshot = await probe.check()

    assert snapshot.status is HealthStatus.FAILED
    assert snapshot.failed_component_names() == ("scheduler:recovery-backup",)


async def test_runtime_health_probe_bounds_hanging_required_check() -> None:
    probe = RuntimeHealthProbe(
        channel=cast(IMChannel, HealthChannel(HealthStatus.OK)),
        registry=_registry(HangingAdapter("claude-code", HealthStatus.OK)),
        timeout_seconds=0.001,
    )

    snapshot = await probe.check()

    assert snapshot.status is HealthStatus.FAILED
    assert snapshot.failed_component_names() == ("adapter:claude-code",)


async def test_runtime_health_probe_does_not_persist_plugin_exception_detail() -> None:
    probe = RuntimeHealthProbe(
        channel=cast(IMChannel, HealthChannel(HealthStatus.OK)),
        registry=_registry(ExplodingAdapter("claude-code", HealthStatus.OK)),
    )

    snapshot = await probe.check()

    assert snapshot.status is HealthStatus.FAILED
    assert "super-secret-provider-detail" not in str(snapshot.to_payload())
