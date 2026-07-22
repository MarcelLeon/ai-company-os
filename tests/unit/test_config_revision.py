from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aico.app.config_revision import (
    ConfigRevisionError,
    capture_config_revision,
    verify_config_checkout,
)


def test_capture_and_verify_bind_clean_revision_and_tracked_configs(tmp_path: Path) -> None:
    checkout = _repo(tmp_path)
    evidence, captured = capture_config_revision(
        checkout,
        Path("config/projects.json"),
        Path("config/personas.json"),
        expected_revision=_head(checkout),
    )
    verified = verify_config_checkout(evidence, checkout)

    assert captured.operation == "capture"
    assert verified.operation == "verify-checkout"
    assert verified.revision == _git(checkout, "rev-parse", "HEAD")
    assert verified.tree_oid == _git(checkout, "rev-parse", "HEAD^{tree}")
    assert verified.config_count == 2
    assert verified.clean is True
    assert evidence.persona_source == "tracked_file"
    assert tuple(config.role for config in evidence.configs) == ("project", "persona")
    assert tuple(config.relative_path for config in evidence.configs) == (
        "config/projects.json",
        "config/personas.json",
    )


def test_built_in_personas_are_bound_to_code_revision(tmp_path: Path) -> None:
    checkout = _repo(tmp_path)

    evidence, summary = capture_config_revision(
        checkout,
        Path("config/projects.json"),
        expected_revision=_head(checkout),
    )

    assert evidence.persona_source == "built_in_at_revision"
    assert len(evidence.configs) == 1
    assert summary.config_count == 1
    assert verify_config_checkout(evidence, checkout).persona_source == "built_in_at_revision"


@pytest.mark.parametrize("dirty_kind", ["tracked", "untracked"])
def test_capture_rejects_dirty_checkout(tmp_path: Path, dirty_kind: str) -> None:
    checkout = _repo(tmp_path)
    if dirty_kind == "tracked":
        (checkout / "app.py").write_text("print('changed')\n")
    else:
        (checkout / "unreviewed.py").write_text("print('unreviewed')\n")

    with pytest.raises(ConfigRevisionError, match="clean"):
        capture_config_revision(
            checkout,
            Path("config/projects.json"),
            expected_revision=_head(checkout),
        )


def test_verify_rejects_wrong_revision_and_config_drift(tmp_path: Path) -> None:
    checkout = _repo(tmp_path)
    evidence, _ = capture_config_revision(
        checkout,
        Path("config/projects.json"),
        expected_revision=_head(checkout),
    )
    (checkout / "app.py").write_text("print('reviewed v2')\n")
    _commit(checkout, "second")

    with pytest.raises(ConfigRevisionError, match="revision"):
        verify_config_checkout(evidence, checkout)

    _git_run(checkout, "checkout", "--detach", evidence.revision)
    (checkout / "config/projects.json").write_text('{"projects":["drift"]}\n')
    with pytest.raises(ConfigRevisionError, match="clean"):
        verify_config_checkout(evidence, checkout)


def test_capture_rejects_external_symlink_and_untracked_config(tmp_path: Path) -> None:
    checkout = _repo(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n")

    with pytest.raises(ConfigRevisionError, match="inside"):
        capture_config_revision(checkout, outside, expected_revision=_head(checkout))

    link = checkout / "config/linked.json"
    link.symlink_to(checkout / "config/projects.json")
    with pytest.raises(ConfigRevisionError, match="clean"):
        capture_config_revision(checkout, link, expected_revision=_head(checkout))

    link.unlink()
    untracked = checkout / "config/untracked.json"
    untracked.write_text("{}\n")
    with pytest.raises(ConfigRevisionError, match="clean"):
        capture_config_revision(checkout, untracked, expected_revision=_head(checkout))


def test_errors_do_not_leak_checkout_path_or_config_payload(tmp_path: Path) -> None:
    checkout = _repo(tmp_path)
    secret = "merchant-private-config-value"
    config = checkout / "config/projects.json"
    config.write_text('{"secret":"' + secret + '"}\n')

    with pytest.raises(ConfigRevisionError) as captured:
        capture_config_revision(checkout, config, expected_revision=_head(checkout))
    rendered = str(captured.value)
    assert str(checkout) not in rendered
    assert secret not in rendered


def test_capture_requires_independently_selected_revision(tmp_path: Path) -> None:
    checkout = _repo(tmp_path)

    with pytest.raises(ConfigRevisionError, match="owner-reviewed"):
        capture_config_revision(
            checkout,
            Path("config/projects.json"),
            expected_revision="0" * 40,
        )

    with pytest.raises(ConfigRevisionError, match="invalid"):
        capture_config_revision(
            checkout,
            Path("config/projects.json"),
            expected_revision="main",
        )


def _repo(tmp_path: Path) -> Path:
    checkout = tmp_path / "checkout"
    (checkout / "config").mkdir(parents=True)
    (checkout / "config/projects.json").write_text('{"projects":["aico"]}\n')
    (checkout / "config/personas.json").write_text('{"personas":["lead"]}\n')
    (checkout / "app.py").write_text("print('reviewed')\n")
    _git_run(checkout, "init", "-q")
    _git_run(checkout, "add", ".")
    _commit(checkout, "initial")
    return checkout


def _commit(checkout: Path, message: str) -> None:
    _git_run(checkout, "add", ".")
    _git_run(
        checkout,
        "-c",
        "user.name=AICO Test",
        "-c",
        "user.email=aico@example.invalid",
        "commit",
        "-q",
        "-m",
        message,
    )


def _git(checkout: Path, *args: str) -> str:
    return _git_run(checkout, *args).stdout.strip()


def _head(checkout: Path) -> str:
    return _git(checkout, "rev-parse", "HEAD")


def _git_run(checkout: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    )
