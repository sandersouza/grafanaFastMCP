"""Tests exercising the dashboard tool helpers."""

from __future__ import annotations

import asyncio
import re
from copy import deepcopy
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from app.tools import dashboard
from mcp.server.fastmcp import FastMCP


@pytest.fixture
def sample_dashboard() -> Dict[str, Any]:
    return {
        "dashboard": {
            "title": "Example",
            "description": "Sample",
            "tags": ["infra"],
            "refresh": "5m",
            "time": {"from": "now-1h", "to": "now"},
            "panels": [
                {
                    "id": 1,
                    "title": "CPU",
                    "type": "graph",
                    "description": "CPU usage",
                    "targets": [{"expr": "sum(rate(http_requests_total[5m]))"}],
                    "datasource": {"uid": "ds1", "type": "prometheus"},
                },
                {
                    "id": 2,
                    "title": "Logs",
                    "type": "logs",
                    "targets": [],
                },
            ],
            "templating": {
                "list": [
                    {"name": "env", "type": "query", "label": "Environment"}
                ]
            },
        },
        "meta": {"folderUid": "folder"},
    }


@pytest.fixture(autouse=True)
def patch_json_path_regex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dashboard,
        "_SEGMENT_RE",
        re.compile(r"([^\.\[\]/]+)(?:\[((?:\d+)|\*)\])?(?:(/-))?"),
    )


def test_parse_json_path_and_navigation() -> None:
    segments = dashboard._parse_json_path("panels[0]")
    assert segments[0].is_array and segments[0].index == 0
    append_segments = dashboard._parse_json_path("panels/-")
    assert append_segments[-1].is_append is True

    data = {"panels": [{"targets": [{}]}]}
    dashboard._apply_json_path(data, "panels[0].targets[0]", {"expr": "1"}, remove=False)
    assert data["panels"][0]["targets"][0]["expr"] == "1"
    dashboard._apply_json_path(data, "panels[0].targets/-", {"expr": "2"}, remove=False)
    assert len(data["panels"][0]["targets"]) == 2
    dashboard._apply_json_path(data, "panels[0].targets", None, remove=True)
    assert data["panels"][0].get("targets") is None


def test_parse_json_path_errors() -> None:
    with pytest.raises(ValueError):
        dashboard._apply_json_path({}, "", None, remove=False)
    with pytest.raises(ValueError):
        dashboard._apply_json_path({}, "panels[*]", None, remove=False)


def test_evaluate_json_path_returns_values(sample_dashboard: Dict[str, Any]) -> None:
    dashboard_obj = sample_dashboard["dashboard"]
    result = dashboard._evaluate_json_path(dashboard_obj, "panels[0].title")
    assert result == "CPU"
    panel_ids = dashboard._evaluate_json_path(dashboard_obj, "panels[*].id")
    assert panel_ids == [1, 2]


def test_build_summary(sample_dashboard: Dict[str, Any]) -> None:
    summary = dashboard._build_summary("uid123", sample_dashboard["dashboard"], sample_dashboard["meta"])
    assert summary["uid"] == "uid123"
    assert summary["panelCount"] == 2
    assert summary["variables"][0]["name"] == "env"


