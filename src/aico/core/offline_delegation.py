"""Phase 8 offline delegation command support."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol

from aico.channel import IMChannel
from aico.core.agent_session import AgentSession
from aico.core.command_messages import short_id_text
from aico.core.message_rendering import rich_text_message
from aico.core.models import IncomingMessage, MessageContent, MetadataEntry, Task, utc_now
from aico.core.project_assignment import (
    AssignmentProfile,
    ProjectAssignmentDirectory,
    ProjectProfile,
)
from aico.core.session_commands import session_scope
from aico.core.sqlite_state import SQLiteStateDatabase

OFFLINE_DELEGATION_INTENT = "offline_delegation"
OFFLINE_DELEGATION_INTENT_KEY = "aico.intent"
OFFLINE_DELEGATION_ID_KEY = "aico.offline_delegation_id"
OFFLINE_DELEGATION_GOAL_KEY = "aico.offline_goal"
_MIN_HANDOFF_CHARS = 160

ProjectTaskFactory = Callable[
    [IncomingMessage, str, AssignmentProfile, str],
    tuple[Task, AgentSession | None],
]
DelegatedTaskRunner = Callable[[IncomingMessage, Task, AgentSession | None], Awaitable[object]]


@dataclass(frozen=True)
class OfflineDelegationRecord:
    delegation_id: str
    project_id: str
    project_name: str
    role: str
    agent: str
    task_id: str
    goal: str
    created_at: datetime = field(default_factory=utc_now)


class OfflineDelegationStore(Protocol):
    """Persistence boundary for offline delegation records."""

    def load_records(self, scope_id: str) -> tuple[OfflineDelegationRecord, ...]: ...

    def upsert_record(self, scope_id: str, record: OfflineDelegationRecord) -> None: ...


class SQLiteOfflineDelegationStore:
    """SQLite-backed offline delegation store sharing the local AICO state DB."""

    def __init__(self, path: Path | str) -> None:
        self._database = SQLiteStateDatabase(path)
        self._init_schema()

    def load_records(self, scope_id: str) -> tuple[OfflineDelegationRecord, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT payload FROM offline_delegations
                WHERE scope_id = ?
                ORDER BY created_at ASC
                """,
                (scope_id,),
            ).fetchall()
        return tuple(_record_from_json(str(row[0])) for row in rows)

    def upsert_record(self, scope_id: str, record: OfflineDelegationRecord) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO offline_delegations (scope_id, delegation_id, created_at, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(scope_id, delegation_id) DO UPDATE SET
                    created_at = excluded.created_at,
                    payload = excluded.payload
                """,
                (
                    scope_id,
                    record.delegation_id,
                    record.created_at.isoformat(),
                    _record_to_json(record),
                ),
            )

    def _init_schema(self) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS offline_delegations (
                    scope_id TEXT NOT NULL,
                    delegation_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (scope_id, delegation_id)
                )
                """
            )


