"""Reviewed Git revision evidence for source-controlled runtime configuration."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_MAX_CONFIG_BYTES = 4 * 1024 * 1024
_GitRunner = Callable[[Path, Sequence[str]], bytes]


class ConfigRevisionError(RuntimeError):
    """A checkout cannot prove the reviewed runtime configuration revision."""


class ConfigFileRevision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["project", "persona"]
    relative_path: str = Field(min_length=1, max_length=1024)
    bytes: int = Field(ge=1, le=_MAX_CONFIG_BYTES)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    git_blob_oid: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")

    @model_validator(mode="after")
    def validate_relative_path(self) -> ConfigFileRevision:
        path = PurePosixPath(self.relative_path)
        if path.is_absolute() or ".." in path.parts or self.relative_path != path.as_posix():
            raise ValueError("config revision path must be normalized and relative")
        return self


class ConfigRevisionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    revision: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    tree_oid: str = Field(pattern=r"^[a-f0-9]{40}([a-f0-9]{24})?$")
    object_format: Literal["sha1", "sha256"]
    clean_checkout_required: Literal[True] = True
    review_authority: Literal["operator_supplied_revision"] = "operator_supplied_revision"
    persona_source: Literal["tracked_file", "built_in_at_revision"]
    configs: tuple[ConfigFileRevision, ...] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def validate_contract(self) -> ConfigRevisionEvidence:
        roles = tuple(config.role for config in self.configs)
        expected = ("project", "persona") if self.persona_source == "tracked_file" else ("project",)
        if roles != expected:
            raise ValueError("config revision roles do not match persona source")
        oid_length = 40 if self.object_format == "sha1" else 64
        if any(
            len(value) != oid_length
            for value in (
                self.revision,
                self.tree_oid,
                *(config.git_blob_oid for config in self.configs),
            )
        ):
            raise ValueError("config revision object IDs do not match Git object format")
        return self


class ConfigCheckoutSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["capture", "verify-checkout"]
    revision: str
    tree_oid: str
    object_format: Literal["sha1", "sha256"]
    config_count: int = Field(ge=1, le=2)
    clean: Literal[True] = True
    persona_source: Literal["tracked_file", "built_in_at_revision"]


def capture_config_revision(
    checkout_path: Path,
    project_config_path: Path,
    persona_config_path: Path | None = None,
    *,
    expected_revision: str,
    runner: _GitRunner | None = None,
) -> tuple[ConfigRevisionEvidence, ConfigCheckoutSummary]:
    checkout = _absolute(checkout_path)
    git = runner or _run_git
    _require_checkout_root(checkout, git)
    _require_clean_checkout(checkout, git)
    object_format = _object_format(checkout, git)
    revision = _oid(checkout, ("rev-parse", "--verify", "HEAD^{commit}"), git)
    if revision != _expected_revision(expected_revision, object_format):
        raise ConfigRevisionError("checkout revision does not match owner-reviewed revision")
    tree_oid = _oid(checkout, ("rev-parse", "--verify", "HEAD^{tree}"), git)
    configs = [
        _capture_config(checkout, project_config_path, "project", git),
    ]
    if persona_config_path is not None:
        configs.append(_capture_config(checkout, persona_config_path, "persona", git))
    persona_source: Literal["tracked_file", "built_in_at_revision"] = (
        "tracked_file" if persona_config_path is not None else "built_in_at_revision"
    )
    evidence = ConfigRevisionEvidence(
        revision=revision,
        tree_oid=tree_oid,
        object_format=object_format,
        persona_source=persona_source,
        configs=tuple(configs),
    )
    return evidence, _summary("capture", evidence)


def verify_config_checkout(
    evidence: ConfigRevisionEvidence,
    checkout_path: Path,
    *,
    runner: _GitRunner | None = None,
) -> ConfigCheckoutSummary:
    checkout = _absolute(checkout_path)
    git = runner or _run_git
    _require_checkout_root(checkout, git)
    _require_clean_checkout(checkout, git)
    if _object_format(checkout, git) != evidence.object_format:
        raise ConfigRevisionError("checkout Git object format does not match recovery set")
    revision = _oid(checkout, ("rev-parse", "--verify", "HEAD^{commit}"), git)
    tree_oid = _oid(checkout, ("rev-parse", "--verify", "HEAD^{tree}"), git)
    if revision != evidence.revision or tree_oid != evidence.tree_oid:
        raise ConfigRevisionError("checkout revision does not match recovery set")
    for config in evidence.configs:
        _verify_config(checkout, config, git)
    return _summary("verify-checkout", evidence)


def _capture_config(
    checkout: Path,
    config_path: Path,
    role: Literal["project", "persona"],
    git: _GitRunner,
) -> ConfigFileRevision:
    path, relative = _config_path(checkout, config_path)
    payload = _read_json_config(path)
    blob_oid = _oid(checkout, ("rev-parse", f"HEAD:{relative}"), git)
    committed = _git_bytes(checkout, ("show", f"HEAD:{relative}"), git)
    if payload != committed:
        raise ConfigRevisionError("runtime config does not match the reviewed revision")
    return ConfigFileRevision(
        role=role,
        relative_path=relative,
        bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        git_blob_oid=blob_oid,
    )


def _verify_config(checkout: Path, config: ConfigFileRevision, git: _GitRunner) -> None:
    path, relative = _config_path(checkout, Path(config.relative_path))
    if relative != config.relative_path:
        raise ConfigRevisionError("checkout config path does not match recovery set")
    payload = _read_json_config(path)
    blob_oid = _oid(checkout, ("rev-parse", f"HEAD:{relative}"), git)
    if (
        len(payload) != config.bytes
        or hashlib.sha256(payload).hexdigest() != config.sha256
        or blob_oid != config.git_blob_oid
    ):
        raise ConfigRevisionError("checkout config does not match recovery set")


def _config_path(checkout: Path, path: Path) -> tuple[Path, str]:
    candidate = _absolute(path if path.is_absolute() else checkout / path)
    try:
        relative = candidate.relative_to(checkout).as_posix()
    except ValueError:
        raise ConfigRevisionError("runtime config must be inside the checkout") from None
    return candidate, relative


def _read_json_config(path: Path) -> bytes:
    try:
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ConfigRevisionError("runtime config must be a regular non-symlink file")
        if metadata.st_size <= 0 or metadata.st_size > _MAX_CONFIG_BYTES:
            raise ConfigRevisionError("runtime config size is outside the supported boundary")
        payload = path.read_bytes()
        json.loads(payload)
        return payload
    except ConfigRevisionError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise ConfigRevisionError("runtime config is missing or invalid JSON") from None


def _require_checkout_root(checkout: Path, git: _GitRunner) -> None:
    if not checkout.is_dir():
        raise ConfigRevisionError("checkout is missing or not a directory")
    root = _git_text(checkout, ("rev-parse", "--show-toplevel"), git)
    if _absolute(Path(root)) != checkout:
        raise ConfigRevisionError("checkout path must be the Git worktree root")


def _require_clean_checkout(checkout: Path, git: _GitRunner) -> None:
    status = _git_bytes(
        checkout,
        ("status", "--porcelain=v1", "--untracked-files=all"),
        git,
    )
    if status.strip():
        raise ConfigRevisionError("checkout must be clean before capture or recovery")


def _object_format(checkout: Path, git: _GitRunner) -> Literal["sha1", "sha256"]:
    value = _git_text(checkout, ("rev-parse", "--show-object-format"), git)
    if value == "sha1":
        return "sha1"
    if value == "sha256":
        return "sha256"
    raise ConfigRevisionError("checkout uses an unsupported Git object format")


def _expected_revision(value: str, object_format: Literal["sha1", "sha256"]) -> str:
    normalized = value.strip().lower()
    expected_length = 40 if object_format == "sha1" else 64
    if len(normalized) != expected_length or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ConfigRevisionError("owner-reviewed revision is invalid")
    return normalized


def _oid(checkout: Path, args: Sequence[str], git: _GitRunner) -> str:
    value = _git_text(checkout, args, git)
    if len(value) not in {40, 64} or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ConfigRevisionError("Git returned an invalid object ID")
    return value


def _git_text(checkout: Path, args: Sequence[str], git: _GitRunner) -> str:
    try:
        return _git_bytes(checkout, args, git).decode("utf-8").strip()
    except UnicodeDecodeError:
        raise ConfigRevisionError("Git returned invalid text") from None


def _git_bytes(checkout: Path, args: Sequence[str], git: _GitRunner) -> bytes:
    try:
        return git(checkout, args)
    except ConfigRevisionError:
        raise
    except (OSError, subprocess.SubprocessError):
        raise ConfigRevisionError("Git checkout verification failed") from None


def _run_git(checkout: Path, args: Sequence[str]) -> bytes:
    environment = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C"}
    result = subprocess.run(
        ("git", "-c", "core.hooksPath=/dev/null", *args),
        cwd=checkout,
        env=environment,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise ConfigRevisionError("Git checkout verification failed")
    return result.stdout


def _summary(
    operation: Literal["capture", "verify-checkout"], evidence: ConfigRevisionEvidence
) -> ConfigCheckoutSummary:
    return ConfigCheckoutSummary(
        operation=operation,
        revision=evidence.revision,
        tree_oid=evidence.tree_oid,
        object_format=evidence.object_format,
        config_count=len(evidence.configs),
        persona_source=evidence.persona_source,
    )


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))
