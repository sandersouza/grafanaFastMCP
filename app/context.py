"""Context helpers for retrieving Grafana configuration per request."""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping

from mcp.server.fastmcp import Context
from starlette.requests import Request

from .config import GrafanaConfig, grafana_config_from_env, grafana_config_from_headers

LOGGER = logging.getLogger(__name__)

_SESSION_STATE_KEY = "_grafana_python_state"
_CONFIG_KEY = "grafana_config"


def _session_state(ctx: Context) -> Dict[str, Any]:
    session = ctx.request_context.session
    state = getattr(session, _SESSION_STATE_KEY, None)
    if state is None:
        state = {}
        setattr(session, _SESSION_STATE_KEY, state)
    return state


def _request_headers(request: Request | None) -> Mapping[str, str]:
    if request is None:
        return {}
    # Starlette Headers behave like a Mapping[str, str]
    return dict(request.headers)


def _build_config(ctx: Context) -> GrafanaConfig:
    request = getattr(ctx.request_context, "request", None)
    if request is None:
        LOGGER.debug(
            "No HTTP request available in context; using environment configuration only")
        return grafana_config_from_env()

    headers = _request_headers(request)
    config = grafana_config_from_headers(headers)
    if not config.api_key:
        LOGGER.warning(
            "Grafana API key missing after header merge; defaulting to environment settings")
        config = grafana_config_from_env()
    LOGGER.debug(
        "Resolved Grafana configuration",
        extra={
            "url": config.url,
            "api_key_set": bool(config.api_key),
            "basic_auth": bool(config.basic_auth),
            "access_token": bool(config.access_token),
            "id_token": bool(config.id_token),
        },
    )
    return config


def get_grafana_config(ctx: Context) -> GrafanaConfig:
    """Retrieve the Grafana configuration for the current request."""

    state = _session_state(ctx)
    config = state.get(_CONFIG_KEY)
    if isinstance(config, GrafanaConfig):
        return config

    config = _build_config(ctx)
    state[_CONFIG_KEY] = config
    return config


__all__ = ["get_grafana_config"]
