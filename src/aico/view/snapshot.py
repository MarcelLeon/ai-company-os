"""Generate self-contained aico-view HTML snapshots for IM delivery."""

from __future__ import annotations

from datetime import datetime
from html import escape

from aico.core.command_messages import short_id_text
from aico.core.memory import MemoryAtom, MemoryKind
from aico.core.models import utc_now
from aico.core.unified_event import UnifiedEvent
from aico.view.app import _VIEW_CSS, ViewSettings, _build_index, _load_memory_atoms
from aico.view.deep_link import DeepLinkSettings, render_command_links


def render_view_snapshot_html(
    settings: ViewSettings,
    deep_link: DeepLinkSettings,
    *,
    project_id: str,
    generated_at: datetime | None = None,
) -> str:
    """Render a single self-contained HTML file; no localhost links or external CSS."""
    generated_at = generated_at or utc_now()
    index = _build_index(settings)
    recent = index.recent(limit=50)
    atoms = _load_memory_atoms(settings)
    sections = (
        _render_brief(project_id, generated_at, recent, atoms, deep_link),
        _render_recent_events(recent),
        _render_trace_details(index_events=recent),
        _render_memory_snapshot(atoms, deep_link),
    )
    return _snapshot_layout(project_id, "".join(sections))


def _snapshot_layout(project_id: str, body: str) -> str:
    title = f"AICO view snapshot — {project_id}"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <style>{_VIEW_CSS}{_SNAPSHOT_CSS}</style>
</head>
<body>
<header><span class="home">AICO view</span><span class="sep">·</span>{escape(project_id)}</header>
<main>{body}</main>
<footer>read-only snapshot · no inbound server required · write through IM</footer>
</body>
</html>"""


def _render_brief(
    project_id: str,
    generated_at: datetime,
    recent: tuple[UnifiedEvent, ...],
    atoms: tuple[MemoryAtom, ...],
    deep_link: DeepLinkSettings,
) -> str:
    active_experiences = sum(1 for atom in atoms if atom.kind is MemoryKind.EXPERIENCE)
    facts = sum(1 for atom in atoms if atom.kind is MemoryKind.FACT)
    latest = recent[-1].summary if recent else "No events yet."
    links = render_command_links(
        deep_link,
        (("/inbox", "/inbox"), ("/morning", "/morning"), ("/undo", "/undo")),
    )
    return (
        "<section class='snapshot-brief'>"
        f"<h1>{escape(project_id)} boss brief</h1>"
        f"<p class='meta'>generated: {escape(generated_at.strftime('%Y-%m-%d %H:%M:%SZ'))}</p>"
        "<div class='brief-grid'>"
        f"<div><b>{len(recent)}</b><span>recent events</span></div>"
        f"<div><b>{active_experiences}</b><span>experiences</span></div>"
        f"<div><b>{facts}</b><span>facts</span></div>"
        "</div>"
        f"<p class='latest'><b>Latest:</b> {escape(latest)}</p>"
        f"{links}</section>"
    )


def _render_recent_events(events: tuple[UnifiedEvent, ...]) -> str:
    if not events:
        return "<section><h2>recent timeline</h2><p class='empty'>No events yet.</p></section>"
    rows = [_event_row(event) for event in reversed(events)]
    return (
        "<section><h2>recent timeline</h2><ul class='timeline'>" + "".join(rows) + "</ul></section>"
    )


def _render_trace_details(*, index_events: tuple[UnifiedEvent, ...]) -> str:
    traces: dict[str, list[UnifiedEvent]] = {}
    for event in index_events:
        traces.setdefault(event.trace_id, []).append(event)
    if not traces:
        return "<section><h2>trace details</h2><p class='empty'>No trace yet.</p></section>"
    blocks: list[str] = []
    for trace_id, events in reversed(tuple(traces.items())):
        short = short_id_text(trace_id)
        rows = "".join(_event_row(event) for event in events)
        blocks.append(
            f"<details><summary>trace {escape(short)} · {len(events)} events</summary>"
            f"<ul class='trace'>{rows}</ul></details>"
        )
    return "<section><h2>trace details</h2>" + "".join(blocks) + "</section>"


def _render_memory_snapshot(
    atoms: tuple[MemoryAtom, ...],
    deep_link: DeepLinkSettings,
) -> str:
    if not atoms:
        return "<section><h2>memory</h2><p class='empty'>No memory recorded.</p></section>"
    experiences = [atom for atom in atoms if atom.kind is MemoryKind.EXPERIENCE]
    facts = [atom for atom in atoms if atom.kind is MemoryKind.FACT]
    return (
        "<section><h2>memory</h2>"
        "<h3>experiences</h3>"
        f"{_atom_rows(experiences, deep_link)}"
        "<h3>facts</h3>"
        f"{_atom_rows(facts, deep_link)}</section>"
    )


def _atom_rows(atoms: list[MemoryAtom], deep_link: DeepLinkSettings) -> str:
    if not atoms:
        return "<p class='empty'>none</p>"
    rows: list[str] = []
    for atom in atoms:
        commands = _atom_commands(atom)
        actions = render_command_links(deep_link, commands) if commands else ""
        rows.append(
            f"<li class='atom {escape(atom.status.value)}'>"
            f"<span class='id'>{escape(short_id_text(atom.memory_id))}</span>"
            f"<span class='status'>{escape(atom.status.value)}</span>"
            f"<span class='confidence'>conf: {atom.confidence:.2f}</span>"
            f"<div class='claim'>{escape(atom.claim)}</div>{actions}</li>"
        )
    return "<ul class='memory'>" + "".join(rows) + "</ul>"


def _atom_commands(atom: MemoryAtom) -> tuple[tuple[str, str | None], ...]:
    if atom.kind is MemoryKind.EXPERIENCE and atom.status.value == "candidate":
        return ((f"/experience promote {atom.memory_id}", "promote"),)
    if atom.kind is MemoryKind.EXPERIENCE and atom.status.value == "active":
        return ((f"/experience archive {atom.memory_id}", "archive"),)
    if atom.kind is MemoryKind.FACT and atom.status.value == "active":
        return ((f"/forget {atom.memory_id}", "forget"),)
    return ()


def _event_row(event: UnifiedEvent) -> str:
    ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"<li><time>{escape(ts)}</time>"
        f"<span class='src {escape(event.source.value)}'>{escape(event.source.value)}</span>"
        f"<span class='kind'>{escape(event.kind)}</span>"
        f"<span class='id'>{escape(event.short_id)}</span>"
        f"<span class='summary'>{escape(event.summary)}</span></li>"
    )


_SNAPSHOT_CSS = """
h1 { margin: .5rem 0 .25rem; font-size: 1.25rem; }
h3 { margin: .9rem 0 .35rem; color: var(--muted); font-size: .9rem; }
section { margin-bottom: 1.1rem; }
.snapshot-brief { padding: .75rem; background: var(--card); border-radius: 6px; }
.snapshot-brief .meta { color: var(--muted); margin: 0 0 .7rem; }
.brief-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: .4rem; }
.brief-grid div { background: #0f1528; border-radius: 6px; padding: .55rem; }
.brief-grid b { display: block; color: var(--accent); font-size: 1.15rem; }
.brief-grid span { color: var(--muted); font-size: .78rem; }
.latest { margin-bottom: 0; }
details { background: var(--card); border-radius: 6px; margin: .45rem 0; padding: .55rem; }
summary { cursor: pointer; color: var(--accent); }
details ul { margin-top: .5rem; }
"""
