"""Machine attestation for the standalone Codex Goal app-server surface."""

from __future__ import annotations

import hashlib
import json
import plistlib
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
_MAX_COMMAND_OUTPUT_BYTES = 65_536
_MAX_PLIST_BYTES = 1_048_576
_METHOD_PATTERN = re.compile(r"^[a-z][A-Za-z0-9_-]*/[A-Za-z0-9_/-]+$")
_CDHASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_TEAM_IDENTIFIER_PATTERN = re.compile(r"^[A-Z0-9]{10}$")
_REQUIRED_METHODS = frozenset(
    {
        "thread/goal/set",
        "thread/goal/get",
        "thread/goal/clear",
        "thread/resume",
        "turn/start",
    }
)
_GOAL_FORK_CONTINUATION_EVIDENCE = "thread/fork.deferGoalContinuation"


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


class CodexCodeSignatureIdentity(FrozenModel):
    identifier: str = Field(min_length=1, max_length=128)
    team_identifier: str = Field(pattern=r"^[A-Z0-9]{10}$")
    cdhash_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class CodexGoalNativeHostCandidateReceipt(FrozenModel):
    """First-party signed host identity plus schema semantics, before a live run."""

    version: Literal[1] = 1
    contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    app_bundle_identifier: Literal["com.openai.codex"] = "com.openai.codex"
    app_version: str = Field(min_length=1, max_length=128)
    app_build: str = Field(min_length=1, max_length=128)
    app_cdhash_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    embedded_cli_identifier: Literal["codex"] = "codex"
    embedded_cli_cdhash_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    team_identifier: str = Field(pattern=r"^[A-Z0-9]{10}$")
    codex_cli_version: str = Field(min_length=1, max_length=128)
    schema_bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    continuation_surface: Literal["thread/fork.deferGoalContinuation"] = (
        "thread/fork.deferGoalContinuation"
    )
    first_party_signature_verified: Literal[True] = True
    notarization_ticket_stapled: Literal[True] = True
    native_continuation_surface_present: Literal[True] = True
    live_native_continuation_observed: Literal[False] = False
    isolated_run_state_observed: Literal[False] = False
    formal_run_admitted: Literal[False] = False
    blocking_reasons: tuple[
        Literal[
            "live_native_continuation_observation_required",
            "isolated_run_state_observation_required",
        ],
        Literal[
            "live_native_continuation_observation_required",
            "isolated_run_state_observation_required",
        ],
    ] = (
        "live_native_continuation_observation_required",
        "isolated_run_state_observation_required",
    )

    @model_validator(mode="after")
    def validate_blocking_reasons(self) -> CodexGoalNativeHostCandidateReceipt:
        expected = (
            "live_native_continuation_observation_required",
            "isolated_run_state_observation_required",
        )
        if self.blocking_reasons != expected:
            raise ValueError("Codex native host candidate blocking reasons drifted")
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


def probe_codex_goal_native_host_candidate(
    *,
    app_bundle: Path,
    embedded_codex: Path,
    expected_cli_version: str,
    contract_sha256: str,
    expected_team_identifier: str = "2DC432GLL2",
    timeout_seconds: float = 10,
) -> CodexGoalNativeHostCandidateReceipt:
    """Bind the first-party signed desktop build to its native continuation schema."""
    _validate_host_paths(app_bundle, embedded_codex)
    metadata = _read_app_metadata(app_bundle)
    _verify_signature(app_bundle, timeout_seconds)
    _verify_signature(embedded_codex, timeout_seconds)
    app_signature, app_notarized = _signature_identity(app_bundle, timeout_seconds)
    cli_signature, _ = _signature_identity(embedded_codex, timeout_seconds)
    surface = probe_codex_goal_host_surface(
        executable=str(embedded_codex),
        expected_cli_version=expected_cli_version,
        contract_sha256=contract_sha256,
        timeout_seconds=timeout_seconds,
    )
    return attest_codex_goal_native_host_candidate(
        surface,
        bundle_identifier=metadata["bundle_identifier"],
        app_version=metadata["app_version"],
        app_build=metadata["app_build"],
        app_signature=app_signature,
        cli_signature=cli_signature,
        expected_team_identifier=expected_team_identifier,
        notarization_ticket_stapled=app_notarized,
    )


