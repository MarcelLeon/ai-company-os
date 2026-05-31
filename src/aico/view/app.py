"""Read-only FastAPI app providing Timeline / Task Trace / Memory Tree views.

This module deliberately does NOT spin up Phase 1 runtime, channels, or
adapters. It opens the same on-disk artifacts that an orchestrator would
write (audit JSONL, memory JSONL, optional SQLite task store) and serves
a small mobile-friendly HTML view. Every route is GET; the FastAPI app
explicitly rejects non-GET methods.

Three views, in priority order:
- /            -> Timeline (most recent events first)
- /trace/<id>  -> Task Trace (all events sharing a trace_id)
- /memory      -> Memory Tree (fact + experience, grouped by scope)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from html import escape
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from aico.core.audit import read_jsonl_audit_events
from aico.core.command_messages import short_id_text
from aico.core.memory import (
    JsonlMemoryStore,
    MemoryAtom,
    MemoryKind,
    MemoryScope,
)
from aico.core.models import AuditEvent, TaskSnapshot
from aico.core.task_store import SQLiteTaskStateStore
from aico.core.unified_event import (
    InMemoryUnifiedEventIndex,
    UnifiedEvent,
    UnifiedEventIndex,
)
from aico.view.deep_link import (
    DeepLinkSettings,
    load_deep_link_settings_from_env,
    render_command_links,
)


@dataclass(frozen=True)
class ViewSettings:
    """Where to read JSONL / SQLite truth sources from."""

    audit_log_path: Path | None
    memory_path: Path | None
    state_db_path: Path | None
    project_ids: tuple[str, ...] = ()


def load_view_settings_from_env() -> ViewSettings:
    """Read the same env vars the Phase 1 runtime uses (read-only)."""
    audit = os.environ.get("AICO_AUDIT_LOG_PATH")
    memory = os.environ.get("AICO_MEMORY_PATH")
    state_db = os.environ.get("AICO_STATE_DB_PATH")
    project_ids_raw = os.environ.get("AICO_VIEW_PROJECT_IDS", "")
    return ViewSettings(
        audit_log_path=Path(audit) if audit else None,
        memory_path=Path(memory) if memory else None,
        state_db_path=_resolved_state_db_path(state_db),
        project_ids=tuple(
            project_id.strip() for project_id in project_ids_raw.split(",") if project_id.strip()
        ),
    )


def _resolved_state_db_path(raw: str | None) -> Path | None:
    if not raw:
        return None
    lowered = raw.strip().lower()
    if lowered in {"true", "1", "yes"}:
        return Path(".aico/state.db")
    return Path(raw)


def build_view_app(
    settings: ViewSettings | None = None,
    *,
    deep_link_settings: DeepLinkSettings | None = None,
) -> FastAPI:
    """Construct the read-only aico-view FastAPI application."""
    settings = settings or load_view_settings_from_env()
    deep_link_settings = deep_link_settings or load_deep_link_settings_from_env()

    app = FastAPI(title="AI Company OS — View", docs_url=None, redoc_url=None)
    app.state.aico_view_settings = settings
    app.state.aico_deep_link_settings = deep_link_settings

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def timeline_view(request: Request) -> HTMLResponse:
        del request
        index = _build_index(settings)
        recent = index.recent(limit=100)
        return HTMLResponse(_render_timeline(recent, deep_link_settings))

    @app.get("/trace/{trace_id}", response_class=HTMLResponse)
    async def trace_view(trace_id: str) -> HTMLResponse:
        index = _build_index(settings)
        events = index.events_for_trace(trace_id)
        if not events:
            for event in index.all_events():
                if event.short_id == short_id_text(trace_id) or event.trace_id.startswith(trace_id):
                    events = index.events_for_trace(event.trace_id)
                    break
        if not events:
            raise HTTPException(status_code=404, detail=f"trace not found: {trace_id}")
        return HTMLResponse(_render_trace(trace_id, events, deep_link_settings))

    @app.get("/memory", response_class=HTMLResponse)
    async def memory_view() -> HTMLResponse:
        atoms = _load_memory_atoms(settings)
        return HTMLResponse(_render_memory(atoms, deep_link_settings))

    @app.get("/static/style.css", response_class=PlainTextResponse)
    async def style_css() -> PlainTextResponse:
        return PlainTextResponse(_VIEW_CSS, media_type="text/css")

    return app


def _build_index(settings: ViewSettings) -> UnifiedEventIndex:
    audit_events = _load_audit_events(settings)
    memory_atoms = _load_memory_atoms(settings)
    task_snapshots = _load_task_snapshots(settings)
    return InMemoryUnifiedEventIndex(
        audit_events=audit_events,
        memory_atoms=memory_atoms,
        task_snapshots=task_snapshots,
    )


def _load_audit_events(settings: ViewSettings) -> tuple[AuditEvent, ...]:
    if settings.audit_log_path is None or not settings.audit_log_path.exists():
        return ()
    return read_jsonl_audit_events(settings.audit_log_path)


def _load_memory_atoms(settings: ViewSettings) -> tuple[MemoryAtom, ...]:
    if settings.memory_path is None or not settings.memory_path.exists():
        return ()
    store = JsonlMemoryStore(settings.memory_path)
    if not settings.project_ids:
        # No project hint; pull every project we can infer from atoms themselves.
        seen_project_ids: list[str] = []
        for atom in store._atoms.values():  # noqa: SLF001 — read-only access into in-mem index
            project_id = atom.scope.project_id
            if project_id and project_id not in seen_project_ids:
                seen_project_ids.append(project_id)
        project_ids = tuple(seen_project_ids)
    else:
        project_ids = settings.project_ids
    atoms: list[MemoryAtom] = []
    for project_id in project_ids:
        atoms.extend(store.list_atoms(MemoryScope.project(project_id), include_archived=True))
    return tuple(atoms)


def _load_task_snapshots(settings: ViewSettings) -> tuple[TaskSnapshot, ...]:
    if settings.state_db_path is None or not settings.state_db_path.exists():
        return ()
    store = SQLiteTaskStateStore(settings.state_db_path)
    return store.load_task_snapshots()


def _render_layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)} — AICO view</title>
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
<header><a class="home" href="/">AICO view</a><span class="sep">·</span>{escape(title)}</header>
<main>{body}</main>
<footer>read-only · write through IM</footer>
</body>
</html>"""


