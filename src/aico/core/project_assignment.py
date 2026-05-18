"""Project, agent, and assignment models for company-style project context."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import StrEnum

from pydantic import Field

from aico.core.models import Capability, FrozenModel, MetadataEntry, Task


class RoleScope(StrEnum):
    DOCS = "docs"
    CODE = "code"
    TESTS = "tests"
    OPS = "ops"
    AUDIT = "audit"


class CompanyAgentProfile(FrozenModel):
    id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    title: str = Field(min_length=1)
    base_prompt: str | None = None
    capabilities: tuple[Capability, ...] = ()


class RoleProfile(FrozenModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    prompt: str | None = None
    summary: str | None = None
    default_permissions: tuple[str, ...] = ()
    approval_required: tuple[str, ...] = ()
    inline_prompt: str | None = None


class ProjectRoleProfile(FrozenModel):
    role: str = Field(min_length=1)
    prompt_override: str | None = None
    inline_prompt_override: str | None = None
    resources: tuple[str, ...] = ()


class ProjectProfile(FrozenModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    repo: str = Field(min_length=1)
    north_star: str | None = None
    status_doc: str | None = None
    journal: str | None = None
    blockers_doc: str | None = None
    pitfalls_doc: str | None = None
    current_phase: str | None = None
    brief: str | None = None
    default_role: str | None = None
    default_assignment: str | None = None
    roles: dict[str, ProjectRoleProfile] = Field(default_factory=dict)


class AssignmentProfile(FrozenModel):
    seat: str = Field(min_length=1)
    project: str = Field(min_length=1)
    agent: str = Field(min_length=1)
    role: str = Field(min_length=1)
    prompt: str | None = None
    session_policy: str = Field(default="project_scoped", min_length=1)
    risk_policy: str = Field(default="approval_required", min_length=1)
    workspace: str | None = None
    permissions: tuple[str, ...] = ()


class ProjectAssignmentConfig(FrozenModel):
    agents: dict[str, CompanyAgentProfile] = Field(default_factory=dict)
    roles: dict[str, RoleProfile] = Field(default_factory=dict)
    projects: dict[str, ProjectProfile] = Field(default_factory=dict)
    appointments: tuple[AssignmentProfile, ...] = ()
    assignments: tuple[AssignmentProfile, ...] = ()


class ProjectAssignmentDirectory:
    """Resolve project-scoped assignments and active project context."""

    def __init__(self, config: ProjectAssignmentConfig | None = None) -> None:
        self._config = config or ProjectAssignmentConfig()
        self._validate()
        self._agents_by_ref = {_normalize(agent_id): agent_id for agent_id in self._config.agents}
        self._roles_by_ref = {_normalize(role_id): role_id for role_id in self._config.roles}
        self._projects_by_ref = {
            _normalize(project_id): project_id for project_id in self._config.projects
        }
        self._runtime_roles: dict[str, RoleProfile] = {}
        self._runtime_project_role_ids: dict[str, set[str]] = {}
        self._appointment_order: list[str] = []
        self._appointments_by_seat: dict[str, AssignmentProfile] = {}
        for appointment in self._appointments():
            self._store_unique_appointment(appointment)
        self._default_roles = {
            project.id: project.default_role or self._role_from_default_assignment(project)
            for project in self._config.projects.values()
        }
        self._active_projects: dict[str, str] = {}

    def agents(self) -> tuple[CompanyAgentProfile, ...]:
        return tuple(self._config.agents.values())

    def roles(self, project_id: str | None = None) -> tuple[RoleProfile, ...]:
        roles = {**self._config.roles, **self._runtime_roles}
        if project_id is None:
            return tuple(roles.values())
        project = self.project(project_id)
        if project is None:
            return ()
        role_ids = set(project.roles) if project.roles else set(roles)
        role_ids.update(self._runtime_project_role_ids.get(project.id, set()))
        return tuple(role for role in roles.values() if role.id in role_ids)

    def role(self, role_id: str) -> RoleProfile | None:
        role_key = self._roles_by_ref.get(_normalize(role_id), role_id)
        return self._runtime_roles.get(role_key) or self._config.roles.get(role_key)

    def project_role(
        self,
        project_id: str,
        role_id: str,
    ) -> ProjectRoleProfile | None:
        project = self.project(project_id)
        if project is None:
            return None
        normalized_role = _normalize(role_id)
        for project_role in project.roles.values():
            if _normalize(project_role.role) == normalized_role:
                return project_role
        return None

    def projects(self) -> tuple[ProjectProfile, ...]:
        return tuple(self._config.projects.values())

    def appointments(self, project_id: str | None = None) -> tuple[AssignmentProfile, ...]:
        appointments = tuple(
            self._appointments_by_seat[seat]
            for seat in self._appointment_order
            if seat in self._appointments_by_seat
        )
        if project_id is None:
            return appointments
        return tuple(
            appointment
            for appointment in appointments
            if _normalize(appointment.project) == _normalize(project_id)
        )

    def assignments(self, project_id: str | None = None) -> tuple[AssignmentProfile, ...]:
        return self.appointments(project_id)

    def project(self, project_id: str) -> ProjectProfile | None:
        project_key = self._projects_by_ref.get(_normalize(project_id), project_id)
        return self._config.projects.get(project_key)

    def agent(self, agent_id: str) -> CompanyAgentProfile | None:
        agent_key = self._agents_by_ref.get(_normalize(agent_id), agent_id)
        return self._config.agents.get(agent_key)

    def assignment(self, seat: str) -> AssignmentProfile | None:
        return self._appointments_by_seat.get(seat)

    def appointment_for_role(
        self,
        project_id: str,
        role_id: str,
    ) -> AssignmentProfile | None:
        normalized_role = _normalize(role_id)
        for appointment in self.appointments(project_id):
            if _normalize(appointment.role) == normalized_role:
                return appointment
        return None

    def default_assignment(self, project_id: str) -> AssignmentProfile | None:
        project = self.project(project_id)
        if project is None:
            return None
        default_role = self._default_roles.get(project.id)
        if default_role:
            appointment = self.appointment_for_role(project.id, default_role)
            if appointment is not None:
                return appointment
        if project.default_assignment:
            return self.assignment(project.default_assignment)
        appointments = self.appointments(project_id)
        return appointments[0] if appointments else None

    def set_default_role(self, project_id: str, role_id: str) -> AssignmentProfile | None:
        project = self.project(project_id)
        if project is None:
            return None
        appointment = self.appointment_for_role(project.id, role_id)
        if appointment is None:
            return None
        self._default_roles[project.id] = appointment.role
        return appointment

    def upsert_appointment(
        self,
        *,
        project_id: str,
        agent_id: str,
        role_id: str,
        permissions: tuple[str, ...] = (),
    ) -> AssignmentProfile | None:
        project = self.project(project_id)
        if project is None:
            return None
        canonical_agent_id = self._agents_by_ref.get(_normalize(agent_id))
        if canonical_agent_id is None:
            return None
        canonical_role_id = self._roles_by_ref.get(_normalize(role_id), _normalize(role_id))
        existing = self.appointment_for_role(project.id, role_id)
        seat = existing.seat if existing is not None else _seat_id(project.id, canonical_role_id)
        role = self.role(canonical_role_id)
        resolved_permissions = permissions
        if not resolved_permissions and role is not None:
            resolved_permissions = role.default_permissions
        appointment = AssignmentProfile(
            project=project.id,
            agent=canonical_agent_id,
            role=canonical_role_id,
            seat=seat,
            permissions=resolved_permissions,
        )
        self._store_unique_appointment(appointment)
        if not self._default_roles.get(project.id):
            self._default_roles[project.id] = canonical_role_id
        return appointment

    def add_project_role(self, project_id: str, role: RoleProfile) -> RoleProfile | None:
        project = self.project(project_id)
        if project is None:
            return None
        canonical_role_id = _normalize(role.id)
        if self.role(canonical_role_id) is not None:
            return None
        runtime_role = role.model_copy(update={"id": canonical_role_id})
        self._runtime_roles[canonical_role_id] = runtime_role
        self._roles_by_ref[_normalize(canonical_role_id)] = canonical_role_id
        self._runtime_project_role_ids.setdefault(project.id, set()).add(canonical_role_id)
        return runtime_role

    def remove_appointment_for_role(
        self,
        project_id: str,
        role_id: str,
    ) -> AssignmentProfile | None:
        project = self.project(project_id)
        if project is None:
            return None
        appointment = self.appointment_for_role(project.id, role_id)
        if appointment is None:
            return None
        self._appointments_by_seat.pop(appointment.seat, None)
        if _normalize(self._default_roles.get(project.id) or "") == _normalize(appointment.role):
            fallback = self.default_assignment(project.id)
            if fallback is None:
                self._default_roles.pop(project.id, None)
            else:
                self._default_roles[project.id] = fallback.role
        return appointment

    def set_active_project(self, scope_id: str, project_id: str) -> ProjectProfile | None:
        project = self.project(project_id)
        if project is None:
            return None
        self._active_projects[scope_id] = project.id
        return project

    def active_project(self, scope_id: str) -> ProjectProfile | None:
        project_id = self._active_projects.get(scope_id)
        if project_id is None:
            return None
        project = self.project(project_id)
        if project is None:
            self._active_projects.pop(scope_id, None)
            return None
        return project

    def _validate(self) -> None:
        _validate_keys("agent", self._config.agents)
        _validate_keys("role", self._config.roles)
        _validate_keys("project", self._config.projects)
        seats = _unique_values(
            "assignment seat",
            (appointment.seat for appointment in self._appointments()),
        )
        for project in self._config.projects.values():
            if project.default_assignment and project.default_assignment not in seats:
                raise ValueError(
                    f"project {project.id} references unknown default assignment "
                    f"{project.default_assignment}"
                )
            for role_id, project_role in project.roles.items():
                if project_role.role != role_id:
                    raise ValueError(
                        f"project {project.id} role key {role_id} must match "
                        f"role value {project_role.role}"
                    )
        for appointment in self._appointments():
            if appointment.project not in self._config.projects:
                raise ValueError(
                    f"assignment {appointment.seat} references unknown project "
                    f"{appointment.project}"
                )
            if appointment.agent not in self._config.agents:
                raise ValueError(
                    f"assignment {appointment.seat} references unknown agent {appointment.agent}"
                )

    def _appointments(self) -> tuple[AssignmentProfile, ...]:
        return (*self._config.assignments, *self._config.appointments)

    def _role_from_default_assignment(self, project: ProjectProfile) -> str | None:
        if not project.default_assignment:
            return None
        for appointment in self._appointments():
            if appointment.seat == project.default_assignment:
                return appointment.role
        return None

    def _store_unique_appointment(self, appointment: AssignmentProfile) -> None:
        existing = self.appointment_for_role(appointment.project, appointment.role)
        if existing is not None and existing.seat != appointment.seat:
            self._appointments_by_seat.pop(existing.seat, None)
            self._appointment_order = [
                seat for seat in self._appointment_order if seat != existing.seat
            ]
        if appointment.seat not in self._appointment_order:
            self._appointment_order.append(appointment.seat)
        self._appointments_by_seat[appointment.seat] = appointment


_PROJECT_ID_KEY = "aico.project_id"
_ASSIGNMENT_SEAT_KEY = "aico.assignment_seat"
_ASSIGNMENT_ROLE_KEY = "aico.assignment_role"
_ASSIGNMENT_KEYS = {
    _PROJECT_ID_KEY,
    _ASSIGNMENT_SEAT_KEY,
    _ASSIGNMENT_ROLE_KEY,
}


def task_with_assignment_context(
    task: Task,
    *,
    project: ProjectProfile,
    assignment: AssignmentProfile,
) -> Task:
    metadata = tuple(entry for entry in task.metadata if entry.key not in _ASSIGNMENT_KEYS)
    return task.model_copy(
        update={
            "context_ref": project.id,
            "metadata": (
                *metadata,
                MetadataEntry(key=_PROJECT_ID_KEY, value=project.id),
                MetadataEntry(key=_ASSIGNMENT_SEAT_KEY, value=assignment.seat),
                MetadataEntry(key=_ASSIGNMENT_ROLE_KEY, value=assignment.role),
            ),
        }
    )


def _validate_keys(label: str, values: Mapping[str, object]) -> None:
    for key in values:
        if not key.strip():
            raise ValueError(f"{label} id must not be empty")


def _unique_values(label: str, values: Iterable[str]) -> frozenset[str]:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"duplicate {label}: {value}")
        seen.add(value)
    return frozenset(seen)


def _normalize(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def _seat_id(project_id: str, role_id: str) -> str:
    return f"{_normalize(project_id)}-{_normalize(role_id)}"
