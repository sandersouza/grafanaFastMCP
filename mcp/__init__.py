"""Lightweight local stubs for the MCP SDK used in tests.

When the real ``mcp`` package is available (and tests have not requested the
stub explicitly), this module adjusts the package search path so imports
resolve against the installed distribution instead of the simplified local
shims.
"""

from __future__ import annotations

import importlib.metadata
import os
import sys
from pathlib import Path
from typing import Iterable

__all__ = ["server"]


def _resolve(path: str | os.PathLike[str]) -> Path:
    """Resolve a filesystem entry, guarding against runtime errors."""

    try:
        return Path(path).resolve()
    except (OSError, RuntimeError):  # pragma: no cover - defensive on exotic fs
        return Path(path)


def _iter_stub_modules() -> Iterable[str]:
    """Yield module names that point at the local stub implementation."""

    repo_root = _resolve(Path(__file__).parent)
    for name, module in list(sys.modules.items()):
        if name == "mcp" or not name.startswith("mcp"):
            continue
        module_path = getattr(module, "__file__", None)
        if not module_path:
            continue
        resolved = _resolve(module_path)
        if repo_root in resolved.parents or resolved == repo_root:
            yield name


def _prefer_real_package() -> None:
    """Insert the real MCP distribution at the front of ``__path__``."""

    if os.environ.get("GRAFANA_FASTMCP_FORCE_STUB") == "1":
        return

    try:
        distribution = importlib.metadata.distribution("mcp")
    except importlib.metadata.PackageNotFoundError:
        return

    package_root = _resolve(Path(distribution.locate_file("mcp")))
    stub_root = _resolve(Path(__file__).parent)
    if package_root == stub_root:
        return

    current_paths = [_resolve(entry) for entry in list(__path__)]  # type: ignore[name-defined]
    if package_root not in current_paths:
        __path__.insert(0, str(package_root))  # type: ignore[name-defined]

    for name in _iter_stub_modules():
        sys.modules.pop(name, None)


_prefer_real_package()
