from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_public_quickstarts_use_unified_aico_cli() -> None:
    chinese_readme = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs/human/quickstart.md").read_text(encoding="utf-8")

    for command in ("uv run aico init", "uv run aico doctor", "uv run aico run"):
        assert command in chinese_readme
        assert command in quickstart

    public_docs = f"{chinese_readme}\n{quickstart}"
    assert "aico-phase1" not in public_docs
    assert "aico-release-room-demo" not in public_docs

    old_service_entrypoints = [line for line in quickstart.splitlines() if "aico-service" in line]
    assert old_service_entrypoints == [
        "uv run aico-service --repo . render | plutil -lint -  # operator diagnostics"
    ]
