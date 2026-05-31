"""aico-view IM deep-link generation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from aico.core import (
    AuditEvent,
    AuditEventType,
    ExperienceMeta,
    JsonlAuditSink,
    JsonlMemoryStore,
    MemoryAtom,
    MemoryEvidence,
    MemoryKind,
    MemoryScope,
    MemoryStatus,
    RiskLevel,
)
from aico.view.app import ViewSettings, build_view_app
from aico.view.deep_link import (
    DeepLinkSettings,
    render_command_link,
    render_command_links,
)


def test_render_command_link_uses_telegram_https_when_bot_present() -> None:
    settings = DeepLinkSettings(telegram_bot_username="aico_dogfood_bot")
    html = render_command_link(settings, command="/undo")
    assert 'href="https://t.me/aico_dogfood_bot?text=%2Fundo"' in html
    assert 'class="cmd-link telegram"' in html


def test_render_command_link_strips_leading_at_and_quotes_payload() -> None:
    settings = DeepLinkSettings(telegram_bot_username="aico_dogfood_bot")
    html = render_command_link(
        settings,
        command="/experience promote mem-123 as implementer",
        label="promote",
    )
    assert "%2Fexperience%20promote%20mem-123%20as%20implementer" in html
    assert ">promote</a>" in html


def test_render_command_link_falls_back_to_copy_when_no_bot() -> None:
    settings = DeepLinkSettings(telegram_bot_username=None)
    html = render_command_link(settings, command="/undo")
    assert "cmd-copy" in html
    assert "href=" not in html


def test_render_command_links_groups_multiple_buttons() -> None:
    settings = DeepLinkSettings(telegram_bot_username="bot")
    html = render_command_links(
        settings,
        (("/undo", None), ("/why mem-123", "why mem-123")),
    )
    assert html.count('class="cmd-link telegram"') == 2
    assert 'class="cmd-links"' in html


def _seed(tmp_path: Path) -> tuple[Path, Path]:
    memory_path = tmp_path / "memory.jsonl"
    audit_path = tmp_path / "audit.jsonl"
    store = JsonlMemoryStore(memory_path)
    store.append_atom(
        MemoryAtom(
            memory_id="mem-exp-dl",
            claim="Retry adapter with verbose logging after idle timeout.",
            evidence=(MemoryEvidence(ref="task:seed", source="dream_review"),),
            scope=MemoryScope.project("aico"),
            source="dream_review",
            confidence=0.7,
            created_by="lead-agent",
            status=MemoryStatus.ACTIVE,
            kind=MemoryKind.EXPERIENCE,
            experience=ExperienceMeta(applies_to=("implementer",)),
        )
    )
    sink = JsonlAuditSink(audit_path)
    sink.write(
        AuditEvent(
            event_id="evt-dl-1",
            event_type=AuditEventType.TASK_SUBMITTED,
            task_id="task-dl-1",
            actor_id="boss-1",
            target_persona="implementer",
            risk_level=RiskLevel.READ_ONLY,
            timestamp=datetime(2026, 5, 31, 9, 0, tzinfo=UTC),
            trace_id="task-dl-1",
        )
    )
    return audit_path, memory_path


def test_timeline_view_shows_boss_links_when_bot_configured(tmp_path: Path) -> None:
    audit_path, memory_path = _seed(tmp_path)
    settings = ViewSettings(
        audit_log_path=audit_path,
        memory_path=memory_path,
        state_db_path=None,
        project_ids=("aico",),
    )
    deep_link = DeepLinkSettings(telegram_bot_username="aico_dogfood_bot")
    client = TestClient(build_view_app(settings, deep_link_settings=deep_link))

    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert 'href="https://t.me/aico_dogfood_bot?text=%2Finbox"' in body
    assert "%2Fundo" in body


def test_trace_view_offers_why_and_task_links(tmp_path: Path) -> None:
    audit_path, memory_path = _seed(tmp_path)
    settings = ViewSettings(
        audit_log_path=audit_path,
        memory_path=memory_path,
        state_db_path=None,
        project_ids=("aico",),
    )
    deep_link = DeepLinkSettings(telegram_bot_username="bot")
    client = TestClient(build_view_app(settings, deep_link_settings=deep_link))

    response = client.get("/trace/task-dl-1")
    assert response.status_code == 200
    body = response.text
    assert "ask /why" in body
    assert "open /task" in body


def test_memory_view_offers_archive_link_for_active_experience(tmp_path: Path) -> None:
    audit_path, memory_path = _seed(tmp_path)
    settings = ViewSettings(
        audit_log_path=audit_path,
        memory_path=memory_path,
        state_db_path=None,
        project_ids=("aico",),
    )
    deep_link = DeepLinkSettings(telegram_bot_username="bot")
    client = TestClient(build_view_app(settings, deep_link_settings=deep_link))

    response = client.get("/memory")
    assert response.status_code == 200
    body = response.text
    assert "%2Fexperience%20archive%20mem-exp-dl" in body
    assert ">archive</a>" in body


def test_memory_view_renders_copy_hint_when_no_bot(tmp_path: Path) -> None:
    audit_path, memory_path = _seed(tmp_path)
    settings = ViewSettings(
        audit_log_path=audit_path,
        memory_path=memory_path,
        state_db_path=None,
        project_ids=("aico",),
    )
    client = TestClient(
        build_view_app(settings, deep_link_settings=DeepLinkSettings(telegram_bot_username=None))
    )

    response = client.get("/memory")
    body = response.text
    assert "cmd-copy" in body
    assert ">archive</span>" in body
