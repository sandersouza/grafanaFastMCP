# Tool de versões do Grafana

## Síntese

Implementada a tool `get_grafana_versions` para retornar a versão do Grafana e versões conhecidas dos plugins/componentes instalados.

## Escopo

- Consulta `/api/health` para dados de versão, commit, buildstamp, database e edition do Grafana.
- Consulta `/api/plugins` para plugins/componentes instalados.
- Normaliza plugins em resposta consolidada com `id`, `name`, `type`, `enabled`, `pinned`, `module`, `baseUrl` e `version`.
- Preserva `version: null` quando o Grafana não informa versão do plugin/componente.
- Registra a tool sem capability gate, pois depende apenas de endpoints centrais do Grafana.

## Validação

- `python -m pytest tests/test_tools_versions.py tests/test_tools_registration.py`
- `python -m pytest`
- `ruff check app/tools/versions.py app/tools/__init__.py tests/test_tools_versions.py tests/test_tools_registration.py`
- `ruff check app/tools/versions.py app/tools/__init__.py tests/test_tools_versions.py tests/test_tools_registration.py tests/test_tokenomics_run_codex_phases.py tokenomics.experiment/scripts/run_codex_phases.py`
- Fase `TESTING`: `python -m pytest tests/test_tools_versions.py tests/test_tools_registration.py` passou com 8 testes.
- Fase `TESTING`: `python -m pytest` passou com 210 testes.
- Fase `TESTING`: `ruff check app/tools/versions.py app/tools/__init__.py tests/test_tools_versions.py tests/test_tools_registration.py` passou.
- Fase `DOCUMENTATION`: validações anteriores reaproveitadas; nenhuma alteração de runtime ou teste foi necessária nesta fase.

## Observações

- `uv run` não foi usado nesta sessão porque `uv` não está disponível no ambiente local.
- `README-PTBR.md` não existe neste checkout.
- Na fase `CODE_REVIEW`, não foram identificados bugs de runtime, regressões, testes faltantes ou escopo acidental na tool `get_grafana_versions`.
- `ruff check .` ainda falha por débitos preexistentes fora do escopo em `app/patches.py` e testes antigos.
- Na fase `TESTING`, os débitos preexistentes reportados por `ruff check .` foram F401/F841 em `app/patches.py`, `tests/test_entrypoints.py`, `tests/test_main.py`, `tests/test_patches.py`, `tests/test_tool_availability.py`, `tests/test_tools_alerting.py`, `tests/test_tools_loki.py` e `tests/test_tools_pyroscope.py`.
- Na fase `DOCUMENTATION`, o README foi complementado para explicitar que `get_grafana_versions` usa `/api/health` e `/api/plugins`, retorna payload consolidado e preserva `version: null` quando a versão do plugin não vem da API.
