"""Tests for Pyroscope datasource helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest

from app.tools import pyroscope
from mcp.server.fastmcp import FastMCP


def test_matchers_and_time_range() -> None:
    assert pyroscope._matchers(None) == "{}"
    assert pyroscope._matchers("{app=\"api\"}") == "{app=\"api\"}"
    start, end = pyroscope._default_time_range(None, None)
    assert isinstance(start, datetime)
    assert isinstance(end, datetime)
    assert end > start
    with pytest.raises(ValueError):
        pyroscope._default_time_range(
            "2024-01-01T00:00:00Z",
            "2023-01-01T00:00:00Z")


class DummyPyroscopeClient:
    def __init__(self) -> None:
        self.responses: Dict[str, Any] = {}
        self.calls: list[tuple[str, Optional[Dict[str, Any]]]] = []

    async def get_json(
            self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.calls.append((path, params))
        return self.responses.get(path, {})

    async def request(self, method: str, path: str,
                      params: Optional[Dict[str, Any]] = None) -> SimpleNamespace:
        self.calls.append((path, params))
        return SimpleNamespace(text="digraph G{}")


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    config = SimpleNamespace(url="https://grafana.local")

    class ValidatingClient(DummyPyroscopeClient):
        async def get_json(
                self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            return {"id": "ds"}

    base_client = ValidatingClient()
    monkeypatch.setattr(pyroscope, "get_grafana_config", lambda _: config)
    monkeypatch.setattr(pyroscope, "GrafanaClient", lambda cfg: base_client)
    return SimpleNamespace()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> DummyPyroscopeClient:
    client = DummyPyroscopeClient()

    async def create(_: Any, __: str) -> DummyPyroscopeClient:
        return client

    monkeypatch.setattr(pyroscope, "_pyroscope_client", create)
    return client


def test_list_label_names(
        ctx: SimpleNamespace,
        client: DummyPyroscopeClient) -> None:
    client.responses["/datasources/proxy/uid/uid/pyroscope/api/v1/label/names"] = {
        "names": ["app", "instance"], }
    names = asyncio.run(
        pyroscope._list_label_names(
            ctx,
            "uid",
            matchers="app=\"api\"",
            start=None,
            end=None))
    assert "app" in names


def test_list_label_values(
        ctx: SimpleNamespace,
        client: DummyPyroscopeClient) -> None:
    client.responses["/datasources/proxy/uid/uid/pyroscope/api/v1/label/app/values"] = {
        "values": ["api", "worker"], }
    values = asyncio.run(
        pyroscope._list_label_values(
            ctx, "uid", "app", None, None, None))
    assert values == ["api", "worker"]


def test_list_profile_types(
        ctx: SimpleNamespace,
        client: DummyPyroscopeClient) -> None:
    client.responses["/datasources/proxy/uid/uid/pyroscope/api/v1/profile_types"] = {
        "types": ["cpu", "memory"], }
    types = asyncio.run(pyroscope._list_profile_types(ctx, "uid", None, None))
    assert types == ["cpu", "memory"]


def test_fetch_profile(
        ctx: SimpleNamespace,
        client: DummyPyroscopeClient) -> None:
    profile = asyncio.run(
        pyroscope._fetch_profile(
            ctx,
            "uid",
            "cpu",
            matchers=None,
            start=None,
            end=None,
            max_node_depth=5))
    assert "digraph" in profile


def test_pyroscope_tools_require_context() -> None:
    app = FastMCP()
    pyroscope.register(app)
    tools = asyncio.run(app.list_tools())
    tool = next(tool for tool in tools if tool.name ==
                "fetch_pyroscope_profile")
    with pytest.raises(ValueError):
        asyncio.run(
            tool.function(
                dataSourceUid="uid",
                profileType="cpu",
                ctx=None))
