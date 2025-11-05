"""Search and fetch tools for Grafana resources."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaClient


def _normalize_identifier(value: Any) -> Optional[str]:
    """Convert potential identifiers into a sanitized string."""

    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    if isinstance(value, int):
        return str(value)
    return None


def _parse_dashboard_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract UID or numeric ID information from dashboard-style URLs."""

    parsed = urlparse(url)
    path = parsed.path or ""
    segments = [segment for segment in path.split("/") if segment]

    uid: Optional[str] = None
    numeric_id: Optional[str] = None

    if len(segments) >= 2 and segments[0] in {"d", "d-solo"}:
        candidate = _normalize_identifier(segments[1])
        if candidate:
            uid = candidate

    for index, segment in enumerate(segments):
        if segment == "dashboards" and index + 2 < len(segments):
            key = segments[index + 1]
            value = _normalize_identifier(segments[index + 2])
            if key == "uid" and value:
                uid = value
                break
            if key == "id" and value:
                numeric_id = value
                break

    return uid, numeric_id


DashboardIdentifier = Mapping[str, Any] | str | int


def _resolve_dashboard_lookup(
    *,
    uid: Optional[str],
    id_value: int | str | None,
    ids: Sequence[DashboardIdentifier] | None,
    url: Optional[str],
    uri: Optional[str],
    item: Mapping[str, Any] | None,
) -> Tuple[Optional[str], Optional[str]]:
    """Determine the best UID or ID to use when fetching a dashboard."""

    candidate_uid = _normalize_identifier(uid)
    candidate_numeric_id = _normalize_identifier(id_value)

    metadata = item or {}
    if not candidate_uid and isinstance(metadata, Mapping):
        candidate_uid = _normalize_identifier(metadata.get("uid"))
    if not candidate_numeric_id and isinstance(metadata, Mapping):
        candidate_numeric_id = _normalize_identifier(metadata.get("id"))

    candidate_url: Optional[str] = None
    for potential in (url, uri):
        if potential and isinstance(potential, str):
            candidate_url = potential
            break
    if not candidate_url and isinstance(metadata, Mapping):
        meta_url = metadata.get("url") or metadata.get("uri")
        if isinstance(meta_url, str):
            candidate_url = meta_url

    if candidate_url:
        parsed_uid, parsed_numeric = _parse_dashboard_url(candidate_url)
        if not candidate_uid and parsed_uid:
            candidate_uid = parsed_uid
        if not candidate_numeric_id and parsed_numeric:
            candidate_numeric_id = parsed_numeric

    if ids:
        for entry in ids:
            if isinstance(entry, Mapping):
                if not candidate_uid:
                    candidate_uid = _normalize_identifier(entry.get("uid"))
                if not candidate_numeric_id:
                    candidate_numeric_id = _normalize_identifier(
                        entry.get("id"))
                if not candidate_url:
                    entry_url = entry.get("url") or entry.get("uri")
                    if isinstance(entry_url, str):
                        candidate_url = entry_url
            else:
                if not candidate_uid:
                    candidate = _normalize_identifier(entry)
                    if candidate:
                        candidate_uid = candidate
            if candidate_uid and candidate_numeric_id:
                break

        if candidate_url:
            parsed_uid, parsed_numeric = _parse_dashboard_url(candidate_url)
            if not candidate_uid and parsed_uid:
                candidate_uid = parsed_uid
            if not candidate_numeric_id and parsed_numeric:
                candidate_numeric_id = parsed_numeric

    if candidate_numeric_id and not candidate_numeric_id.isdigit():
        candidate_numeric_id = None

    return candidate_uid, candidate_numeric_id


async def _fetch_dashboard(
    client: GrafanaClient,
    *,
    uid: Optional[str],
    numeric_id: Optional[str],
) -> Any:
    """Fetch a dashboard using either its UID or numeric ID."""

    if uid:
        return await client.get_json(f"/dashboards/uid/{uid}")
    if numeric_id:
        return await client.get_json(f"/dashboards/id/{numeric_id}")
    raise ValueError(
        "A dashboard UID or ID is required to fetch dashboard details")


