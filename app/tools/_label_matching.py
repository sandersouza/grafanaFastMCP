"""Shared helpers for handling Prometheus-style label matchers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping


_MATCH_TYPE_ALIASES: Dict[str, str] = {
    "": "=",
    "=": "=",
    "!=": "!=",
    "=~": "=~",
    "!~": "!~",
}


@dataclass
class LabelMatcher:
    """Represents a single matcher against a label key."""

    name: str
    value: str
    type: str = "="
    _compiled: re.Pattern[str] | None = field(
        default=None, init=False, repr=False)

    def normalized_type(self) -> str:
        match_type = _MATCH_TYPE_ALIASES.get(self.type, self.type)
        if match_type not in {"=", "!=", "=~", "!~"}:
            raise ValueError(f"Unsupported matcher type: {self.type}")
        return match_type

    def matches(self, labels: Mapping[str, str]) -> bool:
        match_type = self.normalized_type()
        label_value = labels.get(self.name)
        if match_type == "=":
            return label_value == self.value
        if match_type == "!=":
            return label_value != self.value
        # Regex cases
        if self._compiled is None:
            try:
                self._compiled = re.compile(self.value)
            except re.error as exc:  # pragma: no cover - defensive
                raise ValueError(
                    f"Invalid regular expression '{self.value}': {exc}") from exc
        if label_value is None:
            return match_type == "!~"
        is_match = bool(self._compiled.search(label_value))
        return is_match if match_type == "=~" else not is_match


@dataclass
class Selector:
    """Collection of matchers that must all evaluate to true."""

    filters: Iterable[LabelMatcher]

    def __post_init__(self) -> None:
        if not isinstance(self.filters, tuple):
            self.filters = tuple(self.filters)

    def to_promql(self) -> str:
        parts = []
        for matcher in self.filters:
            match_type = matcher.normalized_type()
            value = matcher.value.replace("\\", "\\\\").replace("\"", "\\\"")
            parts.append(f"{matcher.name}{match_type}\"{value}\"")
        inner = ", ".join(parts)
        return f"{{{inner}}}"

    def matches(self, labels: Mapping[str, str]) -> bool:
        for matcher in self.filters:
            if not matcher.matches(labels):
                return False
        return True


def matches_all(selectors: Iterable[Selector],
                labels: Mapping[str, str]) -> bool:
    """Return True if every selector matches the provided labels."""

    for selector in selectors:
        if not selector.matches(labels):
            return False
    return True


__all__ = ["LabelMatcher", "Selector", "matches_all"]
