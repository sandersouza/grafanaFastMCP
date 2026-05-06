"""Tests for Grafana system metadata tools."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.tools import system
from mcp.server.fastmcp import FastMCP


class DummyClient:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.responses: dict[str, Any] = {}
        self.calls: list[tuple[str, Any]] = []

    async def get_json(self, path: str, params: Any = None) -> Any:
        self.calls.append((path, params))
        return self.responses[path]


@pytest.fixture
def setup_system(monkeypatch: pytest.MonkeyPatch) -> tuple[SimpleNamespace, DummyClient]:
    config = SimpleNamespace(url="https://grafana.local")
    client = DummyClient()
    monkeypatch.setattr(system, "get_grafana_config", lambda _: config)
    monkeypatch.setattr(system, "GrafanaClient", lambda cfg: client)
    ctx = SimpleNamespace(
        request_context=SimpleNamespace(session=SimpleNamespace(), request=None)
    )
    return ctx, client


def test_get_grafana_versions_returns_consolidated_response(setup_system) -> None:
    ctx, client = setup_system
    client.responses = {
        "/health": {
            "version": "11.5.2",
            "commit": "abc123",
            "database": "ok",
        },
        "/plugins": {
            "items": [
                {
                    "id": "grafana-lokiexplore-app",
                    "name": "Grafana Loki Explore",
                    "type": "app",
                    "version": "1.0.1",
                    "latestVersion": "1.0.2",
                    "enabled": True,
                },
                {
                    "id": "grafana-pyroscope-datasource",
                    "name": "Pyroscope",
                    "type": "datasource",
                    "info": {"version": "2.3.4"},
                    "enabled": False,
                },
            ]
        },
    }

    result = asyncio.run(system._get_grafana_versions(ctx))

    assert result == {
        "grafana": {
            "version": "11.5.2",
            "commit": "abc123",
            "database": "ok",
            "source": "/api/health",
        },
        "plugins": [
            {
                "id": "grafana-lokiexplore-app",
                "name": "Grafana Loki Explore",
                "type": "app",
                "version": "1.0.1",
                "latest_version": "1.0.2",
                "enabled": True,
                "source": "/api/plugins",
            },
            {
                "id": "grafana-pyroscope-datasource",
                "name": "Pyroscope",
                "type": "datasource",
                "version": "2.3.4",
                "latest_version": None,
                "enabled": False,
                "source": "/api/plugins",
            },
        ],
        "total_count": 2,
        "type": "grafana_versions_result",
    }
    assert client.calls == [("/health", None), ("/plugins", None)]


def test_get_grafana_versions_accepts_plugin_list_payload(setup_system) -> None:
    ctx, client = setup_system
    client.responses = {
        "/health": {"version": "11.5.2"},
        "/plugins": [{"id": "grafana-clock-panel", "pluginVersion": "3.1.0"}],
    }

    result = asyncio.run(system._get_grafana_versions(ctx))

    assert result["plugins"] == [
        {
            "id": "grafana-clock-panel",
            "name": None,
            "type": None,
            "version": "3.1.0",
            "latest_version": None,
            "enabled": None,
            "source": "/api/plugins",
        }
    ]


def test_get_grafana_versions_accepts_empty_plugin_items(setup_system) -> None:
    ctx, client = setup_system
    client.responses = {
        "/health": {"version": "11.5.2"},
        "/plugins": {"items": []},
    }

    result = asyncio.run(system._get_grafana_versions(ctx))

    assert result["plugins"] == []
    assert result["total_count"] == 0


@pytest.mark.parametrize(
    "responses",
    [
        {"/health": [], "/plugins": []},
        {"/health": {}, "/plugins": {"unexpected": []}},
    ],
)
def test_get_grafana_versions_rejects_unexpected_payloads(
    setup_system, responses: dict[str, Any]
) -> None:
    ctx, client = setup_system
    client.responses = responses

    with pytest.raises(ValueError):
        asyncio.run(system._get_grafana_versions(ctx))


def test_system_tool_requires_context() -> None:
    app = FastMCP()
    system.register(app)

    tools = asyncio.run(app.list_tools())
    tool = next(tool for tool in tools if tool.name == "get_grafana_versions")

    with pytest.raises(ValueError):
        asyncio.run(tool.function(ctx=None))
