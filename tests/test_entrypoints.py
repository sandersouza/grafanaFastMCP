"""Tests covering package entrypoints and instruction loader."""

from __future__ import annotations

import os
import runpy
from pathlib import Path

import pytest

from app import instructions


def test_load_instructions_prefers_env_path(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "instructions.md"
    target.write_text("Custom instructions", encoding="utf-8")
    monkeypatch.setenv("MCP_INSTRUCTIONS_PATH", str(target))
    instructions.load_instructions.cache_clear()
    assert instructions.load_instructions() == "Custom instructions"


def test_load_instructions_falls_back_to_default(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_INSTRUCTIONS_PATH", raising=False)
    instructions.load_instructions.cache_clear()
    content = instructions.load_instructions()
    assert "Dashboards" in content


def test_app_module_entrypoint_invokes_main(
        monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    def fake_main() -> None:
        called["app"] = True

    monkeypatch.setattr("app.main.main", fake_main)
    runpy.run_module("app.__main__", run_name="__main__")
    assert called.get("app") is True


def test_run_app_entrypoint_invokes_main(
        monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    def fake_main() -> None:
        called["run_app"] = True

    monkeypatch.setattr("app.main.main", fake_main)
    runpy.run_module("run_app", run_name="__main__")
    assert called.get("run_app") is True
