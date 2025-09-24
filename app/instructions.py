"""Instruction loader for Grafana FastMCP."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

LOGGER = logging.getLogger(__name__)

_DEFAULT_TEXT = """This server provides access to your Grafana instance and the surrounding ecosystem.\n\nAvailable Capabilities:\n- Dashboards: Search, retrieve, update, and create dashboards. Extract panel queries and datasource information.\n- Datasources: List and fetch details for datasources.\n- Prometheus & Loki: Run PromQL and LogQL queries, retrieve metric/log metadata, and explore label names/values.\n- Incidents: Search, create, update, and resolve incidents in Grafana Incident.\n- Sift Investigations: Start and manage Sift investigations, analyze logs/traces, find error patterns, and detect slow requests.\n- Alerting: List and fetch alert rules and notification contact points.\n- OnCall: View and manage on-call schedules, shifts, teams, and users.\n- Admin: List teams and perform administrative tasks.\n- Pyroscope: Profile applications and fetch profiling data.\n- Navigation: Generate deeplink URLs for Grafana resources like dashboards, panels, and Explore queries.\n\nWhen responding, favor concise summaries and include relevant identifiers (dashboard UID, datasource UID, incident ID) so the client can follow up with fetch operations. Avoid expanding raw JSON unless explicitly requested; present key fields and next-step suggestions instead."""


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
                    return content
        except OSError as exc:  # pragma: no cover - filesystem issues
            LOGGER.warning("Failed to read instructions from '%s': %s", path, exc)

    LOGGER.info("Using built-in instructions text")
    return _DEFAULT_TEXT


__all__ = ["load_instructions"]
