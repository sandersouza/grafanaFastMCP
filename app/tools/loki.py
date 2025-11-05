"""Loki datasource tools implemented in Python."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

import httpx

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaClient, USER_AGENT

_DEFAULT_TIMEOUT = httpx.Timeout(30.0)
_MAX_LOG_LIMIT = 100
_DEFAULT_LOG_LIMIT = 10


def _parse_rfc3339(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _time_range(start: Optional[str], end: Optional[str]) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start_dt = _parse_rfc3339(start) if start else now - timedelta(hours=1)
    end_dt = _parse_rfc3339(end) if end else now
    return start_dt.isoformat(), end_dt.isoformat()


def _nanos(value: str) -> str:
    dt = _parse_rfc3339(value)
    return str(int(dt.timestamp() * 1_000_000_000))


class LokiClient:
    """HTTP client for interacting with Loki via Grafana's proxy."""

    def __init__(self, ctx: Context, datasource_uid: str) -> None:
        self._config = get_grafana_config(ctx)
        base = self._config.url.rstrip("/") or ""
        self._base_url = f"{base}/api/datasources/proxy/uid/{datasource_uid}"
        tls = self._config.tls_config
        self._verify = tls.resolve_verify() if tls else True
        self._cert = tls.resolve_cert() if tls else None
        self._auth = httpx.BasicAuth(
            *self._config.basic_auth) if self._config.basic_auth else None
        self._headers = {"User-Agent": USER_AGENT}
        if self._config.api_key:
            self._headers["Authorization"] = f"Bearer {self._config.api_key}"
        if self._config.access_token and self._config.id_token:
            self._headers.setdefault(
                "X-Access-Token", self._config.access_token)
            self._headers.setdefault("X-Grafana-Id", self._config.id_token)

    async def request(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        url = f"{self._base_url}{path}" if path.startswith(
            "/") else f"{self._base_url}/{path}"
        async with httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT,
            verify=self._verify,
            cert=self._cert,
            auth=self._auth,
        ) as client:
            response = await client.get(url, params=params, headers=self._headers)
        if response.status_code >= 400:
            raise ValueError(
                f"Loki API error {response.status_code}: {response.text[:512]}"
            )
        return response

    async def request_json(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Any:
        response = await self.request(path, params=params)
        content = response.text.strip()
        if not content:
            raise ValueError("Empty response from Loki API")
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to parse Loki response: {content[:256]}") from exc


async def _ensure_datasource(ctx: Context, uid: str) -> None:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    await client.get_json(f"/datasources/uid/{uid}")


async def _create_loki_client(ctx: Context, uid: str) -> LokiClient:
    await _ensure_datasource(ctx, uid)
    return LokiClient(ctx, uid)


async def _list_label_items(
    ctx: Context,
    uid: str,
    path: str,
    start: Optional[str],
    end: Optional[str],
) -> List[str]:
    client = await _create_loki_client(ctx, uid)
    params: Dict[str, Any] = {}
    if start or end:
        start_iso, end_iso = _time_range(start, end)
        params["start"] = _nanos(start_iso)
        params["end"] = _nanos(end_iso)
    payload = await client.request_json(path, params=params)
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise ValueError(f"Unexpected Loki response: {payload}")
    data = payload.get("data")
    if data is None:
        return []
    if isinstance(data, list):
        return data
    raise ValueError("Unexpected Loki label response format")


async def _query_range(
    ctx: Context,
    uid: str,
    logql: str,
    start: Optional[str],
    end: Optional[str],
    limit: Optional[int],
    direction: Optional[str],
) -> Any:
    client = await _create_loki_client(ctx, uid)
    start_iso, end_iso = _time_range(start, end)
    params: Dict[str, Any] = {
        "query": logql,
        "start": _nanos(start_iso),
        "end": _nanos(end_iso),
    }
    if limit is not None:
        limit = max(1, min(limit, _MAX_LOG_LIMIT))
    else:
        limit = _DEFAULT_LOG_LIMIT
    params["limit"] = str(limit)
    if direction:
        params["direction"] = direction
    else:
        params["direction"] = "backward"
    payload = await client.request_json("/loki/api/v1/query_range", params=params)
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise ValueError(f"Unexpected Loki response: {payload}")
    return payload.get("data", {}).get("result", [])


def _format_log_entries(streams: Iterable[Any]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        labels = stream.get("stream") if isinstance(
            stream.get("stream"), dict) else {}
        values = stream.get("values")
        if not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, list) or len(value) < 2:
                continue
            timestamp = str(value[0])
            raw = value[1]
            try:
                line = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                line = raw
            if isinstance(line, (int, float)):
                entry: Dict[str, Any] = {
                    "timestamp": timestamp,
                    "value": float(line),
                    "labels": labels,
                }
            else:
                entry = {
                    "timestamp": timestamp,
                    "line": str(line),
                    "labels": labels,
                }
            entries.append(entry)
    return entries


async def _query_stats(
    ctx: Context,
    uid: str,
    logql: str,
    start: Optional[str],
    end: Optional[str],
) -> Dict[str, Any]:
    client = await _create_loki_client(ctx, uid)
    start_iso, end_iso = _time_range(start, end)
    params = {
        "query": logql,
        "start": _nanos(start_iso),
        "end": _nanos(end_iso),
    }
    payload = await client.request_json("/loki/api/v1/index/stats", params=params)
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected Loki stats response: {payload}")
    return payload


def register(app: FastMCP) -> None:
    """Register Loki tools with the FastMCP server."""

    @app.tool(
        name="list_loki_label_names",
        title="List Loki label names",
        description=(
            "List the label keys available in a Loki datasource for an optional time range. "
            "Returns a consolidated response object to prevent JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."
        ),
    )
    async def list_loki_label_names(
        datasourceUid: str,
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_loki_label_names")
        labels = await _list_label_items(ctx, datasourceUid, "/loki/api/v1/labels", startRfc3339, endRfc3339)
        return {
            "labels": labels,
            "total_count": len(labels),
            "datasource_uid": datasourceUid,
            "start": startRfc3339,
            "end": endRfc3339,
            "type": "loki_label_names_result"
        }

    @app.tool(
        name="list_loki_label_values",
        title="List Loki label values",
        description=(
            "List the values for a given label name within a Loki datasource. "
            "Returns a consolidated response object to prevent JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."
        ),
    )
    async def list_loki_label_values(
        datasourceUid: str,
        labelName: str,
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_loki_label_values")
        path = f"/loki/api/v1/label/{labelName}/values"
        values = await _list_label_items(ctx, datasourceUid, path, startRfc3339, endRfc3339)
        return {
            "values": values,
            "total_count": len(values),
            "label_name": labelName,
            "datasource_uid": datasourceUid,
            "start": startRfc3339,
            "end": endRfc3339,
            "type": "loki_label_values_result"
        }

    @app.tool(
        name="query_loki_logs",
        title="Query Loki logs",
        description="Execute a LogQL query against a Loki datasource and return the matching log entries.",
    )
    async def query_loki_logs(
        datasourceUid: str,
        logql: str,
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        limit: Optional[int] = None,
        direction: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> List[Dict[str, Any]]:
        if ctx is None:
            raise ValueError("Context injection failed for query_loki_logs")
        streams = await _query_range(ctx, datasourceUid, logql, startRfc3339, endRfc3339, limit, direction)
        return _format_log_entries(streams)

    @app.tool(
        name="query_loki_stats",
        title="Get Loki log statistics",
        description="Return statistics about the log streams that match a LogQL selector in Loki.",
    )
    async def query_loki_stats(
        datasourceUid: str,
        logql: str,
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError("Context injection failed for query_loki_stats")
        return await _query_stats(ctx, datasourceUid, logql, startRfc3339, endRfc3339)


__all__ = ["register"]
