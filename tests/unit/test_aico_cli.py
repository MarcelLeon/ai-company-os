from __future__ import annotations

import io
import stat
from pathlib import Path

from aico.app.cli import run_aico_cli
from aico.channel.telegram import TelegramAPIError


def test_init_writes_owner_only_minimal_telegram_config(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    output = io.StringIO()
    answers = iter((str(repo), "", "yes"))
    discoveries: list[tuple[str, str]] = []

    def discover(token: str, command: str) -> tuple[str, str]:
        discoveries.append((token, command))
        return "owner-123", "chat-456"

    exit_code = run_aico_cli(
        ["init", "--repo", str(repo)],
        stdout=output,
        stderr=io.StringIO(),
        input_fn=lambda _prompt: next(answers),
        secret_fn=lambda _prompt: "123456789:telegram-test-token-value-abcdef",
        identity_discoverer=discover,
    )

    env_path = repo / ".env"
    env_text = env_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert stat.S_IMODE(env_path.stat().st_mode) == 0o600
    assert "AICO_TELEGRAM_BOT_TOKEN=123456789:telegram-test-token-value-abcdef" in env_text
    assert "AICO_OWNER_SENDER_IDS=owner-123" in env_text
    assert "AICO_TRUSTED_TARGET_IDS=chat-456" in env_text
    assert "AICO_ENABLE_CODEX_ADAPTER=true" in env_text
    assert "AICO_ABSENCE_ADMISSION_MODE=optional" in env_text
    assert "AICO_RUNTIME_LIVENESS_ENABLED" not in env_text
    assert "Created owner-only AICO config" in output.getvalue()
    assert "Dead-Man Receiver is optional" in output.getvalue()
    assert discoveries[0][0] == "123456789:telegram-test-token-value-abcdef"
    assert discoveries[0][1].startswith("/help AICO-setup-")


def test_init_refuses_to_overwrite_existing_env(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    env_path = repo / ".env"
    env_path.write_text("existing=true\n", encoding="utf-8")
    error = io.StringIO()

    exit_code = run_aico_cli(
        ["init", "--repo", str(repo)],
        stdout=io.StringIO(),
        stderr=error,
        input_fn=lambda _prompt: "unused",
        secret_fn=lambda _prompt: "unused",
    )

    assert exit_code == 2
    assert env_path.read_text(encoding="utf-8") == "existing=true\n"
    assert "already exists" in error.getvalue()


def test_init_rejects_invalid_ingress_without_exposing_token(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    error = io.StringIO()
    token = "123456789:telegram-test-token-value-abcdef"
    answers = iter((str(repo), "yes"))

    exit_code = run_aico_cli(
        ["init", "--repo", str(repo)],
        stdout=io.StringIO(),
        stderr=error,
        input_fn=lambda _prompt: next(answers),
        secret_fn=lambda _prompt: token,
        identity_discoverer=lambda _token, _command: ("replace-with-owner", "chat-456"),
    )

    assert exit_code == 2
    assert not (repo / ".env").exists()
    assert "identity" in error.getvalue().casefold()
    assert token not in error.getvalue()


def test_init_accepts_explicit_identity_pair_without_discovery(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    answers = iter((str(repo), "no"))

    exit_code = run_aico_cli(
        [
            "init",
            "--repo",
            str(repo),
            "--owner-id",
            "owner-manual",
            "--chat-id",
            "chat-manual",
        ],
        input_fn=lambda _prompt: next(answers),
        secret_fn=lambda _prompt: "123456789:telegram-test-token-value-abcdef",
        identity_discoverer=lambda _token, _command: (_ for _ in ()).throw(AssertionError()),
    )

    assert exit_code == 0
    env_text = (repo / ".env").read_text(encoding="utf-8")
    assert "AICO_OWNER_SENDER_IDS=owner-manual" in env_text
    assert "AICO_TRUSTED_TARGET_IDS=chat-manual" in env_text
    assert "AICO_ENABLE_CODEX_ADAPTER=false" in env_text


def test_init_pairing_failure_is_actionable_and_does_not_create_env(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    error = io.StringIO()
    answers = iter((str(repo), ""))

    exit_code = run_aico_cli(
        ["init", "--repo", str(repo)],
        stdout=io.StringIO(),
        stderr=error,
        input_fn=lambda _prompt: next(answers),
        secret_fn=lambda _prompt: "123456789:telegram-test-token-value-abcdef",
        identity_discoverer=lambda _token, _command: (_ for _ in ()).throw(
            TelegramAPIError("private detail")
        ),
    )

    assert exit_code == 2
    assert not (repo / ".env").exists()
    assert "account can message the bot" in error.getvalue()
    assert "other bot poller" in error.getvalue()
    assert "private detail" not in error.getvalue()


def test_demo_prints_transcript_from_existing_demo_runner() -> None:
    output = io.StringIO()

    exit_code = run_aico_cli(
        ["demo"],
        stdout=output,
        stderr=io.StringIO(),
        demo_runner=lambda: "Boss:\n/help\nAICO:\nready",
    )

    assert exit_code == 0
    assert output.getvalue() == "Boss:\n/help\nAICO:\nready\n"


def test_doctor_and_service_delegate_to_existing_service_contract(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    calls: list[tuple[str, ...]] = []

    def service_runner(argv: tuple[str, ...]) -> int:
        calls.append(argv)
        return 7

    assert run_aico_cli(["doctor", "--repo", str(repo)], service_runner=service_runner) == 7
    assert (
        run_aico_cli(["service", "install", "--repo", str(repo)], service_runner=service_runner)
        == 7
    )
    assert calls == [
        ("--repo", str(repo.resolve()), "doctor"),
        ("--repo", str(repo.resolve()), "install"),
    ]


def test_run_delegates_to_existing_phase1_runtime() -> None:
    calls: list[str] = []

    def runtime_runner() -> int:
        calls.append("run")
        return 0

    exit_code = run_aico_cli(["run"], runtime_runner=runtime_runner)

    assert exit_code == 0
    assert calls == ["run"]


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    (repo / "config/personas.example.json").write_text("{}\n", encoding="utf-8")
    (repo / "config/projects.example.json").write_text("{}\n", encoding="utf-8")
    return repo
