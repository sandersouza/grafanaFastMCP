#!/usr/bin/env python3
"""Run a Codex task as separate tokenomics phases."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


PHASES = (
    "DESIGN",
    "CODING",
    "CODE_COMPLETION",
    "CODE_REVIEW",
    "TESTING",
    "DOCUMENTATION",
)

PHASE_GOALS = {
    "DESIGN": (
        "Analyze the task and repository context. Produce the implementation plan, "
        "files likely to change, validation strategy, and risks. Do not edit files."
    ),
    "CODING": (
        "Implement the planned code changes. Keep edits scoped to the task. "
        "Do not spend this phase on broad documentation unless needed by code behavior."
    ),
    "CODE_COMPLETION": (
        "Finish integration details, cleanup, edge cases, and any obvious omissions "
        "from the coding phase."
    ),
    "CODE_REVIEW": (
        "Review the local diff for bugs, regressions, missing tests, and accidental "
        "scope creep. Apply fixes that are necessary for the task."
    ),
    "TESTING": (
        "Run the relevant tests and linters. Fix failures caused by this task and "
        "record any pre-existing failures separately."
    ),
    "DOCUMENTATION": (
        "Update task-relevant documentation and produce the final concise handoff. "
        "Include validation results and known limitations."
    ),
}


@dataclass(frozen=True)
class PhaseResult:
    phase: str
    index: int
    prompt_file: str
    raw_log_file: str
    final_message_file: str
    stderr_file: str
    exit_code: int | None
    elapsed_seconds: float | None
    usage: dict[str, Any] | None


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    task = read_task(args)
    workspace = args.workspace.resolve()
    run_id = args.run_id or default_run_id()
    run_dir = args.output_dir.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "run_id": run_id,
        "task": task,
        "workspace": str(workspace),
        "branch": args.branch or current_branch(workspace),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "phases": [],
    }
    write_json(run_dir / "manifest.json", manifest)

    previous_messages: list[tuple[str, str]] = []
    results: list[PhaseResult] = []
    for index, phase in enumerate(PHASES, start=1):
        print(f"[{phase}] starting phase {index}/{len(PHASES)}", flush=True)
        prompt = build_phase_prompt(
            task=task,
            phase=phase,
            previous_messages=previous_messages,
        )
        result = run_phase(
            args=args,
            workspace=workspace,
            run_dir=run_dir,
            run_id=run_id,
            phase=phase,
            index=index,
            prompt=prompt,
        )
        results.append(result)
        manifest["phases"] = [asdict(item) for item in results]
        summary = usage_summary(results)
        write_json(run_dir / "manifest.json", manifest)
        write_json(run_dir / "usage-summary.json", summary)
        write_report(run_dir / "report.md", manifest, summary)
        print(format_phase_status(result), flush=True)

        final_message = read_optional_text(Path(result.final_message_file))
        if final_message:
            previous_messages.append((phase, final_message))
        if result.exit_code and not args.continue_on_failure:
            return result.exit_code

    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "task",
        nargs="?",
        help="Task to execute. Use --task-file for longer prompts.",
    )
    parser.add_argument("--task-file", type=Path, help="Read the task from a file.")
    parser.add_argument(
        "-C",
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Repository/workspace passed to codex exec.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tokenomics.experiment/raw-runs"),
        help="Directory where the per-phase run directory is created.",
    )
    parser.add_argument("--run-id", help="Stable run id. Defaults to a timestamp.")
    parser.add_argument("--branch", default="", help="Branch label for the manifest.")
    parser.add_argument("--codex-bin", default="codex", help="Codex executable.")
    parser.add_argument("-m", "--model", help="Model passed to codex exec.")
    parser.add_argument(
        "--use-sandbox-approval",
        action="store_true",
        help=(
            "Use --sandbox and -a instead of "
            "--dangerously-bypass-approvals-and-sandbox."
        ),
    )
    parser.add_argument(
        "--sandbox",
        default="danger-full-access",
        choices=("read-only", "workspace-write", "danger-full-access"),
        help="Sandbox mode used only with --use-sandbox-approval.",
    )
    parser.add_argument(
        "-a",
        "--approval",
        default="never",
        choices=("untrusted", "on-failure", "on-request", "never"),
        help="Approval policy used only with --use-sandbox-approval.",
    )
    parser.add_argument(
        "--extra-codex-arg",
        action="append",
        default=[],
        help="Additional argument passed to codex exec. Repeat as needed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write prompts and manifest without running codex.",
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Continue later phases even if a phase exits non-zero.",
    )
    parsed = parser.parse_args(argv)
    if parsed.task and parsed.task_file:
        parser.error("pass either task or --task-file, not both")
    if not parsed.task and not parsed.task_file:
        parser.error("task or --task-file is required")
    return parsed


def read_task(args: argparse.Namespace) -> str:
    if args.task_file:
        return args.task_file.read_text(encoding="utf-8").strip()
    return str(args.task).strip()


def build_phase_prompt(
    *,
    task: str,
    phase: str,
    previous_messages: Sequence[tuple[str, str]],
) -> str:
    previous = "\n\n".join(
        f"## Previous Phase: {name}\n\n{message.strip()}"
        for name, message in previous_messages
        if message.strip()
    )
    if not previous:
        previous = "No previous phases have run yet."

    return (
        f"[{phase}]\n"
        "You are running one phase of a multi-phase Codex tokenomics run. "
        "Work only on the current phase, but use the previous phase outputs as context. "
        "Start your user-facing progress/final messages with the current phase label.\n\n"
        f"## Task\n\n{task}\n\n"
        f"## Current Phase\n\n{phase}\n\n"
        f"## Phase Goal\n\n{PHASE_GOALS[phase]}\n\n"
        f"## Previous Phase Outputs\n\n{previous}\n"
    )


def run_phase(
    *,
    args: argparse.Namespace,
    workspace: Path,
    run_dir: Path,
    run_id: str,
    phase: str,
    index: int,
    prompt: str,
) -> PhaseResult:
    prefix = f"{index:02d}-{phase}"
    prompt_file = run_dir / f"{prefix}.prompt.md"
    raw_log_file = run_dir / f"{prefix}.jsonl"
    final_message_file = run_dir / f"{prefix}.final.md"
    stderr_file = run_dir / f"{prefix}.stderr.log"
    prompt_file.write_text(prompt, encoding="utf-8")

    if args.dry_run:
        return PhaseResult(
            phase=phase,
            index=index,
            prompt_file=str(prompt_file),
            raw_log_file=str(raw_log_file),
            final_message_file=str(final_message_file),
            stderr_file=str(stderr_file),
            exit_code=None,
            elapsed_seconds=None,
            usage=None,
        )

    command = codex_command(
        codex_bin=args.codex_bin,
        workspace=workspace,
        model=args.model,
        use_sandbox_approval=args.use_sandbox_approval,
        sandbox=args.sandbox,
        approval=args.approval,
        final_message_file=final_message_file,
        extra_args=args.extra_codex_arg,
        prompt=prompt,
    )
    started = time.monotonic()
    with raw_log_file.open("w", encoding="utf-8") as stdout, stderr_file.open(
        "w", encoding="utf-8"
    ) as stderr:
        completed = subprocess.run(
            command,
            cwd=workspace,
            stdout=stdout,
            stderr=stderr,
            check=False,
        )
    elapsed = time.monotonic() - started
    return PhaseResult(
        phase=phase,
        index=index,
        prompt_file=str(prompt_file),
        raw_log_file=str(raw_log_file),
        final_message_file=str(final_message_file),
        stderr_file=str(stderr_file),
        exit_code=completed.returncode,
        elapsed_seconds=elapsed,
        usage=extract_usage(raw_log_file),
    )


def codex_command(
    *,
    codex_bin: str,
    workspace: Path,
    model: str | None,
    use_sandbox_approval: bool,
    sandbox: str,
    approval: str,
    final_message_file: Path,
    extra_args: Sequence[str],
    prompt: str,
) -> list[str]:
    command = [
        codex_bin,
        "exec",
        "-C",
        str(workspace),
        "--json",
    ]
    if use_sandbox_approval:
        command.extend(["--sandbox", sandbox, "-a", approval])
    else:
        command.append("--dangerously-bypass-approvals-and-sandbox")
    command.extend(["-o", str(final_message_file)])
    if model:
        command.extend(["-m", model])
    command.extend(extra_args)
    command.append(prompt)
    return command


def extract_usage(path: Path) -> dict[str, Any] | None:
    usage: dict[str, Any] | None = None
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        candidate = event.get("usage")
        if isinstance(candidate, dict):
            usage = candidate
    return usage


def usage_summary(results: Sequence[PhaseResult]) -> dict[str, Any]:
    by_phase: dict[str, Any] = {}
    totals = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
    }
    missing_usage: list[str] = []
    for result in results:
        usage = result.usage
        by_phase[result.phase] = {
            "usage": usage,
            "elapsed_seconds": result.elapsed_seconds,
            "exit_code": result.exit_code,
        }
        if usage is None:
            missing_usage.append(result.phase)
            continue
        for key in totals:
            value = usage.get(key)
            if isinstance(value, int):
                totals[key] += value
    return {
        "totals": totals,
        "missing_usage_phases": missing_usage,
        "by_phase": by_phase,
    }


def format_phase_status(result: PhaseResult) -> str:
    usage = result.usage or {}
    input_tokens = int_value(usage.get("input_tokens"))
    cached_tokens = int_value(usage.get("cached_input_tokens"))
    output_tokens = int_value(usage.get("output_tokens"))
    reasoning_tokens = int_value(usage.get("reasoning_output_tokens"))
    non_cached = input_tokens - cached_tokens
    elapsed = result.elapsed_seconds
    elapsed_text = "null" if elapsed is None else f"{elapsed:.1f}s"
    status = "not-run" if result.exit_code is None else (
        "pass" if result.exit_code == 0 else "fail")
    return (
        f"[{result.phase}] status={status} exit_code={result.exit_code} "
        f"elapsed={elapsed_text} input={input_tokens} cached={cached_tokens} "
        f"non_cached={non_cached} output={output_tokens} "
        f"reasoning={reasoning_tokens}"
    )


def render_report(manifest: dict[str, Any], summary: dict[str, Any]) -> str:
    phases = [
        phase for phase in PHASES if phase in summary.get("by_phase", {})
    ]
    totals = summary.get("totals", {})
    total_elapsed = sum(
        float_or_zero(summary["by_phase"][phase].get("elapsed_seconds"))
        for phase in phases
    )
    total_input = int_value(totals.get("input_tokens"))
    total_cached = int_value(totals.get("cached_input_tokens"))
    total_output = int_value(totals.get("output_tokens"))
    total_reasoning = int_value(totals.get("reasoning_output_tokens"))
    total_non_cached = total_input - total_cached
    total_with_reasoning = total_input + total_output + total_reasoning
    cache_rate = percent(total_cached, total_input)

    lines = [
        "# Codex Phase Tokenomics Report",
        "",
        f"- Run ID: `{manifest.get('run_id', 'unknown')}`",
        f"- Branch: `{manifest.get('branch', 'unknown')}`",
        f"- Task: {manifest.get('task', '')}",
        f"- Workspace: `{manifest.get('workspace', '')}`",
        f"- Created at: `{manifest.get('created_at', '')}`",
        f"- Missing usage phases: {summary.get('missing_usage_phases', [])}",
        "",
        "## Totals",
        "",
        f"- Elapsed: `{total_elapsed:.1f}s`",
        f"- Input tokens: `{total_input:,}`",
        f"- Cached input tokens: `{total_cached:,}`",
        f"- Non-cached input tokens: `{total_non_cached:,}`",
        f"- Output tokens: `{total_output:,}`",
        f"- Reasoning output tokens: `{total_reasoning:,}`",
        f"- Input cache rate: `{cache_rate:.1f}%`",
        f"- Input + output + reasoning: `{total_with_reasoning:,}`",
        "",
        "## By Phase",
        "",
        (
            "| Phase | Status | Time | Input | Cached Input | Non-Cached Input | "
            "Output | Reasoning | Cache Rate | Input % | Output % | Reasoning % | "
            "Time % |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for phase in phases:
        row = summary["by_phase"][phase]
        usage = row.get("usage") or {}
        elapsed = float_or_zero(row.get("elapsed_seconds"))
        exit_code = row.get("exit_code")
        status = "not-run" if exit_code is None else (
            "pass" if exit_code == 0 else "fail")
        input_tokens = int_value(usage.get("input_tokens"))
        cached_tokens = int_value(usage.get("cached_input_tokens"))
        non_cached = input_tokens - cached_tokens
        output_tokens = int_value(usage.get("output_tokens"))
        reasoning_tokens = int_value(usage.get("reasoning_output_tokens"))
        lines.append(
            f"| `{phase}` | {status} | {elapsed:.1f}s | {input_tokens:,} | "
            f"{cached_tokens:,} | {non_cached:,} | {output_tokens:,} | "
            f"{reasoning_tokens:,} | {percent(cached_tokens, input_tokens):.1f}% | "
            f"{percent(input_tokens, total_input):.1f}% | "
            f"{percent(output_tokens, total_output):.1f}% | "
            f"{percent(reasoning_tokens, total_reasoning):.1f}% | "
            f"{percent(elapsed, total_elapsed):.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            (
                "- `Non-Cached Input` is calculated as "
                "`input_tokens - cached_input_tokens`."
            ),
            (
                "- `Input + output + reasoning` is a reporting total; provider "
                "billing semantics may treat cached and reasoning tokens differently."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(path: Path, manifest: dict[str, Any], summary: dict[str, Any]) -> None:
    path.write_text(render_report(manifest, summary), encoding="utf-8")


def int_value(value: Any) -> int:
    return value if isinstance(value, int) else 0


def float_or_zero(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def percent(part: float, whole: float) -> float:
    if whole == 0:
        return 0.0
    return part / whole * 100


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def current_branch(workspace: Path) -> str:
    completed = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
    )
    branch = completed.stdout.strip()
    return branch or "unknown"


def read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
