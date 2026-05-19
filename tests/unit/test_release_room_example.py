from __future__ import annotations

import json
from pathlib import Path

from aico.core import ProjectAssignmentConfig, ProjectAssignmentDirectory


def test_release_room_project_config_loads_and_points_to_demo_repo() -> None:
    config_path = Path("examples/release-room/aico-project.json")
    config = ProjectAssignmentConfig.model_validate(
        json.loads(config_path.read_text(encoding="utf-8"))
    )
    directory = ProjectAssignmentDirectory(config)

    project = directory.project("release-room")
    team = directory.appointments("release-room")
    default_assignment = directory.default_assignment("release-room")

    assert project is not None
    assert project.name == "Notes CLI Release Room"
    assert project.repo == "examples/release-room/notes-cli"
    assert default_assignment is not None
    assert default_assignment.role == "pm"
    assert {appointment.role for appointment in team} == {
        "pm",
        "implementer",
        "tester",
        "reviewer",
        "release-manager",
    }


def test_release_room_demo_repo_contains_project_office_docs() -> None:
    repo = Path("examples/release-room/notes-cli")

    required_paths = (
        "NORTH_STAR.md",
        "STATUS.md",
        "README.md",
        "CHANGELOG.md",
        "issues/003-v02-release.md",
        "docs/journal/ROUNDS.md",
        "docs/journal/BLOCKERS.md",
        "docs/journal/PITFALLS.md",
        "docs/release-notes/v0.2.md",
        "tests/test_notes_cli.py",
        "tests/test_v02_contract.py",
    )

    missing = [path for path in required_paths if not (repo / path).exists()]
    assert missing == []
