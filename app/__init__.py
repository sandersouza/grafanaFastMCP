"""Python Grafana FastMCP server supporting multiple transports."""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = ["__version__"]

# Import version from root version.py
try:
    # Add parent directory to path to import version
    _parent_dir = Path(__file__).parent.parent
    if str(_parent_dir) not in sys.path:
        sys.path.insert(0, str(_parent_dir))
    from version import __version__
except ImportError:
    __version__ = "unknown"
