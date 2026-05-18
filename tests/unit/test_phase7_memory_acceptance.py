from collections.abc import AsyncIterator, Callable
from pathlib import Path

from aico.channel import IncomingMessageHandler
from aico.core import (
    AckStatus,
    AdapterStatus,
    AssignmentProfile,
    Capability,
    ChannelTarget,
    CompanyAgentProfile,
    HealthStatus,
    IncomingMessage,
    JsonlMemoryStore,
    MemoryAtom,
    MemoryBroadcastService,
    MemoryEdgeType,
    MemoryEvidence,
    MemoryScope,
    MemoryStatus,
    MessageContent,
    MessageRouter,
    Orchestrator,
    OutputType,
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
    ProjectProfile,
    RoleProfile,
    SentMessage,
    Task,
    TaskAck,
    TaskBus,
    TaskOutput,
    collaboration_payload,
)


async def test_phase7_memory_acceptance_covers_team_management_flow(tmp_path: Path) -> None:
    memory_path = tmp_path / "phase7" / "memory.jsonl"
    store = JsonlMemoryStore(memory_path)
    adapter = AcceptanceAdapter()
    channel = RecordingChannel()
    task_ids = iter(
        (
            "task-memory-use",
            "task-global-feedback",
            "task-global-use",
            "task-candidate-feedback",
            "task-candidate-use",
            "task-team-use",
        )
    )
    orchestrator = _orchestrator(
        channel=channel,
        adapter=adapter,
        store=store,
        task_id_factory=lambda: next(task_ids),
    )

    await orchestrator.handle_incoming(_incoming("/use project aico"))
    store.append_atom(
        _memory_atom(
            "mem-payroll-budget",
            "Payroll project salary budget must stay confidential to HR.",
            MemoryScope.project("payroll"),
        )
    )
    await orchestrator.handle_incoming(
        _incoming("/remember Customer contracts require legal review before external sharing.")
    )
    project_memory_id = _memory_id_from(channel.sent_messages[-1].text)

    await orchestrator.handle_incoming(_incoming("/recall legal"))
    assert "Customer contracts require legal review before external sharing." in (
        channel.sent_messages[-1].text
    )

    await orchestrator.handle_incoming(
        _incoming("Prepare the enterprise delivery plan with legal review checkpoints.")
    )
    project_payload = adapter.received_tasks[-1].payload
    assert "Shared memory:" in project_payload
    assert "Customer contracts require legal review before external sharing." in project_payload
    assert "Payroll project salary budget" not in project_payload

    await orchestrator.handle_incoming(_incoming("我更喜欢汇报进度时告诉我还有几阶段"))
    assert store.list_atoms(MemoryScope.boss("boss-1"))

    await orchestrator.handle_incoming(_incoming("汇报当前项目进度，并告诉我还有几阶段"))
    global_payload = adapter.received_tasks[-1].payload
    assert "Boss feedback: 我更喜欢汇报进度时告诉我还有几阶段" in global_payload

    await orchestrator.handle_incoming(_incoming("这个项目我可能更喜欢状态汇总先短一点"))
    candidate_atoms = store.list_atoms(MemoryScope.project("aico"))
    assert any(atom.status is MemoryStatus.CANDIDATE for atom in candidate_atoms)

    await orchestrator.handle_incoming(_incoming("状态汇总"))
    candidate_payload = adapter.received_tasks[-1].payload
    assert "这个项目我可能更喜欢状态汇总先短一点" not in candidate_payload

    receipt = MemoryBroadcastService(store).broadcast_to_team(
        source_memory_id=project_memory_id,
        team_scope=MemoryScope.team("aico", "default"),
        recipients=("lead", "implementer", "qa"),
        created_by="lead-agent",
        reason="weekly project office consensus",
    )
    assert receipt.recipients == ("lead", "implementer", "qa")
    assert store.list_edges(project_memory_id)[0].edge_type is MemoryEdgeType.BROADCAST_TO

    restored_store = JsonlMemoryStore(memory_path)
    restored_channel = RecordingChannel()
    restored_adapter = AcceptanceAdapter()
    restored_orchestrator = _orchestrator(
        channel=restored_channel,
        adapter=restored_adapter,
        store=restored_store,
        task_id_factory=lambda: "task-restored-team-use",
    )

    await restored_orchestrator.handle_incoming(_incoming("/use project aico"))
    await restored_orchestrator.handle_incoming(
        _incoming("Ask QA to check legal review checkpoints.")
    )
    restored_payload = restored_adapter.received_tasks[-1].payload
    assert receipt.broadcast_memory_id in restored_payload
    assert "scope: team:aico/default" in restored_payload
    assert "Customer contracts require legal review before external sharing." in restored_payload

    assert collaboration_payload(
        "lead",
        "QA should verify the legal-review checklist.",
        memory_refs=(receipt.broadcast_memory_id,),
        use_memory_refs=True,
    ) == (
        "Collaboration request from lead:\n\n"
        f"Memory refs: {receipt.broadcast_memory_id}\n"
        "Delta:\n"
        "QA should verify the legal-review checklist."
    )
    assert collaboration_payload(
        "lead",
        "QA should verify the legal-review checklist.",
        memory_refs=(),
        use_memory_refs=True,
    ) == ("Collaboration request from lead:\n\nQA should verify the legal-review checklist.")

    await restored_orchestrator.handle_incoming(_incoming(f"/forget {project_memory_id}"))
    assert "Memory archived" in restored_channel.sent_messages[-1].text
    assert restored_store.get_atom(project_memory_id).status is MemoryStatus.ARCHIVED  # type: ignore[union-attr]


