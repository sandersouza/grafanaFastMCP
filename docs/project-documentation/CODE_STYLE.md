# Code Style

This page captures local style rules that help agents edit without rediscovering conventions. It is project documentation, not runtime behavior.

## Python Style

| Area | Local rule |
| --- | --- |
| Formatting | Follow Ruff-compatible Python style. Keep imports explicit and grouped by standard library, third-party, then local modules. |
| Typing | Use modern Python 3.13 syntax where the surrounding code does. Preserve existing annotations when editing helpers and tool wrappers. |
| Async | Grafana calls are async. Do not introduce sync HTTP calls in tool execution paths. |
| Errors | Raise `ValueError` for invalid tool inputs or unexpected Grafana payload shapes. Let `GrafanaClient` raise `GrafanaAPIError` for HTTP failures. |
| Comments | Add comments only for non-obvious compatibility shims or complex payload normalization. |

## Tool Module Style

- Keep private helper functions above `register`.
- Keep public MCP wrappers inside `register(app)`.
- Validate `ctx is not None` before resolving config.
- Use `get_grafana_config(ctx)` for Grafana configuration.
- Use `GrafanaClient` for normal Grafana REST calls.
- Use datasource proxy clients only where that pattern already exists for Prometheus, Loki, Pyroscope, or related datasource APIs.
- Preserve compact consolidated response envelopes for list/search/update operations.

## Naming

| Surface | Convention |
| --- | --- |
| Tool names | Snake case, domain-prefixed when useful, such as `query_prometheus` or `list_loki_label_names`. |
| Internal helpers | Snake case with a leading underscore for module-private helpers. |
| Public parameters | Match Grafana/API-facing naming where already exposed, including camelCase names such as `datasourceUid` and `folderUid`. |
| Tests | Match the touched domain with `tests/test_tools_<domain>.py` when possible. |

## Avoid

- Do not instantiate `httpx.AsyncClient` directly in ordinary tool modules.
- Do not return huge raw arrays for list-like operations when a consolidated response is available.
- Do not add architectural labels from unrelated stacks such as FastAPI, SQLAlchemy, CQRS, or DDD unless the runtime actually adopts them.
- Do not refactor neighboring modules just to normalize style.

## Validation

Use focused tests first, then broader checks when Python behavior changed:

```sh
uv run pytest
uv run ruff check .
```
