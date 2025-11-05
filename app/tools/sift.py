"""Grafana Sift investigation tools."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaClient


_BASE_PATH = "/plugins/grafana-ml-app/resources/sift/api/v1"

_DURATION_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)(?P<unit>ns|us|µs|ms|s|m|h|d)")
_UNIT_SECONDS = {
    "ns": 1e-9,
    "us": 1e-6,
    "µs": 1e-6,
    "ms": 1e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _time_range(start: Optional[datetime],
                end: Optional[datetime]) -> tuple[datetime,
                                                  datetime]:
    end_dt = end or _now()
    start_dt = start or end_dt - timedelta(minutes=30)
    if start_dt >= end_dt:
        raise ValueError("start time must be before end time")
    return start_dt, end_dt


async def _sift_request(
    ctx: Context,
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    json: Any = None,
) -> Any:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    return await client.request(method, f"{_BASE_PATH}{path}", params=params, json=json)


async def _sift_get_json(
    ctx: Context,
    path: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response = await _sift_request(ctx, "GET", path, params=params)
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Unexpected response from Sift API")
    return payload


async def _get_investigation(
        ctx: Context, investigation_id: str) -> Dict[str, Any]:
    payload = await _sift_get_json(ctx, f"/investigations/{investigation_id}")
    return payload.get("data") or payload


async def _get_analyses(
        ctx: Context, investigation_id: str) -> List[Dict[str, Any]]:
    payload = await _sift_get_json(ctx, f"/investigations/{investigation_id}/analyses")
    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


async def _list_investigations(
        ctx: Context, limit: Optional[int]) -> List[Dict[str, Any]]:
    params = {"limit": limit or 10}
    payload = await _sift_get_json(ctx, "/investigations", params=params)
    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


async def _create_investigation(
    ctx: Context,
    name: str,
    labels: Dict[str, str],
    checks: List[str],
    start: Optional[datetime],
    end: Optional[datetime],
) -> Dict[str, Any]:
    start_dt, end_dt = _time_range(start, end)
    payload = {
        "name": name,
        "status": "pending",
        "grafanaUrl": get_grafana_config(ctx).url,
        "requestData": {
            "labels": labels,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "checks": checks,
        },
    }
    response = await _sift_request(ctx, "POST", "/investigations", json=payload)
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Unexpected response when creating investigation")
    created = data.get("data") or data
    return created


async def _wait_for_completion(
        ctx: Context, investigation_id: str) -> Dict[str, Any]:
    deadline = _now() + timedelta(minutes=5)
    while True:
        investigation = await _get_investigation(ctx, investigation_id)
        status = str(investigation.get("status", ""))
        if status.lower() == "finished":
            return investigation
        if status.lower() == "failed":
            raise ValueError("Sift investigation failed")
        if _now() > deadline:
            raise TimeoutError(
                "Timed out waiting for Sift investigation to finish")
        await asyncio.sleep(5)


def _find_analysis(analyses: List[Dict[str, Any]],
                   name: str) -> Dict[str, Any]:
    for analysis in analyses:
        if str(analysis.get("name", "")) == name:
            return analysis
    raise ValueError(f"Analysis '{name}' not found in investigation")


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None

    reference = _now()
    lowered = cleaned.lower()
    if lowered == "now":
        return reference
    if lowered.startswith("now-") or lowered.startswith("now+"):
        sign = -1 if lowered.startswith("now-") else 1
        duration_expr = cleaned[4:]
        if not duration_expr:
            raise ValueError(
                "Relative time expressions must include a duration (e.g. now-5m)")
        total_seconds = 0.0
        for match in _DURATION_RE.finditer(duration_expr):
            unit = match.group("unit")
            factor = _UNIT_SECONDS[unit]
            total_seconds += float(match.group("value")) * factor
        if total_seconds == 0.0:
            raise ValueError(
                f"Unable to parse duration expression '{duration_expr}'")
        delta = timedelta(seconds=total_seconds)
        return reference + (delta if sign > 0 else -delta)

    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def _run_check(
    ctx: Context,
    check_name: str,
    name: str,
    labels: Dict[str, str],
    start: Optional[str],
    end: Optional[str],
) -> Dict[str, Any]:
    start_dt = _parse_datetime(start)
    end_dt = _parse_datetime(end)
    created = await _create_investigation(ctx, name, labels, [check_name], start_dt, end_dt)
    investigation_id = str(created.get("id"))
    await _wait_for_completion(ctx, investigation_id)
    analyses = await _get_analyses(ctx, investigation_id)
    return _find_analysis(analyses, check_name)


def register(app: FastMCP) -> None:
    """Register Sift tools."""

    @app.tool(
        name="get_sift_investigation",
        title="Get Sift investigation",
        description="Retrieve a Sift investigation by ID.",
    )
    async def get_sift_investigation(
        investigationId: str,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError(
                "Context injection failed for get_sift_investigation")
        return await _get_investigation(ctx, investigationId)

    @app.tool(
        name="get_sift_analysis",
        title="Get Sift analysis",
        description="Retrieve a specific analysis result from a Sift investigation.",
    )
    async def get_sift_analysis(
        investigationId: str,
        analysisId: str,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError("Context injection failed for get_sift_analysis")
        analyses = await _get_analyses(ctx, investigationId)
        for analysis in analyses:
            if str(analysis.get("id")) == analysisId:
                return analysis
        raise ValueError(f"Analysis '{analysisId}' not found")

    @app.tool(
        name="list_sift_investigations",
        title="List Sift investigations",
        description="List recent Sift investigations.",
    )
    async def list_sift_investigations(
        limit: Optional[int] = None,
        ctx: Optional[Context] = None,
    ) -> List[Dict[str, Any]]:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_sift_investigations")
        return await _list_investigations(ctx, limit)

    @app.tool(
        name="find_error_pattern_logs",
        title="Find error pattern logs",
        description="Run the ErrorPatternLogs check via Sift and return the analysis result.",
    )
    async def find_error_pattern_logs(
        name: str,
        labels: Dict[str, str],
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError(
                "Context injection failed for find_error_pattern_logs")
        return await _run_check(
            ctx,
            "ErrorPatternLogs",
            name,
            labels,
            startRfc3339,
            endRfc3339,
        )

    @app.tool(
        name="find_slow_requests",
        title="Find slow requests",
        description="Run the SlowRequests check via Sift and return the analysis result.",
    )
    async def find_slow_requests(
        name: str,
        labels: Dict[str, str],
        startRfc3339: Optional[str] = None,
        endRfc3339: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError("Context injection failed for find_slow_requests")
        return await _run_check(
            ctx,
            "SlowRequests",
            name,
            labels,
            startRfc3339,
            endRfc3339,
        )


__all__ = ["register"]
