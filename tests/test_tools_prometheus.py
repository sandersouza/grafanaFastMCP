"""Tests for Prometheus helper functions."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest

from app.tools import prometheus
from app.tools._label_matching import LabelMatcher, Selector
from mcp.server.fastmcp import FastMCP


def test_parse_duration_and_time_expression() -> None:
    delta = prometheus._parse_duration("1h30m10s")
    assert int(delta.total_seconds()) == 5410
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert prometheus._parse_time_expression(
        "now-1h", now) == now - timedelta(hours=1)
    assert prometheus._parse_time_expression(
        "2024-01-01T00:00:00Z",
        now) == datetime(
        2024,
        1,
        1,
        tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        prometheus._parse_duration("invalid")


class DummyPrometheusClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Optional[Dict[str, Any]]]] = []
        self.responses: Dict[str, Dict[str, Any]] = {}

    async def request_json(
            self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        normalized = path if path.startswith("/") else f"/{path}"
        self.calls.append((normalized, params))
        return self.responses.get(
            normalized, {
                "status": "success", "data": {}})


@pytest.fixture
def prom_client(monkeypatch: pytest.MonkeyPatch) -> DummyPrometheusClient:
    client = DummyPrometheusClient()

    async def ensure(_: Any, __: str) -> None:
        return None

    monkeypatch.setattr(prometheus, "_ensure_datasource", ensure)
    monkeypatch.setattr(
        prometheus,
        "PrometheusClient",
        lambda ctx,
        uid: client)
    return client


@pytest.fixture
def ctx() -> SimpleNamespace:
    return SimpleNamespace()


def test_query_prometheus_range(
        monkeypatch: pytest.MonkeyPatch,
        prom_client: DummyPrometheusClient,
        ctx: SimpleNamespace) -> None:
    prom_client.responses["/api/v1/query_range"] = {
        "status": "success", "data": {"resultType": "matrix"}}
    result = asyncio.run(
        prometheus._query_prometheus(
            ctx,
            "uid",
            "up",
            start="now-1h",
            end="now",
            step_seconds=60,
            query_type="range",
        )
    )
    assert result["resultType"] == "matrix"
    path, params = prom_client.calls[-1]
    assert path == "/api/v1/query_range"
    assert params["step"] == "60"

    prom_client.responses["/api/v1/query_range"] = {"status": "error"}
    with pytest.raises(ValueError):
        asyncio.run(
            prometheus._query_prometheus(
                ctx,
                "uid",
                "up",
                "now-1h",
                "now",
                step_seconds=30,
                query_type="range",
            )
        )


def test_query_prometheus_instant(
        monkeypatch: pytest.MonkeyPatch,
        prom_client: DummyPrometheusClient,
        ctx: SimpleNamespace) -> None:
    prom_client.responses["/api/v1/query"] = {
        "status": "success", "data": {
            "resultType": "vector"}}
    fixed_now = datetime(2024, 1, 1, tzinfo=timezone.utc)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz: Optional[timezone] = None) -> datetime:
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(prometheus, "datetime", FixedDateTime)
    result = asyncio.run(
        prometheus._query_prometheus(
            ctx,
            "uid",
            "up",
            start=None,
            end=None,
            step_seconds=None,
            query_type="instant",
        )
    )
    assert result["resultType"] == "vector"
    _, params = prom_client.calls[-1]
    assert float(params["time"]) == pytest.approx(fixed_now.timestamp())


def test_metadata_and_label_helpers(
        prom_client: DummyPrometheusClient,
        ctx: SimpleNamespace) -> None:
    prom_client.responses["/api/v1/metadata"] = {
        "status": "success", "data": {"metric": {}}}
    meta = asyncio.run(
        prometheus._metadata(
            ctx,
            "uid",
            metric="http_requests_total",
            limit=5))
    assert "metric" in meta

    selector = Selector([LabelMatcher(name="job", value="api")])
    prom_client.responses["/api/v1/labels"] = {
        "status": "success", "data": ["job", "instance"]}
    labels = asyncio.run(
        prometheus._label_names(
            ctx,
            "uid",
            [selector],
            "now-1h",
            "now"))
    assert "job" in labels

    prom_client.responses["/api/v1/label/__name__/values"] = {
        "status": "success", "data": ["up", "process_start_time_seconds"]}
    values = asyncio.run(
        prometheus._label_values(
            ctx,
            "uid",
            "__name__",
            [selector],
            None,
            None))
    assert "up" in values


def test_metric_names_filters_and_paginates(
        monkeypatch: pytest.MonkeyPatch,
        prom_client: DummyPrometheusClient,
        ctx: SimpleNamespace) -> None:
    async def fake_label_values(*args: Any, **kwargs: Any) -> list[str]:
        return [
            "http_requests_total",
            "go_goroutines",
            "process_start_time_seconds"]

    monkeypatch.setattr(prometheus, "_label_values", fake_label_values)
    names = asyncio.run(
        prometheus._metric_names(
            ctx,
            "uid",
            regex="^go_",
            limit=1,
            page=2))
    assert names == []
    with pytest.raises(ValueError):
        asyncio.run(prometheus._metric_names(ctx, "uid", None, -1, 1))


def test_query_prometheus_range_defaults(
        monkeypatch: pytest.MonkeyPatch,
        prom_client: DummyPrometheusClient,
        ctx: SimpleNamespace) -> None:
    prom_client.responses["/api/v1/query_range"] = {
        "status": "success", "data": {}}
    fixed_now = datetime(2024, 1, 1, tzinfo=timezone.utc)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz: Optional[timezone] = None) -> datetime:
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(prometheus, "datetime", FixedDateTime)
    asyncio.run(
        prometheus._query_prometheus(
            ctx,
            "uid",
            "up",
            start=None,
            end=None,
            step_seconds=None,
            query_type="range",
        )
    )
    _, params = prom_client.calls[-1]
    expected_start = (fixed_now - timedelta(minutes=5)).timestamp()
    expected_end = fixed_now.timestamp()
    assert float(params["start"]) == pytest.approx(expected_start)
    assert float(params["end"]) == pytest.approx(expected_end)
    assert params["step"] == "60"


def test_query_prometheus_range_invalid_step(
        prom_client: DummyPrometheusClient,
        ctx: SimpleNamespace) -> None:
    with pytest.raises(ValueError):
        asyncio.run(
            prometheus._query_prometheus(
                ctx,
                "uid",
                "up",
                start="now-1h",
                end="now",
                step_seconds=0,
                query_type="range",
            )
        )


def test_prometheus_tools_require_context() -> None:
    app = FastMCP()
    prometheus.register(app)
    tools = asyncio.run(app.list_tools())
    tool = next(tool for tool in tools if tool.name == "query_prometheus")
    with pytest.raises(ValueError):
        asyncio.run(
            tool.function(
                datasourceUid="uid",
                expr="up",
                startTime="now",
                ctx=None))
