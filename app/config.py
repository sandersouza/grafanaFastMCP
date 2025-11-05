"""Configuration helpers for the Python Grafana FastMCP server."""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from typing import Mapping, MutableMapping, Optional, Tuple

LOGGER = logging.getLogger(__name__)

DEFAULT_GRAFANA_URL = "http://localhost:3000"

GRAFANA_URL_ENV = "GRAFANA_URL"
GRAFANA_SERVICE_ACCOUNT_ENV = "GRAFANA_SERVICE_ACCOUNT_TOKEN"
GRAFANA_API_KEY_ENV = "GRAFANA_API_KEY"
GRAFANA_USERNAME_ENV = "GRAFANA_USERNAME"
GRAFANA_PASSWORD_ENV = "GRAFANA_PASSWORD"
GRAFANA_ACCESS_TOKEN_ENV = "GRAFANA_ACCESS_TOKEN"
GRAFANA_ID_TOKEN_ENV = "GRAFANA_ID_TOKEN"
GRAFANA_TLS_CERT_FILE_ENV = "GRAFANA_TLS_CERT_FILE"
GRAFANA_TLS_KEY_FILE_ENV = "GRAFANA_TLS_KEY_FILE"
GRAFANA_TLS_CA_FILE_ENV = "GRAFANA_TLS_CA_FILE"
GRAFANA_TLS_SKIP_VERIFY_ENV = "GRAFANA_TLS_SKIP_VERIFY"

GRAFANA_URL_HEADER = "x-grafana-url"
GRAFANA_API_KEY_HEADER = "x-grafana-api-key"
GRAFANA_ID_HEADER = "x-grafana-id"
GRAFANA_ACCESS_TOKEN_HEADER = "x-access-token"
AUTHORIZATION_HEADER = "authorization"


@dataclass
class TLSConfig:
    """Subset of TLS configuration supported by the Go implementation."""

    cert_file: str = ""
    key_file: str = ""
    ca_file: str = ""
    skip_verify: bool = False

    def resolve_verify(self) -> bool | str:
        if self.skip_verify:
            return False
        if self.ca_file:
            return self.ca_file
        return True

    def resolve_cert(self) -> Optional[Tuple[str, str]]:
        if self.cert_file and self.key_file:
            return (self.cert_file, self.key_file)
        return None


@dataclass
class GrafanaConfig:
    """Represents per-request Grafana configuration."""

    url: str = DEFAULT_GRAFANA_URL
    api_key: str = ""
    basic_auth: Optional[Tuple[str, str]] = None
    access_token: str = ""
    id_token: str = ""
    debug: bool = False
    include_arguments_in_spans: bool = False
    tls_config: Optional[TLSConfig] = None


def _sanitize_url(url: str) -> str:
    return url.rstrip("/")


def _url_and_api_key_from_env() -> Tuple[str, str]:
    url = os.getenv(GRAFANA_URL_ENV, "").strip()
    url = _sanitize_url(url) if url else ""

    api_key = os.getenv(GRAFANA_SERVICE_ACCOUNT_ENV, "").strip()
    if not api_key:
        legacy_key = os.getenv(GRAFANA_API_KEY_ENV, "").strip()
        if legacy_key:
            LOGGER.warning(
                "GRAFANA_API_KEY is deprecated, please use GRAFANA_SERVICE_ACCOUNT_TOKEN instead."
            )
            api_key = legacy_key
    LOGGER.debug(
        "Environment configuration read",
        extra={
            "url": url or DEFAULT_GRAFANA_URL,
            "service_account_token": bool(api_key),
        },
    )
    return url, api_key


def _basic_auth_from_env() -> Optional[Tuple[str, str]]:
    username = os.getenv(GRAFANA_USERNAME_ENV, "")
    password = os.getenv(GRAFANA_PASSWORD_ENV)
    if username and password is not None:
        return username, password
    if username and password is None:
        return (username, "")
    return None


def grafana_config_from_env() -> GrafanaConfig:
    url, api_key = _url_and_api_key_from_env()
    basic_auth = _basic_auth_from_env()
    access_token = os.getenv(GRAFANA_ACCESS_TOKEN_ENV, "").strip()
    id_token = os.getenv(GRAFANA_ID_TOKEN_ENV, "").strip()
    config = GrafanaConfig(
        url=url or DEFAULT_GRAFANA_URL,
        api_key=api_key,
        basic_auth=basic_auth,
        access_token=access_token,
        id_token=id_token,
    )
    # TLS configuration from environment
    cert_file = os.getenv(GRAFANA_TLS_CERT_FILE_ENV, "").strip()
    key_file = os.getenv(GRAFANA_TLS_KEY_FILE_ENV, "").strip()
    ca_file = os.getenv(GRAFANA_TLS_CA_FILE_ENV, "").strip()
    skip_verify_raw = os.getenv(GRAFANA_TLS_SKIP_VERIFY_ENV, "").strip().lower()
    skip_verify = False
    if skip_verify_raw in ("1", "true", "yes", "on"):
        skip_verify = True
    if cert_file or key_file or ca_file or skip_verify:
        config.tls_config = TLSConfig(
            cert_file=cert_file,
            key_file=key_file,
            ca_file=ca_file,
            skip_verify=skip_verify,
        )
    LOGGER.debug(
        "Final GrafanaConfig from environment",
        extra={
            "url": config.url,
            "api_key": bool(config.api_key),
            "basic_auth": bool(config.basic_auth),
            "access_token": bool(config.access_token),
            "id_token": bool(config.id_token),
        },
    )
    return config


def _decode_basic_auth(value: str) -> Optional[Tuple[str, str]]:
    try:
        decoded = base64.b64decode(value).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    if ":" not in decoded:
        return None
    username, password = decoded.split(":", 1)
    return username, password


def _extract_basic_auth(
        headers: Mapping[str, str]) -> Optional[Tuple[str, str]]:
    auth = headers.get(AUTHORIZATION_HEADER)
    if not auth:
        return None
    if auth.lower().startswith("basic "):
        encoded = auth.split(" ", 1)[1]
        return _decode_basic_auth(encoded)
    return None


def _extract_bearer_token(headers: Mapping[str, str]) -> str:
    auth = headers.get(AUTHORIZATION_HEADER, "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return ""


def grafana_config_from_headers(headers: Mapping[str, str]) -> GrafanaConfig:
    env_config = grafana_config_from_env()
    lowered: MutableMapping[str, str] = {
        k.lower(): v for k, v in headers.items()}

    url = lowered.get(GRAFANA_URL_HEADER, env_config.url)
    url = _sanitize_url(url) if url else env_config.url

    api_key = lowered.get(
        GRAFANA_API_KEY_HEADER,
        "").strip() or env_config.api_key

    basic_auth = _extract_basic_auth(lowered) or env_config.basic_auth

    access_token = lowered.get(GRAFANA_ACCESS_TOKEN_HEADER, "").strip()
    if not access_token:
        access_token = env_config.access_token or _extract_bearer_token(
            lowered)

    id_token = lowered.get(
        GRAFANA_ID_HEADER,
        "").strip() or env_config.id_token

    return GrafanaConfig(
        url=url or DEFAULT_GRAFANA_URL,
        api_key=api_key,
        basic_auth=basic_auth,
        access_token=access_token,
        id_token=id_token,
        debug=env_config.debug,
        include_arguments_in_spans=env_config.include_arguments_in_spans,
        tls_config=env_config.tls_config,
    )


__all__ = [
    "GrafanaConfig",
    "TLSConfig",
    "DEFAULT_GRAFANA_URL",
    "grafana_config_from_env",
    "grafana_config_from_headers",
]