def _render_timeline(
    events: tuple[UnifiedEvent, ...],
    deep_link: DeepLinkSettings,
) -> str:
    if not events:
        body = '<p class="empty">No events yet.</p>'
        return _render_layout("Timeline", body)
    rows: list[str] = []
    for event in reversed(events):
        ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        trace_link = f'<a href="/trace/{escape(event.trace_id)}">{escape(event.short_id)}</a>'
        rows.append(
            f"<li><time>{escape(ts)}</time>"
            f"<span class='src {escape(event.source.value)}'>{escape(event.source.value)}</span>"
            f"<span class='kind'>{escape(event.kind)}</span>"
            f"{trace_link}"
            f"<span class='summary'>{escape(event.summary)}</span></li>"
        )
    boss_links = render_command_links(
        deep_link,
        (("/inbox", "/inbox"), ("/morning", "/morning"), ("/undo", "/undo")),
    )
    body = (
        '<ul class="timeline">'
        + "".join(rows)
        + "</ul>"
        + '<p class="hint">Tap a short id to open its trace.</p>'
        + boss_links
    )
    return _render_layout("Timeline", body)


def _render_trace(
    trace_id: str,
    events: tuple[UnifiedEvent, ...],
    deep_link: DeepLinkSettings,
) -> str:
    rows: list[str] = []
    for event in events:
        ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        rows.append(
            f"<li><time>{escape(ts)}</time>"
            f"<span class='src {escape(event.source.value)}'>{escape(event.source.value)}</span>"
            f"<span class='kind'>{escape(event.kind)}</span>"
            f"<span class='id'>{escape(event.short_id)}</span>"
            f"<span class='summary'>{escape(event.summary)}</span></li>"
        )
    short = short_id_text(trace_id)
    boss_links = render_command_links(
        deep_link,
        (
            (f"/why {short}", f"ask /why {short}"),
            (f"/task {short}", f"open /task {short}"),
        ),
    )
    body = (
        f"<h2>trace {escape(short)}</h2>"
        + '<ul class="trace">'
        + "".join(rows)
        + "</ul>"
        + boss_links
    )
    return _render_layout("Task Trace", body)


def _render_memory(
    atoms: tuple[MemoryAtom, ...],
    deep_link: DeepLinkSettings,
) -> str:
    if not atoms:
        return _render_layout("Memory Tree", '<p class="empty">No memory recorded.</p>')
    facts = [atom for atom in atoms if atom.kind is MemoryKind.FACT]
    experiences = [atom for atom in atoms if atom.kind is MemoryKind.EXPERIENCE]
    body_parts = ["<h2>experiences</h2>"]
    body_parts.append(
        _render_memory_list(experiences, kind_label="experience", deep_link=deep_link)
    )
    body_parts.append("<h2>facts</h2>")
    body_parts.append(_render_memory_list(facts, kind_label="fact", deep_link=deep_link))
    return _render_layout("Memory Tree", "".join(body_parts))


