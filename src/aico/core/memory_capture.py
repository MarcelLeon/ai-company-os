"""Capture boss feedback into shared memory."""

from __future__ import annotations

from uuid import uuid4

from aico.core.memory import (
    MemoryAtom,
    MemoryEvidence,
    MemoryPurpose,
    MemoryScope,
    MemoryStatus,
    MemoryStore,
)
from aico.core.models import IncomingMessage
from aico.core.project_assignment import ProjectProfile

_PREFERENCE_MARKERS = (
    "我更喜欢",
    "更喜欢",
    "我喜欢",
    "我不喜欢",
    "我希望",
    "我的偏好",
    "反馈",
    "一定要",
    "必须",
)
_PROJECT_MARKERS = ("这个项目", "当前项目", "本项目", "项目")
_GLOBAL_MARKERS = ("所有项目", "全局", "以后都", "我个人")
_UNCERTAIN_MARKERS = ("可能", "也许", "不确定", "先看看", "暂时")


class MemoryCaptureService:
    """Turn explicit boss preferences into scoped MemoryAtom records."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def capture_boss_feedback(
        self,
        message: IncomingMessage,
        *,
        active_project: ProjectProfile | None,
    ) -> tuple[MemoryAtom, ...]:
        text = message.content.text.strip()
        if not _looks_like_boss_feedback(text):
            return ()

        scope, scope_reason = _feedback_scope(
            text,
            boss_id=message.sender_id,
            active_project=active_project,
        )
        status, confidence, status_reason = _feedback_status(text)
        atom = self._store.append_atom(
            MemoryAtom(
                memory_id=f"mem-{uuid4().hex[:12]}",
                claim=f"Boss feedback: {text}",
                evidence=(
                    MemoryEvidence(
                        ref=message.raw_ref,
                        source=message.channel_name,
                        captured_at=message.timestamp,
                        note="boss feedback auto-capture",
                    ),
                ),
                scope=scope,
                source="boss_feedback_capture",
                confidence=confidence,
                created_by=message.sender_id,
                status=status,
                tags=("boss-feedback", "boss-preference"),
                purpose_tags=(MemoryPurpose.GENERAL_CONTEXT,),
                reason=status_reason or scope_reason,
            )
        )
        return (atom,)


def _looks_like_boss_feedback(text: str) -> bool:
    if not text:
        return False
    return any(marker in text for marker in _PREFERENCE_MARKERS) or _looks_like_future_rule(text)


def _looks_like_future_rule(text: str) -> bool:
    return "以后" in text and any(rule_word in text for rule_word in ("要", "不要", "别"))


def _feedback_scope(
    text: str,
    *,
    boss_id: str,
    active_project: ProjectProfile | None,
) -> tuple[MemoryScope, str]:
    if any(marker in text for marker in _GLOBAL_MARKERS) or active_project is None:
        return (
            MemoryScope.boss(boss_id),
            "boss feedback captured from global boss context",
        )
    if active_project.id in text or active_project.name in text:
        return (
            MemoryScope.project(active_project.id),
            "boss feedback captured from explicit project context",
        )
    if any(marker in text for marker in _PROJECT_MARKERS):
        return (
            MemoryScope.project(active_project.id),
            "boss feedback captured from explicit project context",
        )
    return (
        MemoryScope.boss(boss_id),
        "boss feedback captured from global boss context",
    )


def _feedback_status(text: str) -> tuple[MemoryStatus, float, str | None]:
    if any(marker in text for marker in _UNCERTAIN_MARKERS):
        return MemoryStatus.CANDIDATE, 0.55, "candidate: uncertain boss feedback"
    if any(marker in text for marker in ("一定要", "必须", "以后")):
        return MemoryStatus.ACTIVE, 0.9, None
    return MemoryStatus.ACTIVE, 0.8, None