def attest_codex_goal_native_host_candidate(
    surface: CodexGoalHostSurfaceReceipt,
    *,
    bundle_identifier: str,
    app_version: str,
    app_build: str,
    app_signature: CodexCodeSignatureIdentity,
    cli_signature: CodexCodeSignatureIdentity,
    expected_team_identifier: str,
    notarization_ticket_stapled: bool,
) -> CodexGoalNativeHostCandidateReceipt:
    """Admit signed build identity as a candidate, not as a completed live host run."""
    identity_ok = (
        bundle_identifier == "com.openai.codex"
        and app_signature.identifier == bundle_identifier
        and cli_signature.identifier == "codex"
        and _TEAM_IDENTIFIER_PATTERN.fullmatch(expected_team_identifier) is not None
        and app_signature.team_identifier == expected_team_identifier
        and cli_signature.team_identifier == expected_team_identifier
        and _CDHASH_PATTERN.fullmatch(app_signature.cdhash_sha256) is not None
        and _CDHASH_PATTERN.fullmatch(cli_signature.cdhash_sha256) is not None
    )
    if not identity_ok or not notarization_ticket_stapled:
        raise ValueError("Codex native host candidate is not the expected signed build")
    if _GOAL_FORK_CONTINUATION_EVIDENCE not in surface.native_continuation_candidates:
        raise ValueError("Codex native host candidate lacks Goal continuation semantics")
    return CodexGoalNativeHostCandidateReceipt(
        contract_sha256=surface.contract_sha256,
        app_version=app_version,
        app_build=app_build,
        app_cdhash_sha256=app_signature.cdhash_sha256,
        embedded_cli_cdhash_sha256=cli_signature.cdhash_sha256,
        team_identifier=expected_team_identifier,
        codex_cli_version=surface.codex_cli_version,
        schema_bundle_sha256=surface.schema_bundle_sha256,
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
    candidates = {method for method in methods if "continu" in method.lower()}
    if _goal_fork_continuation_present(documents, methods):
        candidates.add(_GOAL_FORK_CONTINUATION_EVIDENCE)
    candidate_tuple = tuple(sorted(candidates))
    reasons: tuple[
        Literal[
            "native_continuation_surface_absent",
            "native_host_build_receipt_required",
        ],
        ...,
    ] = (
        ("native_continuation_surface_absent", "native_host_build_receipt_required")
        if not candidate_tuple
        else ("native_host_build_receipt_required",)
    )
    return CodexGoalHostSurfaceReceipt(
        contract_sha256=contract_sha256,
        codex_cli_version=codex_cli_version,
        schema_bundle_sha256=_schema_digest(documents),
        remote_control_transport_present=any(
            method.lower().startswith("remotecontrol/") for method in methods
        ),
        native_continuation_candidates=candidate_tuple,
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


def _goal_fork_continuation_present(
    documents: tuple[tuple[str, bytes, object], ...],
    methods: set[str],
) -> bool:
    schema = next(
        (payload for path, _, payload in documents if path == "v2/ThreadForkParams.json"),
        None,
    )
    if "thread/fork" not in methods or not isinstance(schema, dict):
        return False
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return False
    field = properties.get("deferGoalContinuation")
    if not isinstance(field, dict) or field.get("type") != "boolean":
        return False
    description = field.get("description")
    return (
        isinstance(description, str)
        and "initial automatic continuation" in description
        and "normal automatic continuation resumes" in description
        and "goal lifecycle" in description
    )


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


def _validate_host_paths(app_bundle: Path, embedded_codex: Path) -> None:
    if (
        not app_bundle.is_absolute()
        or not app_bundle.is_dir()
        or app_bundle.is_symlink()
        or not embedded_codex.is_absolute()
        or not embedded_codex.is_file()
        or embedded_codex.is_symlink()
        or not embedded_codex.is_relative_to(app_bundle)
    ):
        raise ValueError("Codex native host candidate paths are unsafe")


def _read_app_metadata(app_bundle: Path) -> dict[str, str]:
    info_path = app_bundle / "Contents/Info.plist"
    if info_path.is_symlink() or not info_path.is_file():
        raise ValueError("Codex native host candidate Info.plist is unsafe")
    payload = info_path.read_bytes()
    if not payload or len(payload) > _MAX_PLIST_BYTES:
        raise ValueError("Codex native host candidate Info.plist is invalid")
    try:
        parsed = plistlib.loads(payload)
    except plistlib.InvalidFileException:
        raise ValueError("Codex native host candidate Info.plist is invalid") from None
    values = {
        "bundle_identifier": parsed.get("CFBundleIdentifier"),
        "app_version": parsed.get("CFBundleShortVersionString"),
        "app_build": parsed.get("CFBundleVersion"),
    }
    if not all(isinstance(value, str) and 0 < len(value) <= 128 for value in values.values()):
        raise ValueError("Codex native host candidate metadata is incomplete")
    return values


def _verify_signature(path: Path, timeout_seconds: float) -> None:
    completed = _run_codesign(
        ("codesign", "--verify", "--deep", "--strict", "--verbose=2", str(path)),
        timeout_seconds,
    )
    if completed.returncode != 0:
        raise ValueError("Codex native host candidate code signature is invalid")


def _signature_identity(
    path: Path,
    timeout_seconds: float,
) -> tuple[CodexCodeSignatureIdentity, bool]:
    completed = _run_codesign(
        ("codesign", "-dv", "--verbose=4", str(path)),
        timeout_seconds,
    )
    if completed.returncode != 0:
        raise ValueError("Codex native host candidate signature identity is unavailable")
    details = completed.stderr
    values = {
        key: match.group(1)
        for key, pattern in {
            "identifier": r"(?m)^Identifier=(\S+)$",
            "team_identifier": r"(?m)^TeamIdentifier=(\S+)$",
            "cdhash_sha256": r"(?m)^CandidateCDHashFull sha256=([0-9a-f]{64})$",
        }.items()
        if (match := re.search(pattern, details)) is not None
    }
    if len(values) != 3:
        raise ValueError("Codex native host candidate signature identity is incomplete")
    return (
        CodexCodeSignatureIdentity.model_validate(values),
        "Notarization Ticket=stapled" in details,
    )


def _run_codesign(
    command: tuple[str, ...],
    timeout_seconds: float,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.SubprocessError):
        raise ValueError("Codex native host candidate signature command failed") from None
    if len(completed.stdout.encode()) + len(completed.stderr.encode()) > _MAX_COMMAND_OUTPUT_BYTES:
        raise ValueError("Codex native host candidate signature output is oversized")
    return completed
