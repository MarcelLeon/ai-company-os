"""IM-delivered aico-view HTML snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.core import (
    AuditEvent,
    AuditEventType,
    ChannelTarget,
    IncomingMessage,
    JsonlAuditSink,
    MessageContent,
    MessageKind,
    MetadataEntry,
    RiskLevel,
    SentMessage,
    Task,
    TaskSnapshot,
    TaskStatus,
)
from aico.core.offline_delegation import (
    OfflineDelegationRecord,
    SQLiteOfflineDelegationStore,
)
from aico.core.project_assignment import (
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
    ProjectProfile,
)
from aico.core.task_store import SQLiteTaskStateStore
from aico.view.app import ViewSettings
from aico.view.commands import ViewSnapshotCommandHandler
from aico.view.deep_link import DeepLinkSettings
from aico.view.snapshot import render_view_snapshot_html

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

    assert channel.sent[-1].text.startswith("已生成 AICO view")
    assert "/inbox" in channel.sent[-1].text
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
    assert "已生成 AICO view" in body
    assert "本地文件" in body
    local_file_line = next(line for line in body.splitlines() if line.startswith("本地文件: "))
    path = Path(local_file_line.split(":", maxsplit=1)[1].strip())
    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("<!doctype html>")


async def test_view_snapshot_html_includes_task_description_and_detail_command(
    tmp_path: Path,
) -> None:
    state_db = tmp_path / "state.db"
    store = SQLiteTaskStateStore(state_db)
    store.upsert_task_record(
        Task(
            task_id="task-view-long",
            payload=(
                "Role summary: Lead agent.\n\n"
                "Current task:\n"
                "修复 data-agent-v1 Telegram baseline 的表格可读性,并补齐 /view 任务详情。"
            ),
            requester_id="boss-1",
            target_persona="lead",
            metadata=(
                MetadataEntry(key="aico.intent", value="goal_brief"),
                MetadataEntry(key="aico.project_id", value="data-agent-v1"),
            ),
            created_at=datetime(2026, 6, 2, 10, 0, tzinfo=UTC),
        )
    )
    store.upsert_task_snapshot(
        TaskSnapshot(
            task_id="task-view-long",
            target_persona="lead",
            adapter_name="codex",
            status=TaskStatus.RUNNING,
            metadata=(MetadataEntry(key="aico.project_id", value="data-agent-v1"),),
            created_at=datetime(2026, 6, 2, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 6, 2, 10, 2, tzinfo=UTC),
        )
    )

    html = render_view_snapshot_html(
        ViewSettings(
            audit_log_path=None,
            memory_path=None,
            state_db_path=state_db,
            project_ids=("data-agent-v1",),
        ),
        DeepLinkSettings(telegram_bot_username="ai_co_telegram_bot"),
        project_id="data-agent-v1",
        generated_at=datetime(2026, 6, 2, 10, 3, tzinfo=UTC),
    )

    assert "recent tasks" in html
    assert "task-vie" in html
    assert "lead · codex · running" in html
    assert "修复 data-agent-v1 Telegram baseline 的表格可读性" in html
    assert "open /task task-vie" in html
    assert "https://t.me/ai_co_telegram_bot?text=%2Ftask%20task-vie" in html


async def test_view_snapshot_hides_provider_session_identifier(tmp_path: Path) -> None:
    state_db = tmp_path / "state.db"
    store = SQLiteTaskStateStore(state_db)
    store.upsert_task_snapshot(
        TaskSnapshot(
            task_id="task-session-busy",
            target_persona="reviewer",
            adapter_name="codex",
            status=TaskStatus.FAILED,
            reason=("Error: Session ID 019f3b9a-8a26-7453-ac6f-246aaa25b2b6 is already in use."),
            metadata=(MetadataEntry(key="aico.project_id", value="aico"),),
        )
    )

    html = render_view_snapshot_html(
        ViewSettings(
            audit_log_path=None,
            memory_path=None,
            state_db_path=state_db,
            project_ids=("aico",),
        ),
        DeepLinkSettings(telegram_bot_username="ai_co_telegram_bot"),
        project_id="aico",
    )

    assert "role session busy" in html
    assert "Session ID" not in html
    assert "019f3b9a" not in html


async def test_view_snapshot_prioritizes_project_attention_and_hides_other_project(
    tmp_path: Path,
) -> None:
    state_db = tmp_path / "state.db"
    store = SQLiteTaskStateStore(state_db)
    tasks = (
        _snapshot_task(
            "task-approval-aico",
            "aico",
            TaskStatus.WAITING_APPROVAL,
            "发布动作需要老板确认",
            risk_level=RiskLevel.DESTRUCTIVE,
        ),
        _snapshot_task(
            "task-failed-aico",
            "aico",
            TaskStatus.FAILED,
            "provider failed after checkpoint",
        ),
        _snapshot_task("task-running-aico", "aico", TaskStatus.RUNNING, None),
        _snapshot_task(
            "task-night-aico",
            "aico",
            TaskStatus.DONE,
            None,
            intent="offline_delegation",
        ),
        _snapshot_task(
            "task-secret-other",
            "secret-project",
            TaskStatus.FAILED,
            "TOP SECRET OTHER PROJECT",
        ),
    )
    for task, snapshot in tasks:
        store.upsert_task_record(task)
        store.upsert_task_snapshot(snapshot)

    offline_store = SQLiteOfflineDelegationStore(state_db)
    offline_store.upsert_record(
        "telegram:chat-1:boss-1",
        OfflineDelegationRecord(
            delegation_id="night-task-nig",
            project_id="aico",
            project_name="AI Company OS",
            role="lead",
            agent="codex",
            task_id="task-night-aico",
            goal="整理昨夜发布准备并留下交接",
            review_task_ids=("review-challenger", "review-reviewer"),
            created_at=datetime(2026, 7, 21, 1, 0, tzinfo=UTC),
        ),
    )
    offline_store.upsert_record(
        "telegram:chat-2:boss-1",
        OfflineDelegationRecord(
            delegation_id="night-secret",
            project_id="secret-project",
            project_name="Secret",
            role="lead",
            agent="claude",
            task_id="task-secret-other",
            goal="TOP SECRET OVERNIGHT GOAL",
            created_at=datetime(2026, 7, 21, 2, 0, tzinfo=UTC),
        ),
    )
    audit_path = tmp_path / "audit.jsonl"
    sink = JsonlAuditSink(audit_path)
    sink.write(_audit_event("task-failed-aico", "AICO FAILURE EVENT"))
    sink.write(_audit_event("task-secret-other", "TOP SECRET AUDIT EVENT"))

    html = render_view_snapshot_html(
        ViewSettings(
            audit_log_path=audit_path,
            memory_path=None,
            state_db_path=state_db,
            project_ids=("aico",),
        ),
        DeepLinkSettings(telegram_bot_username="ai_co_telegram_bot"),
        project_id="aico",
        generated_at=datetime(2026, 7, 21, 8, 0, tzinfo=UTC),
    )

    assert "First action" in html
    assert "Decide task-app before work can continue" in html
    assert "/approve task-app" in html
    assert "/reject task-app" in html
    assert "Approval needed" in html
    assert "Blockers" in html
    assert "Overnight results" in html
    assert "整理昨夜发布准备并留下交接" in html
    assert "lead · codex · done · 2 reviews" in html
    assert html.index("First action") < html.index("recent tasks")
    assert html.index("Overnight results") < html.index("recent timeline")
    assert "TOP SECRET OTHER PROJECT" not in html
    assert "TOP SECRET OVERNIGHT GOAL" not in html
    assert "TOP SECRET AUDIT EVENT" not in html


async def test_view_snapshot_first_action_falls_back_from_blocker_to_empty_state(
    tmp_path: Path,
) -> None:
    state_db = tmp_path / "state.db"
    store = SQLiteTaskStateStore(state_db)
    task, snapshot = _snapshot_task(
        "task-failed-only",
        "aico",
        TaskStatus.FAILED,
        "tests failed",
    )
    store.upsert_task_record(task)
    store.upsert_task_snapshot(snapshot)
    settings = ViewSettings(
        audit_log_path=None,
        memory_path=None,
        state_db_path=state_db,
        project_ids=("aico",),
    )

    failed_html = render_view_snapshot_html(
        settings,
        DeepLinkSettings(telegram_bot_username=None),
        project_id="aico",
    )

    assert "Recover task-fai before starting new work" in failed_html
    store.upsert_task_snapshot(
        snapshot.model_copy(update={"status": TaskStatus.DONE, "reason": None})
    )

    quiet_html = render_view_snapshot_html(
        settings,
        DeepLinkSettings(telegram_bot_username=None),
        project_id="aico",
    )

    assert "No decision is waiting" in quiet_html
    assert "/inbox" in quiet_html
    assert "/morning" in quiet_html


def _snapshot_task(
    task_id: str,
    project_id: str,
    status: TaskStatus,
    reason: str | None,
    *,
    risk_level: RiskLevel = RiskLevel.READ_ONLY,
    intent: str = "project_task",
) -> tuple[Task, TaskSnapshot]:
    metadata = (
        MetadataEntry(key="aico.project_id", value=project_id),
        MetadataEntry(key="aico.intent", value=intent),
    )
    task = Task(
        task_id=task_id,
        payload=f"Current task:\nHandle {task_id}",
        requester_id="boss-1",
        target_persona="lead",
        metadata=metadata,
        created_at=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
    )
    snapshot = TaskSnapshot(
        task_id=task_id,
        target_persona="lead",
        adapter_name="codex",
        status=status,
        reason=reason,
        risk_level=risk_level,
        metadata=metadata,
        created_at=datetime(2026, 7, 21, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 7, 21, 3, 0, tzinfo=UTC),
    )
    return task, snapshot


def _audit_event(task_id: str, detail: str) -> AuditEvent:
    return AuditEvent(
        event_id=f"event-{task_id}",
        event_type=AuditEventType.TASK_FAILED,
        task_id=task_id,
        actor_id="boss-1",
        target_persona="lead",
        risk_level=RiskLevel.READ_ONLY,
        detail=detail,
        timestamp=datetime(2026, 7, 21, 4, 0, tzinfo=UTC),
        trace_id=task_id,
    )


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
