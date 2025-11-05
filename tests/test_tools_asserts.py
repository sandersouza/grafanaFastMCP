"""Tests for the Grafana Asserts tool helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.tools import asserts as asserts_module
from app.tools.asserts import _parse_time
from mcp.server.fastmcp import FastMCP


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def test_parse_time_accepts_iso_strings() -> None:
    timestamp = _parse_time("2024-01-02T03:04:05+00:00", "startTime")
    assert timestamp == int(
        datetime(
            2024,
            1,
            2,
            3,
            4,
            5,
            tzinfo=timezone.utc).timestamp() *
        1000)


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
    expected = datetime.now(timezone.utc) - \
        timedelta(hours=1) + timedelta(minutes=30)
    assert abs(result - int(expected.timestamp() * 1000)) < 5000


def test_parse_time_rejects_unknown_units() -> None:
    with pytest.raises(ValueError):
        _parse_time("now-5q", "startTime")


def test_parse_time_rejects_empty_string() -> None:
    with pytest.raises(ValueError):
        _parse_time("   ", "startTime")


def test_parse_time_accepts_numeric_epoch() -> None:
    assert _parse_time(1700000, "startTime") == 1700000
    assert _parse_time(1700.5, "startTime") == 1700


def test_parse_time_rejects_invalid_isoformat() -> None:
    with pytest.raises(ValueError):
        _parse_time("invalid", "startTime")


def test_get_assertions_builds_request(
        monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class DummyClient:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        async def post_json(self, path: str, json: dict[str, object]) -> str:
            captured["path"] = path
            captured["json"] = json
            return "summary"

    config = SimpleNamespace(url="https://grafana.local")
    monkeypatch.setattr(asserts_module, "get_grafana_config", lambda _: config)
    monkeypatch.setattr(asserts_module, "GrafanaClient", DummyClient)

    ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            session=SimpleNamespace(),
            request=None))
    args = {
        "startTime": "now-10m",
        "endTime": "now",
        "entityType": "service",
        "entityName": "checkout",
        "env": "prod",
        "site": "us-east",
        "namespace": "default",
    }
    result = asyncio.run(asserts_module._get_assertions(ctx, args))
    assert result == "summary"
    assert captured["path"].endswith("assertions/llm-summary")
    payload = captured["json"]
    assert payload["entityKeys"][0]["scope"]["env"] == "prod"


def test_get_assertions_tool_requires_context(
        monkeypatch: pytest.MonkeyPatch) -> None:
    app = FastMCP()
    asserts_module.register(app)
    tool = next(tool for tool in asyncio.run(app.list_tools())
                if tool.name == "get_assertions")
    with pytest.raises(ValueError):
        asyncio.run(tool.function(
            startTime="now",
            endTime="now",
            entityType="service",
            entityName="checkout",
            ctx=None,
        ))
