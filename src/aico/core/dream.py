"""Dream review that records candidate runbook memory."""

from __future__ import annotations

from collections import defaultdict

from aico.channel import IMChannel
from aico.core.command_messages import short_id_text
from aico.core.memory import (
    ExperienceMeta,
    MemoryAtom,
    MemoryEvidence,
    MemoryKind,
    MemoryPurpose,
    MemoryScope,
    MemoryStatus,
    MemoryStore,
)
from aico.core.message_rendering import rich_text_message
from aico.core.models import IncomingMessage, MessageContent, TaskSnapshot, TaskStatus, utc_now
from aico.core.project_assignment import ProjectAssignmentDirectory
from aico.core.session_commands import session_scope
from aico.core.task_bus import TaskBus

_PROJECT_ID_KEY = "aico.project_id"


class DreamCommandHandler:
    """Turn recent project signals into reviewable memory candidates."""

    def __init__(
        self,
        *,
        channel: IMChannel,
        project_directory: ProjectAssignmentDirectory,
        memory_store: MemoryStore | None,
        task_bus: TaskBus,
    ) -> None:
        self._channel = channel
        self._project_directory = project_directory
        self._memory_store = memory_store
        self._task_bus = task_bus

    async def handle_dream(self, message: IncomingMessage) -> None:
        project = self._project_directory.active_project(session_scope(message))
        if project is None:
            await self._channel.send_message(
                message.source,
                MessageContent(text="No active project. Use /project <project> first."),
            )
            return
        if self._memory_store is None:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=(
                        "Dream review needs shared memory. Set AICO_MEMORY_PATH and restart AICO."
                    )
                ),
            )
            return

        candidates = self._candidate_atoms(project.id, message.sender_id)
        stored = tuple(self._memory_store.append_atom(atom) for atom in candidates)
        await self._channel.send_message(
            message.source,
            dream_review_message(project.id, stored),
        )

    def _candidate_atoms(self, project_id: str, created_by: str) -> tuple[MemoryAtom, ...]:
        scoped_tasks = _scoped_tasks(self._task_bus.task_snapshots(limit=None), project_id)
        grouped: dict[str, list[TaskSnapshot]] = defaultdict(list)
        for snapshot in scoped_tasks:
            key = _candidate_key(snapshot)
            if key is None:
                continue
            grouped[key].append(snapshot)

        candidates: list[MemoryAtom] = []
        for key, snapshots in grouped.items():
            claim = _candidate_claim(key, tuple(snapshots[:5]))
            if claim is None:
                continue
            candidates.append(_memory_atom(project_id, tuple(snapshots[:5]), claim, created_by))
            if len(candidates) >= 5:
                break
        return tuple(candidates)


def dream_review_message(project_id: str, candidates: tuple[MemoryAtom, ...]) -> MessageContent:
    lines = [
        f"# Dream review: {project_id}",
        "status: candidate experience only",
        "",
        "Meaning:",
        "- These are reusable lessons inferred from recent project task signals.",
        "- They are stored as candidate experience; they are not injected into prompts "
        "until promoted.",
    ]
    if not candidates:
        lines.extend(
            (
                "",
                "Candidates:",
                "- none from recent project signals",
                "",
                "Effect:",
                "- active experience unchanged",
            )
        )
    else:
        lines.append("")
        lines.append("Candidates:")
        for atom in candidates:
            refs = ", ".join(evidence.ref.removeprefix("task:")[:8] for evidence in atom.evidence)
            lines.append(f"- {atom.memory_id}: {atom.claim} (status={atom.status.value})")
            lines.append(f"  evidence: {refs}")
        lines.append("")
        lines.append("Effect:")
        lines.append("- written as candidate experience; not injected into prompts until promoted")
    lines.append("")
    lines.append("Next:")
    lines.append("- /inbox")
    lines.append("- /remember <accepted lesson>")
    return rich_text_message("\n".join(lines))


