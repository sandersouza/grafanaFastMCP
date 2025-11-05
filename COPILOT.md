# Instruções padrão para agentes e contribuidores

Estas são as regras padrão do projeto grafanaFastMCP. Devem ser seguidas por pessoas e por agentes (ex.: Copilot Chat) ao sugerir ou aplicar mudanças.

- ISSUES.md: mantenha apenas informações sobre a ISSUE/Feature atual. Não coloque guias gerais ali.
- ISSUES.md: Baseia às informações, na ISSUE criada no Github, relacionadas à branch em uso caso exista.
- Não quebre o funcionamento atual. Preserve compatibilidade e comportamento; mantenha regressões em zero.
- Erros de LINT devem ser evitados e corrigidos antes de concluir a tarefa.
- Ao testar suas alterações, sempre rode o flake8 e caso hajam code smells, rode o autopep8.
- As LINT issues não resolvidas pelo autopep8, precisam ser tratadas por você.
- README.md deve ser atualizado com instruções de toda e qualquer feature implementada / atualizada.
- Os testes unitários devem permanecer funcionando; novas funcionalidades devem incluir novos testes.
- Mantenha boas práticas de documentação: comentários claros, docstrings e exemplos quando útil.
- Sempre atualize o CHANGELOG.md quando o __version__.py for atualizado colocando as alterações feitas

## Como o agente deve agir
- Cumpra todos os requisitos explícitos do pedido do usuário; se algo estiver faltando, faça 1–2 suposições razoáveis e documente-as brevemente.
- Prefira mudanças pequenas e reversíveis. Evite refatorações amplas sem necessidade.
- Após mudanças relevantes em código, rode lint e testes localmente. Se não for possível, informe o que verificar e como rodar.
- Se houver risco de regressão ou ambiguidade, peça confirmação antes de seguir com mudanças destrutivas.
- No mode agent, ao abrir um novo terminal para execução de comandos, carrego o .venv ( source ./venv/bin/activate )

## Checklist rápida (antes de abrir PR)
- [ ] ISSUES.md reflete apenas a issue/feature em andamento
- [ ] Código compila e não introduz regressões aparentes
- [ ] Lint sem erros (ruff/mypy/flake8, conforme aplicável)
- [ ] README.md atualizado com instruções de uso/execução da nova funcionalidade
- [ ] Testes existentes passam; novos testes cobrindo a funcionalidade foram adicionados
- [ ] Comentários/docstrings atualizados quando necessário
- [ ] CHANGELOG.md deve ser atualizado com as issue/features em andamento
