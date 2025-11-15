"""Prometheus datasource tools."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaAPIError, GrafanaClient, USER_AGENT
from ._label_matching import Selector


async def _ensure_datasource(ctx: Context, uid: str) -> None:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    try:
        await client.get_json(f"/datasources/uid/{uid}")
    except GrafanaAPIError as exc:  # pragma: no cover - defensive
        if exc.status_code == 404:
            raise ValueError(f"Datasource with UID '{uid}' not found") from exc
        raise


class PrometheusClient:
    def __init__(self, ctx: Context, datasource_uid: str) -> None:
        self._config = get_grafana_config(ctx)
        base = self._config.url.rstrip("/")
        self._base_url = f"{base}/api/datasources/proxy/uid/{datasource_uid}".rstrip(
            "/")
        tls = self._config.tls_config
        self._verify = tls.resolve_verify() if tls else True
        self._cert = tls.resolve_cert() if tls else None
        self._auth = (
            httpx.BasicAuth(*self._config.basic_auth)
            if self._config.basic_auth
            else None
        )

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"User-Agent": USER_AGENT}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        if self._config.access_token and self._config.id_token:
            headers.setdefault("X-Access-Token", self._config.access_token)
            headers.setdefault("X-Grafana-Id", self._config.id_token)
        return headers

    async def request_json(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self._base_url}{path}" if path.startswith(
            "/") else f"{self._base_url}/{path}"
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            verify=self._verify,
            cert=self._cert,
            auth=self._auth,
        ) as client:
            response = await client.get(url, params=params, headers=self._headers())
        if response.status_code >= 400:
            raise ValueError(
                f"Prometheus API error {response.status_code}: {response.text[:256]}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected response from Prometheus API")
        return payload


def _parse_rfc3339(value: str) -> datetime:
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


_DURATION_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)(?P<unit>ns|us|µs|ms|s|m|h|d)")
_UNIT_FACTORS = {
    "ns": 1e-9,
    "us": 1e-6,
    "µs": 1e-6,
    "ms": 1e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
}


def _parse_duration(expr: str) -> timedelta:
    total_seconds = 0.0
    for match in _DURATION_RE.finditer(expr):
        value = float(match.group("value"))
        unit = match.group("unit")
        factor = _UNIT_FACTORS[unit]
        total_seconds += value * factor
    if total_seconds == 0.0:
        raise ValueError(f"Unable to parse duration expression '{expr}'")
    return timedelta(seconds=total_seconds)


def _parse_time_expression(expr: str, now: datetime) -> datetime:
    if not isinstance(expr, str) or not expr:
        raise ValueError("Time expression must be a non-empty string")
    if expr == "now":
        return now
    if expr.startswith("now-"):
        duration = _parse_duration(expr[4:])
        return now - duration
    if expr.startswith("now+"):
        duration = _parse_duration(expr[4:])
        return now + duration
    return _parse_rfc3339(expr)


def _ensure_success(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("status") != "success":
        raise ValueError(f"Prometheus API returned error: {payload}")
    return payload


def _selectors_to_params(selectors: Iterable[Selector]) -> List[str]:
    return [selector.to_promql() for selector in selectors]


async def _query_prometheus(
    ctx: Context,
    datasource_uid: str,
    expr: str,
    start: Optional[str],
    end: Optional[str],
    step_seconds: Optional[int],
    query_type: Optional[str],
) -> Dict[str, Any]:
    await _ensure_datasource(ctx, datasource_uid)
    client = PrometheusClient(ctx, datasource_uid)
    now = datetime.now(timezone.utc)
    query = (query_type or "range").lower()
    if query == "range":
        effective_start = start or "now-5m"
        effective_end = end or "now"
        effective_step = step_seconds if step_seconds is not None else 60
        if effective_step <= 0:
            raise ValueError(
                "stepSeconds must be greater than zero for range queries")
        start_dt = _parse_time_expression(effective_start, now)
        end_dt = _parse_time_expression(effective_end, now)
        params = {
            "query": expr,
            "start": f"{start_dt.timestamp()}",
            "end": f"{end_dt.timestamp()}",
            "step": str(effective_step),
        }
        payload = await client.request_json("/api/v1/query_range", params=params)
    else:
        effective_start = start or "now"
        start_dt = _parse_time_expression(effective_start, now)
        params = {
            "query": expr,
            "time": f"{start_dt.timestamp()}",
        }
        payload = await client.request_json("/api/v1/query", params=params)
    return _ensure_success(payload).get("data", {})


async def _metadata(ctx: Context,
                    datasource_uid: str,
                    metric: Optional[str],
                    limit: Optional[int]) -> Dict[str,
                                                  Any]:
    await _ensure_datasource(ctx, datasource_uid)
    client = PrometheusClient(ctx, datasource_uid)
    params: Dict[str, Any] = {}
    if metric:
        params["metric"] = metric
    if limit:
        params["limit"] = str(limit)
    payload = await client.request_json("/api/v1/metadata", params=params or None)
    return _ensure_success(payload).get("data", {})


async def _label_names(
    ctx: Context,
    datasource_uid: str,
    matches: Iterable[Selector],
    start: Optional[str],
    end: Optional[str],
) -> List[str]:
    await _ensure_datasource(ctx, datasource_uid)
    client = PrometheusClient(ctx, datasource_uid)
    params: Dict[str, Any] = {}
    selector_params = _selectors_to_params(matches)
    for selector in selector_params:
        params.setdefault("match[]", []).append(selector)
    now = datetime.now(timezone.utc)
    if start:
        params["start"] = f"{_parse_time_expression(start, now).timestamp()}"
    if end:
        params["end"] = f"{_parse_time_expression(end, now).timestamp()}"
    payload = await client.request_json("/api/v1/labels", params=params or None)
    data = _ensure_success(payload).get("data", [])
    return [str(item) for item in data if isinstance(item, str)]


async def _label_values(
    ctx: Context,
    datasource_uid: str,
    label: str,
    matches: Iterable[Selector],
    start: Optional[str],
    end: Optional[str],
) -> List[str]:
    await _ensure_datasource(ctx, datasource_uid)
    client = PrometheusClient(ctx, datasource_uid)
    params: Dict[str, Any] = {}
    selector_params = _selectors_to_params(matches)
    for selector in selector_params:
        params.setdefault("match[]", []).append(selector)
    now = datetime.now(timezone.utc)
    if start:
        params["start"] = f"{_parse_time_expression(start, now).timestamp()}"
    if end:
        params["end"] = f"{_parse_time_expression(end, now).timestamp()}"
    payload = await client.request_json(
        f"/api/v1/label/{label}/values", params=params or None
    )
    data = _ensure_success(payload).get("data", [])
    return [str(item) for item in data if isinstance(item, str)]


async def _metric_names(
    ctx: Context,
    datasource_uid: str,
    regex: Optional[str],
    limit: Optional[int],
    page: Optional[int],
) -> List[str]:
    values = await _label_values(ctx, datasource_uid, "__name__", [], None, None)
    if regex:
        pattern = re.compile(regex)
        values = [value for value in values if pattern.search(value)]
    effective_limit = limit or 10
    effective_page = page or 1
    if effective_limit <= 0 or effective_page <= 0:
        raise ValueError("limit and page must be positive integers")
    start = (effective_page - 1) * effective_limit
    end = start + effective_limit
    if start >= len(values):
        return []
    return values[start:end]


def register(app: FastMCP) -> None:
    """Register Prometheus tools."""

    @app.tool(name="list_prometheus_metric_metadata",
              title="List Prometheus metric metadata",
              description="List metadata entries for metrics in a Prometheus datasource.",
              )
    async def list_prometheus_metric_metadata(
        datasourceUid: str,
        metric: Optional[str] = None,
        limit: Optional[int] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_prometheus_metric_metadata")
        return await _metadata(ctx, datasourceUid, metric, limit)

    @app.tool(
        name="query_prometheus",
        title="Query Prometheus",
        description="Execute PromQL queries against a Prometheus datasource.",
    )
    async def query_prometheus(
        datasourceUid: str,
        expr: str,
        startTime: Optional[str] = None,
        endTime: Optional[str] = None,
        stepSeconds: Optional[int] = None,
        queryType: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError("Context injection failed for query_prometheus")
        return await _query_prometheus(
            ctx,
            datasourceUid,
            expr,
            startTime,
            endTime,
            stepSeconds,
            queryType,
        )

    @app.tool(
        name="list_prometheus_metric_names",
        title="List Prometheus metric names",
        description="List metric names available in a Prometheus datasource.",
    )
    async def list_prometheus_metric_names(
        datasourceUid: str,
        regex: Optional[str] = None,
        limit: Optional[int] = None,
        page: Optional[int] = None,
        ctx: Optional[Context] = None,
    ) -> List[str]:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_prometheus_metric_names")
        return await _metric_names(ctx, datasourceUid, regex, limit, page)

    @app.tool(
        name="list_prometheus_label_names",
        title="List Prometheus label names",
        description="List label names in a Prometheus datasource.",
    )
    async def list_prometheus_label_names(
        datasourceUid: str,
        matches: Optional[Iterable[Dict[str, Any]]] = None,
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> List[str]:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_prometheus_label_names")
        selector_objs = []
        if matches:
            from .alerting import _parse_label_selectors  # type: ignore

            selector_objs = _parse_label_selectors(matches)
        return await _label_names(ctx, datasourceUid, selector_objs, startRfc3339, endRfc3339)

    @app.tool(
        name="list_prometheus_label_values",
        title="List Prometheus label values",
        description="List values for a specific label in a Prometheus datasource.",
    )
    async def list_prometheus_label_values(
        datasourceUid: str,
        labelName: str,
        matches: Optional[Iterable[Dict[str, Any]]] = None,
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> List[str]:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_prometheus_label_values")
        selector_objs = []
        if matches:
            from .alerting import _parse_label_selectors  # type: ignore

            selector_objs = _parse_label_selectors(matches)
        return await _label_values(
            ctx, datasourceUid, labelName, selector_objs, startRfc3339, endRfc3339
        )


__all__ = ["register"]
