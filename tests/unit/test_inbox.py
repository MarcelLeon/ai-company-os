"""Boss-facing inbox summaries."""

from __future__ import annotations

from datetime import UTC, datetime

from aico.core.inbox import inbox_message
from aico.core.memory import (
    ExperienceMeta,
    MemoryAtom,
    MemoryEvidence,
    MemoryKind,
    MemoryScope,
    MemoryStatus,
)
from aico.core.models import MetadataEntry, TaskSnapshot, TaskStatus
from aico.core.standing_proposal import StandingProposal, StandingProposalStatus
from aico.core.unified_event import UnifiedEvent, UnifiedEventSource


def test_inbox_message_collapses_empty_state_for_boss() -> None:
    message = inbox_message(
        project_id="data-agent-v1",
        task_snapshots=(),
        recent_events=(
            UnifiedEvent(
                event_id="event-1",
                trace_id="task-1",
                source=UnifiedEventSource.AUDIT,
                short_id="task-1",
                kind="task_completed",
                timestamp=datetime(2026, 7, 3, 9, 30, tzinfo=UTC),
                summary="task_completed",
            ),
        ),
    )

    assert "当前无待处理事项" in message.text
    assert "Needs attention" not in message.text
    assert "Running" not in message.text
    assert "task_completed" not in message.text


def test_inbox_message_prioritizes_one_boss_action() -> None:
    message = inbox_message(
        project_id="data-agent-v1",
        task_snapshots=(
            TaskSnapshot(
                task_id="abcdef12-0000-0000-0000-000000000000",
                target_persona="lead",
                adapter_name="claude-code",
                status=TaskStatus.RUNNING,
                metadata=(MetadataEntry(key="aico.project_id", value="data-agent-v1"),),
                created_at=datetime(2026, 7, 3, 9, 0, tzinfo=UTC),
                updated_at=datetime(2026, 7, 3, 9, 5, tzinfo=UTC),
            ),
        ),
    )

    assert "下一步" in message.text
    assert "/task abcdef12" in message.text
    assert "/interrupt abcdef12" in message.text
    assert "Recent activity" not in message.text


def test_inbox_message_surfaces_candidate_experience_review() -> None:
    candidate = MemoryAtom(
        memory_id="dream-data-agent-001",
        claim="1 task(s) are blocked on approval; ask the boss before writing docs.",
        evidence=(MemoryEvidence(ref="task:approval-1", source="dream_review"),),
        scope=MemoryScope.project("data-agent-v1"),
        source="dream_review",
        confidence=0.6,
        created_by="lead-agent",
        status=MemoryStatus.CANDIDATE,
        kind=MemoryKind.EXPERIENCE,
        experience=ExperienceMeta(applies_to=("implementer",)),
    )

    message = inbox_message(
        project_id="data-agent-v1",
        task_snapshots=(),
        experience_candidates=(candidate,),
    )

    assert "当前无待处理事项" not in message.text
    assert "下一步:\n• review experience dream-data-agent-001 -> /experience review" in message.text
    assert "经验候选:" in message.text
    assert "dream-data-agent-001" in message.text
    assert "ask the boss before writing docs" in message.text
    assert "/experience promote dream-data-agent-001 as <role>" in message.text
    assert "/experience archive dream-data-agent-001" in message.text


def test_inbox_message_surfaces_standing_proposal_after_existing_work() -> None:
    proposal = StandingProposal(
        proposal_id="prop-12345678",
        project_id="aico",
        charter_id="absence-loop",
        role="lead",
        objective="Inspect the absence loop and propose one bounded repair.",
        acceptance_evidence=("one verified contract",),
        stop_conditions=("stop before external sending",),
        cooldown_hours=168,
        status=StandingProposalStatus.CANDIDATE,
    )

    message = inbox_message(
        project_id="aico",
        task_snapshots=(),
        standing_proposals=(proposal,),
    )

    assert "下一步:\n• decide proposal prop-123" in message.text
    assert "主动提案:" in message.text
    assert "/proposal accept prop-123" in message.text
    assert "/proposal reject prop-123" in message.text
