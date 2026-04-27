"""IM channel interfaces."""

from aico.channel.base import IMChannel, IncomingMessageHandler
from aico.channel.telegram import TelegramAPIError, TelegramChannel

__all__ = ["IMChannel", "IncomingMessageHandler", "TelegramAPIError", "TelegramChannel"]
