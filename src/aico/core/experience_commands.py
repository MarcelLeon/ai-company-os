"""Lead-internal commands for managing project experience lifecycle.

Boss does NOT use these directly. They are tools for the lead role to:
- review candidate experiences emitted by /dream
- promote (accept) one as active experience that auto-injects into role prompts
- archive an active experience that stopped being useful

Promoted experiences are still scope-bound (project) and governed by the same
MemoryGovernor rules as facts; the only difference is they auto-inject into
prompt_stack when role + trigger match. See ADR-0031.
"""

from __future__ import annotations

from aico.channel import IMChannel
from aico.core.memory import (
    MemoryAtom,
    MemoryKind,
    MemoryScope,
    MemoryStatus,
    MemoryStore,
)
from aico.core.message_rendering import rich_text_message
from aico.core.models import IncomingMessage, MessageContent
from aico.core.project_assignment import ProjectAssignmentDirectory, ProjectProfile
from aico.core.session_commands import session_scope

_USAGE = (
    "Usage:\n"
    "- /experience review — list candidate experiences from /dream\n"
    "- /experience list [role] — list active experiences (optionally for one role)\n"
    "- /experience promote <id> [as <role>[,<role>...]] — accept a candidate\n"
    "- /experience archive <id> — retire an active experience"
)