class AcceptanceAdapter:
    def __init__(self) -> None:
        self.received_tasks: list[Task] = []

    @property
    def name(self) -> str:
        return "scripted"

    def capabilities(self) -> frozenset[Capability]:
        return frozenset({Capability.CODE_EDIT, Capability.STREAM_OUTPUT})

    async def receive_task(self, task: Task) -> TaskAck:
        self.received_tasks.append(task)
        return TaskAck(task_id=task.task_id, status=AckStatus.ACCEPTED)

    async def _outputs(self, task_id: str) -> AsyncIterator[TaskOutput]:
        yield TaskOutput(task_id=task_id, sequence=0, type=OutputType.TEXT, content="ok")
        yield TaskOutput(task_id=task_id, sequence=1, type=OutputType.DONE, content="")

    def stream_output(self, task_id: str) -> AsyncIterator[TaskOutput]:
        return self._outputs(task_id)

    def status(self) -> AdapterStatus:
        return AdapterStatus.IDLE

    async def interrupt(self, task_id: str) -> None:
        _ = task_id

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


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
        _ = target
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
        _ = target, message_id

    def on_incoming(self, handler: IncomingMessageHandler) -> None:
        self.handler = handler

    async def health_check(self) -> HealthStatus:
        return HealthStatus.OK


def _orchestrator(
    *,
    channel: RecordingChannel,
    adapter: AcceptanceAdapter,
    store: JsonlMemoryStore,
    task_id_factory: Callable[[], str],
) -> Orchestrator:
    return Orchestrator(
        channel=channel,
        router=MessageRouter(default_persona="lead", task_id_factory=task_id_factory),
        task_bus=TaskBus(adapter),
        project_directory=_project_directory(),
        memory_store=store,
    )


def _project_directory() -> ProjectAssignmentDirectory:
    return ProjectAssignmentDirectory(
        ProjectAssignmentConfig(
            agents={
                "lead": CompanyAgentProfile(id="lead", provider="scripted", title="Lead Agent"),
                "implementer": CompanyAgentProfile(
                    id="implementer",
                    provider="scripted",
                    title="Implementation Agent",
                ),
                "qa": CompanyAgentProfile(id="qa", provider="scripted", title="QA Agent"),
            },
            roles={
                "lead": RoleProfile(id="lead", title="Project Lead"),
                "implementer": RoleProfile(id="implementer", title="Implementation Lead"),
                "qa": RoleProfile(id="qa", title="QA Lead"),
            },
            projects={
                "aico": ProjectProfile(
                    id="aico",
                    name="AI Company OS",
                    repo="/work/aico",
                    default_role="lead",
                ),
                "payroll": ProjectProfile(
                    id="payroll",
                    name="Payroll Modernization",
                    repo="/work/payroll",
                    default_role="lead",
                ),
            },
            appointments=(
                AssignmentProfile(
                    seat="aico-lead",
                    project="aico",
                    agent="lead",
                    role="lead",
                ),
                AssignmentProfile(
                    seat="aico-impl",
                    project="aico",
                    agent="implementer",
                    role="implementer",
                ),
                AssignmentProfile(
                    seat="aico-qa",
                    project="aico",
                    agent="qa",
                    role="qa",
                ),
                AssignmentProfile(
                    seat="payroll-lead",
                    project="payroll",
                    agent="lead",
                    role="lead",
                ),
            ),
        )
    )


def _incoming(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="boss-1",
        mentions=(),
        content=MessageContent(text=text),
        raw_ref=f"message:{text[:16]}",
    )


def _memory_atom(memory_id: str, claim: str, scope: MemoryScope) -> MemoryAtom:
    return MemoryAtom(
        memory_id=memory_id,
        claim=claim,
        evidence=(MemoryEvidence(ref=f"test:{memory_id}", source="acceptance"),),
        scope=scope,
        source="acceptance_fixture",
        confidence=0.95,
        created_by="acceptance",
        tags=("acceptance",),
    )


def _memory_id_from(message: str) -> str:
    for line in message.splitlines():
        if line.startswith("id: "):
            return line.removeprefix("id: ").strip()
    raise AssertionError(f"memory id not found in message: {message}")
