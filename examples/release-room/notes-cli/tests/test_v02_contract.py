from __future__ import annotations

import json

import pytest
from notes_cli.__main__ import main

pytestmark = pytest.mark.skip(reason="v0.2 release-room team should enable and pass these tests.")


def test_add_tags_and_search_by_tag(tmp_path, capsys) -> None:
    store = tmp_path / "notes.json"

    assert main(["--store", str(store), "add", "Draft release notes", "--tag", "release"]) == 0
    assert main(["--store", str(store), "search", "release"]) == 0

    assert "Draft release notes" in capsys.readouterr().out


def test_export_json_includes_release_fields(tmp_path, capsys) -> None:
    store = tmp_path / "notes.json"

    assert main(["--store", str(store), "add", "Run verification", "--tag", "qa"]) == 0
    assert main(["--store", str(store), "export", "--format", "json"]) == 0

    exported = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert exported[0]["id"] == 1
    assert exported[0]["text"] == "Run verification"
    assert exported[0]["done"] is False
    assert exported[0]["tags"] == ["qa"]
    assert "created_at" in exported[0]


def test_done_unknown_id_returns_nonzero(tmp_path) -> None:
    store = tmp_path / "notes.json"

    assert main(["--store", str(store), "done", "999"]) != 0
