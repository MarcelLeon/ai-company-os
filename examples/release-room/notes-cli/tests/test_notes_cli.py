from __future__ import annotations

import json

from notes_cli.__main__ import main


def test_add_and_list_notes(tmp_path, capsys) -> None:
    store = tmp_path / "notes.json"

    assert main(["--store", str(store), "add", "Ship release room"]) == 0
    assert main(["--store", str(store), "list"]) == 0

    output = capsys.readouterr().out
    assert "added note 1" in output
    assert "1. [ ] Ship release room" in output


def test_done_marks_note(tmp_path, capsys) -> None:
    store = tmp_path / "notes.json"

    assert main(["--store", str(store), "add", "Write tests"]) == 0
    assert main(["--store", str(store), "done", "1"]) == 0

    notes = json.loads(store.read_text(encoding="utf-8"))
    assert notes[0]["done"] is True
    assert "done note 1" in capsys.readouterr().out
