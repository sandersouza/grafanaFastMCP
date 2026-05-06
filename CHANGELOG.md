# Changelog

All notable changes to this project are recorded in this file. This format follows the recommendations from "Keep a Changelog", and the project uses semantic versioning.

## [v1.2.3] - 2025-11-05

### Added / Fixed

- Added Grafana connection validation at startup, covering reachability, TLS, and authentication.
- Added TLS/SSL environment variables:
  - `GRAFANA_TLS_CERT_FILE`, `GRAFANA_TLS_KEY_FILE`, `GRAFANA_TLS_CA_FILE`, `GRAFANA_TLS_SKIP_VERIFY`.
- Added CLI flags for quick control:
  - `--ignore-ssl`: sets `GRAFANA_TLS_SKIP_VERIFY` to accept self-signed certificates.
  - `--check-connection`: runs a quick connectivity/authentication check and exits with the appropriate status code.
  - `--require-grafana` / `--no-require-grafana`: control whether the startup check is required. It is enabled by default except in tests.
- Improved Grafana API URL construction to avoid duplicated `/api/api` paths through path normalization in `GrafanaClient`.
- `GrafanaClient.request` and `get_json` now accept an optional `timeout` parameter for quick validation calls.
- Fixed a bug that prevented startup authentication verification due to incorrect indentation. Invalid tokens or credentials now abort immediately on HTTP 401.
- Kept HTTP 403 on `/api/user` as a warning when token/API key auth is configured, because the token may be valid but lack permissions.
- Improved logging setup so `--log-level` and `LOG_LEVEL` apply during startup checks. Full tracebacks are shown only in DEBUG.

### Tests and Validation

- Added unit tests covering TLS environment parsing and connection-check behavior:
  - `tests/test_config_tls_env.py`
  - `tests/test_main_check_connection.py`
- Added `pytest-cov` to the local development environment to allow `pytest --cov`.
- Test suite result: 200 passed.
- Local coverage report: around 85% overall. Lower coverage areas include `app/main.py`, `app/patches.py`, and some tools.

### Documentation

- Updated `env.example` and `README.md` to document the new TLS variables and CLI flags.

### Notes

- Work branch: `33-httpxerror-when-grafana-tlsssl-url-certificate-is-invalid-self-assign`.
- Added small path normalization and timeout improvements to avoid long startup blocks.

## [v1.2.1] - 2025-10-19

### Added

- Added PyPI publication support with `uv build` and `uv publish --token {PYPI_API_TOKEN}`.
- Added dynamic execution with `uvx grafana-fastmcp` directly from PyPI.
- Added minor TOML adjustments for the `app:__main__:main` execution endpoint.
- Added GitHub Actions workflow for automated PyPI publication from PR flow.

## [v1.2.0] - 2025-10-18

### Added

- Added official `uv`/`uvx` support for dependency management and execution through `pyproject.toml` and `uv.lock`.
- Added `COPILOT.md` with default instructions for agents and contributors, plus VS Code settings integration.
- Added PR workflow `.github/workflows/pr-package.yml` to run tests on Python 3.13 and optionally build/upload artifacts when the `build-artifacts` label is applied.
- Added explicit Hatch package configuration with `[tool.hatch.build.targets.wheel] packages = ["app", "mcp"]`.

### Changed

- Raised the project baseline to Python 3.13+ through `requires-python`, classifiers, and mypy settings.
- Left runtime and development dependencies unpinned directly and managed by `uv`; committed `uv.lock` for deterministic builds.
- Restructured `pyproject.toml` for uv compatibility and fixed TOML parsing issues.
- Expanded Makefile shortcuts for `uv-*` flows: sync, local, test, cov, lint, fmt, typecheck, package, and lock.
- Updated README with the new uv workflow, CI/PR badges, and PR artifact instructions.

### Fixed

- Fixed `pyproject.toml` parsing errors that prevented uv from building the project in editable mode.
- Fixed editable build issues with Hatchling through explicit package configuration.

### CI / Build

- Reduced PR workflow to run tests only on Python 3.13 by default for faster reviewer feedback.
- Restricted the main pipeline `.github/workflows/python-package.yml` to pushes on `main` using Python 3.13.
- Added conditional `build-artifacts` PR job to build wheel and PyInstaller binary when the `build-artifacts` label is applied.
- Added PyPI publication workflow triggered by `v*.*.*` tags for sdist and wheel artifacts. The published CLI exposes `grafana-fastmcp` for `uvx`.

### Documentation

- Updated `README.md` with uv instructions, repository badges, `build-artifacts` label explanation, and Python 3.13+ baseline notes.
- Added a `COPILOT.md` section with agent/contributor rules, quality guidance, and a quick checklist.

