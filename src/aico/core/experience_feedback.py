"""Apply grader verdicts to experiences that influenced the graded task.

The grader does not directly touch experience storage; this module bridges
between:
  - the owner Task (the one being graded) which carries
    `aico.injected_experience_ids` metadata written by orchestrator_task_factory
  - the grader output text (parsed via outcome_grader.parse_verdict)
  - MemoryStore.update_experience_meta(...) which is the only side-effect path

Keeping this glue out of TaskBus / Orchestrator preserves the discipline that
core orchestration code does not know about experience semantics.
"""

from __future__ import annotations

import logging

from aico.core.memory import MemoryAtom, MemoryStore
from aico.core.models import Task
from aico.core.orchestrator_task_factory import INJECTED_EXPERIENCE_IDS_KEY
from aico.core.outcome_grader import GraderVerdict

logger = logging.getLogger(__name__)


_CONFIDENCE_DELTA_BY_VERDICT: dict[GraderVerdict, float] = {
    GraderVerdict.PASS: 0.05,
    GraderVerdict.PARTIAL: 0.0,
    GraderVerdict.FAIL: -0.10,
}


def injected_experience_ids(task: Task) -> tuple[str, ...]:
    """Read memory_ids written by orchestrator_task_factory at task assembly."""
    for entry in task.metadata:
        if entry.key == INJECTED_EXPERIENCE_IDS_KEY and isinstance(entry.value, str):
            return tuple(part.strip() for part in entry.value.split(",") if part.strip())
    return ()


def apply_verdict_to_owner_experiences(
    memory_store: MemoryStore,
    *,
    owner_task: Task,
    verdict: GraderVerdict,
) -> tuple[MemoryAtom, ...]:
    """Adjust confidence and hit/miss counters on experiences used by owner_task.

    Returns the updated atoms (empty when the owner task did not consume any
    experience, or when the verdict does not warrant any change beyond the
    injection counter — which is intentionally NOT bumped here because we only
    want to count *graded* uses, and an injection without a grader is silent.
    """
    memory_ids = injected_experience_ids(owner_task)
    if not memory_ids:
        return ()
    delta = _CONFIDENCE_DELTA_BY_VERDICT.get(verdict, 0.0)
    hits = 1 if verdict in (GraderVerdict.PASS, GraderVerdict.PARTIAL) else 0
    misses = 1 if verdict in (GraderVerdict.PARTIAL, GraderVerdict.FAIL) else 0
    updated: list[MemoryAtom] = []
    for memory_id in memory_ids:
        try:
            atom = memory_store.update_experience_meta(
                memory_id,
                confidence_delta=delta,
                verdict_hits_delta=hits,
                verdict_misses_delta=misses,
                injection_count_delta=1,
            )
        except (KeyError, ValueError) as exc:
            logger.warning(
                "experience feedback skipped memory_id=%s verdict=%s reason=%s",
                memory_id,
                verdict.value,
                exc,
            )
            continue
        updated.append(atom)
    return tuple(updated)
