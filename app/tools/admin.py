"""Administrative Grafana FastMCP tools implemented in Python."""

from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaClient


async def _list_teams(query: Optional[str], ctx: Context) -> Dict[str, Any]:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    params = {"query": query} if query else None
    return await client.get_json("/teams/search", params=params)


async def _list_users(ctx: Context) -> Any:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    return await client.get_json("/org/users")


def register(app: FastMCP) -> None:
    """Register administrative tools with the given FastMCP server."""

    @app.tool(
        name="list_teams", title="List teams", description=(
            "Search for Grafana teams by name. Returns a consolidated response object containing "
            "team metadata, search query, and total count. "
            "This format prevents JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."), )
    async def list_teams(
        query: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError("Context injection failed for list_teams")
        result = await _list_teams(query, ctx)

        # Extract teams array from the API response
        teams = result.get(
            "teams",
            []) if isinstance(
            result,
            dict) else (
            result if isinstance(
                result,
                list) else [])

        return {
            "teams": teams,
            "total_count": len(teams),
            "query": query,
            "type": "teams_search_result"
        }

    @app.tool(
        name="list_users_by_org", title="List users by organization", description=(
            "Return all users that belong to the current Grafana organization. Returns a consolidated "
            "response object containing users list, email, roles, and status metadata. "
            "This format prevents JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."), )
    async def list_users_by_org(
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError("Context injection failed for list_users_by_org")
        result = await _list_users(ctx)

        # Ensure we have a list, even if the API returns something unexpected
        users = result if isinstance(result, list) else []

        return {
            "users": users,
            "total_count": len(users),
            "type": "org_users_result"
        }


__all__ = ["register"]
