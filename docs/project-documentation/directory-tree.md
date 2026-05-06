# Directory Tree

This is the practical directory map. Generated artifacts and caches exist in the repo, but agents should usually ignore them.

```text
.
├── app/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── context.py
│   ├── grafana_client.py
│   ├── instructions.py
│   ├── main.py
│   ├── patches.py
│   ├── server.py
│   └── tools/
│       ├── __init__.py
│       ├── _label_matching.py
│       ├── admin.py
│       ├── alerting.py
│       ├── asserts.py
│       ├── availability.py
│       ├── dashboard.py
│       ├── datasources.py
│       ├── incident.py
│       ├── loki.py
│       ├── navigation.py
│       ├── oncall.py
│       ├── prometheus.py
│       ├── pyroscope.py
│       ├── search.py
│       └── sift.py
├── mcp/
│   └── server/
│       ├── fastmcp.py
│       └── streamable_http.py
├── tests/
├── scripts/
├── .github/
│   ├── workflows/
│   └── instructions/
├── docs/
│   └── project-documentation/
├── tokenomics.experiment/
├── Makefile
├── pyproject.toml
├── requirements.txt
├── env.example
├── Dockerfile
├── run_app.py
├── instructions.md
├── instructions-long.md
├── AGENTS.md
├── README.md
└── CHANGELOG.md
```

## What Each Directory Represents

| Directory | What it represents | When to edit |
| --- | --- | --- |
| `app/` | Main Python package and production runtime. It contains the CLI, app factory, config resolution, transport patches, shared Grafana HTTP client, instruction loader, and all MCP tools. | Edit for almost every runtime behavior change. |
| `app/tools/` | Domain modules that expose Grafana features as MCP tools. Each module owns private helpers plus a public `register(app)` function. | Edit when adding/fixing a tool, changing a tool response, or adjusting a Grafana domain workflow. |
| `mcp/` | Local lightweight MCP/FastMCP compatibility layer used mainly for tests and fallback runtimes. It mirrors enough of upstream MCP for schema generation, tool registration, STDIO handling, and Streamable HTTP accept-header tests. | Edit only when tool schema generation, local STDIO behavior, or the test shim needs to change. Do not put Grafana business logic here. |
| `tests/` | Automated test suite. It covers config, context, CLI startup, app factory, patches, MCP shim behavior, tool registration, and individual tool domains. | Edit with any behavior change. Add focused tests near the touched subsystem. |
| `tests/fixtures/` | Static test data used by tests. Currently includes tokenomics fixture data. | Edit when a test needs stable sample input/output. Keep fixtures small. |
| `scripts/` | Developer automation scripts outside the runtime path. Example: syncing `COPILOT.md` into VS Code settings. | Edit for repository maintenance automation, not for MCP runtime behavior. |
| `.github/` | GitHub-specific metadata: Actions workflows and instruction files used by coding assistants or repository automation. | Edit for CI, PR workflows, publish workflows, or GitHub instruction changes. |
| `.github/workflows/` | CI/CD workflows. PR tests, main branch tests, artifact builds, and PyPI publish are defined here. | Edit when changing test/build/publish automation. |
| `.github/instructions/` | Repository instructions for agent/contributor behavior. These are guidance files, not application runtime code. | Edit when changing development rules or agent workflow instructions. |
| `docs/` | Human/agent documentation that is part of the repository. | Edit when project knowledge, architecture, onboarding, or public docs need to change. |
| `docs/project-documentation/` | Deep project map generated for onboarding and token-cost reduction. It documents structure, architecture, semantic ownership, code style, code patterns, tool modules, config/security, testing, memory, worktree isolation, and agent workflow. | Edit whenever project architecture or coding patterns change. Agents should read this before broad code exploration. |
| `tokenomics.experiment/` | Experiment harness for measuring and reducing agent token cost. Contains experiment plans, schemas, tasks, scripts, and supporting paper/analysis material. | Edit when adding instrumentation, log normalization, token-cost experiments, or branch hygiene checks. |
| `.githooks/` | Optional local git hook helpers. Not automatically active unless copied/symlinked into `.git/hooks`. | Edit only for local developer workflow helpers. |
| `.vscode/` | Workspace editor settings and tasks. Can include generated Copilot instruction settings. | Edit only for workspace/editor automation. Avoid changing for runtime features. |
| `build/` | Generated PyInstaller build intermediate output. | Usually do not edit. Regenerate through packaging commands. |
| `dist/` | Generated distribution artifacts such as binaries, wheels, tarballs, and coverage output. | Usually do not edit. Regenerate through build/package workflows. |

## Important Root Files

| File | What it represents |
| --- | --- |
| `README.md` | Public project documentation and user-facing setup/usage guide. |
| `CHANGELOG.md` | Release and change history. |
| `AGENTS.md` | Agent-specific instructions for this tokenomics instrumentation branch. |
| `instructions.md` | Default compact MCP instruction prompt loaded by `app/instructions.py`. |
| `instructions-long.md` | Longer instruction reference for agent behavior and Grafana workflows. |
| `ISSUES.md` | Current branch/issue working context. Should stay focused on the active issue/feature. |
| `pyproject.toml` | Python package metadata, dependencies, build backend, uv dev dependencies, mypy/flake8 config. |
| `uv.lock` | Locked dependency graph for reproducible uv workflows. |
| `requirements.txt` | Runtime dependency fallback for pip/venv and Docker. |
| `Makefile` | Common development, test, lint, package, Docker, and uv commands. |
| `Dockerfile` | Container image definition for running the MCP server. |
| `env.example` | Environment variable template for Grafana credentials, server settings, transport, timeouts, and TLS. |
| `run_app.py` | Standalone entrypoint used by PyInstaller packaging. |
| `version.py`, `__version__.py` | Version metadata sources used by package/runtime code. |
| `grafana-mcp.spec` | PyInstaller spec file. |
| `pytest.ini` | Pytest configuration. |

## What To Edit

| Area | Main files |
| --- | --- |
| CLI/env/startup behavior | `app/main.py`, `app/config.py`, `tests/test_main.py`, `tests/test_config.py` |
| Server path/transport setup | `app/server.py`, `app/patches.py`, `tests/test_server.py`, `tests/test_patches.py` |
| Common Grafana HTTP behavior | `app/grafana_client.py`, `tests/test_grafana_client.py` |
| A Grafana tool | `app/tools/<domain>.py`, matching `tests/test_tools_<domain>.py` |
| Capability registration | `app/tools/__init__.py`, `app/tools/availability.py`, `tests/test_tool_availability.py`, `tests/test_tools_registration.py` |
| Instructions/preprompt behavior | `app/instructions.py`, `instructions.md`, `app/patches.py`, `tests/test_instructions.py`, `tests/test_patches.py` |
| Local MCP shim | `mcp/server/fastmcp.py`, `mcp/server/streamable_http.py`, `tests/test_fastmcp_*`, `tests/test_streamable_http_accept.py` |
| Tokenomics instrumentation | `tokenomics.experiment/`, `AGENTS.md`, `tests/test_tokenomics_normalize.py` |

## What To Ignore During Most Tasks

- `build/`, `dist/`, `.pytest_cache/`, `__pycache__/`, `.coverage`, `.DS_Store`;
- `.venv/` unless debugging local environment issues;
- generated PyInstaller files unless packaging is the task.
