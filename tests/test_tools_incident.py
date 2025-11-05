"""Tests for Grafana incident management helpers."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from app.grafana_client import GrafanaAPIError
from app.tools import incident
from mcp.server.fastmcp import FastMCP


class DummyClient:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.calls: list[tuple[str, Dict[str, Any]]] = []
        self.response: Dict[str, Any] = {"ok": True}

    async def post_json(
            self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append((path, json))
        return self.response


@pytest.fixture
def ctx(
        monkeypatch: pytest.MonkeyPatch) -> tuple[SimpleNamespace, DummyClient]:
    config = SimpleNamespace(url="https://grafana.local")
    client = DummyClient()
    monkeypatch.setattr(incident, "get_grafana_config", lambda _: config)
    monkeypatch.setattr(incident, "GrafanaClient", lambda cfg: client)
    ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            session=SimpleNamespace(),
            request=None))
    return ctx, client


def test_build_query_string_handles_flags() -> None:
    assert incident._build_query_string(False, None) == "isdrill:false"
    assert incident._build_query_string(True, "open") == "status:open"
    assert incident._build_query_string(
        False, "closed") == "isdrill:false status:closed"


def test_list_incidents_builds_payload(
        ctx: tuple[SimpleNamespace, DummyClient]) -> None:
    ctx_obj, client = ctx
    result = asyncio.run(
        incident._list_incidents(
            ctx_obj,
            limit=5,
            include_drill=False,
            status="open"))
    assert result == {"ok": True}
    path, payload = client.calls[0]
    assert path.endswith("QueryIncidentPreviews")
    assert payload["query"]["limit"] == 5
    assert "status:open" in payload["query"]["queryString"]

    asyncio.run(
        incident._list_incidents(
            ctx_obj,
            limit=-1,
            include_drill=True,
            status=None))
    assert client.calls[-1][1]["query"]["limit"] == 10


def test_create_incident_and_add_activity(
        ctx: tuple[SimpleNamespace, DummyClient]) -> None:
    ctx_obj, client = ctx
    asyncio.run(
        incident._create_incident(
            ctx_obj,
            {
                "title": "Outage",
                "severity": "high",
                "roomPrefix": "inc",
                "isDrill": True,
                "status": "open",
                "attachCaption": "More info",
                "attachUrl": "https://example.com",
                "labels": [{"key": "value"}],
            },
        )
    )
    asyncio.run(
        incident._add_activity(
            ctx_obj,
            {"incidentId": "123", "body": "Update", "eventTime": "now"},
        )
    )
    paths = [call[0] for call in client.calls]
    assert paths == [
        "/plugins/grafana-irm-app/resources/api/v1/IncidentsService.CreateIncident",
        "/plugins/grafana-irm-app/resources/api/v1/ActivityService.AddActivity",
    ]


def test_get_incident_handles_errors(
        monkeypatch: pytest.MonkeyPatch, ctx: tuple[SimpleNamespace, DummyClient]) -> None:
    ctx_obj, client = ctx
    asyncio.run(incident._get_incident(ctx_obj, "42"))
    path, payload = client.calls[-1]
    assert path.endswith("GetIncident")
    assert payload == {"incidentID": "42"}

    app = FastMCP()
    incident.register(app)
    tools = asyncio.run(app.list_tools())
    get_tool = next(tool for tool in tools if tool.name == "get_incident")

    def raise_not_found(*_: Any, **__: Any) -> Dict[str, Any]:
        raise GrafanaAPIError(404, "not found")

    monkeypatch.setattr(incident, "_get_incident", raise_not_found)
    with pytest.raises(ValueError):
        asyncio.run(get_tool.function(incidentId="999", ctx=ctx_obj))
