"""Tests for Grafana Sift investigation helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from app.tools import sift
from mcp.server.fastmcp import FastMCP


def test_time_range_defaults_and_validation() -> None:
    start, end = sift._time_range(None, None)
    assert isinstance(start, datetime)
    assert isinstance(end, datetime)
    with pytest.raises(ValueError):
        sift._time_range(start=end, end=start)


def test_parse_datetime_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    reference = datetime(2024, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(sift, "_now", lambda: reference)

    assert sift._parse_datetime("now") == reference

    result = sift._parse_datetime("now-1h30m")
    assert isinstance(result, datetime)
    assert result == reference - timedelta(hours=1, minutes=30)

    future = sift._parse_datetime("now+30m")
    assert future == reference + timedelta(minutes=30)

    iso = sift._parse_datetime("2024-01-02T00:00:00Z")
    assert iso == datetime(2024, 1, 2, tzinfo=timezone.utc)

    with pytest.raises(ValueError):
        sift._parse_datetime("now-")


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    config = SimpleNamespace(url="https://grafana.local")
    monkeypatch.setattr(sift, "get_grafana_config", lambda _: config)
    return SimpleNamespace()


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    data: Dict[str, Any] = {}

    async def fake_request(ctx: Any,
                           method: str,
                           path: str,
                           params: Dict[str,
                                        Any] | None = None,
                           json: Any = None):
        data["method"] = method
        data["path"] = path
        data["json"] = json

        class DummyResponse:
            def json(self_inner) -> Dict[str, Any]:
                return {"data": {"id": "123", "status": "pending"}}
        return DummyResponse()

    async def fake_get_json(ctx: Any,
                            path: str,
                            params: Dict[str,
                                         Any] | None = None) -> Dict[str,
                                                                     Any]:
        data.setdefault("get_json", []).append((path, params))
        if path.endswith("/analyses"):
            return {"data": [{"id": "1", "name": "ErrorPatternLogs"}]}
        if path.endswith("/investigations"):
            return {
                "data": [{"id": "123", "status": "finished", "name": "Investigation"}]}
        return {
            "data": {
                "id": "123",
                "status": "finished",
                "name": "Investigation"}}

    monkeypatch.setattr(sift, "_sift_request", fake_request)
    monkeypatch.setattr(sift, "_sift_get_json", fake_get_json)
    return data


def test_create_investigation(
        ctx: SimpleNamespace, captured: Dict[str, Any]) -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(minutes=5)
    result = asyncio.run(
        sift._create_investigation(
            ctx,
            name="Investigation",
            labels={"service": "api"},
            checks=["Error"],
            start=start,
            end=end,
        )
    )
    assert result["id"] == "123"
    payload = captured["json"]
    assert payload["requestData"]["checks"] == ["Error"]


def test_list_and_get_helpers(
        ctx: SimpleNamespace, captured: Dict[str, Any]) -> None:
    investigations = asyncio.run(sift._list_investigations(ctx, limit=5))
    assert investigations[0]["id"] == "123"
    investigation = asyncio.run(sift._get_investigation(ctx, "123"))
    assert investigation["status"] == "finished"
    analyses = asyncio.run(sift._get_analyses(ctx, "123"))
    assert analyses[0]["name"] == "ErrorPatternLogs"


def test_wait_for_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        {"id": "1", "status": "pending"},
        {"id": "1", "status": "finished"},
    ]

    async def fake_get_investigation(ctx: Any, _id: str) -> Dict[str, Any]:
        return responses.pop(0)

    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(sift, "_get_investigation", fake_get_investigation)
    monkeypatch.setattr(
        sift, "_now", lambda: datetime(
            2024, 1, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    ctx = SimpleNamespace()

    result = asyncio.run(sift._wait_for_completion(ctx, "1"))
    assert result["status"] == "finished"


def test_find_analysis() -> None:
    analyses = [{"name": "ErrorPatternLogs"}]
    found = sift._find_analysis(analyses, "ErrorPatternLogs")
    assert found["name"] == "ErrorPatternLogs"
    with pytest.raises(ValueError):
        sift._find_analysis(analyses, "Missing")


def test_run_check(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_create(ctx: Any, *args: Any, **
                          kwargs: Any) -> Dict[str, Any]:
        return {"id": "1"}

    async def fake_wait(ctx: Any, investigation_id: str) -> Dict[str, Any]:
        return {"id": investigation_id, "status": "finished"}

    async def fake_analyses(
            ctx: Any, investigation_id: str) -> List[Dict[str, Any]]:
        return [{"name": "ErrorPatternLogs", "result": "ok"}]

    monkeypatch.setattr(sift, "_create_investigation", fake_create)
    monkeypatch.setattr(sift, "_wait_for_completion", fake_wait)
    monkeypatch.setattr(sift, "_get_analyses", fake_analyses)

    ctx = SimpleNamespace()
    result = asyncio.run(
        sift._run_check(
            ctx,
            "ErrorPatternLogs",
            name="Investigation",
            labels={"service": "api"},
            start=None,
            end=None,
        )
    )
    assert result["result"] == "ok"


def test_sift_tools_require_context() -> None:
    app = FastMCP()
    sift.register(app)
    tools = asyncio.run(app.list_tools())
    tool = next(tool for tool in tools if tool.name ==
                "list_sift_investigations")
    with pytest.raises(ValueError):
        asyncio.run(tool.function(ctx=None))
