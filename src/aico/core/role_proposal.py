"""Build and parse LLM-assisted project role proposals."""

from __future__ import annotations

import json
import re
from typing import Any

from aico.core.project_assignment import ProjectProfile, RoleProfile

ROLE_PROPOSAL_INTENT = "role_proposal"
ROLE_PROPOSAL_INTENT_KEY = "aico.intent"


def role_proposal_prompt(project: ProjectProfile, request: str) -> str:
    """Ask a provider to draft one role as machine-readable JSON."""
    return (
        "Draft one project role for the boss to review.\n"
        f"Project: {project.id} [{project.name}]\n"
        f"Need: {request.strip()}\n\n"
        "Return only one JSON object with these keys:\n"
        '- "id": lowercase kebab-case role id\n'
        '- "title": short human title\n'
        '- "summary": one sentence responsibility summary\n'
        '- "default_permissions": array of permission tokens\n'
        '- "approval_required": array of risky permission tokens\n'
        '- "inline_prompt": concise instruction for the appointed agent\n'
        "Keep permissions concrete, for example read_repo, read_docs, write_docs, "
        "write_code, run_tests, read_audit."
    )


def role_from_llm_output(output: str, request: str) -> RoleProfile:
    data = _json_object(output)
    title = _required_text(data, "title")
    summary = _required_text(data, "summary")
    role_id = _role_id(str(data.get("id") or title or request))
    inline_prompt = _optional_text(data.get("inline_prompt"))
    return RoleProfile(
        id=role_id,
        title=title,
        summary=summary,
        default_permissions=_string_tuple(data.get("default_permissions")),
        approval_required=_string_tuple(data.get("approval_required")),
        inline_prompt=inline_prompt,
    )


def _json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("role draft did not include a JSON object")
    value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("role draft JSON must be an object")
    return value


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"role draft missing {key}")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    tokens: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            tokens.append(item.strip())
    return tuple(tokens)


def _role_id(value: str) -> str:
    lowered = value.strip().lower().replace("_", "-")
    normalized = re.sub(r"[^a-z0-9-]+", "-", lowered)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "custom-role"
