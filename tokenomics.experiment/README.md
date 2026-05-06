# Tokenomics Experiment

This directory contains the experiment protocol and tooling for measuring token usage by SDLC stage during agentic development work.

## Branch Role

`test/tokenomics-tests-with-instructions` is the instrumentation branch for token-cost reduction techniques. Use this branch to add and validate agent instructions, context compression, semantic maps, measurement scripts, stage labeling, and other workflow optimizations that may reduce token usage.

These assets are part of the experiment harness. They should not be treated as production MCP runtime behavior unless a later branch explicitly promotes them.

## Files

- `experiment-plan.md`: executable protocol for the first experiment.
- `tasks/generic-vs-specialized.md`: fixed tasks to run on both branches.
- `schemas/agent-run.schema.json`: normalized record schema.
- `scripts/normalize_agent_logs.py`: converts exported agent logs into comparable JSON, CSV, and summary files.

## Normalize Logs

Place exported logs in a directory and run:

```sh
python tokenomics.experiment/scripts/normalize_agent_logs.py \
  --input path/to/raw-logs \
  --output-dir tokenomics.experiment/out \
  --branch test/tokenomics-tests-with-instructions \
  --task-id task-001
```

The script writes:

- `normalized.json`
- `normalized.csv`
- `summary.json`

The normalized records and summary keep raw and cache-aware token views separate:

- raw total: `input_tokens + output_tokens + reasoning_tokens`;
- cache-aware total: `non_cached_input_tokens + output_tokens + reasoning_tokens`;
- cache metrics remain `null` when the provider does not report cached input.

## Check Branch Hygiene

Before collecting logs, check whether a branch is valid for its role:

```sh
python tokenomics.experiment/scripts/check_branch_hygiene.py \
  specialized WORKTREE

python tokenomics.experiment/scripts/check_branch_hygiene.py \
  generic test/tokenomics-tests-without-instructions
```

Supported inputs are JSON arrays, JSON objects with `messages`, `events`, `calls`, or `records`, JSONL files, and already-normalized records.

## Branch Hygiene

Before collecting data:

- `test/tokenomics-tests-with-instructions` must expose a project-specific `AGENTS.md`.
- `test/tokenomics-tests-without-instructions` must not expose project-specific instruction files to the agent.

If the generic branch contains `AGENTS.md`, `COPILOT.md`, `CLAUDE.md`, `instructions.md`, or `instructions-long.md`, the run is contaminated and must not be used for conclusions.

## Run Codex By Phase

Use `scripts/run_codex_phases.py` to execute one task as six separate Codex runs:

- `DESIGN`
- `CODING`
- `CODE_COMPLETION`
- `CODE_REVIEW`
- `TESTING`
- `DOCUMENTATION`

Each phase writes its own JSONL log, final message, stderr log, and prompt. The
script passes previous phase final messages into later prompts so the runs remain
connected while preserving one `turn.completed.usage` record per phase.
After each phase, the script prints the phase status and token statistics to
stdout.

```sh
python tokenomics.experiment/scripts/run_codex_phases.py \
  -C /Users/sandersouza/Developer/grafanaFastMCP \
  --run-id token-cost.without-instructions.phased \
  "Crie nova tool que retorne a versão dos componentes/plugins do Grafana e do próprio Grafana."
```

By default the script calls Codex with:

```text
--json --dangerously-bypass-approvals-and-sandbox
```

This matches Codex CLI builds where `codex exec -a never` is not accepted. To use
the sandbox and approval flags instead, pass `--use-sandbox-approval`.

For longer tasks:

```sh
python tokenomics.experiment/scripts/run_codex_phases.py \
  -C /Users/sandersouza/Developer/grafanaFastMCP \
  --task-file tokenomics.experiment/tasks/my-task.md
```

Outputs are written under:

```text
tokenomics.experiment/raw-runs/<run-id>/
```

The phase token totals are summarized in:

```text
tokenomics.experiment/raw-runs/<run-id>/usage-summary.json
```

The human-readable report is written to:

```text
tokenomics.experiment/raw-runs/<run-id>/report.md
```

Use `--dry-run` to generate prompts and manifests without invoking Codex.
