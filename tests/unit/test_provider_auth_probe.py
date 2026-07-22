from __future__ import annotations

import json
from pathlib import Path

import pytest

from aico.app.provider_auth_probe import (
    CliProviderAuthenticationProbe,
    ProviderAuthenticationProbeError,
    _parse_claude_result,
    _parse_codex_result,
    _probe_command,
    build_cli_provider_probe,
)


def test_claude_and_codex_parsers_require_exact_challenge_and_usage() -> None:
    challenge = "aico-auth-v1-" + "a" * 48
    claude = json.dumps(
        {"result": challenge, "is_error": False, "usage": {"input_tokens": 9}}
    ).encode()
    codex = b"\n".join(
        (
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": challenge},
                }
            ).encode(),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 9}}).encode(),
        )
    )

    assert _parse_claude_result(claude, challenge) is True
    assert _parse_codex_result(codex, challenge) is True
    assert _parse_claude_result(claude.replace(challenge.encode(), b"wrong"), challenge) is False
    assert (
        _parse_codex_result(codex.replace(b'"input_tokens": 9', b'"input_tokens": 0'), challenge)
        is False
    )


def test_probe_commands_disable_tools_sessions_writes_and_user_rules() -> None:
    challenge = "aico-auth-v1-" + "b" * 48

    claude = _probe_command("claude-code", "claude", challenge)
    codex = _probe_command("codex", "codex", challenge)

    assert ("--tools", "") == claude[claude.index("--tools") : claude.index("--tools") + 2]
    assert "--safe-mode" in claude
    assert "--no-session-persistence" in claude
    assert "--no-chrome" in claude
    assert "--sandbox" in codex and "read-only" in codex
    assert "--ignore-user-config" in codex
    assert "--ignore-rules" in codex
    assert "-c" not in codex
    assert challenge in claude[-1] and challenge in codex[-1]


def test_probe_rejects_wrappers_and_unapproved_providers() -> None:
    with pytest.raises(ProviderAuthenticationProbeError, match="executable"):
        CliProviderAuthenticationProbe("claude-code", "wrapper claude")
    with pytest.raises(ProviderAuthenticationProbeError, match="no approved"):
        build_cli_provider_probe("cursor", "cursor-agent")


def test_cli_probe_runs_in_private_directory_and_strips_aico_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "claude"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, pathlib, sys\n"
        "prompt = sys.argv[-1]\n"
        "challenge = prompt.splitlines()[-1]\n"
        "ok = 'AICO_PRIVATE_TEST_VALUE' not in os.environ\n"
        "ok = ok and pathlib.Path.cwd().name.startswith('aico-provider-auth-')\n"
        "print(json.dumps({'result': challenge if ok else 'unsafe', "
        "'is_error': False, 'usage': {'input_tokens': 1}}))\n"
    )
    executable.chmod(0o700)
    monkeypatch.setenv("AICO_PRIVATE_TEST_VALUE", "must-not-reach-child")
    challenge = "aico-auth-v1-" + "c" * 48

    result = CliProviderAuthenticationProbe("claude-code", str(executable)).execute(challenge)

    assert result.terminal_success is True
    assert result.exact_challenge_response is True
    assert result.usage_observed is True


@pytest.mark.parametrize(
    ("body", "timeout", "message"),
    (
        ("import time\ntime.sleep(2)\n", 0.03, "timed out"),
        ("import sys\nsys.stdout.write('x' * 300000)\n", 2.0, "exceeded limit"),
    ),
)
def test_cli_probe_bounds_runtime_and_output(
    tmp_path: Path,
    body: str,
    timeout: float,
    message: str,
) -> None:
    executable = tmp_path / "claude"
    executable.write_text("#!/usr/bin/env python3\n" + body)
    executable.chmod(0o700)
    challenge = "aico-auth-v1-" + "f" * 48

    with pytest.raises(ProviderAuthenticationProbeError, match=message):
        CliProviderAuthenticationProbe(
            "claude-code",
            str(executable),
            timeout_seconds=timeout,
        ).execute(challenge)
