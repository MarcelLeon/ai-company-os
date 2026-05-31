"""IM deep-link helpers for aico-view templates.

The view is read-only; deep links push the boss back into IM with the
command pre-filled. Telegram uses the documented `tg://resolve` and
`https://t.me/<bot>?text=` schemes; Feishu has no equivalent standard
deep-link API, so we fall back to a plain text hint the boss can
copy/paste.

Bot username comes from `AICO_VIEW_TELEGRAM_BOT_USERNAME` env (or
constructor argument) — we deliberately do NOT call the Telegram getMe
API at view start to keep the view process independent of network
access.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from html import escape
from urllib.parse import quote


@dataclass(frozen=True)
class DeepLinkSettings:
    telegram_bot_username: str | None = None

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_username and self.telegram_bot_username.strip())


def load_deep_link_settings_from_env() -> DeepLinkSettings:
    bot = os.environ.get("AICO_VIEW_TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")
    return DeepLinkSettings(telegram_bot_username=bot or None)


def render_command_link(
    settings: DeepLinkSettings,
    *,
    command: str,
    label: str | None = None,
) -> str:
    """Render a single deep-link button (or copy hint when no platform fits)."""
    if not command.startswith("/"):
        raise ValueError(f"deep link commands must start with '/': {command!r}")
    label = label or command
    if settings.telegram_enabled:
        url = _telegram_url(settings.telegram_bot_username or "", command)
        return (
            f'<a class="cmd-link telegram" href="{escape(url)}"'
            f' title="open in Telegram">{escape(label)}</a>'
        )
    return f'<span class="cmd-copy" title="copy this command into IM">{escape(label)}</span>'


def render_command_links(
    settings: DeepLinkSettings,
    commands: tuple[tuple[str, str | None], ...],
) -> str:
    """Render a row of deep-link buttons."""
    if not commands:
        return ""
    rendered = "".join(
        render_command_link(settings, command=cmd, label=label) for cmd, label in commands
    )
    return f'<div class="cmd-links">{rendered}</div>'


def _telegram_url(bot_username: str, command: str) -> str:
    text = quote(command, safe="")
    return f"https://t.me/{bot_username}?text={text}"