class ExperienceCommandHandler:
    """Manage candidate -> active -> archived lifecycle for experiences."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        project_directory: ProjectAssignmentDirectory,
        memory_store: MemoryStore | None,
    ) -> None:
        self._channel = channel
        self._project_directory = project_directory
        self._memory_store = memory_store

    async def handle_experience(self, message: IncomingMessage, payload: str) -> None:
        project = await self._active_project_or_reply(message)
        if project is None:
            return
        if self._memory_store is None:
            await self._send_not_configured(message)
            return

        verb, _, rest = payload.strip().partition(" ")
        verb = verb.strip().lower()
        rest = rest.strip()

        if not verb or verb == "review":
            await self._handle_review(message, project)
            return
        if verb == "list":
            await self._handle_list(message, project, role_filter=rest or None)
            return
        if verb == "promote":
            await self._handle_promote(message, project, rest)
            return
        if verb == "archive":
            await self._handle_archive(message, project, rest)
            return

        await self._channel.send_message(message.source, MessageContent(text=_USAGE))

    async def _handle_review(
        self,
        message: IncomingMessage,
        project: ProjectProfile,
    ) -> None:
        store = self._memory_store
        assert store is not None
        candidates = store.list_experiences(
            MemoryScope.project(project.id),
            statuses=(MemoryStatus.CANDIDATE,),
        )
        await self._channel.send_message(
            message.source,
            _render_review_message(project.id, candidates),
        )

    async def _handle_list(
        self,
        message: IncomingMessage,
        project: ProjectProfile,
        *,
        role_filter: str | None,
    ) -> None:
        store = self._memory_store
        assert store is not None
        actives = store.list_experiences(
            MemoryScope.project(project.id),
            role_id=role_filter,
            statuses=(MemoryStatus.ACTIVE,),
        )
        await self._channel.send_message(
            message.source,
            _render_list_message(project.id, actives, role_filter=role_filter),
        )

    async def _handle_promote(
        self,
        message: IncomingMessage,
        project: ProjectProfile,
        payload: str,
    ) -> None:
        store = self._memory_store
        assert store is not None
        memory_id, applies_to = _parse_promote_payload(payload)
        if memory_id is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /experience promote <id> [as <role>[,<role>...]]"),
            )
            return
        atom = store.get_atom(memory_id)
        if atom is None or not atom.scope.matches(MemoryScope.project(project.id)):
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Unknown experience id: {memory_id}"),
            )
            return
        if atom.kind is not MemoryKind.EXPERIENCE:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=(
                        f"Memory {memory_id} is kind={atom.kind.value}; "
                        "/experience promote only accepts kind=experience candidates."
                    )
                ),
            )
            return
        promoted = store.promote_experience(memory_id, applies_to=applies_to)
        await self._channel.send_message(
            message.source,
            _render_promoted_message(promoted),
        )

    async def _handle_archive(
        self,
        message: IncomingMessage,
        project: ProjectProfile,
        payload: str,
    ) -> None:
        store = self._memory_store
        assert store is not None
        memory_id = payload.strip()
        if not memory_id:
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /experience archive <id>"),
            )
            return
        atom = store.get_atom(memory_id)
        if atom is None or not atom.scope.matches(MemoryScope.project(project.id)):
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Unknown experience id: {memory_id}"),
            )
            return
        if atom.kind is not MemoryKind.EXPERIENCE:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=(
                        f"Memory {memory_id} is kind={atom.kind.value}; "
                        "use /forget for fact memory."
                    )
                ),
            )
            return
        archived = store.archive(memory_id, reason="lead /experience archive")
        await self._channel.send_message(
            message.source,
            rich_text_message(
                "\n".join(
                    (
                        "# Experience archived",
                        f"id: {archived.memory_id}",
                        f"scope: {archived.scope.owner_type.value}:{archived.scope.owner_id}",
                    )
                )
            ),
        )

    async def _active_project_or_reply(
        self,
        message: IncomingMessage,
    ) -> ProjectProfile | None:
        project = self._project_directory.active_project(session_scope(message))
        if project is not None:
            return project
        await self._channel.send_message(
            message.source,
            MessageContent(text="No active project. Use /project <project> first."),
        )
        return None

    async def _send_not_configured(self, message: IncomingMessage) -> None:
        await self._channel.send_message(
            message.source,
            MessageContent(
                text=("Experience needs shared memory. Set AICO_MEMORY_PATH and restart AICO.")
            ),
        )


def _parse_promote_payload(payload: str) -> tuple[str | None, tuple[str, ...]]:
    if not payload.strip():
        return None, ()
    parts = payload.split()
    memory_id = parts[0]
    applies_to: tuple[str, ...] = ()
    if len(parts) >= 3 and parts[1].lower() == "as":
        roles_text = " ".join(parts[2:])
        applies_to = tuple(role.strip() for role in roles_text.split(",") if role.strip())
    return memory_id, applies_to


def _render_review_message(
    project_id: str,
    candidates: tuple[MemoryAtom, ...],
) -> MessageContent:
    lines = [
        f"# Experience review: {project_id}",
        "scope: project candidate experiences (not yet injected into prompts)",
    ]
    if not candidates:
        lines.extend(("", "No candidates. Run /dream to surface new ones."))
    else:
        lines.append("")
        for atom in candidates:
            triggers = ""
            if atom.experience is not None and atom.experience.triggers:
                triggers = f" triggers: {', '.join(atom.experience.triggers)}"
            lines.append(
                f"- {atom.memory_id}: {atom.claim} (confidence: {atom.confidence:.2f}){triggers}"
            )
            lines.append(f"  promote: /experience promote {atom.memory_id} as <role>")
    return rich_text_message("\n".join(lines))


def _render_list_message(
    project_id: str,
    actives: tuple[MemoryAtom, ...],
    *,
    role_filter: str | None,
) -> MessageContent:
    header = f"# Active experiences: {project_id}"
    if role_filter is not None:
        header = f"{header} (role={role_filter})"
    lines = [header]
    if not actives:
        lines.extend(("", "No active experience yet. Run /experience review to promote one."))
    else:
        lines.append("")
        for atom in actives:
            applies = ""
            if atom.experience is not None and atom.experience.applies_to:
                applies = f" applies_to: {', '.join(atom.experience.applies_to)}"
            lines.append(
                f"- {atom.memory_id}: {atom.claim} (confidence: {atom.confidence:.2f}){applies}"
            )
    return rich_text_message("\n".join(lines))


def _render_promoted_message(atom: MemoryAtom) -> MessageContent:
    meta = atom.experience
    applies_line = "applies_to: (all roles in project)"
    triggers_line = "triggers: (always inject)"
    if meta is not None and meta.applies_to:
        applies_line = f"applies_to: {', '.join(meta.applies_to)}"
    if meta is not None and meta.triggers:
        triggers_line = f"triggers: {', '.join(meta.triggers)}"
    return rich_text_message(
        "\n".join(
            (
                "# Experience promoted",
                f"id: {atom.memory_id}",
                f"status: {atom.status.value}",
                applies_line,
                triggers_line,
                "",
                "Next:",
                "- /experience list",
                f"- /experience archive {atom.memory_id}",
            )
        )
    )
