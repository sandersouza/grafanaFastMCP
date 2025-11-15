"""Tests for the Grafana FastMCP command line entrypoint."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import __version__
from app import main as main_module


def test_parse_address_accepts_host_and_port() -> None:
    host, port = main_module._parse_address("example.com:1234")
    assert host == "example.com"
    assert port == 1234


@pytest.mark.parametrize("value", ["missing-port", "localhost:not-a-port"])
def test_parse_address_rejects_invalid_values(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        main_module._parse_address(value)


def test_main_prints_version_and_exits(
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    def _unexpected_create_app(**_: object) -> None:
        raise AssertionError("create_app should not be called")

    monkeypatch.setattr(main_module, "create_app", _unexpected_create_app)

    main_module.main(["--version"])

    captured = capsys.readouterr()
    assert captured.out.strip() == __version__


def test_main_runs_server_with_cli_overrides(
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path) -> None:
    env_path = tmp_path / "custom.env"
    env_path.write_text(
        "LOG_LEVEL=warning\nTRANSPORT=sse\nSTREAMABLE_HTTP_PATH=/env\n")

    created: dict[str, object] = {}

    class DummyApp:
        def __init__(self) -> None:
            self.settings = SimpleNamespace(
                sse_path="/sse",
                message_path="/messages/",
                streamable_http_path="/stream",
                mount_path="/mount",
            )
            self.run_calls: list[tuple[str, str | None]] = []

        def run(
                self,
                transport: str,
                *,
                mount_path: str | None = None) -> None:
            self.run_calls.append((transport, mount_path))

    def fake_create_app(**kwargs: object) -> DummyApp:
        created["kwargs"] = kwargs
        app = DummyApp()
        created["app"] = app
        return app

    monkeypatch.setattr(main_module, "create_app", fake_create_app)

    for key in [
        "GRAFANA_URL",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN",
        "GRAFANA_API_KEY",
        "GRAFANA_USERNAME",
        "GRAFANA_PASSWORD",
        "GRAFANA_ACCESS_TOKEN",
        "GRAFANA_ID_TOKEN",
        "ENV_FILE",
        "STREAMABLE_HTTP_PATH",
        "BASE_PATH",
        "APP_ADDRESS",
        "LOG_LEVEL",
        "TRANSPORT",
    ]:
        monkeypatch.delenv(key, raising=False)

    args = [
        "--env-file",
        str(env_path),
        "--address",
        "0.0.0.0:1234",
        "--base-path",
        "/cli-base",
        "--transport",
        "sse",
        "--streamable-http-path",
        "/cli-http",
        "--log-level",
        "warning",
        "--debug",
        "--GRAFANA_URL",
        "http://grafana.local",
        "--GRAFANA_SERVICE_ACCOUNT_TOKEN",
        "svc-token",
        "--GRAFANA_API_KEY",
        "legacy-token",
        "--GRAFANA_USERNAME",
        "user",
        "--GRAFANA_PASSWORD",
        "pass",
        "--GRAFANA_ACCESS_TOKEN",
        "access",
        "--GRAFANA_ID_TOKEN",
        "id",
    ]

    main_module.main(args)

    kwargs = created["kwargs"]
    assert kwargs == {
        "host": "0.0.0.0",
        "port": 1234,
        "base_path": "/cli-base",
        "streamable_http_path": "/cli-http",
        "log_level": "WARNING",
        "debug": True,
    }

    app = created["app"]
    assert isinstance(app, DummyApp)
    assert app.run_calls == [("sse", "/mount")]

    for key, expected in {
        "GRAFANA_URL": "http://grafana.local",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "svc-token",
        "GRAFANA_API_KEY": "legacy-token",
        "GRAFANA_USERNAME": "user",
        "GRAFANA_PASSWORD": "pass",
        "GRAFANA_ACCESS_TOKEN": "access",
        "GRAFANA_ID_TOKEN": "id",
    }.items():
        assert os.environ[key] == expected


def test_main_logs_when_stdio_transport_ignores_base_path(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class DummyApp:
        def __init__(self) -> None:
            self.settings = SimpleNamespace(
                sse_path="/sse",
                message_path="/messages/",
                streamable_http_path="/stream",
                mount_path="/mount",
            )
            self.run_calls: list[tuple[str, str | None]] = []

        def run(
                self,
                transport: str,
                *,
                mount_path: str | None = None) -> None:
            self.run_calls.append((transport, mount_path))

    app = DummyApp()

    monkeypatch.setattr(main_module, "create_app", lambda **kwargs: app)

    for key in [
        "GRAFANA_URL",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN",
        "GRAFANA_API_KEY",
        "GRAFANA_USERNAME",
        "GRAFANA_PASSWORD",
        "GRAFANA_ACCESS_TOKEN",
        "GRAFANA_ID_TOKEN",
        "STREAMABLE_HTTP_PATH",
        "BASE_PATH",
        "APP_ADDRESS",
        "LOG_LEVEL",
        "TRANSPORT",
    ]:
        monkeypatch.delenv(key, raising=False)

    caplog.set_level(logging.INFO)

    main_module.main([
        "--address",
        "localhost:9001",
        "--transport",
        "stdio",
        "--base-path",
        "/ignored",
    ])

    assert app.run_calls == [("stdio", None)]
    assert "Ignoring base path" in caplog.text


def test_main_frozen_defaults_to_stdio(
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path) -> None:
    class DummyApp:
        def __init__(self) -> None:
            self.settings = SimpleNamespace(
                sse_path="/sse",
                message_path="/messages/",
                streamable_http_path="/stream",
                mount_path="/mount",
            )
            self.run_calls: list[tuple[str, str | None]] = []

        def run(
                self,
                transport: str,
                *,
                mount_path: str | None = None) -> None:
            self.run_calls.append((transport, mount_path))

    app = DummyApp()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main_module, "create_app", lambda **kwargs: app)
    monkeypatch.setattr(main_module.sys, "frozen", True, raising=False)

    for key in [
        "GRAFANA_URL",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN",
        "GRAFANA_API_KEY",
        "GRAFANA_USERNAME",
        "GRAFANA_PASSWORD",
        "GRAFANA_ACCESS_TOKEN",
        "GRAFANA_ID_TOKEN",
        "ENV_FILE",
        "STREAMABLE_HTTP_PATH",
        "BASE_PATH",
        "APP_ADDRESS",
        "LOG_LEVEL",
    ]:
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("TRANSPORT", "sse")

    main_module.main([])

    assert app.run_calls == [("stdio", None)]
    assert os.environ["TRANSPORT"] == "stdio"
