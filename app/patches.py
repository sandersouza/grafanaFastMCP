"""Compatibility patches for the upstream MCP server implementation."""

from __future__ import annotations

import logging
import os

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
_PATCH_SSE_ALIAS_APPLIED = False


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


def ensure_sse_post_alias_patch() -> None:
    """Allow POST requests on the SSE endpoint to deliver JSON-RPC messages."""

    global _PATCH_SSE_ALIAS_APPLIED
    if _PATCH_SSE_ALIAS_APPLIED:
        return

    try:
        from mcp.server.fastmcp.server import FastMCP  # type: ignore[import]
        from mcp.server.sse import SseServerTransport  # type: ignore[import]
        import mcp.types as mcp_types  # type: ignore[import]
        from mcp.shared.message import ServerMessageMetadata, SessionMessage  # type: ignore[import]
    except (ImportError, SyntaxError) as exc:  # pragma: no cover - depends on runtime env
        LOGGER.debug("Skipping SSE alias patch: %s", exc)
        return

    try:
        from starlette.applications import Starlette
        from starlette.background import BackgroundTask
        from starlette.middleware import Middleware
        from starlette.middleware.authentication import AuthenticationMiddleware
        from starlette.requests import Request
        from starlette.responses import Response
        from starlette.routing import Mount, Route
    except ImportError as exc:  # pragma: no cover - runtime dependency
        LOGGER.debug("Starlette import failed, skipping SSE alias patch: %s", exc)
        return

    try:
        from pydantic import ValidationError
    except ImportError as exc:  # pragma: no cover
        LOGGER.debug("Pydantic not available, skipping SSE alias patch: %s", exc)
        return

    original_sse_app = FastMCP.sse_app

    def patched_sse_app(self: FastMCP, mount_path: str | None = None):
        if mount_path is not None:
            self.settings.mount_path = mount_path

        normalized_message_endpoint = self._normalize_path(  # type: ignore[attr-defined]
            self.settings.mount_path, self.settings.message_path
        )

        sse_transport = SseServerTransport(normalized_message_endpoint)

        async def handle_sse(scope, receive, send):
            async with sse_transport.connect_sse(scope, receive, send) as streams:  # type: ignore[attr-defined]
                await self._mcp_server.run(  # type: ignore[attr-defined]
                    streams[0],
                    streams[1],
                    self._mcp_server.create_initialization_options(),  # type: ignore[attr-defined]
                )
            return Response()

        async def handle_sse_post(request: Request) -> Response:
            session_id_param = request.query_params.get("session_id")
            if session_id_param is None:
                return Response("session_id is required", status_code=400)

            try:
                from uuid import UUID

                session_id = UUID(hex=session_id_param)
            except ValueError:
                return Response("Invalid session ID", status_code=400)

            writer = sse_transport._read_stream_writers.get(session_id)  # type: ignore[attr-defined]
            if not writer:
                return Response("Could not find session", status_code=404)

            body = await request.body()
            try:
                message = mcp_types.JSONRPCMessage.model_validate_json(body)  # type: ignore[attr-defined]
            except ValidationError as err:
                task = BackgroundTask(writer.send, err)
                return Response("Could not parse message", status_code=400, background=task)

            metadata = ServerMessageMetadata(request_context=request)
            session_message = SessionMessage(message, metadata=metadata)
            task = BackgroundTask(writer.send, session_message)
            return Response("Accepted", status_code=202, background=task)

        async def dispatch_endpoint(request: Request) -> Response:
            if request.method.upper() == "POST":
                return await handle_sse_post(request)
            return await handle_sse(request.scope, request.receive, request._send)

        routes: list[Route | Mount] = []
        middleware: list[Middleware] = []
        required_scopes: list[str] = []

        if getattr(self, "_auth_server_provider", None):
            try:
                from mcp.server.auth.middleware.auth_context import AuthContextMiddleware  # type: ignore[import]
                from mcp.server.auth.middleware.bearer_auth import (  # type: ignore[import]
                    BearerAuthBackend,
                    RequireAuthMiddleware,
                )
                from mcp.server.auth.routes import create_auth_routes  # type: ignore[import]
            except ImportError as exc:  # pragma: no cover - optional runtime dependency
                LOGGER.warning("Auth modules missing, skipping SSE alias patch: %s", exc)
                return original_sse_app(self, mount_path=mount_path)

            assert self.settings.auth  # type: ignore[attr-defined]
            required_scopes = self.settings.auth.required_scopes or []  # type: ignore[attr-defined]

            middleware = [
                Middleware(
                    AuthenticationMiddleware,
                    backend=BearerAuthBackend(provider=self._auth_server_provider),  # type: ignore[attr-defined]
                ),
                Middleware(AuthContextMiddleware),
            ]

            routes.extend(
                create_auth_routes(
                    provider=self._auth_server_provider,  # type: ignore[attr-defined]
                    issuer_url=self.settings.auth.issuer_url,  # type: ignore[attr-defined]
                    service_documentation_url=self.settings.auth.service_documentation_url,  # type: ignore[attr-defined]
                    client_registration_options=self.settings.auth.client_registration_options,  # type: ignore[attr-defined]
                    revocation_options=self.settings.auth.revocation_options,  # type: ignore[attr-defined]
                )
            )

            protected_endpoint = RequireAuthMiddleware(dispatch_endpoint, required_scopes)
            routes.append(
                Route(self.settings.sse_path, endpoint=protected_endpoint, methods=["GET", "POST"])
            )
            routes.append(
                Mount(
                    self.settings.message_path,
                    app=RequireAuthMiddleware(sse_transport.handle_post_message, required_scopes),
                )
            )
        else:
            async def combined_endpoint(request: Request) -> Response:
                return await dispatch_endpoint(request)

            routes.append(
                Route(self.settings.sse_path, endpoint=combined_endpoint, methods=["GET", "POST"])
            )
            routes.append(Mount(self.settings.message_path, app=sse_transport.handle_post_message))

        routes.extend(getattr(self, "_custom_starlette_routes", []))

        return Starlette(debug=self.settings.debug, routes=routes, middleware=middleware)  # type: ignore[name-defined]

    FastMCP.sse_app = patched_sse_app  # type: ignore[assignment]
    setattr(FastMCP, "_original_sse_app", original_sse_app)
    _PATCH_SSE_ALIAS_APPLIED = True


__all__ = [
    "ensure_streamable_http_accept_patch",
    "ensure_streamable_http_server_patch",
    "ensure_sse_post_alias_patch",
]
