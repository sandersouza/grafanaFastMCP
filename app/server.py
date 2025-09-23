"""Factory for the Python Grafana FastMCP server."""

from __future__ import annotations

from mcp.server import FastMCP

from .patches import ensure_streamable_http_accept_patch, ensure_streamable_http_server_patch
from .tools import register_all


def _normalize_mount_path(base_path: str) -> str:
    """Ensure the base path is absolute without trailing slash (except root)."""

    path = base_path or "/"
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return path or "/"


def _join_path(base: str, segment: str) -> str:
    """Join the base mount path with an additional segment."""

    base_part = base.rstrip("/") if base else ""
    segment_part = (segment or "").strip("/")

    if not segment_part:
        return base_part or "/"
    if not base_part or base_part == "/":
        return f"/{segment_part}"
    return f"{base_part}/{segment_part}"


def _normalize_streamable_http_path(path: str, mount_path: str, default_segment: str) -> str:
    """Resolve the streamable HTTP path, supporting relative or absolute values."""

    value = path or default_segment
    if value.startswith("/"):
        resolved = value
    else:
        resolved = _join_path(mount_path, value)

    if len(resolved) > 1 and resolved.endswith("/"):
        resolved = resolved.rstrip("/")
    return resolved or "/"

INSTRUCTIONS = """
This server provides access to your Grafana instance and the surrounding ecosystem.

Available Capabilities:
- Dashboards: Search, retrieve, update, and create dashboards. Extract panel queries and datasource information.
- Datasources: List and fetch details for datasources.
- Prometheus & Loki: Run PromQL and LogQL queries, retrieve metric/log metadata, and explore label names/values.
- Incidents: Search, create, update, and resolve incidents in Grafana Incident.
- Sift Investigations: Start and manage Sift investigations, analyze logs/traces, find error patterns, and detect slow requests.
- Alerting: List and fetch alert rules and notification contact points.
- OnCall: View and manage on-call schedules, shifts, teams, and users.
- Admin: List teams and perform administrative tasks.
- Pyroscope: Profile applications and fetch profiling data.
- Navigation: Generate deeplink URLs for Grafana resources like dashboards, panels, and Explore queries.
"""


def create_app(
    *,
    host: str,
    port: int,
    base_path: str = "/",
    streamable_http_path: str = "mcp",
    log_level: str = "INFO",
    debug: bool = False,
) -> FastMCP:
    """Create and configure the FastMCP application."""

    ensure_streamable_http_accept_patch()
    ensure_streamable_http_server_patch()

    normalized_base_path = _normalize_mount_path(base_path)
    sse_path = _join_path(normalized_base_path, "sse")
    message_path = _join_path(normalized_base_path, "messages")
    if not message_path.endswith("/"):
        message_path = f"{message_path}/"
    resolved_streamable_http_path = _normalize_streamable_http_path(
        streamable_http_path,
        normalized_base_path,
        default_segment="mcp",
    )

    app = FastMCP(
        name="mcp-grafana",
        instructions=INSTRUCTIONS,
        host=host,
        port=port,
        mount_path="/",
        sse_path=sse_path,
        message_path=message_path,
        streamable_http_path=resolved_streamable_http_path,
        log_level=log_level.upper(),
        debug=debug,
    )
    register_all(app)
    return app


__all__ = ["create_app"]
