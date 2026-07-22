from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from pathlib import Path

from aico.channel import IncomingMessageHandler
from aico.core import (
    AckStatus,
    AdapterStatus,
    AssignmentProfile,
    AuditEventType,
    Capability,
    ChannelTarget,
    CompanyAgentProfile,
    HealthStatus,
    IncomingMessage,
    JsonlMemoryStore,
    MemoryKind,
    MemoryScope,
    MemoryStatus,
    MessageContent,
    MessageRouter,
    MetadataEntry,
    Orchestrator,
    OutputType,
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
    ProjectProfile,
    ProjectRoleProfile,
    RoleProfile,
    SentMessage,
    Task,
    TaskAck,
    TaskBus,
    TaskOutput,
)


async def test_fantasy_party_case_validates_shared_memory_dream_and_experience(
    tmp_path: Path,
) -> None:
    adapter = RoleAwareAdapter(
        {
            "lead": "Journey plan: keep companion promises visible before assigning work.",
            "implementer": "Retry plan: resolve approval boundary before touching the travel log.",
        }
    )
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    memory_store = JsonlMemoryStore(tmp_path / "frieren-memory.jsonl")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="lead", task_id_factory=_task_ids("frieren-task")),
        task_bus=bus,
        project_directory=_project_directory(
            "frieren-party",
            "Long Memory Fantasy Party",
            roles=("lead", "implementer"),
            default_role="lead",
        ),
        memory_store=memory_store,
    )

    await _send(orchestrator, "/project frieren-party")
    await _send(
        orchestrator,
        "/remember The party promised to write down companion preferences before "
        "accepting a new village request.",
    )
    await _send(orchestrator, "/ask lead plan the winter village request")

    lead_payload = adapter.latest_task_for_role("lead").payload
    assert "Shared memory:" in lead_payload
    assert "companion preferences" in lead_payload

    await bus.submit(
        _project_task(
            "frieren-approval-1",
            project_id="frieren-party",
            role="implementer",
            payload="update the travel log before asking the boss",
        )
    )
    await _send(orchestrator, "/dream")

    dream_text = channel.sent_messages[-1].text
    candidate = memory_store.list_atoms(MemoryScope.project("frieren-party"))[-1]
    assert "Dream review: frieren-party" in dream_text
    assert "candidate experience only" in dream_text
    assert candidate.kind is MemoryKind.EXPERIENCE
    assert candidate.status is MemoryStatus.CANDIDATE
    assert candidate.source == "dream_review"
    assert "/experience review" in dream_text

    await _send(orchestrator, "/inbox")
    inbox_text = channel.sent_messages[-1].text
    assert "经验候选:" in inbox_text
    assert candidate.memory_id in inbox_text
    assert f"/experience promote {candidate.memory_id} as <role>" in inbox_text
    assert f"/experience archive {candidate.memory_id}" in inbox_text

    await _send(orchestrator, "/morning")
    morning_text = channel.sent_messages[-1].text
    assert "Experience candidates:" in morning_text
    assert candidate.memory_id in morning_text
    assert "/experience review" in morning_text

    await _send(orchestrator, f"/experience promote {candidate.memory_id} as implementer")
    promoted = memory_store.get_atom(candidate.memory_id)
    assert promoted is not None
    assert promoted.status is MemoryStatus.ACTIVE

    await _send(orchestrator, "/inbox")
    inbox_after_accept = channel.sent_messages[-1].text
    assert "经验候选:" not in inbox_after_accept
    assert candidate.memory_id not in inbox_after_accept

    adapter.received_tasks.clear()
    await _send(orchestrator, "/ask implementer plan the retry")

    implementer_task = adapter.latest_task_for_role("implementer")
    assert "Reusable experience (promoted lessons):" in implementer_task.payload
    assert candidate.memory_id in implementer_task.payload
    injected_ids = _metadata_value(implementer_task, "aico.injected_experience_ids")
    assert injected_ids is not None
    assert candidate.memory_id in injected_ids


