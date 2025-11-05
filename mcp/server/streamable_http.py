"""Minimal stub of the streamable HTTP transport used in tests."""

from __future__ import annotations

from typing import Optional, Tuple

CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_SSE = "text/event-stream"


class StreamableHTTPServerTransport:
    """Placeholder transport exposing the hook patched during tests."""

    def __init__(self, *, mcp_session_id: Optional[str] = None) -> None:
        self.mcp_session_id = mcp_session_id or ""

    def _check_accept_headers(self, request) -> Tuple[bool, bool]:  # pragma: no cover - overwritten in tests
        accept = getattr(request, "headers", {}).get("accept", "")
        accept = (accept or "").strip().lower()
        if not accept:
            return True, True
        has_json = CONTENT_TYPE_JSON in accept
        has_sse = CONTENT_TYPE_SSE in accept
        return has_json or has_sse, has_sse


__all__ = [
    "StreamableHTTPServerTransport",
    "CONTENT_TYPE_JSON",
    "CONTENT_TYPE_SSE"]
