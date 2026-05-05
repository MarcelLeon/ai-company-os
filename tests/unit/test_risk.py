from aico.core import MetadataEntry, RiskLevel, Task, TextRiskAssessor
from aico.core.role_proposal import ROLE_PROPOSAL_INTENT, ROLE_PROPOSAL_INTENT_KEY


def test_text_risk_assessor_keeps_read_only_tasks_unblocked() -> None:
    task = Task(
        task_id="task-1",
        payload="summarize this repo in one sentence",
        requester_id="user-1",
        target_persona="reviewer",
    )

    risk = TextRiskAssessor().assess(task)

    assert risk.risk_level is RiskLevel.READ_ONLY
    assert risk.requires_approval is False


def test_text_risk_assessor_requires_approval_for_write_tasks() -> None:
    task = Task(
        task_id="task-1",
        payload="modify src/aico/core/task_bus.py",
        requester_id="user-1",
        target_persona="implementer",
    )

    risk = TextRiskAssessor().assess(task)

    assert risk.risk_level is RiskLevel.WRITE_FILES
    assert risk.requires_approval is True


def test_text_risk_assessor_escalates_shell_and_destructive_tasks() -> None:
    shell_task = Task(
        task_id="task-1",
        payload="run pytest",
        requester_id="user-1",
        target_persona="implementer",
    )
    destructive_task = Task(
        task_id="task-2",
        payload="rm -rf generated output",
        requester_id="user-1",
        target_persona="implementer",
    )

    assert TextRiskAssessor().assess(shell_task).risk_level is RiskLevel.SHELL_EXEC
    assert TextRiskAssessor().assess(destructive_task).risk_level is RiskLevel.DESTRUCTIVE


def test_text_risk_assessor_keeps_all_matching_reasons() -> None:
    task = Task(
        task_id="task-1",
        payload="modify code then run pytest",
        requester_id="user-1",
        target_persona="implementer",
    )

    risk = TextRiskAssessor().assess(task)

    assert risk.risk_level is RiskLevel.SHELL_EXEC
    assert risk.reasons == (
        "mentions file or code changes",
        "mentions shell or command execution",
    )


def test_text_risk_assessor_treats_internal_role_proposals_as_read_only() -> None:
    task = Task(
        task_id="task-1",
        payload="Draft a role that can run pytest and write docs",
        requester_id="user-1",
        target_persona="implementer",
        metadata=(MetadataEntry(key=ROLE_PROPOSAL_INTENT_KEY, value=ROLE_PROPOSAL_INTENT),),
    )

    risk = TextRiskAssessor().assess(task)

    assert risk.risk_level is RiskLevel.READ_ONLY
    assert risk.requires_approval is False
