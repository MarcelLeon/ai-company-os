from aico.core import (
    AssignmentProfile,
    Capability,
    CompanyAgentProfile,
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
    ProjectProfile,
    ProjectRoleProfile,
    RoleProfile,
    Task,
    task_with_assignment_context,
)


def test_project_assignment_directory_tracks_active_project_by_scope() -> None:
    directory = ProjectAssignmentDirectory(_config())

    active = directory.set_active_project("telegram:chat:user", "aico")

    assert active is not None
    assert active.name == "AI Company OS"
    assert directory.active_project("telegram:chat:user") == active
    assert directory.default_assignment("aico") == directory.assignment("aico-implementer")
    assert directory.appointments("aico")[0].seat == "aico-implementer"
    assert directory.assignments("aico")[0].seat == "aico-implementer"


def test_project_assignment_directory_updates_default_role_and_appointments() -> None:
    directory = ProjectAssignmentDirectory(_config())

    appointment = directory.upsert_appointment(
        project_id="aico",
        agent_id="Claude",
        role_id="Tester",
        permissions=("read_repo", "run_tests"),
    )

    assert appointment is not None
    assert appointment.seat == "aico-tester"
    assert appointment.agent == "claude"
    assert appointment.role == "tester"
    assert directory.appointment_for_role("aico", "tester") == appointment
    assert directory.set_default_role("aico", "tester") == appointment
    assert directory.default_assignment("aico") == appointment


def test_project_assignment_directory_resolves_lead_alias_to_default_assignment() -> None:
    directory = ProjectAssignmentDirectory(_config())

    assert directory.appointment_for_role("aico", "lead") == directory.default_assignment("aico")
    assert directory.appointment_for_role("aico", "default") == directory.default_assignment("aico")


def test_project_assignment_directory_inherits_role_permissions_when_appointing() -> None:
    directory = ProjectAssignmentDirectory(_config())

    appointment = directory.upsert_appointment(
        project_id="aico",
        agent_id="claude",
        role_id="tester",
    )

    assert appointment is not None
    assert appointment.permissions == ("code", "tests")


def test_project_assignment_directory_reports_missing_required_team_roles() -> None:
    directory = ProjectAssignmentDirectory(_config())

    assert directory.missing_required_team_roles("aico") == ("challenger",)

    challenger = directory.upsert_appointment(
        project_id="aico",
        agent_id="claude",
        role_id="challenger",
        permissions=("docs", "audit"),
    )

    assert challenger is not None
    assert directory.missing_required_team_roles("aico") == ()


def test_project_assignment_directory_resolves_agent_by_provider_name() -> None:
    config = _config().model_copy(
        update={
            "agents": {
                **_config().agents,
                "flicker": CompanyAgentProfile(
                    id="flicker",
                    provider="codeflicker",
                    title="CodeFlicker",
                    max_concurrent_tasks=5,
                    recommended_max_appointments=5,
                ),
            }
        }
    )
    directory = ProjectAssignmentDirectory(config)

    appointment = directory.upsert_appointment(
        project_id="aico",
        agent_id="codeflicker",
        role_id="tester",
    )

    assert appointment is not None
    assert appointment.agent == "flicker"
    assert directory.agent("codeflicker") == config.agents["flicker"]


def test_project_assignment_directory_keeps_one_appointment_per_project_role() -> None:
    directory = ProjectAssignmentDirectory(
        _config().model_copy(
            update={
                "appointments": (
                    AssignmentProfile(
                        project="aico",
                        agent="claude",
                        role="tester",
                        seat="aico-old-tester",
                        permissions=("read_repo",),
                    ),
                    AssignmentProfile(
                        project="aico",
                        agent="claude",
                        role="tester",
                        seat="aico-new-tester",
                        permissions=("read_repo", "run_tests"),
                    ),
                )
            }
        )
    )

    assert [appointment.role for appointment in directory.appointments("aico")] == [
        "implementer",
        "tester",
    ]
    assert directory.assignment("aico-old-tester") is None
    assert directory.appointment_for_role("aico", "tester") == directory.assignment(
        "aico-new-tester"
    )

    updated = directory.upsert_appointment(
        project_id="aico",
        agent_id="claude",
        role_id="tester",
        permissions=("read_repo", "run_tests"),
    )

    assert updated is not None
    assert [appointment.role for appointment in directory.appointments("aico")] == [
        "implementer",
        "tester",
    ]
    assert directory.appointment_for_role("aico", "tester") == updated


