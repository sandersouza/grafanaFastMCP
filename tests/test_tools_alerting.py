"""Tests for Grafana alerting helper functions."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, Iterable

import pytest

from app.grafana_client import GrafanaAPIError
from app.tools import alerting
from app.tools._label_matching import LabelMatcher
from mcp.server.fastmcp import FastMCP


class DummyClient:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.responses: Dict[str, Any] = {}
        self.calls: list[tuple[str, Any]] = []

    async def get_json(self, path: str, params: Any = None) -> Any:
        self.calls.append((path, params))
        if path in self.responses:
            result = self.responses[path]
            if isinstance(result, Exception):
                raise result
            return result
        return self.responses.get(path)


@pytest.fixture
def ctx(
        monkeypatch: pytest.MonkeyPatch) -> tuple[SimpleNamespace, DummyClient]:
    config = SimpleNamespace(url="https://grafana.local")
    client = DummyClient()
    monkeypatch.setattr(alerting, "get_grafana_config", lambda _: config)
    monkeypatch.setattr(alerting, "GrafanaClient", lambda cfg: client)
    ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            session=SimpleNamespace(),
            request=None))
    return ctx, client


def test_parse_label_matchers_and_selectors() -> None:
    raw_filters = [
        {"name": "job", "value": "api", "type": "="},
        {"name": "env", "value": "prod", "type": "!="},
    ]
    matchers = alerting._parse_label_matchers(raw_filters)
    assert len(matchers) == 2
    selectors = alerting._parse_label_selectors([{"filters": raw_filters}])
    assert len(selectors) == 1
    assert selectors[0].matches({"job": "api", "env": "stage"}) is True

    with pytest.raises(ValueError):
        alerting._parse_label_matchers([{"name": "", "value": "x"}])
    with pytest.raises(ValueError):
        alerting._parse_label_selectors([{"filters": "invalid"}])


def test_fetch_alert_rules_and_filtering(
        ctx: tuple[SimpleNamespace, DummyClient]) -> None:
    ctx_obj, client = ctx
    client.responses["/prometheus/grafana/api/v1/rules"] = {
        "data": {
            "groups": [
                {
                    "rules": [
                        {"uid": "1", "name": "Rule A", "state": "ok", "labels": {"job": "api"}},
                        {"uid": "2", "name": "Rule B", "state": "ok", "labels": {"job": "worker"}},
                    ]
                }
            ]
        }
    }
    selectors = [LabelMatcher(name="job", value="api")]
    rules = asyncio.run(alerting._fetch_alert_rules(client))
    filtered = alerting._filter_rules_by_selectors(
        rules, [alerting.Selector(selectors)])
    assert filtered == [rules[0]]

    paged = alerting._apply_pagination(filtered, limit=1, page=1)
    assert len(paged) == 1
    with pytest.raises(ValueError):
        alerting._apply_pagination(filtered, limit=-5, page=1)

    summarized = [alerting._summarize_alert_rule(rule) for rule in filtered]
    assert summarized[0]["uid"] == "1"

    listing = asyncio.run(alerting._list_alert_rules(ctx_obj, limit=1, page=1, label_selectors=[
                          {"filters": [{"name": "job", "value": "api"}]}]))
    assert listing[0]["title"] == "Rule A"


def test_get_alert_rule_handles_404(
        monkeypatch: pytest.MonkeyPatch, ctx: tuple[SimpleNamespace, DummyClient]) -> None:
    ctx_obj, client = ctx
    client.responses["/v1/provisioning/alert-rules/rule"] = GrafanaAPIError(
        404, "not found")
    with pytest.raises(ValueError):
        asyncio.run(alerting._get_alert_rule(ctx_obj, "rule"))


def test_list_contact_points_and_validation(
        ctx: tuple[SimpleNamespace, DummyClient]) -> None:
    ctx_obj, client = ctx
    client.responses["/v1/provisioning/contact-points"] = [
        {"uid": "1", "name": "Email", "type": "email"},
        {"uid": "2", "name": "Pager", "type": "pagerduty"},
    ]
    result = asyncio.run(
        alerting._list_contact_points(
            ctx_obj, limit=1, name="Email"))
    assert result == [{"uid": "1", "name": "Email", "type": "email"}]
    with pytest.raises(ValueError):
        asyncio.run(
            alerting._list_contact_points(
                ctx_obj,
                limit=-1,
                name=None))


def test_alerting_tools_require_context() -> None:
    app = FastMCP()
    alerting.register(app)
    tools = asyncio.run(app.list_tools())
    no_ctx_tool = next(
        tool for tool in tools if tool.name == "list_alert_rules")
    with pytest.raises(ValueError):
        asyncio.run(no_ctx_tool.function(ctx=None))
