from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.core.standing_evidence_pack import (
    StandingEvidenceSourceSpec,
    build_standing_evidence_pack,
    standing_evidence_pack_sha256,
)
from aico.core.standing_result import (
    MAX_STANDING_CRITERIA,
    MAX_STANDING_LIST_ITEMS,
    MAX_STANDING_PATH_CHARS,
    MAX_STANDING_RESULT_CHARS,
    MAX_STANDING_SOURCE_FILE_BYTES,
    MAX_STANDING_SOURCES_PER_CRITERION,
    MAX_STANDING_STOPS,
    MAX_STANDING_TEXT_CHARS,
    MAX_STANDING_VERIFIED_SOURCES,
    StandingEvidenceStatus,
    StandingResultContractStatus,
    StandingResultFailure,
    standing_result_evidence_status,
    validate_standing_result,
)

_NOW = datetime(2026, 7, 21, 9, tzinfo=UTC)


def test_complete_standing_result_verifies_local_sources(tmp_path: Path) -> None:
    (tmp_path / "STATUS.md").write_text("first\nsecond\n", encoding="utf-8")

    receipt = validate_standing_result(
        _result(),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        clock=lambda: _NOW,
    )

    assert receipt.status is StandingResultContractStatus.COMPLETE
    assert receipt.criteria_met == 2
    assert receipt.criteria_total == 2
    assert receipt.verified_sources == 2
    assert len(receipt.source_manifest) == 2
    assert receipt.evidence_sha256 is not None
    assert standing_result_evidence_status(receipt, tmp_path) is StandingEvidenceStatus.CURRENT
    assert receipt.checked_at == _NOW
    assert receipt.failure is None


def test_blocked_standing_result_is_distinct_from_invalid(tmp_path: Path) -> None:
    (tmp_path / "STATUS.md").write_text("first\nsecond\n", encoding="utf-8")
    payload = json.loads(_result())
    payload["result"] = "blocked"
    payload["criteria"][1]["verdict"] = "unmet"
    payload["gaps"] = ["second criterion is not yet met"]

    receipt = validate_standing_result(
        json.dumps(payload),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        clock=lambda: _NOW,
    )

    assert receipt.status is StandingResultContractStatus.BLOCKED
    assert receipt.criteria_met == 1
    assert receipt.failure is None


@pytest.mark.parametrize(
    ("mutation", "failure"),
    [
        (lambda payload: payload["criteria"].reverse(), StandingResultFailure.CRITERIA_MISMATCH),
        (
            lambda payload: payload["stop_conditions"][0].update({"stop_id": "S2"}),
            StandingResultFailure.STOP_CONDITIONS_MISMATCH,
        ),
        (
            lambda payload: payload.update({"result": "complete", "gaps": ["not done"]}),
            StandingResultFailure.RESULT_INCONSISTENT,
        ),
    ],
)
def test_standing_result_rejects_contract_mismatch(
    tmp_path: Path,
    mutation: object,
    failure: StandingResultFailure,
) -> None:
    (tmp_path / "STATUS.md").write_text("first\nsecond\n", encoding="utf-8")
    payload = json.loads(_result())
    mutation(payload)  # type: ignore[operator]

    receipt = validate_standing_result(
        json.dumps(payload),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        clock=lambda: _NOW,
    )

    assert receipt.status is StandingResultContractStatus.INVALID
    assert receipt.failure is failure


@pytest.mark.parametrize("source_path", ["../outside.md", "/tmp/outside.md", "missing.md"])
def test_standing_result_rejects_unverified_source(
    tmp_path: Path,
    source_path: str,
) -> None:
    (tmp_path / "STATUS.md").write_text("first\nsecond\n", encoding="utf-8")
    payload = json.loads(_result())
    payload["criteria"][0]["sources"][0]["path"] = source_path

    receipt = validate_standing_result(
        json.dumps(payload),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        clock=lambda: _NOW,
    )

    assert receipt.failure is StandingResultFailure.SOURCE_UNVERIFIED


def test_standing_result_rejects_missing_line_or_root(tmp_path: Path) -> None:
    (tmp_path / "STATUS.md").write_text("first\n", encoding="utf-8")
    missing_line = validate_standing_result(
        _result(),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        clock=lambda: _NOW,
    )
    missing_root = validate_standing_result(
        _result(),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=None,
        clock=lambda: _NOW,
    )

    assert missing_line.failure is StandingResultFailure.SOURCE_UNVERIFIED
    assert missing_root.failure is StandingResultFailure.EVIDENCE_ROOT_UNAVAILABLE


