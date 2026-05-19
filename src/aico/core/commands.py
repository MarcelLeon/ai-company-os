"""Parse built-in IM commands without coupling them to a channel."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CommandName(StrEnum):
    HELP = "help"
    STATUS = "status"
    METRICS = "metrics"
    TASKS = "tasks"
    TASK = "task"
    AUDIT = "audit"
    PROJECTS = "projects"
    PROJECT = "project"
    BRIEF = "brief"
    RISKS = "risks"
    BLOCKERS = "blockers"
    NEXT = "next"
    DAILY = "daily"
    WEEKLY = "weekly"
    OVERNIGHT = "overnight"
    ASSIGNMENTS = "assignments"
    ASSIGNMENT = "assignment"
    ROLES = "roles"
    ROLE = "role"
    TEAM = "team"
    WHO = "who"
    APPOINT = "appoint"
    UNAPPOINT = "unappoint"
    ASK = "ask"
    LEAD = "lead"
    DEFAULT = "default"
    AGENTS = "agents"
    AGENT = "agent"
    SKILLS = "skills"
    TOOLS = "tools"
    REMEMBER = "remember"
    RECALL = "recall"
    FORGET = "forget"
    BROADCAST = "broadcast"
    SESSIONS = "sessions"
    NEW = "new"
    USE = "use"
    BIND = "bind"
    APPROVE = "approve"
    REJECT = "reject"
    INTERRUPT = "interrupt"


@dataclass(frozen=True)
class Command:
    name: CommandName
    payload: str = ""


def parse_command(text: str) -> Command | None:
    stripped = text.strip()
    lowered = stripped.lower()
    if lowered in {
        CommandName.HELP,
        CommandName.STATUS,
        CommandName.METRICS,
        CommandName.TASKS,
        CommandName.AUDIT,
        CommandName.PROJECTS,
        CommandName.BRIEF,
        CommandName.RISKS,
        CommandName.BLOCKERS,
        CommandName.DAILY,
        CommandName.WEEKLY,
        CommandName.OVERNIGHT,
        CommandName.ASSIGNMENTS,
        CommandName.ROLES,
        CommandName.TEAM,
        CommandName.AGENTS,
        CommandName.SESSIONS,
    }:
        return Command(CommandName(lowered))

    first, separator, rest = stripped.partition(" ")
    if not first.startswith("/"):
        return None

    name = first[1:].split("@", maxsplit=1)[0].lower()
    try:
        command_name = CommandName(name)
    except ValueError:
        return None
    return Command(command_name, rest.strip() if separator else "")


def reject_parts(command: Command) -> tuple[str | None, str | None]:
    if not command.payload:
        return None, None
    task_id, separator, reason = command.payload.partition(" ")
    return task_id.strip(), reason.strip() if separator and reason.strip() else None


def help_text() -> str:
    return (
        "Commands:\n"
        "/status - show adapter status\n"
        "/metrics - show local task and agent metrics\n"
        "/tasks [limit] - show recent tasks\n"
        "/task <task_id> - show one task and available actions\n"
        "/audit - show recent audit events\n"
        "/projects - list configured projects\n"
        "/project [project] - enter or show the project office\n"
        "/brief [project] - show a project brief from local state\n"
        "/risks [project] - show current project risks from local state\n"
        "/blockers [project] - show current blocked work and decisions\n"
        "/next [project] - suggest next project actions from local state\n"
        "/daily [project] - show a daily local project report\n"
        "/weekly [project] - show a weekly local project report\n"
        "/overnight <goal> - delegate an offline project goal to the current lead\n"
        "/roles [project|all] - show compact role board; add all for hidden roles\n"
        "/role <id> - show one role's scope and approval policy\n"
        "/role propose <need> - draft a new project role for confirmation\n"
        "/role confirm - add the pending role draft to the active project\n"
        "/team [project] - show project team appointments\n"
        "/who <role> - show who owns a role in the active project\n"
        "/appoint <agent> as <role> [scope] - appoint an agent; default scope comes from role\n"
        "/unappoint <role> - remove a role appointment from the active project\n"
        "/ask <role> <task> - send one task to a project role\n"
        "/lead <role> - set the lead role for plain messages\n"
        "/default <role> - legacy alias for /lead <role>\n"
        "/use project <project> - route plain messages to a project\n"
        "/assignments [project] - list project assignment seats\n"
        "/assignment <seat> - show one project assignment\n"
        "/agents - list configured agents\n"
        "/agent <agent> - show role, status, and provider facade\n"
        "/skills <agent> - ask the provider to list its own skills\n"
        "/tools <agent> - ask the provider to list its own tools\n"
        "/remember <fact> - remember an important fact for the active project\n"
        "/recall [query] - show active project memory\n"
        "/forget <memory_id> - archive one active project memory\n"
        "/sessions - list AICO agent sessions\n"
        "/new <agent> - create an AICO session reference\n"
        "/use <session_id> - route plain messages to a session\n"
        "/bind <session_id|agent> <provider_session_id> - bind an existing provider session\n"
        "/broadcast <task> - send task to every active persona\n"
        "/approve [task_id] - approve a waiting risky task\n"
        "/reject [task_id] [reason] - reject a waiting risky task\n"
        "/interrupt <task_id> - interrupt a running task\n"
        "/claude <task> - send task to Claude Code\n"
        "/codex <task> - send read-only task to Codex\n"
        "@codex <task> or codex: <task> also work"
    )
