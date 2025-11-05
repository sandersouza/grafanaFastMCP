"""Navigation helper tools for Grafana."""

from __future__ import annotations

from typing import Dict, Optional
from urllib.parse import urlencode

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config


def _ensure_base_url(ctx: Context) -> str:
    config = get_grafana_config(ctx)
    base_url = config.url.rstrip("/")
    if not base_url:
        raise ValueError(
            "Grafana URL not configured. Set GRAFANA_URL or provide the X-Grafana-URL header."
        )
    return base_url


def _append_query(base: str, params: Dict[str, str]) -> str:
    if not params:
        return base
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{urlencode(params)}"


def register(app: FastMCP) -> None:
    """Register navigation helpers."""

    @app.tool(
        name="generate_deeplink",
        title="Generate navigation deeplink",
        description=(
            "Generate navigation URLs for dashboards, panels, or the Explore view. Optional time ranges and custom "
            "query parameters are supported."),
    )
    async def generate_deeplink(
        resourceType: str,
        dashboardUid: Optional[str] = None,
        datasourceUid: Optional[str] = None,
        panelId: Optional[int] = None,
        queryParams: Optional[Dict[str, str]] = None,
        timeRange: Optional[Dict[str, str]] = None,
        ctx: Optional[Context] = None,
    ) -> str:
        if ctx is None:
            raise ValueError("Context injection failed for generate_deeplink")
        base_url = _ensure_base_url(ctx)
        resource = resourceType.lower()
        deeplink: str
        if resource == "dashboard":
            if not dashboardUid:
                raise ValueError(
                    "dashboardUid is required for dashboard links")
            deeplink = f"{base_url}/d/{dashboardUid}"
        elif resource == "panel":
            if not dashboardUid or panelId is None:
                raise ValueError(
                    "dashboardUid and panelId are required for panel links")
            deeplink = f"{base_url}/d/{dashboardUid}?viewPanel={panelId}"
        elif resource == "explore":
            if not datasourceUid:
                raise ValueError("datasourceUid is required for Explore links")
            state = {"left": f"{{\"datasource\":\"{datasourceUid}\"}}"}
            deeplink = f"{base_url}/explore?{urlencode(state)}"
        else:
            raise ValueError(
                "Unsupported resource type. Supported values are: dashboard, panel, explore."
            )

        if timeRange:
            params = {}
            if "from" in timeRange and timeRange["from"]:
                params["from"] = timeRange["from"]
            if "to" in timeRange and timeRange["to"]:
                params["to"] = timeRange["to"]
            deeplink = _append_query(deeplink, params)

        if queryParams:
            deeplink = _append_query(deeplink, queryParams)

        return deeplink


__all__ = ["register"]
