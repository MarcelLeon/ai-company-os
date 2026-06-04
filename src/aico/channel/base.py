"""Protocol implemented by IM channel plugins."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol, TypeAlias, runtime_checkable

if TYPE_CHECKING:
    from aico.core.models import (
        ChannelTarget,
        HealthStatus,
        IncomingMessage,
        MessageContent,
        SentMessage,
    )

IncomingMessageHandler: TypeAlias = Callable[["IncomingMessage"], Awaitable[None]]


@runtime_checkable
class IMChannel(Protocol):
    """Boundary for IM platforms such as Telegram, Feishu, and QQ."""

    @property
    def name(self) -> str: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> SentMessage: ...

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> None: ...

    async def delete_message(self, target: ChannelTarget, message_id: str) -> None: ...

    def on_incoming(self, handler: IncomingMessageHandler) -> None: ...

    async def health_check(self) -> HealthStatus: ...


@runtime_checkable
class DocumentChannel(Protocol):
    """Optional channel capability for sending file attachments."""

    async def send_document(
        self,
        target: ChannelTarget,
        *,
        filename: str,
        content: bytes,
        media_type: str,
        caption: str | None = None,
    ) -> SentMessage: ...
