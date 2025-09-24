"""Tests for the Grafana FastMCP server factory."""

from __future__ import annotations

from types import SimpleNamespace

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
    assert server._normalize_streamable_http_path(value, mount_path, default_segment) == expected


def test_create_app_configures_fastmcp(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"accept": 0, "server": 0}

    def _increment_accept() -> None:
        calls["accept"] += 1

    def _increment_server() -> None:
        calls["server"] += 1

    monkeypatch.setattr(server, "ensure_streamable_http_accept_patch", _increment_accept)
    monkeypatch.setattr(server, "ensure_streamable_http_server_patch", _increment_server)

    instructions = object()
    monkeypatch.setattr(server, "load_instructions", lambda: instructions)

    registered: list[object] = []
    monkeypatch.setattr(server, "register_all", lambda app: registered.append(app))

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
