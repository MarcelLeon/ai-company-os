from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aico.core.inbox import inbox_message
from aico.core.models import MetadataEntry, TaskSnapshot, TaskStatus, TaskUsage
from aico.core.morning import morning_message
from aico.core.standing_autonomy import (
    StandingAutonomyOutcomeStatus,
    StandingAutonomyReceiptStatus,
    standing_autonomy_receipts,
)
from aico.core.standing_proposal import (
    SQLiteStandingProposalStore,
    StandingProposal,
    StandingProposalDecisionMode,
    StandingProposalStatus,
)
from aico.core.standing_result import (
    StandingEvidenceStatus,
    StandingResultContractStatus,
    StandingResultReceipt,
    validate_standing_result,
)
from aico.core.task_store import SQLiteTaskStateStore

_DECIDED_AT = datetime(2026, 7, 21, 8, tzinfo=UTC)


@pytest.mark.parametrize(
    "task_status",
    [
        TaskStatus.RUNNING,
        TaskStatus.WAITING_APPROVAL,
        TaskStatus.DONE,
        TaskStatus.FAILED,
        TaskStatus.INTERRUPTED,
        TaskStatus.REJECTED,
    ],
)
def test_standing_autonomy_receipts_project_authoritative_task_status(
    task_status: TaskStatus,
) -> None:
    proposal = _proposal()
    snapshot = _snapshot(task_status)

    receipt = standing_autonomy_receipts((proposal,), (snapshot,))[0]

    assert receipt.status is StandingAutonomyReceiptStatus(task_status.value)
    assert receipt.task_id == snapshot.task_id
    assert receipt.authorization_id == proposal.authorization_id
    assert receipt.total_tokens == 100
    expected_outcome = StandingAutonomyOutcomeStatus.MISSING
    if task_status in {TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL}:
        expected_outcome = StandingAutonomyOutcomeStatus.PENDING
    elif task_status is TaskStatus.DONE:
        expected_outcome = StandingAutonomyOutcomeStatus.COMPLETE
    assert receipt.outcome_status is expected_outcome
    if task_status in {
        TaskStatus.DONE,
        TaskStatus.FAILED,
        TaskStatus.INTERRUPTED,
        TaskStatus.REJECTED,
    }:
        assert receipt.finished_at == snapshot.updated_at
        assert receipt.elapsed_seconds == 30
    else:
        assert receipt.finished_at is None
        assert receipt.elapsed_seconds is None


def test_standing_autonomy_receipts_surface_missing_or_mismatched_evidence() -> None:
    proposal = _proposal()
    missing = standing_autonomy_receipts((proposal,), ())
    mismatched = standing_autonomy_receipts(
        (proposal,),
        (
            _snapshot(
                TaskStatus.DONE,
                grant_id="another-grant-private-value",
            ),
        ),
    )
    manual = proposal.model_copy(
        update={
            "proposal_id": "proposal-manual-private-value",
            "decision_mode": StandingProposalDecisionMode.MANUAL,
            "authorization_id": None,
        }
    )

    assert missing[0].status is StandingAutonomyReceiptStatus.EVIDENCE_MISSING
    assert missing[0].task_id == proposal.task_id
    assert mismatched[0].status is StandingAutonomyReceiptStatus.EVIDENCE_MISSING
    assert standing_autonomy_receipts((manual,), ()) == ()

    missing_usage = proposal.model_copy(update={"usage": None, "usage_recorded_at": None})
    usage_receipt = standing_autonomy_receipts((missing_usage,), (_snapshot(TaskStatus.DONE),))[0]
    assert usage_receipt.status is StandingAutonomyReceiptStatus.EVIDENCE_MISSING


def test_invalid_result_remains_invalid_when_source_manifest_is_absent(tmp_path: Path) -> None:
    invalid_result = _proposal().result_receipt.model_copy(  # type: ignore[union-attr]
        update={"status": StandingResultContractStatus.INVALID}
    )
    proposal = _proposal().model_copy(update={"result_receipt": invalid_result})

    receipt = standing_autonomy_receipts(
        (proposal,),
        (_snapshot(TaskStatus.DONE),),
        evidence_root=tmp_path,
    )[0]

    assert receipt.outcome_status is StandingAutonomyOutcomeStatus.INVALID
    assert receipt.evidence_status is None


