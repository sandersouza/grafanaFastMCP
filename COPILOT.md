# Instruções padrão para agentes e contribuidores

Estas são as regras padrão do projeto grafanaFastMCP. Devem ser seguidas por pessoas e por agentes (ex.: Copilot Chat) ao sugerir ou aplicar mudanças.

- ISSUES.md: mantenha apenas informações sobre a ISSUE/Feature atual. Não coloque guias gerais ali.
- Não quebre o funcionamento atual. Preserve compatibilidade e comportamento; mantenha regressões em zero.
- Erros de LINT devem ser evitados e corrigidos antes de concluir a tarefa.
- README.md deve ser atualizado com instruções de toda e qualquer feature implementada.
- Os testes unitários devem permanecer funcionando; novas funcionalidades devem incluir novos testes.
- Mantenha boas práticas de documentação: comentários claros, docstrings e exemplos quando útil.

## Como o agente deve agir
- Cumpra todos os requisitos explícitos do pedido do usuário; se algo estiver faltando, faça 1–2 suposições razoáveis e documente-as brevemente.
- Prefira mudanças pequenas e reversíveis. Evite refatorações amplas sem necessidade.
- Após mudanças relevantes em código, rode lint e testes localmente. Se não for possível, informe o que verificar e como rodar.
- Se houver risco de regressão ou ambiguidade, peça confirmação antes de seguir com mudanças destrutivas.

## Checklist rápida (antes de abrir PR)
- [ ] ISSUES.md reflete apenas a issue/feature em andamento
- [ ] Código compila e não introduz regressões aparentes
- [ ] Lint sem erros (ruff/mypy, conforme aplicável)
- [ ] README.md atualizado com instruções de uso/execução da nova funcionalidade
- [ ] Testes existentes passam; novos testes cobrindo a funcionalidade foram adicionados
- [ ] Comentários/docstrings atualizados quando necessário
- [ ] CHANGELOG.md deve ser atualizado com as issue/features em andamento