def test_standing_result_detects_source_drift_and_missing_file(tmp_path: Path) -> None:
    source = tmp_path / "STATUS.md"
    source.write_text("first\nsecond\n", encoding="utf-8")
    receipt = validate_standing_result(
        _result(),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        clock=lambda: _NOW,
    )

    source.write_text("changed\nsecond\n", encoding="utf-8")
    assert standing_result_evidence_status(receipt, tmp_path) is StandingEvidenceStatus.DRIFTED

    source.unlink()
    assert standing_result_evidence_status(receipt, tmp_path) is StandingEvidenceStatus.MISSING


def test_standing_result_rejects_oversized_evidence_file(tmp_path: Path) -> None:
    (tmp_path / "STATUS.md").write_bytes(b"x" * (MAX_STANDING_SOURCE_FILE_BYTES + 1))

    receipt = validate_standing_result(
        _result(),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        clock=lambda: _NOW,
    )

    assert receipt.failure is StandingResultFailure.SOURCE_TOO_LARGE


def test_standing_result_accepts_only_current_lines_from_bounded_pack(tmp_path: Path) -> None:
    source = tmp_path / "STATUS.md"
    source.write_text(
        "x" * (MAX_STANDING_SOURCE_FILE_BYTES + 1) + "\n## Selected\nfirst\nsecond\n## End\n",
        encoding="utf-8",
    )
    pack = build_standing_evidence_pack(
        tmp_path,
        project_id="aico",
        charter_id="absence-loop",
        source_specs=(
            StandingEvidenceSourceSpec(
                path="STATUS.md",
                start_marker="## Selected",
                end_marker="## End",
            ),
        ),
    )
    payload = json.loads(_result())
    payload["criteria"][0]["sources"][0]["line"] = 3
    payload["criteria"][1]["sources"][0]["line"] = 4

    direct = validate_standing_result(
        json.dumps(payload),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        clock=lambda: _NOW,
    )
    receipt = validate_standing_result(
        json.dumps(payload),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        evidence_pack=pack,
        clock=lambda: _NOW,
    )

    assert direct.failure is StandingResultFailure.SOURCE_TOO_LARGE
    assert receipt.status is StandingResultContractStatus.COMPLETE
    assert receipt.evidence_pack_sha256 == standing_evidence_pack_sha256(pack)
    assert standing_result_evidence_status(receipt, tmp_path) is StandingEvidenceStatus.CURRENT

    payload["criteria"][0]["sources"][0]["line"] = 1
    unlisted = validate_standing_result(
        json.dumps(payload),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        evidence_pack=pack,
        clock=lambda: _NOW,
    )
    assert unlisted.failure is StandingResultFailure.SOURCE_UNVERIFIED

    source.write_text(source.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
    drifted = validate_standing_result(
        json.dumps(payload),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        evidence_pack=pack,
        clock=lambda: _NOW,
    )
    assert drifted.failure is StandingResultFailure.EVIDENCE_PACK_DRIFTED
    assert standing_result_evidence_status(receipt, tmp_path) is StandingEvidenceStatus.DRIFTED


def test_standing_result_rejects_too_many_verified_sources(tmp_path: Path) -> None:
    source_lines = "\n".join(f"line {index}" for index in range(1, 40)) + "\n"
    (tmp_path / "STATUS.md").write_text(source_lines, encoding="utf-8")
    payload = json.loads(_result())
    criteria = []
    next_line = 1
    criterion_count = (MAX_STANDING_VERIFIED_SOURCES // MAX_STANDING_SOURCES_PER_CRITERION) + 1
    for criterion_index in range(1, criterion_count + 1):
        source_count = min(
            MAX_STANDING_SOURCES_PER_CRITERION,
            MAX_STANDING_VERIFIED_SOURCES + 1 - (next_line - 1),
        )
        sources = [
            {"path": "STATUS.md", "line": line}
            for line in range(next_line, next_line + source_count)
        ]
        next_line += source_count
        criteria.append(
            {
                "criterion_id": f"A{criterion_index}",
                "verdict": "met",
                "evidence": "bounded evidence",
                "sources": sources,
            }
        )
    payload["criteria"] = criteria

    receipt = validate_standing_result(
        json.dumps(payload),
        acceptance_evidence=tuple(f"criterion {index}" for index in range(1, criterion_count + 1)),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        clock=lambda: _NOW,
    )

    assert next_line - 1 == MAX_STANDING_VERIFIED_SOURCES + 1
    assert receipt.failure is StandingResultFailure.SOURCE_LIMIT_EXCEEDED


def test_standing_result_rejects_invalid_json() -> None:
    receipt = validate_standing_result(
        "not-json",
        acceptance_evidence=("one",),
        stop_conditions=("stop",),
        evidence_root=Path.cwd(),
        clock=lambda: _NOW,
    )

    assert receipt.status is StandingResultContractStatus.INVALID
    assert receipt.failure is StandingResultFailure.INVALID_JSON


def test_standing_result_rejects_duplicate_json_keys() -> None:
    output = _result().replace('"version": 1,', '"version": 1, "version": 1,', 1)

    receipt = validate_standing_result(
        output,
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=Path.cwd(),
        clock=lambda: _NOW,
    )

    assert receipt.failure is StandingResultFailure.RESULT_SCHEMA_INVALID


def test_standing_result_rejects_oversized_envelope_before_json_parse() -> None:
    receipt = validate_standing_result(
        "x" * (MAX_STANDING_RESULT_CHARS + 1),
        acceptance_evidence=("one",),
        stop_conditions=("stop",),
        evidence_root=Path.cwd(),
        clock=lambda: _NOW,
    )

    assert receipt.status is StandingResultContractStatus.INVALID
    assert receipt.failure is StandingResultFailure.RESULT_TOO_LARGE


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update({"summary": "x" * (MAX_STANDING_TEXT_CHARS + 1)}),
        lambda payload: payload.update({"gaps": ["gap"] * (MAX_STANDING_LIST_ITEMS + 1)}),
        lambda payload: payload["criteria"][0].update(
            {"sources": [{"path": "STATUS.md", "line": 1}] * 9}
        ),
    ],
)
def test_standing_result_rejects_field_count_or_length_overflow(
    tmp_path: Path,
    mutation: object,
) -> None:
    (tmp_path / "STATUS.md").write_text("first\nsecond\n", encoding="utf-8")
    payload = json.loads(_result())
    mutation(payload)  # type: ignore[operator]

    receipt = validate_standing_result(
        json.dumps(payload),
        acceptance_evidence=("one", "two"),
        stop_conditions=("stop",),
        evidence_root=tmp_path,
        clock=lambda: _NOW,
    )

    assert receipt.status is StandingResultContractStatus.INVALID
    assert receipt.failure is StandingResultFailure.RESULT_SCHEMA_INVALID


