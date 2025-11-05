"""Tests for the Grafana FastMCP server factory."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from app import server


@pytest.mark.parametrize(
    "value, expected",
    [
        ("", "/"),
        ("/", "/"),
        ("api", "/api"),
        ("/api/", "/api"),
    ],
)
def test_normalize_mount_path(value: str, expected: str) -> None:
    assert server._normalize_mount_path(value) == expected


@pytest.mark.parametrize(
    "base, segment, expected",
    [
        ("/", "", "/"),
        ("/", "stream", "/stream"),
        ("/api", "messages", "/api/messages"),
        ("/api/", "/nested/", "/api/nested"),
        ("", "relative", "/relative"),
    ],
)
def test_join_path(base: str, segment: str, expected: str) -> None:
    assert server._join_path(base, segment) == expected


@pytest.mark.parametrize(
    "value, mount_path, default_segment, expected",
    [
        ("", "/", "mcp", "/mcp"),
        ("/absolute", "/ignored", "mcp", "/absolute"),
        ("relative", "/base", "mcp", "/base/relative"),
        ("relative/", "/base", "mcp", "/base/relative"),
    ],
)
def test_normalize_streamable_http_path(
    value: str, mount_path: str, default_segment: str, expected: str
) -> None:
    assert server._normalize_streamable_http_path(
        value, mount_path, default_segment) == expected


def test_create_app_configures_fastmcp(
        monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"accept": 0, "server": 0}

    def _increment_accept() -> None:
        calls["accept"] += 1

    def _increment_server() -> None:
        calls["server"] += 1

    monkeypatch.setattr(
        server,
        "ensure_streamable_http_accept_patch",
        _increment_accept)
    monkeypatch.setattr(
        server,
        "ensure_streamable_http_server_patch",
        _increment_server)

    instructions = object()
    monkeypatch.setattr(server, "load_instructions", lambda: instructions)

    registered: list[object] = []
    monkeypatch.setattr(
        server,
        "register_all",
        lambda app: registered.append(app))

    class DummyFastMCP:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            self.settings = SimpleNamespace(
                host=kwargs["host"],
                port=kwargs["port"],
                log_level=kwargs["log_level"],
                mount_path=kwargs["mount_path"],
                sse_path=kwargs["sse_path"],
                message_path=kwargs["message_path"],
                streamable_http_path=kwargs["streamable_http_path"],
            )

        def streamable_http_app(self) -> str:
            return "dummy-app"

    monkeypatch.setattr(server, "FastMCP", DummyFastMCP)

    app = server.create_app(
        host="127.0.0.1",
        port=9000,
        base_path="api/v1/",
        streamable_http_path="stream",
        log_level="debug",
        debug=True,
    )

    assert isinstance(app, DummyFastMCP)
    assert calls == {"accept": 1, "server": 1}
    assert registered == [app]

    assert app.kwargs["instructions"] is instructions
    assert app.kwargs["name"] == "mcp-grafana"
    assert app.kwargs["sse_path"] == "/api/v1/sse"
    assert app.kwargs["message_path"] == "/api/v1/messages/"
    assert app.kwargs["streamable_http_path"] == "/api/v1/stream"
    assert app.kwargs["log_level"] == "DEBUG"


def test_register_streamable_http_alias_ignores_missing_routes() -> None:
    class DummyFastMCP:
        pass

    server._register_streamable_http_alias(
        DummyFastMCP())  # type: ignore[arg-type]


def test_register_streamable_http_alias_adds_route(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    alias_calls: list[str] = []

    class DummyStreamableHTTPASGIApp:
        def __init__(self, session_manager: object) -> None:
            self.session_manager = session_manager

        # type: ignore[no-untyped-def]
        async def __call__(self, scope, receive, send) -> None:
            alias_calls.append(scope["path"])
            response = PlainTextResponse("alias-handled")
            await response(scope, receive, send)

    module = ModuleType("mcp.server.fastmcp.server")
    module.StreamableHTTPASGIApp = DummyStreamableHTTPASGIApp
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp.server", module)

    class DummyFastMCP:
        def __init__(self) -> None:
            self.settings = SimpleNamespace(streamable_http_path="/mcp")
            self._session_manager = object()
            self._custom_starlette_routes: list[Route] = []

        def streamable_http_app(self) -> None:
            return None

    dummy = DummyFastMCP()
    server._register_streamable_http_alias(dummy)
    assert len(dummy._custom_starlette_routes) == 1

    alias_route = dummy._custom_starlette_routes[0]
    assert alias_route.path == "/{prefix}/link_{link_id}/{rest:path}"
    assert alias_route.methods == {"DELETE", "GET", "HEAD", "POST"}

    base_calls: list[str] = []

    # type: ignore[no-untyped-def]
    async def base_endpoint(scope, receive, send) -> None:
        base_calls.append(scope["path"])
        response = PlainTextResponse("base")
        await response(scope, receive, send)

    app = Starlette(
        routes=[
            Route(
                "/mcp",
                endpoint=base_endpoint,
                methods=["POST"]),
            alias_route])
    client = TestClient(app)

    response = client.post("/Grafana/link_123/update_dashboard")
    assert response.status_code == 200
    assert response.text == "alias-handled"
    assert alias_calls == ["/mcp"]
    assert base_calls == []

    server._register_streamable_http_alias(dummy)
    assert len(dummy._custom_starlette_routes) == 1
