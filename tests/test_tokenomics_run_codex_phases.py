"""Tests for the phased Codex tokenomics runner."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tokenomics.experiment" / "scripts" / "run_codex_phases.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_codex_phases", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_phase_prompt_references_previous_outputs() -> None:
    runner = load_module()

    prompt = runner.build_phase_prompt(
        task="Add a Grafana versions tool.",
        phase="CODING",
        previous_messages=[("DESIGN", "Use /api/health and /api/plugins.")],
    )

    assert prompt.startswith("[CODING]")
    assert "Add a Grafana versions tool." in prompt
    assert "## Previous Phase: DESIGN" in prompt
    assert "Use /api/health and /api/plugins." in prompt


def test_codex_command_uses_json_and_bypass_by_default(tmp_path: Path) -> None:
    runner = load_module()

    command = runner.codex_command(
        codex_bin="codex",
        workspace=tmp_path,
        model="gpt-test",
        use_sandbox_approval=False,
        sandbox="danger-full-access",
        approval="never",
        final_message_file=tmp_path / "final.md",
        extra_args=["--skip-git-repo-check"],
        prompt="[DESIGN] Task",
    )

    assert command[:5] == ["codex", "exec", "-C", str(tmp_path), "--json"]
    assert "--dangerously-bypass-approvals-and-sandbox" in command
    assert "--sandbox" not in command
    assert "-a" not in command
    assert "--ask-for-approval" not in command
    model_index = command.index("-m")
    assert command[model_index:model_index + 2] == ["-m", "gpt-test"]
    assert command[-1] == "[DESIGN] Task"


def test_codex_command_can_use_sandbox_approval(tmp_path: Path) -> None:
    runner = load_module()

    command = runner.codex_command(
        codex_bin="codex",
        workspace=tmp_path,
        model=None,
        use_sandbox_approval=True,
        sandbox="workspace-write",
        approval="never",
        final_message_file=tmp_path / "final.md",
        extra_args=[],
        prompt="[TESTING] Task",
    )

    assert "--dangerously-bypass-approvals-and-sandbox" not in command
    assert "--sandbox" in command
    assert "workspace-write" in command
    assert "-a" in command
    assert "never" in command
    assert command[-1] == "[TESTING] Task"


def test_extract_usage_returns_last_usage_event(tmp_path: Path) -> None:
    runner = load_module()
    raw_log = tmp_path / "phase.jsonl"
    raw_log.write_text(
        "\n".join(
            [
                json.dumps({"type": "turn.started"}),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 10,
                            "cached_input_tokens": 2,
                            "output_tokens": 3,
                            "reasoning_output_tokens": 1,
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert runner.extract_usage(raw_log) == {
        "input_tokens": 10,
        "cached_input_tokens": 2,
        "output_tokens": 3,
        "reasoning_output_tokens": 1,
    }


def test_usage_summary_groups_by_phase() -> None:
    runner = load_module()
    results = [
        runner.PhaseResult(
            phase="DESIGN",
            index=1,
            prompt_file="design.prompt.md",
            raw_log_file="design.jsonl",
            final_message_file="design.final.md",
            stderr_file="design.stderr.log",
            exit_code=0,
            elapsed_seconds=1.5,
            usage={
                "input_tokens": 10,
                "cached_input_tokens": 2,
                "output_tokens": 3,
                "reasoning_output_tokens": 1,
            },
        ),
        runner.PhaseResult(
            phase="CODING",
            index=2,
            prompt_file="coding.prompt.md",
            raw_log_file="coding.jsonl",
            final_message_file="coding.final.md",
            stderr_file="coding.stderr.log",
            exit_code=None,
            elapsed_seconds=None,
            usage=None,
        ),
    ]

    summary = runner.usage_summary(results)

    assert summary["totals"] == {
        "input_tokens": 10,
        "cached_input_tokens": 2,
        "output_tokens": 3,
        "reasoning_output_tokens": 1,
    }
    assert summary["missing_usage_phases"] == ["CODING"]
    assert summary["by_phase"]["DESIGN"]["elapsed_seconds"] == 1.5


def test_format_phase_status_includes_usage_stats() -> None:
    runner = load_module()
    result = runner.PhaseResult(
        phase="TESTING",
        index=5,
        prompt_file="testing.prompt.md",
        raw_log_file="testing.jsonl",
        final_message_file="testing.final.md",
        stderr_file="testing.stderr.log",
        exit_code=0,
        elapsed_seconds=12.34,
        usage={
            "input_tokens": 100,
            "cached_input_tokens": 75,
            "output_tokens": 20,
            "reasoning_output_tokens": 5,
        },
    )

    status = runner.format_phase_status(result)

    assert status.startswith("[TESTING] status=pass")
    assert "elapsed=12.3s" in status
    assert "input=100" in status
    assert "non_cached=25" in status
    assert "reasoning=5" in status


def test_render_report_includes_totals_and_phase_table() -> None:
    runner = load_module()
    manifest = {
        "run_id": "run-1",
        "branch": "test/branch",
        "task": "Add a tool.",
        "workspace": "/repo",
        "created_at": "2026-05-06T00:00:00+00:00",
    }
    summary = {
        "totals": {
            "input_tokens": 100,
            "cached_input_tokens": 80,
            "output_tokens": 20,
            "reasoning_output_tokens": 5,
        },
        "missing_usage_phases": [],
        "by_phase": {
            "DESIGN": {
                "elapsed_seconds": 10.0,
                "exit_code": 0,
                "usage": {
                    "input_tokens": 100,
                    "cached_input_tokens": 80,
                    "output_tokens": 20,
                    "reasoning_output_tokens": 5,
                },
            }
        },
    }

    report = runner.render_report(manifest, summary)

    assert "# Codex Phase Tokenomics Report" in report
    assert "Run ID: `run-1`" in report
    assert "Input tokens: `100`" in report
    assert "Non-cached input tokens: `20`" in report
    assert "| `DESIGN` | pass | 10.0s | 100 | 80 | 20 | 20 | 5 | 80.0%" in report
