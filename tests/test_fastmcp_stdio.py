"""Tests for the lightweight STDIO FastMCP shim."""

from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import Context, FastMCP, _STDIOHandler


def _initialize(handler: _STDIOHandler) -> Dict[str, Any]:
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1"},
        },
    }
    response = handler._handle_request(request)
    assert "result" in response
    return response


def test_stdio_initialize_sets_capabilities() -> None:
    app = FastMCP(name="mcp-grafana", instructions="hello")
    handler = _STDIOHandler(app)

    response = _initialize(handler)
    result = response["result"]

    assert result["protocolVersion"] == "2025-06-18"
    assert result["capabilities"] == {"tools": {"listChanged": False}}
    assert result["serverInfo"]["name"] == "mcp-grafana"
    assert result["instructions"] == "hello"


def test_stdio_list_tools_returns_registered_tool() -> None:
    app = FastMCP(name="mcp-grafana", instructions=None)

    @app.tool(name="echo", title="Echo", description="Echoes input")
    async def echo(
            message: str, ctx: Optional[Context] = None) -> Dict[str, str]:
        return {"message": message}

    handler = _STDIOHandler(app)
    _initialize(handler)

    response = handler._handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    })

    tools = response["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "echo"
    assert tools[0]["inputSchema"]["type"] == "object"
    assert tools[0]["parameters"]["type"] == "object"
    assert tools[0]["parameters"] == tools[0]["inputSchema"]


def test_stdio_list_tools_includes_empty_parameters_for_no_argument_tool() -> None:
    app = FastMCP(name="mcp-grafana", instructions=None)

    @app.tool(name="noop", title="Noop", description="No arguments")
    async def noop() -> Dict[str, str]:
        return {"result": "ok"}

    handler = _STDIOHandler(app)
    _initialize(handler)

    response = handler._handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/list",
        "params": {},
    })

    tool = response["result"]["tools"][0]
    assert tool["parameters"]["type"] == "object"
    assert tool["parameters"].get("properties") == {}


def test_stdio_call_tool_invokes_async_function() -> None:
    app = FastMCP(name="mcp-grafana", instructions=None)

    @app.tool(name="uppercase", title="Upper", description="Uppercase text")
    async def uppercase(
            value: str, ctx: Optional[Context] = None) -> Dict[str, str]:
        return {"result": value.upper()}

    handler = _STDIOHandler(app)
    _initialize(handler)

    response = handler._handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "uppercase", "arguments": {"value": "grafana"}},
    })

    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"] == {"result": "GRAFANA"}
    assert any(block["text"].find("GRAFANA") >=
               0 for block in result["content"])


def test_stdio_call_tool_missing_argument_raises_error() -> None:
    app = FastMCP(name="test", instructions=None)

    @app.tool(name="req", title="Req", description="Needs param")
    async def req(param: str) -> Dict[str, str]:
        return {"param": param}

    handler = _STDIOHandler(app)
    _initialize(handler)

    response = handler._handle_request({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "req", "arguments": {}},
    })

    assert response["error"]["code"] == -32602
