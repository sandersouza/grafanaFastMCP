"""Tool registrations for the Python Grafana FastMCP server."""

from __future__ import annotations

import logging
from typing import Callable

from mcp.server.fastmcp import FastMCP

from ..config import grafana_config_from_env
from . import (
    admin,
    alerting,
    asserts,
    dashboard,
    datasources,
    incident,
    loki,
    navigation,
    oncall,
    prometheus,
    pyroscope,
    search,
    sift,
)
from .availability import GrafanaCapabilities, detect_capabilities

__all__ = ["register_all"]

LOGGER = logging.getLogger(__name__)


def _resolve_capabilities() -> GrafanaCapabilities:
    config = grafana_config_from_env()
    return detect_capabilities(config)


def register_all(app: FastMCP) -> None:
    """Register all tool groups with the provided FastMCP application."""

    capabilities = _resolve_capabilities()

    def _register(
        name: str,
        register_func: Callable[[FastMCP], None],
        *,
        supported: bool = True,
        reason: str | None = None,
    ) -> None:
        if supported:
            register_func(app)
            return
        message = reason or "required Grafana capability is not available"
        LOGGER.info("Skipping registration of %s tools: %s", name, message)

    _register("admin", admin.register)
    _register("datasources", datasources.register)
    _register("dashboard", dashboard.register)
    _register("alerting", alerting.register)

    has_irm_plugin = capabilities.has_plugin("grafana-irm-app")

    _register(
        "asserts",
        asserts.register,
        supported=capabilities.has_plugin("grafana-asserts-app"),
        reason="requires the Grafana Asserts plugin (grafana-asserts-app)",
    )
    _register(
        "incident",
        incident.register,
        supported=has_irm_plugin,
        reason="requires the Grafana Incident plugin (grafana-irm-app)",
    )
    _register(
        "loki",
        loki.register,
        supported=capabilities.has_datasource_type("loki"),
        reason="requires a Grafana Loki datasource",
    )
    _register("navigation", navigation.register)
    _register(
        "oncall",
        oncall.register,
        supported=has_irm_plugin,
        reason="requires the Grafana OnCall plugin (grafana-irm-app)",
    )
    _register(
        "prometheus",
        prometheus.register,
        supported=capabilities.has_datasource_type("prometheus"),
        reason="requires a Grafana Prometheus datasource",
    )
    _register(
        "pyroscope",
        pyroscope.register,
        supported=capabilities.has_datasource_type("pyroscope"),
        reason="requires a Grafana Pyroscope datasource",
    )
    _register("search", search.register)
    _register(
        "sift",
        sift.register,
        supported=capabilities.has_plugin("grafana-ml-app"),
        reason="requires the Grafana Machine Learning plugin (grafana-ml-app)",
    )
