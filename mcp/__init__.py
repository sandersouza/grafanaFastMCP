"""Compat wrapper that exposes either the real MCP package or local stubs.

This repository vendors a very small subset of the MCP SDK so that the test
suite can exercise the Grafana tooling without needing the real dependency.
When the genuine :mod:`mcp` package is installed (for example in production
environments or inside the PyInstaller bundle) we should defer to it so that
runtime behaviour matches the upstream implementation.

To keep backwards compatibility with the tests we allow forcing the lightweight
stubs via the ``GRAFANA_FASTMCP_USE_STUB`` environment variable.  This flag is
set by the test harness and therefore does not affect real executions.
"""

from __future__ import annotations

import importlib.metadata as metadata
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

_FORCE_STUB_ENV = "GRAFANA_FASTMCP_USE_STUB"


def _should_use_stub() -> bool:
    """Return ``True`` when the lightweight stubs should be used."""

    value = os.getenv(_FORCE_STUB_ENV)
    if value is None:
        return False

    normalized = value.strip().lower()
    return normalized not in {"", "0", "false", "no"}


def _load_real_mcp() -> ModuleType | None:
    """Attempt to load the upstream :mod:`mcp` package from site-packages."""

    try:
        distribution = metadata.distribution("mcp")
    except metadata.PackageNotFoundError:
        return None

    package_root = Path(distribution.locate_file("mcp"))
    init_file = package_root / "__init__.py"
    if not init_file.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        __name__,
        init_file,
        submodule_search_locations=[str(package_root)],
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[__name__] = module
    spec.loader.exec_module(module)
    return module


_real_module = None if _should_use_stub() else _load_real_mcp()

if _real_module is not None:
    # Mirror the real package's globals in our module namespace so importing
    # code observes the genuine implementation.  Special attributes such as
    # ``__path__`` are already configured by :func:`exec_module`.
    globals().update(_real_module.__dict__)
    __all__ = getattr(_real_module, "__all__", [])
else:  # pragma: no cover - exercised indirectly through the test-suite stubs
    from . import server as server  # type: ignore=unused-ignore  # noqa: F401

    __all__ = ["server"]
