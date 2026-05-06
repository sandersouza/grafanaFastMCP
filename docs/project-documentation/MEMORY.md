# Memory And Decisions

This page is the durable project memory for stable facts that reduce repeated agent rediscovery. Keep it short and update it only for decisions expected to remain true across tasks.

## Stable Decisions

| Decision | Rationale | Source area |
| --- | --- | --- |
| Use the **Capability-Gated MCP Tool Facade** pattern as the local architecture label. | It matches the actual FastMCP-to-Grafana facade better than generic enterprise patterns from the tokenomics paper. | `app/server.py`, `app/tools/__init__.py`, `app/tools/*.py` |
| Keep Grafana HTTP access centralized. | Shared auth, TLS, URL joining, and JSON handling belong in one client path. | `app/grafana_client.py` |
| Keep per-request config resolution behind `get_grafana_config(ctx)`. | Header overrides and session caching must stay consistent across tools. | `app/context.py`, `app/config.py` |
| Preserve consolidated list responses. | Compact envelopes reduce Streamable HTTP chunking issues and improve agent readability. | `app/tools/*.py` |
| Treat `tokenomics.experiment/` as harness, not runtime. | Token-cost controls must not leak into production MCP behavior. | `tokenomics.experiment/`, `AGENTS.md` |

## Known Contracts

| Contract | Notes |
| --- | --- |
| Tool wrappers require injected `ctx`. | Raise `ValueError` if context injection fails. |
| Capability-gated tools must not register when Grafana lacks the required datasource or plugin. | Update registration tests when adding optional tools. |
| `reasoning_tokens` is nullable. | Store `null` when unavailable, never `0` unless explicitly reported as zero. |
| Startup auth/connection failures use process exit code `2`. | Preserve CLI behavior when changing startup checks. |

## Known Traps

- The repository may contain stale local virtualenv paths. Prefer `uv run ...` commands.
- Generic architecture examples from the paper are illustrative, not project requirements.
- Broad repository scans increase the same input-token cost this branch is designed to reduce.
- Instruction files must not contaminate the generic comparison branch.

## Update Rule

Add a row here when a task discovers a stable API contract, architectural decision, anti-pattern, or repeated failure mode. Do not log transient task notes here; keep run-specific data in `tokenomics.experiment/`.
