"""Tests for Grafana configuration resolution within request context."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from app import context
from app.config import GrafanaConfig


def _make_context(request: object | None) -> SimpleNamespace:
    return SimpleNamespace(
        request_context=SimpleNamespace(
            session=SimpleNamespace(),
            request=request,
        )
    )


def test_get_config_without_request_uses_environment(
        monkeypatch: pytest.MonkeyPatch) -> None:
    env_calls = 0

    def fake_env() -> GrafanaConfig:
        nonlocal env_calls
        env_calls += 1
        return GrafanaConfig(api_key="env")

    monkeypatch.setattr(context, "grafana_config_from_env", fake_env)
    monkeypatch.setattr(
        context,
        "grafana_config_from_headers",
        lambda _: GrafanaConfig(
            api_key="header"))

    ctx = _make_context(request=None)

    result = context.get_grafana_config(ctx)
    again = context.get_grafana_config(ctx)

    assert result is again
    assert result.api_key == "env"
    assert env_calls == 1


def test_get_config_when_request_attribute_missing(
        monkeypatch: pytest.MonkeyPatch) -> None:
    env_calls = 0

    def fake_env() -> GrafanaConfig:
        nonlocal env_calls
        env_calls += 1
        return GrafanaConfig(api_key="env")

    monkeypatch.setattr(context, "grafana_config_from_env", fake_env)
    monkeypatch.setattr(
        context,
        "grafana_config_from_headers",
        lambda _: GrafanaConfig(
            api_key="header"))

    ctx = SimpleNamespace(
        request_context=SimpleNamespace(
            session=SimpleNamespace()))

    result = context.get_grafana_config(ctx)
    again = context.get_grafana_config(ctx)

    assert result is again
    assert result.api_key == "env"
    assert env_calls == 1


def test_get_config_prefers_header_values(
        monkeypatch: pytest.MonkeyPatch) -> None:
    header_config = GrafanaConfig(api_key="header", url="https://headers")

    def fake_headers(headers: dict[str, str]) -> GrafanaConfig:
        assert headers == {"x-test": "value"}
        return header_config

    monkeypatch.setattr(
        context,
        "grafana_config_from_env",
        lambda: GrafanaConfig(
            api_key="env"))
    monkeypatch.setattr(context, "grafana_config_from_headers", fake_headers)

    request = SimpleNamespace(headers={"x-test": "value"})
    ctx = _make_context(request)

    assert context.get_grafana_config(ctx) is header_config


def test_get_config_falls_back_to_env_when_api_key_missing(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    env_config = GrafanaConfig(api_key="env", url="https://env")

    env_calls = 0

    def fake_env() -> GrafanaConfig:
        nonlocal env_calls
        env_calls += 1
        return env_config

    monkeypatch.setattr(context, "grafana_config_from_env", fake_env)
    monkeypatch.setattr(
        context,
        "grafana_config_from_headers",
        lambda _: GrafanaConfig(
            api_key=""))

    request = SimpleNamespace(headers={})
    ctx = _make_context(request)

    caplog.set_level(logging.WARNING)

    result = context.get_grafana_config(ctx)
    again = context.get_grafana_config(ctx)

    assert result is env_config
    assert again is env_config
    assert env_calls == 1
    assert "defaulting to environment settings" in caplog.text
