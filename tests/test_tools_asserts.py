"""Tests for the Grafana Asserts tool helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.tools.asserts import _parse_time


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def test_parse_time_accepts_iso_strings() -> None:
    timestamp = _parse_time("2024-01-02T03:04:05+00:00", "startTime")
    assert timestamp == int(datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc).timestamp() * 1000)


def test_parse_time_accepts_relative_now() -> None:
    before = _now_ms()
    value = _parse_time("now", "startTime")
    after = _now_ms()
    assert before <= value <= after


def test_parse_time_accepts_now_minus_duration() -> None:
    result = _parse_time("now-1h", "startTime")
    expected = datetime.now(timezone.utc) - timedelta(hours=1)
    difference_ms = abs(result - int(expected.timestamp() * 1000))
    assert difference_ms < 5000  # allow a small delta for runtime delay


def test_parse_time_accepts_combined_offsets() -> None:
    result = _parse_time("now-1h+30m", "startTime")
    expected = datetime.now(timezone.utc) - timedelta(hours=1) + timedelta(minutes=30)
    assert abs(result - int(expected.timestamp() * 1000)) < 5000


def test_parse_time_rejects_unknown_units() -> None:
    with pytest.raises(ValueError):
        _parse_time("now-5q", "startTime")


def test_parse_time_rejects_empty_string() -> None:
    with pytest.raises(ValueError):
        _parse_time("   ", "startTime")
