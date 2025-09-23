<table>
  <tr>
    <td align="left" valign="middle">
      <h1>Grafana FastMCP Server / CLI</h1>
    </td>
    <td align="right" valign="middle">
      <a href="https://link.mercadopago.com.br/buymecoke">
        <img src="donation.png" alt="Me compre um café!" width="140">
      </a>
    </td>
  </tr>
</table>

## Visão geral
Python FastMCP Server / CLI ( OpenAI Compliance ), com suporte a transportes Server-Sent Events (SSE), Streamable HTTP e STDIO. A aplicação expõe recursos de uma instância Grafana para agentes compatíveis com o protocolo MCP, oferecendo operações para busca, criação e atualização de dashboards, exploração de logs via Loki, consulta de datasources, gestão de alertas, incidentes, turnos de on-call e acesso a dados de observabilidade (Prometheus, Pyroscope, Grafana Sift e muito mais).

## Estrutura do projeto
Todo o código-fonte fica no diretório `app/`, deixando a raiz do repositório reservada para arquivos de configuração (como `.env`, `Dockerfile`, `requirements.txt` e este `README`). A organização completa é:

```
.
├── app/
│   ├── __init__.py            # Metadados e versão do pacote
│   ├── __main__.py            # Permite executar com `python -m app`
│   ├── config.py              # Carregamento e saneamento das variáveis de ambiente
│   ├── context.py             # Resolução de configuração por requisição
│   ├── grafana_client.py      # Cliente HTTP assíncrono para a API do Grafana
│   ├── main.py                # CLI que instancia e publica o servidor MCP
│   ├── patches.py             # Ajustes de compatibilidade para FastMCP/transportes
│   ├── server.py              # Fábrica do FastMCP e registro das ferramentas
│   └── tools/                 # Coleção de ferramentas MCP (dashboards, Loki, etc.)
├── legacy/                    # Implementação original em Go preservada para consulta
├── run_app.py                 # Entrypoint usado pelo PyInstaller (`make package`)
├── tests/                     # Testes automatizados em Python
├── Dockerfile                 # Imagem Docker/Podman
├── Makefile                   # Atalhos de automação (venv, package, docker...)
├── env.example                # Exemplo de variáveis de ambiente
├── requirements.txt           # Dependências de runtime
└── pytest.ini                 # Configuração do pytest
```

Consulte [release.md](./release.md) para detalhes das versões publicadas.

Cada submódulo em `app/tools/` registra um conjunto de ferramentas MCP, abrangendo desde administração de usuários até consultas de observabilidade e automação de incidentes.

## Requisitos
- Python 3.11 ou superior
- Instância Grafana acessível (local ou remota) e credenciais de API válidas

## Configuração
A aplicação lê os parâmetros de conexão a partir de variáveis de ambiente, argumentos de linha de comando ou cabeçalhos HTTP. As principais variáveis disponíveis em `app/config.py` são:

- `GRAFANA_URL`: URL base da instância Grafana (padrão `http://localhost:3000`).
- `GRAFANA_SERVICE_ACCOUNT_TOKEN`: token de service account recomendado.
- `GRAFANA_API_KEY`: chave de API legada (use apenas se não houver service account).
- `GRAFANA_USERNAME` / `GRAFANA_PASSWORD`: credenciais para autenticação básica.
- `GRAFANA_ACCESS_TOKEN` / `GRAFANA_ID_TOKEN`: tokens OIDC utilizados quando disponíveis.

Defina as variáveis conforme o método de autenticação que estiver usando. Também é possível fornecer certificados TLS personalizados por meio da estrutura `TLSConfig` definida no módulo de configuração.

## Execução
Após configurar o ambiente, execute o servidor MCP com:

```bash
python -m app --address localhost:8000 --log-level INFO
```

Por padrão, o transporte STDIO é utilizado. Para executar em modos HTTP, informe `--transport sse` ou `--transport streamable-http` conforme necessário.

