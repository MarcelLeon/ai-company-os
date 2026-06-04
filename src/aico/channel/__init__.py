"""IM channel interfaces."""

from aico.channel.base import DocumentChannel, IMChannel, IncomingMessageHandler
from aico.channel.feishu import FeishuAPIError, FeishuChannel
from aico.channel.telegram import TelegramAPIError, TelegramChannel

__all__ = [
    "FeishuAPIError",
    "FeishuChannel",
    "DocumentChannel",
    "IMChannel",
    "IncomingMessageHandler",
    "TelegramAPIError",
    "TelegramChannel",
]
