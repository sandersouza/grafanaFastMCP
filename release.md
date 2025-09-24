# Release Notes

## v1.0.1 – 2025-09-23

### Highlights
- Carregamento do `.env` da raiz do projeto passa a ser automático e sempre priorizado, garantindo uma configuração consistente a cada inicialização.
- Argumentos da CLI agora substituem explicitamente os valores lidos do `.env`, permitindo ajustes rápidos por execução sem alterar arquivos.
- Variáveis exportadas no shell só são consideradas quando nenhum arquivo `.env` válido é encontrado, evitando sobreposições inesperadas.
- Prompt inicial agora é carregado a partir de `instructions.md` (ou `MCP_INSTRUCTIONS_PATH`), facilitando ajustes rápidos sem rebuild e mantendo um fallback empacotado.
- Documentação do prompt cobre boas práticas para todas as tools (dashboards, Prometheus/Loki, incidents, etc.), reduzindo respostas verbosas e acelerando o fluxo com os agentes MCP.

### Melhorias principais
- Resolução de arquivos `.env` aceita caminhos de `--env-file`, `ENV_FILE`, diretório atual e varredura via `find_dotenv`, mantendo compatibilidade retroativa como fallback.
- Os caminhos informados são normalizados com `expanduser()` e `resolve()` para suportar referências como `~/secrets/.env` em qualquer shell.
- CLI lê `APP_ADDRESS`, `BASE_PATH`, `STREAMABLE_HTTP_PATH`, `LOG_LEVEL` e `TRANSPORT` do `.env` como defaults antes do parse, permitindo iniciar apenas com `python -m app`.
- Loader de instruções reutiliza cache, prioriza `MCP_INSTRUCTIONS_PATH` e loga a origem do texto; novo teste cobre o fluxo (`tests/test_instructions.py`).
- Logs adicionais no carregamento de credenciais (env/header) ajudam a depurar 401, mantendo fallback transparente quando o cliente não envia tokens.

### Itens adicionais
- `Makefile` volta a empacotar somente `run_app.py`, já que `instructions.md` fica editável na raiz.
- `env.example` lista todas as variáveis suportadas (incluindo timeouts e `MCP_INSTRUCTIONS_PATH`) com nomes corretos para evitar erros de grafia.
- `README.md` e `instructions.md` foram atualizados com orientações detalhadas de uso das ferramentas e referência ao prompt customizável.

## v1.0.0 – 2025-02-08

### Highlights
- Primeira versão estável do servidor/CLI Grafana FastMCP totalmente compatível com o conector MCP da OpenAI, incluindo transporte STDIO como padrão e suporte completo a SSE e Streamable HTTP.
- Ferramentas MCP completas para Grafana (dashboards, datasources, alerting, incident, OnCall, Prometheus, Loki, Pyroscope, Sift, navigation, admin), todas expostas com schemas validados e aderentes ao protocolo.
- Ferramenta `fetch` garante parâmetros obrigatórios (`id` string) e `search`/`search_dashboards` expõem somente `query` como requerido.
- Pacote PyInstaller (`make package`) gera um único binário auto contido (`dist/grafana-mcp`) para distribuição e uso em agentes STDIO como Claude Desktop.
- Ajustes de estabilidade para o transporte Streamable HTTP (timeouts configuráveis via `MCP_STREAMABLE_HTTP_TIMEOUT_*`) e silenciamento de logs ruidosos por padrão.

### Melhorias principais
- Suporte a expressões de tempo relativas (`now-1h`, `now-1d+2h`) nas ferramentas Grafana Asserts.
- Normalização de consultas de busca (`query`) para evitar inconsistências com clientes MCP.
- Cliente HTTP resiliente para Grafana com mensagens de erro menos verbosas em produção.
- Documentação atualizada com exemplos de integração Claude (SSE, Streamable HTTP, STDIO) e instruções de empacotamento.

### Itens adicionais
- Script `run_app.py` para empacotamento com PyInstaller.
- Makefile reorganizado (`make venv`, `make local`, `make package`) e STDIO como transporte padrão.
- Testes automatizados para ferramentas de busca e Asserts garantindo o contrato MCP.
