"""ExperienceLayer injection in render_appointment_prompt."""

from __future__ import annotations

from datetime import UTC, datetime

from aico.core import (
    ExperienceMeta,
    MemoryAtom,
    MemoryEvidence,
    MemoryKind,
    MemoryScope,
    MemoryStatus,
    Task,
)
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectProfile,
)
from aico.core.prompt_stack import render_appointment_prompt


def _task() -> Task:
    return Task(
        task_id="task-1",
        payload="Implement adapter retry path.",
        requester_id="boss-1",
        target_persona="claude",
    )


def _project() -> ProjectProfile:
    return ProjectProfile(
        id="aico",
        name="AI Company OS",
        repo="/repo/aico",
    )


def _appointment() -> AssignmentProfile:
    return AssignmentProfile(
        project="aico",
        agent="claude",
        role="implementer",
        seat="aico-implementer",
        permissions=("code", "tests"),
    )


def _active_experience(memory_id: str, *, confidence: float = 0.8) -> MemoryAtom:
    return MemoryAtom(
        memory_id=memory_id,
        claim="Retry adapter with verbose logging after idle timeout.",
        evidence=(MemoryEvidence(ref=f"task:{memory_id}", source="dream_review"),),
        scope=MemoryScope.project("aico"),
        source="dream_review",
        confidence=confidence,
        created_by="lead-agent",
        created_at=datetime(2026, 5, 31, 9, 0, tzinfo=UTC),
        status=MemoryStatus.ACTIVE,
        kind=MemoryKind.EXPERIENCE,
        experience=ExperienceMeta(
            applies_to=("implementer",),
            triggers=("adapter_idle_timeout",),
        ),
    )


def test_render_prompt_omits_experience_section_when_none() -> None:
    rendered = render_appointment_prompt(
        task=_task(),
        agent=None,
        role=None,
        project=_project(),
        project_role=None,
        appointment=_appointment(),
    )
    assert "Reusable experience" not in rendered


def test_render_prompt_includes_experience_section_when_present() -> None:
    rendered = render_appointment_prompt(
        task=_task(),
        agent=None,
        role=None,
        project=_project(),
        project_role=None,
        appointment=_appointment(),
        experiences=(_active_experience("mem-exp-1"),),
    )
    assert "Reusable experience (promoted lessons):" in rendered
    assert "mem-exp-1" in rendered
    assert "confidence: 0.80" in rendered
    assert "triggers: adapter_idle_timeout" in rendered


def test_render_prompt_orders_runtime_section_last() -> None:
    rendered = render_appointment_prompt(
        task=_task(),
        agent=None,
        role=None,
        project=_project(),
        project_role=None,
        appointment=_appointment(),
        experiences=(_active_experience("mem-exp-1"),),
    )
    experience_pos = rendered.index("Reusable experience")
    runtime_pos = rendered.index("Current task:")
    assert experience_pos < runtime_pos