class DummyDashboardClient:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = deepcopy(payload)
        self.post_calls: list[tuple[str, Dict[str, Any], Dict[str, Any]]] = []
        self.get_calls: List[str] = []

    async def get_json(self, path: str) -> Dict[str, Any]:
        self.get_calls.append(path)
        return deepcopy(self.payload)

    async def post_json(
        self,
        path: str,
        json: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.post_calls.append((path, json, {"params": params, "headers": headers}))
        return {"status": "ok"}


@pytest.fixture
def dashboard_tools(monkeypatch: pytest.MonkeyPatch, sample_dashboard: Dict[str, Any]) -> tuple[Dict[str, Any], DummyDashboardClient, SimpleNamespace]:
    client = DummyDashboardClient(sample_dashboard)
    config = SimpleNamespace()
    monkeypatch.setattr(dashboard, "get_grafana_config", lambda _: config)
    monkeypatch.setattr(dashboard, "GrafanaClient", lambda cfg: client)
    ctx = SimpleNamespace(request_context=SimpleNamespace(session=SimpleNamespace()))
    app = FastMCP()
    dashboard.register(app)
    tool_map = {tool.name: tool for tool in asyncio.run(app.list_tools())}
    return tool_map, client, ctx


def test_update_dashboard_with_patches(monkeypatch: pytest.MonkeyPatch, sample_dashboard: Dict[str, Any]) -> None:
    captured: Dict[str, Any] = {}

    async def fake_get(ctx: Any, uid: str, *, use_cache: bool = True) -> Dict[str, Any]:
        return deepcopy(sample_dashboard)

    async def fake_post(
        ctx: Any,
        dashboard_json: Dict[str, Any],
        folder: str | None,
        message: str | None,
        overwrite: bool,
        user_id: int | None,
    ) -> Dict[str, Any]:
        captured["dashboard"] = dashboard_json
        captured["folder"] = folder
        captured["message"] = message
        captured["overwrite"] = overwrite
        captured["user_id"] = user_id
        return {"status": "ok"}

    monkeypatch.setattr(dashboard, "_get_dashboard", fake_get)
    monkeypatch.setattr(dashboard, "_post_dashboard", fake_post)

    ctx = SimpleNamespace(request_context=SimpleNamespace(session=SimpleNamespace()))
    operations = [
        {"op": "replace", "path": "title", "value": "Updated"},
        {"op": "add", "path": "panels/-", "value": {"id": 3}},
        {"op": "remove", "path": "description"},
    ]

    result = asyncio.run(
        dashboard._update_dashboard_with_patches(
            ctx,
            "uid123",
            operations,
            folder_uid=None,
            message="msg",
            user_id=7,
        )
    )
    assert result == {"status": "ok"}
    assert captured["dashboard"]["title"] == "Updated"
    assert len(captured["dashboard"]["panels"]) == 3
    assert captured["folder"] == "folder"
def test_update_dashboard_full(monkeypatch: pytest.MonkeyPatch, sample_dashboard: Dict[str, Any]) -> None:
    captured: Dict[str, Any] = {}

    async def fake_post(
        ctx: Any,
        dashboard_json: Dict[str, Any],
        folder: str | None,
        message: str | None,
        overwrite: bool,
        user_id: int | None,
    ) -> Dict[str, Any]:
        captured["dashboard"] = dashboard_json
        captured["folder"] = folder
        captured["overwrite"] = overwrite
        return {"status": "ok"}

    monkeypatch.setattr(dashboard, "_post_dashboard", fake_post)
    ctx = SimpleNamespace(request_context=SimpleNamespace(session=SimpleNamespace()))
    result = asyncio.run(
        dashboard._update_dashboard(
            ctx,
            sample_dashboard["dashboard"],
            None,
            None,
            folder_uid="custom",
            message=None,
            overwrite=True,
            user_id=None,
        )
    )
    assert result == {"status": "ok"}
    assert captured["folder"] == "custom"

    with pytest.raises(ValueError):
        asyncio.run(dashboard._update_dashboard(ctx, None, None, None, None, None, False, None))


def test_get_panel_queries(sample_dashboard: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(ctx: Any, uid: str, *, use_cache: bool = True) -> Dict[str, Any]:
        return sample_dashboard

    monkeypatch.setattr(dashboard, "_get_dashboard", fake_get)
    ctx = SimpleNamespace(request_context=SimpleNamespace(session=SimpleNamespace()))
    queries = asyncio.run(dashboard._get_panel_queries(ctx, "uid123"))
    assert queries[0]["datasource"]["uid"] == "ds1"


def test_dashboard_tools_require_context() -> None:
    app = FastMCP()
    dashboard.register(app)

    async def gather() -> List[str]:
        tools = await app.list_tools()
        return [tool.name for tool in tools]

    tool_names = asyncio.run(gather())
    assert "get_dashboard_by_uid" in tool_names
    tool_map = {tool.name: tool for tool in asyncio.run(app.list_tools())}
    with pytest.raises(ValueError):
        asyncio.run(tool_map["get_dashboard_by_uid"].function(uid="uid", ctx=None))


def test_dashboard_tool_functions_execute(dashboard_tools: tuple[Dict[str, Any], DummyDashboardClient, SimpleNamespace]) -> None:
    tools, client, ctx = dashboard_tools
    result = asyncio.run(tools["get_dashboard_by_uid"].function(uid="abc", ctx=ctx))
    assert result["dashboard"]["title"] == "Example"

    update_result = asyncio.run(
        tools["update_dashboard"].function(
            dashboard={"title": "New", "panels": []},
            ctx=ctx,
        )
    )
    assert update_result == {"status": "ok"}

    summary = asyncio.run(tools["get_dashboard_summary"].function(uid="abc", ctx=ctx))
    assert summary["panelCount"] == 2

    property_value = asyncio.run(tools["get_dashboard_property"].function(uid="abc", jsonPath="panels[0].title", ctx=ctx))
    assert property_value == "CPU"

    queries = asyncio.run(tools["get_dashboard_panel_queries"].function(uid="abc", ctx=ctx))
    assert queries[0]["query"] == "sum(rate(http_requests_total[5m]))"

    operations = [{"op": "replace", "path": "title", "value": "Updated"}]
    asyncio.run(
        tools["update_dashboard"].function(
            uid="abc",
            operations=operations,
            ctx=ctx,
        )
    )
    assert client.post_calls


def test_dashboard_cache_reuse(dashboard_tools: tuple[Dict[str, Any], DummyDashboardClient, SimpleNamespace]) -> None:
    tools, client, ctx = dashboard_tools
    asyncio.run(tools["get_dashboard_by_uid"].function(uid="abc", ctx=ctx))
    initial_fetches = len(client.get_calls)
    asyncio.run(tools["get_dashboard_summary"].function(uid="abc", ctx=ctx))
    assert len(client.get_calls) == initial_fetches

    asyncio.run(tools["get_dashboard_by_uid"].function(uid="abc", forceRefresh=True, ctx=ctx))
    assert len(client.get_calls) == initial_fetches + 1
