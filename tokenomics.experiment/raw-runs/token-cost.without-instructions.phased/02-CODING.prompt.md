[CODING]
You are running one phase of a multi-phase Codex tokenomics run. Work only on the current phase, but use the previous phase outputs as context. Start your user-facing progress/final messages with the current phase label.

## Task

Crie nova tool que retorne a versão dos componentes/plugins do Grafana e do próprio Grafana.

## Current Phase

CODING

## Phase Goal

Implement the planned code changes. Keep edits scoped to the task. Do not spend this phase on broad documentation unless needed by code behavior.

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
