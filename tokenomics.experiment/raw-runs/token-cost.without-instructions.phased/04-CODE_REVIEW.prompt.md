[CODE_REVIEW]
You are running one phase of a multi-phase Codex tokenomics run. Work only on the current phase, but use the previous phase outputs as context. Start your user-facing progress/final messages with the current phase label.

## Task

Crie nova tool que retorne a versão dos componentes/plugins do Grafana e do próprio Grafana.

## Current Phase

CODE_REVIEW

## Phase Goal

Review the local diff for bugs, regressions, missing tests, and accidental scope creep. Apply fixes that are necessary for the task.

## Previous Phase Outputs

## Previous Phase: DESIGN

DESIGN: Plano da fase de design concluído. Não editei arquivos.

**Plano**
Criar uma nova tool, provavelmente `get_grafana_versions`, registrada sempre, sem capability gate. Ela deve chamar:

- `/api/health` para versão do Grafana, commit/build info disponível e estado básico.
- `/api/plugins` para plugins/componentes instalados, extraindo `id`, `name`, `type`, `enabled`, `pinned`, `module`, `baseUrl` e versão a partir de `info.version` ou campos equivalentes quando existirem.

Resposta proposta, consolidada:

```json
{
  "grafana": {...},
  "plugins": [...],
  "total_count": 0,
  "type": "grafana_versions_result"
}
```

**Arquivos Prováveis**
- `app/tools/versions.py`: novo módulo da tool e helpers de normalização.
- `app/tools/__init__.py`: importar e registrar `versions.register`.
- `tests/test_tools_versions.py`: testes unitários dos helpers e da tool.
- `tests/test_tools_registration.py`: garantir que a tool aparece no `register_all`.
- `README.md`: adicionar seção/listagem da nova tool.
- `ISSUES.md` e possivelmente `docs/issues/*`: registrar síntese da sessão/branch na fase de implementação, conforme instruções locais. `README-PTBR.md` não existe neste checkout.

**Validação**
Na fase de implementação, rodar:

```bash
uv run pytest tests/test_tools_versions.py tests/test_tools_registration.py
uv run pytest
uv run ruff check .
```

**Riscos**
- O payload de `/api/plugins` pode variar entre versões do Grafana; a normalização deve aceitar lista direta e formatos com `items`/`plugins`.
- Nem todo plugin informa versão; nesses casos, retornar `version: null`, não inventar valor.
- “Componentes” pode significar algo além de plugins. Pelas APIs públicas e pelo contexto anterior, a interpretação mais segura é plugins/componentes instalados via `/api/plugins`.
- A pasta `docs/project-documentation` citada nas instruções não existe no checkout atual.

## Previous Phase: CODING

CODING: Implementado `get_grafana_versions`.

A nova tool está em [app/tools/versions.py](/Users/sandersouza/Developer/grafanaFastMCP/app/tools/versions.py:84) e chama `/health` + `/plugins`, retornando payload consolidado com `grafana`, `plugins`, `total_count` e `type`. Também foi registrada sem capability gate em [app/tools/__init__.py](/Users/sandersouza/Developer/grafanaFastMCP/app/tools/__init__.py:102).

Adicionei testes em [tests/test_tools_versions.py](/Users/sandersouza/Developer/grafanaFastMCP/tests/test_tools_versions.py:63) e cobertura de registro em [tests/test_tools_registration.py](/Users/sandersouza/Developer/grafanaFastMCP/tests/test_tools_registration.py:63). Atualizei o README e ISSUES com a entrada mínima da feature.

Verificação:
- `uv run ...` não pôde rodar: `uv` não está instalado.
- `python -m pytest`: `210 passed`
- `ruff check app/tools/versions.py app/tools/__init__.py tests/test_tools_versions.py tests/test_tools_registration.py`: passou
- `ruff check .`: falhou por débitos preexistentes fora do escopo, como imports não usados em `app/patches.py`, `tests/test_entrypoints.py`, `tests/test_main.py` e outros.

## Previous Phase: CODE_COMPLETION

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
