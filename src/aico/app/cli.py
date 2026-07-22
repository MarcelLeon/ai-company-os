"""Single public entrypoint for trying, configuring, and running AICO."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import secrets
import sys
from collections.abc import Callable, Sequence
from contextlib import chdir
from pathlib import Path
from typing import TextIO

import httpx

from aico.app.phase1 import load_phase1_settings, run_phase1
from aico.app.release_room_demo import run_demo
from aico.app.service_cli import run_service_cli
from aico.channel.telegram import TelegramAPIError, TelegramChannel
from aico.core.ingress_authorization import IngressBindingError, parse_ingress_ids

InputFunction = Callable[[str], str]
SecretFunction = Callable[[str], str]
ServiceRunner = Callable[[tuple[str, ...]], int]
TextRunner = Callable[[], str]
RuntimeRunner = Callable[[], int]
IdentityDiscoverer = Callable[[str, str], tuple[str, str]]

_PLACEHOLDER_FRAGMENTS = ("replace-with", "replace-me", "your-", "<", ">")


def run_aico_cli(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    input_fn: InputFunction = input,
    secret_fn: SecretFunction = getpass.getpass,
    service_runner: ServiceRunner | None = None,
    demo_runner: TextRunner | None = None,
    runtime_runner: RuntimeRunner | None = None,
    identity_discoverer: IdentityDiscoverer | None = None,
) -> int:
    """Run the public onboarding facade while reusing authoritative subcommands."""
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    args = _parser().parse_args(argv)
    if args.command == "init":
        return _init(
            args.repo.resolve(),
            stdout=output,
            stderr=error_output,
            input_fn=input_fn,
            secret_fn=secret_fn,
            owner_id=args.owner_id,
            chat_id=args.chat_id,
            identity_discoverer=identity_discoverer or _discover_telegram_identity,
        )
    if args.command == "demo":
        transcript = (demo_runner or _run_demo)()
        output.write(transcript.rstrip() + "\n")
        return 0
    if args.command == "run":
        repo = args.repo.resolve()
        if runtime_runner is not None:
            return runtime_runner()
        with chdir(repo):
            return _run_runtime(stderr=error_output)

    repo = args.repo.resolve()
    delegated = ("--repo", str(repo), args.action if args.command == "service" else "doctor")
    if service_runner is not None:
        return service_runner(delegated)
    return run_service_cli(delegated, stdout=output, stderr=error_output)


def main() -> None:
    raise SystemExit(run_aico_cli())


def _init(
    repo: Path,
    *,
    stdout: TextIO,
    stderr: TextIO,
    input_fn: InputFunction,
    secret_fn: SecretFunction,
    owner_id: str | None,
    chat_id: str | None,
    identity_discoverer: IdentityDiscoverer,
) -> int:
    env_path = repo / ".env"
    if env_path.exists():
        stderr.write(f"AICO config already exists: {env_path}\n")
        return 2
    error = _repo_error(repo)
    if error is not None:
        stderr.write(f"AICO init refused: {error}\n")
        return 2

    try:
        working_directory = _working_directory(input_fn, repo)
        token = _required_secret(secret_fn("Telegram Bot Token (hidden): "))
        owner, target = _telegram_identity(
            token=token,
            owner_id=owner_id,
            chat_id=chat_id,
            stdout=stdout,
            input_fn=input_fn,
            identity_discoverer=identity_discoverer,
        )
        enable_codex = _yes(input_fn("Enable the local Codex adapter? [Y/n]: "))
    except TelegramAPIError:
        stderr.write(
            "AICO init refused: Telegram private-chat pairing failed; verify the account can "
            "message the bot, stop any other bot poller, then retry the exact setup command\n"
        )
        return 2
    except (IngressBindingError, ValueError) as exc:
        stderr.write(f"AICO init refused: {exc}\n")
        return 2

    payload = _minimal_env(
        working_directory=working_directory,
        token=token,
        owner=owner,
        target=target,
        enable_codex=enable_codex,
    )
    try:
        _write_owner_only(env_path, payload)
    except OSError:
        stderr.write("AICO init failed: could not create the local owner-only config\n")
        return 2

    stdout.write(f"Created owner-only AICO config: {env_path}\n")
    stdout.write("Next: uv run aico doctor, then uv run aico run.\n")
    stdout.write(
        "Dead-Man Receiver is optional; add it only for advanced whole-machine outage alerts.\n"
    )
    return 0


def _working_directory(input_fn: InputFunction, repo: Path) -> Path:
    raw = input_fn(f"Agent working directory [{repo}]: ").strip()
    path = Path(raw).expanduser().resolve() if raw else repo
    if not path.is_dir():
        raise ValueError("agent working directory must already exist")
    return path


def _required_secret(value: str) -> str:
    normalized = value.strip().casefold()
    if (
        not value.strip()
        or any(character in value for character in "\r\n")
        or any(fragment in normalized for fragment in _PLACEHOLDER_FRAGMENTS)
    ):
        raise ValueError("Telegram Bot Token is missing or unsafe")
    return value.strip()


def _one_identity(value: str) -> str:
    identities = parse_ingress_ids(value)
    if len(identities) != 1:
        raise IngressBindingError("exactly one IM identity is required during init")
    return identities[0]


def _telegram_identity(
    *,
    token: str,
    owner_id: str | None,
    chat_id: str | None,
    stdout: TextIO,
    input_fn: InputFunction,
    identity_discoverer: IdentityDiscoverer,
) -> tuple[str, str]:
    if (owner_id is None) != (chat_id is None):
        raise ValueError("--owner-id and --chat-id must be provided together")
    if owner_id is not None and chat_id is not None:
        return _one_identity(owner_id), _one_identity(chat_id)

    setup_command = f"/help AICO-setup-{secrets.token_hex(4)}"
    stdout.write("Send this exact command in your private chat with the bot:\n")
    stdout.write(f"  {setup_command}\n")
    input_fn("Press Enter after Telegram shows the sent command: ")
    owner, target = identity_discoverer(token, setup_command)
    return _one_identity(owner), _one_identity(target)


def _yes(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"", "y", "yes"}:
        return True
    if normalized in {"n", "no"}:
        return False
    raise ValueError("answer must be yes or no")


def _minimal_env(
    *,
    working_directory: Path,
    token: str,
    owner: str,
    target: str,
    enable_codex: bool,
) -> str:
    values = (
        ("AICO_CHANNEL", "telegram"),
        ("AICO_TELEGRAM_BOT_TOKEN", token),
        ("AICO_CLAUDE_WORKING_DIRECTORY", str(working_directory)),
        ("AICO_ENABLE_CODEX_ADAPTER", str(enable_codex).lower()),
        ("AICO_PERSONA_CONFIG_PATH", "config/personas.example.json"),
        ("AICO_PROJECT_CONFIG_PATH", "config/projects.example.json"),
        ("AICO_OWNER_SENDER_IDS", owner),
        ("AICO_TRUSTED_TARGET_IDS", target),
        ("AICO_INGRESS_DISCOVERY_LOG_IDENTITIES", "false"),
        ("AICO_ABSENCE_ADMISSION_MODE", "optional"),
        ("AICO_STATE_DB_PATH", ".aico/state.db"),
        ("AICO_AUDIT_LOG_PATH", ".aico/audit.jsonl"),
        ("AICO_MEMORY_PATH", ".aico/memory.jsonl"),
        ("AICO_LOG_PATH", "logs/aico.log"),
        ("AICO_RUNTIME_HEARTBEAT_PATH", ".aico/runtime-heartbeat.json"),
    )
    return "# Generated by `aico init`; advanced options remain in .env.example.\n" + "".join(
        f"{key}={_dotenv_value(value)}\n" for key, value in values
    )


def _dotenv_value(value: str) -> str:
    if all(character.isalnum() or character in "-._/:,@" for character in value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _write_owner_only(path: Path, payload: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _repo_error(repo: Path) -> str | None:
    if not repo.is_dir():
        return "checkout directory does not exist"
    required = (repo / "config/personas.example.json", repo / "config/projects.example.json")
    if not all(path.is_file() for path in required):
        return "run init from an AICO checkout containing the example configs"
    return None


def _run_demo() -> str:
    return asyncio.run(run_demo())


def _discover_telegram_identity(token: str, expected_text: str) -> tuple[str, str]:
    async def discover() -> tuple[str, str]:
        channel = TelegramChannel(token, poll_timeout_seconds=1)
        try:
            return await channel.discover_private_identity(expected_text)
        finally:
            await channel.stop()

    try:
        return asyncio.run(discover())
    except TelegramAPIError:
        raise
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        raise TelegramAPIError("Telegram setup request failed") from None


def _run_runtime(*, stderr: TextIO) -> int:
    try:
        asyncio.run(run_phase1(load_phase1_settings()))
    except KeyboardInterrupt:
        return 0
    except RuntimeError as exc:
        stderr.write(f"aico run: {exc}\n")
        return 2
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aico",
        description="Try, configure, run, and supervise the local AICO runtime.",
        epilog=(
            "The local runtime is the normal installation. The external Dead-Man Receiver is "
            "optional and only needed for advanced whole-machine outage detection."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="Run the deterministic no-token product demo")
    init = commands.add_parser("init", help="Create a minimal owner-only Telegram config")
    init.add_argument("--repo", type=Path, default=Path.cwd(), help="AICO checkout root")
    init.add_argument("--owner-id", help="Use a known Telegram owner sender ID")
    init.add_argument("--chat-id", help="Use a known trusted private chat ID")
    run = commands.add_parser("run", help="Run the configured Telegram runtime in foreground")
    run.add_argument("--repo", type=Path, default=Path.cwd(), help="AICO checkout root")
    doctor = commands.add_parser("doctor", help="Check local configuration and runtime health")
    doctor.add_argument("--repo", type=Path, default=Path.cwd(), help="AICO checkout root")
    service = commands.add_parser("service", help="Manage the user-level macOS LaunchAgent")
    service.add_argument("action", choices=("install", "restart", "status", "uninstall"))
    service.add_argument("--repo", type=Path, default=Path.cwd(), help="AICO checkout root")
    return parser
