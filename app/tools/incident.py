"""Incident management tools for Grafana."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaAPIError, GrafanaClient


async def _incident_rpc(ctx: Context, method: str,
                        payload: Dict[str, Any]) -> Dict[str, Any]:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    path = f"/plugins/grafana-irm-app/resources/api/v1/{method}"
    response = await client.post_json(path, json=payload)
    if not isinstance(response, dict):
        raise ValueError(f"Unexpected response from incident API for {method}")
    return response


def _build_query_string(include_drill: bool, status: Optional[str]) -> str:
    parts: List[str] = []
    if not include_drill:
        parts.append("isdrill:false")
    if status:
        parts.append(f"status:{status}")
    return " ".join(parts)


async def _list_incidents(
    ctx: Context,
    limit: Optional[int],
    include_drill: bool,
    status: Optional[str],
) -> Dict[str, Any]:
    effective_limit = limit if limit and limit > 0 else 10
    if effective_limit <= 0:
        raise ValueError("limit must be greater than zero")
    query_string = _build_query_string(include_drill, status)
    payload = {
        "query": {
            "limit": effective_limit,
            "orderDirection": "DESC",
            "queryString": query_string,
        }
    }
    return await _incident_rpc(ctx, "IncidentsService.QueryIncidentPreviews", payload)


async def _create_incident(
        ctx: Context, args: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "title": args.get("title"),
        "severity": args.get("severity"),
        "roomPrefix": args.get("roomPrefix"),
        "isDrill": bool(args.get("isDrill", False)),
        "status": args.get("status"),
        "attachCaption": args.get("attachCaption"),
        "attachUrl": args.get("attachUrl"),
        "labels": args.get("labels", []),
    }
    return await _incident_rpc(ctx, "IncidentsService.CreateIncident", payload)


async def _add_activity(ctx: Context, args: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "incidentID": args.get("incidentId"),
        "activityKind": "userNote",
        "body": args.get("body"),
        "eventTime": args.get("eventTime"),
    }
    return await _incident_rpc(ctx, "ActivityService.AddActivity", payload)


async def _get_incident(ctx: Context, incident_id: str) -> Dict[str, Any]:
    payload = {"incidentID": incident_id}
    return await _incident_rpc(ctx, "IncidentsService.GetIncident", payload)


def register(app: FastMCP) -> None:
    """Register incident tools."""

    @app.tool(
        name="list_incidents",
        title="List incidents",
        description="List Grafana incidents with optional status filtering and drill inclusion.",
    )
    async def list_incidents(
        limit: Optional[int] = None,
        drill: bool = False,
        status: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError("Context injection failed for list_incidents")
        return await _list_incidents(ctx, limit, drill, status)

    @app.tool(
        name="create_incident",
        title="Create incident",
        description="Create a new Grafana incident with the provided details.",
    )
    async def create_incident(
        title: str,
        severity: str,
        roomPrefix: str,
        isDrill: bool = False,
        status: Optional[str] = None,
        attachCaption: Optional[str] = None,
        attachUrl: Optional[str] = None,
        labels: Optional[List[Dict[str, Any]]] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError("Context injection failed for create_incident")
        args = {
            "title": title,
            "severity": severity,
            "roomPrefix": roomPrefix,
            "isDrill": isDrill,
            "status": status,
            "attachCaption": attachCaption,
            "attachUrl": attachUrl,
            "labels": labels or [],
        }
        return await _create_incident(ctx, args)

    @app.tool(
        name="add_activity_to_incident",
        title="Add activity to incident",
        description="Add a user note to an incident's activity timeline.",
    )
    async def add_activity_to_incident(
        incidentId: str,
        body: str,
        eventTime: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError(
                "Context injection failed for add_activity_to_incident")
        args = {
            "incidentId": incidentId,
            "body": body,
            "eventTime": eventTime,
        }
        return await _add_activity(ctx, args)

    @app.tool(
        name="get_incident",
        title="Get incident details",
        description="Retrieve the full details for a Grafana incident by ID.",
    )
    async def get_incident(
        incidentId: str,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError("Context injection failed for get_incident")
        try:
            return await _get_incident(ctx, incidentId)
        except GrafanaAPIError as exc:
            if exc.status_code == 404:
                raise ValueError(
                    f"Incident with ID '{incidentId}' not found") from exc
            raise


__all__ = ["register"]
