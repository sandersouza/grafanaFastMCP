"""Tests for datasource helper functions."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.tools import datasources


class DummyClient:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.payload: Any = []
        self.calls: list[tuple[str, Any]] = []

    async def get_json(self, path: str, params: Any = None) -> Any:
        self.calls.append((path, params))
        return self.payload


@pytest.fixture
def setup_datasources(
        monkeypatch: pytest.MonkeyPatch) -> tuple[SimpleNamespace, DummyClient]:
    config = SimpleNamespace(url="https://grafana.local")
    client = DummyClient()
    monkeypatch.setattr(datasources, "get_grafana_config", lambda _: config)
    monkeypatch.setattr(datasources, "GrafanaClient", lambda cfg: client)
    ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            session=SimpleNamespace(),
            request=None))
    return ctx, client


def test_filter_datasources_matches_type() -> None:
    input_data = [
        {"name": "Prometheus", "type": "prometheus"},
        {"name": "Loki", "type": "loki"},
    ]
    filtered = datasources._filter_datasources(input_data, "prom")
    assert filtered == [input_data[0]]
    assert datasources._filter_datasources(input_data, None) == input_data


def test_list_datasources_returns_summaries(setup_datasources) -> None:
    ctx, client = setup_datasources
    client.payload = [
        {"id": 1, "uid": "a", "name": "A", "type": "prometheus", "isDefault": True},
        {"id": 2, "uid": "b", "name": "B", "type": "loki", "isDefault": False},
    ]
    result = asyncio.run(datasources._list_datasources(ctx, "loki"))
    assert result == [
        {"id": 2, "uid": "b", "name": "B", "type": "loki", "isDefault": False}
    ]
    assert client.calls == [("/datasources", None)]


def test_list_datasources_rejects_unexpected_payload(
        setup_datasources) -> None:
    ctx, client = setup_datasources
    client.payload = {"not": "a list"}
    with pytest.raises(ValueError):
        asyncio.run(datasources._list_datasources(ctx, None))


def test_get_datasource_by_uid_and_name(setup_datasources) -> None:
    ctx, client = setup_datasources
    client.payload = {"uid": "abc"}
    result_uid = asyncio.run(datasources._get_by_uid(ctx, "abc"))
    result_name = asyncio.run(datasources._get_by_name(ctx, "primary"))
    assert result_uid == {"uid": "abc"}
    assert result_name == {"uid": "abc"}
    assert client.calls == [
        ("/datasources/uid/abc", None),
        ("/datasources/name/primary", None),
    ]
