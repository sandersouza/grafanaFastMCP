"""Datasource-related tools for the Python Grafana FastMCP implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaAPIError, GrafanaClient


def _filter_datasources(
        datasources: List[Dict[str, Any]], ds_type: Optional[str]) -> List[Dict[str, Any]]:
    if not ds_type:
        return datasources
    lowered = ds_type.lower()
    return [
        ds for ds in datasources if lowered in str(
            ds.get(
                "type",
                "")).lower()]


def _summarize_datasource(ds: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": ds.get("id"),
        "uid": ds.get("uid"),
        "name": ds.get("name"),
        "type": ds.get("type"),
        "isDefault": ds.get("isDefault"),
    }


async def _list_datasources(
        ctx: Context, ds_type: Optional[str]) -> List[Dict[str, Any]]:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    datasources = await client.get_json("/datasources")
    if not isinstance(datasources, list):
        raise ValueError(
            "Unexpected response format from Grafana while listing datasources")
    filtered = _filter_datasources(datasources, ds_type)
    return [_summarize_datasource(ds) for ds in filtered]


async def _get_by_uid(ctx: Context, uid: str) -> Any:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    try:
        return await client.get_json(f"/datasources/uid/{uid}")
    except GrafanaAPIError as exc:  # pragma: no cover - defensive
        if exc.status_code == 404:
            raise ValueError(f"Datasource with UID '{uid}' not found") from exc
        raise


async def _get_by_name(ctx: Context, name: str) -> Any:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    try:
        return await client.get_json(f"/datasources/name/{name}")
    except GrafanaAPIError as exc:  # pragma: no cover - defensive
        if exc.status_code == 404:
            raise ValueError(
                f"Datasource with name '{name}' not found") from exc
        raise


def register(app: FastMCP) -> None:
    """Register datasource tools with the FastMCP server."""

    @app.tool(
        name="list_datasources",
        title="List datasources",
        description=(
            "List available Grafana datasources. Optionally filter the list by a substring matching the datasource type, "
            "for example 'prometheus' or 'loki'."),
    )
    async def list_datasources(
        datasourceType: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> List[Dict[str, Any]]:
        if ctx is None:
            raise ValueError("Context injection failed for list_datasources")
        return await _list_datasources(ctx, datasourceType)

    @app.tool(
        name="get_datasource_by_uid",
        title="Get datasource by UID",
        description=(
            "Retrieve full metadata for a datasource using its unique identifier. Returns the Grafana datasource object as "
            "provided by the HTTP API."),
    )
    async def get_datasource_by_uid(
        uid: str,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for get_datasource_by_uid")
        return await _get_by_uid(ctx, uid)

    @app.tool(
        name="get_datasource_by_name",
        title="Get datasource by name",
        description=(
            "Retrieve full metadata for a datasource using its configured name. Returns the Grafana datasource object as "
            "provided by the HTTP API."),
    )
    async def get_datasource_by_name(
        name: str,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for get_datasource_by_name")
        return await _get_by_name(ctx, name)


__all__ = ["register"]
