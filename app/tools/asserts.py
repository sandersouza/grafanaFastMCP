"""Tools for interacting with Grafana Asserts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, Optional

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaClient


_RELATIVE_TIME_PATTERN = re.compile(
    r"^now(?:(?P<sign>[+-])(?P<value>\d+)(?P<unit>[smhdw]))*$",
    re.IGNORECASE)


_RELATIVE_UNIT_TO_DELTA = {
    "s": lambda amount: timedelta(seconds=amount),
    "m": lambda amount: timedelta(minutes=amount),
    "h": lambda amount: timedelta(hours=amount),
    "d": lambda amount: timedelta(days=amount),
    "w": lambda amount: timedelta(weeks=amount),
}


def _parse_relative_time(expression: str) -> datetime | None:
    match = _RELATIVE_TIME_PATTERN.fullmatch(expression)
    if not match:
        return None

    current = datetime.now(timezone.utc)
    # Extract segments after the leading "now"
    for segment in re.finditer(
            r"([+-])(\d+)([smhdw])", expression[3:], re.IGNORECASE):
        sign, value_str, unit = segment.groups()
        amount = int(value_str)
        delta_factory = _RELATIVE_UNIT_TO_DELTA.get(unit.lower())
        if delta_factory is None:
            raise ValueError(
                f"Unsupported relative time unit '{unit}' in expression '{expression}'")
        delta = delta_factory(amount)
        if sign == "+":
            current += delta
        else:
            current -= delta
    return current


def _parse_time(value: Any, field_name: str) -> int:
    if isinstance(value, (int, float)):
        return int(float(value))
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"{field_name} must not be empty")
        relative = _parse_relative_time(cleaned)
        if relative is not None:
            return int(relative.timestamp() * 1000)
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(cleaned)
        except ValueError as exc:
            raise ValueError(
                f"Invalid RFC3339 timestamp for {field_name}: {value}") from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    raise ValueError(
        f"Unsupported timestamp type for {field_name}: {type(value)!r}")


async def _get_assertions(ctx: Context, args: Dict[str, Any]) -> str:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)

    start_ms = _parse_time(args.get("startTime"), "startTime")
    end_ms = _parse_time(args.get("endTime"), "endTime")

    entity_type = args.get("entityType")
    entity_name = args.get("entityName")
    if not entity_type or not entity_name:
        raise ValueError("Both entityType and entityName must be provided")

    scope: Dict[str, str] = {}
    for key in ("env", "site", "namespace"):
        value = args.get(key)
        if isinstance(value, str) and value:
            scope[key] = value

    request_body = {"startTime": start_ms,
                    "endTime": end_ms,
                    "entityKeys": [{"name": entity_name,
                                    "type": entity_type,
                                    "scope": scope,
                                    }],
                    "suggestionSrcEntities": [],
                    "alertCategories": ["saturation",
                                        "amend",
                                        "anomaly",
                                        "failure",
                                        "error"],
                    }

    path = "/plugins/grafana-asserts-app/resources/asserts/api-server/v1/assertions/llm-summary"
    response = await client.post_json(path, json=request_body)
    return response if isinstance(response, str) else str(response)


def register(app: FastMCP) -> None:
    """Register Grafana Asserts tools."""

    @app.tool(
        name="get_assertions",
        title="Get assertions summary",
        description="Retrieve Grafana Asserts summary for a specific entity and time range.",
    )
    async def get_assertions(
        startTime: Any,
        endTime: Any,
        entityType: str,
        entityName: str,
        env: Optional[str] = None,
        site: Optional[str] = None,
        namespace: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> str:
        if ctx is None:
            raise ValueError("Context injection failed for get_assertions")
        args = {
            "startTime": startTime,
            "endTime": endTime,
            "entityType": entityType,
            "entityName": entityName,
            "env": env,
            "site": site,
            "namespace": namespace,
        }
        return await _get_assertions(ctx, args)


__all__ = ["register"]
