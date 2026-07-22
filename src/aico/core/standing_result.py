"""Deterministic contract checks for owner-preauthorized standing results."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from aico.core.models import FrozenModel, utc_now

MAX_STANDING_RESULT_CHARS = 32_768
MAX_STANDING_CRITERIA = 16
MAX_STANDING_STOPS = 16
MAX_STANDING_SOURCES_PER_CRITERION = 8
MAX_STANDING_LIST_ITEMS = 16
MAX_STANDING_TEXT_CHARS = 2_000
MAX_STANDING_PATH_CHARS = 512
MAX_STANDING_SOURCE_FILE_BYTES = 262_144
MAX_STANDING_VERIFIED_SOURCES = 16
_MAX_SOURCE_LINE = 1_000_000
_BoundedText = Annotated[
    str,
    Field(min_length=1, max_length=MAX_STANDING_TEXT_CHARS),
]


class StandingResultStatus(StrEnum):
    COMPLETE = "complete"
    BLOCKED = "blocked"


class StandingCriterionVerdict(StrEnum):
    MET = "met"
    UNMET = "unmet"


class StandingResultContractStatus(StrEnum):
    COMPLETE = "complete"
    BLOCKED = "blocked"
    INVALID = "invalid"


class StandingEvidenceStatus(StrEnum):
    CURRENT = "current"
    DRIFTED = "drifted"
    MISSING = "missing"


class StandingResultFailure(StrEnum):
    INVALID_JSON = "invalid_json"
    RESULT_SCHEMA_INVALID = "result_schema_invalid"
    CRITERIA_MISMATCH = "criteria_mismatch"
    STOP_CONDITIONS_MISMATCH = "stop_conditions_mismatch"
    SOURCE_UNVERIFIED = "source_unverified"
    RESULT_INCONSISTENT = "result_inconsistent"
    EVIDENCE_ROOT_UNAVAILABLE = "evidence_root_unavailable"
    RESULT_TOO_LARGE = "result_too_large"
    SOURCE_TOO_LARGE = "source_too_large"
    SOURCE_LIMIT_EXCEEDED = "source_limit_exceeded"


class StandingSourceRef(FrozenModel):
    path: str = Field(min_length=1, max_length=MAX_STANDING_PATH_CHARS)
    line: int = Field(ge=1, le=_MAX_SOURCE_LINE)


class StandingCriterionResult(FrozenModel):
    criterion_id: str = Field(max_length=8, pattern=r"^A[1-9][0-9]*$")
    verdict: StandingCriterionVerdict
    evidence: _BoundedText
    sources: tuple[StandingSourceRef, ...] = Field(
        min_length=1,
        max_length=MAX_STANDING_SOURCES_PER_CRITERION,
    )


class StandingStopConditionResult(FrozenModel):
    stop_id: str = Field(max_length=8, pattern=r"^S[1-9][0-9]*$")
    observed: Literal[True]


class StandingVerifiedSource(FrozenModel):
    path: str = Field(min_length=1, max_length=MAX_STANDING_PATH_CHARS)
    line: int = Field(ge=1, le=_MAX_SOURCE_LINE)
    size_bytes: int = Field(ge=0, le=MAX_STANDING_SOURCE_FILE_BYTES)
    file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class StandingStructuredResult(FrozenModel):
    version: Literal[1]
    result: StandingResultStatus
    summary: _BoundedText
    criteria: tuple[StandingCriterionResult, ...] = Field(
        min_length=1,
        max_length=MAX_STANDING_CRITERIA,
    )
    stop_conditions: tuple[StandingStopConditionResult, ...] = Field(
        min_length=1,
        max_length=MAX_STANDING_STOPS,
    )
    gaps: tuple[_BoundedText, ...] = Field(max_length=MAX_STANDING_LIST_ITEMS)
    risks: tuple[_BoundedText, ...] = Field(max_length=MAX_STANDING_LIST_ITEMS)
    next_actions: tuple[_BoundedText, ...] = Field(
        min_length=1,
        max_length=MAX_STANDING_LIST_ITEMS,
    )

    @model_validator(mode="after")
    def _require_unique_ids(self) -> StandingStructuredResult:
        if len({item.criterion_id for item in self.criteria}) != len(self.criteria):
            raise ValueError("duplicate standing result criterion id")
        if len({item.stop_id for item in self.stop_conditions}) != len(self.stop_conditions):
            raise ValueError("duplicate standing result stop id")
        return self


class StandingResultReceipt(FrozenModel):
    status: StandingResultContractStatus
    criteria_met: int = Field(ge=0)
    criteria_total: int = Field(ge=1)
    verified_sources: int = Field(ge=0)
    checked_at: datetime
    failure: StandingResultFailure | None = None
    source_manifest: tuple[StandingVerifiedSource, ...] = Field(
        default=(),
        max_length=MAX_STANDING_VERIFIED_SOURCES,
    )
    evidence_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


def validate_standing_result(
    output: str,
    *,
    acceptance_evidence: tuple[str, ...],
    stop_conditions: tuple[str, ...],
    evidence_root: Path | None,
    clock: Callable[[], datetime] = utc_now,
) -> StandingResultReceipt:
    """Validate shape, charter coverage, and repository-local source locations."""
    output = output.strip()
    if len(output) > MAX_STANDING_RESULT_CHARS:
        return _invalid_receipt(
            StandingResultFailure.RESULT_TOO_LARGE,
            criteria_total=len(acceptance_evidence),
            clock=clock,
        )
    try:
        raw_result = json.loads(output, object_pairs_hook=_unique_json_object)
    except json.JSONDecodeError:
        return _invalid_receipt(
            StandingResultFailure.INVALID_JSON,
            criteria_total=len(acceptance_evidence),
            clock=clock,
        )
    except ValueError:
        return _invalid_receipt(
            StandingResultFailure.RESULT_SCHEMA_INVALID,
            criteria_total=len(acceptance_evidence),
            clock=clock,
        )
    try:
        result = StandingStructuredResult.model_validate(raw_result)
    except ValueError:
        return _invalid_receipt(
            StandingResultFailure.RESULT_SCHEMA_INVALID,
            criteria_total=len(acceptance_evidence),
            clock=clock,
        )
    expected_criteria = tuple(f"A{index}" for index in range(1, len(acceptance_evidence) + 1))
    if tuple(item.criterion_id for item in result.criteria) != expected_criteria:
        return _invalid_result(result, StandingResultFailure.CRITERIA_MISMATCH, clock)
    expected_stops = tuple(f"S{index}" for index in range(1, len(stop_conditions) + 1))
    if tuple(item.stop_id for item in result.stop_conditions) != expected_stops:
        return _invalid_result(result, StandingResultFailure.STOP_CONDITIONS_MISMATCH, clock)
    root = _validated_root(evidence_root)
    if root is None:
        return _invalid_result(result, StandingResultFailure.EVIDENCE_ROOT_UNAVAILABLE, clock)
    sources = tuple(source for criterion in result.criteria for source in criterion.sources)
    manifest, source_failure = _build_source_manifest(root, sources)
    if source_failure is not None:
        return _invalid_result(result, source_failure, clock)
    met = sum(item.verdict is StandingCriterionVerdict.MET for item in result.criteria)
    complete = met == len(result.criteria) and not result.gaps
    blocked = met < len(result.criteria) and bool(result.gaps)
    if (result.result is StandingResultStatus.COMPLETE and not complete) or (
        result.result is StandingResultStatus.BLOCKED and not blocked
    ):
        return _invalid_result(result, StandingResultFailure.RESULT_INCONSISTENT, clock)
    return StandingResultReceipt(
        status=StandingResultContractStatus(result.result.value),
        criteria_met=met,
        criteria_total=len(result.criteria),
        verified_sources=len(manifest),
        checked_at=clock(),
        source_manifest=manifest,
        evidence_sha256=_manifest_sha256(manifest),
    )


def standing_result_evidence_status(
    receipt: StandingResultReceipt,
    evidence_root: Path | None,
) -> StandingEvidenceStatus:
    """Revalidate persisted source fingerprints without exposing source text."""
    if not receipt.source_manifest or receipt.evidence_sha256 is None:
        return StandingEvidenceStatus.MISSING
    root = _validated_root(evidence_root)
    if root is None:
        return StandingEvidenceStatus.MISSING
    sources = tuple(
        StandingSourceRef(path=item.path, line=item.line) for item in receipt.source_manifest
    )
    current, failure = _build_source_manifest(root, sources)
    if failure is StandingResultFailure.SOURCE_UNVERIFIED:
        return StandingEvidenceStatus.MISSING
    if failure is not None:
        return StandingEvidenceStatus.DRIFTED
    if current != receipt.source_manifest or _manifest_sha256(current) != receipt.evidence_sha256:
        return StandingEvidenceStatus.DRIFTED
    return StandingEvidenceStatus.CURRENT


def _validated_root(evidence_root: Path | None) -> Path | None:
    if evidence_root is None:
        return None
    try:
        root = evidence_root.expanduser().resolve(strict=True)
    except OSError:
        return None
    return root if root.is_dir() else None


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate standing result JSON key")
        result[key] = value
    return result


def _build_source_manifest(
    root: Path,
    sources: tuple[StandingSourceRef, ...],
) -> tuple[tuple[StandingVerifiedSource, ...], StandingResultFailure | None]:
    unique_sources = tuple(dict.fromkeys(sources))
    if len(unique_sources) > MAX_STANDING_VERIFIED_SOURCES:
        return (), StandingResultFailure.SOURCE_LIMIT_EXCEEDED
    cache: dict[Path, tuple[int, int, str] | StandingResultFailure] = {}
    manifest: list[StandingVerifiedSource] = []
    for source in unique_sources:
        evidence, failure = _verified_source(root, source, cache)
        if failure is not None:
            return (), failure
        assert evidence is not None
        manifest.append(evidence)
    return tuple(manifest), None


def _verified_source(
    root: Path,
    source: StandingSourceRef,
    cache: dict[Path, tuple[int, int, str] | StandingResultFailure],
) -> tuple[StandingVerifiedSource | None, StandingResultFailure | None]:
    candidate_path = Path(source.path)
    if candidate_path.is_absolute():
        return None, StandingResultFailure.SOURCE_UNVERIFIED
    try:
        candidate = (root / candidate_path).resolve(strict=True)
    except OSError:
        return None, StandingResultFailure.SOURCE_UNVERIFIED
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return None, StandingResultFailure.SOURCE_UNVERIFIED
    fact = cache.get(candidate)
    if fact is None:
        fact = _source_file_fact(candidate)
        cache[candidate] = fact
    if isinstance(fact, StandingResultFailure):
        return None, fact
    size_bytes, line_count, file_hash = fact
    if source.line > line_count:
        return None, StandingResultFailure.SOURCE_UNVERIFIED
    return (
        StandingVerifiedSource(
            path=candidate.relative_to(root).as_posix(),
            line=source.line,
            size_bytes=size_bytes,
            file_sha256=file_hash,
        ),
        None,
    )


def _source_file_fact(path: Path) -> tuple[int, int, str] | StandingResultFailure:
    try:
        with path.open("rb") as source_file:
            content = source_file.read(MAX_STANDING_SOURCE_FILE_BYTES + 1)
    except OSError:
        return StandingResultFailure.SOURCE_UNVERIFIED
    if len(content) > MAX_STANDING_SOURCE_FILE_BYTES:
        return StandingResultFailure.SOURCE_TOO_LARGE
    line_count = len(content.splitlines())
    return len(content), line_count, sha256(content).hexdigest()


def _manifest_sha256(manifest: tuple[StandingVerifiedSource, ...]) -> str:
    payload = [item.model_dump(mode="json") for item in manifest]
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _invalid_result(
    result: StandingStructuredResult,
    failure: StandingResultFailure,
    clock: Callable[[], datetime],
) -> StandingResultReceipt:
    return _invalid_receipt(failure, criteria_total=len(result.criteria), clock=clock)


def _invalid_receipt(
    failure: StandingResultFailure,
    *,
    criteria_total: int,
    clock: Callable[[], datetime],
) -> StandingResultReceipt:
    return StandingResultReceipt(
        status=StandingResultContractStatus.INVALID,
        criteria_met=0,
        criteria_total=max(1, criteria_total),
        verified_sources=0,
        checked_at=clock(),
        failure=failure,
    )
