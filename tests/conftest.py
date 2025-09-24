"""Pytest configuration for Grafana FastMCP tests."""

from __future__ import annotations

import os

# The test-suite exercises lightweight stubs instead of the real MCP package to
# avoid pulling in optional heavy dependencies. Force the shim implementation by
# default; runtime entrypoints clear this flag so the production server uses the
# real SDK.
os.environ.setdefault("GRAFANA_FASTMCP_FORCE_STUB", "1")
