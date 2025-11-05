"""Utilities for detecting Grafana capabilities used during tool registration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, FrozenSet, Iterable, Set

from ..config import GrafanaConfig
from ..grafana_client import GrafanaAPIError, GrafanaClient

LOGGER = logging.getLogger(__name__)


def _normalize_items(values: Iterable[Any]) -> FrozenSet[str]:
    normalized: Set[str] = set()
    for value in values:
        if not isinstance(value, str):
            value = str(value or "")
        cleaned = value.strip().lower()
        if cleaned:
            normalized.add(cleaned)
    return frozenset(normalized)


@dataclass(frozen=True)
class GrafanaCapabilities:
    """Represents the Grafana features available to the MCP server."""

    datasource_types: FrozenSet[str] = field(default_factory=frozenset)
    plugin_ids: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:  # pragma: no cover - dataclass hook
        object.__setattr__(
            self,
            "datasource_types",
            _normalize_items(
                self.datasource_types))
        object.__setattr__(
            self, "plugin_ids", _normalize_items(
                self.plugin_ids))

    def has_datasource_type(self, expected: str) -> bool:
        if not expected:
            return False
        normalized = expected.strip().lower()
        return any(normalized in ds_type for ds_type in self.datasource_types)

    def has_plugin(self, plugin_id: str) -> bool:
        if not plugin_id:
            return False
        normalized = plugin_id.strip().lower()
        return normalized in self.plugin_ids


async def _fetch_datasource_types(client: GrafanaClient) -> Set[str]:
    try:
        payload = await client.get_json("/datasources")
    except GrafanaAPIError as exc:  # pragma: no cover - defensive
        LOGGER.info(
            "Grafana datasources endpoint returned %s; assuming no datasource-based tools",
            exc.status_code)
        return set()
    except Exception:  # pragma: no cover - defensive
        LOGGER.warning("Failed to list Grafana datasources", exc_info=True)
        return set()

    items: Iterable[Any]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        candidate = payload.get("datasources") or payload.get("items")
        if isinstance(candidate, list):
            items = candidate
        else:
            LOGGER.debug("Unexpected datasources payload format: %r", payload)
            return set()
    else:
        LOGGER.debug(
            "Ignoring datasources payload of type %s",
            type(payload).__name__)
        return set()

    types: Set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        type_value = item.get("type")
        if isinstance(type_value, str):
            cleaned = type_value.strip().lower()
            if cleaned:
                types.add(cleaned)
    return types


async def _fetch_plugin_ids(client: GrafanaClient) -> Set[str]:
    try:
        payload = await client.get_json("/plugins")
    except GrafanaAPIError as exc:  # pragma: no cover - defensive
        LOGGER.info(
            "Grafana plugins endpoint returned %s; plugin-dependent tools will be disabled",
            exc.status_code)
        return set()
    except Exception:  # pragma: no cover - defensive
        LOGGER.warning("Failed to list Grafana plugins", exc_info=True)
        return set()

    items: Iterable[Any]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        candidate = payload.get("items") or payload.get("plugins")
        if isinstance(candidate, list):
            items = candidate
        else:
            LOGGER.debug("Unexpected plugins payload format: %r", payload)
            return set()
    else:
        LOGGER.debug(
            "Ignoring plugins payload of type %s",
            type(payload).__name__)
        return set()

    plugin_ids: Set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        plugin_id = item.get("id")
        if isinstance(plugin_id, str):
            cleaned = plugin_id.strip().lower()
            if cleaned:
                plugin_ids.add(cleaned)
    return plugin_ids


async def _collect_capabilities(config: GrafanaConfig) -> GrafanaCapabilities:
    client = GrafanaClient(config)
    datasource_types, plugin_ids = await asyncio.gather(
        _fetch_datasource_types(client),
        _fetch_plugin_ids(client),
    )
    LOGGER.debug(
        "Detected Grafana capabilities",
        extra={
            "datasource_types": sorted(datasource_types),
            "plugin_ids": sorted(plugin_ids),
        },
    )
    return GrafanaCapabilities(
        datasource_types=frozenset(datasource_types),
        plugin_ids=frozenset(plugin_ids))


def detect_capabilities(config: GrafanaConfig) -> GrafanaCapabilities:
    """Synchronously detect Grafana capabilities for tool registration."""

    try:
        return asyncio.run(_collect_capabilities(config))
    except RuntimeError as exc:
        message = str(exc)
        if "asyncio.run" not in message:
            LOGGER.warning("Capability detection failed", exc_info=True)
            return GrafanaCapabilities()
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_collect_capabilities(config))
        except Exception:  # pragma: no cover - defensive
            LOGGER.warning(
                "Capability detection failed inside fallback loop",
                exc_info=True)
            return GrafanaCapabilities()
        finally:
            loop.close()
    except Exception:  # pragma: no cover - defensive
        LOGGER.warning("Capability detection failed", exc_info=True)
        return GrafanaCapabilities()


__all__ = ["GrafanaCapabilities", "detect_capabilities"]
