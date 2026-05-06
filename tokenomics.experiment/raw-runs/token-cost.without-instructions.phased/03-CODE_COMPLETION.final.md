CODE_COMPLETION: Finalizei a passada de integração.

A feature `get_grafana_versions` já estava consistente; mantive o runtime e completei a rastreabilidade adicionando:
- [docs/issues/grafana-versions-tool.md](/Users/sandersouza/Developer/grafanaFastMCP/docs/issues/grafana-versions-tool.md)
- [docs/handoff/test/without-agent-instructions.md](/Users/sandersouza/Developer/grafanaFastMCP/docs/handoff/test/without-agent-instructions.md)

Validação:
- `python -m pytest tests/test_tools_versions.py tests/test_tools_registration.py`: 8 passed
- `python -m pytest`: 210 passed
- `ruff check app/tools/versions.py app/tools/__init__.py tests/test_tools_versions.py tests/test_tools_registration.py`: passed
- `ruff check .`: falha por débitos preexistentes fora do escopo
- `uv` não está instalado neste ambiente, então `uv run ...` não pôde ser executado.