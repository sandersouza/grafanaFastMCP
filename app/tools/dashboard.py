"""Dashboard tools for the Python Grafana FastMCP implementation."""

from __future__ import annotations

import copy
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from pydantic import BaseModel, ConfigDict, Field

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaAPIError, GrafanaClient


_CACHE_KEY = "_dashboard_payload_cache"


def _dashboard_cache(ctx: Context) -> Dict[str, Any]:
    session = ctx.request_context.session
    cache = getattr(session, _CACHE_KEY, None)
    if cache is None:
        cache = {}
        setattr(session, _CACHE_KEY, cache)
    return cache


def _cache_dashboard(ctx: Context, uid: str, payload: Dict[str, Any]) -> None:
    cache = _dashboard_cache(ctx)
    cache[uid] = copy.deepcopy(payload)


def _cached_dashboard(ctx: Context, uid: str) -> Optional[Dict[str, Any]]:
    cache = _dashboard_cache(ctx)
    payload = cache.get(uid)
    return copy.deepcopy(payload) if isinstance(payload, dict) else None


async def _get_dashboard(ctx: Context, uid: str, *, use_cache: bool = True) -> Dict[str, Any]:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    if use_cache:
        cached = _cached_dashboard(ctx, uid)
        if cached is not None:
            return cached
    dashboard = await client.get_json(f"/dashboards/uid/{uid}")
    if not isinstance(dashboard, dict):
        raise ValueError("Unexpected Grafana response when fetching dashboard")
    _cache_dashboard(ctx, uid, dashboard)
    return copy.deepcopy(dashboard)


async def _post_dashboard(
    ctx: Context,
    dashboard: Dict[str, Any],
    folder_uid: Optional[str],
    message: Optional[str],
    overwrite: bool,
    user_id: Optional[int],
) -> Any:
    """
    Post dashboard to Grafana API and return a consolidated response.

    This function wraps the raw Grafana dashboard creation/update response
    to prevent JSON chunking issues when used with streamable HTTP transport
    alongside ChatGPT/OpenAI. Instead of returning the raw response from
    Grafana's /dashboards/db endpoint, we return a consolidated summary.
    """
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    payload: Dict[str, Any] = {
        "dashboard": dashboard,
        "overwrite": overwrite,
    }
    if folder_uid is not None:
        payload["folderUid"] = folder_uid
    if message is not None:
        payload["message"] = message
    if user_id is not None:
        payload["userId"] = user_id

    try:
        # Get the raw response from Grafana
        raw_response = await client.post_json("/dashboards/db", json=payload)

        # Extract key information for a consolidated response
        dashboard_title = dashboard.get("title", "Unknown Dashboard")
        dashboard_uid = dashboard.get("uid", "")

        # Return a consolidated response object to avoid chunking issues
        # in streamable HTTP with ChatGPT/OpenAI
        return {
            "status": "success",
            "operation": "update" if dashboard.get("id") else "create",
            "dashboard": {
                "uid": dashboard_uid,
                "title": dashboard_title,
                "url": raw_response.get("url", ""),
                "id": raw_response.get("id", 0),
                "version": raw_response.get("version", 1)
            },
            "message": message or "",
            "folder_uid": folder_uid or "",
            "overwrite": overwrite,
            "grafana_response": raw_response,
            "type": "dashboard_operation_result"
        }

    except GrafanaAPIError as exc:
        if exc.status_code == 412 and "name-exists" in exc.message:
            raise ValueError(
                "Grafana recusou a criação porque já existe um dashboard com o mesmo título na pasta. "
                "Defina overwrite=True para sobrescrever ou escolha outro nome.") from exc
        raise


def _schema_version_default() -> int:
    raw = os.getenv("DASHBOARD_SCHEMA_VERSION")
    if raw is None:
        return 39
    try:
        return int(raw)
    except ValueError:
        return 39


def _apply_dashboard_defaults(dashboard_obj: Dict[str, Any]) -> None:
    time_defaults = dashboard_obj.setdefault("time", {})
    time_defaults.setdefault(
        "from", os.getenv(
            "DASHBOARD_TIME_FROM", "now-1h"))
    time_defaults.setdefault("to", os.getenv("DASHBOARD_TIME_TO", "now"))

    if "schemaVersion" not in dashboard_obj:
        dashboard_obj["schemaVersion"] = _schema_version_default()

    version = dashboard_obj.get("version")
    if isinstance(version, int):
        dashboard_obj["version"] = version + 1
    else:
        dashboard_obj["version"] = 1

    default_uid = os.getenv("DASH_UID")
    if default_uid and not dashboard_obj.get("uid"):
        dashboard_obj["uid"] = default_uid

    prom_uid = os.getenv("PROM_DS_UID")
    if prom_uid:
        panels = dashboard_obj.get("panels")
        if isinstance(panels, list):
            for panel in panels:
                if not isinstance(panel, dict):
                    continue
                datasource = panel.get("datasource")
                if datasource is None:
                    panel["datasource"] = {"uid": prom_uid}
                elif isinstance(datasource, dict) and "uid" not in datasource:
                    datasource["uid"] = prom_uid


