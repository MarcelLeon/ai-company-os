"""IM-delivered aico-view HTML snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.core import ChannelTarget, IncomingMessage, MessageContent, MessageKind, SentMessage
from aico.core.project_assignment import (
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
    ProjectProfile,
)
from aico.view.app import ViewSettings
from aico.view.commands import ViewSnapshotCommandHandler
from aico.view.deep_link import DeepLinkSettings

pytestmark = pytest.mark.asyncio


class _TextOnlyChannel:
    name = "feishu"

    def __init__(self) -> None:
        self.sent: list[MessageContent] = []

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> SentMessage:
        del target
        self.sent.append(content)
        return SentMessage(message_id=f"msg-{len(self.sent)}", target=_target())


class _DocumentRecordingChannel(_TextOnlyChannel):
    name = "telegram"

    def __init__(self) -> None:
        super().__init__()
        self.documents: list[tuple[str, bytes, str, str | None]] = []

    async def send_document(
        self,
        target: ChannelTarget,
        *,
        filename: str,
        content: bytes,
        media_type: str,
        caption: str | None = None,
    ) -> SentMessage:
        del target
        self.documents.append((filename, content, media_type, caption))
        return SentMessage(message_id=f"doc-{len(self.documents)}", target=_target())


async def test_view_snapshot_command_requires_enabled_flag(tmp_path: Path) -> None:
    channel = _TextOnlyChannel()
    handler = _handler(tmp_path, channel=channel, enabled=False)

    await handler.handle_view(_incoming("/view"), "")

    assert "AICO_VIEW_ENABLED=true" in channel.sent[-1].text


async def test_view_snapshot_command_sends_self_contained_html_document(tmp_path: Path) -> None:
    channel = _DocumentRecordingChannel()
    handler = _handler(tmp_path, channel=channel, enabled=True)

    await handler.handle_view(_incoming("/view"), "")

    filename, content, media_type, caption = channel.documents[-1]
    html = content.decode("utf-8")
    assert filename == "aico-view-aico.html"
    assert media_type == "text/html; charset=utf-8"
    assert caption == "AICO view snapshot for aico (read-only)"
    assert "aico boss brief" in html
    assert "<style>" in html
    assert "/static/style.css" not in html
    assert "127.0.0.1" not in html
    assert "localhost" not in html


async def test_view_snapshot_command_falls_back_to_local_file_for_text_channel(
    tmp_path: Path,
) -> None:
    channel = _TextOnlyChannel()
    handler = _handler(tmp_path, channel=channel, enabled=True)

    await handler.handle_view(_incoming("/view"), "")

    body = channel.sent[-1].text
    assert "snapshot written locally" in body
    path = Path(body.split(":", maxsplit=1)[1].splitlines()[0].strip())
    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("<!doctype html>")


def _handler(
    tmp_path: Path,
    *,
    channel: _TextOnlyChannel,
    enabled: bool,
) -> ViewSnapshotCommandHandler:
    directory = ProjectAssignmentDirectory(
        ProjectAssignmentConfig(
            projects={"aico": ProjectProfile(id="aico", name="AI Company OS", repo="/repo/aico")}
        )
    )
    directory.set_active_project("telegram:chat-1:boss-1", "aico")
    return ViewSnapshotCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        project_directory=directory,
        settings_factory=lambda project_id: ViewSettings(
            audit_log_path=None,
            memory_path=None,
            state_db_path=None,
            project_ids=(project_id,),
        ),
        deep_link_factory=lambda: DeepLinkSettings(telegram_bot_username=None),
        enabled=enabled,
        output_dir=tmp_path,
    )


def _incoming(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=_target(),
        sender_id="boss-1",
        mentions=(),
        content=MessageContent(kind=MessageKind.TEXT, text=text),
        timestamp=datetime(2026, 6, 2, 10, 0, tzinfo=UTC),
        raw_ref="raw-1",
    )


def _target() -> ChannelTarget:
    return ChannelTarget(channel_name="telegram", target_id="chat-1")