def _candidate_key(snapshot: TaskSnapshot) -> str | None:
    if snapshot.status is TaskStatus.WAITING_APPROVAL:
        return "waiting_approval"
    if snapshot.status is TaskStatus.RUNNING:
        return "running"
    if snapshot.status is TaskStatus.FAILED:
        reason = (snapshot.reason or "unknown failure").casefold()
        if "idle timeout" in reason or "no adapter output" in reason:
            return "failed:adapter_idle_timeout"
        if "interrupted" in reason:
            return "failed:interrupted"
        return f"failed:{_compact_reason(reason)}"
    if snapshot.status is TaskStatus.INTERRUPTED:
        return "interrupted"
    if snapshot.status is TaskStatus.REJECTED:
        return "rejected"
    return None


def _candidate_claim(key: str, snapshots: tuple[TaskSnapshot, ...]) -> str | None:
    refs = _task_refs(snapshots)
    count = len(snapshots)
    if key == "waiting_approval":
        return (
            f"{count} task(s) are blocked on approval ({refs}); decide before delegating "
            "related follow-up work."
        )
    if key == "running":
        return (
            f"{count} task(s) are still running ({refs}); inspect or interrupt before "
            "stacking more work."
        )
    if key == "failed:adapter_idle_timeout":
        return (
            f"Adapter idle timeout repeated on {count} task(s) ({refs}); before retrying, "
            "inspect adapter logs, provider session health, and captured task output."
        )
    if key in {"failed:interrupted", "interrupted"}:
        return (
            f"Interrupted work appears in {count} task(s) ({refs}); inspect partial output "
            "and clarify the retry boundary before restarting."
        )
    if key == "rejected":
        return f"{count} task(s) were rejected ({refs}); clarify approval boundary before retrying."
    if key.startswith("failed:"):
        reason = key.removeprefix("failed:")
        return (
            f"{count} task(s) failed with similar reason '{reason}' ({refs}); capture a "
            "recovery step before retrying."
        )
    return None


def _memory_atom(
    project_id: str,
    snapshots: tuple[TaskSnapshot, ...],
    claim: str,
    created_by: str,
) -> MemoryAtom:
    now = utc_now()
    first = snapshots[0]
    trigger_key = _candidate_key(first) or "unknown"
    return MemoryAtom(
        memory_id=f"dream-{short_id_text(first.task_id)}-{int(now.timestamp())}",
        claim=claim,
        evidence=tuple(
            MemoryEvidence(
                ref=f"task:{snapshot.task_id}",
                source="dream_review",
                captured_at=now,
                note=snapshot.status.value,
            )
            for snapshot in snapshots
        ),
        scope=MemoryScope.project(project_id),
        source="dream_review",
        confidence=0.6,
        created_by=created_by,
        status=MemoryStatus.CANDIDATE,
        tags=("dream", "runbook-candidate"),
        purpose_tags=(MemoryPurpose.TASK_KEY_PROGRESS,),
        kind=MemoryKind.EXPERIENCE,
        experience=ExperienceMeta(triggers=(trigger_key,)),
    )


def _scoped_tasks(
    task_snapshots: tuple[TaskSnapshot, ...],
    project_id: str,
) -> tuple[TaskSnapshot, ...]:
    scoped = tuple(
        snapshot
        for snapshot in task_snapshots
        if _metadata_value(snapshot, _PROJECT_ID_KEY) == project_id
    )
    return tuple(sorted(scoped, key=lambda snapshot: snapshot.updated_at, reverse=True))


def _metadata_value(snapshot: TaskSnapshot, key: str) -> str | None:
    for entry in snapshot.metadata:
        if entry.key == key and entry.value is not None:
            return str(entry.value)
    return None


def _task_refs(snapshots: tuple[TaskSnapshot, ...]) -> str:
    return ", ".join(short_id_text(snapshot.task_id) for snapshot in snapshots)


def _compact_reason(reason: str) -> str:
    compact = " ".join(reason.split())
    if len(compact) > 64:
        return f"{compact[:61]}..."
    return compact
