"""Minimal stub of the FastMCP server used by the tests.

This is not a full implementation of the real package, but it is sufficient to
exercise the surrounding application logic under Python 3.9 where the real
package is unavailable.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Dict, List, Optional, get_args, get_origin


@dataclass
class Context:
    """Very small stand-in for the real MCP request context."""

    request_context: SimpleNamespace


@dataclass
class ToolDefinition:
    """Represents a registered tool with metadata for discovery."""

    name: str
    title: str
    description: str
    inputSchema: Dict[str, Any]
    function: Callable[..., Awaitable[Any]]


def _annotation_to_schema(annotation: Any) -> Dict[str, Any]:
    """Convert a Python annotation into a JSON-schema-ish mapping."""

    if annotation is inspect._empty or annotation is Any:
        return {}

    if isinstance(annotation, str):
        normalized = annotation.strip()
        if normalized.startswith("typing."):
            normalized = normalized[len("typing.") :]
        if normalized.endswith(" | None"):
            normalized = normalized[: -len(" | None")]
            return _annotation_to_schema(normalized)
        if normalized.startswith("Optional[") and normalized.endswith("]"):
            inner = normalized[len("Optional[") : -1]
            return _annotation_to_schema(inner)
        lower = normalized.lower()
        if lower in {"str", "string"}:
            return {"type": "string"}
        if lower in {"int", "integer"}:
            return {"type": "integer"}
        if lower in {"bool", "boolean"}:
            return {"type": "boolean"}
        if lower in {"float", "double"}:
            return {"type": "number"}
        if lower.startswith(("list[", "list", "sequence[", "sequence")):
            return {"type": "array"}
        if lower.startswith(("dict[", "dict", "mapping[", "mapping")):
            return {"type": "object"}
        return {}

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Optional:  # pragma: no cover - Optional is simply an alias for Union
        origin = get_origin(args[0]) if args else None

    # typing.Optional resolves to typing.Union[..., NoneType]
    if origin is getattr(__import__("typing"), "Union", None) and type(None) in args:
        non_none = [arg for arg in args if arg is not type(None)]  # noqa: E721
        if len(non_none) == 1:
            return _annotation_to_schema(non_none[0])

    if annotation in {str, "".__class__}:
        return {"type": "string"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int or (origin is int and not args):
        return {"type": "integer"}
    if annotation is float or (origin is float and not args):
        return {"type": "number"}
    if annotation in {list, List} or origin in {list, List}:
        return {"type": "array"}
    if annotation in {dict, Dict} or origin in {dict, Dict}:
        return {"type": "object"}

    return {}


class FastMCP:
    """Tiny FastMCP façade for registering tools and listing them in tests."""

    def __init__(
        self,
        *,
        name: str = "",
        instructions: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        mount_path: str = "/",
        sse_path: str = "/sse",
        message_path: str = "/messages/",
        streamable_http_path: str = "/mcp",
        log_level: str = "INFO",
        debug: bool = False,
    ) -> None:
        self.name = name
        self.instructions = instructions
        self.debug = debug
        self._tools: List[ToolDefinition] = []
        self._run_calls: List[tuple[str, Optional[str]]] = []
        self.settings = SimpleNamespace(
            host=host,
            port=port,
            log_level=log_level,
            mount_path=mount_path,
            sse_path=sse_path,
            message_path=message_path,
            streamable_http_path=streamable_http_path,
        )

    # Decorator -----------------------------------------------------------------
    def tool(
        self,
        *,
        name: str,
        title: str,
        description: str,
    ) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
        """Register a tool function with metadata and inferred schema."""

        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
            schema = self._build_schema(func)
            tool_def = ToolDefinition(
                name=name,
                title=title,
                description=description,
                inputSchema=schema,
                function=func,
            )
            self._tools.append(tool_def)
            return func

        return decorator

    # Discovery -----------------------------------------------------------------
    async def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools)

    # Execution -----------------------------------------------------------------
    def run(self, transport: str, *, mount_path: Optional[str] = None) -> None:
        self._run_calls.append((transport, mount_path))

    # Utilities -----------------------------------------------------------------
    def streamable_http_app(self) -> "FastMCP":
        return self

    async def run_streamable_http_async(self) -> None:  # pragma: no cover - patched in tests
        raise RuntimeError("Streamable HTTP transport not implemented in stub")

    # Schema generation ----------------------------------------------------------
    def _build_schema(self, func: Callable[..., Awaitable[Any]]) -> Dict[str, Any]:
        signature = inspect.signature(func)
        properties: Dict[str, Dict[str, Any]] = {}
        required: List[str] = []

        for name, param in signature.parameters.items():
            if name == "ctx":
                continue
            if param.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
                continue

            schema = _annotation_to_schema(param.annotation)
            if param.kind is inspect.Parameter.KEYWORD_ONLY and not schema:
                schema = {}
            properties[name] = schema

            if param.default is inspect._empty and param.kind is not inspect.Parameter.VAR_KEYWORD:
                required.append(name)

        schema: Dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema


__all__ = ["Context", "FastMCP", "ToolDefinition"]
