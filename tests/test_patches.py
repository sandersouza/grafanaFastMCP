"""Tests for compatibility patches applied to upstream MCP components."""

from __future__ import annotations

import builtins
import sys
from contextlib import asynccontextmanager
from types import ModuleType, SimpleNamespace

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route
from starlette.testclient import TestClient

from app import patches


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_normalize_media_types_parses_values() -> None:
    result = patches._normalize_media_types("text/html; q=0.8, application/json, */* , application/*;version=1")
    assert result == ["text/html", "application/json", "*/*", "application/*"]


def test_ensure_streamable_http_accept_patch_relaxes_requirements(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyTransport:
        def _check_accept_headers(self, request: SimpleNamespace) -> tuple[bool, bool]:
            raise AssertionError("Original accept check should be replaced")

    monkeypatch.setattr(patches, "StreamableHTTPServerTransport", DummyTransport)
    monkeypatch.setattr(patches, "_PATCH_ACCEPT_APPLIED", False)

    patches.ensure_streamable_http_accept_patch()

    patched = DummyTransport._check_accept_headers
    assert hasattr(DummyTransport, "_original_check_accept_headers")

    request = SimpleNamespace(headers={"accept": "text/event-stream"})
    assert patched(DummyTransport(), request) == (True, True)

    json_only = SimpleNamespace(headers={"accept": "application/json"})
    assert patched(DummyTransport(), json_only) == (True, False)

    wildcard = SimpleNamespace(headers={"accept": "*/*"})
    assert patched(DummyTransport(), wildcard) == (True, True)

    empty = SimpleNamespace(headers={"accept": "  "})
    assert patched(DummyTransport(), empty) == (True, True)

    patches.ensure_streamable_http_accept_patch()
    assert DummyTransport._check_accept_headers is patched


@pytest.mark.anyio("asyncio")
async def test_ensure_streamable_http_server_patch_overrides_run(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyFastMCP:
        def __init__(self) -> None:
            self.settings = SimpleNamespace(host="localhost", port=8080, log_level="INFO")

        def streamable_http_app(self) -> str:
            return "app"

    async def original_run(self) -> None:
        raise AssertionError("Original implementation should be wrapped")

    DummyFastMCP.run_streamable_http_async = original_run

    monkeypatch.setattr(patches, "FastMCP", DummyFastMCP)
    monkeypatch.setattr(patches, "_PATCH_STREAMABLE_SERVER_APPLIED", False)

    records: dict[str, object] = {}

    class DummyConfig:
        def __init__(
            self,
            app: object,
            *,
            host: str,
            port: int,
            log_level: str,
            timeout_keep_alive: float,
            timeout_notify: float,
            timeout_graceful_shutdown: float,
        ) -> None:
            records["config"] = {
                "app": app,
                "host": host,
                "port": port,
                "log_level": log_level,
                "keep_alive": timeout_keep_alive,
                "notify": timeout_notify,
                "graceful": timeout_graceful_shutdown,
            }

    class DummyServer:
        def __init__(self, config: DummyConfig) -> None:
            records["server_config"] = config

        async def serve(self) -> None:
            records["served"] = True

    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(Config=DummyConfig, Server=DummyServer))

    patches.ensure_streamable_http_server_patch()

    instance = DummyFastMCP()

    monkeypatch.setenv("MCP_STREAMABLE_HTTP_TIMEOUT_KEEP_ALIVE", "70")
    monkeypatch.setenv("MCP_STREAMABLE_HTTP_TIMEOUT_NOTIFY", "150")
    monkeypatch.setenv("MCP_STREAMABLE_HTTP_TIMEOUT_GRACEFUL_SHUTDOWN", "200")

    await instance.run_streamable_http_async()

    assert isinstance(records["server_config"], DummyConfig)
    assert records["config"]["keep_alive"] == 70.0
    assert records["config"]["notify"] == 150.0
    assert records["config"]["graceful"] == 200.0
    assert records["config"]["log_level"] == "info"
    assert records["served"] is True
    assert DummyFastMCP._original_run_streamable_http_async is original_run

    patches.ensure_streamable_http_server_patch()
    assert DummyFastMCP.run_streamable_http_async is not original_run


def test_ensure_sse_post_alias_patch_skips_when_fastmcp_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(patches, "_PATCH_SSE_ALIAS_APPLIED", False)
    monkeypatch.delitem(sys.modules, "mcp.server.fastmcp.server", raising=False)

    patches.ensure_sse_post_alias_patch()

    assert patches._PATCH_SSE_ALIAS_APPLIED is False


def test_ensure_sse_post_alias_patch_idempotent_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(patches, "_PATCH_SSE_ALIAS_APPLIED", True)

    patches.ensure_sse_post_alias_patch()

    assert patches._PATCH_SSE_ALIAS_APPLIED is True


def test_set_streamable_http_instructions_assigns_attribute(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyTransport:
        pass

    monkeypatch.setattr(patches, "StreamableHTTPServerTransport", DummyTransport)
    patches.set_streamable_http_instructions("  example ")

    assert getattr(DummyTransport, "_fastmcp_preprompt_text") == "example"
    assert patches._STREAMABLE_HTTP_INSTRUCTIONS == "example"


def test_ensure_streamable_http_instructions_patch_noop_without_method(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyTransport:
        pass

    monkeypatch.setattr(patches, "StreamableHTTPServerTransport", DummyTransport)
    monkeypatch.setattr(patches, "_PATCH_STREAMABLE_INSTRUCTIONS_APPLIED", False)

    patches.ensure_streamable_http_instructions_patch()

    assert patches._PATCH_STREAMABLE_INSTRUCTIONS_APPLIED is False
