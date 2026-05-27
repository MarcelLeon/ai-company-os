from pathlib import Path

from aico.core import (
    ChannelTarget,
    JsonlMemoryStore,
    MemoryPurpose,
    MemoryScope,
    MemoryStatus,
    MessageContent,
)
from aico.core.memory_capture import MemoryCaptureService
from aico.core.models import IncomingMessage
from aico.core.project_assignment import ProjectProfile


def test_memory_capture_records_project_feedback_when_project_is_explicit(
    tmp_path: Path,
) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    service = MemoryCaptureService(store)
    project = ProjectProfile(id="aico", name="AI Company OS", repo="/repo/aico")

    captured = service.capture_boss_feedback(
        _incoming_message("以后这个项目汇报进度一定要告诉我还剩几阶段"),
        active_project=project,
    )

    assert len(captured) == 1
    atom = captured[0]
    assert atom.scope == MemoryScope.project("aico")
    assert atom.status is MemoryStatus.ACTIVE
    assert atom.source == "boss_feedback_capture"
    assert atom.created_by == "boss-1"
    assert atom.purpose_tags == (MemoryPurpose.GENERAL_CONTEXT,)
    assert "以后这个项目汇报进度一定要告诉我还剩几阶段" in atom.claim
    assert atom.reason == "boss feedback captured from explicit project context"
    assert store.list_atoms(MemoryScope.project("aico")) == (atom,)


def test_memory_capture_records_global_boss_preference_without_project_context(
    tmp_path: Path,
) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    service = MemoryCaptureService(store)

    captured = service.capture_boss_feedback(
        _incoming_message("我更喜欢汇报进度时告诉我还有几阶段"),
        active_project=None,
    )

    assert len(captured) == 1
    atom = captured[0]
    assert atom.scope == MemoryScope.boss("boss-1")
    assert atom.status is MemoryStatus.ACTIVE
    assert atom.tags == ("boss-feedback", "boss-preference")
    assert store.list_atoms(MemoryScope.boss("boss-1")) == (atom,)


def test_memory_capture_marks_uncertain_feedback_as_candidate(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    service = MemoryCaptureService(store)
    project = ProjectProfile(id="aico", name="AI Company OS", repo="/repo/aico")

    captured = service.capture_boss_feedback(
        _incoming_message("这个项目我可能更喜欢先少写一点状态汇总"),
        active_project=project,
    )

    assert len(captured) == 1
    atom = captured[0]
    assert atom.scope == MemoryScope.project("aico")
    assert atom.status is MemoryStatus.CANDIDATE
    assert atom.confidence == 0.55
    assert atom.reason == "candidate: uncertain boss feedback"


def test_memory_capture_ignores_plain_task_text(tmp_path: Path) -> None:
    store = JsonlMemoryStore(tmp_path / "memory.jsonl")
    service = MemoryCaptureService(store)

    captured = service.capture_boss_feedback(
        _incoming_message("继续推进 Phase 7"),
        active_project=None,
    )

    assert captured == ()
    assert store.list_atoms(MemoryScope.boss("boss-1")) == ()


def _incoming_message(text: str) -> IncomingMessage:
    return IncomingMessage(
        channel_name="telegram",
        source=ChannelTarget(channel_name="telegram", target_id="chat-1"),
        sender_id="boss-1",
        mentions=(),
        content=MessageContent(text=text),
        raw_ref="message-1",
    )
