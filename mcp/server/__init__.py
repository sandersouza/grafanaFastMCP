"""Stub server package exposing the minimal FastMCP API surface for tests."""

from .fastmcp import Context, FastMCP
from .streamable_http import (
    CONTENT_TYPE_JSON,
    CONTENT_TYPE_SSE,
    StreamableHTTPServerTransport,
)

__all__ = [
    "Context",
    "FastMCP",
    "CONTENT_TYPE_JSON",
    "CONTENT_TYPE_SSE",
    "StreamableHTTPServerTransport",
]
