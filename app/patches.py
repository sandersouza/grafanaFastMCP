"""Compatibility patches for the upstream MCP server implementation."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from starlette.requests import Request

from mcp.server.streamable_http import (
    CONTENT_TYPE_JSON,
    CONTENT_TYPE_SSE,
    StreamableHTTPServerTransport,
)
from mcp.server.fastmcp import FastMCP

from .instructions import format_instructions

LOGGER = logging.getLogger(__name__)

_PATCH_ACCEPT_APPLIED = False
_PATCH_STREAMABLE_SERVER_APPLIED = False
_PATCH_SSE_SERVER_APPLIED = False
_PATCH_SSE_ALIAS_APPLIED = False
_PATCH_STREAMABLE_INSTRUCTIONS_APPLIED = False

_STREAMABLE_HTTP_INSTRUCTIONS: str | None = None


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
    return media_type.endswith(
        "/*") and media_type.split("/", 1)[0] == "application"


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

    # type: ignore[assignment]
    StreamableHTTPServerTransport._check_accept_headers = patched_check_accept_headers
    setattr(
        StreamableHTTPServerTransport,
        "_original_check_accept_headers",
        original_check)
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

        keep_alive_timeout = float(
            os.environ.get(
                "MCP_STREAMABLE_HTTP_TIMEOUT_KEEP_ALIVE",
                "65"))
        notify_timeout = float(
            os.environ.get(
                "MCP_STREAMABLE_HTTP_TIMEOUT_NOTIFY",
                "120"))
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
        setattr(self, "_uvicorn_server", server)
        try:
            await server.serve()
        finally:
            if getattr(self, "_uvicorn_server", None) is server:
                setattr(self, "_uvicorn_server", None)

    setattr(FastMCP, "_original_run_streamable_http_async", original_impl)
    # type: ignore[assignment]
    FastMCP.run_streamable_http_async = patched_run_streamable_http_async
    _PATCH_STREAMABLE_SERVER_APPLIED = True


def ensure_sse_server_patch() -> None:
    """Store the SSE uvicorn server instance for graceful shutdown."""

    global _PATCH_SSE_SERVER_APPLIED
    if _PATCH_SSE_SERVER_APPLIED:
        return

    try:
        original_impl = FastMCP.run_sse_async
    except AttributeError:
        LOGGER.debug("SSE server patch skipped: run_sse_async not available")
        _PATCH_SSE_SERVER_APPLIED = True
        return

    async def patched_run_sse_async(
            self: FastMCP,
            mount_path: str | None = None) -> None:
        import uvicorn

        starlette_app = self.sse_app(mount_path)
        config = uvicorn.Config(
            starlette_app,
            host=self.settings.host,
            port=self.settings.port,
            log_level=self.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        setattr(self, "_uvicorn_server", server)
        try:
            await server.serve()
        finally:
            if getattr(self, "_uvicorn_server", None) is server:
                setattr(self, "_uvicorn_server", None)

    setattr(FastMCP, "_original_run_sse_async", original_impl)
    FastMCP.run_sse_async = patched_run_sse_async  # type: ignore[assignment]
    _PATCH_SSE_SERVER_APPLIED = True


def set_streamable_http_instructions(value: str | None) -> None:
    """Persist the pre-prompt that should be enforced on Streamable HTTP sessions."""

    global _STREAMABLE_HTTP_INSTRUCTIONS
    normalized = value.strip() if isinstance(value, str) else ""
    _STREAMABLE_HTTP_INSTRUCTIONS = normalized or ""
    try:
        setattr(
            StreamableHTTPServerTransport,
            "_fastmcp_preprompt_text",
            _STREAMABLE_HTTP_INSTRUCTIONS)
    except Exception:
        LOGGER.debug(
            "Could not attach pre-prompt to StreamableHTTP transport",
            exc_info=True)


def _resolve_request_instructions(
        request: Request,
        default_text: str | None) -> Optional[str]:
    """Resolve the instruction text using headers or the cached default."""

    header_template = request.headers.get("x-preprompt-id")
    if header_template:
        env_key = f"MCP_PREPROMPT_{header_template}".upper().replace("-", "_")
        env_value = os.getenv(env_key)
        if env_value:
            return format_instructions(env_value.strip())

    tenant_key = request.headers.get("x-tenant")
    if tenant_key:
        env_key = f"MCP_PREPROMPT_TENANT_{tenant_key}".upper().replace(
            "-", "_")
        env_value = os.getenv(env_key)
        if env_value:
            return format_instructions(env_value.strip())

    header_text = request.headers.get("x-preprompt")
    if header_text and header_text.strip():
        return format_instructions(header_text.strip())

    if isinstance(default_text, str) and default_text.strip():
        return format_instructions(default_text.strip())
    return None


def _build_session_update_event(instructions_text: str) -> dict[str, str]:
    payload = {
        "type": "session.update",
        "session": {"instructions": instructions_text},
    }
    return {"event": "message", "data": json.dumps(payload)}


def ensure_streamable_http_instructions_patch() -> None:
    """Emit session.update events so hosts receive the configured pre-prompt."""

    global _PATCH_STREAMABLE_INSTRUCTIONS_APPLIED
    if _PATCH_STREAMABLE_INSTRUCTIONS_APPLIED:
        return

    if not hasattr(StreamableHTTPServerTransport, "_handle_post_request"):
        LOGGER.debug(
            "Streamable HTTP instructions patch skipped: transport does not expose '_handle_post_request'"
        )
        return

    try:  # pragma: no cover - depends on optional runtime dependencies
        import anyio
        from http import HTTPStatus
        from pydantic import ValidationError
        from sse_starlette import EventSourceResponse
        from starlette.types import Receive, Scope, Send

        from mcp.server.streamable_http import EventMessage
        from mcp.shared.message import ServerMessageMetadata, SessionMessage
        from mcp.types import (
            INTERNAL_ERROR,
            INVALID_PARAMS,
            PARSE_ERROR,
            JSONRPCError,
            JSONRPCMessage,
            JSONRPCRequest,
            JSONRPCResponse,
        )
    except Exception as exc:  # pragma: no cover - runtime guard
        LOGGER.warning(
            "Streamable HTTP instructions patch unavailable: %s", exc)
        return

    transport_logger = logging.getLogger(
        StreamableHTTPServerTransport.__module__)

    original_handle_post = StreamableHTTPServerTransport._handle_post_request

    async def patched_handle_post_request(
        self: StreamableHTTPServerTransport,
        scope: Scope,
        request: Request,
        receive: Receive,
        send: Send,
    ) -> None:
        writer = self._read_stream_writer
        if writer is None:
            raise ValueError(
                "No read stream writer available. Ensure connect() is called first.")
        try:
            has_json, has_sse = self._check_accept_headers(request)
            if not (has_json and has_sse):
                response = self._create_error_response(
                    ("Not Acceptable: Client must accept both application/json and text/event-stream"),
                    HTTPStatus.NOT_ACCEPTABLE,
                )
                await response(scope, receive, send)
                return

            if not self._check_content_type(request):
                response = self._create_error_response(
                    "Unsupported Media Type: Content-Type must be application/json",
                    HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                )
                await response(scope, receive, send)
                return

            body = await request.body()

            try:
                raw_message = json.loads(body)
            except json.JSONDecodeError as err:
                response = self._create_error_response(
                    f"Parse error: {err}", HTTPStatus.BAD_REQUEST, PARSE_ERROR
                )
                await response(scope, receive, send)
                return

            try:
                message = JSONRPCMessage.model_validate(raw_message)
            except ValidationError as err:
                response = self._create_error_response(
                    f"Validation error: {err}",
                    HTTPStatus.BAD_REQUEST,
                    INVALID_PARAMS,
                )
                await response(scope, receive, send)
                return

            is_initialization_request = (
                isinstance(
                    message.root,
                    JSONRPCRequest) and message.root.method == "initialize")

            if is_initialization_request:
                if self.mcp_session_id:
                    request_session_id = self._get_session_id(request)
                    if request_session_id and request_session_id != self.mcp_session_id:
                        response = self._create_error_response(
                            "Not Found: Invalid or expired session ID",
                            HTTPStatus.NOT_FOUND,
                        )
                        await response(scope, receive, send)
                        return
            elif not await self._validate_request_headers(request, send):
                return

            if not isinstance(message.root, JSONRPCRequest):
                response = self._create_json_response(
                    None,
                    HTTPStatus.ACCEPTED,
                )
                await response(scope, receive, send)

                metadata = ServerMessageMetadata(request_context=request)
                session_message = SessionMessage(message, metadata=metadata)
                await writer.send(session_message)

                return

            request_id = str(message.root.id)
            self._request_streams[request_id] = anyio.create_memory_object_stream[EventMessage](
                0)
            request_stream_reader = self._request_streams[request_id][1]

            instructions_event: dict[str, str] | None = None
            if is_initialization_request:
                instructions_event_text = _resolve_request_instructions(request, getattr(
                    self, "_fastmcp_preprompt_text", _STREAMABLE_HTTP_INSTRUCTIONS), )
                if instructions_event_text:
                    instructions_event = _build_session_update_event(
                        instructions_event_text)
                    if hasattr(request, "state"):
                        setattr(
                            request.state,
                            "fastmcp_instructions_applied",
                            True)
                        setattr(
                            request.state,
                            "fastmcp_instructions",
                            instructions_event_text)

            if self.is_json_response_enabled:
                metadata = ServerMessageMetadata(request_context=request)
                session_message = SessionMessage(message, metadata=metadata)
                await writer.send(session_message)
                try:
                    response_message = None

                    async for event_message in request_stream_reader:
                        if isinstance(
                                event_message.message.root,
                                JSONRPCResponse | JSONRPCError):
                            response_message = event_message.message
                            break
                        else:
                            transport_logger.debug("received: %s", getattr(
                                event_message.message.root, "method", "?"))

                    if response_message:
                        response = self._create_json_response(response_message)
                        await response(scope, receive, send)
                    else:
                        transport_logger.error(
                            "No response message received before stream closed")
                        response = self._create_error_response(
                            "Error processing request: No response received",
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                        )
                        await response(scope, receive, send)
                except Exception:
                    transport_logger.exception(
                        "Error processing JSON response")
                    response = self._create_error_response(
                        "Error processing request",
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        INTERNAL_ERROR,
                    )
                    await response(scope, receive, send)
                finally:
                    await self._clean_up_memory_streams(request_id)
            else:
                sse_stream_writer, sse_stream_reader = anyio.create_memory_object_stream[dict[str, str]](
                    0)

                instructions_event_state = instructions_event

                async def sse_writer() -> None:
                    nonlocal instructions_event_state
                    try:
                        async with sse_stream_writer, request_stream_reader:
                            async for event_message in request_stream_reader:
                                event_data = self._create_event_data(
                                    event_message)
                                await sse_stream_writer.send(event_data)

                                if (instructions_event_state and isinstance(
                                        event_message.message.root, JSONRPCResponse)):
                                    await sse_stream_writer.send(instructions_event_state)
                                    instructions_event_state = None

                                if isinstance(
                                    event_message.message.root,
                                    JSONRPCResponse | JSONRPCError,
                                ):
                                    break
                    except Exception:
                        transport_logger.exception("Error in SSE writer")
                    finally:
                        transport_logger.debug("Closing SSE writer")
                        await self._clean_up_memory_streams(request_id)

                headers = {
                    "Cache-Control": "no-cache, no-transform",
                    "Connection": "keep-alive",
                    "Content-Type": CONTENT_TYPE_SSE,
                    **({"mcp-session-id": self.mcp_session_id} if self.mcp_session_id else {}),
                }
                response = EventSourceResponse(
                    content=sse_stream_reader,
                    data_sender_callable=sse_writer,
                    headers=headers,
                )

                try:
                    async with anyio.create_task_group() as tg:
                        tg.start_soon(response, scope, receive, send)
                        metadata = ServerMessageMetadata(
                            request_context=request)
                        session_message = SessionMessage(
                            message, metadata=metadata)
                        await writer.send(session_message)
                except Exception:
                    transport_logger.exception("SSE response error")
                    await sse_stream_writer.aclose()
                    await sse_stream_reader.aclose()
                    await self._clean_up_memory_streams(request_id)

        except Exception as err:  # pragma: no cover - defensive
            transport_logger.exception("Error handling POST request")
            response = self._create_error_response(
                f"Error handling POST request: {err}",
                HTTPStatus.INTERNAL_SERVER_ERROR,
                INTERNAL_ERROR,
            )
            await response(scope, receive, send)
            if writer:
                await writer.send(Exception(err))
            return

    # type: ignore[assignment]
    StreamableHTTPServerTransport._handle_post_request = patched_handle_post_request
    setattr(
        StreamableHTTPServerTransport,
        "_original_handle_post_request",
        original_handle_post)
    _PATCH_STREAMABLE_INSTRUCTIONS_APPLIED = True


def ensure_sse_post_alias_patch() -> None:
    """Allow POST requests on the SSE endpoint to deliver JSON-RPC messages."""

    global _PATCH_SSE_ALIAS_APPLIED
    if _PATCH_SSE_ALIAS_APPLIED:
        return

    try:
        from mcp.server.fastmcp.server import FastMCP  # type: ignore[import]
        from mcp.server.sse import SseServerTransport  # type: ignore[import]
        import mcp.types as mcp_types  # type: ignore[import]
        # type: ignore[import]
        from mcp.shared.message import ServerMessageMetadata, SessionMessage
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
        LOGGER.debug(
            "Starlette import failed, skipping SSE alias patch: %s", exc)
        return

    try:
        from pydantic import ValidationError
    except ImportError as exc:  # pragma: no cover
        LOGGER.debug(
            "Pydantic not available, skipping SSE alias patch: %s", exc)
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
            # type: ignore[attr-defined]
            async with sse_transport.connect_sse(scope, receive, send) as streams:
                await self._mcp_server.run(  # type: ignore[attr-defined]
                    streams[0],
                    streams[1],
                    # type: ignore[attr-defined]
                    self._mcp_server.create_initialization_options(),
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

            writer = sse_transport._read_stream_writers.get(
                session_id)  # type: ignore[attr-defined]
            if not writer:
                return Response("Could not find session", status_code=404)

            body = await request.body()
            try:
                message = mcp_types.JSONRPCMessage.model_validate_json(
                    body)  # type: ignore[attr-defined]
            except ValidationError as err:
                task = BackgroundTask(writer.send, err)
                return Response(
                    "Could not parse message",
                    status_code=400,
                    background=task)

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
                # type: ignore[import]
                from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
                from mcp.server.auth.middleware.bearer_auth import (  # type: ignore[import]
                    BearerAuthBackend,
                    RequireAuthMiddleware,
                )
                # type: ignore[import]
                from mcp.server.auth.routes import create_auth_routes
            except ImportError as exc:  # pragma: no cover - optional runtime dependency
                LOGGER.warning(
                    "Auth modules missing, skipping SSE alias patch: %s", exc)
                return original_sse_app(self, mount_path=mount_path)

            assert self.settings.auth  # type: ignore[attr-defined]
            # type: ignore[attr-defined]
            required_scopes = self.settings.auth.required_scopes or []

            middleware = [
                Middleware(
                    AuthenticationMiddleware,
                    backend=BearerAuthBackend(
                        provider=self._auth_server_provider),
                    # type: ignore[attr-defined]
                ),
                Middleware(AuthContextMiddleware),
            ]

            routes.extend(
                create_auth_routes(
                    # type: ignore[attr-defined]
                    provider=self._auth_server_provider,
                    # type: ignore[attr-defined]
                    issuer_url=self.settings.auth.issuer_url,
                    # type: ignore[attr-defined]
                    service_documentation_url=self.settings.auth.service_documentation_url,
                    # type: ignore[attr-defined]
                    client_registration_options=self.settings.auth.client_registration_options,
                    # type: ignore[attr-defined]
                    revocation_options=self.settings.auth.revocation_options,
                )
            )

            protected_endpoint = RequireAuthMiddleware(
                dispatch_endpoint, required_scopes)
            routes.append(
                Route(
                    self.settings.sse_path,
                    endpoint=protected_endpoint,
                    methods=[
                        "GET",
                        "POST"]))
            routes.append(
                Mount(
                    self.settings.message_path,
                    app=RequireAuthMiddleware(
                        sse_transport.handle_post_message,
                        required_scopes),
                ))
        else:
            async def combined_endpoint(request: Request) -> Response:
                return await dispatch_endpoint(request)

            routes.append(
                Route(
                    self.settings.sse_path,
                    endpoint=combined_endpoint,
                    methods=[
                        "GET",
                        "POST"]))
            routes.append(
                Mount(
                    self.settings.message_path,
                    app=sse_transport.handle_post_message))

        routes.extend(getattr(self, "_custom_starlette_routes", []))

        return Starlette(
            debug=self.settings.debug,
            routes=routes,
            middleware=middleware)  # type: ignore[name-defined]

    FastMCP.sse_app = patched_sse_app  # type: ignore[assignment]
    setattr(FastMCP, "_original_sse_app", original_sse_app)
    _PATCH_SSE_ALIAS_APPLIED = True


__all__ = [
    "ensure_streamable_http_accept_patch",
    "ensure_streamable_http_server_patch",
    "ensure_streamable_http_instructions_patch",
    "ensure_sse_post_alias_patch",
    "set_streamable_http_instructions",
]