async def _fetch_resource(
    client: GrafanaClient,
    *,
    resource_type: Optional[str],
    id_value: int | str | None,
    uid: Optional[str],
    ids: Sequence[DashboardIdentifier] | None,
    url: Optional[str],
    uri: Optional[str],
    item: Mapping[str, Any] | None,
) -> Any:
    """Dispatch resource fetching based on the provided metadata."""

    type_hint = _normalize_identifier(resource_type)
    if not type_hint and item:
        type_hint = _normalize_identifier(item.get("type"))

    resolved_type = (type_hint or "dash-db").lower()
    if resolved_type in {"dash-db", "dashboard", "dashboards"}:
        resolved_uid, resolved_numeric_id = _resolve_dashboard_lookup(
            uid=uid,
            id_value=id_value,
            ids=ids,
            url=url,
            uri=uri,
            item=item,
        )
        if not resolved_uid and not resolved_numeric_id:
            raise ValueError(
                "An UID, numeric ID, or URL is required to fetch dashboard details")
        return await _fetch_dashboard(client, uid=resolved_uid, numeric_id=resolved_numeric_id)

    raise ValueError(f"Unsupported resource type '{resolved_type}' for fetch")


async def _search_dashboards(query: Optional[str], ctx: Context) -> Any:
    """
    Search for Grafana dashboards and return a consolidated response.

    This function wraps the raw Grafana search API response in a structured object
    to prevent JSON chunking issues when used with streamable HTTP transport
    alongside ChatGPT/OpenAI. Instead of returning the raw array from Grafana's
    /search endpoint, we return a consolidated object with metadata.

    Args:
        query: Optional search query string
        ctx: MCP context for configuration

    Returns:
        Dict containing:
        - dashboards: List of dashboard objects from Grafana API
        - total_count: Number of dashboards found
        - query: The original search query
        - type: Response type identifier ('dashboard_search_results')
    """
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    params: Dict[str, Any] = {"type": "dash-db"}
    if query:
        params["query"] = query

    # Get the raw JSON response from Grafana
    raw_response = await client.get_json("/search", params=params)

    # Ensure we have a list, even if the API returns something unexpected
    dashboards = raw_response if isinstance(raw_response, list) else []

    # Return a consolidated response object to avoid chunking issues
    # in streamable HTTP with ChatGPT/OpenAI
    return {
        "dashboards": dashboards,
        "total_count": len(dashboards),
        "query": query or "",
        "type": "dashboard_search_results"
    }


def _normalize_search_query(raw: Optional[str]) -> Optional[str]:
    """Normalize search query inputs to satisfy MCP search contract."""

    if raw is None:
        return None
    trimmed = raw.strip()
    return trimmed or None


def register(app: FastMCP) -> None:
    """Register search-related tools."""

    @app.tool(
        name="search_dashboards", title="Search dashboards", description=(
            "Search Grafana dashboards by a query string. Returns a consolidated response object "
            "containing matching dashboards, total count, query, and metadata. "
            "This format prevents JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."), )
    async def search_dashboards(
        query: str,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError("Context injection failed for search_dashboards")
        normalized_query = _normalize_search_query(query)
        return await _search_dashboards(normalized_query, ctx)

    @app.tool(
        name="search", title="Search Grafana", description=(
            "General purpose search endpoint used by MCP clients. Returns a consolidated response "
            "object containing matching dashboard metadata, total count, and query info. "
            "This format prevents JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."), )
    async def search(
        query: str,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError("Context injection failed for search")
        normalized_query = _normalize_search_query(query)
        return await _search_dashboards(normalized_query, ctx)

    @app.tool(
        name="fetch", title="Fetch Grafana resource", description=(
            "Retrieve detailed Grafana resource data using identifiers returned by search results. "
            "Currently supports dashboards via UID, numeric ID, or dashboard URLs."), )
    async def fetch(
        *,
        id: str,
        uid: Optional[str] = None,
        ids: Optional[Sequence[DashboardIdentifier]] = None,
        url: Optional[str] = None,
        uri: Optional[str] = None,
        type: Optional[str] = None,
        resource_type: Optional[str] = None,
        item: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError("Context injection failed for fetch")

        metadata: Mapping[str, Any] | None = item
        type_hint = resource_type or type
        if not type_hint and metadata:
            type_hint = metadata.get("type")  # type: ignore[arg-type]

        normalized_id = _normalize_identifier(id)

        config = get_grafana_config(ctx)
        client = GrafanaClient(config)
        return await _fetch_resource(
            client,
            resource_type=type_hint,
            id_value=normalized_id,
            uid=uid,
            ids=ids,
            url=url,
            uri=uri,
            item=metadata,
        )


__all__ = ["register"]
