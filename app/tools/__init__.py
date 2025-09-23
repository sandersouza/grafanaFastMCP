"""Tool registrations for the Python Grafana FastMCP server."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

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

__all__ = ["register_all"]


def register_all(app: FastMCP) -> None:
    """Register all tool groups with the provided FastMCP application."""

    admin.register(app)
    datasources.register(app)
    dashboard.register(app)
    alerting.register(app)
    asserts.register(app)
    incident.register(app)
    loki.register(app)
    navigation.register(app)
    oncall.register(app)
    prometheus.register(app)
    pyroscope.register(app)
    search.register(app)
    sift.register(app)
