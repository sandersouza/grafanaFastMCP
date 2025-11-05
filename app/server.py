"""Factory for the Python Grafana FastMCP server."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server import FastMCP

from .instructions import load_instructions
from .patches import (
    ensure_sse_post_alias_patch,
    ensure_sse_server_patch,
    ensure_streamable_http_accept_patch,
    ensure_streamable_http_instructions_patch,
    ensure_streamable_http_server_patch,
    set_streamable_http_instructions,
)
from .tools import register_all

LOGGER = logging.getLogger(__name__)


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


def _normalize_streamable_http_path(
        path: str,
        mount_path: str,
        default_segment: str) -> str:
    """Resolve the streamable HTTP path, supporting relative or absolute values."""

    value = path or default_segment
    if value.startswith("/"):
        resolved = value
    else:
        resolved = _join_path(mount_path, value)

    if len(resolved) > 1 and resolved.endswith("/"):
        resolved = resolved.rstrip("/")
    return resolved or "/"


def _register_streamable_http_alias(app: FastMCP) -> None:
    """Expose ``/{prefix}/link_{id}/…`` as an alias for the Streamable HTTP endpoint."""

    routes: Any = getattr(app, "_custom_starlette_routes", None)
    if not isinstance(routes, list):
        return

    alias_name = "streamable-http-link-alias"
    if any(getattr(route, "name", None) == alias_name for route in routes):
        return

    try:
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
    except Exception:  # pragma: no cover - optional runtime dependency
        LOGGER.debug(
            "Streamable HTTP alias disabled: Starlette not available",
            exc_info=True)
        return

    try:
        from mcp.server.fastmcp.server import StreamableHTTPASGIApp
    except Exception:  # pragma: no cover - optional runtime dependency
        LOGGER.debug(
            "Streamable HTTP alias disabled: FastMCP server module unavailable",
            exc_info=True)
        return

    class _StreamableHTTPLinkAlias:
        def __init__(self, fastmcp_app: FastMCP) -> None:
            self._fastmcp = fastmcp_app

        # type: ignore[no-untyped-def]
        async def __call__(self, scope, receive, send) -> None:
            fastmcp_app = self._fastmcp
            if getattr(fastmcp_app, "_session_manager", None) is None:
                fastmcp_app.streamable_http_app()

            session_manager = getattr(fastmcp_app, "_session_manager", None)
            if session_manager is None:
                response = PlainTextResponse(
                    "Streamable HTTP session manager unavailable",
                    status_code=503,
                )
                await response(scope, receive, send)
                return

            alias_scope = dict(scope)
            alias_scope["path"] = fastmcp_app.settings.streamable_http_path
            alias_scope.setdefault("root_path", "")

            alias_app = StreamableHTTPASGIApp(session_manager)
            await alias_app(alias_scope, receive, send)

    routes.append(
        Route(
            "/{prefix}/link_{link_id}/{rest:path}",
            endpoint=_StreamableHTTPLinkAlias(app),
            methods=["GET", "POST", "DELETE"],
            name=alias_name,
            include_in_schema=False,
        )
    )


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

    instructions = load_instructions()
    set_streamable_http_instructions(instructions)

    ensure_streamable_http_accept_patch()
    ensure_streamable_http_server_patch()
    ensure_sse_server_patch()
    ensure_streamable_http_instructions_patch()
    ensure_sse_post_alias_patch()

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
        instructions=instructions,
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
    _register_streamable_http_alias(app)
    return app


__all__ = ["create_app"]
