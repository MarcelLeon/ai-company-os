"""Bounded readers for project documents used by local project summaries."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from aico.core.models import FrozenModel
from aico.core.project_assignment import ProjectProfile


class ProjectDocumentSnippet(FrozenModel):
    label: str = Field(min_length=1)
    path: str = Field(min_length=1)
    lines: tuple[str, ...] = ()


def brief_document_snippets(project: ProjectProfile) -> tuple[ProjectDocumentSnippet, ...]:
    return tuple(
        snippet
        for snippet in (
            _read_snippet(project, "north_star", project.north_star, tail=False),
            _read_snippet(project, "status", project.status_doc, tail=False),
            _read_snippet(project, "journal", project.journal, tail=True),
        )
        if snippet is not None
    )


def risk_document_snippets(project: ProjectProfile) -> tuple[ProjectDocumentSnippet, ...]:
    return tuple(
        snippet
        for snippet in (
            _read_snippet(project, "blockers", project.blockers_doc, tail=True),
            _read_snippet(project, "pitfalls", project.pitfalls_doc, tail=True),
        )
        if snippet is not None
    )


def blocker_document_snippets(project: ProjectProfile) -> tuple[ProjectDocumentSnippet, ...]:
    snippet = _read_snippet(project, "blockers", project.blockers_doc, tail=True)
    return () if snippet is None else (snippet,)


def _read_snippet(
    project: ProjectProfile,
    label: str,
    configured_path: str | None,
    *,
    tail: bool,
) -> ProjectDocumentSnippet | None:
    if configured_path is None:
        return None
    path = _project_path(project.repo, configured_path)
    if path is None or not path.is_file():
        return None
    lines = _interesting_lines(path, tail=tail)
    if not lines:
        return None
    return ProjectDocumentSnippet(label=label, path=configured_path, lines=lines)


def _project_path(repo: str, configured_path: str) -> Path | None:
    repo_path = Path(repo).expanduser()
    path = Path(configured_path).expanduser()
    if not path.is_absolute():
        path = repo_path / path
    try:
        resolved = path.resolve()
    except OSError:
        return None
    return resolved


def _interesting_lines(path: Path, *, tail: bool) -> tuple[str, ...]:
    try:
        raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ()
    cleaned = tuple(_clean_line(line) for line in raw_lines)
    interesting = tuple(line for line in cleaned if line)
    selected = interesting[-4:] if tail else interesting[:4]
    return tuple(_trim_line(line) for line in selected)


def _clean_line(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped in {"---", "```"}:
        return ""
    return stripped


def _trim_line(line: str, *, limit: int = 140) -> str:
    if len(line) <= limit:
        return line
    return f"{line[: limit - 3]}..."
