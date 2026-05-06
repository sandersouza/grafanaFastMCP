DOCUMENTATION: Atualizei a documentação da feature `get_grafana_versions`.

Arquivos alterados:
- [README.md](/Users/sandersouza/Developer/grafanaFastMCP/README.md:256): detalha endpoints usados e payload.
- [ISSUES.md](/Users/sandersouza/Developer/grafanaFastMCP/ISSUES.md:40): registra a fase `DOCUMENTATION`.
- [docs/issues/grafana-versions-tool.md](/Users/sandersouza/Developer/grafanaFastMCP/docs/issues/grafana-versions-tool.md:24): consolida validações e limitações.
- [docs/handoff/test/without-agent-instructions.md](/Users/sandersouza/Developer/grafanaFastMCP/docs/handoff/test/without-agent-instructions.md:5): handoff final atualizado.

Validação: não rodei testes nesta fase porque só houve alteração documental. Mantive os resultados anteriores: testes focados e suíte completa passaram com `python -m pytest`; `uv` não está instalado; `ruff check .` segue bloqueado por débitos preexistentes fora do escopo.