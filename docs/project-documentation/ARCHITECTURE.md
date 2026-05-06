# Runtime Architecture

The architecture is a modular MCP server around a shared Grafana HTTP client and domain-specific tool modules.

## Main Components

```mermaid
flowchart TD
    User[CLI or packaged executable] --> Main[app/main.py]
    Main --> DotEnv[dotenv/env resolution]
    Main --> Startup[Optional Grafana startup checks]
    Startup --> Client[GrafanaClient]
    Main --> AppFactory[create_app]
    AppFactory --> Instructions[load_instructions]
    AppFactory --> PatchLayer[transport patches]
    AppFactory --> FastMCP[FastMCP app]
    AppFactory --> RegisterAll[register_all]
    RegisterAll --> CapabilityDetection[detect_capabilities]
    CapabilityDetection --> GrafanaAPI[Grafana /datasources and /plugins]
    RegisterAll --> ToolModules[Domain tool modules]
    ToolModules --> Context[get_grafana_config]
    Context --> Config[env/header/session config]
    ToolModules --> GrafanaClient[Grafana REST client]
    GrafanaClient --> Grafana[Grafana API and datasource proxy]
```

## CLI And Startup Flow

`app/main.py` is responsible for:

- loading `.env` from the project root or fallback locations;
- applying CLI overrides to environment variables;
- configuring logging and reducing noisy loggers;
- optionally checking Grafana health/auth;
- creating the app with `create_app`;
- running the selected transport.

```mermaid
sequenceDiagram
    participant User
    participant Main as app/main.py
    participant Config as app/config.py
    participant Client as GrafanaClient
    participant Server as app/server.py
    participant MCP as FastMCP

    User->>Main: python -m app --transport streamable-http
    Main->>Main: parse args and load .env
    Main->>Config: grafana_config_from_env()
    alt check connection or require Grafana
        Main->>Client: GET /api/health
        Main->>Client: GET /api/user
    end
    Main->>Server: create_app(host, port, paths)
    Server->>Server: load instructions and apply patches
    Server->>MCP: instantiate mcp-grafana app
    Server->>MCP: register tools
    Main->>MCP: run(transport)
```

## Tool Execution Flow

Every MCP tool follows the same operational shape:

1. FastMCP injects `ctx`.
2. The tool validates that `ctx` is present.
3. The tool resolves `GrafanaConfig` via `get_grafana_config(ctx)`.
4. The tool creates `GrafanaClient` or a datasource proxy client.
5. The tool calls Grafana.
6. The tool returns either raw API data for detail fetches or a compact consolidated response for large/list operations.

```mermaid
sequenceDiagram
    participant Host as MCP Host
    participant Tool as app/tools/<domain>.py
    participant Context as app/context.py
    participant Config as app/config.py
    participant Client as GrafanaClient
    participant Grafana

    Host->>Tool: call tool with arguments and ctx
    Tool->>Context: get_grafana_config(ctx)
    Context->>Config: env/header merge
    Context-->>Tool: cached GrafanaConfig
    Tool->>Client: request endpoint
    Client->>Grafana: HTTP request
    Grafana-->>Client: JSON/text response
    Client-->>Tool: parsed data
    Tool-->>Host: raw or consolidated result
```

## Transport Patch Layer

`app/patches.py` modifies upstream MCP behavior at runtime. These patches are intentional compatibility shims.

| Patch | Purpose |
| --- | --- |
| `ensure_streamable_http_accept_patch` | Allows clients that send only `text/event-stream`, wildcard, or relaxed Accept headers. |
| `ensure_streamable_http_server_patch` | Runs Streamable HTTP with configurable uvicorn timeouts. |
| `ensure_sse_server_patch` | Stores the uvicorn server instance for graceful shutdown. |
| `ensure_streamable_http_instructions_patch` | Emits `session.update` preprompt events during initialization. |
| `ensure_sse_post_alias_patch` | Allows JSON-RPC POST delivery on the SSE endpoint. |

```mermaid
flowchart LR
    create_app --> set_instructions
    create_app --> accept_patch
    create_app --> server_patch
    create_app --> sse_patch
    create_app --> instructions_patch
    create_app --> sse_alias_patch
    accept_patch --> StreamableHTTPTransport
    server_patch --> FastMCPRunHTTP
    sse_patch --> FastMCPRunSSE
    instructions_patch --> SessionUpdate
    sse_alias_patch --> StarletteRoutes
```

## Capability-Gated Registration

`app/tools/__init__.py` registers always-available tools first, then skips optional domains based on Grafana capability detection.

```mermaid
flowchart TD
    RegisterAll --> Always[admin, datasources, dashboard, alerting, navigation, search]
    RegisterAll --> Detect[detect_capabilities]
    Detect --> Datasources[/datasources]
    Detect --> Plugins[/plugins]
    Detect --> Optional{Capability present?}
    Optional -->|loki datasource| Loki
    Optional -->|prometheus datasource| Prometheus
    Optional -->|pyroscope datasource| Pyroscope
    Optional -->|grafana-irm-app| IncidentAndOnCall
    Optional -->|grafana-asserts-app| Asserts
    Optional -->|grafana-ml-app| Sift
```