def test_standing_autonomy_receipt_rebuilds_from_existing_sqlite_truth(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.db"
    proposal = _proposal()
    snapshot = _snapshot(TaskStatus.DONE)
    SQLiteStandingProposalStore(state_path).upsert(proposal)
    SQLiteTaskStateStore(state_path).upsert_task_snapshot(snapshot)

    restarted_proposals = SQLiteStandingProposalStore(state_path).list_project("aico")
    restarted_snapshots = SQLiteTaskStateStore(state_path).load_task_snapshots()

    assert standing_autonomy_receipts(restarted_proposals, restarted_snapshots) == (
        standing_autonomy_receipts((proposal,), (snapshot,))[0],
    )


def test_standing_autonomy_receipt_surfaces_source_drift_without_leaking_path(
    tmp_path: Path,
) -> None:
    source = tmp_path / "private-evidence.md"
    source.write_text("evidence\n", encoding="utf-8")
    result = validate_standing_result(
        json.dumps(
            {
                "version": 1,
                "result": "complete",
                "summary": "complete",
                "criteria": [
                    {
                        "criterion_id": "A1",
                        "verdict": "met",
                        "evidence": "present",
                        "sources": [{"path": source.name, "line": 1}],
                    }
                ],
                "stop_conditions": [{"stop_id": "S1", "observed": True}],
                "gaps": [],
                "risks": [],
                "next_actions": ["wait"],
            }
        ),
        acceptance_evidence=("one bounded report",),
        stop_conditions=("stop before external communication",),
        evidence_root=tmp_path,
        clock=lambda: _DECIDED_AT,
    )
    proposal = _proposal().model_copy(update={"result_receipt": result})
    store = SQLiteStandingProposalStore(tmp_path / "state.db")
    store.upsert(proposal)
    proposal = store.list_project("aico")[0]

    current = standing_autonomy_receipts(
        (proposal,),
        (_snapshot(TaskStatus.DONE),),
        evidence_root=tmp_path,
    )[0]
    source.write_text("changed\n", encoding="utf-8")
    drifted = standing_autonomy_receipts(
        (proposal,),
        (_snapshot(TaskStatus.DONE),),
        evidence_root=tmp_path,
    )[0]
    message = inbox_message(
        project_id="aico",
        task_snapshots=(),
        standing_autonomy_receipts=(drifted,),
    )

    assert current.evidence_status is StandingEvidenceStatus.CURRENT
    assert current.outcome_status is StandingAutonomyOutcomeStatus.COMPLETE
    assert drifted.evidence_status is StandingEvidenceStatus.DRIFTED
    assert drifted.outcome_status is StandingAutonomyOutcomeStatus.DRIFTED
    assert "evidence=drifted" in message.text
    assert source.name not in message.text


def test_standing_autonomy_receipts_bound_evidence_revalidation_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def current_evidence(result: object, root: object) -> StandingEvidenceStatus:
        nonlocal calls
        _ = (result, root)
        calls += 1
        return StandingEvidenceStatus.CURRENT

    monkeypatch.setattr(
        "aico.core.standing_autonomy.standing_result_evidence_status",
        current_evidence,
    )
    proposals: list[StandingProposal] = []
    snapshots: list[TaskSnapshot] = []
    for index in range(7):
        proposal_id = f"proposal-{index}"
        task_id = f"task-{index}"
        proposals.append(
            _proposal().model_copy(
                update={
                    "proposal_id": proposal_id,
                    "task_id": task_id,
                    "decided_at": _DECIDED_AT + timedelta(minutes=index),
                }
            )
        )
        snapshots.append(
            _snapshot(TaskStatus.DONE).model_copy(
                update={
                    "task_id": task_id,
                    "metadata": (
                        MetadataEntry(key="aico.standing_proposal_id", value=proposal_id),
                        MetadataEntry(
                            key="aico.preauthorized_grant_id",
                            value="authorization-grant-private-value",
                        ),
                    ),
                }
            )
        )

    receipts = standing_autonomy_receipts(
        tuple(proposals),
        tuple(snapshots),
        evidence_root=tmp_path,
    )

    assert calls == 5
    assert [receipt.evidence_status for receipt in receipts[:2]] == [None, None]
    assert all(
        receipt.evidence_status is StandingEvidenceStatus.CURRENT for receipt in receipts[2:]
    )


def test_boss_views_render_receipts_without_leaking_full_identity_or_output() -> None:
    done = standing_autonomy_receipts((_proposal(),), (_snapshot(TaskStatus.DONE),))[0]
    missing = standing_autonomy_receipts(
        (
            _proposal().model_copy(
                update={
                    "proposal_id": "proposal-missing-private-value",
                    "task_id": None,
                }
            ),
        ),
        (),
    )[0]

    inbox = inbox_message(
        project_id="aico",
        task_snapshots=(),
        standing_autonomy_receipts=(done,),
    )
    missing_inbox = inbox_message(
        project_id="aico",
        task_snapshots=(),
        standing_autonomy_receipts=(missing,),
    )
    morning = morning_message(
        project_id="aico",
        task_snapshots=(),
        standing_autonomy_receipts=(done, missing),
    )

    assert "当前无待处理事项" in inbox.text
    assert "自治回执:" in inbox.text
    assert "[done]" in inbox.text
    assert "tokens=100" in inbox.text
    assert "outcome=complete criteria=1/1 sources=1" in inbox.text
    assert "下一步:\n• inspect autonomy proposal -> /proposals" in missing_inbox.text
    assert "Standing autonomy receipts:" in morning.text
    assert morning.text.index("Blocked:") < morning.text.index("Standing autonomy receipts:")
    rendered = "\n".join((inbox.text, missing_inbox.text, morning.text))
    assert "authorization-grant-private-value" not in rendered
    assert "owner-private-value" not in rendered
    assert "target-private-value" not in rendered
    assert "provider private output" not in rendered


def _proposal() -> StandingProposal:
    return StandingProposal(
        proposal_id="proposal-autonomy-private-value",
        project_id="aico",
        charter_id="absence-loop",
        role="reviewer",
        objective="Inspect bounded recovery evidence.",
        acceptance_evidence=("one bounded report",),
        stop_conditions=("stop before external communication",),
        cooldown_hours=168,
        status=StandingProposalStatus.ACCEPTED,
        task_id="task-autonomy-private-value",
        decision_mode=StandingProposalDecisionMode.PREAUTHORIZED,
        authorization_id="authorization-grant-private-value",
        usage=TaskUsage(input_tokens=80, output_tokens=20, total_tokens=100),
        usage_recorded_at=_DECIDED_AT + timedelta(seconds=30),
        result_receipt=StandingResultReceipt(
            status=StandingResultContractStatus.COMPLETE,
            criteria_met=1,
            criteria_total=1,
            verified_sources=1,
            checked_at=_DECIDED_AT + timedelta(seconds=30),
        ),
        created_at=_DECIDED_AT - timedelta(minutes=1),
        decided_at=_DECIDED_AT,
    )


def _snapshot(
    status: TaskStatus,
    *,
    grant_id: str = "authorization-grant-private-value",
) -> TaskSnapshot:
    return TaskSnapshot(
        task_id="task-autonomy-private-value",
        target_persona="reviewer",
        adapter_name="codex",
        status=status,
        metadata=(
            MetadataEntry(
                key="aico.standing_proposal_id",
                value="proposal-autonomy-private-value",
            ),
            MetadataEntry(key="aico.preauthorized_grant_id", value=grant_id),
        ),
        created_at=_DECIDED_AT,
        updated_at=_DECIDED_AT + timedelta(seconds=30),
    )
