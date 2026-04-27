"""Protocol implemented by AI tool adapters."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from aico.core.models import AdapterStatus, Capability, HealthStatus, Task, TaskAck, TaskOutput


@runtime_checkable
class AIAdapter(Protocol):
    """Boundary for integrating AI CLIs without leaking tool-specific behavior."""

    @property
    def name(self) -> str: ...

    def capabilities(self) -> frozenset[Capability]: ...

    async def receive_task(self, task: Task) -> TaskAck: ...

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]: ...

    def status(self) -> AdapterStatus: ...

    async def interrupt(self, task_id: str) -> None: ...

    async def health_check(self) -> HealthStatus: ...