@dataclass
class JSONPathSegment:
    key: str
    index: int = 0
    is_array: bool = False
    is_append: bool = False
    is_wildcard: bool = False


_SEGMENT_RE = re.compile(r"([^.\\[\\]/]+)(?:\\[((?:\\d+)|\*)\\])?(?:(/-))?")


def _parse_json_path(path: str) -> List[JSONPathSegment]:
    if path.startswith("$."):
        path = path[2:]
    path = path.lstrip(".")
    segments: List[JSONPathSegment] = []
    for match in _SEGMENT_RE.finditer(path):
        key = match.group(1)
        if not key:
            continue
        index_str = match.group(2)
        is_append = bool(match.group(3))
        segment = JSONPathSegment(key=key)
        if index_str is not None:
            segment.is_array = True
            if index_str == "*":
                segment.is_wildcard = True
            else:
                try:
                    segment.index = int(index_str)
                except ValueError as exc:  # pragma: no cover - defensive
                    raise ValueError(
                        f"Invalid array index in JSONPath: {index_str}") from exc
        segment.is_append = is_append
        if segment.is_append and segment.is_wildcard:
            raise ValueError(
                "Cannot combine append syntax with wildcard JSONPath segments")
        segments.append(segment)
    return segments


def _validate_array(current: Dict[str, Any],
                    segment: JSONPathSegment) -> List[Any]:
    value = current.get(segment.key)
    if not isinstance(value, list):
        raise ValueError(f"Field '{segment.key}' is not an array")
    if segment.is_wildcard:
        return value
    if not segment.is_append and not (0 <= segment.index < len(value)):
        raise ValueError(
            f"Index {segment.index} out of bounds for array '{segment.key}' (length {len(value)})"
        )
    return value


def _navigate_segment(
        current: Dict[str, Any], segment: JSONPathSegment) -> Dict[str, Any]:
    if segment.is_append:
        raise ValueError(
            "Append syntax can only be used at the final JSONPath segment")
    if segment.is_array:
        arr = _validate_array(current, segment)
        if segment.is_wildcard:
            raise ValueError(
                "Wildcard JSONPath segments are not supported for navigation")
        value = arr[segment.index]
        if not isinstance(value, dict):
            raise ValueError(
                f"Element at {segment.key}[{segment.index}] is not an object")
        return value
    value = current.get(segment.key)
    if not isinstance(value, dict):
        raise ValueError(f"Field '{segment.key}' is not an object")
    return value


def _set_at_segment(current: Dict[str, Any],
                    segment: JSONPathSegment, value: Any) -> None:
    if segment.is_append:
        arr = _validate_array(current, segment)
        arr.append(value)
        current[segment.key] = arr
        return
    if segment.is_wildcard:
        raise ValueError(
            "Wildcard JSONPath segments are not supported for modification")
    if segment.is_array:
        arr = _validate_array(current, segment)
        arr[segment.index] = value
        return
    current[segment.key] = value


def _remove_at_segment(
        current: Dict[str, Any], segment: JSONPathSegment) -> None:
    if segment.is_append:
        raise ValueError("Cannot use append syntax when removing values")
    if segment.is_array:
        raise ValueError("Removing individual array elements is not supported")
    if segment.is_wildcard:
        raise ValueError(
            "Wildcard JSONPath segments are not supported for removal")
    if segment.key in current:
        del current[segment.key]


def _apply_json_path(data: Dict[str, Any],
                     path: str, value: Any, remove: bool) -> None:
    segments = _parse_json_path(path)
    if not segments:
        raise ValueError("JSONPath cannot be empty")
    current = data
    for segment in segments[:-1]:
        current = _navigate_segment(current, segment)
    final_segment = segments[-1]
    if remove:
        _remove_at_segment(current, final_segment)
    else:
        _set_at_segment(current, final_segment, value)


