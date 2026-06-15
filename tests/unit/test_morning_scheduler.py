from datetime import datetime

import pytest

from aico.app.morning_scheduler import parse_push_time, seconds_until_next_push


def test_parse_push_time_accepts_hh_mm() -> None:
    parsed = parse_push_time("08:30")

    assert parsed.hour == 8
    assert parsed.minute == 30


def test_parse_push_time_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="HH:MM"):
        parse_push_time("25:00")


def test_seconds_until_next_push_uses_today_when_time_is_future() -> None:
    seconds = seconds_until_next_push(
        parse_push_time("08:30"),
        now=datetime(2026, 6, 15, 8, 0, 0),
    )

    assert seconds == 30 * 60


def test_seconds_until_next_push_rolls_to_tomorrow() -> None:
    seconds = seconds_until_next_push(
        parse_push_time("08:30"),
        now=datetime(2026, 6, 15, 9, 0, 0),
    )

    assert seconds == 23.5 * 60 * 60
