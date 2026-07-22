"""Fail-closed authorization for external IM control-plane ingress."""

from __future__ import annotations

import logging
from typing import Protocol

from aico.core.models import IncomingMessage

log = logging.getLogger(__name__)

MAX_INGRESS_IDENTITIES = 16
MAX_INGRESS_ID_CHARS = 256
_PLACEHOLDER_FRAGMENTS = ("replace-with", "replace-me", "your-", "<", ">")


class IngressBindingError(ValueError):
    """Raised when an owner or target binding is unsafe or unbounded."""


class IngressAuthorizer(Protocol):
    """Decide whether one immutable channel message may enter orchestration."""

    def allows(self, message: IncomingMessage) -> bool: ...


class AllowAllIngressAuthorizer:
    """Compatibility policy for explicitly embedded/test orchestrators."""

    def allows(self, message: IncomingMessage) -> bool:
        _ = message
        return True


class OwnerBoundIngressAuthorizer:
    """Require exact channel, owner sender, and trusted reply target bindings."""

    def __init__(
        self,
        *,
        channel_name: str,
        owner_sender_ids: tuple[str, ...],
        trusted_target_ids: tuple[str, ...],
    ) -> None:
        self._channel_name = channel_name
        self._owner_sender_ids = frozenset(owner_sender_ids)
        self._trusted_target_ids = frozenset(trusted_target_ids)

    def allows(self, message: IncomingMessage) -> bool:
        return (
            message.channel_name == self._channel_name
            and message.source.channel_name == self._channel_name
            and message.sender_id in self._owner_sender_ids
            and message.source.target_id in self._trusted_target_ids
        )


class IngressGuard:
    """Apply authorization before parsing and emit bounded identity-safe evidence."""

    def __init__(
        self,
        authorizer: IngressAuthorizer,
        *,
        reveal_denied_identity: bool = False,
    ) -> None:
        self._authorizer = authorizer
        self._reveal_denied_identity = reveal_denied_identity
        self._denied_count = 0

    def accepts(self, message: IncomingMessage) -> bool:
        if self._authorizer.allows(message):
            return True
        self._denied_count += 1
        if _is_power_of_two(self._denied_count):
            self._log_denial(message)
        return False

    def _log_denial(self, message: IncomingMessage) -> None:
        if self._reveal_denied_identity:
            log.warning(
                "Unauthorized IM ingress dropped: total=%s channel=%s sender=%s target=%s",
                self._denied_count,
                _log_value(message.channel_name),
                _log_value(message.sender_id),
                _log_value(message.source.target_id),
            )
            return
        log.warning("Unauthorized IM ingress dropped: total=%s", self._denied_count)


def parse_ingress_ids(value: str) -> tuple[str, ...]:
    """Parse one bounded comma-separated identity list without accepting placeholders."""
    identities: list[str] = []
    seen: set[str] = set()
    for raw_identity in value.split(","):
        identity = raw_identity.strip()
        if not identity:
            continue
        if not _safe_identity(identity):
            raise IngressBindingError("IM ingress identity binding is invalid")
        if identity not in seen:
            identities.append(identity)
            seen.add(identity)
    if len(identities) > MAX_INGRESS_IDENTITIES:
        raise IngressBindingError("IM ingress identity binding is unbounded")
    return tuple(identities)


def _safe_identity(identity: str) -> bool:
    normalized = identity.casefold()
    return (
        len(identity) <= MAX_INGRESS_ID_CHARS
        and normalized != "unknown"
        and not any(character.isspace() or ord(character) < 32 for character in identity)
        and not any(fragment in normalized for fragment in _PLACEHOLDER_FRAGMENTS)
    )


def _is_power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


def _log_value(value: str) -> str:
    return ascii(value[:MAX_INGRESS_ID_CHARS])