def test_project_assignment_directory_adds_runtime_project_role() -> None:
    directory = ProjectAssignmentDirectory(_config())
    role = RoleProfile(
        id="growth-analyst",
        title="Growth Analyst",
        summary="Analyze activation and retention opportunities.",
        default_permissions=("read_docs",),
    )

    added = directory.add_project_role("aico", role)

    assert added == role
    assert directory.role("growth_analyst") == role
    assert role in directory.roles("aico")
    assert directory.add_project_role("aico", role) is None


def test_project_assignment_directory_removes_role_appointment_and_falls_back_lead() -> None:
    directory = ProjectAssignmentDirectory(_config())
    appointment = directory.upsert_appointment(
        project_id="aico",
        agent_id="claude",
        role_id="tester",
        permissions=("read_repo", "run_tests"),
    )

    assert appointment is not None
    assert directory.set_default_role("aico", "tester") == appointment

    removed = directory.remove_appointment_for_role("aico", "tester")

    assert removed == appointment
    assert directory.appointment_for_role("aico", "tester") is None
    assert directory.assignment("aico-tester") is None
    assert directory.default_assignment("aico") == directory.assignment("aico-implementer")


def test_project_assignment_directory_rejects_unknown_assignment_reference() -> None:
    config = ProjectAssignmentConfig(
        agents={
            "claude": CompanyAgentProfile(
                id="claude",
                provider="claude-code",
                title="Senior Implementer",
            )
        },
        projects={
            "aico": ProjectProfile(
                id="aico",
                name="AI Company OS",
                repo="/repo",
                default_assignment="missing-seat",
            )
        },
    )

    try:
        ProjectAssignmentDirectory(config)
    except ValueError as exc:
        assert "unknown default assignment missing-seat" in str(exc)
    else:
        raise AssertionError("expected config validation to fail")


def test_task_assignment_context_metadata_roundtrips() -> None:
    directory = ProjectAssignmentDirectory(_config())
    project = directory.project("aico")
    assignment = directory.assignment("aico-implementer")
    task = Task(
        task_id="task-1",
        payload="continue",
        requester_id="user-1",
        target_persona="implementer",
    )

    assert project is not None
    assert assignment is not None

    updated = task_with_assignment_context(task, project=project, assignment=assignment)
    metadata = {entry.key: entry.value for entry in updated.metadata}

    assert updated.context_ref == "aico"
    assert metadata["aico.project_id"] == "aico"
    assert metadata["aico.assignment_seat"] == "aico-implementer"
    assert metadata["aico.assignment_role"] == "implementer"


def _config() -> ProjectAssignmentConfig:
    return ProjectAssignmentConfig(
        agents={
            "claude": CompanyAgentProfile(
                id="claude",
                provider="claude-code",
                title="Senior Implementer",
                capabilities=(Capability.CODE_EDIT,),
            )
        },
        roles={
            "implementer": RoleProfile(
                id="implementer",
                title="Implementation Lead",
                default_permissions=("code", "tests", "docs"),
            ),
            "tester": RoleProfile(
                id="tester",
                title="Test Lead",
                default_permissions=("code", "tests"),
            ),
        },
        projects={
            "aico": ProjectProfile(
                id="aico",
                name="AI Company OS",
                repo="/repo",
                current_phase="Phase 5",
                default_role="implementer",
                default_assignment="aico-implementer",
                roles={
                    "implementer": ProjectRoleProfile(role="implementer"),
                    "tester": ProjectRoleProfile(role="tester"),
                },
            )
        },
        assignments=(
            AssignmentProfile(
                project="aico",
                agent="claude",
                role="implementer",
                seat="aico-implementer",
            ),
        ),
    )
