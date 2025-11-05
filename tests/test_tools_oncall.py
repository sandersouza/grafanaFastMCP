"""Tests for Grafana OnCall helper functions."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest

from app.tools import oncall
from mcp.server.fastmcp import FastMCP


class DummyGrafanaClient:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.payload: Dict[str, Any] = {}
        self.calls: list[str] = []

    async def get_json(self, path: str) -> Dict[str, Any]:
        self.calls.append(path)
        return self.payload


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    config = SimpleNamespace(
        api_key="token",
        access_token="access",
        id_token="id",
        basic_auth=("user", "pass"),
        url="https://grafana.local",
    )
    client = DummyGrafanaClient()
    client.payload = {
        "jsonData": {
            "onCallApiUrl": "https://oncall.example.com",
        }
    }
    monkeypatch.setattr(oncall, "get_grafana_config", lambda _: config)
    monkeypatch.setattr(oncall, "GrafanaClient", lambda cfg: client)
    return SimpleNamespace(
        request_context=SimpleNamespace(
            session=SimpleNamespace(),
            request=None))


def test_fetch_oncall_base_url_appends_default(ctx: SimpleNamespace) -> None:
    base = asyncio.run(oncall._fetch_oncall_base_url(ctx))
    assert base == "https://oncall.example.com/api/v1/"


def test_fetch_oncall_base_url_validates_json(
        ctx: SimpleNamespace,
        monkeypatch: pytest.MonkeyPatch) -> None:
    bad_client = DummyGrafanaClient()
    bad_client.payload = {"jsonData": {}}
    monkeypatch.setattr(oncall, "GrafanaClient", lambda cfg: bad_client)
    with pytest.raises(ValueError):
        asyncio.run(oncall._fetch_oncall_base_url(ctx))


class DummyOnCallClient:
    def __init__(self) -> None:
        self.responses: Dict[str, Any] = {}
        self.calls: list[tuple[str, Optional[Dict[str, Any]]]] = []

    async def request(
            self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        normalized = path if path.endswith("/") else f"{path}/"
        self.calls.append((normalized, params))
        result = self.responses.get(normalized)
        if isinstance(result, Exception):
            raise result
        return result or {}


@pytest.fixture
def client_fixture(monkeypatch: pytest.MonkeyPatch) -> DummyOnCallClient:
    client = DummyOnCallClient()

    async def create_client(_: Any) -> DummyOnCallClient:
        return client

    monkeypatch.setattr(oncall, "_create_client", create_client)
    return client


def test_list_schedules_handles_single_and_multiple(
        ctx: SimpleNamespace,
        client_fixture: DummyOnCallClient) -> None:
    client_fixture.responses["schedules/123/"] = {
        "id": 123,
        "name": "Primary",
        "team_id": 1,
        "time_zone": "UTC",
        "shifts": [
            "a",
            "b"]}
    single = asyncio.run(oncall._list_schedules(ctx, "123", None, None))
    assert single[0]["name"] == "Primary"

    client_fixture.responses["schedules/"] = {
        "results": [{"id": 1, "name": "Team"}, {"invalid": True}]}
    multiple = asyncio.run(oncall._list_schedules(ctx, None, "7", 2))
    assert multiple[0]["teamId"] is None
    assert client_fixture.calls[-1][1]["team_id"] == "7"


def test_oncall_client_headers_and_request(
        monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        api_key="token",
        access_token="access",
        id_token="id",
        basic_auth=("user", "pass"),
        url="https://grafana.local",
    )
    client = oncall.OnCallClient("https://oncall/api/v1/", config)

    headers = client._headers()
    assert headers["Authorization"] == "token"
    assert headers["X-Access-Token"] == "access"
    assert headers["X-Grafana-URL"] == "https://grafana.local"

    class DummyResponse:
        def __init__(self, status_code: int, payload: Dict[str, Any]) -> None:
            self.status_code = status_code
            self._payload = payload
            self.text = "{}"

        def json(self) -> Dict[str, Any]:
            return self._payload

    class DummyAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.calls: list[tuple[str, Dict[str, Any] | None]] = []

        async def __aenter__(self) -> "DummyAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self,
                      url: str,
                      params: Dict[str,
                                   Any] | None = None,
                      headers: Dict[str,
                                    Any] | None = None) -> DummyResponse:
            self.calls.append((url, params))
            if "error" in url:
                return DummyResponse(500, {})
            return DummyResponse(200, {"ok": True})

    dummy_client = DummyAsyncClient()
    monkeypatch.setattr(
        oncall.httpx,
        "AsyncClient",
        lambda *args,
        **kwargs: dummy_client)

    result = asyncio.run(client.request("schedules/", params={"page": 1}))
    assert result == {"ok": True}

    with pytest.raises(ValueError):
        asyncio.run(client.request("error/", params=None))


def test_get_shift_and_lists(
        ctx: SimpleNamespace,
        client_fixture: DummyOnCallClient) -> None:
    client_fixture.responses.update(
        {
            "on_call_shifts/1/": {"id": 1},
            "teams/": {"results": [{"id": 1}]},
            "users/": {"results": [{"id": "u1"}]},
            "users/u1/": {"id": "u1", "name": "User"},
            "schedules/1/": {"id": "1", "name": "Schedule", "on_call_now": ["u1"]},
        }
    )

    shift = asyncio.run(oncall._get_shift(ctx, "1"))
    assert shift["id"] == 1
    teams = asyncio.run(oncall._get_team_list(ctx, page=1))
    assert teams[0]["id"] == 1
    users = asyncio.run(
        oncall._get_users_list(
            ctx,
            page=None,
            username="user"))
    assert users[0]["id"] == "u1"
    user = asyncio.run(oncall._get_user(ctx, "u1"))
    assert user["name"] == "User"
    current = asyncio.run(oncall._current_oncall_users(ctx, "1"))
    assert current["users"][0]["id"] == "u1"


def test_current_oncall_users_aggregates_details(
        monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_schedule(ctx: Any, schedule_id: str) -> Dict[str, Any]:
        return {
            "id": schedule_id,
            "name": "Schedule",
            "on_call_now": [
                "1",
                "2"]}

    async def fake_get_user(ctx: Any, user_id: str) -> Dict[str, Any]:
        return {"id": user_id, "name": f"User {user_id}"}

    monkeypatch.setattr(oncall, "_get_schedule", fake_get_schedule)
    monkeypatch.setattr(oncall, "_get_user", fake_get_user)

    ctx = SimpleNamespace()
    result = asyncio.run(oncall._current_oncall_users(ctx, "99"))
    assert result["scheduleName"] == "Schedule"
    assert len(result["users"]) == 2


def test_oncall_tools_require_context() -> None:
    app = FastMCP()
    oncall.register(app)
    tools = asyncio.run(app.list_tools())
    tool = next(tool for tool in tools if tool.name == "list_oncall_schedules")
    with pytest.raises(ValueError):
        asyncio.run(tool.function(ctx=None))