def test_standing_result_schema_matches_local_resource_limits() -> None:
    schema_path = (
        Path(__file__).parents[2] / "src/aico/adapter/schemas/standing-result-v1.schema.json"
    )
    properties = json.loads(schema_path.read_text(encoding="utf-8"))["properties"]
    criterion = properties["criteria"]["items"]["properties"]
    stop = properties["stop_conditions"]

    assert properties["summary"]["maxLength"] == MAX_STANDING_TEXT_CHARS
    assert properties["criteria"]["maxItems"] == MAX_STANDING_CRITERIA
    assert criterion["evidence"]["maxLength"] == MAX_STANDING_TEXT_CHARS
    assert criterion["sources"]["maxItems"] == MAX_STANDING_SOURCES_PER_CRITERION
    assert criterion["sources"]["items"]["properties"]["path"]["maxLength"] == (
        MAX_STANDING_PATH_CHARS
    )
    assert stop["maxItems"] == MAX_STANDING_STOPS
    assert properties["gaps"]["maxItems"] == MAX_STANDING_LIST_ITEMS
    assert properties["risks"]["maxItems"] == MAX_STANDING_LIST_ITEMS
    assert properties["next_actions"]["maxItems"] == MAX_STANDING_LIST_ITEMS


def _result() -> str:
    return json.dumps(
        {
            "version": 1,
            "result": "complete",
            "summary": "bounded inspection complete",
            "criteria": [
                {
                    "criterion_id": "A1",
                    "verdict": "met",
                    "evidence": "first line",
                    "sources": [{"path": "STATUS.md", "line": 1}],
                },
                {
                    "criterion_id": "A2",
                    "verdict": "met",
                    "evidence": "second line",
                    "sources": [{"path": "STATUS.md", "line": 2}],
                },
            ],
            "stop_conditions": [{"stop_id": "S1", "observed": True}],
            "gaps": [],
            "risks": [],
            "next_actions": ["wait for the next bounded schedule"],
        }
    )
