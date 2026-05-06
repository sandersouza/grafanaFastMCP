# Agent Instructions

## Project

`grafanaFastMCP` is a Python 3.13+ MCP server/CLI built with FastMCP. It exposes Grafana capabilities as MCP tools across STDIO, SSE, and Streamable HTTP transports.

The runtime entrypoint is `app/main.py`. Tool modules live under `app/tools/`, shared Grafana API access lives in `app/grafana_client.py`, configuration lives in `app/config.py`, and tests live under `tests/`.

## Branch Role

This branch, `test/tokenomics-tests-with-instructions`, is the instrumentation branch for token-cost reduction techniques. Any technique intended to reduce token usage must be designed, documented, instrumented, and validated here before comparison against the generic branch or promotion to another workflow.

This branch may contain specialized instructions, semantic maps, architecture summaries, log normalization scripts, and stage-labeling conventions. These artifacts are part of the tokenomics experiment and must not be treated as MCP runtime behavior.

## Working Rules

- Read the current file before changing any tool, payload, documentation, or test.
- Prefer existing project patterns over new abstractions.
- Keep runtime changes separate from experiment harness changes.
- Do not introduce specialized instructions into `test/tokenomics-tests-without-instructions`.
- Do not use results from branches contaminated by incorrect or unrelated instructions.
- When changing runtime behavior, add or update focused tests.
- Use `uv run pytest` and `uv run ruff check .` for verification when the change touches Python behavior.
- If you are not familiar with the project, read the documentation in `docs/project-documentation/*.md` before making changes.

## MCP Runtime Pattern

The project follows a local pattern named **Capability-Gated MCP Tool Facade**:

- `app/main.py` creates and configures the FastMCP application.
- `app/config.py` reads CLI and environment configuration.
- `app/grafana_client.py` centralizes async HTTP access to Grafana.
- `app/tools/*.py` register focused MCP tool groups.
- Tool registration is conditional on Grafana capabilities where applicable.
- List-like tool responses are normalized into consolidated payloads to reduce Streamable HTTP chunking issues.

## Tokenomics Experiment Rules

- Treat `tokenomics.experiment/` as the experiment harness, not production runtime.
- Normalize logs through `tokenomics.experiment/scripts/normalize_agent_logs.py`.
- Keep task definitions stable between branches.
- Compare runs by branch, task, stage, token usage, elapsed time, human prompts, file churn, test/lint loops, and final result.
- Record `reasoning_tokens` as `null` when unavailable, never as `0`.
