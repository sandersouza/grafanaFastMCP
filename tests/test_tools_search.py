"""Tests for the search and fetch tool registration and helpers."""

from __future__ import annotations

import asyncio
import pytest

import app.tools as tools
from app.tools import register_all
from app.tools.availability import GrafanaCapabilities
from app.tools.search import (
    _fetch_dashboard,
    _fetch_resource,
    _parse_dashboard_url,
    _resolve_dashboard_lookup,
)
from mcp.server.fastmcp import FastMCP


@pytest.fixture(autouse=True)
def _allow_all_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    capabilities = GrafanaCapabilities(
        datasource_types=frozenset({"loki", "prometheus", "pyroscope"}),
        plugin_ids=frozenset({"grafana-irm-app", "grafana-asserts-app", "grafana-ml-app"}),
    )
    monkeypatch.setattr(tools, "_resolve_capabilities", lambda: capabilities)


def test_search_tool_is_registered() -> None:
    app = FastMCP()
    register_all(app)

    tools = asyncio.run(app.list_tools())
    tool_names = {tool.name for tool in tools}

    assert "search" in tool_names
    assert "search_dashboards" in tool_names
    assert "fetch" in tool_names


def test_search_tool_metadata() -> None:
    app = FastMCP()
    register_all(app)

    tools = asyncio.run(app.list_tools())
    tool = next((tool for tool in tools if tool.name == "search"), None)
    assert tool is not None
    assert "General purpose search" in (tool.description or "")


def test_fetch_tool_metadata() -> None:
    app = FastMCP()
    register_all(app)

    tools = asyncio.run(app.list_tools())
    tool = next((tool for tool in tools if tool.name == "fetch"), None)
    assert tool is not None
    assert "Retrieve detailed Grafana resource data" in (
        tool.description or "")


def test_search_and_dashboards_tools_require_only_query() -> None:
    app = FastMCP()
    register_all(app)

    tools = asyncio.run(app.list_tools())
    for tool_name in ("search", "search_dashboards"):
        tool = next((tool for tool in tools if tool.name == tool_name), None)
        assert tool is not None

        schema = tool.inputSchema
        assert schema.get("required") == ["query"], schema
        assert set(schema.get("properties", {})) == {"query"}


def test_fetch_schema_exposes_string_identifiers() -> None:
    app = FastMCP()
    register_all(app)

    tools = asyncio.run(app.list_tools())
    tool = next((tool for tool in tools if tool.name == "fetch"), None)
    assert tool is not None

    schema = tool.inputSchema
    assert schema.get("required") == ["id"], schema
    id_schema = schema.get("properties", {}).get("id")
    assert id_schema is not None
    assert id_schema.get("type") == "string"


def test_fetch_schema_defines_array_items_for_ids() -> None:
    app = FastMCP()
    register_all(app)

    tools = asyncio.run(app.list_tools())
    tool = next((tool for tool in tools if tool.name == "fetch"), None)
    assert tool is not None

    schema = tool.inputSchema
    ids_schema = schema.get("properties", {}).get("ids")
    assert ids_schema is not None, schema
    assert ids_schema.get("type") == "array"
    assert "items" in ids_schema
    items_schema = ids_schema["items"]
    assert isinstance(items_schema, dict) and items_schema, ids_schema

    if "anyOf" in items_schema:
        any_of = items_schema["anyOf"]
        assert isinstance(any_of, list) and any_of, items_schema
        item_types = {entry.get("type")
                      for entry in any_of if isinstance(entry, dict)}
    else:
        item_types = {items_schema.get("type")}

    assert {"string", "integer", "object"}.issubset(item_types)


def test_parse_dashboard_url_handles_relative_and_absolute_paths() -> None:
    uid, numeric = _parse_dashboard_url("/d/abc123/example")
    assert uid == "abc123"
    assert numeric is None

    uid, numeric = _parse_dashboard_url(
        "https://grafana.example.com/d-solo/xyz/view")
    assert uid == "xyz"
    assert numeric is None