def _render_memory_list(
    atoms: list[MemoryAtom],
    *,
    kind_label: str,
    deep_link: DeepLinkSettings,
) -> str:
    if not atoms:
        return f'<p class="empty">no {escape(kind_label)} memory.</p>'
    rows: list[str] = []
    for atom in atoms:
        status_class = atom.status.value
        meta = ""
        if atom.experience is not None:
            triggers = ", ".join(atom.experience.triggers) or "—"
            applies = ", ".join(atom.experience.applies_to) or "any role"
            meta = (
                f"<div class='meta'>applies_to: {escape(applies)}"
                f" · triggers: {escape(triggers)}"
                f" · hits/misses: {atom.experience.verdict_hits}"
                f"/{atom.experience.verdict_misses}</div>"
            )
        actions = _memory_action_links(atom, deep_link)
        rows.append(
            f"<li class='atom {escape(status_class)}'>"
            f"<span class='id'>{escape(short_id_text(atom.memory_id))}</span>"
            f"<span class='status'>{escape(atom.status.value)}</span>"
            f"<span class='confidence'>conf: {atom.confidence:.2f}</span>"
            f"<div class='claim'>{escape(atom.claim)}</div>"
            f"{meta}"
            f"{actions}"
            f"</li>"
        )
    return '<ul class="memory">' + "".join(rows) + "</ul>"


def _memory_action_links(atom: MemoryAtom, deep_link: DeepLinkSettings) -> str:
    pairs: list[tuple[str, str | None]] = []
    if atom.kind is MemoryKind.EXPERIENCE:
        if atom.status.value == "candidate":
            pairs.append((f"/experience promote {atom.memory_id}", "promote"))
        elif atom.status.value == "active":
            pairs.append((f"/experience archive {atom.memory_id}", "archive"))
    elif atom.kind is MemoryKind.FACT and atom.status.value == "active":
        pairs.append((f"/forget {atom.memory_id}", "forget"))
    if not pairs:
        return ""
    return render_command_links(deep_link, tuple(pairs))


_VIEW_CSS = """
:root {
  --bg:#0b1020; --card:#141a2e; --text:#e6e9f5; --muted:#9aa3c0;
  --accent:#7dd3fc; --warn:#fbbf24; --danger:#f87171; --ok:#34d399;
}
* { box-sizing: border-box; }
body { margin:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--text); font-size: 15px; line-height: 1.45; }
header { padding:.75rem 1rem; background: var(--card); position: sticky; top:0; }
header .home { color: var(--accent); text-decoration: none; font-weight: 600; }
header .sep { color: var(--muted); margin: 0 .5rem; }
main { padding: .75rem 1rem; max-width: 720px; margin: 0 auto; }
footer { padding: 1rem; text-align: center; color: var(--muted); font-size: .85em; }
.empty, .hint { color: var(--muted); }
h2 { margin: 1.25rem 0 .5rem; font-size: 1rem; color: var(--accent); }
ul { list-style: none; padding: 0; margin: 0; }
li { padding: .5rem .6rem; background: var(--card); margin: .35rem 0; border-radius: 6px;
  display: grid; grid-template-columns: auto auto 1fr; gap: .4rem; align-items: baseline; }
li time { color: var(--muted); font-size: .8em; grid-column: 1 / -1; }
.src { font-size: .7em; padding: 1px 5px; border-radius: 3px; background: #222b48; }
.src.audit { background:#1e3a5c; }
.src.memory { background:#3b2a5c; }
.src.task { background:#5c3a1e; }
.kind { color: var(--muted); font-size: .85em; }
.summary { grid-column: 1 / -1; }
.atom.archived { opacity:.55; }
.atom .id { color: var(--accent); font-family: ui-monospace, monospace; }
.atom .status { font-size: .7em; padding: 1px 5px; border-radius: 3px; background:#2a3251; }
.atom .confidence { color: var(--muted); font-size: .8em; }
.atom .claim { grid-column: 1 / -1; }
.atom .meta { grid-column: 1 / -1; color: var(--muted); font-size: .8em; }
a { color: var(--accent); }
.id { color: var(--accent); font-family: ui-monospace, monospace; }
.trace .summary { color: var(--text); }
.cmd-links { display: flex; flex-wrap: wrap; gap: .4rem; margin: 1rem 0; }
.cmd-link, .cmd-copy { display: inline-block; padding: .35rem .7rem; border-radius: 999px;
  background: var(--card); border: 1px solid var(--accent); color: var(--accent);
  text-decoration: none; font-size: .85em; font-family: ui-monospace, monospace; }
.cmd-link.telegram::before { content: "→ "; }
.cmd-copy::before { content: "⌘ "; }
.cmd-copy { color: var(--muted); border-color: var(--muted); cursor: text; }
"""
