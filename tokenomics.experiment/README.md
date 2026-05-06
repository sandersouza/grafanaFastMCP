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
