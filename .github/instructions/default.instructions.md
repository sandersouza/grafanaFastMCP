# Default Instructions for Agents and Contributors
These are the default rules for the `grafanaFastMCP` project. They apply to people and agents when suggesting, reviewing, or applying changes.

## Core Rules
- Keep `ISSUES.md`, when present, focused only on the current issue or feature. Do not place general project guidance there.
- Use the active GitHub issue as the source of truth for the branch scope when an issue exists.
- Preserve current behavior and compatibility unless the task explicitly changes it.
- Keep regressions at zero.
- Follow `AGENTS.md` for project-specific architecture, runtime, and tokenomics constraints.
- Update `README.md` when a feature changes user-facing setup, commands, configuration, or behavior.
- Add or update tests for new behavior.
- Keep documentation clear: use comments, docstrings, and examples only where they add practical value.
- Update `CHANGELOG.md` when `__version__.py` changes.
- Write all documentation and code comments in English.
- Document persistent operational context in `/docs/handoff/` and reference it into `CONTEXT.md`, not in instructions files.
- All persistent operational context must be in english and follow the same style as `CONTEXT.md`.
- Don't document files and folders exclude in .gitignore, except when they are relevant for the project and not self-explanatory.
- When in doubt about documentation placement, prefer `docs/project-documentation/` for technical details and `docs/handoff/` for branch-specific context.
- When in doubt about documentation content, prefer concise, relevant information with references to consulted files or modules over excessive historical detail.

## Local Workflow
- Prefer `uv` for dependency management and command execution. See `AGENTS.md` and `.github/instructions/good-pratices.instructions.md` for project-specific validation commands.\
- If a legacy virtual environment is required, activate it before running commands:

```bash
source ./venv/bin/activate
```

- If lint finds code smells that can be safely autofixed, apply the configured formatter/linter first and manually address the remaining issues.

## Collaboration Rules
- Satisfy all explicit user requirements.
- If details are missing, make one or two reasonable assumptions and document them briefly.
- Prefer small, reversible changes.
- Avoid broad refactors unless they are necessary for the requested work.
- Ask before destructive operations or changes with high regression risk.
- Do not revert unrelated user changes.
- Document assumptions when closing the branch or finalizing work.

## Pull Request Checklist
- [ ] Code compiles and does not introduce obvious regressions.
- [ ] Lint passes with the project tools.
- [ ] Tests pass or any skipped verification is explicitly documented.
- [ ] `README.md` is updated when user-facing behavior changes.
- [ ] `CHANGELOG.md` is updated when the version changes.
- [ ] Comments and docstrings are updated when needed.
- [ ] Tokenomics experiment artifacts stay separate from MCP runtime behavior.
