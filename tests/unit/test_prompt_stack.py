from aico.core import (
    AssignmentProfile,
    CompanyAgentProfile,
    MemoryCitation,
    MemoryPacket,
    MemoryPacketItem,
    MemoryScope,
    ProjectProfile,
    RoleProfile,
    Task,
    render_appointment_prompt,
)


def test_render_appointment_prompt_injects_memory_before_current_task() -> None:
    prompt = render_appointment_prompt(
        task=Task(
            task_id="task-1",
            payload="design recall",
            requester_id="boss",
            target_persona="implementer",
        ),
        agent=CompanyAgentProfile(
            id="claude",
            provider="claude-code",
            title="Senior Implementer",
        ),
        role=RoleProfile(id="implementer", title="Implementation Lead"),
        project=ProjectProfile(id="aico", name="AI Company OS", repo="/repo"),
        project_role=None,
        appointment=AssignmentProfile(
            seat="aico-implementer",
            project="aico",
            agent="claude",
            role="implementer",
        ),
        memory_packet=MemoryPacket(
            items=(
                MemoryPacketItem(
                    memory_id="mem-1",
                    claim="Memory must stay project scoped.",
                    confidence=0.91,
                    scope=MemoryScope.project("aico"),
                ),
            ),
            citations=(MemoryCitation(memory_id="mem-1", reason="scope=query match"),),
            policy_summary="max_sensitivity=internal; min_confidence=0.0",
        ),
    )

    assert "Shared memory:\n- [mem-1] Memory must stay project scoped." in prompt
    assert prompt.index("Shared memory:") < prompt.index("Current task:")
    assert "Current task:\ndesign recall" in prompt


def test_render_appointment_prompt_marks_project_lead_responsibility() -> None:
    prompt = render_appointment_prompt(
        task=Task(
            task_id="task-1",
            payload="decide release scope",
            requester_id="boss",
            target_persona="pm",
        ),
        agent=CompanyAgentProfile(id="claude", provider="claude-code", title="Lead Agent"),
        role=RoleProfile(id="pm", title="Project Lead"),
        project=ProjectProfile(id="aico", name="AI Company OS", repo="/repo"),
        project_role=None,
        appointment=AssignmentProfile(
            seat="aico-pm",
            project="aico",
            agent="claude",
            role="pm",
        ),
        is_project_lead=True,
    )

    assert "Lead responsibility:" in prompt
    assert "Reduce boss cognitive load" in prompt
    assert "challenger, reviewer" in prompt
    assert prompt.index("Lead responsibility:") < prompt.index("Project: aico")
