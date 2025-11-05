"""Tests for the administrative Grafana tool helpers."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.tools import admin
from mcp.server.fastmcp import FastMCP


class DummyClient:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def get_json(self, path: str, params: Any = None) -> dict[str, Any]:
        self.calls.append((path, params))
        return {"path": path, "params": params}


@pytest.fixture
def dummy_ctx(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    config = SimpleNamespace(url="https://grafana.local")
    monkeypatch.setattr(admin, "get_grafana_config", lambda _: config)
    monkeypatch.setattr(admin, "GrafanaClient", DummyClient)
    ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            session=SimpleNamespace(),
            request=None))
    return ctx


def test_list_teams_calls_grafana_api(dummy_ctx: SimpleNamespace) -> None:
    result = asyncio.run(admin._list_teams("prod", dummy_ctx))
    assert result == {"path": "/teams/search", "params": {"query": "prod"}}

    result_no_query = asyncio.run(admin._list_teams(None, dummy_ctx))
    assert result_no_query == {"path": "/teams/search", "params": None}


def test_list_users(dummy_ctx: SimpleNamespace) -> None:
    result = asyncio.run(admin._list_users(dummy_ctx))
    assert result == {"path": "/org/users", "params": None}


def test_admin_tools_require_context(monkeypatch: pytest.MonkeyPatch) -> None:
    app = FastMCP()
    admin.register(app)

    tools = asyncio.run(app.list_tools())
    tool_names = {tool.name for tool in tools}
    assert {"list_teams", "list_users_by_org"}.issubset(tool_names)

    list_teams_tool = next(tool for tool in tools if tool.name == "list_teams")
    with pytest.raises(ValueError):
        asyncio.run(list_teams_tool.function(query="foo", ctx=None))