async def test_infinity_castle_case_validates_collaboration_audit_and_dream(
    tmp_path: Path,
) -> None:
    adapter = RoleAwareAdapter(
        {
            "scout": (
                "Raid plan: map shifting rooms before dispatch.\n"
                "@reviewer: inspect the raid plan for blind spots and missing approvals."
            ),
            "reviewer": "Review findings: approval boundary is the main raid risk.",
            "swordsman": "Next strike: wait for approval before changing route notes.",
        }
    )
    channel = RecordingChannel()
    bus = TaskBus(adapter)
    memory_store = JsonlMemoryStore(tmp_path / "castle-memory.jsonl")
    orchestrator = Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="scout", task_id_factory=_task_ids("castle-task")),
        task_bus=bus,
        project_directory=_project_directory(
            "infinity-castle",
            "Infinity Castle Raid Room",
            roles=("scout", "reviewer", "swordsman"),
            default_role="swordsman",
        ),
        memory_store=memory_store,
    )

    await _send(orchestrator, "/project infinity-castle")
    await _send(
        orchestrator,
        "/remember The castle route shifts after every encounter; preserve last known safe exits.",
    )
    await _send(orchestrator, "/ask scout prepare the first raid plan using safe exits")

    scout_payload = adapter.latest_task_for_role("scout").payload
    reviewer_payload = adapter.latest_task_for_role("reviewer").payload
    assert "Shared memory:" in scout_payload
    assert "last known safe exits" in scout_payload
    assert "Context from scout output so far:" in reviewer_payload

    collaboration_events = [
        event
        for event in bus.audit_events(limit=None)
        if event.event_type is AuditEventType.COLLABORATION_REQUESTED
    ]
    assert len(collaboration_events) == 1
    assert collaboration_events[0].actor_id == "scout"
    assert collaboration_events[0].target_persona == "reviewer"
    assert collaboration_events[0].detail == "parent_task=castle-task-001"

    await bus.submit(
        _project_task(
            "castle-approval-1",
            project_id="infinity-castle",
            role="swordsman",
            payload="update the raid route notes before approval",
        )
    )
    await _send(orchestrator, "/dream")
    candidate = memory_store.list_atoms(MemoryScope.project("infinity-castle"))[-1]
    assert candidate.kind is MemoryKind.EXPERIENCE
    assert "blocked on approval" in candidate.claim

    await _send(orchestrator, "/inbox")
    inbox_text = channel.sent_messages[-1].text
    assert "经验候选:" in inbox_text
    assert candidate.memory_id in inbox_text
    assert f"/experience promote {candidate.memory_id} as <role>" in inbox_text
    assert f"/experience archive {candidate.memory_id}" in inbox_text

    await _send(orchestrator, "/morning")
    morning_text = channel.sent_messages[-1].text
    assert "Experience candidates:" in morning_text
    assert candidate.memory_id in morning_text
    assert "/experience review" in morning_text

    await _send(orchestrator, f"/experience archive {candidate.memory_id}")
    archived = memory_store.get_atom(candidate.memory_id)
    assert archived is not None
    assert archived.status is MemoryStatus.ARCHIVED

    await _send(orchestrator, "/inbox")
    inbox_after_reject = channel.sent_messages[-1].text
    assert "经验候选:" not in inbox_after_reject
    assert candidate.memory_id not in inbox_after_reject

    adapter.received_tasks.clear()
    await _send(orchestrator, "/ask swordsman prepare the next strike")

    swordsman_task = adapter.latest_task_for_role("swordsman")
    assert "Reusable experience (promoted lessons):" not in swordsman_task.payload
    assert candidate.memory_id not in swordsman_task.payload


