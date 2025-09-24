"""Tests for instruction loading helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.instructions import load_instructions


@pytest.fixture(autouse=True)
def clear_cache():
    load_instructions.cache_clear()  # type: ignore[attr-defined]
    yield
    load_instructions.cache_clear()  # type: ignore[attr-defined]


def test_load_instructions_defaults_to_builtin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_INSTRUCTIONS_PATH", raising=False)
    value = load_instructions()
    assert "Grafana" in value


def test_load_instructions_uses_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom = tmp_path / "custom.md"
    custom.write_text("Custom instructions", encoding="utf-8")
    monkeypatch.setenv("MCP_INSTRUCTIONS_PATH", str(custom))

    value = load_instructions()
    assert value == "Custom instructions"
