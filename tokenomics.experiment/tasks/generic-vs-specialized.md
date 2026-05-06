# Generic vs Specialized Task Set

Use the same prompt text for each task on both branches. Start from the same base commit and record the raw exported agent log for each run.

## Task 001: Small Bug Fix

Prompt:

```text
Find and fix one narrowly scoped bug in an existing Grafana MCP tool module. Keep the change localized, preserve the public MCP contract, and add or update the smallest relevant test.
```

Acceptance checks:

- the changed behavior is covered by a focused test;
- no unrelated modules are rewritten;
- `uv run pytest` passes;
- `uv run ruff check .` passes.

## Task 002: Existing Behavior Test

Prompt:

```text
Add a unit test for an existing behavior in the Grafana MCP server without changing runtime behavior. Prefer a behavior that protects a public tool schema, transport contract, or configuration edge case.
```

Acceptance checks:

- only tests or test fixtures change unless a test helper is clearly needed;
- the test fails for a meaningful regression;
- `uv run pytest` passes;
- `uv run ruff check .` passes.

## Task 003: Documentation Update

Prompt:

```text
Update project documentation for one existing grafanaFastMCP workflow. Keep the documentation accurate to the current code and avoid changing runtime code.
```

Acceptance checks:

- documentation references existing commands, files, and behavior;
- no runtime files change;
- markdown is concise and actionable;
- `uv run ruff check .` passes if Python files changed.