class RoleAwareAdapter:
    def __init__(self, outputs_by_role: dict[str, str]) -> None:
        self._outputs_by_role = outputs_by_role
        self._tasks_by_id: dict[str, Task] = {}
        self.received_tasks: list[Task] = []

    @property
    def name(self) -> str:
        return "showcase-agent"

    def capabilities(self) -> frozenset[Capability]:
        return frozenset(
            {
                Capability.CODE_EDIT,
                Capability.CODE_REVIEW,
                Capability.SHELL_EXEC,
                Capability.STREAM_OUTPUT,
            }
        )

    async def receive_task(self, task: Task) -> TaskAck:
        self.received_tasks.append(task)
        self._tasks_by_id[task.task_id] = task
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        return self._outputs(task_id)

    async def _outputs(self, task_id: str) -> AsyncIterator[TaskOutput]:
        task = self._tasks_by_id[task_id]
        role = _metadata_value(task, "aico.assignment_role") or task.target_persona
        yield TaskOutput(
            task_id=task_id,
            sequence=0,
            type=OutputType.TEXT,
            content=self._outputs_by_role.get(role, f"{role} completed."),
        )
        yield TaskOutput(task_id=task_id, sequence=1, type=OutputType.DONE, content="")

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        _ = task_id

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK

    def latest_task_for_role(self, role: str) -> Task:
        for task in reversed(self.received_tasks):
            task_role = _metadata_value(task, "aico.assignment_role") or task.target_persona
            if task_role == role:
                return task
        raise AssertionError(f"role task not found: {role}")


class RecordingChannel:
    def __init__(self) -> None:
        self.handler: IncomingMessageHandler | None = None
        self.sent_messages: list[MessageContent] = []
        self.edited_messages: list[MessageContent] = []

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
        _ = (target, message_id)
        self.edited_messages.append(content)

    async def delete_message(self, target: ChannelTarget, message_id: str) -> None:
        _ = (target, message_id)

    def on_incoming(self, handler: IncomingMessageHandler) -> None:
        self.handler = handler

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


async def _send(orchestrator: Orchestrator, text: str) -> None:
    await orchestrator.handle_incoming(
        IncomingMessage(
            channel_name="telegram",
            source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
            sender_id="boss",
            mentions=(),
            content=MessageContent(text=text),
            raw_ref=f"raw:{text}",
        )
    )


def _project_directory(
    project_id: str,
    project_name: str,
    *,
    roles: tuple[str, ...],
    default_role: str,
) -> ProjectAssignmentDirectory:
    assignments = tuple(
        AssignmentProfile(
            project=project_id,
            agent="showcase-agent",
            role=role,
            seat=f"{project_id}-{role}",
            permissions=("docs", "audit", "code", "tests"),
        )
        for role in roles
    )
    return ProjectAssignmentDirectory(
        ProjectAssignmentConfig(
            agents={
                "showcase-agent": CompanyAgentProfile(
                    id="showcase-agent",
                    provider="showcase-agent",
                    title="Showcase Agent",
                )
            },
            roles={
                role: RoleProfile(
                    id=role,
                    title=role.replace("-", " ").title(),
                    default_permissions=("docs", "audit", "code", "tests"),
                )
                for role in roles
            },
            projects={
                project_id: ProjectProfile(
                    id=project_id,
                    name=project_name,
                    repo=f"/repo/{project_id}",
                    current_phase="showcase",
                    default_role=default_role,
                    default_assignment=f"{project_id}-{default_role}",
                    roles={role: ProjectRoleProfile(role=role) for role in roles},
                )
            },
            assignments=assignments,
        )
    )


def _project_task(task_id: str, *, project_id: str, role: str, payload: str) -> Task:
    return Task(
        task_id=task_id,
        payload=payload,
        requester_id="boss",
        target_persona=role,
        metadata=(
            MetadataEntry(key="aico.project_id", value=project_id),
            MetadataEntry(key="aico.assignment_role", value=role),
        ),
    )


def _task_ids(prefix: str) -> Callable[[], str]:
    counter = 0

    def _next() -> str:
        nonlocal counter
        counter += 1
        return f"{prefix}-{counter:03d}"

    return _next


def _metadata_value(task: Task, key: str) -> str | None:
    for entry in task.metadata:
        if entry.key == key:
            return str(entry.value)
    return None
