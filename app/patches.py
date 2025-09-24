"""Compatibility patches for the upstream MCP server implementation."""

from __future__ import annotations

import os
import logging

from starlette.requests import Request

from mcp.server.streamable_http import (
    CONTENT_TYPE_JSON,
    CONTENT_TYPE_SSE,
    StreamableHTTPServerTransport,
)
from mcp.server.fastmcp import FastMCP

LOGGER = logging.getLogger(__name__)

_PATCH_ACCEPT_APPLIED = False
_PATCH_STREAMABLE_SERVER_APPLIED = False


def _normalize_media_types(accept_header: str) -> list[str]:
    """Split and normalize media types from an Accept header."""

    media_types: list[str] = []
    for raw_media in accept_header.split(","):
        media = raw_media.strip()
        if not media:
            continue
        base_media = media.split(";", 1)[0].strip().lower()
        if base_media:
            media_types.append(base_media)
    return media_types


def _is_application_wildcard(media_type: str) -> bool:
    return media_type.endswith("/*") and media_type.split("/", 1)[0] == "application"


def _is_text_wildcard(media_type: str) -> bool:
    return media_type.endswith("/*") and media_type.split("/", 1)[0] == "text"


def ensure_streamable_http_accept_patch() -> None:
    """Relax the Accept header requirements for StreamableHTTP requests."""

    global _PATCH_ACCEPT_APPLIED
    if _PATCH_ACCEPT_APPLIED:
        return

    original_check = StreamableHTTPServerTransport._check_accept_headers

    def patched_check_accept_headers(
        self: StreamableHTTPServerTransport,
        request: Request,
    ) -> tuple[bool, bool]:
        accept_header = request.headers.get("accept", "")
        if not accept_header.strip():
            return True, True

        media_types = _normalize_media_types(accept_header)
        if not media_types:
            return True, True

        wildcard_all = any(media in {"*/*", "*"} for media in media_types)

        has_json = any(
            media.startswith(CONTENT_TYPE_JSON)
            or _is_application_wildcard(media)
            or media.startswith(f"{CONTENT_TYPE_JSON}+")
            for media in media_types
        )
        has_sse = any(
            media.startswith(CONTENT_TYPE_SSE)
            or _is_text_wildcard(media)
            for media in media_types
        )

        if wildcard_all:
            return True, True

        if not has_json and has_sse:
            has_json = True

        return has_json, has_sse

    StreamableHTTPServerTransport._check_accept_headers = patched_check_accept_headers  # type: ignore[assignment]
    setattr(StreamableHTTPServerTransport, "_original_check_accept_headers", original_check)
    _PATCH_ACCEPT_APPLIED = True


def ensure_streamable_http_server_patch() -> None:
    """Adjust FastMCP Streamable HTTP server defaults for long-running requests."""

    global _PATCH_STREAMABLE_SERVER_APPLIED
    if _PATCH_STREAMABLE_SERVER_APPLIED:
        return

    original_impl = FastMCP.run_streamable_http_async

    async def patched_run_streamable_http_async(self: FastMCP) -> None:
        """Run Streamable HTTP transport with configurable timeout settings."""

        import uvicorn

        starlette_app = self.streamable_http_app()

        keep_alive_timeout = float(os.environ.get("MCP_STREAMABLE_HTTP_TIMEOUT_KEEP_ALIVE", "65"))
        notify_timeout = float(os.environ.get("MCP_STREAMABLE_HTTP_TIMEOUT_NOTIFY", "120"))
        graceful_timeout = float(
            os.environ.get(
                "MCP_STREAMABLE_HTTP_TIMEOUT_GRACEFUL_SHUTDOWN",
                str(max(notify_timeout, 120.0)),
            )
        )

        LOGGER.info(
            "Streamable HTTP timeouts configured (keep_alive=%ss, notify=%ss, graceful_shutdown=%ss)",
            keep_alive_timeout,
            notify_timeout,
            graceful_timeout,
        )

        config = uvicorn.Config(
            starlette_app,
            host=self.settings.host,
            port=self.settings.port,
            log_level=self.settings.log_level.lower(),
            timeout_keep_alive=keep_alive_timeout,
            timeout_notify=notify_timeout,
            timeout_graceful_shutdown=graceful_timeout,
        )
        server = uvicorn.Server(config)
        await server.serve()

    setattr(FastMCP, "_original_run_streamable_http_async", original_impl)
    FastMCP.run_streamable_http_async = patched_run_streamable_http_async  # type: ignore[assignment]
    _PATCH_STREAMABLE_SERVER_APPLIED = True


__all__ = ["ensure_streamable_http_accept_patch", "ensure_streamable_http_server_patch"]
