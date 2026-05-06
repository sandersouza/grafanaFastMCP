# Agent Onboarding Guide

## Minimum Read

1. Pick one row in `CONTEXT-PACKS.md`.
2. Use `SEMANTIC-MAP.md` to identify owner and closest test.
3. Open only that owner file, that test, and exact `rg` hits needed for the task.

## Hard Rules

- No full docs-folder scan during `DESIGN`.
- No architecture rediscovery during `CODE_COMPLETION`; start from `git diff`.
- Do not rewrite a tool module when a helper edit is enough.
- Do not bypass `get_grafana_config(ctx)`.
- Do not expose optional tools without capability gating.
- Preserve consolidated list/search/update responses.
- Raise `ValueError` for unexpected Grafana payload shapes.

## Done

- Focused test added or updated when behavior changes.
- `uv run pytest` and `uv run ruff check .` attempted for Python behavior.
- Runtime, docs, and tokenomics harness changes remain separated.
