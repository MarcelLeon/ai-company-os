from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aico.channel import IncomingMessageHandler
from aico.core import (
    AgentSession,
    AssignmentProfile,
    ChannelTarget,
    CompanyAgentProfile,
    HealthStatus,
    IncomingMessage,
    InMemoryStandingProposalStore,
    MessageContent,
    MetadataEntry,
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
    ProjectProfile,
    ProjectRoleProfile,
    RoleProfile,
    SentMessage,
    SQLiteStandingProposalStore,
    StandingCharterItem,
    StandingProposalCoordinator,
    StandingProposalStatus,
    Task,
    TaskSnapshot,
    TaskStatus,
)
from aico.core.sqlite_state import SQLiteStateDatabase

TaskRunner = Callable[[IncomingMessage, Task, AgentSession | None], Awaitable[str]]


class RecordingChannel:
    def __init__(self) -> None:
        self.sent_messages: list[MessageContent] = []
        self.handler: IncomingMessageHandler | None = None

    @property
    def name(self) -> str:
        return "telegram"

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> SentMessage:
        self.sent_messages.append(content)
        return SentMessage(message_id=f"message-{len(self.sent_messages)}", target=target)

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> None:
        del target, message_id, content

    async def delete_message(self, target: ChannelTarget, message_id: str) -> None:
        del target, message_id

    def on_incoming(self, handler: IncomingMessageHandler) -> None:
        self.handler = handler

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


def test_standing_proposal_refresh_requires_idle_complete_configured_project() -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    store = InMemoryStandingProposalStore()
    coordinator = _coordinator(store=store, clock=lambda: now)

    proposals = coordinator.refresh("aico", ())

    assert len(proposals) == 1
    assert proposals[0].charter_id == "absence-loop"
    assert proposals[0].status is StandingProposalStatus.CANDIDATE
    assert coordinator.refresh("aico", ()) == proposals

    active = TaskSnapshot(
        task_id="task-running",
        target_persona="claude",
        status=TaskStatus.RUNNING,
        metadata=(MetadataEntry(key="aico.project_id", value="aico"),),
    )
    assert coordinator.refresh("aico", (active,)) == proposals

    assert _coordinator(store=InMemoryStandingProposalStore()).refresh("aico", (active,)) == ()
    assert _coordinator(store=InMemoryStandingProposalStore()).refresh("missing", ()) == ()

    complete = _project_directory()
    incomplete_config = complete._config.model_copy(  # noqa: SLF001
        update={
            "assignments": tuple(
                assignment
                for assignment in complete._config.assignments  # noqa: SLF001
                if assignment.role != "challenger"
            )
        }
    )
    incomplete = ProjectAssignmentDirectory(incomplete_config)
    assert (
        _coordinator(
            store=InMemoryStandingProposalStore(),
            directory=incomplete,
        ).refresh("aico", ())
        == ()
    )


def test_standing_proposal_refresh_respects_rejection_cooldown() -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    clock = [now]
    store = InMemoryStandingProposalStore()
    coordinator = _coordinator(store=store, clock=lambda: clock[0])
    proposal = coordinator.refresh("aico", ())[0]
    store.upsert(
        proposal.model_copy(
            update={
                "status": StandingProposalStatus.REJECTED,
                "decided_at": now,
                "decision_reason": "not this week",
            }
        )
    )

    assert coordinator.refresh("aico", ()) == ()

    clock[0] = now + timedelta(hours=169)
    refreshed = coordinator.refresh("aico", ())
    assert len(refreshed) == 1
    assert refreshed[0].proposal_id != proposal.proposal_id


