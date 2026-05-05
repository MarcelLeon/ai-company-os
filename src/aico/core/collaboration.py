"""Parse lightweight persona-to-persona collaboration directives."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CollaborationDirective:
    target_persona: str
    payload: str


def parse_collaboration_directive(text: str) -> CollaborationDirective | None:
    line = _first_non_empty_line(text)
    if line is None or not line.startswith("@"):
        return None

    target, payload = _split_directive(line[1:])
    if target is None or payload is None:
        return None
    target = target.strip()
    payload = payload.strip()
    if not target or not payload or not _is_persona_name(target):
        return None
    return CollaborationDirective(target_persona=target, payload=payload)


def collaboration_payload(source_persona: str, payload: str) -> str:
    return f"Collaboration request from {source_persona}:\n\n{payload}"


def _first_non_empty_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


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
