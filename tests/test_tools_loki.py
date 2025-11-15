"""Tests for the Loki datasource helpers."""

from __future__ import annotations

import asyncio
from datetime import timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from app.tools import loki
from mcp.server.fastmcp import FastMCP


def test_time_range_defaults_to_last_hour() -> None:
    start_iso, end_iso = loki._time_range(None, None)
    start_dt = loki._parse_rfc3339(start_iso)
    end_dt = loki._parse_rfc3339(end_iso)
    delta = end_dt - start_dt
    assert timedelta(minutes=59) < delta <= timedelta(hours=1)


def test_parse_rfc3339_and_nanos() -> None:
    dt = loki._parse_rfc3339("2024-01-01T00:00:00Z")
    assert dt.tzinfo == timezone.utc
    nanos = loki._nanos("2024-01-01T00:00:00+00:00")
    assert nanos.endswith("000000000")


def test_format_log_entries_handles_json_and_numbers() -> None:
    streams = [
        {
            "stream": {"level": "info"},
            "values": [
                ["1700000000", '"plain"'],
                ["1700000001", "123"],
            ],
        }
    ]
    entries = loki._format_log_entries(streams)
    assert entries[0]["line"] == "plain"
    assert entries[1]["value"] == 123.0


class FakeLokiClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Dict[str, Any]]] = []
        self.responses: Dict[str, Any] = {}

    async def request_json(
            self, path: str, params: Dict[str, Any] | None = None) -> Any:
        self.calls.append((path, params or {}))
        response = self.responses.get(path)
        if isinstance(response, Exception):
            raise response
        return response


def test_loki_client_headers_and_request(
        monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        url="https://grafana.local",
        api_key="token",
        basic_auth=("user", "pass"),
        access_token="access",
        id_token="id",
        tls_config=None,
    )
    monkeypatch.setattr(loki, "get_grafana_config", lambda ctx: config)

    class DummyResponse:
        def __init__(self, status_code: int, payload: Dict[str, Any]) -> None:
            self.status_code = status_code
            self._payload = payload
            self.text = "{}"

        def json(self) -> Dict[str, Any]:
            return self._payload

    class DummyAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.calls: list[tuple[str, Dict[str, Any] | None]] = []

        async def __aenter__(self) -> "DummyAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self,
                      url: str,
                      params: Dict[str,
                                   Any] | None = None,
                      headers: Dict[str,
                                    Any] | None = None) -> DummyResponse:
            self.calls.append((url, params))
            if "error" in url:
                return DummyResponse(500, {})
            return DummyResponse(200, {"status": "success", "data": {}})

    dummy_client = DummyAsyncClient()
    monkeypatch.setattr(
        loki.httpx,
        "AsyncClient",
        lambda *args,
        **kwargs: dummy_client)

    client = loki.LokiClient(SimpleNamespace(), "datasource")
    headers = client._headers
    assert headers["Authorization"] == "Bearer token"
    result = asyncio.run(client.request_json("/success", params={"q": 1}))
    assert result["status"] == "success"
    with pytest.raises(ValueError):
        asyncio.run(client.request("/error"))


@pytest.fixture
def ctx(
        monkeypatch: pytest.MonkeyPatch) -> tuple[SimpleNamespace, FakeLokiClient]:
    fake_client = FakeLokiClient()

    async def create_client(_ctx: Any, _uid: str) -> FakeLokiClient:
        return fake_client

    monkeypatch.setattr(loki, "_create_loki_client", create_client)
    return SimpleNamespace(), fake_client


def test_list_label_items(ctx: tuple[SimpleNamespace, FakeLokiClient]) -> None:
    ctx_obj, client = ctx
    client.responses["/loki/api/v1/labels"] = {
        "status": "success", "data": ["job", "env"]}
    labels = asyncio.run(
        loki._list_label_items(
            ctx_obj,
            "uid",
            "/loki/api/v1/labels",
            "2024-01-01T00:00:00Z",
            "2024-01-01T01:00:00Z"))
    assert labels == ["job", "env"]
    params = client.calls[0][1]
    assert "start" in params and "end" in params

    client.responses["/loki/api/v1/labels"] = {"status": "error"}
    with pytest.raises(ValueError):
        asyncio.run(
            loki._list_label_items(
                ctx_obj,
                "uid",
                "/loki/api/v1/labels",
                None,
                None))


def test_query_range_and_stats(
        ctx: tuple[SimpleNamespace, FakeLokiClient]) -> None:
    ctx_obj, client = ctx
    client.responses["/loki/api/v1/query_range"] = {
        "status": "success",
        "data": {"result": [{"stream": {}, "values": []}]},
    }
    result = asyncio.run(
        loki._query_range(
            ctx_obj,
            "uid",
            "{job=\"api\"}",
            None,
            None,
            limit=5,
            direction="forward"))
    assert isinstance(result, list)
    params = client.calls[-1][1]
    assert params["limit"] == "5"

    asyncio.run(
        loki._query_range(
            ctx_obj,
            "uid",
            "{job=\"api\"}",
            None,
            None,
            limit=1000,
            direction=None))
    params_capped = client.calls[-1][1]
    assert params_capped["limit"] == str(loki._MAX_LOG_LIMIT)
    assert params_capped["direction"] == "backward"

    client.responses["/loki/api/v1/index/stats"] = {
        "summary": {"bytesProcessed": 10}}
    stats = asyncio.run(
        loki._query_stats(
            ctx_obj,
            "uid",
            "{job=\"api\"}",
            None,
            None))
    assert stats["summary"]["bytesProcessed"] == 10


def test_loki_tools_require_context() -> None:
    app = FastMCP()
    loki.register(app)
    tools = asyncio.run(app.list_tools())
    tool = next(tool for tool in tools if tool.name == "query_loki_logs")
    with pytest.raises(ValueError):
        asyncio.run(tool.function(datasourceUid="uid", logql="{}", ctx=None))
