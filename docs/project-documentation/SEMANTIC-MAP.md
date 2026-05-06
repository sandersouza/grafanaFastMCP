# Semantic Map

This map compresses repository ownership so agents can jump to the smallest useful context.

## Runtime Ownership

| Concern | Primary owner | Supporting files | Closest tests |
| --- | --- | --- | --- |
| CLI parsing, `.env`, startup checks, transport selection | `app/main.py` | `app/server.py`, `app/config.py` | `tests/test_main*.py`, `tests/test_server.py` |
| FastMCP app creation and route setup | `app/server.py` | `app/patches.py`, `app/instructions.py` | `tests/test_server.py`, `tests/test_patches*.py` |
| Grafana env/header configuration | `app/config.py` | `app/context.py`, `env.example` | `tests/test_config*.py`, `tests/test_context.py` |
| Shared Grafana REST access | `app/grafana_client.py` | `app/config.py` | `tests/test_grafana_client.py` |
| Capability detection and registration | `app/tools/__init__.py` | `app/tools/availability.py` | `tests/test_tool_availability.py`, `tests/test_tools_registration.py` |
| MCP schema and local test shim | `mcp/server/fastmcp.py` | `mcp/server/streamable_http.py` | `tests/test_fastmcp*.py`, `tests/test_streamable_http_accept.py` |
| Session instructions and preprompt delivery | `app/instructions.py` | `instructions.md`, `instructions-long.md`, `app/patches.py` | `tests/test_instructions.py`, `tests/test_patches.py` |
| Tokenomics experiment harness | `tokenomics.experiment/` | `AGENTS.md`, `tests/fixtures/` | `tests/test_tokenomics_normalize.py` |

## Tool Domain Ownership

| Domain | Tool module | External surface |
| --- | --- | --- |
| Dashboards | `app/tools/dashboard.py` | Dashboard fetch, summary, panel query extraction, targeted patch/update. |
| Search | `app/tools/search.py` | Dashboard and folder search. |
| Datasources | `app/tools/datasources.py` | Datasource listing, lookup, proxy routing foundations. |
| Prometheus | `app/tools/prometheus.py` | PromQL, metric metadata, labels, series-like exploration. |
| Loki | `app/tools/loki.py` | Log queries, labels, stats, datasource proxy calls. |
| Pyroscope | `app/tools/pyroscope.py` | Profile metadata and profile fetch workflows. |
| Alerting | `app/tools/alerting.py` | Alert rules and contact point discovery. |
| Incident and OnCall | `app/tools/incident.py`, `app/tools/oncall.py` | IRM plugin workflows. |
| Asserts and Sift | `app/tools/asserts.py`, `app/tools/sift.py` | Plugin-gated investigation workflows. |
| Navigation | `app/tools/navigation.py` | Grafana deeplinks. |
| Admin | `app/tools/admin.py` | Grafana version, plugin inventory, health-style metadata. |

## Read Strategy

1. Classify the requested behavior by concern or tool domain.
2. Read the primary owner and closest test.
3. Use `rg` for exact helper, endpoint, or tool names before opening additional files.
4. Stop reading once the local pattern and acceptance test are clear.

## Update Rule

Update this map when adding a new runtime subsystem, tool domain, shared helper, or test ownership boundary.
