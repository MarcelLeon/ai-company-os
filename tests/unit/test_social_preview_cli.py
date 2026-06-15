from io import StringIO
from pathlib import Path

from aico.app.social_preview_cli import (
    GitHubSocialPreview,
    image_size,
    is_suspected_default_github_card,
    run_social_preview_cli,
)


def test_image_size_reads_png_dimensions() -> None:
    assert image_size(_png_bytes(1280, 640)) == (1280, 640)


def test_default_github_card_heuristic_requires_owner_upload(tmp_path: Path) -> None:
    asset = tmp_path / "social-preview.png"
    asset.write_bytes(_png_bytes(1280, 640))
    stdout = StringIO()

    exit_code = run_social_preview_cli(
        ["--repo", "MarcelLeon/ai-company-os", "--asset", str(asset)],
        stdout=stdout,
        repo_view_loader=lambda repo: GitHubSocialPreview(
            repo=repo,
            visibility="PUBLIC",
            open_graph_image_url=(
                "https://opengraph.githubassets.com/hash/MarcelLeon/ai-company-os"
            ),
        ),
        url_fetcher=lambda _url: _png_bytes(1200, 600),
    )

    assert exit_code == 2
    output = stdout.getvalue()
    assert "finding: GitHub still appears to serve the default repository card." in output
    assert "status: needs-owner-upload" in output


def test_non_default_social_preview_passes_with_spot_check_note(tmp_path: Path) -> None:
    asset = tmp_path / "social-preview.png"
    asset.write_bytes(_png_bytes(1280, 640))
    stdout = StringIO()

    exit_code = run_social_preview_cli(
        ["--repo", "MarcelLeon/ai-company-os", "--asset", str(asset)],
        stdout=stdout,
        repo_view_loader=lambda repo: GitHubSocialPreview(
            repo=repo,
            visibility="PUBLIC",
            open_graph_image_url="https://repository-images.githubusercontent.com/1/preview.png",
        ),
        url_fetcher=lambda _url: _png_bytes(1280, 640),
    )

    assert exit_code == 0
    output = stdout.getvalue()
    assert "finding: social preview does not match the known default-card heuristic." in output
    assert "status: ok" in output


def test_allow_default_keeps_exit_zero_without_calling_it_ok(tmp_path: Path) -> None:
    asset = tmp_path / "social-preview.png"
    asset.write_bytes(_png_bytes(1280, 640))
    stdout = StringIO()

    exit_code = run_social_preview_cli(
        ["--repo", "MarcelLeon/ai-company-os", "--asset", str(asset), "--allow-default"],
        stdout=stdout,
        repo_view_loader=lambda repo: GitHubSocialPreview(
            repo=repo,
            visibility="PUBLIC",
            open_graph_image_url=(
                "https://opengraph.githubassets.com/hash/MarcelLeon/ai-company-os"
            ),
        ),
        url_fetcher=lambda _url: _png_bytes(1200, 600),
    )

    assert exit_code == 0
    assert "status: default-allowed" in stdout.getvalue()


def test_default_card_heuristic_matches_current_github_shape() -> None:
    assert is_suspected_default_github_card(
        "https://opengraph.githubassets.com/hash/MarcelLeon/ai-company-os",
        (1200, 600),
    )
    assert not is_suspected_default_github_card(
        "https://repository-images.githubusercontent.com/1/preview.png",
        (1200, 600),
    )


def _png_bytes(width: int, height: int) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + width.to_bytes(
            4,
            "big",
        )
        + height.to_bytes(4, "big")
    )
