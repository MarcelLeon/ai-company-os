"""Render appointment-aware task prompts without owning provider tool execution."""

from __future__ import annotations

from aico.core.memory import MemoryPacket
from aico.core.models import Task
from aico.core.project_assignment import (
    AssignmentProfile,
    CompanyAgentProfile,
    ProjectProfile,
    ProjectRoleProfile,
    RoleProfile,
)


def render_appointment_prompt(
    *,
    task: Task,
    agent: CompanyAgentProfile | None,
    role: RoleProfile | None,
    project: ProjectProfile,
    project_role: ProjectRoleProfile | None,
    appointment: AssignmentProfile,
    memory_packet: MemoryPacket | None = None,
) -> str:
    sections = [
        _agent_section(agent, appointment),
        _role_section(role, appointment),
        _project_section(project, project_role),
        _appointment_section(project, appointment),
        _memory_section(memory_packet),
        _runtime_section(task),
    ]
    return "\n\n".join(section for section in sections if section)


def _agent_section(agent: CompanyAgentProfile | None, appointment: AssignmentProfile) -> str:
    title = appointment.agent if agent is None else agent.title
    lines = [f"Agent: {appointment.agent}", f"Title: {title}"]
    if agent is not None and agent.base_prompt:
        lines.append(f"Base prompt: {agent.base_prompt}")
    return "\n".join(lines)


def _role_section(role: RoleProfile | None, appointment: AssignmentProfile) -> str:
    if role is None:
        return f"Role: {appointment.role}"
    lines = [f"Role: {role.id}", f"Role title: {role.title}"]
    if role.summary:
        lines.append(f"Role summary: {role.summary}")
    if role.inline_prompt:
        lines.append(role.inline_prompt)
    elif role.prompt:
        lines.append(f"Role prompt: {role.prompt}")
    return "\n".join(lines)


def _project_section(
    project: ProjectProfile,
    project_role: ProjectRoleProfile | None,
) -> str:
    lines = [
        f"Project: {project.id} [{project.name}]",
        f"Repo: {project.repo}",
    ]
    if project.current_phase:
        lines.append(f"Phase: {project.current_phase}")
    if project.north_star:
        lines.append(f"North star: {project.north_star}")
    if project.status_doc:
        lines.append(f"Status doc: {project.status_doc}")
    if project.journal:
        lines.append(f"Journal: {project.journal}")
    if project.brief:
        lines.append(f"Project brief: {project.brief}")
    if project_role is not None:
        if project_role.inline_prompt_override:
            lines.append(project_role.inline_prompt_override)
        elif project_role.prompt_override:
            lines.append(f"Project role prompt: {project_role.prompt_override}")
        if project_role.resources:
            lines.append(f"Role resources: {', '.join(project_role.resources)}")
    return "\n".join(lines)


def _appointment_section(project: ProjectProfile, appointment: AssignmentProfile) -> str:
    permissions = ", ".join(appointment.permissions) or appointment.risk_policy
    workspace = appointment.workspace or project.repo
    return "\n".join(
        (
            "Appointment contract:",
            f"- {appointment.agent} is appointed to {project.id} as {appointment.role}.",
            f"- Workspace: {workspace}",
            f"- Permissions: {permissions}",
            f"- Seat: {appointment.seat}",
        )
    )


def _memory_section(memory_packet: MemoryPacket | None) -> str:
    if memory_packet is None:
        return ""
    return memory_packet.render_prompt_section()


def _runtime_section(task: Task) -> str:
    return "\n".join(("Current task:", task.payload))
