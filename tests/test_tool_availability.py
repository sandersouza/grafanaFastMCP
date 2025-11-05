"""Tests for Grafana capability detection used during tool registration."""

from __future__ import annotations

import asyncio
from typing import Any, Iterable

import pytest

from app.config import GrafanaConfig
from app.tools import availability


class DummyGrafanaClient:
    def __init__(self, config: GrafanaConfig) -> None:
        self.config = config
        self.calls: list[str] = []

    async def get_json(self,
                       path: str,
                       params: dict[str,
                                    Any] | None = None) -> Any:
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


def test_detect_capabilities_normalizes_values(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(availability, "GrafanaClient", DummyGrafanaClient)

    config = GrafanaConfig(url="https://grafana.example.com")
    capabilities = availability.detect_capabilities(config)

    assert capabilities.has_datasource_type("LOKI")
    assert capabilities.has_datasource_type("prometheus")
    assert not capabilities.has_datasource_type("pyroscope")

    assert capabilities.has_plugin("grafana-ml-app")
    assert capabilities.has_plugin("grafana-irm-app")
    assert not capabilities.has_plugin("grafana-asserts-app")


def test_detect_capabilities_handles_event_loop(
        monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    collected = False

    async def fake_collect(
            config: GrafanaConfig) -> availability.GrafanaCapabilities:
        nonlocal collected
        collected = True
        return availability.GrafanaCapabilities(
            plugin_ids=frozenset({"fallback"}))

    monkeypatch.setattr(availability, "_collect_capabilities", fake_collect)

    original_run = asyncio.run
    real_new_loop = asyncio.new_event_loop

    def fake_run(coro: object) -> availability.GrafanaCapabilities:
        if hasattr(coro, "close"):
            coro.close()  # type: ignore[attr-defined]
        raise RuntimeError(
            "asyncio.run() cannot be called from a running event loop")

    class DummyLoop:
        def run_until_complete(
                self,
                coro: object) -> availability.GrafanaCapabilities:
            calls.append("loop_run")
            temp_loop = real_new_loop()
            try:
                asyncio.set_event_loop(temp_loop)
                return temp_loop.run_until_complete(
                    coro)  # type: ignore[arg-type]
            finally:
                asyncio.set_event_loop(None)
                temp_loop.close()

        def close(self) -> None:
            calls.append("loop_close")

    monkeypatch.setattr(asyncio, "run", fake_run)
    monkeypatch.setattr(asyncio, "new_event_loop", lambda: DummyLoop())

    capabilities = availability.detect_capabilities(GrafanaConfig())

    assert isinstance(capabilities, availability.GrafanaCapabilities)
    assert capabilities.plugin_ids == frozenset({"fallback"})
    assert collected is True
    assert calls == ["loop_run", "loop_close"]


def test_detect_capabilities_handles_runtime_error(
        monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(coro: object) -> availability.GrafanaCapabilities:
        if hasattr(coro, "close"):
            coro.close()  # type: ignore[attr-defined]
        raise RuntimeError("boom")

    monkeypatch.setattr(asyncio, "run", fake_run)

    capabilities = availability.detect_capabilities(GrafanaConfig())

    assert isinstance(capabilities, availability.GrafanaCapabilities)
    assert not capabilities.datasource_types
    assert not capabilities.plugin_ids


def test_normalize_items_handles_mixed_values() -> None:
    values: Iterable[Any] = [
        " Loki  ",
        "",
        None,
        "Prometheus",
        123,
        "prometheus",  # duplicate after normalization
    ]

    normalized = availability._normalize_items(values)

    assert normalized == frozenset({"loki", "prometheus", "123"})


@pytest.mark.parametrize("payload, expected",
                         [([{"type": "Loki"},
                            {"type": "  prometheus  "},
                             {"type": None},
                             "ignored"],
                             {"loki",
                              "prometheus"}),
                             ({"datasources": [{"type": "Tempo"}]},
                              {"tempo"}),
                             ({"items": [{"type": "Zipkin"}]},
                              {"zipkin"}),
                             ({"unexpected": True},
                              set()),
                             ("not-iterable",
                              set()),
                          ],
                         )
def test_fetch_datasource_types_parses_payloads(
        payload: Any, expected: set[str]) -> None:
    class PayloadClient:
        def __init__(self, value: Any) -> None:
            self.value = value

        async def get_json(
                self, path: str, params: dict[str, Any] | None = None) -> Any:
            assert path == "/datasources"
            return self.value

    client = PayloadClient(payload)
    result = asyncio.run(availability._fetch_datasource_types(
        client))  # type: ignore[arg-type]
    assert result == expected


@pytest.mark.parametrize("payload, expected",
                         [([{"id": "grafana-ml-app"},
                            {"id": " Grafana-IRM-App "},
                             {"id": None},
                             123],
                             {"grafana-ml-app",
                              "grafana-irm-app"}),
                             ({"items": [{"id": "grafana-asserts-app"}]},
                              {"grafana-asserts-app"}),
                             ({"plugins": [{"id": "grafana-pyroscope-app"}]},
                              {"grafana-pyroscope-app"}),
                             ({"unexpected": True},
                              set()),
                             (123,
                              set()),
                          ],
                         )
def test_fetch_plugin_ids_parses_payloads(
        payload: Any, expected: set[str]) -> None:
    class PayloadClient:
        def __init__(self, value: Any) -> None:
            self.value = value

        async def get_json(
                self, path: str, params: dict[str, Any] | None = None) -> Any:
            assert path == "/plugins"
            return self.value

    client = PayloadClient(payload)
    result = asyncio.run(availability._fetch_plugin_ids(
        client))  # type: ignore[arg-type]
    assert result == expected


def test_collect_capabilities_uses_grafana_client(
        monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class DummyClient:
        def __init__(self, config: GrafanaConfig) -> None:
            self.config = config

        async def get_json(
                self, path: str, params: dict[str, Any] | None = None) -> Any:
            calls.append(path)
            if path == "/datasources":
                return [{"type": "Loki"}]
            if path == "/plugins":
                return [{"id": "grafana-ml-app"}]
            raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(availability, "GrafanaClient", DummyClient)

    config = GrafanaConfig(url="https://grafana.example.com")
    capabilities = availability.detect_capabilities(config)

    assert calls == ["/datasources", "/plugins"]
    assert capabilities.datasource_types == frozenset({"loki"})
    assert capabilities.plugin_ids == frozenset({"grafana-ml-app"})
