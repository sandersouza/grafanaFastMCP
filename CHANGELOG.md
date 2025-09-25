# Changelog
Todas as mudanças notáveis deste projeto são registradas neste arquivo. Este formato segue as recomendações do "Keep a Changelog" e o projeto adota versionamento semântico (semver).

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
