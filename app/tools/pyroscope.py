"""Pyroscope profiling datasource tools."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaClient


def _parse_rfc3339(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _default_time_range(
        start: Optional[str], end: Optional[str]) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    end_dt = _parse_rfc3339(end) or now
    start_dt = _parse_rfc3339(start) or end_dt - timedelta(hours=1)
    if start_dt >= end_dt:
        raise ValueError("start time must be before end time")
    return start_dt, end_dt


def _matchers(value: Optional[str]) -> str:
    if not value:
        return "{}"
    cleaned = value.strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned
    return f"{{{cleaned}}}"


async def _pyroscope_client(ctx: Context, uid: str) -> GrafanaClient:
    config = get_grafana_config(ctx)
    await GrafanaClient(config).get_json(f"/datasources/uid/{uid}")
    return GrafanaClient(config)


def _proxy_path(uid: str, path: str) -> str:
    prefix = f"/datasources/proxy/uid/{uid}"
    return f"{prefix}{path}"


async def _list_label_names(
    ctx: Context,
    uid: str,
    matchers: Optional[str],
    start: Optional[str],
    end: Optional[str],
) -> List[str]:
    client = await _pyroscope_client(ctx, uid)
    start_dt, end_dt = _default_time_range(start, end)
    params = {
        "match[]": [_matchers(matchers)],
        "start": str(int(start_dt.timestamp() * 1000)),
        "end": str(int(end_dt.timestamp() * 1000)),
    }
    payload = await client.get_json(_proxy_path(uid, "/pyroscope/api/v1/label/names"), params=params)
    if not isinstance(payload, dict):
        raise ValueError("Unexpected response from Pyroscope label names API")
    data = payload.get("data")
    if isinstance(data, list):
        return [str(item) for item in data]
    names = payload.get("names")
    if isinstance(names, list):
        return [str(item) for item in names]
    return []


async def _list_label_values(
    ctx: Context,
    uid: str,
    label: str,
    matchers: Optional[str],
    start: Optional[str],
    end: Optional[str],
) -> List[str]:
    client = await _pyroscope_client(ctx, uid)
    start_dt, end_dt = _default_time_range(start, end)
    params = {
        "match[]": [_matchers(matchers)],
        "start": str(int(start_dt.timestamp() * 1000)),
        "end": str(int(end_dt.timestamp() * 1000)),
    }
    payload = await client.get_json(
        _proxy_path(uid, f"/pyroscope/api/v1/label/{label}/values"), params=params
    )
    if not isinstance(payload, dict):
        raise ValueError("Unexpected response from Pyroscope label values API")
    data = payload.get("data")
    if isinstance(data, list):
        return [str(item) for item in data]
    values = payload.get("values")
    if isinstance(values, list):
        return [str(item) for item in values]
    return []


async def _list_profile_types(
    ctx: Context, uid: str, start: Optional[str], end: Optional[str]
) -> List[str]:
    client = await _pyroscope_client(ctx, uid)
    start_dt, end_dt = _default_time_range(start, end)
    params = {
        "start": str(int(start_dt.timestamp() * 1000)),
        "end": str(int(end_dt.timestamp() * 1000)),
    }
    payload = await client.get_json(
        _proxy_path(uid, "/pyroscope/api/v1/profile_types"), params=params
    )
    if not isinstance(payload, dict):
        raise ValueError(
            "Unexpected response from Pyroscope profile types API")
    types = payload.get("profileTypes") or payload.get("types")
    if isinstance(types, list):
        return [str(item) for item in types]
    return []


async def _fetch_profile(
    ctx: Context,
    uid: str,
    profile_type: str,
    matchers: Optional[str],
    start: Optional[str],
    end: Optional[str],
    max_node_depth: Optional[int],
) -> str:
    client = await _pyroscope_client(ctx, uid)
    start_dt, end_dt = _default_time_range(start, end)
    params = {
        "query": f"{profile_type}{_matchers(matchers)}",
        "from": str(int(start_dt.timestamp() * 1000)),
        "until": str(int(end_dt.timestamp() * 1000)),
        "format": "dot",
    }
    if max_node_depth is not None:
        params["max-nodes"] = str(max_node_depth)
    response = await client.request(
        "GET",
        _proxy_path(uid, "/pyroscope/render"),
        params=params,
    )
    return response.text


def register(app: FastMCP) -> None:
    """Register Pyroscope tools."""

    @app.tool(
        name="list_pyroscope_label_names",
        title="List Pyroscope label names",
        description=(
            "List available label names in a Pyroscope datasource. "
            "Returns a consolidated response object to prevent JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."
        ),
    )
    async def list_pyroscope_label_names(
        dataSourceUid: str,
        matchers: Optional[str] = None,
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_pyroscope_label_names")
        labels = await _list_label_names(ctx, dataSourceUid, matchers, startRfc3339, endRfc3339)
        return {
            "labels": labels,
            "total_count": len(labels),
            "datasource_uid": dataSourceUid,
            "matchers": matchers,
            "start": startRfc3339,
            "end": endRfc3339,
            "type": "pyroscope_label_names_result"
        }

    @app.tool(
        name="list_pyroscope_label_values",
        title="List Pyroscope label values",
        description=(
            "List values for a specific label within a Pyroscope datasource. "
            "Returns a consolidated response object to prevent JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."
        ),
    )
    async def list_pyroscope_label_values(
        dataSourceUid: str,
        name: str,
        matchers: Optional[str] = None,
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_pyroscope_label_values")
        values = await _list_label_values(ctx, dataSourceUid, name, matchers, startRfc3339, endRfc3339)
        return {
            "values": values,
            "total_count": len(values),
            "label_name": name,
            "datasource_uid": dataSourceUid,
            "matchers": matchers,
            "start": startRfc3339,
            "end": endRfc3339,
            "type": "pyroscope_label_values_result"
        }

    @app.tool(
        name="list_pyroscope_profile_types",
        title="List Pyroscope profile types",
        description=(
            "List profile types available in a Pyroscope datasource. "
            "Returns a consolidated response object to prevent JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."
        ),
    )
    async def list_pyroscope_profile_types(
        dataSourceUid: str,
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_pyroscope_profile_types")
        types = await _list_profile_types(ctx, dataSourceUid, startRfc3339, endRfc3339)
        return {
            "profile_types": types,
            "total_count": len(types),
            "datasource_uid": dataSourceUid,
            "start": startRfc3339,
            "end": endRfc3339,
            "type": "pyroscope_profile_types_result"
        }

    @app.tool(
        name="fetch_pyroscope_profile",
        title="Fetch Pyroscope profile",
        description="Fetch a Pyroscope profile in DOT format for a given query.",
    )
    async def fetch_pyroscope_profile(
        dataSourceUid: str,
        profileType: str,
        matchers: Optional[str] = None,
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        maxNodeDepth: Optional[int] = None,
        ctx: Optional[Context] = None,
    ) -> str:
        if ctx is None:
            raise ValueError(
                "Context injection failed for fetch_pyroscope_profile")
        return await _fetch_profile(
            ctx,
            dataSourceUid,
            profileType,
            matchers,
            startRfc3339,
            endRfc3339,
            maxNodeDepth,
        )


__all__ = ["register"]
