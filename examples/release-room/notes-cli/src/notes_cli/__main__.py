from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    store = Path(args.store)
    notes = _load_notes(store)
    if args.command == "add":
        note = _add_note(notes, args.text)
        _save_notes(store, notes)
        print(f"added note {note['id']}")
        return 0
    if args.command == "list":
        _print_notes(notes)
        return 0
    if args.command == "done":
        if not _mark_done(notes, args.note_id):
            print(f"note not found: {args.note_id}")
            return 0
        _save_notes(store, notes)
        print(f"done note {args.note_id}")
        return 0
    parser.print_help()
    return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="notes-cli")
    parser.add_argument("--store", default="notes.json", help="Path to the local notes JSON file.")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Add a note.")
    add_parser.add_argument("text")

    subparsers.add_parser("list", help="List notes.")

    done_parser = subparsers.add_parser("done", help="Mark a note as done.")
    done_parser.add_argument("note_id", type=int)
    return parser


def _load_notes(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_notes(path: Path, notes: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(notes, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _add_note(notes: list[dict[str, Any]], text: str) -> dict[str, Any]:
    note = {
        "id": _next_id(notes),
        "text": text,
        "done": False,
        "created_at": datetime.now(UTC).isoformat(),
    }
    notes.append(note)
    return note


def _next_id(notes: list[dict[str, Any]]) -> int:
    if not notes:
        return 1
    return max(int(note["id"]) for note in notes) + 1


def _mark_done(notes: list[dict[str, Any]], note_id: int) -> bool:
    for note in notes:
        if note["id"] == note_id:
            note["done"] = True
            return True
    return False


def _print_notes(notes: list[dict[str, Any]]) -> None:
    if not notes:
        print("no notes")
        return
    for note in notes:
        marker = "x" if note["done"] else " "
        print(f"{note['id']}. [{marker}] {note['text']}")


if __name__ == "__main__":
    raise SystemExit(main())
