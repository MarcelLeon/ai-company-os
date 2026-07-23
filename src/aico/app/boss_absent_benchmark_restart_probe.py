"""Process-isolated restart probe for the no-model benchmark harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Literal

from pydantic import Field

from aico.core.boss_absent_benchmark import BenchmarkSystem
from aico.core.models import FrozenModel

_MODULE = "aico.app.boss_absent_benchmark_restart_probe"
_MAX_STATE_BYTES = 4_096


class BenchmarkRestartProbeReceipt(FrozenModel):
    version: Literal[1] = 1
    system: BenchmarkSystem
    checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminated_returncode: int = Field(lt=0)
    resumed_returncode: Literal[0] = 0
    resumed_from_exact_checkpoint: Literal[True] = True


def run_restart_probe(
    output_dir: Path,
    system: BenchmarkSystem,
    *,
    timeout_seconds: float = 5,
) -> BenchmarkRestartProbeReceipt:
    state_path = output_dir / f"restart-state-{system.value}.json"
    process = subprocess.Popen(
        [sys.executable, "-m", _MODULE, "checkpoint", "--state", str(state_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + timeout_seconds
        while not state_path.is_file() and time.monotonic() < deadline:
            if process.poll() is not None:
                raise ValueError("restart probe worker exited before durable checkpoint")
            time.sleep(0.01)
        if not state_path.is_file():
            raise ValueError("restart probe did not create a durable checkpoint")
        checkpoint = _read_state(state_path)
        checkpoint_sha = hashlib.sha256(checkpoint).hexdigest()
        process.terminate()
        terminated = process.wait(timeout=timeout_seconds)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=timeout_seconds)
    if terminated >= 0:
        raise ValueError("restart probe worker was not terminated by the harness")
    resumed = subprocess.run(
        [
            sys.executable,
            "-m",
            _MODULE,
            "resume",
            "--state",
            str(state_path),
            "--expected-sha256",
            checkpoint_sha,
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if resumed.returncode != 0 or resumed.stdout.strip() != "resumed":
        raise ValueError("restart probe did not resume from the durable checkpoint")
    return BenchmarkRestartProbeReceipt(
        system=system,
        checkpoint_sha256=checkpoint_sha,
        terminated_returncode=terminated,
        resumed_returncode=0,
        resumed_from_exact_checkpoint=True,
    )


def main() -> None:
    args = _parser().parse_args()
    if args.command == "checkpoint":
        _write_checkpoint(args.state)
        time.sleep(30)
        raise SystemExit(3)
    if args.command == "resume":
        checkpoint = _read_state(args.state)
        if hashlib.sha256(checkpoint).hexdigest() != args.expected_sha256:
            raise SystemExit(4)
        if json.loads(checkpoint) != {"checkpoint": "durable", "version": 1}:
            raise SystemExit(5)
        print("resumed")
        return
    raise AssertionError("unknown restart probe command")


def _write_checkpoint(path: Path) -> None:
    payload = b'{"checkpoint":"durable","version":1}\n'
    with path.open("xb") as output:
        output.write(payload)
        output.flush()


def _read_state(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ValueError("restart probe state must be a regular non-symlink file")
    with path.open("rb") as source:
        payload = source.read(_MAX_STATE_BYTES + 1)
    if len(payload) > _MAX_STATE_BYTES:
        raise ValueError("restart probe state exceeds bounded size")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aico-benchmark-restart-probe")
    commands = parser.add_subparsers(dest="command", required=True)
    checkpoint = commands.add_parser("checkpoint")
    checkpoint.add_argument("--state", type=Path, required=True)
    resume = commands.add_parser("resume")
    resume.add_argument("--state", type=Path, required=True)
    resume.add_argument("--expected-sha256", required=True)
    return parser


if __name__ == "__main__":
    main()
