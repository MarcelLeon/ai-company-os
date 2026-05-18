"""IM channel interfaces."""

from aico.channel.base import IMChannel, IncomingMessageHandler
from aico.channel.feishu import FeishuAPIError, FeishuChannel
from aico.channel.telegram import TelegramAPIError, TelegramChannel

__all__ = [
    "FeishuAPIError",
    "FeishuChannel",
    "IMChannel",
    "IncomingMessageHandler",
    "TelegramAPIError",
    "TelegramChannel",
]
