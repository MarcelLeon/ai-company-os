"""IM-facing shared memory commands."""

from __future__ import annotations

from uuid import uuid4

from aico.channel import IMChannel
from aico.core.memory import (
    MemoryAtom,
    MemoryEvidence,
    MemoryRetrievalQuery,
    MemoryRetriever,
    MemoryScope,
    MemoryStore,
)
from aico.core.models import IncomingMessage, MessageContent
from aico.core.project_assignment import ProjectAssignmentDirectory, ProjectProfile
from aico.core.session_commands import session_scope


class MemoryCommandHandler:
    """Expose project-scoped memory without making the boss curate storage internals."""

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

    async def handle_remember(self, message: IncomingMessage, claim: str) -> None:
        project = await self._active_project_or_reply(message)
        if project is None:
            return
        if self._memory_store is None:
            await self._send_memory_not_configured(message)
            return
        if not claim.strip():
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /remember <fact>"),
            )
            return

        atom = self._memory_store.append_atom(
            MemoryAtom(
                memory_id=f"mem-{uuid4().hex[:12]}",
                claim=claim.strip(),
                evidence=(
                    MemoryEvidence(
                        ref=message.raw_ref,
                        source=message.channel_name,
                        captured_at=message.timestamp,
                        note="manual /remember command",
                    ),
                ),
                scope=MemoryScope.project(project.id),
                source="boss_remember_command",
                confidence=1.0,
                created_by=message.sender_id,
                tags=("manual", "project"),
                reason="Manual /remember command",
            )
        )
        await self._channel.send_message(
            message.source,
            MessageContent(
                text=(
                    "Memory remembered\n"
                    f"id: {atom.memory_id}\n"
                    f"scope: {_scope_label(atom.scope)}\n"
                    f"project: {project.id}\n\n"
                    "Next:\n"
                    "- /recall <query>\n"
                    f"- /forget {atom.memory_id}"
                )
            ),
        )

    async def handle_recall(self, message: IncomingMessage, query: str) -> None:
        project = await self._active_project_or_reply(message)
        if project is None:
            return
        if self._memory_store is None:
            await self._send_memory_not_configured(message)
            return

        hits = MemoryRetriever(self._memory_store).retrieve(
            MemoryRetrievalQuery(
                scopes=(MemoryScope.project(project.id),),
                query=query.strip(),
                top_k=20,
                max_tokens=2_000,
            )
        )
        if not hits:
            await self._channel.send_message(
                message.source,
                MessageContent(
                    text=f"No memories found for {project.id}.\n\nNext:\n- /remember <fact>"
                ),
            )
            return

        lines = [f"Memories: {project.id}"]
        if query.strip():
            lines.append(f"query: {query.strip()}")
        for hit in hits:
            atom = hit.atom
            evidence = atom.evidence[0]
            lines.extend(
                (
                    f"- {atom.memory_id} | confidence: {atom.confidence:.2f} "
                    f"| scope: {_scope_label(atom.scope)}",
                    f"  {atom.claim}",
                    f"  reason: {hit.reason}",
                    "  score: "
                    f"final={hit.final_score:.2f} "
                    f"semantic={hit.semantic_score:.2f} "
                    f"scope={hit.scope_score:.2f} "
                    f"graph={hit.graph_score:.2f}",
                    f"  source: {atom.source} | evidence: {evidence.source}:{evidence.ref}",
                )
            )
        lines.extend(("", "Next:", "- /remember <fact>", "- /forget <memory_id>"))
        await self._channel.send_message(message.source, MessageContent(text="\n".join(lines)))

    async def handle_forget(self, message: IncomingMessage, memory_id: str) -> None:
        project = await self._active_project_or_reply(message)
        if project is None:
            return
        if self._memory_store is None:
            await self._send_memory_not_configured(message)
            return
        if not memory_id.strip():
            await self._channel.send_message(
                message.source,
                MessageContent(text="Usage: /forget <memory_id>"),
            )
            return

        memory_ref = memory_id.strip()
        scope = MemoryScope.project(project.id)
        if not any(
            atom.memory_id == memory_ref
            for atom in self._memory_store.list_atoms(scope, include_archived=True)
        ):
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Memory not found in active project: {memory_ref}"),
            )
            return
        try:
            atom = self._memory_store.archive(
                memory_ref,
                reason=f"forgotten by {message.sender_id}",
            )
        except KeyError:
            await self._channel.send_message(
                message.source,
                MessageContent(text=f"Memory not found in active project: {memory_ref}"),
            )
            return
        await self._channel.send_message(
            message.source,
            MessageContent(
                text=f"Memory archived\nid: {atom.memory_id}\nscope: {_scope_label(atom.scope)}"
            ),
        )

    async def _active_project_or_reply(self, message: IncomingMessage) -> ProjectProfile | None:
        project = self._project_directory.active_project(session_scope(message))
        if project is not None:
            return project
        await self._channel.send_message(
            message.source,
            MessageContent(text="No active project. Use /project <project> first."),
        )
        return None

    async def _send_memory_not_configured(self, message: IncomingMessage) -> None:
        await self._channel.send_message(
            message.source,
            MessageContent(
                text=(
                    "Shared memory is not enabled for this running AICO process.\n\n"
                    "Set AICO_MEMORY_PATH before starting aico-phase1, then restart it:\n"
                    'export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"\n\n'
                    "After restart:\n"
                    "- /use project <project>\n"
                    "- /remember <fact>"
                )
            ),
        )


def _scope_label(scope: MemoryScope) -> str:
    return f"{scope.owner_type.value}:{scope.owner_id}"
