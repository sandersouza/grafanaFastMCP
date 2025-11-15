"""HTTP helper for interacting with Grafana's REST API."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping, Optional
from urllib.parse import urljoin, urlparse, urlunparse

import httpx

from . import __version__
from .config import DEFAULT_GRAFANA_URL, GrafanaConfig

LOGGER = logging.getLogger(__name__)

USER_AGENT = f"mcp-grafana-python/{__version__}"
_DEFAULT_TIMEOUT = httpx.Timeout(30.0)


class GrafanaAPIError(RuntimeError):
    """Error raised when the Grafana API returns an unexpected response."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(
            f"Grafana API request failed with status {status_code}: {message}")
        self.status_code = status_code
        self.message = message


def _build_api_base_url(url: str) -> str:
    if not url:
        url = DEFAULT_GRAFANA_URL
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    api_path = f"{path}/api" if path else "/api"
    rebuilt = parsed._replace(path=api_path, params="", query="", fragment="")
    return urlunparse(rebuilt)


@dataclass
class GrafanaClient:
    config: GrafanaConfig
    _base_url: str = field(init=False, repr=False)
    _verify: bool | str = field(init=False, repr=False)
    _cert: Optional[tuple[str, str]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._base_url = _build_api_base_url(self.config.url)
        tls = self.config.tls_config
        if tls is not None:
            self._verify = tls.resolve_verify()
            self._cert = tls.resolve_cert()
        else:
            self._verify = True
            self._cert = None

    def _headers(
            self, extra: Optional[Mapping[str, str]] = None) -> MutableMapping[str, str]:
        headers: MutableMapping[str, str] = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        if self.config.api_key:
            headers.setdefault(
                "Authorization",
                f"Bearer {self.config.api_key}")
        if self.config.access_token and self.config.id_token:
            headers.setdefault("X-Access-Token", self.config.access_token)
            headers.setdefault("X-Grafana-Id", self.config.id_token)
        if extra:
            headers.update(extra)
        return headers

    def _auth(self) -> Optional[httpx.Auth]:
        if self.config.basic_auth:
            username, password = self.config.basic_auth
            return httpx.BasicAuth(username, password)
        return None

    def _absolute_url(self, path: str) -> str:
        # Normalize the incoming path to avoid duplicating the '/api' segment.
        # Callers sometimes pass paths starting with '/api/...' (for example
        # '/api/health'). Since _build_api_base_url already ensures the base
        # URL ends with '/api', strip a leading '/api' from the provided path
        # to prevent requests like '.../api/api/health'.
        path = path or ""
        if path.startswith("/api/"):
            path = path[len("/api/"):]
        elif path == "/api":
            path = ""
        return urljoin(self._base_url + "/", path.lstrip("/"))

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float | httpx.Timeout] = None,
    ) -> httpx.Response:
        url = self._absolute_url(path)
        combined_headers = self._headers(headers)
        LOGGER.debug(
            "Performing Grafana request",
            extra={
                "method": method,
                "url": url})
        # Allow callers to pass a short timeout for quick startup checks.
        if timeout is None:
            client_timeout = _DEFAULT_TIMEOUT
        else:
            client_timeout = timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout)

        async with httpx.AsyncClient(
            timeout=client_timeout,
            verify=self._verify,
            cert=self._cert,
            auth=self._auth(),
        ) as client:
            response = await client.request(
                method,
                url,
                params=params,
                json=json,
                headers=combined_headers,
            )
        if response.status_code >= 400:
            body = response.text
            LOGGER.debug("Grafana API error", extra={
                         "status": response.status_code, "body": body[:512]})
            raise GrafanaAPIError(response.status_code, body)
        return response

    async def get_json(
        self,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float | httpx.Timeout] = None,
    ) -> Any:
        response = await self.request("GET", path, params=params, timeout=timeout)
        return response.json()

    async def post_json(
        self,
        path: str,
        *,
        json: Any,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        response = await self.request("POST", path, params=params, json=json, headers=headers)
        if response.headers.get(
            "content-type",
                "").startswith("application/json"):
            return response.json()
        return response.text

    async def delete(self, path: str, *, params: Optional[Mapping[str, Any]] = None) -> None:
        await self.request("DELETE", path, params=params)


__all__ = ["GrafanaClient", "GrafanaAPIError", "USER_AGENT"]
