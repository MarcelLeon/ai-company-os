"""Generate self-contained aico-view HTML snapshots for IM delivery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape

from aico.core.command_messages import short_id_text, task_error_summary
from aico.core.memory import MemoryAtom, MemoryKind
from aico.core.models import AuditEvent, MetadataEntry, Task, TaskSnapshot, utc_now
from aico.core.offline_delegation import (
    OfflineDelegationRecord,
    SQLiteOfflineDelegationStore,
)
from aico.core.task_store import SQLiteTaskStateStore
from aico.core.unified_event import InMemoryUnifiedEventIndex, UnifiedEvent
from aico.view.app import (
    _VIEW_CSS,
    ViewSettings,
    _load_audit_events,
    _load_memory_atoms,
)
from aico.view.deep_link import DeepLinkSettings, render_command_links


@dataclass(frozen=True)
class SnapshotTaskBrief:
    task_id: str
    short_id: str
    target_persona: str
    adapter_name: str
    status: str
    description: str
    reason: str | None
    risk_level: str
    intent: str
    updated_at: datetime


@dataclass(frozen=True)
class SnapshotProjectTasks:
    briefs: tuple[SnapshotTaskBrief, ...]
    snapshots: tuple[TaskSnapshot, ...]


def render_view_snapshot_html(
    settings: ViewSettings,
    deep_link: DeepLinkSettings,
    *,
    project_id: str,
    generated_at: datetime | None = None,
) -> str:
    """Render a single self-contained HTML file; no localhost links or external CSS."""
    generated_at = generated_at or utc_now()
    project_tasks = _load_project_tasks(settings, project_id)
    atoms = _project_memory_atoms(settings, project_id)
    audit_events = _project_audit_events(settings, project_tasks.briefs)
    index = InMemoryUnifiedEventIndex(
        audit_events=audit_events,
        memory_atoms=atoms,
        task_snapshots=project_tasks.snapshots,
    )
    recent = index.recent(limit=50)
    overnight = _load_overnight_records(settings, project_id)
    sections = (
        _render_brief(
            project_id,
            generated_at,
            project_tasks.briefs,
            overnight,
            deep_link,
        ),
        _render_recent_tasks(project_tasks.briefs, deep_link),
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
    tasks: tuple[SnapshotTaskBrief, ...],
    overnight: tuple[OfflineDelegationRecord, ...],
    deep_link: DeepLinkSettings,
) -> str:
    approvals = tuple(task for task in tasks if task.status == "waiting_approval")
    blockers = tuple(task for task in tasks if task.status in {"failed", "interrupted", "rejected"})
    running = tuple(task for task in tasks if task.status == "running")
    return (
        "<section class='snapshot-brief'>"
        f"<h1>{escape(project_id)} boss brief</h1>"
        f"<p class='meta'>generated: {escape(generated_at.strftime('%Y-%m-%d %H:%M:%SZ'))}</p>"
        "<div class='brief-grid'>"
        f"<div><b>{len(approvals)}</b><span>approvals</span></div>"
        f"<div><b>{len(blockers)}</b><span>blockers</span></div>"
        f"<div><b>{len(running)}</b><span>running</span></div>"
        f"<div><b>{len(overnight)}</b><span>overnight</span></div>"
        "</div>"
        f"{_render_first_action(approvals, blockers, running, overnight, deep_link)}"
        "<div class='attention-grid'>"
        f"{_render_attention_tasks('Approval needed', approvals, deep_link, approval=True)}"
        f"{_render_attention_tasks('Blockers', blockers, deep_link)}"
        f"{_render_overnight_results(overnight, tasks, deep_link)}"
        "</div></section>"
    )


def _render_first_action(
    approvals: tuple[SnapshotTaskBrief, ...],
    blockers: tuple[SnapshotTaskBrief, ...],
    running: tuple[SnapshotTaskBrief, ...],
    overnight: tuple[OfflineDelegationRecord, ...],
    deep_link: DeepLinkSettings,
) -> str:
    title: str
    detail: str
    commands: tuple[tuple[str, str | None], ...]
    if approvals:
        task = approvals[0]
        title = f"Decide {task.short_id} before work can continue"
        detail = task.reason or task.description
        commands = _task_commands(task, approval=True)
    elif blockers:
        task = blockers[0]
        title = f"Recover {task.short_id} before starting new work"
        detail = task.reason or task.description
        commands = _task_commands(task)
    elif running:
        task = running[0]
        title = f"Check {task.short_id} before interrupting or adding work"
        detail = task.description
        commands = (
            (f"/task {task.short_id}", f"open /task {task.short_id}"),
            (f"/interrupt {task.short_id}", f"/interrupt {task.short_id}"),
        )
    elif overnight:
        record = overnight[-1]
        task_id = short_id_text(record.task_id)
        title = f"Review overnight handoff {task_id}"
        detail = record.goal
        commands = ((f"/task {task_id}", f"open /task {task_id}"),)
    else:
        title = "No decision is waiting"
        detail = "Open the inbox or morning brief before assigning new work."
        commands = (("/inbox", "/inbox"), ("/morning", "/morning"))
    return (
        "<article class='first-action'><span class='eyebrow'>First action</span>"
        f"<h2>{escape(title)}</h2><p>{escape(task_error_summary(detail))}</p>"
        f"{render_command_links(deep_link, commands)}</article>"
    )


def _render_attention_tasks(
    title: str,
    tasks: tuple[SnapshotTaskBrief, ...],
    deep_link: DeepLinkSettings,
    *,
    approval: bool = False,
) -> str:
    if not tasks:
        body = "<p class='empty'>None waiting.</p>"
    else:
        rows = []
        for task in tasks[:3]:
            detail = task.reason or task.description
            rows.append(
                f"<li><b>{escape(task.short_id)}</b><span>{escape(detail)}</span>"
                f"{render_command_links(deep_link, _task_commands(task, approval=approval))}</li>"
            )
        body = "<ul>" + "".join(rows) + "</ul>"
    return f"<article class='attention'><h2>{escape(title)}</h2>{body}</article>"


def _render_overnight_results(
    records: tuple[OfflineDelegationRecord, ...],
    tasks: tuple[SnapshotTaskBrief, ...],
    deep_link: DeepLinkSettings,
) -> str:
    by_id = {task.task_id: task for task in tasks}
    if not records:
        body = "<p class='empty'>No overnight handoff.</p>"
    else:
        rows = []
        for record in reversed(records[-3:]):
            task = by_id.get(record.task_id)
            status = task.status if task is not None else "unknown"
            reviews = len(record.review_task_ids)
            short_id = short_id_text(record.task_id)
            meta = f"{record.role} · {record.agent} · {status} · {reviews} reviews"
            commands = ((f"/task {short_id}", f"open /task {short_id}"),)
            rows.append(
                f"<li><b>{escape(record.goal)}</b><span>{escape(meta)}</span>"
                f"{render_command_links(deep_link, commands)}</li>"
            )
        body = "<ul>" + "".join(rows) + "</ul>"
    return f"<article class='attention overnight'><h2>Overnight results</h2>{body}</article>"


def _task_commands(
    task: SnapshotTaskBrief,
    *,
    approval: bool = False,
) -> tuple[tuple[str, str | None], ...]:
    commands: list[tuple[str, str | None]] = [
        (f"/task {task.short_id}", f"open /task {task.short_id}")
    ]
    if approval:
        commands[0:0] = [
            (f"/approve {task.short_id}", f"/approve {task.short_id}"),
            (f"/reject {task.short_id}", f"/reject {task.short_id}"),
        ]
    return tuple(commands)


def _render_recent_events(events: tuple[UnifiedEvent, ...]) -> str:
    if not events:
        return "<section><h2>recent timeline</h2><p class='empty'>No events yet.</p></section>"
    rows = [_event_row(event) for event in reversed(events)]
    return (
        "<section><h2>recent timeline</h2><ul class='timeline'>" + "".join(rows) + "</ul></section>"
    )


def _render_recent_tasks(
    tasks: tuple[SnapshotTaskBrief, ...],
    deep_link: DeepLinkSettings,
) -> str:
    if not tasks:
        return "<section><h2>recent tasks</h2><p class='empty'>No task records yet.</p></section>"
    rows: list[str] = []
    for task in tasks[:12]:
        commands = ((f"/task {task.short_id}", f"open /task {task.short_id}"),)
        actions = render_command_links(deep_link, commands)
        updated = task.updated_at.strftime("%Y-%m-%d %H:%M:%SZ")
        rows.append(
            f"<li class='task-brief {escape(task.status)}'>"
            f"<span class='id'>{escape(task.short_id)}</span>"
            f"<span class='task-meta'>{escape(task.target_persona)} · "
            f"{escape(task.adapter_name)} · {escape(task.status)}</span>"
            f"<time>{escape(updated)}</time>"
            f"<div class='task-desc'>{escape(task.description)}</div>"
            f"{actions}</li>"
        )
    return "<section><h2>recent tasks</h2><ul class='tasks'>" + "".join(rows) + "</ul></section>"


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
        f"<span class='summary'>{escape(task_error_summary(event.summary))}</span></li>"
    )


def _load_project_tasks(settings: ViewSettings, project_id: str) -> SnapshotProjectTasks:
    if settings.state_db_path is None or not settings.state_db_path.exists():
        return SnapshotProjectTasks(briefs=(), snapshots=())
    store = SQLiteTaskStateStore(settings.state_db_path)
    records = {task.task_id: task for task in store.load_task_records()}
    snapshots = sorted(
        (
            snapshot
            for snapshot in store.load_task_snapshots()
            if _task_project_id(snapshot, records.get(snapshot.task_id)) == project_id
        ),
        key=lambda snapshot: snapshot.updated_at,
        reverse=True,
    )
    return SnapshotProjectTasks(
        briefs=tuple(
            _task_brief(snapshot, records.get(snapshot.task_id)) for snapshot in snapshots
        ),
        snapshots=tuple(snapshots),
    )


def _task_brief(snapshot: TaskSnapshot, task: Task | None) -> SnapshotTaskBrief:
    metadata = _metadata_dict(snapshot.metadata)
    if task is not None:
        metadata = {**metadata, **_metadata_dict(task.metadata)}
    return SnapshotTaskBrief(
        task_id=snapshot.task_id,
        short_id=short_id_text(snapshot.task_id),
        target_persona=snapshot.target_persona,
        adapter_name=snapshot.adapter_name or "adapter?",
        status=snapshot.status.value,
        description=_task_description(snapshot, task),
        reason=task_error_summary(snapshot.reason) if snapshot.reason else None,
        risk_level=snapshot.risk_level.value,
        intent=str(metadata.get("aico.intent", "project_task")),
        updated_at=snapshot.updated_at,
    )


def _task_project_id(snapshot: TaskSnapshot, task: Task | None) -> str | None:
    if task is not None:
        project_id = _metadata_dict(task.metadata).get("aico.project_id")
        if project_id:
            return str(project_id)
    project_id = _metadata_dict(snapshot.metadata).get("aico.project_id")
    return str(project_id) if project_id else None


def _project_memory_atoms(settings: ViewSettings, project_id: str) -> tuple[MemoryAtom, ...]:
    return tuple(
        atom for atom in _load_memory_atoms(settings) if atom.scope.project_id == project_id
    )


def _project_audit_events(
    settings: ViewSettings,
    tasks: tuple[SnapshotTaskBrief, ...],
) -> tuple[AuditEvent, ...]:
    task_ids = {task.task_id for task in tasks}
    return tuple(event for event in _load_audit_events(settings) if event.task_id in task_ids)


def _load_overnight_records(
    settings: ViewSettings,
    project_id: str,
) -> tuple[OfflineDelegationRecord, ...]:
    if settings.state_db_path is None or not settings.state_db_path.exists():
        return ()
    store = SQLiteOfflineDelegationStore(settings.state_db_path)
    return store.load_project_records(project_id)


def _task_description(snapshot: TaskSnapshot, task: Task | None) -> str:
    if task is not None:
        metadata = _metadata_dict(task.metadata)
        if objective := metadata.get("aico.goal_objective"):
            return _compact_text(str(objective))
        if current_task := _current_task_from_payload(task.payload):
            return _compact_text(current_task)
        return _compact_text(task.payload)
    metadata = _metadata_dict(snapshot.metadata)
    if objective := metadata.get("aico.goal_objective"):
        return _compact_text(str(objective))
    if snapshot.reason:
        return _compact_text(task_error_summary(snapshot.reason))
    return "No task description recorded. Use /task for raw trace."


def _metadata_dict(metadata: tuple[MetadataEntry, ...]) -> dict[str, object]:
    return {entry.key: entry.value for entry in metadata}


def _current_task_from_payload(payload: str) -> str | None:
    _, separator, current_task = payload.rpartition("Current task:")
    if not separator:
        return None
    return current_task.strip() or None


def _compact_text(text: str, *, limit: int = 220) -> str:
    compact = " ".join(part.strip() for part in text.splitlines() if part.strip())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


_SNAPSHOT_CSS = """
h1 { margin: .5rem 0 .25rem; font-size: 1.25rem; }
h3 { margin: .9rem 0 .35rem; color: var(--muted); font-size: .9rem; }
section { margin-bottom: 1.1rem; }
.snapshot-brief { padding: .75rem; background: var(--card); border-radius: 6px; }
.snapshot-brief .meta { color: var(--muted); margin: 0 0 .7rem; }
.brief-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: .4rem; }
.brief-grid div { background: #0f1528; border-radius: 6px; padding: .55rem; }
.brief-grid b { display: block; color: var(--accent); font-size: 1.15rem; }
.brief-grid span { color: var(--muted); font-size: .78rem; }
.first-action {
  margin-top: .65rem; padding: .85rem; border: 1px solid var(--accent);
  border-radius: 6px; background: #111a31;
}
.first-action .eyebrow {
  color: var(--accent); font-size: .72rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .08em;
}
.first-action h2 { margin: .25rem 0; font-size: 1.05rem; }
.first-action p { margin: .25rem 0 .55rem; }
.attention-grid {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .55rem; margin-top: .65rem;
}
.attention { min-width: 0; padding: .7rem; border-radius: 6px; background: #0f1528; }
.attention h2 { margin: 0 0 .5rem; font-size: .92rem; }
.attention ul { list-style: none; margin: 0; padding: 0; }
.attention li { display: grid; gap: .25rem; padding: .45rem 0; border-top: 1px solid #26304a; }
.attention li:first-child { border-top: 0; padding-top: 0; }
.attention li span { color: var(--muted); font-size: .8rem; overflow-wrap: anywhere; }
.attention .cmd-links { margin: .1rem 0 0; }
details { background: var(--card); border-radius: 6px; margin: .45rem 0; padding: .55rem; }
summary { cursor: pointer; color: var(--accent); }
details ul { margin-top: .5rem; }
.tasks .task-brief { grid-template-columns: auto 1fr; }
.task-brief .task-meta { color: var(--muted); font-size: .85em; }
.task-brief time { grid-column: 1 / -1; }
.task-brief .task-desc { grid-column: 1 / -1; }
.task-brief .cmd-links { grid-column: 1 / -1; margin: .35rem 0 0; }
@media (max-width: 700px) {
  .attention-grid { grid-template-columns: 1fr; }
  .brief-grid { grid-template-columns: repeat(2, 1fr); }
}
"""
