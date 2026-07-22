from __future__ import annotations

import json
from pathlib import Path

from aico.core import ProjectAssignmentConfig, ProjectAssignmentDirectory


def test_data_agent_project_config_loads_with_benchmark_team() -> None:
    config_path = Path("projects/data-agent-v1/aico-project.json")
    config = ProjectAssignmentConfig.model_validate(
        json.loads(config_path.read_text(encoding="utf-8"))
    )
    directory = ProjectAssignmentDirectory(config)

    project = directory.project("data-agent-v1")

    assert project is not None
    assert project.repo == "projects/data-agent-v1"
    assert directory.default_assignment("data-agent-v1") is not None
    assert {item.role for item in directory.appointments("data-agent-v1")} == {
        "lead",
        "architect",
        "implementer",
        "tester",
        "reviewer",
        "challenger",
    }
    assert directory.missing_required_team_roles("data-agent-v1") == ()


def test_data_agent_project_contains_baseline_artifacts() -> None:
    root = Path("projects/data-agent-v1")
    required_paths = (
        "AGENTS.md",
        "NORTH_STAR.md",
        "STATUS.md",
        "README.md",
        "docs/goals/baseline-v1.md",
        "docs/handoffs/current.md",
        "docs/journal/ROUNDS.md",
        "docs/journal/PITFALLS.md",
        "docs/journal/BLOCKERS.md",
        "docs/evidence/baseline-v1.md",
        "evals/golden_questions.json",
        "tests/unit/test_engine.py",
    )

    assert [path for path in required_paths if not (root / path).exists()] == []
