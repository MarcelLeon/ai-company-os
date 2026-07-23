"""CLI for the independent signed Codex Goal live host observer."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO, TypeVar

from pydantic import BaseModel

from aico.app.boss_absent_codex_goal_capability import (
    CodexGoalNativeHostCandidateReceipt,
    probe_codex_goal_native_host_candidate,
)
from aico.app.boss_absent_codex_goal_live_observer import (
    CodexGoalLiveObservationIntent,
    begin_codex_goal_live_observation,
    finalize_codex_goal_live_observation,
    inspect_codex_desktop_host,
)
from aico.app.boss_absent_codex_goal_probe import observe_codex_goal_state
from aico.core.boss_absent_benchmark import (
    BossAbsentBenchmarkContract,
    canonical_sha256,
)

_MAX_MODEL_BYTES = 1_048_576
ModelT = TypeVar("ModelT", bound=BaseModel)


def run(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error = stderr or sys.stderr
    args = _parser().parse_args(argv)
    try:
        candidate = _probe_candidate(args)
        host = inspect_codex_desktop_host(
            args.host_pid,
            app_bundle=args.app_bundle.resolve(),
            embedded_codex=args.embedded_codex.resolve(),
        )
        if host is None:
            raise ValueError("Codex desktop host process is not running")
        goal = observe_codex_goal_state(
            executable=str(args.embedded_codex.resolve()),
            codex_home=args.codex_home.resolve(),
            thread_id=args.thread_id,
        )
        if args.command == "start":
            intent = begin_codex_goal_live_observation(
                candidate,
                session_path=_session_path(args),
                thread_id=args.thread_id,
                host=host,
                goal=goal,
            )
            _write_new_model(args.output, intent)
            output.write(
                "Codex Goal live observation started: "
                f"host_pid={host.pid} session_bytes={intent.session_before.size_bytes}\n"
            )
            return 0
        intent = _read_private_model(args.intent, CodexGoalLiveObservationIntent)
        receipt = finalize_codex_goal_live_observation(
            intent,
            candidate,
            session_path=_session_path(args),
            thread_id=args.thread_id,
            host_after=host,
            goal_after=goal,
            old_host_terminated=_old_host_terminated(args, intent),
        )
        _write_new_model(args.output, receipt)
        output.write(
            "Codex Goal live host admitted: "
            f"restart=true native_continuation=true "
            f"goal_tokens={receipt.goal_token_delta} "
            f"provider_tokens={receipt.provider_token_delta}\n"
        )
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        error.write(f"Codex Goal observer failed: {exc}\n")
        return 2


def main() -> None:
    raise SystemExit(run())


def _probe_candidate(args: argparse.Namespace) -> CodexGoalNativeHostCandidateReceipt:
    contract = _read_model(args.contract, BossAbsentBenchmarkContract)
    return probe_codex_goal_native_host_candidate(
        app_bundle=args.app_bundle.resolve(),
        embedded_codex=args.embedded_codex.resolve(),
        expected_cli_version=contract.codex_cli_version,
        contract_sha256=canonical_sha256(contract),
        expected_team_identifier=args.team_identifier,
    )


def _old_host_terminated(
    args: argparse.Namespace,
    intent: CodexGoalLiveObservationIntent,
) -> bool:
    try:
        old = inspect_codex_desktop_host(
            intent.host_before.pid,
            app_bundle=args.app_bundle.resolve(),
            embedded_codex=args.embedded_codex.resolve(),
        )
    except ValueError as exc:
        if "command does not match" in str(exc) or "parent is not" in str(exc):
            return True
        raise
    return old is None


def _session_path(args: argparse.Namespace) -> Path:
    raw_session: Path = args.session
    codex_home: Path = args.codex_home
    thread_id: str = args.thread_id
    if (
        not raw_session.is_absolute()
        or raw_session != raw_session.resolve()
        or not codex_home.is_absolute()
        or codex_home != codex_home.resolve()
    ):
        raise ValueError("Codex Goal observer paths must be canonical and symlink-free")
    session = raw_session
    sessions_root = codex_home / "sessions"
    if (
        not session.is_relative_to(sessions_root)
        or not session.name.endswith(f"-{thread_id}.jsonl")
        or session.is_symlink()
        or not session.is_file()
    ):
        raise ValueError("Codex Goal observer session is not the exact Codex thread artifact")
    metadata = session.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o022:
        raise ValueError("Codex Goal observer session ownership or permissions are unsafe")
    return session


def _read_model(path: Path, model_type: type[ModelT]) -> ModelT:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_MODEL_BYTES:
        raise ValueError("Codex Goal observer input is invalid")
    try:
        return model_type.model_validate_json(path.read_bytes())
    except ValueError:
        raise ValueError("Codex Goal observer input is invalid") from None


def _read_private_model(path: Path, model_type: type[ModelT]) -> ModelT:
    model = _read_model(path, model_type)
    metadata = path.stat()
    if stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_uid != os.getuid():
        raise ValueError("Codex Goal observer intent must be owner-only")
    return model


def _write_new_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(model.model_dump_json(indent=2))
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        if path.exists():
            path.unlink()
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aico-codex-goal-observer",
        description="Observe signed Codex Goal continuation across a desktop host restart.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start", help="Freeze the pre-restart observation intent.")
    _add_common_arguments(start)
    start.add_argument("--output", type=Path, required=True)
    finish = subparsers.add_parser(
        "finish",
        help="Verify append-only resume, native continuation, and usage after restart.",
    )
    _add_common_arguments(finish)
    finish.add_argument("--intent", type=Path, required=True)
    finish.add_argument("--output", type=Path, required=True)
    return parser


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--host-pid", type=int, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument(
        "--app-bundle",
        type=Path,
        default=Path("/Applications/ChatGPT.app"),
    )
    parser.add_argument(
        "--embedded-codex",
        type=Path,
        default=Path("/Applications/ChatGPT.app/Contents/Resources/codex"),
    )
    parser.add_argument("--team-identifier", default="2DC432GLL2")


if __name__ == "__main__":
    main()
