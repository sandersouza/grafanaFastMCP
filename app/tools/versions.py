"""Grafana and plugin version tools."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaClient


def _as_mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_plugins(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [plugin for plugin in payload if isinstance(plugin, dict)]
    if not isinstance(payload, dict):
        return []

    for key in ("plugins", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [plugin for plugin in value if isinstance(plugin, dict)]
    return []


def _first_present(mapping: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _normalize_grafana_health(payload: Any) -> Dict[str, Any]:
    health = _as_mapping(payload)
    return {
        "version": health.get("version"),
        "commit": health.get("commit"),
        "buildstamp": health.get("buildstamp"),
        "database": health.get("database"),
        "edition": health.get("edition"),
    }


def _normalize_plugin(plugin: Dict[str, Any]) -> Dict[str, Any]:
    info = _as_mapping(plugin.get("info"))
    version = _first_present(
        info,
        ("version", "pluginVersion", "buildVersion"),
    )
    if version is None:
        version = _first_present(
            plugin,
            ("version", "pluginVersion", "buildVersion"),
        )

    return {
        "id": plugin.get("id"),
        "name": plugin.get("name"),
        "type": plugin.get("type"),
        "enabled": plugin.get("enabled"),
        "pinned": plugin.get("pinned"),
        "module": plugin.get("module"),
        "baseUrl": plugin.get("baseUrl"),
        "version": version,
    }


def _normalize_versions_result(health: Any, plugins: Any) -> Dict[str, Any]:
    normalized_plugins = [
        _normalize_plugin(plugin) for plugin in _extract_plugins(plugins)
    ]
    return {
        "grafana": _normalize_grafana_health(health),
        "plugins": normalized_plugins,
        "total_count": len(normalized_plugins),
        "type": "grafana_versions_result",
    }


async def _get_grafana_versions(ctx: Context) -> Dict[str, Any]:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    health = await client.get_json("/health")
    plugins = await client.get_json("/plugins")
    return _normalize_versions_result(health, plugins)


def register(app: FastMCP) -> None:
    """Register Grafana version tools with the FastMCP server."""

    @app.tool(
        name="get_grafana_versions",
        title="Get Grafana versions",
        description=(
            "Return the Grafana server version and installed plugin/component "
            "versions in a consolidated response object."
        ),
    )
    async def get_grafana_versions(
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError("Context injection failed for get_grafana_versions")
        return await _get_grafana_versions(ctx)


__all__ = ["register"]
