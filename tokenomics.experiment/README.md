# Tokenomics Experiment

This directory stores raw Codex JSONL logs and helper scripts for measuring token
usage by development phase.

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