class DashboardPatchOperation(BaseModel):
    """Structured representation of a JSON patch operation for dashboards."""

    op: str = Field(
        description="Operation to perform (supported: add, remove, replace)",
        pattern="^(add|remove|replace)$",
    )
    path: str = Field(
        description="JSONPath identifying the dashboard field to modify")
    value: Any | None = Field(
        default=None,
        description="Value to apply for add/replace operations. Omit for remove operations.",
    )

    model_config = ConfigDict(populate_by_name=True)

    def as_mapping(self) -> Dict[str, Any]:
        payload = self.model_dump(by_alias=True)
        if self.op == "remove":
            payload.pop("value", None)
        return payload


PatchOperationInput = Union[DashboardPatchOperation, Mapping[str, Any]]


def _normalize_patch_operations(
        operations: Sequence[PatchOperationInput]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for index, operation in enumerate(operations):
        if isinstance(operation, DashboardPatchOperation):
            normalized.append(operation.as_mapping())
        elif isinstance(operation, Mapping):
            normalized.append(dict(operation))
        else:
            raise TypeError(
                "Invalid patch operation at index "
                f"{index}: expected mapping-compatible data, got {type(operation)!r}")
    return normalized


async def _update_dashboard_with_patches(
    ctx: Context,
    uid: str,
    operations: Sequence[PatchOperationInput],
    folder_uid: Optional[str],
    message: Optional[str],
    user_id: Optional[int],
) -> Any:
    normalized_operations = _normalize_patch_operations(operations)
    source = await _get_dashboard(ctx, uid)
    dashboard_obj = source.get("dashboard")
    if not isinstance(dashboard_obj, dict):
        raise ValueError("Dashboard payload does not contain a JSON object")
    working_copy: Dict[str, Any] = copy.deepcopy(dashboard_obj)
    for idx, operation in enumerate(normalized_operations):
        op = str(operation.get("op", ""))
        path = str(operation.get("path", ""))
        if not op or not path:
            raise ValueError(f"Operation {idx} missing op or path")
        if op not in {"replace", "add", "remove"}:
            raise ValueError(
                f"Unsupported patch operation '{op}' at index {idx}")
        remove = op == "remove"
        value = operation.get("value") if not remove else None
        try:
            _apply_json_path(working_copy, path, value, remove)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(
                f"Failed to apply operation {idx} ({op} {path}): {exc}") from exc

    effective_folder = folder_uid
    meta = source.get("meta")
    if effective_folder is None and isinstance(meta, dict):
        meta_folder = meta.get("folderUid")
        if isinstance(meta_folder, str):
            effective_folder = meta_folder

    result = await _post_dashboard(
        ctx,
        working_copy,
        effective_folder,
        message,
        overwrite=True,
        user_id=user_id,
    )
    _cache_dashboard(
        ctx, uid, {
            "dashboard": working_copy, "meta": source.get("meta")})
    return result


async def _update_dashboard_full(
    ctx: Context,
    dashboard: Dict[str, Any],
    folder_uid: Optional[str],
    message: Optional[str],
    overwrite: bool,
    user_id: Optional[int],
) -> Any:
    effective_overwrite = overwrite
    if not effective_overwrite:
        dash_id = dashboard.get("id")
        if isinstance(dash_id, int) and dash_id > 0:
            effective_overwrite = True
    result = await _post_dashboard(ctx, dashboard, folder_uid, message, effective_overwrite, user_id)
    uid = dashboard.get("uid")
    if isinstance(uid, str) and uid:
        _cache_dashboard(ctx, uid, {"dashboard": dashboard})
    return result


async def _update_dashboard(
    ctx: Context,
    dashboard: Optional[Dict[str, Any]],
    uid: Optional[str],
    operations: Optional[Sequence[PatchOperationInput]],
    folder_uid: Optional[str],
    message: Optional[str],
    overwrite: bool,
    user_id: Optional[int],
) -> Any:
    if operations and uid:
        return await _update_dashboard_with_patches(
            ctx,
            uid,
            operations,
            folder_uid,
            message,
            user_id,
        )
    if dashboard is not None:
        return await _update_dashboard_full(
            ctx,
            dashboard,
            folder_uid,
            message,
            overwrite,
            user_id,
        )
    raise ValueError(
        "Either dashboard JSON or (uid + operations) must be provided")


async def _get_panel_queries(ctx: Context, uid: str, *, use_cache: bool = True) -> List[Dict[str, Any]]:
    payload = await _get_dashboard(ctx, uid, use_cache=use_cache)
    dashboard_obj = payload.get("dashboard")
    if not isinstance(dashboard_obj, dict):
        raise ValueError("Dashboard payload does not contain a JSON object")
    panels = dashboard_obj.get("panels")
    if not isinstance(panels, list):
        raise ValueError("Dashboard does not contain a panels array")
    results: List[Dict[str, Any]] = []
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        title = panel.get("title", "")
        datasource_info: Dict[str, Any] = {}
        datasource_field = panel.get("datasource")
        if isinstance(datasource_field, dict):
            if "uid" in datasource_field:
                datasource_info["uid"] = datasource_field.get("uid")
            if "type" in datasource_field:
                datasource_info["type"] = datasource_field.get("type")
        targets = panel.get("targets")
        if not isinstance(targets, list):
            continue
        for target in targets:
            if not isinstance(target, dict):
                continue
            expr = target.get("expr")
            if isinstance(expr, str) and expr:
                results.append(
                    {
                        "title": title,
                        "query": expr,
                        "datasource": datasource_info,
                    }
                )
    return results


def _evaluate_json_path(data: Dict[str, Any], path: str) -> Any:
    segments = _parse_json_path(path)
    if not segments:
        raise ValueError("JSONPath cannot be empty")

    current_values: List[Any] = [data]
    for idx, segment in enumerate(segments):
        next_values: List[Any] = []
        for value in current_values:
            if not isinstance(value, dict):
                raise ValueError(
                    f"Segment '{segment.key}' at position {idx} cannot be applied to non-object value"
                )

            if segment.is_array:
                if segment.key not in value:
                    raise ValueError(
                        f"Field '{segment.key}' not found while evaluating JSONPath")
                array_value = value.get(segment.key)
                if not isinstance(array_value, list):
                    raise ValueError(f"Field '{segment.key}' is not an array")
                if segment.is_append:
                    raise ValueError(
                        "Append syntax is not supported when evaluating JSONPath expressions")
                if segment.is_wildcard:
                    next_values.extend(array_value)
                else:
                    if not (0 <= segment.index < len(array_value)):
                        raise ValueError(
                            f"Index {segment.index} out of bounds for array '{segment.key}' (length {len(array_value)})"
                        )
                    next_values.append(array_value[segment.index])
            else:
                if segment.is_append:
                    raise ValueError(
                        "Append syntax is not supported when evaluating JSONPath expressions")
                if segment.key not in value:
                    raise ValueError(
                        f"Field '{segment.key}' not found while evaluating JSONPath")
                next_values.append(value.get(segment.key))

        current_values = next_values

    if not current_values:
        return []
    if len(current_values) == 1:
        return current_values[0]
    return current_values


def _safe_string(data: Dict[str, Any], key: str) -> str:
    value = data.get(key)
    return value if isinstance(value, str) else ""


def _safe_string_list(data: Dict[str, Any], key: str) -> List[str]:
    value = data.get(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _safe_object(data: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    value = data.get(key)
    return value if isinstance(value, dict) else None


def _safe_array(data: Dict[str, Any], key: str) -> Optional[List[Any]]:
    value = data.get(key)
    return value if isinstance(value, list) else None


def _safe_int(data: Dict[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool):  # bool is subclass of int; exclude explicitly
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _extract_time_range(dashboard: Dict[str, Any]) -> Dict[str, str]:
    time_obj = _safe_object(dashboard, "time")
    if not time_obj:
        return {"from": "", "to": ""}
    return {
        "from": _safe_string(time_obj, "from"),
        "to": _safe_string(time_obj, "to"),
    }


def _extract_panel_summary(panel: Dict[str, Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "id": _safe_int(panel, "id"),
        "title": _safe_string(panel, "title"),
        "type": _safe_string(panel, "type"),
        "queryCount": len(_safe_array(panel, "targets") or []),
    }
    description = _safe_string(panel, "description")
    if description:
        summary["description"] = description
    return summary


def _extract_variable_summary(variable: Dict[str, Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "name": _safe_string(variable, "name"),
        "type": _safe_string(variable, "type"),
    }
    label = _safe_string(variable, "label")
    if label:
        summary["label"] = label
    return summary


def _extract_basic_dashboard_info(
        dashboard: Dict[str, Any], summary: Dict[str, Any]) -> None:
    summary["title"] = _safe_string(dashboard, "title")
    description = _safe_string(dashboard, "description")
    if description:
        summary["description"] = description
    tags = _safe_string_list(dashboard, "tags")
    if tags:
        summary["tags"] = tags
    refresh = _safe_string(dashboard, "refresh")
    if refresh:
        summary["refresh"] = refresh


def _build_summary(
        uid: str, dashboard: Dict[str, Any], meta: Any) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "uid": uid,
        "panels": [],
        "panelCount": 0,
        "timeRange": _extract_time_range(dashboard),
    }
    _extract_basic_dashboard_info(dashboard, summary)

    panels = _safe_array(dashboard, "panels") or []
    summary["panelCount"] = len(panels)
    summary["panels"] = [_extract_panel_summary(
        panel) for panel in panels if isinstance(panel, dict)]

    templating = _safe_object(dashboard, "templating")
    variables: List[Dict[str, Any]] = []
    if templating:
        for variable in _safe_array(templating, "list") or []:
            if isinstance(variable, dict):
                variables.append(_extract_variable_summary(variable))
    if variables:
        summary["variables"] = variables

    if isinstance(meta, dict) and meta:
        summary["meta"] = meta

    return summary


def register(app: FastMCP) -> None:
    """Register dashboard tools with the FastMCP server."""

    @app.tool(
        name="get_dashboard_by_uid",
        title="Get dashboard details",
        description=(
            "Retrieve the complete dashboard payload, including metadata and panels, for a given dashboard UID."
        ),
    )
    async def get_dashboard_by_uid(
        uid: str,
        forceRefresh: bool = False,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for get_dashboard_by_uid")
        return await _get_dashboard(ctx, uid, use_cache=not forceRefresh)

    @app.tool(
        name="update_dashboard", title="Create or update dashboard", description=(
            "Create a new dashboard or update an existing one. Returns a consolidated response object "
            "with operation status, dashboard metadata, and success confirmation. "
            "This format prevents JSON chunking issues in streamable HTTP with ChatGPT/OpenAI. "
            "Provide either the full dashboard JSON (for create/replace) "
            "or supply a dashboard UID with patch operations for targeted edits."), )
    async def update_dashboard(
        dashboard: Optional[Dict[str, Any]] = None,
        uid: Optional[str] = None,
        operations: Optional[Sequence[PatchOperationInput]] = None,
        folderUid: Optional[str] = None,
        message: Optional[str] = None,
        overwrite: bool = True,
        userId: Optional[int] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError("Context injection failed for update_dashboard")

        dashboard_payload = copy.deepcopy(
            dashboard) if dashboard is not None else None
        if dashboard_payload is not None:
            _apply_dashboard_defaults(dashboard_payload)

        default_folder = os.getenv("FOLDER_UID")
        if folderUid is None and default_folder:
            folderUid = default_folder

        if dashboard_payload is not None and uid is None:
            potential_uid = dashboard_payload.get("uid")
            if isinstance(potential_uid, str) and potential_uid:
                uid = potential_uid
        default_uid = os.getenv("DASH_UID")
        if uid is None and default_uid:
            uid = default_uid

        return await _update_dashboard(
            ctx,
            dashboard_payload,
            uid,
            operations,
            folderUid,
            message,
            overwrite,
            userId,
        )

    @app.tool(
        name="get_dashboard_panel_queries",
        title="Get dashboard panel queries",
        description=(
            "Return a list of panel queries for the specified dashboard. Each entry includes the panel title, the LogQL/PromQL "
            "expression, and datasource metadata."),
    )
    async def get_dashboard_panel_queries(
        uid: str,
        forceRefresh: bool = False,
        ctx: Optional[Context] = None,
    ) -> List[Dict[str, Any]]:
        if ctx is None:
            raise ValueError(
                "Context injection failed for get_dashboard_panel_queries")
        return await _get_panel_queries(ctx, uid, use_cache=not forceRefresh)

    @app.tool(
        name="get_dashboard_property",
        title="Get dashboard property",
        description="Retrieve a specific property from a dashboard using a simplified JSONPath expression.",
    )
    async def get_dashboard_property(
        uid: str,
        jsonPath: str,
        forceRefresh: bool = False,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for get_dashboard_property")
        dashboard = await _get_dashboard(ctx, uid, use_cache=not forceRefresh)
        data = dashboard.get("dashboard")
        if not isinstance(data, dict):
            raise ValueError(
                "Dashboard payload does not contain a JSON object")
        return _evaluate_json_path(data, jsonPath)

    @app.tool(
        name="get_dashboard_summary",
        title="Get dashboard summary",
        description="Return a compact summary of the dashboard including panels, variables, and metadata.",
    )
    async def get_dashboard_summary(
        uid: str,
        forceRefresh: bool = False,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError(
                "Context injection failed for get_dashboard_summary")
        dashboard = await _get_dashboard(ctx, uid, use_cache=not forceRefresh)
        data = dashboard.get("dashboard")
        if not isinstance(data, dict):
            raise ValueError(
                "Dashboard payload does not contain a JSON object")
        return _build_summary(uid, data, dashboard.get("meta"))


__all__ = ["register"]
