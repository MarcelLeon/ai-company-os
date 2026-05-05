from pathlib import Path

from aico.core import ProjectProfile
from aico.core.project_docs import (
    blocker_document_snippets,
    brief_document_snippets,
    risk_document_snippets,
)


def test_project_document_snippets_read_bounded_lines(tmp_path: Path) -> None:
    (tmp_path / "NORTH_STAR.md").write_text(
        "# North\n\nbusiness value\ntechnical principle\nops principle\nextra\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs" / "journal"
    docs.mkdir(parents=True)
    (docs / "PITFALLS.md").write_text(
        "# Pitfalls\n\nold\nnew risk\nlast line\n",
        encoding="utf-8",
    )
    project = ProjectProfile(
        id="demo",
        name="Demo",
        repo=str(tmp_path),
        north_star="NORTH_STAR.md",
        pitfalls_doc="docs/journal/PITFALLS.md",
    )

    brief = brief_document_snippets(project)
    risks = risk_document_snippets(project)
    blockers = blocker_document_snippets(project)

    assert len(brief) == 1
    assert brief[0].label == "north_star"
    assert brief[0].lines == ("# North", "business value", "technical principle", "ops principle")
    assert len(risks) == 1
    assert risks[0].label == "pitfalls"
    assert risks[0].lines == ("# Pitfalls", "old", "new risk", "last line")
    assert blockers == ()


def test_project_document_snippets_skip_missing_files(tmp_path: Path) -> None:
    project = ProjectProfile(
        id="demo",
        name="Demo",
        repo=str(tmp_path),
        north_star="missing.md",
    )

    assert brief_document_snippets(project) == ()
