"""Scoped agent response language preferences."""

from __future__ import annotations

from dataclasses import dataclass

from aico.core.message_rendering import rich_text_message
from aico.core.models import MessageContent, MetadataEntry, Task

RESPONSE_LANGUAGE_METADATA_KEY = "aico.response_language"
DEFAULT_LANGUAGE_CODE = "en"


@dataclass(frozen=True)
class ResponseLanguage:
    code: str
    label: str
    instruction: str
    is_default: bool = False


class ResponseLanguageStore:
    """In-memory language preference by IM session scope."""

    def __init__(self) -> None:
        self._languages_by_scope: dict[str, ResponseLanguage] = {}

    def current(self, scope_id: str) -> ResponseLanguage:
        return self._languages_by_scope.get(scope_id, DEFAULT_RESPONSE_LANGUAGE)

    def set_language(self, scope_id: str, language: ResponseLanguage) -> None:
        if language.is_default:
            self._languages_by_scope.pop(scope_id, None)
            return
        self._languages_by_scope[scope_id] = language


def parse_response_language(payload: str) -> ResponseLanguage | None:
    normalized = _normalize_language_ref(payload)
    if not normalized:
        return None
    return _LANGUAGE_ALIASES.get(normalized)


def language_message(
    *,
    current: ResponseLanguage,
    updated: bool = False,
) -> MessageContent:
    title = "Agent response language updated" if updated else "Agent response language"
    return rich_text_message(
        "\n".join(
            (
                f"# {title}",
                f"current: {current.label}",
                "default: English",
                "",
                "Effect:",
                "- Future agent tasks in this chat will use this reply language.",
                "- Built-in AICO command text, code, commands, paths, logs, and identifiers "
                "stay unchanged.",
                "",
                "Usage:",
                "- /language zh",
                "- /language en",
            )
        )
    )


def language_usage_message() -> MessageContent:
    return rich_text_message(
        "\n".join(
            (
                "# Unsupported language",
                "Usage:",
                "- /language zh",
                "- /language en",
            )
        )
    )


def task_with_response_language(task: Task, language: ResponseLanguage) -> Task:
    if language.is_default or _metadata_value(task, RESPONSE_LANGUAGE_METADATA_KEY) is not None:
        return task
    return task.model_copy(
        update={
            "payload": f"{language.instruction}\n\n{task.payload}",
            "metadata": (
                *task.metadata,
                MetadataEntry(key=RESPONSE_LANGUAGE_METADATA_KEY, value=language.code),
            ),
        }
    )


def _metadata_value(task: Task, key: str) -> object | None:
    for entry in task.metadata:
        if entry.key == key:
            return entry.value
    return None


def _normalize_language_ref(value: str) -> str:
    return value.strip().casefold().replace("_", "-")


DEFAULT_RESPONSE_LANGUAGE = ResponseLanguage(
    code=DEFAULT_LANGUAGE_CODE,
    label="English",
    instruction="",
    is_default=True,
)

ZH_CN_RESPONSE_LANGUAGE = ResponseLanguage(
    code="zh",
    label="Simplified Chinese",
    instruction=(
        "Response language:\n"
        "- Reply to the boss in Simplified Chinese.\n"
        "- Keep code blocks, CLI snippets, file paths, logs, identifiers, protocol keywords, "
        "and quoted source text unchanged.\n"
        "- If the task requires strict JSON or another machine-readable schema, keep that "
        "schema exactly."
    ),
)

_LANGUAGE_ALIASES: dict[str, ResponseLanguage] = {
    "en": DEFAULT_RESPONSE_LANGUAGE,
    "english": DEFAULT_RESPONSE_LANGUAGE,
    "default": DEFAULT_RESPONSE_LANGUAGE,
    "reset": DEFAULT_RESPONSE_LANGUAGE,
    "zh": ZH_CN_RESPONSE_LANGUAGE,
    "zh-cn": ZH_CN_RESPONSE_LANGUAGE,
    "cn": ZH_CN_RESPONSE_LANGUAGE,
    "chinese": ZH_CN_RESPONSE_LANGUAGE,
    "simplified chinese": ZH_CN_RESPONSE_LANGUAGE,
    "中文": ZH_CN_RESPONSE_LANGUAGE,
    "汉语": ZH_CN_RESPONSE_LANGUAGE,
    "简体中文": ZH_CN_RESPONSE_LANGUAGE,
}