class OfflineDelegationCommandHandler:
    """Create and list project-scoped offline delegation work orders."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        project_directory: ProjectAssignmentDirectory,
        task_for_assignment: ProjectTaskFactory,
        run_delegated_task: DelegatedTaskRunner,
        store: OfflineDelegationStore | None = None,
        max_records_per_scope: int = 5,
    ) -> None:
        self._channel = channel
        self._project_directory = project_directory
        self._task_for_assignment = task_for_assignment
        self._run_delegated_task = run_delegated_task
        self._store = store
        self._max_records_per_scope = max_records_per_scope
        self._records_by_scope: dict[str, list[OfflineDelegationRecord]] = {}

    async def handle_overnight(self, message: IncomingMessage, payload: str) -> None:
        goal = payload.strip()
        if not goal:
            await self._send_current_delegations(message)
            return

        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="No active project. Use /project <project> first."),
            )
            return
        assignment = self._project_directory.default_assignment(project.id)
        if assignment is None:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=(
                        f"No appointed lead for {project.id}. Use /appoint <agent> as <role> first."
                    )
                ),
            )
            return
        missing_roles = self._project_directory.missing_required_team_roles(project.id)
        if missing_roles:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=(
                        f"Team incomplete for {project.id}: missing {', '.join(missing_roles)}.\n"
                        "Offline delegation needs a project lead and challenger.\n\n"
                        "Next:\n"
                        "- /team\n"
                        "- /appoint <agent> as challenger"
                    )
                ),
            )
            return

        task, session = self._task_for_assignment(
            message,
            project.id,
            assignment,
            offline_delegation_prompt(project, assignment, goal),
        )
        delegation_id = f"night-{short_id_text(task.task_id)}"
        task = _task_with_offline_metadata(task, delegation_id, goal)
        record = OfflineDelegationRecord(
            delegation_id=delegation_id,
            project_id=project.id,
            project_name=project.name,
            role=assignment.role,
            agent=assignment.agent,
            task_id=task.task_id,
            goal=goal,
        )
        self._remember_record(session_scope(message), record)
        await self._channel.send_message(
            message.source,
            offline_delegation_started_message(record),
        )
        await self._run_delegated_task(message, task, session)

    async def _send_current_delegations(self, message: IncomingMessage) -> None:
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="No active project. Use /project <project> first."),
            )
            return
        scope_id = session_scope(message)
        records = [
            record
            for record in self._records_for_scope(scope_id)
            if record.project_id == project.id
        ]
        if not records:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=f"No overnight delegations for {project.id}. Use /overnight <goal>."
                ),
            )
            return
        lines = [f"Overnight delegations for {project.id}:"]
        lines.extend(
            f"• {record.delegation_id}: {record.role} -> {record.agent} "
            f"({short_id_text(record.task_id)})"
            for record in records
        )
        lines.append("")
        lines.append("Boss route:")
        lines.append("- now: /inbox")
        lines.append("- morning: /morning")
        lines.append("- exact trace: /task <short_id>")
        lines.append("- visual snapshot: /view")
        await self._channel.send_message(message.source, rich_text_message("\n".join(lines)))

    def records_for_scope(
        self,
        scope_id: str,
        *,
        project_id: str | None = None,
    ) -> tuple[OfflineDelegationRecord, ...]:
        records = self._records_for_scope(scope_id)
        if project_id is None:
            return records
        return tuple(record for record in records if record.project_id == project_id)

    def _remember_record(self, scope_id: str, record: OfflineDelegationRecord) -> None:
        records = [*self._records_for_scope(scope_id), record]
        self._records_by_scope[scope_id] = records[-self._max_records_per_scope :]
        if self._store is not None:
            self._store.upsert_record(scope_id, record)

    def _records_for_scope(self, scope_id: str) -> tuple[OfflineDelegationRecord, ...]:
        if scope_id not in self._records_by_scope and self._store is not None:
            records = self._store.load_records(scope_id)
            self._records_by_scope[scope_id] = list(records[-self._max_records_per_scope :])
        return tuple(self._records_by_scope.get(scope_id, ()))


def offline_delegation_prompt(
    project: ProjectProfile,
    assignment: AssignmentProfile,
    goal: str,
) -> str:
    return (
        "Offline delegation request for the project lead.\n"
        f"Project: {project.id} [{project.name}]\n"
        f"Lead role: {assignment.role}\n"
        f"Boss goal: {goal}\n\n"
        "Operating rules:\n"
        "- Work in small auditable steps and keep the project north star in mind.\n"
        "- Stay within AICO approval policy. If blocked by approval, missing credentials, "
        "or unclear scope, stop and report the blocker.\n"
        "- Leave a morning handoff with: done, blocked, risks, and next 3 actions.\n"
        "- Prefer project/team context and shared memory already provided above."
    )


def offline_delegation_completion_issue(output: str) -> str | None:
    text = output.strip()
    if len(text) < _MIN_HANDOFF_CHARS:
        return "handoff output is too short for an overnight delegation"

    missing = [
        label
        for label, markers in _HANDOFF_MARKERS
        if not any(marker in text.lower() for marker in markers)
    ]
    if missing:
        return f"handoff output is missing sections: {', '.join(missing)}"
    return None


def offline_delegation_started_message(record: OfflineDelegationRecord) -> MessageContent:
    text = (
        f"Overnight delegation queued: {record.delegation_id}\n"
        f"project: {record.project_id} [{record.project_name}]\n"
        f"lead: {record.role} -> {record.agent}\n"
        f"goal: {record.goal}\n"
        f"tracking: /task {short_id_text(record.task_id)}\n\n"
        "Boss route:\n"
        "- now: /inbox shows the first action and running work\n"
        "- morning: /morning shows done / blocked / risks / next actions\n"
        f"- exact trace: /task {short_id_text(record.task_id)} opens the lead handoff\n"
        "- visual snapshot: /view sends the HTML board when enabled\n"
        "- project context: /brief explains the project, not the overnight execution log\n\n"
        "Guardrails:\n"
        "- risky work still pauses for /approve\n"
        "- the lead should report done, blocked, risks, and next actions"
    )
    return rich_text_message(text)


def offline_delegation_incomplete_message(task_id: str, issue: str) -> MessageContent:
    short_id = short_id_text(task_id)
    return rich_text_message(
        "Overnight delegation output incomplete\n"
        f"task: {short_id}\n"
        f"reason: {issue}\n\n"
        "This was marked failed so it does not look like a successful morning handoff.\n\n"
        "Next:\n"
        f"- /task {short_id}\n"
        "- /inbox\n"
        "- rerun /overnight with a narrower goal, or ask the lead to continue"
    )


def _task_with_offline_metadata(task: Task, delegation_id: str, goal: str) -> Task:
    return task.model_copy(
        update={
            "metadata": (
                *task.metadata,
                MetadataEntry(key=OFFLINE_DELEGATION_INTENT_KEY, value=OFFLINE_DELEGATION_INTENT),
                MetadataEntry(key=OFFLINE_DELEGATION_ID_KEY, value=delegation_id),
                MetadataEntry(key=OFFLINE_DELEGATION_GOAL_KEY, value=goal[:200]),
            )
        }
    )


def _record_to_json(record: OfflineDelegationRecord) -> str:
    return json.dumps(
        {
            "delegation_id": record.delegation_id,
            "project_id": record.project_id,
            "project_name": record.project_name,
            "role": record.role,
            "agent": record.agent,
            "task_id": record.task_id,
            "goal": record.goal,
            "created_at": record.created_at.isoformat(),
        },
        ensure_ascii=False,
    )


def _record_from_json(payload: str) -> OfflineDelegationRecord:
    data = json.loads(payload)
    created_at = data.get("created_at")
    return OfflineDelegationRecord(
        delegation_id=str(data["delegation_id"]),
        project_id=str(data["project_id"]),
        project_name=str(data["project_name"]),
        role=str(data["role"]),
        agent=str(data["agent"]),
        task_id=str(data["task_id"]),
        goal=str(data["goal"]),
        created_at=datetime.fromisoformat(created_at) if created_at else utc_now(),
    )


_HANDOFF_MARKERS = (
    ("done", ("done", "完成", "已完成")),
    ("blocked", ("blocked", "blocker", "阻塞", "卡点")),
    ("risks", ("risks", "risk", "风险")),
    ("next actions", ("next", "下一步", "后续动作", "后续行动")),
)
