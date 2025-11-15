"""Unit tests for the configuration helpers."""

import base64
import pytest

from app import config


ENV_VARS = [
    config.GRAFANA_URL_ENV,
    config.GRAFANA_SERVICE_ACCOUNT_ENV,
    config.GRAFANA_API_KEY_ENV,
    config.GRAFANA_USERNAME_ENV,
    config.GRAFANA_PASSWORD_ENV,
    config.GRAFANA_ACCESS_TOKEN_ENV,
    config.GRAFANA_ID_TOKEN_ENV,
]


@pytest.fixture(autouse=True)
def clear_grafana_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each test starts with a clean environment."""

    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_config_defaults_from_env() -> None:
    config_from_env = config.grafana_config_from_env()

    assert config_from_env.url == config.DEFAULT_GRAFANA_URL
    assert config_from_env.api_key == ""
    assert config_from_env.basic_auth is None
    assert config_from_env.access_token == ""
    assert config_from_env.id_token == ""


def test_config_env_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.GRAFANA_URL_ENV, "https://grafana.example.com/")
    monkeypatch.setenv(config.GRAFANA_SERVICE_ACCOUNT_ENV, "env-token")
    monkeypatch.setenv(config.GRAFANA_USERNAME_ENV, "grafana-user")
    monkeypatch.setenv(config.GRAFANA_PASSWORD_ENV, "secret")
    monkeypatch.setenv(config.GRAFANA_ACCESS_TOKEN_ENV, "access-token")
    monkeypatch.setenv(config.GRAFANA_ID_TOKEN_ENV, "id-token")

    config_from_env = config.grafana_config_from_env()

    assert config_from_env.url == "https://grafana.example.com"
    assert config_from_env.api_key == "env-token"
    assert config_from_env.basic_auth == ("grafana-user", "secret")
    assert config_from_env.access_token == "access-token"
    assert config_from_env.id_token == "id-token"


def test_headers_override_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.GRAFANA_URL_ENV, "http://env-url:3000")
    monkeypatch.setenv(config.GRAFANA_SERVICE_ACCOUNT_ENV, "env-token")

    basic_auth = base64.b64encode(b"header-user:header-pass").decode()
    headers = {
        "X-Grafana-Url": "https://grafana-header.example.com/",
        "X-Grafana-Api-Key": "header-token",
        "Authorization": f"Basic {basic_auth}",
        "X-Access-Token": "header-access",
        "X-Grafana-Id": "header-id",
    }

    config_from_headers = config.grafana_config_from_headers(headers)

    assert config_from_headers.url == "https://grafana-header.example.com"
    assert config_from_headers.api_key == "header-token"
    assert config_from_headers.basic_auth == ("header-user", "header-pass")
    assert config_from_headers.access_token == "header-access"
    assert config_from_headers.id_token == "header-id"


def test_headers_fallback_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.GRAFANA_URL_ENV, "http://env-url:3000")
    monkeypatch.setenv(config.GRAFANA_SERVICE_ACCOUNT_ENV, "env-token")
    monkeypatch.setenv(config.GRAFANA_ACCESS_TOKEN_ENV, "env-access-token")

    headers = {"Authorization": "Bearer bearer-token"}

    config_from_headers = config.grafana_config_from_headers(headers)

    assert config_from_headers.url == "http://env-url:3000"
    assert config_from_headers.api_key == "env-token"
    # Como há access token configurado no ambiente, ele tem prioridade
    assert config_from_headers.access_token == "env-access-token"
    assert config_from_headers.basic_auth is None


def test_headers_use_bearer_when_env_missing(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.GRAFANA_SERVICE_ACCOUNT_ENV, "env-token")

    headers = {"Authorization": "Bearer bearer-token"}

    config_from_headers = config.grafana_config_from_headers(headers)

    assert config_from_headers.api_key == "env-token"
    assert config_from_headers.access_token == "bearer-token"
