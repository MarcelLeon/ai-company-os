"""Bounded, fingerprinted source excerpts for unattended standing work."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import Field, model_validator

from aico.core.models import FrozenModel

MAX_STANDING_EVIDENCE_PACK_CHARS = 65_536
MAX_STANDING_EVIDENCE_SOURCES = 8
MAX_STANDING_EVIDENCE_SOURCE_BYTES = 1_048_576
MAX_STANDING_EVIDENCE_LINES = 384
MAX_STANDING_EVIDENCE_LINE_CHARS = 2_000


class StandingEvidencePackError(RuntimeError):
    pass


class StandingEvidenceSourceSpec(FrozenModel):
    path: str = Field(min_length=1, max_length=512)
    start_marker: str | None = Field(default=None, min_length=1, max_length=512)
    end_marker: str | None = Field(default=None, min_length=1, max_length=512)

    @model_validator(mode="after")
    def validate_markers(self) -> StandingEvidenceSourceSpec:
        if self.start_marker is not None and self.start_marker == self.end_marker:
            raise ValueError("standing evidence markers must differ")
        return self


class StandingEvidenceLine(FrozenModel):
    line: int = Field(ge=1, le=1_000_000)
    text: str = Field(max_length=MAX_STANDING_EVIDENCE_LINE_CHARS)


class StandingEvidencePackSource(FrozenModel):
    path: str = Field(min_length=1, max_length=512)
    size_bytes: int = Field(ge=0, le=MAX_STANDING_EVIDENCE_SOURCE_BYTES)
    file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lines: tuple[StandingEvidenceLine, ...] = Field(min_length=1)


class StandingEvidencePack(FrozenModel):
    version: int = Field(default=1, ge=1, le=1)
    project_id: str = Field(min_length=1)
    charter_id: str = Field(min_length=1)
    sources: tuple[StandingEvidencePackSource, ...] = Field(
        min_length=1,
        max_length=MAX_STANDING_EVIDENCE_SOURCES,
    )


def build_standing_evidence_pack(
    root: Path,
    *,
    project_id: str,
    charter_id: str,
    source_specs: tuple[StandingEvidenceSourceSpec, ...],
) -> StandingEvidencePack:
    if not source_specs:
        raise StandingEvidencePackError("standing evidence sources are not configured")
    resolved_root = _resolved_root(root)
    sources = tuple(_pack_source(resolved_root, spec) for spec in source_specs)
    pack = StandingEvidencePack(
        project_id=project_id,
        charter_id=charter_id,
        sources=sources,
    )
    if len(render_standing_evidence_pack(pack)) > MAX_STANDING_EVIDENCE_PACK_CHARS:
        raise StandingEvidencePackError("standing evidence pack exceeds bounded size")
    return pack


def render_standing_evidence_pack(pack: StandingEvidencePack) -> str:
    lines = [
        f"<standing_evidence_pack version=1 sha256={standing_evidence_pack_sha256(pack)}>",
        "Only the original source path and line pairs listed below may be cited.",
    ]
    for source in pack.sources:
        lines.append(
            _render_record(
                "SOURCE",
                {"path": source.path, "size": source.size_bytes, "sha256": source.file_sha256},
            )
        )
        lines.extend(
            _render_record(
                "LINE",
                {"path": source.path, "line": item.line, "text": item.text},
            )
            for item in source.lines
        )
    lines.append("</standing_evidence_pack>")
    return "\n".join(lines)


def standing_evidence_pack_sha256(pack: StandingEvidencePack) -> str:
    payload = json.dumps(
        pack.model_dump(mode="json"),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _render_record(kind: str, payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    sanitized = encoded.replace("<", r"\u003c").replace(">", r"\u003e")
    return f"{kind} {sanitized}"


def evidence_pack_source(
    pack: StandingEvidencePack,
    path: str,
    line: int,
) -> StandingEvidencePackSource | None:
    for source in pack.sources:
        if source.path == path and any(item.line == line for item in source.lines):
            return source
    return None


def evidence_pack_is_current(pack: StandingEvidencePack, root: Path) -> bool:
    try:
        resolved_root = _resolved_root(root)
        for source in pack.sources:
            content = _read_source(resolved_root, source.path)
            if len(content) != source.size_bytes:
                return False
            if hashlib.sha256(content).hexdigest() != source.file_sha256:
                return False
        return True
    except StandingEvidencePackError:
        return False


def _pack_source(root: Path, spec: StandingEvidenceSourceSpec) -> StandingEvidencePackSource:
    content = _read_source(root, spec.path)
    try:
        text = content.decode("utf-8")
    except UnicodeError:
        raise StandingEvidencePackError("standing evidence source is not UTF-8") from None
    raw_lines = text.splitlines()
    start = _marker_index(raw_lines, spec.start_marker, default=0)
    end = _marker_index(raw_lines, spec.end_marker, default=len(raw_lines))
    if end <= start:
        raise StandingEvidencePackError("standing evidence marker order is invalid")
    selected = raw_lines[start:end]
    if not selected or len(selected) > MAX_STANDING_EVIDENCE_LINES:
        raise StandingEvidencePackError("standing evidence excerpt line count is invalid")
    if any(len(line) > MAX_STANDING_EVIDENCE_LINE_CHARS for line in selected):
        raise StandingEvidencePackError("standing evidence line exceeds bounded size")
    return StandingEvidencePackSource(
        path=spec.path,
        size_bytes=len(content),
        file_sha256=hashlib.sha256(content).hexdigest(),
        lines=tuple(
            StandingEvidenceLine(line=start + offset + 1, text=line)
            for offset, line in enumerate(selected)
        ),
    )


def _resolved_root(root: Path) -> Path:
    try:
        resolved = root.expanduser().resolve(strict=True)
    except OSError:
        raise StandingEvidencePackError("standing evidence root is unavailable") from None
    if not resolved.is_dir():
        raise StandingEvidencePackError("standing evidence root is unavailable")
    return resolved


def _read_source(root: Path, path: str) -> bytes:
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts:
        raise StandingEvidencePackError("standing evidence source must be relative")
    unresolved = root / relative
    if _has_symlink_component(root, relative):
        raise StandingEvidencePackError("standing evidence source is unavailable")
    try:
        candidate = unresolved.resolve(strict=True)
    except OSError:
        raise StandingEvidencePackError("standing evidence source is unavailable") from None
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise StandingEvidencePackError("standing evidence source is unavailable")
    try:
        with candidate.open("rb") as source_file:
            content = source_file.read(MAX_STANDING_EVIDENCE_SOURCE_BYTES + 1)
    except OSError:
        raise StandingEvidencePackError("standing evidence source is unavailable") from None
    if len(content) > MAX_STANDING_EVIDENCE_SOURCE_BYTES:
        raise StandingEvidencePackError("standing evidence source exceeds scan limit")
    return content


def _has_symlink_component(root: Path, relative: Path) -> bool:
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            return True
    return False


def _marker_index(lines: list[str], marker: str | None, *, default: int) -> int:
    if marker is None:
        return default
    matches = [index for index, line in enumerate(lines) if line == marker]
    if len(matches) != 1:
        raise StandingEvidencePackError("standing evidence marker is missing or ambiguous")
    return matches[0]