### Tests

- Confirmed tests with uv locally. The current suite had 197 passing tests after the changes.

### Compatibility

- Preserved the legacy `venv`/`pip` workflow as a fallback. uv is the recommended path for development and CI.

## [v1.1.0] - 2025-10-08

### Added

- Added a consolidated response pattern for all tools that return lists or arrays.
- Added a `type` field to identify the response type in all corrected tools.
- Added contextual metadata such as `total_count` and request parameters to all responses.
- Added complete documentation of the problems and solutions in `ISSUES.md`.

### Changed

- **BREAKING**: `search_dashboards` now returns `{"dashboards": [...], "total_count": N, ...}` instead of a raw array.
- **BREAKING**: `update_dashboard` now returns a consolidated response with metadata instead of the raw API response.
- **BREAKING**: Loki tools such as `list_loki_label_names` and `list_loki_label_values` now return consolidated objects.
- **BREAKING**: Pyroscope tools such as `list_pyroscope_label_names`, `list_pyroscope_label_values`, and `list_pyroscope_profile_types` now return consolidated objects.
- **BREAKING**: OnCall tools such as `list_oncall_schedules`, `list_oncall_teams`, and `list_oncall_users` now return consolidated objects.
- **BREAKING**: Alerting tools such as `list_alert_rules` and `list_contact_points` now return consolidated objects.
- **BREAKING**: Admin tools such as `list_teams` and `list_users_by_org` now return consolidated objects.

### Fixed

- **CRITICAL**: Eliminated the Streamable HTTP JSON chunking problem with ChatGPT/OpenAI that caused:
  - extreme slowness, with timeouts in most operations;
  - frequent session loss during tool execution;
  - partial data reads, often only the first chunk;
  - failed JSON parsing due to fragmentation.
- Updated all tests to reflect the new consolidated response formats.
- Updated test mocks to return correct consolidated structures.

### Performance

- Reduced latency by over 90% for tools that return lists.
- Eliminated timeouts caused by JSON chunking.
- Enabled instant parsing in ChatGPT/OpenAI with consolidated objects.
- Improved session stability during long operations.

### Tests

- All 197 tests passed after the fixes.
- Updated tests to validate consolidated structures.
- Validated Streamable HTTP compatibility.

### Documentation

- Documented identified problems and resolutions in `ISSUES.md`.
- Updated tool descriptions to mention chunking prevention.
- Updated response examples for all affected tools.

### Compatibility

- Fully compatible with Streamable HTTP and ChatGPT/OpenAI.
- Preserved original data in subfields.
- Kept original data accessible through specific fields for backward compatibility.

## [v1.0.1] - 2025-09-24

### Added

- Loaded the initial prompt from `instructions.md` or `MCP_INSTRUCTIONS_PATH`, allowing quick updates without rebuilds while keeping the packaged fallback.
- Implemented the `initialize` method for OpenAI MCP compliance, with session fallback support.
- Added cache usage in tools such as dashboard operations to reduce duplicate calls and unnecessary traffic.

### Changed

- `.env` loading from the repository root is automatic and prioritized. CLI arguments explicitly override `.env` values.
- Exported shell variables are considered only when no valid `.env` is found, avoiding unexpected overrides.
- `.env` resolution accepts `--env-file`, `ENV_FILE`, the current directory, and `find_dotenv`; paths are normalized with `expanduser()` and `resolve()`.
- CLI reads `APP_ADDRESS`, `BASE_PATH`, `STREAMABLE_HTTP_PATH`, `LOG_LEVEL`, and `TRANSPORT` from `.env` as defaults before parsing arguments.
- Standardized tool responses in a VS Code/Copilot-friendly style for MCP server usage in both environments.
- Tools are listed only when the Grafana instance has the required capability.

### Performance

- Improved dashboard, Prometheus, and Loki tool speed using cache in `ctx.request_context.session`.
- Added Prometheus defaults of `start=now-5m`, `end=now`, and `step=60` to avoid requiring a time window.
- Updated Sift `find_error_pattern_logs` to accept relative expressions such as `now-1h`.

### Tests and Observability

- Instruction loader reuses cache and prioritizes `MCP_INSTRUCTIONS_PATH`; added `tests/test_instructions.py`.
- Added credential-loading logs for 401 debugging while preserving transparent fallback behavior.

### Documentation and Build

- Expanded `README.md` and `instructions.md` with good practices for all tools and customizable prompts.
- Listed all supported variables in `env.example`, including timeouts and `MCP_INSTRUCTIONS_PATH`.
- Restored Makefile packaging to package only `run_app.py`, keeping `instructions.md` editable at the repository root.

