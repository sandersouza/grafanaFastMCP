# Good Practices: uv and uvx

Adopt [uv](https://github.com/astral-sh/uv) as the default dependency and execution manager for development and CI, while keeping compatibility with existing `venv`/`pip` workflows when needed.

## Definition of Ready

- Move project metadata and dependencies to `pyproject.toml` using PEP 621 and uv dependency groups.
- Commit `uv.lock` for deterministic builds.
- Add `uv` and `uvx` commands to the Makefile or scripts.
- Update `README.md` with usage instructions.
- Keep the existing `venv`/`pip` path as a fallback while the migration settles.

## Definition of Done

- `pyproject.toml` includes complete `[project]` metadata, dependencies, and optional development dependency groups.
- `uv.lock` is versioned.
- `uv run pytest` passes.
- `uv run ruff check .` passes when Ruff is configured for the project.
- `uvx grafana-fastmcp` works after package publication.
- CI uses uv as the preferred installation and execution path.

## Notes

- Use `uv sync --dev --all-extras` for local setup.
- Use `uv run -m app` for direct project execution.
- Use `uv build` for package artifacts.
- Use `uv publish --token "$PYPI_API_TOKEN"` for PyPI publication.
