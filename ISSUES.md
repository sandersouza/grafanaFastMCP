## ✨ Feature: Suporte a uv/uvx
### Objetivo
Adotar o [uv](https://github.com/astral-sh/uv) como gerenciador padrão de dependências/execução para desenvolvimento e CI, mantendo compatibilidade com `venv`/`pip` existentes.

### Escopo e Expectativas
- Migrar metadados e dependências para `pyproject.toml` (PEP 621) com grupos de dependência do `uv`.
- Versionar `uv.lock` para builds determinísticos.
- Adicionar alvos `make` para fluxos comuns (sync, run, test, lint, fmt, typecheck, package) usando `uv/uvx`.
- Atualizar `README.md` com instruções de uso.
- Preservar os alvos atuais baseados em `venv`/`pip` como fallback.

### Definition of Ready (DOR)
- pyproject com:
    - [project] preenchido (nome, versão, requires-python, license)
    - dependencies, optional-dependencies (ex.: `sse`)
    - [tool.uv.dependency-groups] com dev (pytest, pytest-asyncio, pytest-cov, ruff, mypy)
- Makefile com esqueleto dos alvos `uv-*` definidos
- uv instalado localmente ou instruções claras de instalação
- Decisão de versionamento do `uv.lock` (sim: versionado)

### Definition of Done (DOD)
- `pyproject.toml` criado/atualizado com metadados e grupos do uv
- `Makefile` ampliado com alvos:
    - `uv-sync`, `uv-local`, `uv-test`, `uv-cov`, `uv-lint`, `uv-fmt`, `uv-typecheck`, `uv-package`, `uv-lock`
- `README.md` inclui seção de uv com:
    - instalação, sync, execução, testes, lint/format, typecheck, empacote
    - mapeamento para alvos make
- `uv.lock` presente e atualizado
- Testes executam com `uv run pytest` sem regressões
- Compatibilidade com `make venv` preservada