### Commits

- [[`c5556de`](https://github.com/sandersouza/grafanaFastMCP/commit/c5556de)] Release v101-pre (see release.md)
- [[`91a3adf`](https://github.com/sandersouza/grafanaFastMCP/commit/91a3adf)] test:cover core server entrypoints
- [[`690d715`](https://github.com/sandersouza/grafanaFastMCP/commit/690d715)] Increasetests to near 90%
- [[`ad9d115`](https://github.com/sandersouza/grafanaFastMCP/commit/ad9d115)] Cachesupport add @dashboard
- [[`6521518`](https://github.com/sandersouza/grafanaFastMCP/commit/6521518)] Load realmcp package when available
- [[`e136882`](https://github.com/sandersouza/grafanaFastMCP/commit/e136882)] Oh boy! tomany fixes!!!
- [[`ca6590f`](https://github.com/sandersouza/grafanaFastMCP/commit/ca6590f)] feat:enforce streamable instructions and templating
- [[`b084c42`](https://github.com/sandersouza/grafanaFastMCP/commit/b084c42)] fixupdate_dashboard and reduce instructions.md to 1500 chars max
- [[`aa1cd50`](https://github.com/sandersouza/grafanaFastMCP/commit/aa1cd50)] so manyfix :S
- [[`7cf377f`](https://github.com/sandersouza/grafanaFastMCP/commit/7cf377f)] Handlemissing request in context config
- [[`546c01f`](https://github.com/sandersouza/grafanaFastMCP/commit/546c01f)] Filter MCPtools based on Grafana capabilities
- [[`b6b1a5e`](https://github.com/sandersouza/grafanaFastMCP/commit/b6b1a5e)] Ensuretool parameters include object schema
- [[`fb8c820`](https://github.com/sandersouza/grafanaFastMCP/commit/fb8c820)] Updaterealease.md
- [[`2bbe5d5`](https://github.com/sandersouza/grafanaFastMCP/commit/2bbe5d5)] FixFastMCP array schema items
- [[`2529709`](https://github.com/sandersouza/grafanaFastMCP/commit/2529709)] Ensurefetch ids schema defines item types
- [[`f37c8a9`](https://github.com/sandersouza/grafanaFastMCP/commit/f37c8a9)] Normalizetool parameter schemas
- [[`77c551e`](https://github.com/sandersouza/grafanaFastMCP/commit/77c551e)] Recursively normalize array schemas for tools
- [[`a68e584`](https://github.com/sandersouza/grafanaFastMCP/commit/a68e584)] Revert "Normalize tool parameter schemas"
- [[`d58bf7a`](https://github.com/sandersouza/grafanaFastMCP/commit/d58bf7a)] ddcomprehensive guidance for resource updates, dashboards, and Prom...
- [[`88a3c8c`](https://github.com/sandersouza/grafanaFastMCP/commit/88a3c8c)] A Improvedashboard tool schema and graceful shutdown
- [[`b583a96`](https://github.com/sandersouza/grafanaFastMCP/commit/b583a96)] Refinefallback schema by excluding "array" type to prevent nested ar...
- [[`b85c39b`](https://github.com/sandersouza/grafanaFastMCP/commit/b85c39b)] Updatedocumentation and tests: replace release notes with changelog...

## [v1.0.0] - 2025-02-08

### Added

- First stable version of the Grafana FastMCP server/CLI compatible with the OpenAI MCP connector, using STDIO as the default transport and supporting SSE and Streamable HTTP.
- MCP tools for Grafana dashboards, datasources, alerting, incident, OnCall, Prometheus, Loki, Pyroscope, Sift, navigation, and admin APIs, with validated protocol-compliant schemas.
- PyInstaller package through `make package`, generating the single binary `dist/grafana-mcp`.

### Changed

- Normalized queries and required parameters, including `query` in `search`/`search_dashboards` and `id` in `fetch`.
- Added support for relative time expressions in Grafana Asserts, such as `now-1h` and `now-1d+2h`.
- Added documentation with Claude integration examples for SSE, Streamable HTTP, and STDIO, plus packaging instructions.

### Stability

- Adjusted Streamable HTTP transport with configurable `MCP_STREAMABLE_HTTP_TIMEOUT_*` timeouts and reduced default log noise.

### Tests

- Added automated tests for search tools and Asserts to guarantee the MCP contract.

---

Notes:

- Dates use ISO format: YYYY-MM-DD. `Unreleased` entries can be published at any time.
- Sections are organized by category: Added, Changed, Fixed, Removed, Deprecated, Security, Performance, Documentation, Build/CI, and Tests.
