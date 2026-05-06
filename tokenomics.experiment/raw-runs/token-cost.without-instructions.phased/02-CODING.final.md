CODING: Implementado `get_grafana_versions`.

A nova tool está em [app/tools/versions.py](/Users/sandersouza/Developer/grafanaFastMCP/app/tools/versions.py:84) e chama `/health` + `/plugins`, retornando payload consolidado com `grafana`, `plugins`, `total_count` e `type`. Também foi registrada sem capability gate em [app/tools/__init__.py](/Users/sandersouza/Developer/grafanaFastMCP/app/tools/__init__.py:102).

Adicionei testes em [tests/test_tools_versions.py](/Users/sandersouza/Developer/grafanaFastMCP/tests/test_tools_versions.py:63) e cobertura de registro em [tests/test_tools_registration.py](/Users/sandersouza/Developer/grafanaFastMCP/tests/test_tools_registration.py:63). Atualizei o README e ISSUES com a entrada mínima da feature.

Verificação:
- `uv run ...` não pôde rodar: `uv` não está instalado.
- `python -m pytest`: `210 passed`
- `ruff check app/tools/versions.py app/tools/__init__.py tests/test_tools_versions.py tests/test_tools_registration.py`: passou
- `ruff check .`: falhou por débitos preexistentes fora do escopo, como imports não usados em `app/patches.py`, `tests/test_entrypoints.py`, `tests/test_main.py` e outros.