Parâmetros úteis:
- `--address`: endereço e porta nos quais o servidor será publicado.
- `--base-path`: caminho base para expor o transporte HTTP (padrão `/`).
- `--streamable-http-path`: caminho do endpoint Streamable HTTP (padrão `mcp`; aceita valores absolutos ou relativos ao `--base-path`).
- `--transport`: transporte MCP a utilizar (`sse`, `streamable-http` ou `stdio`; padrão `stdio`).
- `--log-level`: nível de log (`DEBUG`, `INFO`, `WARNING`, etc.).
- `--debug`: ativa modo de depuração do FastMCP.
- `--version`: imprime a versão da aplicação e encerra.

O servidor registra automaticamente todas as ferramentas MCP descritas em `app/tools/` através da função `register_all`. Agentes MCP podem consumir as capacidades para listar datasources, atualizar dashboards, executar consultas no Loki e gerar links de navegação no Grafana, entre outras.

Também é possível sobrescrever as credenciais do Grafana diretamente pela CLI, utilizando os mesmos nomes das variáveis de ambiente, por exemplo:

```bash
python -m app --address localhost:5501 --GRAFANA_URL http://127.0.0.1:3000 \
  --GRAFANA_SERVICE_ACCOUNT_TOKEN glsa_example_token
```

