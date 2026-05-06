# Agent Instructions

## Project

`grafanaFastMCP` is a Python 3.13+ MCP server/CLI built with FastMCP. It exposes Grafana capabilities as MCP tools across STDIO, SSE, and Streamable HTTP transports.

The runtime entrypoint is `app/main.py`. Tool modules live under `app/tools/`, shared Grafana API access lives in `app/grafana_client.py`, configuration lives in `app/config.py`, and tests live under `tests/`.

## Branch Role

This branch, `test/tokenomics-tests-with-instructions`, is the instrumentation branch for token-cost reduction techniques. Any technique intended to reduce token usage must be designed, documented, instrumented, and validated here before comparison against the generic branch or promotion to another workflow.

This branch may contain specialized instructions, semantic maps, architecture summaries, log normalization scripts, and stage-labeling conventions. These artifacts are part of the tokenomics experiment and must not be treated as MCP runtime behavior.

## Working Rules

- Read the current file before changing any tool, payload, documentation, or test.
- Prefer existing project patterns over new abstractions.
- Keep runtime changes separate from experiment harness changes.
- Do not introduce specialized instructions into `test/tokenomics-tests-without-instructions`.
- Do not use results from branches contaminated by incorrect or unrelated instructions.
- When changing runtime behavior, add or update focused tests.
- Use `uv run pytest` and `uv run ruff check .` for verification when the change touches Python behavior.
- If you don't have knowledgement about the project, read all documention on `docs/project-documentation/*.md`
- When you add/remove a feature, update all documentation with informations about it.
- When we finish/close a branch, update `README.md` and `README-PTBR.md`.
- Update ISSUE and local copy of ISSUE with a synthetic information about work in session/branch.

## MCP Runtime Pattern

The project follows a local pattern named **Capability-Gated MCP Tool Facade**:

- `app/main.py` creates and configures the FastMCP application.
- `app/config.py` reads CLI and environment configuration.
- `app/grafana_client.py` centralizes async HTTP access to Grafana.
- `app/tools/*.py` register focused MCP tool groups.
- Tool registration is conditional on Grafana capabilities where applicable.
- List-like tool responses are normalized into consolidated payloads to reduce Streamable HTTP chunking issues.

## Tokenomics Experiment Rules

- Treat `tokenomics.experiment/` as the experiment harness, not production runtime.
- Normalize logs through `tokenomics.experiment/scripts/normalize_agent_logs.py`.
- Keep task definitions stable between branches.
- Compare runs by branch, task, stage, token usage, elapsed time, human prompts, file churn, test/lint loops, and final result.
- Record `reasoning_tokens` as `null` when unavailable, never as `0`.

## Documentation good pratices
`/docs/issues`: folder for issues local copies
`/docs/milestones`: folder for milestones local copies
`/docs/templates`: folder for any type of documentation for templates to be follow for agents and team mates
`/docs/handoff`: folder to document agent handoff of current work after any iteration.
`/docs/project-documentation`: folder with all informations like `code patterns` e `directory tree information` os project

# AGENTS

## Objetivo do projeto

Construir uma base baremetal para Raspberry Pi 3B e evoluir até um emulador MSX executável sem sistema operacional.

## Fonte canonica de regras de fluxo
- As regras operacionais estao centralizadas em `.github/instructions/`.
- Regra unica: sempre carregar e aplicar **todos** os arquivos `*.instructions.md` dessa pasta.
- Leia a documentação do projeto em caso de dúvidas, e para minimizar o custo de tokens para tarefas como CODE REVIEW e TESTING.

## Prioridade interna:
- Novas regras devem ser adicionadas dentro de seus arquivos de contexto (ex.: regras de gestao em `project-management.instructions.md`).
- Regras que impactam o fluxo geral do projeto (ex.: sincronizacao de docs, atualizacao de contexto) devem ser adicionadas em `docs-sync.instructions.md`.
- Regras que impactam a organizacao do trabalho e ciclo de desenvolvimento devem ser adicionadas em `project-management.instructions.md`.
- Regras que impactam a implementacao tecnica e padrao de codigo devem ser adicionadas em arquivos de instrucoes especificos (ex.: `debug-layer.instructions.md` para regras de debug layer).
- Caso o arquivo de instrucoes especifico ainda nao exista crie um novo arquivo.
- Regras marcadas como imutaveis/obrigatorias tem precedencia maxima.
- Regras de preferencia podem ser flexibilizadas apenas com justificativa tecnica registrada.

## Referencias rapidas

- Contexto persistente da branch: `docs/handoff/<nome-da-branch>.md`
- Ponteiro de contexto atual: `CONTEXT.md`
- Fonte de verdade de gestao: `docs/github-project-management.md`