def test_sqlite_standing_proposal_store_survives_restart_and_reset(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    first = SQLiteStandingProposalStore(path)
    proposal = _coordinator(store=first).refresh("aico", ())[0]

    second = SQLiteStandingProposalStore(path)

    assert second.list_project("aico") == (proposal,)
    assert SQLiteStateDatabase(path).table_counts()["standing_proposals"] == 1

    SQLiteStateDatabase(path).reset_state_tables()

    assert second.list_project("aico") == ()


def test_sme_agent_standing_charter_machine_dogfood(tmp_path: Path) -> None:
    config = ProjectAssignmentConfig.model_validate(
        json.loads(Path("projects/sme-agent/aico-project.json").read_text(encoding="utf-8"))
    )
    directory = ProjectAssignmentDirectory(config)
    store = SQLiteStandingProposalStore(tmp_path / "sme-state.db")

    def unreachable_task_factory(
        message: IncomingMessage,
        project_id: str,
        assignment: AssignmentProfile,
        payload: str,
    ) -> tuple[Task, AgentSession | None]:
        del message, project_id, assignment, payload
        raise AssertionError("refresh must not create a task")

    async def unreachable_runner(
        message: IncomingMessage,
        task: Task,
        session: AgentSession | None,
    ) -> str:
        del message, task, session
        raise AssertionError("refresh must not execute a task")

    coordinator = StandingProposalCoordinator(
        channel=RecordingChannel(),
        project_directory=directory,
        task_for_assignment=unreachable_task_factory,
        run_delegated_task=unreachable_runner,
        store=store,
        proposal_id_factory=lambda: "prop-sme-dogfood",
    )

    proposals = coordinator.refresh("sme-agent", ())

    assert len(proposals) == 1
    assert proposals[0].charter_id == "commercial-evidence-loop"
    assert proposals[0].status is StandingProposalStatus.CANDIDATE
    assert (
        SQLiteStandingProposalStore(tmp_path / "sme-state.db").list_project("sme-agent")
        == proposals
    )


async def test_standing_proposal_accept_routes_normal_project_task() -> None:
    store = InMemoryStandingProposalStore()
    channel = RecordingChannel()
    received: list[Task] = []

    async def run_task(
        message: IncomingMessage,
        task: Task,
        session: AgentSession | None,
    ) -> str:
        del message, session
        received.append(task)
        return "done"

    coordinator = _coordinator(store=store, channel=channel, run_task=run_task)
    message = _message("/inbox")
    proposal = coordinator.refresh("aico", ())[0]

    await coordinator.handle_proposal(message, f"accept {proposal.proposal_id}")

    accepted = store.list_project("aico")[0]
    assert accepted.status is StandingProposalStatus.ACCEPTED
    assert accepted.task_id == "task-standing"
    assert len(received) == 1
    assert _metadata_value(received[0], "aico.intent") == "standing_charter"
    assert _metadata_value(received[0], "aico.standing_proposal_id") == proposal.proposal_id
    assert "Boss accepted standing-charter proposal" in received[0].payload
    assert "normal risk and approval controls" in received[0].payload


async def test_standing_proposal_reject_records_reason_without_task() -> None:
    store = InMemoryStandingProposalStore()
    channel = RecordingChannel()
    coordinator = _coordinator(store=store, channel=channel)
    proposal = coordinator.refresh("aico", ())[0]

    await coordinator.handle_proposal(
        _message("/proposal reject"),
        f"reject {proposal.proposal_id} focus on customers first",
    )

    rejected = store.list_project("aico")[0]
    assert rejected.status is StandingProposalStatus.REJECTED
    assert rejected.decision_reason == "focus on customers first"
    assert rejected.task_id is None
    assert channel.sent_messages[-1].text.startswith("Proposal rejected:")


def _coordinator(
    *,
    store: InMemoryStandingProposalStore | SQLiteStandingProposalStore,
    clock: Callable[[], datetime] | None = None,
    channel: RecordingChannel | None = None,
    run_task: TaskRunner | None = None,
    directory: ProjectAssignmentDirectory | None = None,
) -> StandingProposalCoordinator:
    directory = directory or _project_directory()
    directory.set_active_project("telegram:chat-1:boss", "aico")
    task_ids = iter(("task-standing", "task-standing-2"))

    def task_for_assignment(
        message: IncomingMessage,
        project_id: str,
        assignment: AssignmentProfile,
        payload: str,
    ) -> tuple[Task, AgentSession | None]:
        del message
        return (
            Task(
                task_id=next(task_ids),
                payload=payload,
                requester_id="boss",
                target_persona=assignment.agent,
                context_ref=project_id,
            ),
            None,
        )

    async def default_run_task(
        message: IncomingMessage,
        task: Task,
        session: AgentSession | None,
    ) -> str:
        del message, task, session
        return "done"

    return StandingProposalCoordinator(
        channel=channel or RecordingChannel(),
        project_directory=directory,
        task_for_assignment=task_for_assignment,
        run_delegated_task=run_task or default_run_task,
        store=store,
        proposal_id_factory=iter(("prop-one", "prop-two", "prop-three")).__next__,
        clock=clock or (lambda: datetime(2026, 7, 21, 12, tzinfo=UTC)),
    )


def _project_directory() -> ProjectAssignmentDirectory:
    return ProjectAssignmentDirectory(
        ProjectAssignmentConfig(
            agents={
                "claude": CompanyAgentProfile(
                    id="claude",
                    provider="claude-code",
                    title="Lead",
                )
            },
            roles={
                "lead": RoleProfile(id="lead", title="Lead"),
                "challenger": RoleProfile(id="challenger", title="Challenger"),
            },
            projects={
                "aico": ProjectProfile(
                    id="aico",
                    name="AI Company OS",
                    repo="/repo/aico",
                    default_role="lead",
                    roles={
                        "lead": ProjectRoleProfile(role="lead"),
                        "challenger": ProjectRoleProfile(role="challenger"),
                    },
                    standing_charter=(
                        StandingCharterItem(
                            id="absence-loop",
                            objective="Inspect the absence loop and propose one bounded repair.",
                            role="lead",
                            acceptance_evidence=("one verified contract",),
                            stop_conditions=("stop before external sending",),
                            cooldown_hours=168,
                        ),
                    ),
                )
            },
            assignments=(
                AssignmentProfile(
                    project="aico",
                    agent="claude",
                    role="lead",
                    seat="aico-lead",
                ),
                AssignmentProfile(
                    project="aico",
                    agent="claude",
                    role="challenger",
                    seat="aico-challenger",
                ),
            ),
        )
    )


def _message(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        sender_id="boss",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        content=MessageContent(text=text),
        raw_ref="msg-1",
    )


def _metadata_value(task: Task, key: str) -> str | None:
    return next((str(item.value) for item in task.metadata if item.key == key), None)
