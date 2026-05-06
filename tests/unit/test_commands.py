from aico.core import CommandName, parse_command, reject_parts


def test_parse_command_accepts_plain_readonly_commands() -> None:
    status = parse_command("status")
    tasks = parse_command("tasks")
    help_command = parse_command("help")
    audit = parse_command("audit")
    agents = parse_command("agents")
    projects = parse_command("projects")
    brief = parse_command("brief")
    risks = parse_command("risks")
    blockers = parse_command("blockers")
    daily = parse_command("daily")
    weekly = parse_command("weekly")
    roles = parse_command("roles")
    assignments = parse_command("assignments")
    sessions = parse_command("sessions")

    assert status is not None
    assert tasks is not None
    assert help_command is not None
    assert audit is not None
    assert agents is not None
    assert projects is not None
    assert brief is not None
    assert risks is not None
    assert blockers is not None
    assert daily is not None
    assert weekly is not None
    assert roles is not None
    assert assignments is not None
    assert sessions is not None
    assert status.name is CommandName.STATUS
    assert tasks.name is CommandName.TASKS
    assert help_command.name is CommandName.HELP
    assert audit.name is CommandName.AUDIT
    assert agents.name is CommandName.AGENTS
    assert projects.name is CommandName.PROJECTS
    assert brief.name is CommandName.BRIEF
    assert risks.name is CommandName.RISKS
    assert blockers.name is CommandName.BLOCKERS
    assert daily.name is CommandName.DAILY
    assert weekly.name is CommandName.WEEKLY
    assert roles.name is CommandName.ROLES
    assert assignments.name is CommandName.ASSIGNMENTS
    assert sessions.name is CommandName.SESSIONS


def test_parse_command_accepts_slash_command_with_bot_suffix() -> None:
    command = parse_command("/approve@aico_bot abcdef12")

    assert command is not None
    assert command.name is CommandName.APPROVE
    assert command.payload == "abcdef12"


def test_parse_command_accepts_interrupt_command() -> None:
    command = parse_command("/interrupt abcdef12")

    assert command is not None
    assert command.name is CommandName.INTERRUPT
    assert command.payload == "abcdef12"


def test_parse_command_accepts_task_trace_commands() -> None:
    tasks_command = parse_command("/tasks 20")
    task_command = parse_command("/task abcdef12")

    assert tasks_command is not None
    assert task_command is not None
    assert tasks_command.name is CommandName.TASKS
    assert tasks_command.payload == "20"
    assert task_command.name is CommandName.TASK
    assert task_command.payload == "abcdef12"


def test_parse_command_ignores_persona_routes() -> None:
    assert parse_command("/claude inspect this") is None
    assert parse_command("@codex inspect this") is None
    assert parse_command("codex: inspect this") is None


def test_reject_parts_splits_task_id_and_reason() -> None:
    command = parse_command("/reject abcdef12 too broad")

    assert command is not None
    assert reject_parts(command) == ("abcdef12", "too broad")


def test_parse_command_accepts_session_commands() -> None:
    new_command = parse_command("/new claude")
    use_command = parse_command("/use abcdef12")
    sessions_command = parse_command("/sessions")
    bind_command = parse_command("/bind codex provider-123")

    assert new_command is not None
    assert use_command is not None
    assert sessions_command is not None
    assert bind_command is not None
    assert new_command.name is CommandName.NEW
    assert new_command.payload == "claude"
    assert use_command.name is CommandName.USE
    assert use_command.payload == "abcdef12"
    assert sessions_command.name is CommandName.SESSIONS
    assert bind_command.name is CommandName.BIND
    assert bind_command.payload == "codex provider-123"


def test_parse_command_accepts_agent_capability_commands() -> None:
    agent_command = parse_command("/agent claude")
    skills_command = parse_command("/skills claude")
    tools_command = parse_command("/tools codex")

    assert agent_command is not None
    assert skills_command is not None
    assert tools_command is not None
    assert agent_command.name is CommandName.AGENT
    assert agent_command.payload == "claude"
    assert skills_command.name is CommandName.SKILLS
    assert skills_command.payload == "claude"
    assert tools_command.name is CommandName.TOOLS
    assert tools_command.payload == "codex"


def test_parse_command_accepts_project_assignment_commands() -> None:
    project_command = parse_command("/project aico")
    use_project_command = parse_command("/use project aico")
    assignments_command = parse_command("/assignments aico")
    assignment_command = parse_command("/assignment aico-implementer")
    team_command = parse_command("/team aico")
    brief_command = parse_command("/brief aico")
    risks_command = parse_command("/risks aico")
    blockers_command = parse_command("/blockers aico")
    next_command = parse_command("/next aico")
    daily_command = parse_command("/daily aico")
    weekly_command = parse_command("/weekly aico")
    roles_command = parse_command("/roles aico")
    role_command = parse_command("/role propose 需要一个增长分析岗位")
    who_command = parse_command("/who implementer")
    appoint_command = parse_command("/appoint claude as implementer")
    unappoint_command = parse_command("/unappoint tester")
    ask_command = parse_command("/ask reviewer inspect this")
    lead_command = parse_command("/lead tester")
    default_command = parse_command("/default implementer")

    assert project_command is not None
    assert use_project_command is not None
    assert assignments_command is not None
    assert assignment_command is not None
    assert team_command is not None
    assert brief_command is not None
    assert risks_command is not None
    assert blockers_command is not None
    assert next_command is not None
    assert daily_command is not None
    assert weekly_command is not None
    assert roles_command is not None
    assert role_command is not None
    assert who_command is not None
    assert appoint_command is not None
    assert unappoint_command is not None
    assert ask_command is not None
    assert lead_command is not None
    assert default_command is not None
    assert project_command.name is CommandName.PROJECT
    assert project_command.payload == "aico"
    assert use_project_command.name is CommandName.USE
    assert use_project_command.payload == "project aico"
    assert assignments_command.name is CommandName.ASSIGNMENTS
    assert assignments_command.payload == "aico"
    assert assignment_command.name is CommandName.ASSIGNMENT
    assert assignment_command.payload == "aico-implementer"
    assert team_command.name is CommandName.TEAM
    assert team_command.payload == "aico"
    assert brief_command.name is CommandName.BRIEF
    assert brief_command.payload == "aico"
    assert risks_command.name is CommandName.RISKS
    assert risks_command.payload == "aico"
    assert blockers_command.name is CommandName.BLOCKERS
    assert blockers_command.payload == "aico"
    assert next_command.name is CommandName.NEXT
    assert next_command.payload == "aico"
    assert daily_command.name is CommandName.DAILY
    assert daily_command.payload == "aico"
    assert weekly_command.name is CommandName.WEEKLY
    assert weekly_command.payload == "aico"
    assert roles_command.name is CommandName.ROLES
    assert roles_command.payload == "aico"
    assert role_command.name is CommandName.ROLE
    assert role_command.payload == "propose 需要一个增长分析岗位"
    assert who_command.name is CommandName.WHO
    assert who_command.payload == "implementer"
    assert appoint_command.name is CommandName.APPOINT
    assert appoint_command.payload == "claude as implementer"
    assert unappoint_command.name is CommandName.UNAPPOINT
    assert unappoint_command.payload == "tester"
    assert ask_command.name is CommandName.ASK
    assert ask_command.payload == "reviewer inspect this"
    assert lead_command.name is CommandName.LEAD
    assert lead_command.payload == "tester"
    assert default_command.name is CommandName.DEFAULT
    assert default_command.payload == "implementer"
