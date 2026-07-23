"""Machine attestation for the standalone Codex Goal app-server surface."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from aico.core.models import FrozenModel

_MAX_SCHEMA_FILES = 2_048
_MAX_SCHEMA_FILE_BYTES = 4_194_304
_MAX_SCHEMA_BUNDLE_BYTES = 67_108_864
_METHOD_PATTERN = re.compile(r"^[a-z][A-Za-z0-9_-]*/[A-Za-z0-9_/-]+$")
_REQUIRED_METHODS = frozenset(
    {
        "thread/goal/set",
        "thread/goal/get",
        "thread/goal/clear",
        "thread/resume",
        "turn/start",
    }
)


class CodexGoalHostSurfaceReceipt(FrozenModel):
    """Bounded evidence about an app-server surface, never a native-host admission."""

    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    codex_cli_version: str = Field(min_length=1, max_length=128)
    schema_bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    experimental_schema: Literal[True] = True
    surface_kind: Literal["standalone_app_server"] = "standalone_app_server"
    goal_control_plane_present: Literal[True] = True
    persistent_thread_resume_present: Literal[True] = True
    turn_start_requires_client_input: Literal[True] = True
    remote_control_transport_present: bool
    native_continuation_candidates: tuple[str, ...] = Field(default=(), max_length=32)
    native_host_build_receipt_present: Literal[False] = False
    formal_run_admitted: Literal[False] = False
    blocking_reasons: tuple[
        Literal[
            "native_continuation_surface_absent",
            "native_host_build_receipt_required",
        ],
        ...,
    ] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def validate_reasons(self) -> CodexGoalHostSurfaceReceipt:
        absent = not self.native_continuation_candidates
        expected = (
            (
                "native_continuation_surface_absent",
                "native_host_build_receipt_required",
            )
            if absent
            else ("native_host_build_receipt_required",)
        )
        if self.blocking_reasons != expected:
            raise ValueError("Codex Goal host surface blocking reasons drifted")
        return self


def probe_codex_goal_host_surface(
    *,
    executable: str,
    expected_cli_version: str,
    contract_sha256: str,
    timeout_seconds: float = 10,
) -> CodexGoalHostSurfaceReceipt:
    """Generate the installed schema and attest why it is not a native Goal host."""
    version = _codex_version(executable, timeout_seconds)
    if version != expected_cli_version:
        raise ValueError("Codex Goal host probe CLI version does not match frozen contract")
    with tempfile.TemporaryDirectory(prefix="aico-codex-goal-schema-") as directory:
        output = Path(directory)
        try:
            completed = subprocess.run(
                (
                    executable,
                    "app-server",
                    "generate-json-schema",
                    "--experimental",
                    "--out",
                    str(output),
                ),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError):
            raise ValueError(
                "Codex Goal host probe could not generate the app-server schema"
            ) from None
        if completed.returncode != 0:
            raise ValueError("Codex Goal host probe schema generation failed")
        return attest_codex_goal_app_server_schema(
            output,
            contract_sha256=contract_sha256,
            codex_cli_version=version,
        )


def attest_codex_goal_app_server_schema(
    schema_root: Path,
    *,
    contract_sha256: str,
    codex_cli_version: str,
) -> CodexGoalHostSurfaceReceipt:
    """Validate a generated schema bundle without treating it as a host build receipt."""
    documents = _read_schema_bundle(schema_root)
    methods = {
        value
        for _, _, payload in documents
        for value in _walk_strings(payload)
        if _METHOD_PATTERN.fullmatch(value)
    }
    if not _REQUIRED_METHODS.issubset(methods):
        raise ValueError("Codex Goal host probe is missing the required Goal control plane")
    turn_schema = next(
        (payload for path, _, payload in documents if path == "v2/TurnStartParams.json"),
        None,
    )
    if not isinstance(turn_schema, dict) or "input" not in turn_schema.get("required", ()):
        raise ValueError("Codex Goal turn/start no longer requires explicit client input")
    candidates = tuple(sorted(method for method in methods if "continu" in method.lower()))
    reasons: tuple[
        Literal[
            "native_continuation_surface_absent",
            "native_host_build_receipt_required",
        ],
        ...,
    ] = (
        ("native_continuation_surface_absent", "native_host_build_receipt_required")
        if not candidates
        else ("native_host_build_receipt_required",)
    )
    return CodexGoalHostSurfaceReceipt(
        contract_sha256=contract_sha256,
        codex_cli_version=codex_cli_version,
        schema_bundle_sha256=_schema_digest(documents),
        remote_control_transport_present=any(
            method.lower().startswith("remotecontrol/") for method in methods
        ),
        native_continuation_candidates=candidates,
        blocking_reasons=reasons,
    )


def _read_schema_bundle(
    root: Path,
) -> tuple[tuple[str, bytes, object], ...]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Codex Goal host probe schema directory is unsafe")
    paths = sorted(root.rglob("*.json"))
    if not paths or len(paths) > _MAX_SCHEMA_FILES:
        raise ValueError("Codex Goal host probe schema file count is invalid")
    total = 0
    documents: list[tuple[str, bytes, object]] = []
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError("Codex Goal host probe schema file is unsafe")
        payload = path.read_bytes()
        if not payload or len(payload) > _MAX_SCHEMA_FILE_BYTES:
            raise ValueError("Codex Goal host probe schema file is invalid")
        total += len(payload)
        if total > _MAX_SCHEMA_BUNDLE_BYTES:
            raise ValueError("Codex Goal host probe schema bundle is oversized")
        try:
            parsed = json.loads(payload, object_pairs_hook=_unique_object)
        except (UnicodeError, ValueError):
            raise ValueError("Codex Goal host probe schema JSON is invalid") from None
        documents.append((path.relative_to(root).as_posix(), payload, parsed))
    return tuple(documents)


def _schema_digest(documents: tuple[tuple[str, bytes, object], ...]) -> str:
    digest = hashlib.sha256()
    for relative_path, payload, _ in documents:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
    return digest.hexdigest()


def _walk_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _walk_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_strings(nested)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate schema key")
        result[key] = value
    return result


def _codex_version(executable: str, timeout_seconds: float) -> str:
    try:
        completed = subprocess.run(
            (executable, "--version"),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.SubprocessError):
        raise ValueError("Codex Goal host probe could not read the CLI version") from None
    prefix = "codex-cli "
    version = completed.stdout.strip()
    if completed.returncode != 0 or not version.startswith(prefix):
        raise ValueError("Codex Goal host probe received an invalid CLI version")
    return version.removeprefix(prefix)
