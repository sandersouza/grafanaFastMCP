"""Tests for the Grafana HTTP client helper."""

from __future__ import annotations

import pytest

from app import grafana_client
from app.config import GrafanaConfig, TLSConfig


class DummyResponse:
    def __init__(self,
                 *,
                 status_code: int = 200,
                 text: str = "",
                 headers: dict[str,
                               str] | None = None,
                 json_data: object = None) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self._json_data = json_data if json_data is not None else {}

    def json(self) -> object:
        return self._json_data


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://grafana.example", "https://grafana.example/api"),
        ("https://grafana.example/", "https://grafana.example/api"),
        ("https://grafana.example/sub", "https://grafana.example/sub/api"),
        ("", "http://localhost:3000/api"),
    ],
)
def test_build_api_base_url(url: str, expected: str) -> None:
    assert grafana_client._build_api_base_url(url) == expected


def test_client_initialization_configures_tls() -> None:
    tls = TLSConfig(cert_file="cert.pem", key_file="key.pem", ca_file="ca.pem")
    config = GrafanaConfig(url="https://grafana.example/sub", tls_config=tls)

    client = grafana_client.GrafanaClient(config)

    assert client._verify == "ca.pem"
    assert client._cert == ("cert.pem", "key.pem")
    assert client._absolute_url(
        "alerts") == "https://grafana.example/sub/api/alerts"


def test_client_headers_include_tokens() -> None:
    config = GrafanaConfig(
        url="https://grafana.example",
        api_key="svc-token",
        access_token="access",
        id_token="id",
    )
    client = grafana_client.GrafanaClient(config)
    headers = client._headers({"X-Test": "value"})

    assert headers["Authorization"] == "Bearer svc-token"
    assert headers["X-Access-Token"] == "access"
    assert headers["X-Grafana-Id"] == "id"
    assert headers["X-Test"] == "value"
    assert headers["User-Agent"].startswith(
        grafana_client.USER_AGENT.split("/")[0])


def test_client_auth_uses_basic_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, tuple[str, str]] = {}

    class FakeBasicAuth:
        def __init__(self, username: str, password: str) -> None:
            captured["credentials"] = (username, password)

    monkeypatch.setattr(grafana_client.httpx, "BasicAuth", FakeBasicAuth)

    config = GrafanaConfig(
        url="https://grafana.example",
        basic_auth=(
            "user",
            "pass"))
    client = grafana_client.GrafanaClient(config)
    auth = client._auth()

    assert isinstance(auth, FakeBasicAuth)
    assert captured["credentials"] == ("user", "pass")


@pytest.mark.anyio("asyncio")
async def test_request_invokes_httpx_client(
        monkeypatch: pytest.MonkeyPatch) -> None:
    tls = TLSConfig(cert_file="cert.pem", key_file="key.pem", ca_file="ca.pem")
    config = GrafanaConfig(
        url="https://grafana.example/base",
        api_key="svc-token",
        basic_auth=("user", "pass"),
        access_token="access",
        id_token="id",
        tls_config=tls,
    )
    client = grafana_client.GrafanaClient(config)

    captured: dict[str, object] = {}
    response = DummyResponse(json_data={"ok": True})

    class DummyAsyncClient:
        def __init__(
                self,
                *,
                timeout: object,
                verify: object,
                cert: object,
                auth: object) -> None:
            captured["init"] = {
                "timeout": timeout,
                "verify": verify,
                "cert": cert,
                "auth": auth,
            }

        async def __aenter__(self) -> "DummyAsyncClient":
            captured["enter"] = True
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            captured["exit"] = True

        async def request(self,
                          method: str,
                          url: str,
                          *,
                          params: object = None,
                          json: object = None,
                          headers: dict[str,
                                        str] | None = None) -> DummyResponse:
            captured["request"] = {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
                "headers": headers,
            }
            return response

    monkeypatch.setattr(grafana_client.httpx, "AsyncClient", DummyAsyncClient)

    result = await client.request("POST", "/path", params={"q": "1"}, json={"body": 1}, headers={"X-Test": "value"})

    assert result is response
    assert captured["init"]["verify"] == "ca.pem"
    assert captured["init"]["cert"] == ("cert.pem", "key.pem")
    assert captured["request"]["url"] == "https://grafana.example/base/api/path"
    assert captured["request"]["headers"]["Authorization"] == "Bearer svc-token"
    assert captured["request"]["headers"]["X-Test"] == "value"


@pytest.mark.anyio("asyncio")
async def test_request_raises_on_error(
        monkeypatch: pytest.MonkeyPatch) -> None:
    client = grafana_client.GrafanaClient(
        GrafanaConfig(url="https://grafana.example"))
    error_response = DummyResponse(status_code=500, text="boom")

    class DummyAsyncClient:
        def __init__(self, **_: object) -> None:
            pass

        async def __aenter__(self) -> "DummyAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            pass

        async def request(self, *_, **__) -> DummyResponse:
            return error_response

    monkeypatch.setattr(grafana_client.httpx, "AsyncClient", DummyAsyncClient)

    with pytest.raises(grafana_client.GrafanaAPIError) as excinfo:
        await client.request("GET", "/fail")

    assert excinfo.value.status_code == 500
    assert "boom" in str(excinfo.value)


@pytest.mark.anyio("asyncio")
async def test_post_json_handles_text_response(
        monkeypatch: pytest.MonkeyPatch) -> None:
    client = grafana_client.GrafanaClient(
        GrafanaConfig(url="https://grafana.example"))

    async def fake_request(self: grafana_client.GrafanaClient, *_: object, **__: object) -> DummyResponse:  # pragma: no cover - helper
        return DummyResponse(
            headers={
                "content-type": "text/plain"},
            text="plain")

    monkeypatch.setattr(grafana_client.GrafanaClient, "request", fake_request)

    result = await client.post_json("/path", json={"value": 1})
    assert result == "plain"


@pytest.mark.anyio("asyncio")
async def test_post_json_returns_parsed_body(
        monkeypatch: pytest.MonkeyPatch) -> None:
    client = grafana_client.GrafanaClient(
        GrafanaConfig(url="https://grafana.example"))

    async def fake_request(self: grafana_client.GrafanaClient, *_: object, **__: object) -> DummyResponse:  # pragma: no cover - helper
        return DummyResponse(
            headers={
                "content-type": "application/json"},
            json_data={
                "ok": True})

    monkeypatch.setattr(grafana_client.GrafanaClient, "request", fake_request)

    result = await client.post_json("/path", json={"value": 1})
    assert result == {"ok": True}


@pytest.mark.anyio("asyncio")
async def test_get_json_returns_parsed_body(
        monkeypatch: pytest.MonkeyPatch) -> None:
    client = grafana_client.GrafanaClient(
        GrafanaConfig(url="https://grafana.example"))

    async def fake_request(self: grafana_client.GrafanaClient, *_: object, **__: object) -> DummyResponse:  # pragma: no cover - helper
        return DummyResponse(json_data={"value": 1})

    monkeypatch.setattr(grafana_client.GrafanaClient, "request", fake_request)

    assert await client.get_json("/path") == {"value": 1}
