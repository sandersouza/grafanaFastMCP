[![Tests](https://github.com/sandersouza/grafanaFastMCP/actions/workflows/tests.yml/badge.svg)](https://github.com/sandersouza/grafanaFastMCP/actions/workflows/tests.yml)
[![PR Package](https://github.com/sandersouza/grafanaFastMCP/actions/workflows/pr-package.yml/badge.svg)](https://github.com/sandersouza/grafanaFastMCP/actions/workflows/pr-package.yml)

# Grafana FastMCP Server / CLI

English documentation. The original Portuguese README is available at [README-PTBR.md](./README-PTBR.md).

`grafanaFastMCP` is a Python 3.13+ MCP server and CLI for Grafana. It exposes Grafana resources as Model Context Protocol tools and supports STDIO, SSE, and Streamable HTTP transports.

The project is built for agentic clients such as ChatGPT/OpenAI-compatible MCP hosts, Claude Desktop, and local automation agents. It provides tools for dashboards, datasources, Loki logs, alerting, incidents, on-call workflows, Prometheus, Pyroscope, Sift, and other Grafana APIs.

## Highlights

- FastMCP-based MCP server.
- Multiple transports: STDIO, SSE, and Streamable HTTP.
- Grafana authentication through token, API key, basic auth, or OIDC bearer token.
- Optional startup connection validation.
- TLS/SSL configuration through environment variables and CLI flags.
- Consolidated responses for list-like tools to reduce Streamable HTTP JSON chunking issues.
- `uv` and `uvx` workflow for local development and package execution.
- PyPI publication and PyInstaller packaging support.

## Project Structure

```text
grafanaFastMCP/
├── app/
│   ├── main.py              # CLI entrypoint, transport setup, tool registration
│   ├── config.py            # environment and CLI configuration
│   ├── grafana_client.py    # async Grafana HTTP client
│   ├── instructions.py      # MCP session instruction loading
│   └── tools/               # MCP tool modules grouped by Grafana capability
├── docs/project-documentation/
│   └── *.md                 # architecture and agent onboarding docs
├── tests/                   # pytest suite
├── tokenomics.experiment/   # token-cost experiment harness
├── pyproject.toml
├── uv.lock
└── README.md
```

## Requirements

- Python 3.13 or newer.
- A Grafana instance.
- Grafana credentials with permissions for the APIs you want to expose.
- `uv` for the recommended development workflow.

Install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install dependencies:

```bash
uv sync --dev --all-extras
```

## Quick Start

Run the MCP server with STDIO:

```bash
uv run -m app \
  --address localhost:8000 \
  --log-level INFO \
  --transport stdio
```

Run with SSE:

```bash
uv run -m app \
  --address localhost:8000 \
  --transport sse
```

Run with Streamable HTTP:

```bash
uv run -m app \
  --address localhost:8000 \
  --transport streamable-http \
  --streamable-http-path /mcp
```

Run the published package with `uvx`:

```bash
uvx grafana-fastmcp \
  --grafana-url https://grafana.example.com \
  --grafana-api-key "$GRAFANA_API_KEY" \
  --transport stdio
```

## Configuration

Configuration can be provided through CLI flags, environment variables, or a `.env` file.

Common environment variables:

| Variable | Purpose |
| --- | --- |
| `GRAFANA_URL` | Base URL for the Grafana instance. |
| `GRAFANA_TOKEN` | Grafana bearer token. |
| `GRAFANA_API_KEY` | Grafana API key. |
| `GRAFANA_USERNAME` | Username for basic auth. |
| `GRAFANA_PASSWORD` | Password for basic auth. |
| `GRAFANA_OIDC_TOKEN` | OIDC bearer token. |
| `GRAFANA_SSL_VERIFY` | Enable or disable TLS certificate verification. |
| `GRAFANA_CA_BUNDLE` | Custom CA bundle path. |
| `GRAFANA_CLIENT_CERT` | Client certificate path. |
| `GRAFANA_CLIENT_KEY` | Client certificate key path. |
| `APP_ADDRESS` | Default bind address. |
| `BASE_PATH` | Optional base path for HTTP transports. |
| `STREAMABLE_HTTP_PATH` | Streamable HTTP endpoint path. |
| `TRANSPORT` | Default transport. |
| `LOG_LEVEL` | Runtime log level. |

Useful CLI flags:

```bash
--grafana-url <url>
--grafana-api-key <key>
--grafana-token <token>
--grafana-username <username>
--grafana-password <password>
--ignore-ssl
--check-connection
--require-grafana
--no-require-grafana
--transport stdio|sse|streamable-http
--address <host:port>
--base-path <path>
--streamable-http-path <path>
--log-level INFO|DEBUG|WARNING|ERROR
```

Example:

```bash
uv run -m app \
  --grafana-url https://grafana.example.com \
  --grafana-api-key "$GRAFANA_API_KEY" \
  --check-connection \
  --transport streamable-http
```

## OpenAI MCP Compatibility

The server follows OpenAI MCP compatibility expectations:

- `search` and `search_dashboards` accept a simple string `query`.
- `fetch` accepts a string `id` and optional enrichment parameters.
- STDIO, SSE, and Streamable HTTP transports are supported.
- Tool metadata, session instructions, and tool schemas are published through MCP.
- Consolidated responses avoid fragmented JSON payloads in Streamable HTTP clients.

## Available Tool Groups

### Admin

- List organizations.
- List and inspect users.
- Inspect folders and permissions where supported.

### Alerting

- List alert rules.
- Inspect alert rule details.
- Work with contact points and notification policies when available.

### Asserts

- Query Grafana Asserts data.
- Support relative time expressions such as `now-1h`.

### Dashboards

- Search dashboards.
- Fetch dashboard details.
- Inspect dashboard metadata and panels.
- Provide OpenAI-compatible `search` and `fetch` flows.

### Datasources

- List datasources.
- Inspect datasource details.
- Query datasource metadata where supported.

### Incident

- List incidents.
- Fetch incident details.
- Inspect incident activity and related metadata.

### Loki

- Run Loki log queries.
- Query labels and label values.
- Fetch log volume and series metadata.

### Navigation

- Expose Grafana navigation resources and shortcuts where available.

### OnCall

- List schedules, teams, escalation chains, and on-call metadata when the integration is available.

### Prometheus

- Run Prometheus queries.
- Inspect labels, series, and metadata.
- Support common Prometheus HTTP API operations exposed through Grafana.

### Pyroscope

- Query profiling data where the integration is available.
- Inspect profiling labels and metadata.

### Search

- Generic MCP search over Grafana resources.
- Dashboard-focused search for MCP clients that expect search/fetch style workflows.

### Sift

- List recent Sift investigations.
- Fetch investigation details.
- Fetch analysis results.
- Run `ErrorPatternLogs` checks through `find_error_pattern_logs`.

Each tool uses the shared async HTTP client in `app/grafana_client.py`, which adds the required headers and authentication for the Grafana API. Consolidated tool responses include metadata such as `total_count`, `type`, request context, and preserved original data for compatibility.

## Transports

### SSE

With `--transport sse`, FastMCP exposes two main paths:

1. `GET /sse`: opens the SSE session and emits MCP events.
2. `POST /messages/`: receives client messages, tool calls, and confirmations.

If `--base-path /grafana` is used, the paths become `/grafana/sse` and `/grafana/messages/`.

### Streamable HTTP

With `--transport streamable-http`, the server exposes a single HTTP endpoint. The default path is `/mcp`, and it can be changed with `--streamable-http-path`.

Useful timeout environment variables:

| Variable | Default |
| --- | --- |
| `MCP_STREAMABLE_HTTP_TIMEOUT_KEEP_ALIVE` | `65` seconds |
| `MCP_STREAMABLE_HTTP_TIMEOUT_NOTIFY` | `120` seconds |
| `MCP_STREAMABLE_HTTP_TIMEOUT_GRACEFUL_SHUTDOWN` | max notify timeout or `120` seconds |

### STDIO

With `--transport stdio`, the server runs as a child process and communicates through standard input and output. This is the best mode for local clients and environments that should not expose HTTP ports.

## Claude Desktop Examples

### SSE

```json
{
  "mcpServers": {
    "grafana-fastmcp-sse": {
      "command": "uv",
      "args": [
        "run",
        "-m",
        "app",
        "--transport",
        "sse",
        "--address",
        "localhost:8000"
      ],
      "env": {
        "GRAFANA_URL": "https://grafana.example.com",
        "GRAFANA_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Streamable HTTP

```json
{
  "mcpServers": {
    "grafana-fastmcp-http": {
      "command": "uv",
      "args": [
        "run",
        "-m",
        "app",
        "--transport",
        "streamable-http",
        "--address",
        "localhost:8000",
        "--streamable-http-path",
        "/mcp"
      ],
      "env": {
        "GRAFANA_URL": "https://grafana.example.com",
        "GRAFANA_API_KEY": "your-api-key"
      }
    }
  }
}
```

### STDIO

```json
{
  "mcpServers": {
    "grafana-fastmcp-stdio": {
      "command": "uv",
      "args": [
        "run",
        "-m",
        "app",
        "--transport",
        "stdio"
      ],
      "env": {
        "GRAFANA_URL": "https://grafana.example.com",
        "GRAFANA_API_KEY": "your-api-key"
      }
    }
  }
}
```

For a packaged binary workflow, run `make package` first and point the client command to `dist/grafana-mcp`.

## Development Commands

```bash
uv sync --dev --all-extras
uv run pytest
uv run ruff check .
uv build
```

Makefile targets are also available for local virtual environments, uv workflows, packaging, Docker, and Podman.

## Tests

Run the full test suite:

```bash
uv run pytest
```

Run lint:

```bash
uv run ruff check .
```

The project includes unit and regression coverage for configuration, startup behavior, instruction loading, tool helpers, transport-related behavior, and tokenomics normalization utilities.

## Additional Documentation

- [CHANGELOG.md](./CHANGELOG.md): release history.
- [README-PTBR.md](./README-PTBR.md): Portuguese README.
- [docs/project-documentation/](./docs/project-documentation/): architecture and onboarding documentation.
- [tokenomics.experiment/](./tokenomics.experiment/): token-cost experiment harness.

## Next Steps

Add new Grafana-specific MCP tools under `app/tools/` and cover them with focused tests under `tests/`. For larger changes, update the project documentation and changelog with the relevant behavior, commands, or schema changes.
