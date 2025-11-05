"""Alerting-related tools for Grafana."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

from ..context import get_grafana_config
from ..grafana_client import GrafanaAPIError, GrafanaClient
from ._label_matching import LabelMatcher, Selector, matches_all


def _parse_label_matchers(
        raw_filters: Iterable[Dict[str, Any]]) -> List[LabelMatcher]:
    matchers: List[LabelMatcher] = []
    for filt in raw_filters:
        if not isinstance(filt, dict):
            raise ValueError("Label matcher entries must be objects")
        name = filt.get("name")
        value = filt.get("value")
        match_type = filt.get("type", "=")
        if not isinstance(name, str) or not name:
            raise ValueError("Label matcher missing required 'name' field")
        if not isinstance(value, str):
            raise ValueError("Label matcher 'value' must be a string")
        if not isinstance(match_type, str):
            raise ValueError("Label matcher 'type' must be a string")
        matchers.append(LabelMatcher(name=name, value=value, type=match_type))
    return matchers


def _parse_label_selectors(
        raw: Optional[Iterable[Dict[str, Any]]]) -> List[Selector]:
    selectors: List[Selector] = []
    if not raw:
        return selectors
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("Label selector entries must be objects")
        filters_raw = entry.get("filters", [])
        if not isinstance(filters_raw, Iterable):
            raise ValueError("Label selector 'filters' must be an array")
        matchers = _parse_label_matchers(filters_raw)
        if matchers:
            selectors.append(Selector(matchers))
    return selectors


async def _fetch_alert_rules(client: GrafanaClient) -> List[Dict[str, Any]]:
    payload = await client.get_json("/prometheus/grafana/api/v1/rules")
    if not isinstance(payload, dict):
        raise ValueError("Unexpected response from Grafana alerting API")
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    groups = data.get("groups", [])
    rules: List[Dict[str, Any]] = []
    if not isinstance(groups, list):
        return rules
    for group in groups:
        if not isinstance(group, dict):
            continue
        group_rules = group.get("rules")
        if not isinstance(group_rules, list):
            continue
        for rule in group_rules:
            if isinstance(rule, dict):
                rules.append(rule)
    return rules


def _summarize_alert_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    labels = rule.get("labels") if isinstance(rule.get("labels"), dict) else {}
    return {
        "uid": rule.get("uid"),
        "title": rule.get("name"),
        "state": rule.get("state"),
        "labels": labels,
    }


def _filter_rules_by_selectors(
    rules: List[Dict[str, Any]], selectors: List[Selector]
) -> List[Dict[str, Any]]:
    if not selectors:
        return rules
    filtered: List[Dict[str, Any]] = []
    for rule in rules:
        labels = rule.get("labels") if isinstance(
            rule.get("labels"), dict) else {}
        if matches_all(selectors, labels):
            filtered.append(rule)
    return filtered


def _apply_pagination(
    items: List[Dict[str, Any]], limit: Optional[int], page: Optional[int]
) -> List[Dict[str, Any]]:
    if not items:
        return []
    effective_limit = limit or 100
    effective_page = page or 1
    if effective_limit <= 0:
        raise ValueError("limit must be greater than zero")
    if effective_page <= 0:
        raise ValueError("page must be greater than zero")
    start = (effective_page - 1) * effective_limit
    end = start + effective_limit
    if start >= len(items):
        return []
    return items[start:end]


async def _list_alert_rules(
    ctx: Context,
    limit: Optional[int],
    page: Optional[int],
    label_selectors: Optional[Iterable[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    selectors = _parse_label_selectors(label_selectors)
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    rules = await _fetch_alert_rules(client)
    filtered = _filter_rules_by_selectors(rules, selectors)
    paged = _apply_pagination(filtered, limit, page)
    return [_summarize_alert_rule(rule) for rule in paged]


async def _get_alert_rule(ctx: Context, uid: str) -> Any:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    try:
        return await client.get_json(f"/v1/provisioning/alert-rules/{uid}")
    except GrafanaAPIError as exc:
        if exc.status_code == 404:
            raise ValueError(f"Alert rule with UID '{uid}' not found") from exc
        raise


async def _list_contact_points(
    ctx: Context, limit: Optional[int], name: Optional[str]
) -> List[Dict[str, Any]]:
    config = get_grafana_config(ctx)
    client = GrafanaClient(config)
    params: Dict[str, Any] = {}
    if name:
        params["name"] = name
    payload = await client.get_json("/v1/provisioning/contact-points", params=params or None)
    if not isinstance(payload, list):
        raise ValueError("Unexpected response when listing contact points")
    effective_limit = limit or 100
    if effective_limit <= 0:
        raise ValueError("limit must be greater than zero")
    subset = payload[:effective_limit]
    results: List[Dict[str, Any]] = []
    for item in subset:
        if not isinstance(item, dict):
            continue
        summary = {
            "uid": item.get("uid"),
            "name": item.get("name"),
            "type": item.get("type"),
        }
        results.append(summary)
    return results


def register(app: FastMCP) -> None:
    """Register alerting tools with the FastMCP application."""

    @app.tool(
        name="list_alert_rules", title="List alert rules", description=(
            "List Grafana alert rules with optional pagination and label filtering. "
            "Returns a consolidated response object containing rules metadata, total count, and pagination info. "
            "This format prevents JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."), )
    async def list_alert_rules(
        limit: Optional[int] = None,
        page: Optional[int] = None,
        labelSelectors: Optional[Iterable[Dict[str, Any]]] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError("Context injection failed for list_alert_rules")
        rules = await _list_alert_rules(ctx, limit, page, labelSelectors)
        return {
            "alert_rules": rules,
            "total_count": len(rules),
            "limit": limit,
            "page": page,
            "label_selectors": list(labelSelectors) if labelSelectors else None,
            "type": "alert_rules_result"}

    @app.tool(
        name="get_alert_rule_by_uid",
        title="Get alert rule details",
        description="Retrieve the full configuration for a Grafana alert rule identified by its UID.",
    )
    async def get_alert_rule_by_uid(
        uid: str,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for get_alert_rule_by_uid")
        return await _get_alert_rule(ctx, uid)

    @app.tool(
        name="list_contact_points",
        title="List contact points",
        description=(
            "List Grafana notification contact points with optional name filtering. "
            "Returns a consolidated response object to prevent JSON chunking issues in streamable HTTP with ChatGPT/OpenAI."
        ),
    )
    async def list_contact_points(
        limit: Optional[int] = None,
        name: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Any:
        if ctx is None:
            raise ValueError(
                "Context injection failed for list_contact_points")
        contacts = await _list_contact_points(ctx, limit, name)
        return {
            "contact_points": contacts,
            "total_count": len(contacts),
            "limit": limit,
            "name": name,
            "type": "contact_points_result"
        }


__all__ = ["register"]
