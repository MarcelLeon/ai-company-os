from aico.adapter.codex import DEFAULT_CODEX_COMMAND, CodexAdapter
from aico.core import Capability


def test_codex_adapter_uses_safe_non_interactive_defaults() -> None:
    adapter = CodexAdapter()

    assert adapter.name == "codex"
    assert DEFAULT_CODEX_COMMAND == (
        "codex",
        "--ask-for-approval",
        "never",
        "exec",
        "--sandbox",
        "read-only",
        "--color",
        "never",
    )
    assert adapter.capabilities() == frozenset(
        {
            Capability.CODE_REVIEW,
            Capability.LONG_RUNNING,
            Capability.STREAM_OUTPUT,
            Capability.INTERRUPTIBLE,
        }
    )
