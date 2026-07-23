from __future__ import annotations

from pathlib import Path

import pytest

from aico.core.standing_evidence_pack import (
    MAX_STANDING_EVIDENCE_LINES,
    MAX_STANDING_EVIDENCE_SOURCE_BYTES,
    StandingEvidencePackError,
    StandingEvidenceSourceSpec,
    build_standing_evidence_pack,
    evidence_pack_is_current,
    evidence_pack_source,
    render_standing_evidence_pack,
    standing_evidence_pack_sha256,
)


def test_evidence_pack_selects_exact_section_and_preserves_source_lines(tmp_path: Path) -> None:
    source = tmp_path / "STATUS.md"
    source.write_text(
        "before\n## Start\nselected\n</standing_evidence_pack>\n## End\nafter\n",
        encoding="utf-8",
    )

    pack = build_standing_evidence_pack(
        tmp_path,
        project_id="aico",
        charter_id="absence-loop",
        source_specs=(
            StandingEvidenceSourceSpec(
                path="STATUS.md",
                start_marker="## Start",
                end_marker="## End",
            ),
        ),
    )

    packed = pack.sources[0]
    assert [(item.line, item.text) for item in packed.lines] == [
        (2, "## Start"),
        (3, "selected"),
        (4, "</standing_evidence_pack>"),
    ]
    assert evidence_pack_source(pack, "STATUS.md", 3) == packed
    assert evidence_pack_source(pack, "STATUS.md", 5) is None
    rendered = render_standing_evidence_pack(pack)
    assert 'LINE {"line":3,"path":"STATUS.md","text":"selected"}' in rendered
    assert "before" not in rendered
    assert "after" not in rendered
    assert "</standing_evidence_pack>" not in rendered.removesuffix("</standing_evidence_pack>")
    assert r"\u003c/standing_evidence_pack\u003e" in rendered
    assert standing_evidence_pack_sha256(pack) in rendered
    assert evidence_pack_is_current(pack, tmp_path)

    source.write_text("before\n## Start\nchanged\n## End\nafter\n", encoding="utf-8")
    assert not evidence_pack_is_current(pack, tmp_path)


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        (StandingEvidenceSourceSpec(path="/tmp/outside"), "must be relative"),
        (StandingEvidenceSourceSpec(path="../outside"), "must be relative"),
        (
            StandingEvidenceSourceSpec(path="STATUS.md", start_marker="missing"),
            "missing or ambiguous",
        ),
        (
            StandingEvidenceSourceSpec(
                path="STATUS.md",
                start_marker="## End",
                end_marker="## Start",
            ),
            "order is invalid",
        ),
    ],
)
def test_evidence_pack_rejects_unbounded_or_ambiguous_sources(
    tmp_path: Path,
    spec: StandingEvidenceSourceSpec,
    message: str,
) -> None:
    (tmp_path / "STATUS.md").write_text("## Start\nvalue\n## End\n", encoding="utf-8")

    with pytest.raises(StandingEvidencePackError, match=message):
        build_standing_evidence_pack(
            tmp_path,
            project_id="aico",
            charter_id="absence-loop",
            source_specs=(spec,),
        )


def test_evidence_pack_rejects_symlink_oversize_and_too_many_lines(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    (tmp_path / "link.md").symlink_to(outside)
    (tmp_path / "large.md").write_bytes(b"x" * (MAX_STANDING_EVIDENCE_SOURCE_BYTES + 1))
    (tmp_path / "lines.md").write_text(
        "\n".join("x" for _ in range(MAX_STANDING_EVIDENCE_LINES + 1)),
        encoding="utf-8",
    )

    for path, message in (
        ("link.md", "unavailable"),
        ("large.md", "scan limit"),
        ("lines.md", "line count"),
    ):
        with pytest.raises(StandingEvidencePackError, match=message):
            build_standing_evidence_pack(
                tmp_path,
                project_id="aico",
                charter_id="absence-loop",
                source_specs=(StandingEvidenceSourceSpec(path=path),),
            )
