# Changelog
Todas as mudanças notáveis deste projeto são registradas neste arquivo. Este formato segue as recomendações do "Keep a Changelog" e o projeto adota versionamento semântico (semver).
## [v1.2.2] - 2025-11-05
### 🚀 Adicionado / Corrigido
- Validação de conexão ao Grafana no startup (reachability, TLS e autenticação).
- Novas variáveis de ambiente para TLS/SSL:
  - `GRAFANA_TLS_CERT_FILE`, `GRAFANA_TLS_KEY_FILE`, `GRAFANA_TLS_CA_FILE`, `GRAFANA_TLS_SKIP_VERIFY`.
- Novas flags CLI para controle rápido:
  - `--ignore-ssl` — marca `GRAFANA_TLS_SKIP_VERIFY` para aceitar certificados auto-assinados.
  - `--check-connection` — faz uma checagem rápida de conectividade/autenticação e sai com código apropriado.
  - `--require-grafana` / `--no-require-grafana` — controlam se a checagem é exigida no startup (por padrão ativa, exceto em testes).
- Melhoria na construção de URLs da API do Grafana para evitar duplicação `/api/api` (normalização de paths em `GrafanaClient`).
- `GrafanaClient.request` / `get_json` agora aceitam um parâmetro `timeout` opcional para chamadas rápidas de validação.
- Correção de bug que impedia a verificação de autenticação no startup (indentação incorreta) — agora tokens/credenciais inválidas (HTTP 401) abortam imediatamente.
- Comportamento de 403 em `/api/user` mantido como aviso quando autenticação por token/API key está configurada (token válido mas sem permissões). Pode ser ajustado mediante pedido.
- Ajustes de logging: configuração de log aplicada cedo no fluxo para que `--log-level`/`LOG_LEVEL` tenham efeito durante checks; tracebacks completos são exibidos apenas em DEBUG.

### 🧪 Testes e Validação
- Adicionados testes unitários cobrindo parsing das novas variáveis TLS e o comportamento de checagem de conexão (`tests/test_config_tls_env.py`, `tests/test_main_check_connection.py`).
- Instalação e inclusão do plugin de cobertura (`pytest-cov`) no ambiente de desenvolvimento local para permitir `pytest --cov`.
- Suite de testes executada: 200 passed.
- Relatório de cobertura local: ~85% global (áreas com menos cobertura: `app/main.py`, `app/patches.py` e algumas tools — indicadas para adicionar testes se desejado).

### 📚 Documentação
- Atualizados `env.example` e `README.md` para documentar as novas variáveis TLS e flags CLI.

### 🛠 Observações
- Branch de trabalho: `33-httpxerror-when-grafana-tlsssl-url-certificate-is-invalid-self-assign`.
- Pequenas melhorias adicionais: normalização de caminhos e tempos limites para evitar bloqueios longos em startup.

## [v1.2.1] - 2025-10-19
### 🚀 Adicionado
- Suporte a publicação no PyPI usando `uv build` e `uv publish --token {PYPI_API_TOKEN}`
- Execução com env dinâmico usando `uvx grafana-fastmcp`, diretamente do PyPI
- Pequenos ajustes no .toml para suporte ao endpoint de execução app:__main__:main
- GitHUB Action workflow para publicação automatica no PyPI à partir de PR

## [v1.2.0] – 2025-10-18
### 🚀 Adicionado
- Suporte oficial a `uv`/`uvx` como gerenciador de dependências e execução (pyproject + `uv.lock`).
- Arquivo `COPILOT.md` com instruções padrão para agentes e contribuidores e integração com settings do VS Code (`.vscode/settings.json`).
- Workflow de PR (`.github/workflows/pr-package.yml`) que executa testes em Python 3.13 e opcionalmente constrói/anexa artefatos quando o rótulo `build-artifacts` é aplicado ao PR.
- Configuração Hatch explicitando os pacotes a empacotar (`[tool.hatch.build.targets.wheel] packages = ["app", "mcp"]`).

