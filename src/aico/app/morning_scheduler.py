"""Optional scheduled morning handoff push for absence-first operation."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from aico.core.models import ChannelTarget
from aico.core.orchestrator import Orchestrator

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class MorningPushConfig:
    channel_name: str
    target_id: str
    project_id: str
    push_time: time
    thread_id: str | None = None
    scope_id: str | None = None
    push_on_start: bool = False


class MorningPushScheduler:
    """Send `/morning` output into a configured IM chat on a daily schedule."""

    def __init__(
        self,
        *,
        orchestrator: Orchestrator,
        config: MorningPushConfig,
    ) -> None:
        self._orchestrator = orchestrator
        self._config = config
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="aico-morning-push")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def dispatch_once(self) -> None:
        target = ChannelTarget(
            channel_name=self._config.channel_name,
            target_id=self._config.target_id,
            thread_id=self._config.thread_id,
        )
        await self._orchestrator.send_morning_handoff(
            target,
            project_id=self._config.project_id,
            scope_id=self._config.scope_id,
        )

    async def _run(self) -> None:
        if self._config.push_on_start:
            await self._safe_dispatch()
        while True:
            await asyncio.sleep(seconds_until_next_push(self._config.push_time))
            await self._safe_dispatch()

    async def _safe_dispatch(self) -> None:
        try:
            await self.dispatch_once()
        except Exception:
            log.exception(
                "Morning push failed: project=%s target=%s",
                self._config.project_id,
                self._config.target_id,
            )


def parse_push_time(value: str) -> time:
    try:
        hour_text, minute_text = value.strip().split(":", maxsplit=1)
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError as exc:
        raise ValueError("morning push time must be HH:MM") from exc
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("morning push time must be HH:MM")
    return time(hour=hour, minute=minute)


def seconds_until_next_push(push_time: time, *, now: datetime | None = None) -> float:
    current = now or datetime.now()
    next_push = current.replace(
        hour=push_time.hour,
        minute=push_time.minute,
        second=0,
        microsecond=0,
    )
    if next_push <= current:
        next_push += timedelta(days=1)
    return (next_push - current).total_seconds()
