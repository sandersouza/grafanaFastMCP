"""Tests for the relaxed StreamableHTTP Accept header validation."""

from __future__ import annotations

from starlette.requests import Request

from app.patches import ensure_streamable_http_accept_patch
from mcp.server.streamable_http import StreamableHTTPServerTransport


def _make_request(accept_header: str | None) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/mcp",
        "raw_path": b"/mcp",
        "root_path": "",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 1234),
        "server": ("testserver", 80),
    }

    if accept_header is not None:
        scope["headers"].append((b"accept", accept_header.encode("latin-1")))

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


def test_event_stream_only_accept_header_is_allowed() -> None:
    ensure_streamable_http_accept_patch()
    transport = StreamableHTTPServerTransport(mcp_session_id="abc123")

    request = _make_request("text/event-stream")
    has_json, has_sse = transport._check_accept_headers(request)

    assert has_sse is True
    assert has_json is True


def test_wildcard_accept_header_is_allowed() -> None:
    ensure_streamable_http_accept_patch()
    transport = StreamableHTTPServerTransport(mcp_session_id="abc123")

    request = _make_request("*/*")
    has_json, has_sse = transport._check_accept_headers(request)

    assert has_sse is True
    assert has_json is True


def test_missing_event_stream_is_detected() -> None:
    ensure_streamable_http_accept_patch()
    transport = StreamableHTTPServerTransport(mcp_session_id="abc123")

    request = _make_request("application/json")
    has_json, has_sse = transport._check_accept_headers(request)

    assert has_json is True
    assert has_sse is False