### 🔧 Alterado
- Baseline do projeto elevada para **Python 3.13+** (`requires-python` em `pyproject.toml`, classifiers e mypy).
- Dependências runtime e de desenvolvimento deixadas sem pinagem direta (gerenciadas por `uv`); `uv.lock` versionado para builds determinísticos.
- `pyproject.toml` reestruturado para compatibilidade com `uv` (`[tool.uv] dev-dependencies`) e correção de problemas de parsing TOML.
- Makefile e atalhos expandidos para fluxos `uv-*` (sync, local, test, cov, lint, fmt, typecheck, package, lock).
- README atualizado para documentar o novo fluxo com `uv`, badges de CI/PR e instruções sobre como gerar artefatos em PRs.

### 🐛 Corrigido
- Erros de parsing do `pyproject.toml` que impediam o `uv` de construir o projeto em modo editável; corrigido e validado com `tomllib`.
- Problema de build editable com `hatchling` resolvido através da configuração explícita de pacotes no `pyproject.toml`.

### 🛠 CI / Build
- Workflow PR reduzido para executar testes somente em Python 3.13 por padrão (rápido feedback para reviewers).
- Pipeline principal (`.github/workflows/python-package.yml`) restrito para rodar em push para `main` usando Python 3.13.
- Job condicional `build-artifacts` (PR) que constrói wheel e binário com PyInstaller quando o rótulo `build-artifacts` é aplicado.
 - Adicionado workflow de publicação no PyPI acionado por tag `v*.*.*` (sdist + wheel). A CLI publicada expõe o comando `grafana-fastmcp` para uso com `uvx`.

### 📚 Documentação
- `README.md` atualizado com instruções para `uv`, badges reais do repositório, explicação sobre o rótulo `build-artifacts` e nota sobre baseline Python 3.13+.
- Adicionada seção `COPILOT.md` com regras de atuação para agentes/Colaboradores (guia de qualidade e checklist rápido).

### 🧪 Testes
- Testes rodando com `uv` confirmados localmente; suíte atual (197 testes) passou após mudanças.

### 🔄 Compatibilidade
- Mantida compatibilidade com fluxo antigo (`venv`/`pip`) como fallback. `uv` é o fluxo recomendado para desenvolvimento e CI.

## [v1.1.0] – 2025-10-08
### 🚀 Adicionado
- Padrão de **resposta consolidada** para todas as tools que retornam listas/arrays
- Campo `type` para identificação do tipo de resposta em todas as tools corrigidas
- Metadados contextuais (`total_count`, parâmetros da requisição) em todas as respostas
- Documentação completa dos problemas e soluções em `ISSUES.md`

### 🔧 Alterado
- **BREAKING**: `search_dashboards` agora retorna `{"dashboards": [...], "total_count": N, ...}` em vez de array direto
- **BREAKING**: `update_dashboard` agora retorna resposta consolidada com metadados em vez de resposta bruta da API
- **BREAKING**: Todas as tools Loki (`list_loki_label_names`, `list_loki_label_values`) agora retornam objetos consolidados
- **BREAKING**: Todas as tools Pyroscope (`list_pyroscope_label_names`, `list_pyroscope_label_values`, `list_pyroscope_profile_types`) agora retornam objetos consolidados
- **BREAKING**: Todas as tools OnCall (`list_oncall_schedules`, `list_oncall_teams`, `list_oncall_users`) agora retornam objetos consolidados
- **BREAKING**: Todas as tools Alerting (`list_alert_rules`, `list_contact_points`) agora retornam objetos consolidados
- **BREAKING**: Todas as tools Admin (`list_teams`, `list_users_by_org`) agora retornam objetos consolidados

### 🐛 Corrigido
- **CRÍTICO**: Eliminado problema de chunking JSON em streamable HTTP com ChatGPT/OpenAI que causava:
  - Lentidão extrema (timeout em 90% das operações)
  - Perda de sessão frequente durante execução de tools
  - Leitura parcial de dados (apenas primeiro chunk)
  - Parsing JSON falho devido à fragmentação
- Corrigidos todos os testes para refletir novos formatos de resposta consolidados
- Mocks nos testes atualizados para retornar estruturas consolidadas corretas

