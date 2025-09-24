"""Tests for the label matching helpers used by multiple tool modules."""

from __future__ import annotations

import pytest

from app.tools._label_matching import LabelMatcher, Selector, matches_all


def test_label_matcher_normalized_type_and_equality() -> None:
    matcher = LabelMatcher(name="env", value="prod", type="=")
    assert matcher.normalized_type() == "="
    assert matcher.matches({"env": "prod"}) is True
    assert matcher.matches({"env": "dev"}) is False


def test_label_matcher_negation_and_regex() -> None:
    matcher_ne = LabelMatcher(name="env", value="prod", type="!=")
    assert matcher_ne.matches({"env": "dev"}) is True
    assert matcher_ne.matches({"env": "prod"}) is False

    matcher_regex = LabelMatcher(name="cluster", value="^prod-", type="=~")
    assert matcher_regex.matches({"cluster": "prod-us"}) is True
    assert matcher_regex.matches({"cluster": "test"}) is False

    matcher_not_regex = LabelMatcher(name="cluster", value="^test", type="!~")
    assert matcher_not_regex.matches({"cluster": "stage"}) is True
    assert matcher_not_regex.matches({"cluster": "test-eu"}) is False


def test_label_matcher_invalid_type_raises() -> None:
    matcher = LabelMatcher(name="env", value="prod", type="~~")
    with pytest.raises(ValueError):
        matcher.normalized_type()


def test_selector_to_promql_and_matching() -> None:
    matchers = [
        LabelMatcher(name="job", value="grafana"),
        LabelMatcher(name="env", value="prod", type="!="),
    ]
    selector = Selector(matchers)
    promql = selector.to_promql()
    assert promql == '{job="grafana", env!="prod"}'

    labels = {"job": "grafana", "env": "stage"}
    assert selector.matches(labels) is True
    assert selector.matches({"job": "grafana", "env": "prod"}) is False


def test_matches_all_returns_false_on_first_failure() -> None:
    selectors = [
        Selector([LabelMatcher(name="job", value="grafana")]),
        Selector([LabelMatcher(name="env", value="prod")]),
    ]
    assert matches_all(selectors, {"job": "grafana", "env": "prod"}) is True
    assert matches_all(selectors, {"job": "grafana", "env": "stage"}) is False
