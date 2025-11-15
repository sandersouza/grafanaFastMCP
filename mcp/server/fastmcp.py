"""Minimal FastMCP shim with basic STDIO support for Python 3.9 runtimes."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import sys
from collections.abc import Mapping as ABCMapping, Sequence as ABCSequence
from dataclasses import dataclass, field
from types import SimpleNamespace
try:  # pragma: no cover - Python < 3.10 fallback
    from types import UnionType  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - Python 3.9 compatibility
    UnionType = None  # type: ignore[assignment]
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    get_args,
    get_origin,
    get_type_hints,
)


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
    parameters: Dict[str, Any]
    function: Callable[..., Awaitable[Any]]
    signature: inspect.Signature = field(repr=False)


def _annotation_to_schema(annotation: Any) -> Dict[str, Any]:
    """Convert a Python annotation into a JSON-schema-ish mapping."""

    if annotation is inspect._empty or annotation is Any:
        return {}

    if isinstance(annotation, str):
        normalized = annotation.strip()
        if normalized.startswith("typing."):
            normalized = normalized[len("typing."):]
        if normalized.endswith(" | None"):
            normalized = normalized[: -len(" | None")]
            return _annotation_to_schema(normalized)
        if normalized.startswith("Optional[") and normalized.endswith("]"):
            inner = normalized[len("Optional["): -1]
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
        if lower.startswith(("list[", "sequence[")):
            open_bracket = normalized.find("[")
            close_bracket = normalized.rfind("]")
            item_annotation: Optional[str] = None
            if open_bracket != -1 and close_bracket != - \
                    1 and close_bracket > open_bracket + 1:
                item_annotation = normalized[open_bracket + 1: close_bracket]
            items_schema = _annotation_to_schema(
                item_annotation) if item_annotation else {}
            return {"type": "array", "items": items_schema or {}}
        if lower in {"list", "sequence"}:
            return {"type": "array", "items": {}}
        if lower.startswith(("dict[", "dict", "mapping[", "mapping")):
            return {"type": "object"}
        return {}

    origin = get_origin(annotation)
    args = get_args(annotation)

    union_origin = getattr(__import__("typing"), "Union", None)
    union_types = {union_origin}
    if UnionType is not None:
        union_types.add(UnionType)

    if origin in union_types:
        non_none = [arg for arg in args if arg is not type(None)]  # noqa: E721
        schemas = [
            schema for schema in (
                _annotation_to_schema(arg) or {} for arg in non_none) if schema]
        if not schemas:
            return {}
        if len(non_none) == 1:
            return schemas[0]
        return {"anyOf": schemas}

    if annotation in {str, "".__class__}:
        return {"type": "string"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int or (origin is int and not args):
        return {"type": "integer"}
    if annotation is float or (origin is float and not args):
        return {"type": "number"}
    array_origins: Tuple[Any, ...] = (list, List, Sequence, ABCSequence)
    if annotation in array_origins or origin in array_origins:
        item_schema: Dict[str, Any] = {}
        if args:
            if len(args) == 1:
                item_schema = _annotation_to_schema(args[0]) or {}
            else:
                item_schema = {
                    "anyOf": [
                        schema for schema in (
                            _annotation_to_schema(arg) or {} for arg in args) if schema]}
                if not item_schema["anyOf"]:
                    item_schema = {}
        return {"type": "array", "items": item_schema or {}}
    mapping_origins: Tuple[Any, ...] = (dict, Dict, Mapping, ABCMapping)
    if annotation in mapping_origins or origin in mapping_origins:
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
        self._logger = logging.getLogger(__name__)

    # Decorator --------------------------------------------------------------
    def tool(
        self,
        *,
        name: str,
        title: str,
        description: str,
    ) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
        """Register a tool function with metadata and inferred schema."""

        def decorator(func: Callable[..., Awaitable[Any]]
                      ) -> Callable[..., Awaitable[Any]]:
            schema = self._normalize_schema(self._build_schema(func))
            tool_def = ToolDefinition(
                name=name,
                title=title,
                description=description,
                inputSchema=schema,
                parameters=schema,
                function=func,
                signature=inspect.signature(func),
            )
            self._tools.append(tool_def)
            return func

        return decorator

    # Discovery --------------------------------------------------------------
    async def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools)

    # Execution --------------------------------------------------------------
    def run(self, transport: str, *, mount_path: Optional[str] = None) -> None:
        self._run_calls.append((transport, mount_path))
        if transport == "stdio":
            self._run_stdio()

    # Utilities --------------------------------------------------------------
    def streamable_http_app(self) -> "FastMCP":
        return self

    async def run_streamable_http_async(self) -> None:  # pragma: no cover - patched in tests
        raise RuntimeError("Streamable HTTP transport not implemented in stub")

    # Internal helpers -------------------------------------------------------
    def _run_stdio(self) -> None:
        session = _STDIOHandler(self)
        session.run()

    # Schema generation ------------------------------------------------------
    def _build_schema(
            self, func: Callable[..., Awaitable[Any]]) -> Dict[str, Any]:
        signature = inspect.signature(func)
        try:
            type_hints = get_type_hints(func, include_extras=True)
        except Exception:  # pragma: no cover - defensive fallback
            type_hints = {}
        properties: Dict[str, Dict[str, Any]] = {}
        required: List[str] = []

        for name, param in signature.parameters.items():
            if name == "ctx":
                continue
            if param.kind in {
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD}:
                continue

            annotation = type_hints.get(name, param.annotation)
            schema = _annotation_to_schema(annotation)
            if param.kind is inspect.Parameter.KEYWORD_ONLY and not schema:
                schema = {}
            properties[name] = schema

            if param.default is inspect._empty and param.kind is not inspect.Parameter.VAR_KEYWORD:
                required.append(name)

        schema: Dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema

    def _normalize_schema(self, schema: Any) -> Dict[str, Any]:
        """Ensure schemas used for tool parameters are always valid objects."""

        def fallback_items_schema() -> Dict[str, Any]:
            # Important: do NOT include "array" here because some validators
            # require any schema with type=="array" to also define an "items"
            # schema. Since this is a generic fallback used for array items, we
            # avoid producing nested array schemas without explicit items.
            return {
                "type": [
                    "boolean",
                    "integer",
                    "number",
                    "string",
                    "object",
                    "null"],
            }

        def normalize(node: Any) -> Dict[str, Any]:
            if not isinstance(node, dict):
                return {"type": "object", "properties": {}}

            normalized: Dict[str, Any] = dict(node)
            schema_type = normalized.get("type")

            if isinstance(schema_type, list):
                if "array" in schema_type:
                    items = normalized.get("items")
                    if isinstance(items, list):
                        normalized["items"] = [
                            normalize(item) for item in items] or fallback_items_schema()
                    elif isinstance(items, dict):
                        normalized["items"] = normalize(items)
                    else:
                        normalized["items"] = fallback_items_schema()
            elif schema_type == "array":
                items = normalized.get("items")
                if isinstance(items, list):
                    normalized["items"] = [
                        normalize(item) for item in items] or fallback_items_schema()
                elif isinstance(items, dict):
                    normalized["items"] = normalize(items)
                else:
                    normalized["items"] = fallback_items_schema()
            elif schema_type == "object":
                properties = normalized.get("properties")
                if isinstance(properties, dict):
                    normalized["properties"] = {
                        key: normalize(value) for key,
                        value in properties.items()}
                else:
                    normalized["properties"] = {}
            else:
                if not isinstance(schema_type, str):
                    normalized["type"] = "object"
                    normalized.setdefault("properties", {})

            for key in ("anyOf", "oneOf", "allOf"):
                options = normalized.get(key)
                if isinstance(options, list):
                    normalized[key] = [
                        normalize(option) for option in options if isinstance(
                            option, dict)]

            required = normalized.get("required")
            if required is not None:
                if isinstance(required, list):
                    filtered = [
                        name for name in required if isinstance(
                            name, str)]
                    if filtered:
                        normalized["required"] = filtered
                    else:
                        normalized.pop("required", None)
                else:
                    normalized.pop("required", None)

            return normalized

        return normalize(schema)


__all__ = ["Context", "FastMCP", "ToolDefinition"]


# ---------------------------------------------------------------------------
# STDIO implementation (best-effort, not full MCP compatibility)

MCP_PROTOCOL_VERSION = "2025-06-18"


class _STDIOHandler:
    """Lightweight STDIO transport for the Python 3.9 shim."""

    def __init__(self, app: FastMCP) -> None:
        self._app = app
        self._logger = logging.getLogger("mcp.stdio")
        self._tool_map: Dict[str, ToolDefinition] = {
            tool.name: tool for tool in app._tools}
        self._context = Context(
            request_context=SimpleNamespace(
                session=SimpleNamespace()))
        self._initialized = False

    # Public API -------------------------------------------------------------
    def run(self) -> None:
        stdin = sys.stdin
        for raw_line in stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                self._logger.warning("Failed to parse STDIO message: %s", exc)
                self._write_error(None, -32700, f"Parse error: {exc}")
                continue

            try:
                response = self._handle_message(message)
                if response is not None:
                    self._write_response(response)
            except SystemExit:
                raise
            except Exception as err:  # pragma: no cover - defensive
                self._logger.error(
                    "Unhandled STDIO error: %s", err, exc_info=True)
                if isinstance(message, dict) and "id" in message:
                    self._write_error(message.get("id"), -32603, str(err))

    # Message handling -------------------------------------------------------
    def _handle_message(
            self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(message, dict):
            return None

        if "method" not in message:
            return None

        if "id" not in message:
            self._handle_notification(message)
            return None

        return self._handle_request(message)

    def _handle_notification(self, message: Dict[str, Any]) -> None:
        method = message.get("method")
        if method == "logging/setLevel":
            params = message.get("params") or {}
            level = params.get("level")
            if isinstance(level, str):
                try:
                    logging.getLogger().setLevel(level.upper())
                except Exception:  # pragma: no cover - defensive
                    self._logger.debug(
                        "Failed to set log level to %s", level, exc_info=True)
        # Other notifications are currently ignored.

    def _handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}

        try:
            if method == "initialize":
                result = self._handle_initialize(params)
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = self._handle_tools_list(params)
            elif method == "tools/call":
                result = self._handle_tools_call(params)
            elif method == "logging/setLevel":
                self._handle_notification(message)
                result = {}
            else:
                return self._error_response(
                    request_id, -32601, f"Method '{method}' not implemented")
        except _JSONRPCError as exc:
            return self._error_response(
                request_id, exc.code, exc.message, exc.data)
        except Exception as err:  # pragma: no cover - defensive
            self._logger.error("STDIO request failed: %s", err, exc_info=True)
            return self._error_response(request_id, -32603, str(err))

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    # Individual request handlers --------------------------------------------
    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        protocol = params.get("protocolVersion") or MCP_PROTOCOL_VERSION
        self._initialized = True
        capabilities = {
            "tools": {"listChanged": False},
        }
        if self._app.debug:
            capabilities["logging"] = {}

        instructions = self._app.instructions if isinstance(
            self._app.instructions, str) else None
        try:
            from app import __version__ as app_version  # type: ignore
        except Exception:  # pragma: no cover - defensive
            app_version = "unknown"

        server_info = {
            "name": self._app.name or "FastMCP",
            "version": app_version,
        }

        return {
            "protocolVersion": protocol,
            "capabilities": capabilities,
            "serverInfo": server_info,
            "instructions": instructions,
        }

    def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            raise _JSONRPCError(-32600, "Server not initialized")

        tools_payload = []
        for tool in self._app._tools:
            entry = {
                "name": tool.name,
                "title": tool.title,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
                "parameters": tool.parameters,
            }
            annotations = {}
            if tool.title:
                annotations["title"] = tool.title
            if annotations:
                entry["annotations"] = annotations
            tools_payload.append(entry)

        return {"tools": tools_payload}

    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            raise _JSONRPCError(-32600, "Server not initialized")

        name = params.get("name")
        if not isinstance(name, str):
            raise _JSONRPCError(-32602, "Tool name must be a string")

        tool = self._tool_map.get(name)
        if tool is None:
            raise _JSONRPCError(-32601, f"Tool '{name}' not found")

        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise _JSONRPCError(-32602, "Tool arguments must be an object")

        bound_arguments = self._prepare_tool_arguments(tool, arguments)
        result = asyncio.run(self._invoke_tool(tool, bound_arguments))
        content, structured = self._format_tool_result(result)

        response: Dict[str, Any] = {
            "content": content,
            "isError": False,
        }
        if structured is not None:
            response["structuredContent"] = structured
        return response

    # Tool helpers -----------------------------------------------------------
    def _prepare_tool_arguments(
            self, tool: ToolDefinition, arguments: Dict[str, Any]) -> Dict[str, Any]:
        signature = tool.signature
        prepared: Dict[str, Any] = {}

        for name, parameter in signature.parameters.items():
            if name == "ctx":
                continue

            if parameter.kind in {
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD}:
                continue

            if name in arguments:
                prepared[name] = arguments[name]
            elif parameter.default is inspect._empty:
                raise _JSONRPCError(-32602,
                                    f"Missing required argument: {name}")

        # Include any unexpected arguments that the tool can accept via
        # **kwargs.
        has_var_kwargs = any(
            param.kind is inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())
        if has_var_kwargs:
            for key, value in arguments.items():
                if key not in prepared and key != "ctx":
                    prepared[key] = value

        return prepared

    async def _invoke_tool(self, tool: ToolDefinition,
                           arguments: Dict[str, Any]) -> Any:
        kwargs = dict(arguments)
        if "ctx" in tool.signature.parameters:
            kwargs["ctx"] = self._context
        return await tool.function(**kwargs)  # type: ignore[arg-type]

    def _format_tool_result(
            self, result: Any) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        structured: Optional[Dict[str, Any]] = None
        if isinstance(result, dict):
            structured = result

        if isinstance(result, str):
            text_output = result
        else:
            try:
                text_output = json.dumps(result, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                text_output = str(result)

        content_block = {"type": "text", "text": text_output}
        return [content_block], structured

    # Response helpers -------------------------------------------------------
    def _write_response(self, response: Dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def _write_error(
            self,
            request_id: Any,
            code: int,
            message: str,
            data: Optional[Any] = None) -> None:
        sys.stdout.write(
            json.dumps(
                self._error_response(
                    request_id,
                    code,
                    message,
                    data),
                ensure_ascii=False) +
            "\n")
        sys.stdout.flush()

    def _error_response(self,
                        request_id: Any,
                        code: int,
                        message: str,
                        data: Optional[Any] = None) -> Dict[str,
                                                            Any]:
        error: Dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": "2.0", "id": request_id, "error": error}


class _JSONRPCError(RuntimeError):
    def __init__(
            self,
            code: int,
            message: str,
            data: Optional[Any] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data
