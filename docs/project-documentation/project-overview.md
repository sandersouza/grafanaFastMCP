# Project Overview

`grafanaFastMCP` is a Python MCP server/CLI that exposes Grafana capabilities to MCP-compatible agents. It supports STDIO, SSE, and Streamable HTTP transports and focuses on OpenAI/ChatGPT MCP compatibility.

The server provides tools for:

- dashboard search, fetch, summary, targeted patching, and update;
- datasource listing and lookup;
- Prometheus metadata, labels, metric names, and PromQL queries;
- Loki labels, log queries, and stats;
- Pyroscope label/profile metadata and profile fetch;
- Grafana Alerting rule/contact point discovery;
- Grafana Incident and OnCall workflows through the IRM plugin;
- Grafana Asserts and Sift plugin workflows;
- deeplink generation for dashboards, panels, and Explore.

## Important Runtime Entry Points

| File | Role |
| --- | --- |
| `app/main.py` | CLI parsing, `.env` loading, startup checks, transport selection, server run. |
| `app/server.py` | Creates `FastMCP`, loads instructions, applies transport patches, registers tools. |
| `app/tools/__init__.py` | Detects Grafana capabilities and conditionally registers tool groups. |
| `app/context.py` | Resolves per-request Grafana configuration and caches it in the MCP session. |
| `app/config.py` | Reads env/header configuration and TLS/auth settings. |
| `app/grafana_client.py` | Shared async HTTP client for Grafana REST API calls. |
| `app/patches.py` | Monkey patches upstream MCP/FastMCP transport behavior for compatibility. |
| `mcp/server/fastmcp.py` | Local lightweight FastMCP shim used in tests and fallback runtimes. |

## Runtime Summary

```mermaid
flowchart TD
    CLI[app/main.py] --> Env[Load .env and CLI overrides]
    Env --> Checks{Grafana startup checks?}
    Checks -->|enabled| Health[/api/health and /api/user]
    Checks -->|disabled or passed| Factory[app/server.py create_app]
    Factory --> Instructions[app/instructions.py]
    Factory --> Patches[app/patches.py]
    Factory --> Registry[app/tools/register_all]
    Registry --> Capabilities[Detect datasources and plugins]
    Registry --> Tools[Register supported MCP tools]
    Tools --> Run[FastMCP.run transport]
    Run --> STDIO[STDIO]
    Run --> SSE[SSE]
    Run --> HTTP[Streamable HTTP]
```

## Project Constraints

- Python package metadata lives in `pyproject.toml`; runtime dependencies are `httpx`, `mcp`, `python-dotenv`, and `starlette`.
- `uv` is the preferred dependency workflow, but `venv`/`pip` fallbacks remain in the Makefile.
- Tool responses often use compact consolidated objects to avoid streamable HTTP JSON chunking issues with ChatGPT/OpenAI.
- Capability-dependent tools are skipped if the Grafana instance lacks required plugins or datasource types.
- Tests force the local MCP shim through `GRAFANA_FASTMCP_USE_STUB=1` in `tests/conftest.py`.