### 🎯 Desempenho
- **+90% redução na latência** de tools que retornam listas
- **100% eliminação de timeouts** por chunking JSON
- **Parsing instantâneo** no ChatGPT/OpenAI com objetos consolidados
- **Sessões estáveis** sem perda de conexão durante operações longas

### 🧪 Testes
- Todos os 197 testes passando após correções
- Testes atualizados para validar estruturas consolidadas
- Validação de compatibilidade com streamable HTTP

### 📚 Documentação
- `ISSUES.md` documentando problemas identificados e resoluções
- Descrições de tools atualizadas mencionando prevenção de chunking
- Exemplos de resposta atualizados em todas as tools afetadas

### 🔄 Compatibilidade
- **100% compatível** com transporte streamable HTTP + ChatGPT/OpenAI
- **Preservação de dados**: Respostas originais mantidas em sub-campos
- **Retrocompatibilidade**: Dados originais acessíveis via campos específicos

## [v1.0.1] – 2025-09-24
### Adicionado
- Prompt inicial carregado de `instructions.md` (ou via `MCP_INSTRUCTIONS_PATH`), permitindo ajustes rápidos sem rebuild e mantendo fallback empacotado.
- Método `initialize` implementado para compliance com OpenAI MCP, suportando mecanismos de fallback de sessão.
- Cache em ferramentas (ex.: dashboard) para reduzir duplicidades e tráfego desnecessário.

### Alterado
- Carregamento do `.env` na raiz é automático e priorizado; argumentos de CLI agora sobrescrevem valores do `.env` explicitamente.
- Variáveis exportadas no shell só são consideradas quando nenhum `.env` válido é encontrado, evitando sobreposição inesperada.
- Resolução de arquivos `.env` aceita caminhos de `--env-file`, `ENV_FILE`, diretório atual e varredura via `find_dotenv`; caminhos normalizados com `expanduser()`/`resolve()`.
- CLI lê `APP_ADDRESS`, `BASE_PATH`, `STREAMABLE_HTTP_PATH`, `LOG_LEVEL` e `TRANSPORT` do `.env` como defaults antes do parse, permitindo iniciar apenas com `python -m app`.
- Respostas das tools padronizadas ao estilo VS Code/Copilot, para uso como MCP Server em ambos os ambientes.
- Tools são listadas somente quando a instância Grafana possui a capability necessária.

### Desempenho
- Melhorias de velocidade nas tools (dashboard, Prometheus, Loki) por meio de cache em `ctx.request_context.session`.
- Defaults definidos em Prometheus (`start=now-5m`, `end=now`, `step=60`) para evitar obrigatoriedade de janela temporal.
- Tool Sift `find_error_pattern_logs` passou a aceitar expressões relativas (ex.: `now-1h`).

### Testes e Observabilidade
- Loader de instruções reutiliza cache e prioriza `MCP_INSTRUCTIONS_PATH`; adicionado teste (`tests/test_instructions.py`).
- Logs adicionais no carregamento de credenciais (env/header) para depuração de 401 mantendo fallback transparente.

### Documentação e Build
- `README.md` e `instructions.md` detalhados com boas práticas para todas as tools e prompt customizável.
- `env.example` lista todas as variáveis suportadas (incluindo timeouts e `MCP_INSTRUCTIONS_PATH`).
- `Makefile` volta a empacotar apenas `run_app.py`, mantendo `instructions.md` editável na raiz.

