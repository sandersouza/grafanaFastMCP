"""Tests for Grafana capability detection used during tool registration."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.config import GrafanaConfig
from app.tools import availability


class DummyGrafanaClient:
    def __init__(self, config: GrafanaConfig) -> None:
        self.config = config
        self.calls: list[str] = []

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self.calls.append(path)
        if path == "/datasources":
            return [
                {"type": "loki"},
                {"type": "Prometheus"},
                {"type": None},
                {"missing": True},
            ]
        if path == "/plugins":
            return [
                {"id": "grafana-ml-app"},
                {"id": "Grafana-IRM-App"},
                {"id": None},
            ]
        raise AssertionError(f"Unexpected path requested: {path}")


def test_detect_capabilities_normalizes_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(availability, "GrafanaClient", DummyGrafanaClient)

    config = GrafanaConfig(url="https://grafana.example.com")
    capabilities = availability.detect_capabilities(config)

    assert capabilities.has_datasource_type("LOKI")
    assert capabilities.has_datasource_type("prometheus")
    assert not capabilities.has_datasource_type("pyroscope")

    assert capabilities.has_plugin("grafana-ml-app")
    assert capabilities.has_plugin("grafana-irm-app")
    assert not capabilities.has_plugin("grafana-asserts-app")


def test_detect_capabilities_handles_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_collect(config: GrafanaConfig) -> availability.GrafanaCapabilities:
        calls.append("collect")
        return availability.GrafanaCapabilities()

    monkeypatch.setattr(availability, "_collect_capabilities", fake_collect)

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        capabilities = availability.detect_capabilities(GrafanaConfig())
    finally:
        asyncio.set_event_loop(None)
        loop.close()

    assert isinstance(capabilities, availability.GrafanaCapabilities)
    assert calls == ["collect"]
