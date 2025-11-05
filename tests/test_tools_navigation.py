"""Tests for Grafana navigation helper utility functions."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Dict

import pytest

from app.tools import navigation
from mcp.server.fastmcp import FastMCP


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    config = SimpleNamespace(url="https://grafana.local/")
    monkeypatch.setattr(navigation, "get_grafana_config", lambda _: config)
    return SimpleNamespace(
        request_context=SimpleNamespace(
            session=SimpleNamespace(),
            request=None))


def test_ensure_base_url_strips_trailing_slash(ctx: SimpleNamespace) -> None:
    assert navigation._ensure_base_url(ctx) == "https://grafana.local"


@pytest.mark.parametrize("base, params, expected",
                         [("https://grafana.local/d/uid",
                           {"viewPanel": "1"},
                             "https://grafana.local/d/uid?viewPanel=1"),
                             ("https://grafana.local/d/uid?viewPanel=1",
                              {"foo": "bar"},
                              "https://grafana.local/d/uid?viewPanel=1&foo=bar"),
                             ("https://grafana.local",
                              {},
                              "https://grafana.local"),
                          ],
                         )
def test_append_query_handles_existing_parameters(
        base: str, params: Dict[str, str], expected: str) -> None:
    assert navigation._append_query(base, params) == expected


def test_generate_deeplink_supports_multiple_resource_types(
        ctx: SimpleNamespace) -> None:
    app = FastMCP()
    navigation.register(app)

    tools = asyncio.run(app.list_tools())
    deeplink_tool = next(
        tool for tool in tools if tool.name == "generate_deeplink")

    result_dashboard = asyncio.run(
        deeplink_tool.function(
            resourceType="dashboard",
            dashboardUid="abc",
            ctx=ctx))
    assert result_dashboard == "https://grafana.local/d/abc"

    result_panel = asyncio.run(
        deeplink_tool.function(
            resourceType="panel",
            dashboardUid="abc",
            panelId=5,
            queryParams={"var-service": "payments"},
            timeRange={"from": "now-1h", "to": "now"},
            ctx=ctx,
        )
    )
    assert "viewPanel=5" in result_panel
    assert "from=now-1h" in result_panel
    assert "var-service=payments" in result_panel

    result_explore = asyncio.run(
        deeplink_tool.function(
            resourceType="explore",
            datasourceUid="loki",
            ctx=ctx))
    assert result_explore.startswith("https://grafana.local/explore?")

    with pytest.raises(ValueError):
        asyncio.run(deeplink_tool.function(resourceType="dashboard", ctx=ctx))
    with pytest.raises(ValueError):
        asyncio.run(
            deeplink_tool.function(
                resourceType="panel",
                dashboardUid="abc",
                ctx=ctx))
    with pytest.raises(ValueError):
        asyncio.run(deeplink_tool.function(resourceType="explore", ctx=ctx))
    with pytest.raises(ValueError):
        asyncio.run(deeplink_tool.function(resourceType="unknown", ctx=ctx))
