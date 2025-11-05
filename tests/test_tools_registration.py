"""Integration-style tests for conditional tool registration."""

from __future__ import annotations

import asyncio

import pytest

import app.tools as tools
from app.tools import register_all
from app.tools.availability import GrafanaCapabilities
from mcp.server.fastmcp import FastMCP


def _capabilities_with(
    *,
    datasource_types: set[str],
        plugin_ids: set[str]) -> GrafanaCapabilities:
    return GrafanaCapabilities(
        datasource_types=frozenset(datasource_types),
        plugin_ids=frozenset(plugin_ids),
    )


def _tool_names(app: FastMCP) -> set[str]:
    registered = asyncio.run(app.list_tools())
    return {tool.name for tool in registered}


def test_register_all_skips_loki_without_datasource(
        monkeypatch: pytest.MonkeyPatch) -> None:
    capabilities = _capabilities_with(
        datasource_types={
            "prometheus", "pyroscope"}, plugin_ids={
            "grafana-irm-app", "grafana-asserts-app", "grafana-ml-app"}, )
    monkeypatch.setattr(tools, "_resolve_capabilities", lambda: capabilities)

    app = FastMCP()
    register_all(app)
    names = _tool_names(app)

    assert "query_loki_logs" not in names
    assert "search" in names


def test_register_all_skips_oncall_without_plugin(
        monkeypatch: pytest.MonkeyPatch) -> None:
    capabilities = _capabilities_with(
        datasource_types={"loki", "prometheus", "pyroscope"},
        plugin_ids={"grafana-ml-app"},
    )
    monkeypatch.setattr(tools, "_resolve_capabilities", lambda: capabilities)

    app = FastMCP()
    register_all(app)
    names = _tool_names(app)

    assert "list_oncall_schedules" not in names
    assert "create_incident" not in names
    assert "search" in names


def test_all_tools_define_array_item_schemas(
        monkeypatch: pytest.MonkeyPatch) -> None:
    capabilities = _capabilities_with(
        datasource_types={
            "loki", "prometheus", "pyroscope"}, plugin_ids={
            "grafana-irm-app", "grafana-asserts-app", "grafana-ml-app"}, )
    monkeypatch.setattr(tools, "_resolve_capabilities", lambda: capabilities)

    app = FastMCP()
    register_all(app)

    registered_tools = asyncio.run(app.list_tools())
    for tool in registered_tools:
        properties = tool.inputSchema.get("properties", {})
        for name, schema in properties.items():
            if schema.get("type") == "array":
                items_schema = schema.get("items")
                assert isinstance(items_schema, dict) and items_schema, (
                    f"Tool {tool.name} parameter '{name}' must define a non-empty items schema",
                )
