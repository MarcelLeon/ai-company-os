"""ExperienceCommandHandler + prompt injection integration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from aico.core import (
    ExperienceMeta,
    JsonlMemoryStore,
    MemoryAtom,
    MemoryEvidence,
    MemoryKind,
    MemoryScope,
    MemoryStatus,
    MessageContent,
    MessageKind,
)
from aico.core.experience_commands import ExperienceCommandHandler
from aico.core.models import ChannelTarget, IncomingMessage
from aico.core.project_assignment import (
    AssignmentProfile,
    CompanyAgentProfile,
    ProjectAssignmentConfig,
    ProjectAssignmentDirectory,
    ProjectProfile,
    ProjectRoleProfile,
    RoleProfile,
)
from aico.core.session_commands import session_scope

pytestmark = pytest.mark.asyncio


class _RecordingChannel:
    name = "telegram"

    def __init__(self) -> None:
        self.sent: list[MessageContent] = []

    async def send_message(self, target: ChannelTarget, content: MessageContent) -> MessageContent:
        del target
        self.sent.append(content)
        return content

    async def edit_message(
        self,
        target: ChannelTarget,
        message_id: str,
        content: MessageContent,
    ) -> MessageContent:
        del target, message_id
        self.sent.append(content)
        return content


def _incoming(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="boss-1",
        mentions=(),
        content=MessageContent(kind=MessageKind.TEXT, text=text),
        timestamp=datetime(2026, 5, 31, 9, 0, tzinfo=UTC),
        raw_ref="raw-1",
    )


def _project_directory() -> ProjectAssignmentDirectory:
    return ProjectAssignmentDirectory(
        ProjectAssignmentConfig(
            agents={
                "claude": CompanyAgentProfile(
                    id="claude",
                    provider="claude-code",
                    title="Senior Implementer",
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
                    repo="/repo/aico",
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
                    permissions=("code", "tests", "docs"),
                ),
            ),
        )
    )


def _candidate_atom(memory_id: str, *, triggers: tuple[str, ...] = ()) -> MemoryAtom:
    return MemoryAtom(
        memory_id=memory_id,
        claim="Retry adapter with verbose logging after idle timeout.",
        evidence=(MemoryEvidence(ref=f"task:{memory_id}", source="dream_review"),),
        scope=MemoryScope.project("aico"),
        source="dream_review",
        confidence=0.6,
        created_by="lead-agent",
        status=MemoryStatus.CANDIDATE,
        kind=MemoryKind.EXPERIENCE,
        experience=ExperienceMeta(triggers=triggers),
    )


def _make_handler(
    tmp_path: Path,
) -> tuple[ExperienceCommandHandler, _RecordingChannel, JsonlMemoryStore]:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    channel = _RecordingChannel()
    directory = _project_directory()
    handler = ExperienceCommandHandler(
        channel=channel,  # type: ignore[arg-type]
        project_directory=directory,
        memory_store=store,
    )
    scope = session_scope(_incoming("/experience review"))
    directory.set_active_project(scope, "aico")
    return handler, channel, store


async def test_experience_review_lists_only_candidates(tmp_path: Path) -> None:
    handler, channel, store = _make_handler(tmp_path)
    store.append_atom(_candidate_atom("mem-cand-1", triggers=("adapter_idle",)))
    store.promote_experience("mem-cand-1", applies_to=("implementer",))
    store.append_atom(_candidate_atom("mem-cand-2"))

    await handler.handle_experience(_incoming("/experience review"), "")

    assert channel.sent
    body = channel.sent[-1].text
    assert "Experience review: aico" in body
    assert "mem-cand-2" in body
    assert "mem-cand-1" not in body


async def test_experience_promote_marks_active_and_records_applies_to(tmp_path: Path) -> None:
    handler, channel, store = _make_handler(tmp_path)
    store.append_atom(_candidate_atom("mem-cand-3", triggers=("adapter_idle",)))

    await handler.handle_experience(
        _incoming("/experience promote mem-cand-3 as implementer,tester"),
        "promote mem-cand-3 as implementer,tester",
    )

    promoted = store.get_atom("mem-cand-3")
    assert promoted is not None
    assert promoted.status is MemoryStatus.ACTIVE
    assert promoted.experience is not None
    assert promoted.experience.applies_to == ("implementer", "tester")
    body = channel.sent[-1].text
    assert "Experience promoted" in body
    assert "applies_to: implementer, tester" in body


async def test_experience_archive_marks_archived(tmp_path: Path) -> None:
    handler, channel, store = _make_handler(tmp_path)
    store.append_atom(_candidate_atom("mem-cand-4"))
    store.promote_experience("mem-cand-4", applies_to=("implementer",))

    await handler.handle_experience(
        _incoming("/experience archive mem-cand-4"), "archive mem-cand-4"
    )

    archived = store.get_atom("mem-cand-4")
    assert archived is not None
    assert archived.status is MemoryStatus.ARCHIVED
    assert "Experience archived" in channel.sent[-1].text


async def test_experience_promote_rejects_fact_kind(tmp_path: Path) -> None:
    handler, channel, store = _make_handler(tmp_path)
    store.append_atom(
        MemoryAtom(
            memory_id="mem-fact-1",
            claim="Boss prefers concise reports.",
            evidence=(MemoryEvidence(ref="raw:1", source="boss_remember_command"),),
            scope=MemoryScope.project("aico"),
            source="boss_remember_command",
            confidence=1.0,
            created_by="boss-1",
        )
    )

    await handler.handle_experience(
        _incoming("/experience promote mem-fact-1"), "promote mem-fact-1"
    )

    body = channel.sent[-1].text
    assert "kind=fact" in body
    atom: Any = store.get_atom("mem-fact-1")
    assert atom is not None
    assert atom.status is MemoryStatus.ACTIVE


async def test_experience_list_filters_by_role_and_orders_by_confidence(tmp_path: Path) -> None:
    handler, channel, store = _make_handler(tmp_path)
    high = _candidate_atom("mem-high").model_copy(update={"confidence": 0.9})
    low = _candidate_atom("mem-low").model_copy(update={"confidence": 0.4})
    store.append_atom(high)
    store.append_atom(low)
    store.promote_experience("mem-high", applies_to=("implementer",))
    store.promote_experience("mem-low", applies_to=("tester",))

    await handler.handle_experience(_incoming("/experience list implementer"), "list implementer")

    body = channel.sent[-1].text
    assert "mem-high" in body
    assert "mem-low" not in body
