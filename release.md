# Release Notes

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

Boa publicação! 🎉
