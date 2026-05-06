"""Tests for Grafana version tool helpers."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from app.tools import versions


class DummyClient:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def get_json(self, path: str, params: Any = None) -> Any:
        self.calls.append((path, params))
        if path == "/health":
            return {
                "version": "11.4.0",
                "commit": "abc123",
                "buildstamp": 1710000000,
                "database": "ok",
            }
        if path == "/plugins":
            return {
                "items": [
                    {
                        "id": "grafana-clock-panel",
                        "name": "Clock",
                        "type": "panel",
                        "enabled": True,
                        "pinned": False,
                        "module": "plugins/grafana-clock-panel/module",
                        "baseUrl": "public/plugins/grafana-clock-panel",
                        "info": {"version": "2.1.8"},
                    }
                ]
            }
        raise AssertionError(f"Unexpected path: {path}")


@pytest.fixture
def setup_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[SimpleNamespace, DummyClient]:
    config = SimpleNamespace(url="https://grafana.local")
    client = DummyClient()
    monkeypatch.setattr(versions, "get_grafana_config", lambda _: config)
    monkeypatch.setattr(versions, "GrafanaClient", lambda cfg: client)
    ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            session=SimpleNamespace(),
            request=None,
        )
    )
    return ctx, client


def test_extract_plugins_accepts_known_payload_shapes() -> None:
    plugin = {"id": "grafana-test-app"}

    assert versions._extract_plugins([plugin]) == [plugin]
    assert versions._extract_plugins({"plugins": [plugin]}) == [plugin]
    assert versions._extract_plugins({"items": [plugin]}) == [plugin]
    assert versions._extract_plugins({"items": ["skip", plugin]}) == [plugin]
    assert versions._extract_plugins({"unexpected": []}) == []
    assert versions._extract_plugins(None) == []


def test_normalize_versions_result() -> None:
    result = versions._normalize_versions_result(
        {
            "version": "11.4.0",
            "commit": "abc123",
            "buildstamp": 1710000000,
            "database": "ok",
            "edition": "Open Source",
            "ignored": "value",
        },
        [
            {
                "id": "grafana-clock-panel",
                "name": "Clock",
                "type": "panel",
                "enabled": True,
                "pinned": False,
                "module": "plugins/grafana-clock-panel/module",
                "baseUrl": "public/plugins/grafana-clock-panel",
                "info": {"version": "2.1.8"},
            },
            {
                "id": "grafana-missing-version",
                "name": "Missing Version",
                "type": "app",
                "enabled": False,
            },
        ],
    )

    assert result == {
        "grafana": {
            "version": "11.4.0",
            "commit": "abc123",
            "buildstamp": 1710000000,
            "database": "ok",
            "edition": "Open Source",
        },
        "plugins": [
            {
                "id": "grafana-clock-panel",
                "name": "Clock",
                "type": "panel",
                "enabled": True,
                "pinned": False,
                "module": "plugins/grafana-clock-panel/module",
                "baseUrl": "public/plugins/grafana-clock-panel",
                "version": "2.1.8",
            },
            {
                "id": "grafana-missing-version",
                "name": "Missing Version",
                "type": "app",
                "enabled": False,
                "pinned": None,
                "module": None,
                "baseUrl": None,
                "version": None,
            },
        ],
        "total_count": 2,
        "type": "grafana_versions_result",
    }


def test_get_grafana_versions_calls_health_and_plugins(
    setup_versions: tuple[SimpleNamespace, DummyClient],
) -> None:
    ctx, client = setup_versions

    result = asyncio.run(versions._get_grafana_versions(ctx))

    assert result["grafana"]["version"] == "11.4.0"
    assert result["plugins"][0]["version"] == "2.1.8"
    assert result["total_count"] == 1
    assert client.calls == [("/health", None), ("/plugins", None)]


def test_get_grafana_versions_requires_context() -> None:
    app = FastMCP()
    versions.register(app)

    tools = asyncio.run(app.list_tools())
    tool = next(tool for tool in tools if tool.name == "get_grafana_versions")

    with pytest.raises(ValueError):
        asyncio.run(tool.function(ctx=None))