def test_parse_dashboard_url_handles_api_paths() -> None:
    uid, numeric = _parse_dashboard_url("/api/dashboards/id/42")
    assert uid is None
    assert numeric == "42"

    uid, numeric = _parse_dashboard_url("/api/dashboards/uid/uid-value")
    assert uid == "uid-value"


def test_resolve_dashboard_lookup_uses_available_metadata() -> None:
    uid, numeric = _resolve_dashboard_lookup(
        uid=None,
        id_value=None,
        ids=None,
        url=None,
        uri=None,
        item={"uid": "from-item"},
    )
    assert uid == "from-item"
    assert numeric is None


def test_resolve_dashboard_lookup_extracts_from_url_and_ids() -> None:
    uid, numeric = _resolve_dashboard_lookup(
        uid=None,
        id_value=None,
        ids=["fallback-uid"],
        url="/d/url-uid/example",
        uri=None,
        item=None,
    )
    assert uid == "url-uid"
    assert numeric is None


class DummyClient:
    """Simple stubbed Grafana client for fetch helper tests."""

    def __init__(self) -> None:
        self.paths: list[str] = []

    async def get_json(self,
                       path: str,
                       params: dict[str,
                                    object] | None = None) -> dict[str,
                                                                   str]:
        self.paths.append(path)
        return {"path": path}


def test_fetch_dashboard_prefers_uid() -> None:
    client = DummyClient()

    result = asyncio.run(
        _fetch_dashboard(
            client,
            uid="abc123",
            numeric_id=None))

    assert result == {"path": "/dashboards/uid/abc123"}
    assert client.paths == ["/dashboards/uid/abc123"]


def test_fetch_dashboard_supports_numeric_id() -> None:
    client = DummyClient()

    result = asyncio.run(_fetch_dashboard(client, uid=None, numeric_id="99"))

    assert result == {"path": "/dashboards/id/99"}
    assert client.paths == ["/dashboards/id/99"]


def test_fetch_dashboard_requires_identifier() -> None:
    client = DummyClient()

    with pytest.raises(ValueError):
        asyncio.run(_fetch_dashboard(client, uid=None, numeric_id=None))


def test_fetch_resource_uses_url_when_available() -> None:
    client = DummyClient()

    result = asyncio.run(
        _fetch_resource(
            client,
            resource_type="dash-db",
            id_value=None,
            uid=None,
            ids=None,
            url="/d/uid-from-url/example",
            uri=None,
            item=None,
        )
    )

    assert result == {"path": "/dashboards/uid/uid-from-url"}
    assert client.paths == ["/dashboards/uid/uid-from-url"]


def test_fetch_resource_uses_metadata_item() -> None:
    client = DummyClient()

    result = asyncio.run(
        _fetch_resource(
            client,
            resource_type=None,
            id_value=None,
            uid=None,
            ids=None,
            url=None,
            uri=None,
            item={"url": "/d/item-uid/example", "type": "dash-db"},
        )
    )

    assert result == {"path": "/dashboards/uid/item-uid"}
    assert client.paths == ["/dashboards/uid/item-uid"]


def test_fetch_resource_requires_identifier() -> None:
    client = DummyClient()

    with pytest.raises(ValueError):
        asyncio.run(
            _fetch_resource(
                client,
                resource_type="dash-db",
                id_value=None,
                uid=None,
                ids=None,
                url=None,
                uri=None,
                item=None,
            )
        )


def test_fetch_resource_rejects_unsupported_types() -> None:
    client = DummyClient()

    with pytest.raises(ValueError):
        asyncio.run(
            _fetch_resource(
                client,
                resource_type="datasource",
                id_value=None,
                uid=None,
                ids=None,
                url="/d/uid/example",
                uri=None,
                item=None,
            )
        )
