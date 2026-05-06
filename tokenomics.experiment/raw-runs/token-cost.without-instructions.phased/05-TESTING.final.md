TESTING: Validação concluída. Não precisei alterar runtime nem testes da tool; só atualizei os registros locais da fase em `ISSUES.md`, `docs/issues/grafana-versions-tool.md` e `docs/handoff/test/without-agent-instructions.md`.

Passou:
- `python -m pytest tests/test_tools_versions.py tests/test_tools_registration.py`: 8 passed
- `python -m pytest`: 210 passed
- `ruff check app/tools/versions.py app/tools/__init__.py tests/test_tools_versions.py tests/test_tools_registration.py`: passed

Limitações/falhas separadas:
- `uv run ...` não rodou porque `uv` não está instalado.
- `ruff check .` ainda falha por débitos preexistentes fora da feature: F401/F841 em `app/patches.py`, `tests/test_entrypoints.py`, `tests/test_main.py`, `tests/test_patches.py`, `tests/test_tool_availability.py`, `tests/test_tools_alerting.py`, `tests/test_tools_loki.py` e `tests/test_tools_pyroscope.py`.