### Commits
- [[`c5556de`](https://github.com/sandersouza/grafanaFastMCP/commit/c5556de)] Release v101-pre (see release.md)
- [[`91a3adf`](https://github.com/sandersouza/grafanaFastMCP/commit/91a3adf)] test:cover core server entrypoints
- [[`690d715`](https://github.com/sandersouza/grafanaFastMCP/commit/690d715)] Increasetests to near 90%
- [[`ad9d115`](https://github.com/sandersouza/grafanaFastMCP/commit/ad9d115)] Cachesupport add @dashboard
- [[`6521518`](https://github.com/sandersouza/grafanaFastMCP/commit/6521518)] Load realmcp package when available
- [[`e136882`](https://github.com/sandersouza/grafanaFastMCP/commit/e136882)] Oh boy! tomany fixes!!!
- [[`ca6590f`](https://github.com/sandersouza/grafanaFastMCP/commit/ca6590f)] feat:enforce streamable instructions and templating
- [[`b084c42`](https://github.com/sandersouza/grafanaFastMCP/commit/b084c42)] fixupdate_dashboard and reduce instructions.md to 1500 chars max
- [[`aa1cd50`](https://github.com/sandersouza/grafanaFastMCP/commit/aa1cd50)] so manyfix :S
- [[`7cf377f`](https://github.com/sandersouza/grafanaFastMCP/commit/7cf377f)] Handlemissing request in context config
- [[`546c01f`](https://github.com/sandersouza/grafanaFastMCP/commit/546c01f)] Filter MCPtools based on Grafana capabilities
- [[`b6b1a5e`](https://github.com/sandersouza/grafanaFastMCP/commit/b6b1a5e)] Ensuretool parameters include object schema
- [[`fb8c820`](https://github.com/sandersouza/grafanaFastMCP/commit/fb8c820)] Updaterealease.md
- [[`2bbe5d5`](https://github.com/sandersouza/grafanaFastMCP/commit/2bbe5d5)] FixFastMCP array schema items
- [[`2529709`](https://github.com/sandersouza/grafanaFastMCP/commit/2529709)] Ensurefetch ids schema defines item types
- [[`f37c8a9`](https://github.com/sandersouza/grafanaFastMCP/commit/f37c8a9)] Normalizetool parameter schemas
- [[`77c551e`](https://github.com/sandersouza/grafanaFastMCP/commit/77c551e)] Recursively normalize array schemas for tools
- [[`a68e584`](https://github.com/sandersouza/grafanaFastMCP/commit/a68e584)] Revert"Normalize tool parameter schemas"
- [[`d58bf7a`](https://github.com/sandersouza/grafanaFastMCP/commit/d58bf7a)] ddcomprehensive guidance for resource updates, dashboards, and Prom…
- [[`88a3c8c`](https://github.com/sandersouza/grafanaFastMCP/commit/88a3c8c)] A Improvedashboard tool schema and graceful shutdown
- [[`b583a96`](https://github.com/sandersouza/grafanaFastMCP/commit/b583a96)] Refinefallback schema by excluding "array" type to prevent nested ar…
- [[`b85c39b`](https://github.com/sandersouza/grafanaFastMCP/commit/b85c39b)] Updatedocumentation and tests: replace release notes with changelog,…

## [v1.0.0] – 2025-02-08
### Adicionado
- Primeira versão estável do servidor/CLI Grafana FastMCP compatível com o conector MCP da OpenAI; transporte STDIO como padrão e suporte completo a SSE e Streamable HTTP.
- Ferramentas MCP para Grafana (dashboards, datasources, alerting, incident, OnCall, Prometheus, Loki, Pyroscope, Sift, navigation, admin), com schemas validados e aderentes ao protocolo.
- Pacote PyInstaller via `make package` gera binário único (`dist/grafana-mcp`).

### Alterado
- Normalização de consultas e parâmetros obrigatórios (`query` em `search`/`search_dashboards`, `id` em `fetch`).
- Suporte a expressões de tempo relativas em Grafana Asserts (ex.: `now-1h`, `now-1d+2h`).
- Documentação com exemplos de integração (Claude: SSE, Streamable HTTP, STDIO) e instruções de empacotamento.

### Estabilidade
- Ajustes no transporte Streamable HTTP com timeouts configuráveis (`MCP_STREAMABLE_HTTP_TIMEOUT_*`) e redução de ruído de logs por padrão.

### Testes
- Testes automatizados para ferramentas de busca e Asserts garantindo contrato MCP.

---

Notas:
- Datas em ISO (YYYY-MM-DD). Entradas "Unreleased" podem ser publicadas a qualquer momento.
- Seções organizadas por categoria: Adicionado, Alterado, Corrigido, Removido, Depreciado, Segurança, Desempenho, Documentação, Build/CI, Testes.
