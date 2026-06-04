"""IM command handler for sending aico-view HTML snapshots."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from aico.channel import DocumentChannel, IMChannel
from aico.core.models import IncomingMessage, MessageContent
from aico.core.project_assignment import ProjectAssignmentDirectory, ProjectProfile
from aico.core.session_commands import session_scope
from aico.view.app import ViewSettings
from aico.view.deep_link import DeepLinkSettings
from aico.view.snapshot import render_view_snapshot_html

ViewSettingsFactory = Callable[[str], ViewSettings]
DeepLinkSettingsFactory = Callable[[], DeepLinkSettings]


class ViewSnapshotCommandHandler:
    """Send read-only project state as a self-contained HTML file."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        project_directory: ProjectAssignmentDirectory,
        settings_factory: ViewSettingsFactory,
        deep_link_factory: DeepLinkSettingsFactory,
        enabled: bool,
        output_dir: Path,
    ) -> None:
        self._channel = channel
        self._project_directory = project_directory
        self._settings_factory = settings_factory
        self._deep_link_factory = deep_link_factory
        self._enabled = enabled
        self._output_dir = output_dir

    async def handle_view(self, message: IncomingMessage, payload: str) -> None:
        if not self._enabled:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=(
                        "AICO view snapshots are disabled. Set AICO_VIEW_ENABLED=true "
                        "and restart aico-phase1."
                    )
                ),
            )
            return
        project = self._project_for(message, payload)
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="No active project. Use /project <project> first."),
            )
            return
        await self._send_snapshot(message, project)

    async def _send_snapshot(self, message: IncomingMessage, project: ProjectProfile) -> None:
        settings = self._settings_factory(project.id)
        html = render_view_snapshot_html(
            settings,
            self._deep_link_factory(),
            project_id=project.id,
        )
        filename = f"aico-view-{_safe_filename(project.id)}.html"
        content = html.encode("utf-8")
        if isinstance(self._channel, DocumentChannel):
            await self._channel.send_document(
                message.source,
                filename=filename,
                content=content,
                media_type="text/html; charset=utf-8",
                caption=f"AICO view snapshot for {project.id} (read-only)",
            )
            return
        path = self._write_snapshot_file(filename, content)
        await self._channel.send_message(
            message.source,
            MessageContent(
                text=(
                    f"AICO view snapshot written locally: {path}\n"
                    "This channel cannot send document attachments yet."
                )
            ),
        )

    def _project_for(self, message: IncomingMessage, payload: str) -> ProjectProfile | None:
        project_id = payload.strip()
        if project_id:
            return self._project_directory.project(project_id)
        return self._project_directory.active_project(session_scope(message))

    def _write_snapshot_file(self, filename: str, content: bytes) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        path = self._output_dir / filename
        path.write_bytes(content)
        return path.resolve()


def _safe_filename(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.strip())
    return safe or "project"
