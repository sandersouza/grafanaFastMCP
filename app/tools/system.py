"""System metadata tools for Grafana FastMCP."""

from __future__ import annotations

from typing import Any, Iterable

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaClient


def _first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _plugin_items(payload: Any) -> list[dict[str, Any]]:
    items: Iterable[Any]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        candidate = payload.get("items") if "items" in payload else payload.get("plugins")
        if not isinstance(candidate, list):
            raise ValueError("Unexpected response format from Grafana while listing plugins")
        items = candidate
    else:
        raise ValueError("Unexpected response format from Grafana while listing plugins")

    return [item for item in items if isinstance(item, dict)]


def _plugin_version(plugin: dict[str, Any]) -> Any:
    version = _first_present(
        plugin,
        "version",
        "installedVersion",
        "installed_version",
        "pluginVersion",
    )
    if version is not None:
        return version
    info = plugin.get("info")
    if isinstance(info, dict):
        return info.get("version")
    return None


def _summarize_plugin(plugin: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _first_present(plugin, "id", "pluginId", "pluginSlug"),
        "name": _first_present(plugin, "name", "pluginName"),
        "type": _first_present(plugin, "type", "pluginType"),
        "version": _plugin_version(plugin),
        "latest_version": _first_present(plugin, "latestVersion", "latest_version"),
        "enabled": plugin.get("enabled"),
        "source": "/api/plugins",
    }


async def _get_grafana_versions(ctx: Context) -> dict[str, Any]:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)

    health = await client.get_json("/health")
    if not isinstance(health, dict):
        raise ValueError("Unexpected response format from Grafana health endpoint")

    plugins_payload = await client.get_json("/plugins")
    plugins = [_summarize_plugin(plugin) for plugin in _plugin_items(plugins_payload)]

    return {
        "grafana": {
            "version": health.get("version"),
            "commit": health.get("commit"),
            "database": health.get("database"),
            "source": "/api/health",
        },
        "plugins": plugins,
        "total_count": len(plugins),
        "type": "grafana_versions_result",
    }


def register(app: FastMCP) -> None:
    """Register Grafana system metadata tools with the FastMCP server."""

    @app.tool(
        name="get_grafana_versions",
        title="Get Grafana versions",
        description=(
            "Return the Grafana server version and installed plugin versions. "
            "Uses Grafana health and plugins APIs and returns a consolidated "
            "response object to avoid JSON chunking issues in MCP clients."
        ),
    )
    async def get_grafana_versions(ctx: Context | None = None) -> Any:
        if ctx is None:
            raise ValueError("Context injection failed for get_grafana_versions")
        return await _get_grafana_versions(ctx)


__all__ = ["register"]