### Conformidade com a especificação MCP da OpenAI
Esta implementação segue os requisitos publicados em [platform.openai.com/docs/mcp#create-an-mcp-server](https://platform.openai.com/docs/mcp#create-an-mcp-server):

- As ações `search` e `search_dashboards` expõem somente o parâmetro obrigatório `query`, tipado como `string`.
- A ação `fetch` exige apenas o parâmetro `id`, também tipado como `string`, mantendo campos opcionais (`uid`, `url`, etc.) para enriquecer o contexto sem ferir a especificação.
- Os transportes SSE, Streamable HTTP e STDIO respeitam os caminhos e formatos esperados pelo conector MCP da OpenAI e podem ser montados em um `base_path` customizado.
- O servidor publica metadados (`instructions`, lista de ferramentas e schemas JSON) diretamente do `FastMCP`, assegurando compatibilidade com clientes que validam o contrato MCP.

## Makefile
O repositório disponibiliza um `Makefile` com alvos que agilizam as tarefas mais comuns de desenvolvimento. O alvo padrão (`make`) executa `make help`, listando um resumo dos principais comandos disponíveis.

### Ambiente local
- `make venv`: cria o ambiente virtual e instala as dependências listadas em `requirements.txt`.
- `make local`: inicia o servidor MCP utilizando o virtualenv criado; o comando lê automaticamente variáveis definidas em `.env`.
- `make package`: gera um executável único (`dist/grafana-mcp`) via PyInstaller.

Variáveis como `APP_ADDRESS`, `BASE_PATH`, `STREAMABLE_HTTP_PATH`, `LOG_LEVEL`, `TRANSPORT` e `ENV_FILE` podem ser sobrescritas diretamente na linha de comando (`make run-local APP_ADDRESS=127.0.0.1:9000 TRANSPORT=streamable-http STREAMABLE_HTTP_PATH=/stream`).

Após executar `make package`, o binário resultante pode ser distribuído como comando único, sem depender do Python local ou do virtualenv. Os assets e dependências Python são incorporados pelo PyInstaller.

### Containers
- `make docker` / `make podman`: empacotam a aplicação em uma imagem Docker ou Podman.

Os alvos de containers respeitam variáveis como `IMAGE_NAME`, `CONTAINER_NAME`, `APP_PORT`, `TRANSPORT` e `ENV_FILE`, permitindo adaptar os comandos ao seu fluxo de trabalho.

## Ferramentas disponíveis

### Admin
- `list_teams`: busca times da organização por nome, retornando identificadores e URLs.
- `list_users_by_org`: lista todos os usuários da organização atual com e-mail, cargo e status.

### Alerting
- `list_alert_rules`: lista regras de alerta com paginação e filtros por label.
- `get_alert_rule_by_uid`: obtém a configuração completa de uma regra de alerta pelo UID.
- `list_contact_points`: lista contact points configurados no Grafana Alerting.

### Asserts
- `get_assertions`: recupera o resumo de Grafana Asserts para uma entidade e janela de tempo.

Os parâmetros `startTime` e `endTime` aceitam timestamps RFC3339 (por exemplo, `2024-01-02T03:04:05Z`) ou expressões relativas baseadas em `now`, como `now-1h` ou `now-1d+2h`.

### Dashboard
- `get_dashboard_by_uid`: retorna o JSON completo de um dashboard.
- `get_dashboard_summary`: gera um resumo compacto de painéis, variáveis e metadados.
- `get_dashboard_panel_queries`: extrai queries LogQL/PromQL e metadados dos painéis.
- `get_dashboard_property`: acessa propriedades específicas usando uma expressão semelhante a JSONPath.
- `update_dashboard`: cria ou atualiza um dashboard existente.

### Datasources
- `list_datasources`: lista datasources disponíveis com filtro por tipo.
- `get_datasource_by_uid`: obtém detalhes completos de um datasource pelo UID.
- `get_datasource_by_name`: obtém detalhes completos de um datasource pelo nome configurado.

### Incident
- `list_incidents`: lista incidentes (com filtros de status e drilldown opcional).
- `get_incident`: recupera detalhes completos de um incidente específico.
- `create_incident`: cria um novo incidente Grafana.
- `add_activity_to_incident`: adiciona notas à linha do tempo do incidente.

### Loki
- `query_loki_logs`: executa consultas LogQL e retorna logs correspondentes.
- `query_loki_stats`: retorna estatísticas agregadas para um seletor LogQL.
- `list_loki_label_names`: lista labels disponíveis em um datasource Loki.
- `list_loki_label_values`: lista valores para um label específico em Loki.

### Navigation
- `generate_deeplink`: gera URLs de navegação para dashboards, painéis ou Explore com parâmetros opcionais.

### OnCall
- `list_oncall_teams`: lista equipes configuradas no Grafana OnCall.
- `list_oncall_schedules`: retorna escalas de plantão com filtros opcionais.
- `get_oncall_shift`: consulta detalhes de um turno específico.
- `get_current_oncall_users`: lista quem está de plantão neste momento.
- `list_oncall_users`: lista usuários ou busca um usuário específico do OnCall.

### Prometheus
- `query_prometheus`: executa consultas PromQL em datasources Prometheus.
- `list_prometheus_metric_names`: lista métricas disponíveis.
- `list_prometheus_metric_metadata`: retorna metadados para métricas.
- `list_prometheus_label_names`: lista labels disponíveis.
- `list_prometheus_label_values`: retorna valores para um label específico.

### Pyroscope
- `list_pyroscope_profile_types`: lista tipos de perfil suportados.
- `list_pyroscope_label_names`: lista labels disponíveis em um datasource Pyroscope.
- `list_pyroscope_label_values`: lista valores para um label.
- `fetch_pyroscope_profile`: obtém um perfil em formato DOT para visualização.

### Search
- `search`: busca dashboards no Grafana (modo genérico usado por clientes MCP).
- `search_dashboards`: busca dashboards com metadados detalhados.
- `fetch`: recupera dados completos de recursos retornados pelo search (dashboards via `id` ou `uid`).

### Sift
- `list_sift_investigations`: lista investigações recentes do Grafana Sift.
- `get_sift_investigation`: recupera detalhes de uma investigação específica.
- `get_sift_analysis`: acessa um resultado de análise associado a uma investigação.
- `find_error_pattern_logs`: executa o check `ErrorPatternLogs` para encontrar padrões de erro.
- `find_slow_requests`: executa o check `SlowRequests` para identificar chamadas lentas.

Cada ferramenta utiliza o cliente HTTP assíncrono definido em `app/grafana_client.py`, adicionando os cabeçalhos e autenticações necessários para conversar com a API do Grafana.

## Transportes MCP suportados

### Server-Sent Events (SSE)
O servidor publica um endpoint SSE capaz de manter uma conexão HTTP aberta para envio de eventos do servidor para o cliente. Ao executar `python -m app --transport sse`, o FastMCP monta dois caminhos principais:

1. `GET /sse`: inicializa a sessão SSE, retornando `Content-Type: text/event-stream` e enviando eventos `message`, `ping` e `response` conforme o protocolo MCP.
2. `POST /messages/`: recebe mensagens do cliente com prompts, chamadas de ferramenta ou confirmações. Cada payload é correlacionado por ID e as respostas são emitidas pela conexão SSE aberta.

Esse fluxo permite que plataformas de IA ou agentes MCP recebam respostas em streaming enquanto enviam comandos de maneira independente. O caminho base pode ser customizado via `--base-path` (por exemplo, `/grafana` expõe o SSE em `/grafana/sse` e o endpoint de mensagens em `/grafana/messages/`).

### Streamable HTTP
Com `python -m app --transport streamable-http`, o servidor expõe um único endpoint HTTP compatível com o transporte Streamable HTTP do MCP. Por padrão, o caminho é `/mcp`, mas ele pode ser ajustado com `--streamable-http-path` (valores relativos respeitam o `--base-path`). Esse modo é útil para clientes que preferem uma API HTTP tradicional, mantendo suporte a respostas parciais via streaming.

Para investigações ou buscas longas, ajuste os timeouts padrão do servidor HTTP definindo variáveis de ambiente antes de iniciar o processo:

- `MCP_STREAMABLE_HTTP_TIMEOUT_KEEP_ALIVE` (padrão `65` segundos)
- `MCP_STREAMABLE_HTTP_TIMEOUT_NOTIFY` (padrão `120` segundos)
- `MCP_STREAMABLE_HTTP_TIMEOUT_GRACEFUL_SHUTDOWN` (padrão igual ao maior valor entre o notify e `120` segundos)

Valores maiores evitam que clientes MCP desconectem durante respostas demoradas, aproximando-se da robustez observada no transporte SSE.

### STDIO
O transporte STDIO (`python -m app --transport stdio`) permite executar o servidor como um processo filho de um agente, comunicando-se por entrada e saída padrão. Não há endpoints HTTP nesse modo, tornando-o ideal para integrações locais ou ambientes restritos.

## Integração com Claude
Claude Desktop (macOS/Windows/Linux) já reconhece os três transportes publicados por este servidor. Basta adicionar um bloco em `claude_desktop_config.json` com o comando desejado, o transporte correspondente e as variáveis de ambiente apontando para a sua instância Grafana.

### SSE (streaming bidirecional)
```json
{
  "mcpServers": {
    "grafana-sse": {
      "command": "python",
      "args": [
        "-m", "app",
        "--address", "127.0.0.1:8000",
        "--transport", "sse"
      ],
      "transport": {
        "type": "sse",
        "url": "http://127.0.0.1:8000/sse",
        "messagesUrl": "http://127.0.0.1:8000/messages/"
      },
      "env": {
        "GRAFANA_URL": "https://grafana.example.com",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "glsa_example_token"
      }
    }
  }
}
```

Nesse modo, Claude consome respostas em streaming pela sessão SSE enquanto envia comandos HTTP independentes para o endpoint de mensagens.

### Streamable HTTP (endpoint único)
```json
{
  "mcpServers": {
    "grafana-http": {
      "command": "python",
      "args": [
        "-m", "app",
        "--address", "127.0.0.1:8100",
        "--transport", "streamable-http",
        "--streamable-http-path", "mcp"
      ],
      "transport": {
        "type": "http",
        "url": "http://127.0.0.1:8100/mcp",
        "streaming": true
      },
      "env": {
        "GRAFANA_URL": "https://grafana.example.com",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "glsa_example_token"
      }
    }
  }
}
```

Claude enviará todas as requisições MCP para o único endpoint configurado, recebendo respostas parciais usando o modo Streamable HTTP do FastMCP.

### STDIO (processo filho)
```json
{
  "mcpServers": {
    "grafana-stdio": {
      "command": "/caminho/para/dist/grafana-mcp",
      "transport": {
        "type": "stdio"
      },
      "env": {
        "GRAFANA_URL": "https://grafana.example.com",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "glsa_example_token"
      }
    }
  }
}
```

Esse modo executa o servidor como subprocesso direto do Claude, ideal para ambientes offline ou quando não se deseja abrir portas locais.
Antes de configurar o comando no Claude, execute `make package` para gerar o binário `dist/grafana-mcp` utilizado no exemplo acima.

## Próximos passos
O diretório `app/` pode receber novos módulos ou ferramentas MCP específicas da sua instância. Recomenda-se adicionar testes automatizados sob `app/tests/` (ou estrutura equivalente) à medida que novos recursos forem implementados.
