from __future__ import annotations

import json
from pathlib import Path

from aico.core import ProjectAssignmentConfig, ProjectAssignmentDirectory


def test_sme_agent_project_config_loads_with_durable_team() -> None:
    config_path = Path("projects/sme-agent/aico-project.json")
    config = ProjectAssignmentConfig.model_validate(
        json.loads(config_path.read_text(encoding="utf-8"))
    )
    directory = ProjectAssignmentDirectory(config)

    project = directory.project("sme-agent")

    assert project is not None
    assert project.repo == "projects/sme-agent"
    assert directory.default_assignment("sme-agent") is not None
    assert {item.role for item in directory.appointments("sme-agent")} == {
        "lead",
        "metadata-engineer",
        "knowledge-engineer",
        "runtime-engineer",
        "tester",
        "reviewer",
        "challenger",
    }
    assert directory.missing_required_team_roles("sme-agent") == ()
    charter = project.standing_charter[0]
    reviewer = directory.appointment_for_role("sme-agent", charter.role)
    assert charter.id == "commercial-evidence-loop"
    assert charter.role == "reviewer"
    assert reviewer is not None
    assert reviewer.agent == "codex"
    assert reviewer.risk_policy == "read_only"


def test_sme_agent_project_contains_continuity_artifacts() -> None:
    root = Path("projects/sme-agent")
    required_paths = (
        "AGENTS.md",
        "NORTH_STAR.md",
        "STATUS.md",
        "docs/operating-model/alignment.md",
        "docs/operating-model/aico-runbook.md",
        "docs/goals/phase-1-metadata.md",
        "docs/handoffs/current.md",
        "docs/journal/ROUNDS.md",
        "docs/journal/PITFALLS.md",
        "docs/journal/BLOCKERS.md",
        "docs/decisions/0001-project-boundary-and-modular-monolith.md",
        "docs/architecture/system.md",
        "docs/evidence/round-1.md",
        "tests/unit/test_catalog.py",
    )

    assert [path for path in required_paths if not (root / path).exists()] == []
