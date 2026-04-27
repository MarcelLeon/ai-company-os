"""Translate incoming channel messages into core tasks."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from aico.core.models import IncomingMessage, Task

TaskIdFactory = Callable[[], str]


class MessageRouter:
    """Phase 1 text router from IM messages to adapter tasks."""

    def __init__(
        self,
        default_persona: str,
        task_id_factory: TaskIdFactory | None = None,
    ) -> None:
        self._default_persona = default_persona
        self._task_id_factory = task_id_factory or _new_task_id

    def to_task(self, message: IncomingMessage) -> Task:
        target_persona, payload = _route_text(
            message.content.text,
            message.mentions,
            self._default_persona,
        )
        return self.to_task_for_target(message, target_persona, payload)

    def to_task_for_target(
        self,
        message: IncomingMessage,
        target_persona: str,
        payload: str,
    ) -> Task:
        return Task(
            task_id=self._task_id_factory(),
            payload=payload,
            requester_id=message.sender_id,
            target_persona=target_persona,
            context_ref=message.raw_ref,
        )


def _new_task_id() -> str:
    return str(uuid4())


def _route_text(
    text: str,
    mentions: tuple[str, ...],
    default_persona: str,
) -> tuple[str, str]:
    stripped = text.strip()
    command = _parse_leading_command(stripped)
    if command is not None:
        target, payload = command
        return target, payload

    if mentions:
        target = mentions[0]
        return target, _strip_leading_mention(stripped, target)

    return default_persona, stripped


def _parse_leading_command(text: str) -> tuple[str, str] | None:
    first, separator, rest = text.partition(" ")
    if first.startswith("/"):
        target = first[1:].split("@", maxsplit=1)[0]
        if target:
            return target, _payload_or_fallback(rest, text)

    if first.startswith("@"):
        target = first[1:]
        if target:
            return target, _payload_or_fallback(rest, text)

    prefix, separator, rest = text.partition(":")
    if separator and _is_route_prefix(prefix):
        return prefix, _payload_or_fallback(rest, text)

    return None


def _strip_leading_mention(text: str, target: str) -> str:
    aliases = {f"@{target}", f"@{target.replace('_', '-')}", f"@{target.replace('-', '_')}"}
    first, separator, rest = text.partition(" ")
    if first in aliases and separator:
        return rest.strip()
    return text


def _payload_or_fallback(payload: str, fallback: str) -> str:
    stripped = payload.strip()
    return stripped if stripped else fallback


def _is_route_prefix(prefix: str) -> bool:
    return bool(prefix) and all(char.isalnum() or char in {"-", "_"} for char in prefix)
