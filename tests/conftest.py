"""Test configuration for Grafana FastMCP."""

from __future__ import annotations

import os

# Ensure the lightweight MCP stubs remain active during the tests even when the
# real package is installed in the environment.  The application code will load
# the genuine dependency in production runs where the environment variable is
# not set.
os.environ.setdefault("GRAFANA_FASTMCP_USE_STUB", "1")
