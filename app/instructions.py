"""Instruction loader for Grafana FastMCP."""

from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Callable, Mapping

LOGGER = logging.getLogger(__name__)

_DEFAULT_TEXT = """This server provides access to your Grafana instance and the surrounding ecosystem.

Available Capabilities:
- Dashboards: Search, retrieve, update, and create dashboards. Extract panel queries and datasource
  information.
- Datasources: List and fetch details for datasources.
- Prometheus & Loki: Run PromQL and LogQL queries, retrieve metric/log metadata, and explore label
  names/values.
- Incidents: Search, create, update, and resolve incidents in Grafana Incident.
- Sift Investigations: Start and manage Sift investigations, analyze logs/traces, find error patterns,
  and detect slow requests.
- Alerting: List and fetch alert rules and notification contact points.
- OnCall: View and manage on-call schedules, shifts, teams, and users.
- Admin: List teams and perform administrative tasks.
- Pyroscope: Profile applications and fetch profiling data.
- Navigation: Generate deeplink URLs for Grafana resources like dashboards, panels, and Explore
  queries.

When responding, favor concise summaries and include relevant identifiers (dashboard UID, datasource
UID, incident ID) so the client can follow up with fetch operations. Avoid expanding raw JSON unless
explicitly requested; present key fields and next-step suggestions instead."""

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Z][A-Z0-9_]+)\s*\}\}")


def _placeholder_resolver() -> Mapping[str, str]:
    """Return a mapping of placeholder names to replacement values."""

    # Environment variables take precedence and can be extended without code
    # changes.
    return {key: value for key, value in os.environ.items() if key}


def _replace_placeholders(
        text: str, value_lookup: Callable[[str], str | None]) -> str:
    """Replace ``{{PLACEHOLDER}}`` tokens using ``value_lookup`` to resolve values."""

    def _replacement(match: re.Match[str]) -> str:
        key = match.group(1)
        value = value_lookup(key)
        return value if value is not None else match.group(0)

    return _PLACEHOLDER_RE.sub(_replacement, text)


def format_instructions(text: str) -> str:
    """Render the instruction template applying environment-driven substitutions."""

    lookup = _placeholder_resolver()
    # ``lookup.get`` already returns ``None`` for missing keys, preserving the token.
    return _replace_placeholders(text, lookup.get)


def _candidate_paths() -> tuple[Path, ...]:
    candidates: list[Path] = []

    env_path = os.getenv("MCP_INSTRUCTIONS_PATH")
    if env_path:
        candidates.append(Path(env_path))

    project_path = Path.cwd() / "instructions.md"
    candidates.append(project_path)

    package_path = Path(__file__).resolve().with_name("instructions.md")
    candidates.append(package_path)

    return tuple(candidates)


@lru_cache(maxsize=1)
def load_instructions() -> str:
    """Load instructions text from configured sources, falling back to the default string."""

    for path in _candidate_paths():
        try:
            if path.exists():
                content = path.read_text(encoding="utf-8").strip()
                if content:
                    LOGGER.info("Using instructions from '%s'", path)
                    return format_instructions(content)
        except OSError as exc:  # pragma: no cover - filesystem issues
            LOGGER.warning(
                "Failed to read instructions from '%s': %s", path, exc)

    LOGGER.info("Using built-in instructions text")
    return format_instructions(_DEFAULT_TEXT)


__all__ = ["format_instructions", "load_instructions"]
