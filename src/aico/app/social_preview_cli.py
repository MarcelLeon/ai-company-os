"""Check whether GitHub still appears to serve the default social preview card."""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO
from urllib.parse import urlparse

DEFAULT_REPO = "MarcelLeon/ai-company-os"
DEFAULT_ASSET = Path("docs/assets/social-preview.png")


@dataclass(frozen=True)
class GitHubSocialPreview:
    repo: str
    visibility: str
    open_graph_image_url: str


@dataclass(frozen=True)
class SocialPreviewCheck:
    repo: str
    visibility: str
    open_graph_image_url: str
    remote_size: tuple[int, int]
    local_size: tuple[int, int]
    suspected_default_card: bool


RepoViewLoader = Callable[[str], GitHubSocialPreview]
UrlFetcher = Callable[[str], bytes]


def run_social_preview_cli(
    argv: list[str] | None = None,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    repo_view_loader: RepoViewLoader | None = None,
    url_fetcher: UrlFetcher | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    loader = repo_view_loader or load_github_social_preview
    fetcher = url_fetcher or fetch_url
    try:
        check = check_social_preview(args.repo, args.asset, loader=loader, fetcher=fetcher)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        stderr.write(f"social preview check failed: {exc}\n")
        return 1

    stdout.write(format_check(check))
    if check.suspected_default_card:
        if args.allow_default:
            stdout.write("status: default-allowed\n")
            return 0
        stdout.write("status: needs-owner-upload\n")
        return 2
    stdout.write("status: ok\n")
    return 0


def main() -> None:
    raise SystemExit(run_social_preview_cli())


def check_social_preview(
    repo: str,
    asset_path: Path,
    *,
    loader: RepoViewLoader | None = None,
    fetcher: UrlFetcher | None = None,
) -> SocialPreviewCheck:
    repo_view_loader = loader or load_github_social_preview
    url_fetcher = fetcher or fetch_url
    preview = repo_view_loader(repo)
    remote_bytes = url_fetcher(preview.open_graph_image_url)
    remote_size = image_size(remote_bytes)
    local_size = image_size(asset_path.read_bytes())
    return SocialPreviewCheck(
        repo=preview.repo,
        visibility=preview.visibility,
        open_graph_image_url=preview.open_graph_image_url,
        remote_size=remote_size,
        local_size=local_size,
        suspected_default_card=is_suspected_default_github_card(
            preview.open_graph_image_url,
            remote_size,
        ),
    )


def load_github_social_preview(repo: str) -> GitHubSocialPreview:
    completed = subprocess.run(
        [
            "gh",
            "repo",
            "view",
            repo,
            "--json",
            "nameWithOwner,visibility,openGraphImageUrl",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    return GitHubSocialPreview(
        repo=str(payload["nameWithOwner"]),
        visibility=str(payload["visibility"]),
        open_graph_image_url=str(payload["openGraphImageUrl"]),
    )


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "aico-social-preview-check"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read()
    if not isinstance(data, bytes):
        raise ValueError("downloaded response was not bytes")
    return data


def image_size(data: bytes) -> tuple[int, int]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        if len(data) < 24:
            raise ValueError("truncated PNG")
        width, height = struct.unpack(">II", data[16:24])
        return width, height
    if data.startswith((b"GIF87a", b"GIF89a")):
        if len(data) < 10:
            raise ValueError("truncated GIF")
        width, height = struct.unpack("<HH", data[6:10])
        return width, height
    if data.startswith(b"\xff\xd8"):
        return _jpeg_size(data)
    raise ValueError("unsupported image format")


def is_suspected_default_github_card(url: str, size: tuple[int, int]) -> bool:
    parsed = urlparse(url)
    return parsed.netloc == "opengraph.githubassets.com" and size == (1200, 600)


def format_check(check: SocialPreviewCheck) -> str:
    lines = [
        f"repo: {check.repo}",
        f"visibility: {check.visibility}",
        f"openGraphImageUrl: {check.open_graph_image_url}",
        f"remote_image: {check.remote_size[0]}x{check.remote_size[1]}",
        f"local_asset: {check.local_size[0]}x{check.local_size[1]}",
    ]
    if check.suspected_default_card:
        lines.append("finding: GitHub still appears to serve the default repository card.")
        lines.append(f"action: upload {DEFAULT_ASSET} in GitHub Settings -> Social preview.")
    else:
        lines.append("finding: social preview does not match the known default-card heuristic.")
        lines.append("action: visually spot-check the image once before tagging.")
    return "\n".join(lines) + "\n"


def _jpeg_size(data: bytes) -> tuple[int, int]:
    index = 2
    while index < len(data):
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            break
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            raise ValueError("truncated JPEG segment")
        segment_length = struct.unpack(">H", data[index : index + 2])[0]
        if segment_length < 2 or index + segment_length > len(data):
            raise ValueError("invalid JPEG segment")
        if 0xC0 <= marker <= 0xC3:
            if segment_length < 7:
                raise ValueError("invalid JPEG SOF segment")
            height, width = struct.unpack(">HH", data[index + 3 : index + 7])
            return width, height
        index += segment_length
    raise ValueError("JPEG size marker not found")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aico-github-social-preview")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository owner/name")
    parser.add_argument(
        "--asset",
        default=DEFAULT_ASSET,
        type=Path,
        help="Local social preview asset expected to be uploaded",
    )
    parser.add_argument(
        "--allow-default",
        action="store_true",
        help="Return success even when GitHub still appears to serve the default card",
    )
    return parser
