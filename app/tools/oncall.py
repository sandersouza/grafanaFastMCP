"""Grafana OnCall tools implemented in Python."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaClient
from ..grafana_client import USER_AGENT


async def _fetch_oncall_base_url(ctx: Context) -> str:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    settings = await client.get_json("/plugins/grafana-irm-app/settings")
    if not isinstance(settings, dict):
        raise ValueError("Unexpected response when retrieving OnCall settings")
    json_data = settings.get("jsonData")
    if not isinstance(json_data, dict):
        raise ValueError("OnCall settings missing jsonData field")
    api_url = json_data.get("onCallApiUrl")
    if not isinstance(api_url, str) or not api_url:
        raise ValueError("OnCall API URL not configured in Grafana")
    base = api_url.rstrip("/")
    if not base.endswith("/api/v1"):
        base = f"{base}/api/v1"
    return f"{base}/"


class OnCallClient:
    # type: ignore[no-untyped-def]
    def __init__(self, base_url: str, config) -> None:
        self._base_url = base_url
        self._config = config

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if self._config.api_key:
            headers["Authorization"] = self._config.api_key
        if self._config.access_token and self._config.id_token:
            headers.setdefault("X-Access-Token", self._config.access_token)
            headers.setdefault("X-Grafana-Id", self._config.id_token)
        if self._config.url:
            headers.setdefault("X-Grafana-URL", self._config.url)
        return headers

    async def request(
            self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self._base_url}{path.lstrip('/')}"
        auth: httpx.Auth | None = None
        if self._config.basic_auth:
            username, password = self._config.basic_auth
            auth = httpx.BasicAuth(username, password)
        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout, auth=auth) as client:
            response = await client.get(url, params=params, headers=self._headers())
        if response.status_code >= 400:
            raise ValueError(
                f"OnCall API error {response.status_code}: {response.text[:256]}"
            )
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected response from OnCall API")
        return data


async def _create_client(ctx: Context) -> OnCallClient:
    config = get_grafana_config(ctx)
    base_url = await _fetch_oncall_base_url(ctx)
    return OnCallClient(base_url, config)


def _summarize_schedule(schedule: Dict[str, Any]) -> Dict[str, Any]:
    shifts = schedule.get("shifts")
    if isinstance(shifts, list):
        shift_ids = [str(item) for item in shifts]
    else:
        shift_ids = []
    return {
        "id": schedule.get("id"),
        "name": schedule.get("name"),
        "teamId": schedule.get("team_id"),
        "timezone": schedule.get("time_zone"),
        "shifts": shift_ids,
    }


async def _list_schedules(ctx: Context,
                          schedule_id: Optional[str],
                          team_id: Optional[str],
                          page: Optional[int]) -> List[Dict[str,
                                                            Any]]:
    client = await _create_client(ctx)
    if schedule_id:
        try:
            schedule = await client.request(f"schedules/{schedule_id}/")
        except ValueError as exc:
            raise ValueError(
                f"Failed to fetch schedule '{schedule_id}': {exc}") from exc
        return [_summarize_schedule(schedule)]
    params: Dict[str, Any] = {}
    if page:
        params["page"] = page
    if team_id:
        params["team_id"] = team_id
    payload = await client.request("schedules/", params=params or None)
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    return [_summarize_schedule(item)
            for item in results if isinstance(item, dict)]


async def _get_shift(ctx: Context, shift_id: str) -> Dict[str, Any]:
    client = await _create_client(ctx)
    return await client.request(f"on_call_shifts/{shift_id}/")


async def _get_team_list(
        ctx: Context, page: Optional[int]) -> List[Dict[str, Any]]:
    client = await _create_client(ctx)
    params = {"page": page} if page else None
    payload = await client.request("teams", params=params)
    items = payload.get("results")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


async def _get_users_list(
    ctx: Context, page: Optional[int], username: Optional[str]
) -> List[Dict[str, Any]]:
    client = await _create_client(ctx)
    params: Dict[str, Any] = {}
    if page:
        params["page"] = page
    if username:
        params["username"] = username
    payload = await client.request("users/", params=params or None)
    items = payload.get("results")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


async def _get_user(ctx: Context, user_id: str) -> Dict[str, Any]:
    client = await _create_client(ctx)
    return await client.request(f"users/{user_id}/")


async def _get_schedule(ctx: Context, schedule_id: str) -> Dict[str, Any]:
    client = await _create_client(ctx)
    return await client.request(f"schedules/{schedule_id}/")


async def _current_oncall_users(
        ctx: Context, schedule_id: str) -> Dict[str, Any]:
    schedule = await _get_schedule(ctx, schedule_id)
    oncall = schedule.get("on_call_now")
    users: List[Dict[str, Any]] = []
    if isinstance(oncall, list):
        for user_id in oncall:
            try:
                user = await _get_user(ctx, str(user_id))
            except Exception:  # pragma: no cover - defensive
                continue
            users.append(user)
    return {
        "scheduleId": schedule.get("id"),
        "scheduleName": schedule.get("name"),
        "users": users,
    }


def register(app: FastMCP) -> None:
    """Register OnCall tools."""

    @app.tool(
        name="list_oncall_schedules",
        title="List OnCall schedules",
        description=(
            "List Grafana OnCall schedules with optional filtering by schedule ID or team ID. "
            "Returns a consolidated response object to prevent JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."
        ),
    )
    async def list_oncall_schedules(
        scheduleId: Optional[str] = None,
        teamId: Optional[str] = None,
        page: Optional[int] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_oncall_schedules")
        schedules = await _list_schedules(ctx, scheduleId, teamId, page)
        return {
            "schedules": schedules,
            "total_count": len(schedules),
            "schedule_id": scheduleId,
            "team_id": teamId,
            "page": page,
            "type": "oncall_schedules_result"
        }

    @app.tool(
        name="get_oncall_shift",
        title="Get OnCall shift",
        description="Retrieve details for a specific OnCall shift by ID.",
    )
    async def get_oncall_shift(
        shiftId: str,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError("Context injection failed for get_oncall_shift")
        try:
            return await _get_shift(ctx, shiftId)
        except ValueError as exc:
            raise ValueError(
                f"Failed to fetch shift '{shiftId}': {exc}") from exc

    @app.tool(
        name="get_current_oncall_users",
        title="Get current OnCall users",
        description="Return the users currently on call for a schedule.",
    )
    async def get_current_oncall_users(
        scheduleId: str,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        if ctx is None:
            raise ValueError(
                "Context injection failed for get_current_oncall_users")
        return await _current_oncall_users(ctx, scheduleId)

    @app.tool(
        name="list_oncall_teams",
        title="List OnCall teams",
        description=(
            "List teams configured in Grafana OnCall. "
            "Returns a consolidated response object to prevent JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."
        ),
    )
    async def list_oncall_teams(
        page: Optional[int] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError("Context injection failed for list_oncall_teams")
        teams = await _get_team_list(ctx, page)
        return {
            "teams": teams,
            "total_count": len(teams),
            "page": page,
            "type": "oncall_teams_result"
        }

    @app.tool(
        name="list_oncall_users",
        title="List OnCall users",
        description=(
            "List Grafana OnCall users or retrieve a specific user by ID. "
            "Returns a consolidated response object to prevent JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."
        ),
    )
    async def list_oncall_users(
        userId: Optional[str] = None,
        username: Optional[str] = None,
        page: Optional[int] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError("Context injection failed for list_oncall_users")
        if userId:
            try:
                user = await _get_user(ctx, userId)
                return {
                    "users": [user],
                    "total_count": 1,
                    "user_id": userId,
                    "type": "oncall_users_result"
                }
            except ValueError as exc:
                raise ValueError(
                    f"Failed to fetch OnCall user '{userId}': {exc}") from exc
        users = await _get_users_list(ctx, page, username)
        return {
            "users": users,
            "total_count": len(users),
            "username": username,
            "page": page,
            "type": "oncall_users_result"
        }


__all__ = ["register"]
