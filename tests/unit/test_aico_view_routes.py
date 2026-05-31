"""Read-only aico-view FastAPI routes."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
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


def _seed_memory(path: Path) -> str:
    store = JsonlMemoryStore(path)
    fact = MemoryAtom(
        memory_id="mem-fact-view",
        claim="Boss prefers concise reports.",
        evidence=(MemoryEvidence(ref="raw:1", source="boss"),),
        scope=MemoryScope.project("aico"),
        source="boss_remember_command",
        confidence=1.0,
        created_by="boss-1",
    )
    experience = MemoryAtom(
        memory_id="mem-exp-view",
        claim="Retry adapter with verbose logging after idle timeout.",
        evidence=(MemoryEvidence(ref="task:seed", source="dream_review"),),
        scope=MemoryScope.project("aico"),
        source="dream_review",
        confidence=0.65,
        created_by="lead-agent",
        status=MemoryStatus.ACTIVE,
        kind=MemoryKind.EXPERIENCE,
        experience=ExperienceMeta(applies_to=("implementer",), verdict_hits=1),
    )
    store.append_atom(fact)
    store.append_atom(experience)
    return "task-view-1"


def _seed_audit(path: Path) -> None:
    sink = JsonlAuditSink(path)
    sink.write(
        AuditEvent(
            event_id="evt-view-1",
            event_type=AuditEventType.TASK_SUBMITTED,
            task_id="task-view-1",
            actor_id="boss-1",
            target_persona="implementer",
            risk_level=RiskLevel.READ_ONLY,
            timestamp=datetime(2026, 5, 31, 9, 0, tzinfo=UTC),
            trace_id="task-view-1",
        )
    )
    sink.write(
        AuditEvent(
            event_id="evt-view-2",
            event_type=AuditEventType.TASK_COMPLETED,
            task_id="task-view-1",
            actor_id="boss-1",
            target_persona="implementer",
            risk_level=RiskLevel.READ_ONLY,
            timestamp=datetime(2026, 5, 31, 9, 1, tzinfo=UTC),
            trace_id="task-view-1",
        )
    )


def _client(tmp_path: Path) -> TestClient:
    audit_path = tmp_path / "audit.jsonl"
    memory_path = tmp_path / "memory.jsonl"
    _seed_memory(memory_path)
    _seed_audit(audit_path)
    settings = ViewSettings(
        audit_log_path=audit_path,
        memory_path=memory_path,
        state_db_path=None,
        project_ids=("aico",),
    )
    return TestClient(build_view_app(settings))


def test_healthz_returns_ok(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_timeline_renders_recent_events(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "AICO view" in body
    assert "task_submitted" in body
    assert "task_completed" in body
    assert "mem-fact" in body or "mem-exp" in body


def test_trace_renders_events_for_id(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/trace/task-view-1")
    assert response.status_code == 200
    body = response.text
    assert "task_submitted" in body
    assert "task_completed" in body


def test_trace_unknown_id_returns_404(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/trace/does-not-exist")
    assert response.status_code == 404


def test_memory_view_lists_fact_and_experience(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/memory")
    assert response.status_code == 200
    body = response.text
    assert "Boss prefers concise reports." in body
    assert "Retry adapter with verbose logging" in body
    assert "applies_to: implementer" in body
    assert "hits/misses: 1/0" in body


def test_writes_are_rejected_405(tmp_path: Path) -> None:
    client = _client(tmp_path)
    for method in ("post", "put", "patch", "delete"):
        response = getattr(client, method)("/")
        assert response.status_code == 405


def test_static_css_is_served(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.get("/static/style.css")
    assert response.status_code == 200
    assert "background: var(--bg)" in response.text


@pytest.mark.parametrize(
    "path",
    ["/", "/memory", "/trace/task-view-1", "/static/style.css", "/healthz"],
)
def test_only_get_is_allowed_at_each_route(tmp_path: Path, path: str) -> None:
    client = _client(tmp_path)
    # GET is allowed (verified in other tests).
    forbidden = client.delete(path)
    assert forbidden.status_code in {404, 405}, (path, forbidden.status_code)
