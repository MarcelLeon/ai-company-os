"""Parse lightweight persona-to-persona collaboration directives."""

from __future__ import annotations

from dataclasses import dataclass

from aico.core.models import MetadataEntry, Task

COLLABORATION_MODE_METADATA_KEY = "aico.collaboration_mode"
COLLABORATION_DISABLED = "disabled"


@dataclass(frozen=True)
class CollaborationDirective:
    target_persona: str
    payload: str


def parse_collaboration_directive(text: str) -> CollaborationDirective | None:
    directive, _ = split_collaboration_directive(text)
    return directive


def split_collaboration_directive(
    text: str,
) -> tuple[CollaborationDirective | None, str]:
    kept_lines: list[str] = []
    directive: CollaborationDirective | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if directive is None and stripped.startswith("@"):
            target, payload = _split_directive(stripped[1:])
            if target is not None and payload is not None:
                target = target.strip()
                payload = payload.strip()
                if target and payload and _is_persona_name(target):
                    directive = CollaborationDirective(target_persona=target, payload=payload)
                    continue
        kept_lines.append(line)
    return directive, "\n".join(kept_lines)


def collaboration_payload(
    source_persona: str,
    payload: str,
    *,
    memory_refs: tuple[str, ...] = (),
    source_context: str | None = None,
    use_memory_refs: bool = False,
) -> str:
    context = _trim_source_context(source_context)
    if not context:
        if use_memory_refs and memory_refs:
            return (
                f"Collaboration request from {source_persona}:\n\n"
                f"Memory refs: {', '.join(memory_refs)}\n"
                "Delta:\n"
                f"{payload}"
            )
        return f"Collaboration request from {source_persona}:\n\n{payload}"

    if use_memory_refs and memory_refs:
        text = (
            f"Collaboration request from {source_persona}:\n\n"
            f"Memory refs: {', '.join(memory_refs)}\n"
        )
    else:
        text = f"Collaboration request from {source_persona}:\n\n"

    if context:
        text += f"Context from {source_persona} output so far:\n{context}\n\n"

    return f"{text}Current task:\n{payload}"


def exact_output_requested(text: str) -> bool:
    """Return whether the boss explicitly requested a one-shot, non-delegating answer."""
    normalized = text.casefold()
    return any(marker in normalized for marker in _EXACT_OUTPUT_MARKERS)


def task_with_exact_output_constraint(task: Task) -> Task:
    """Make exact-output behavior durable across prompt execution and stream parsing."""
    metadata = tuple(
        entry for entry in task.metadata if entry.key != COLLABORATION_MODE_METADATA_KEY
    )
    constrained_payload = (
        f"{task.payload}\n\n"
        "Exact-output constraint:\n"
        "- Answer only the current request and preserve its requested output shape.\n"
        "- Do not delegate, request collaboration, or emit @role directives."
    )
    return task.model_copy(
        update={
            "payload": constrained_payload,
            "metadata": (
                *metadata,
                MetadataEntry(
                    key=COLLABORATION_MODE_METADATA_KEY,
                    value=COLLABORATION_DISABLED,
                ),
            ),
        }
    )


def collaboration_disabled(task: Task) -> bool:
    return any(
        entry.key == COLLABORATION_MODE_METADATA_KEY and entry.value == COLLABORATION_DISABLED
        for entry in task.metadata
    )


_SOURCE_CONTEXT_LIMIT = 4000
_EXACT_OUTPUT_MARKERS = (
    "不要请求协作",
    "不要协作",
    "不要 @",
    "不要@",
    "只输出本条",
    "只返回本条",
    "no-collab",
    "no collaboration",
    "do not request collaboration",
    "do not delegate",
    "exact-output",
)


def _trim_source_context(source_context: str | None) -> str:
    if source_context is None:
        return ""
    context = source_context.strip()
    if len(context) <= _SOURCE_CONTEXT_LIMIT:
        return context
    return f"...\n{context[-_SOURCE_CONTEXT_LIMIT:]}"


def _is_persona_name(value: str) -> bool:
    return all(char.isalnum() or char in {"-", "_"} for char in value)


def _split_directive(text: str) -> tuple[str | None, str | None]:
    target, separator, payload = text.partition(":")
    if separator:
        return target, payload

    target, separator, payload = text.partition(" ")
    if separator:
        return target, payload
    return None, None
